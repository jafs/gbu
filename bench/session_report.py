"""Línea de comandos del analizador de sesiones de gbu.

Dos modos:

    python bench/session_report.py <ruta-proyecto> [--desde <fecha-o-commit>]
                                   [--version <x.y.z>] [--salida <dir>]

    python bench/session_report.py --comparar <proyecto> [<base> <nueva>]

El primero analiza un proyecto y archiva el informe. El segundo cruza dos
informes ya archivados y saca el cuadro de variación; el veredicto lo pone
quien lo lea.

**Dónde se archiva y por qué ahí.** Los informes van a
`~/.claude/gbu-informes/<proyecto>/<version>.json`, con su markdown al
lado, fuera de todo repositorio a propósito: hablan de proyectos que
pueden ser privados —rutas, nombres de fichero, comandos ejecutados— y no
deben acabar versionados en un repositorio público. Un informe nunca pisa
a otro: si ya hay uno de esa versión, el nuevo se guarda al lado y se
avisa.

Este módulo solo cablea; el trabajo lo hacen los otros. Lo suyo es que los
errores previsibles salgan como un mensaje entendible y no como una traza.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from comparador import a_markdown as comparacion_a_markdown
from comparador import comparar
from eventos import cargar_conversacion, parsear_instante
from informe import a_json, a_markdown, analizar_sesion, componer
from localizador import localizar_sesiones
from metricas_coste import SHERIFF, Participante, coste
from pagina import generar as generar_pagina
from seleccion import (
    clasificar,
    fecha_de_commit,
    resolver_ventana,
    seleccionar,
    version_instalada,
)

ARCHIVO_POR_DEFECTO = Path.home() / ".claude" / "gbu-informes"

# Cuántos hallazgos se resumen por pantalla. El informe entero está
# archivado; volcarlo en la conversación costaría lo que se está midiendo.
_HALLAZGOS_EN_PANTALLA = 10


class ErrorDeUso(Exception):
    """Un fallo que se le cuenta al usuario, no se le vuelca como traza."""


def main(argv=None, salida=None, ejecutar=None):
    """Punto de entrada. Devuelve el código de salida del proceso.

    `ejecutar` es la costura por la que entran `claude` y `git`. Existe
    para que las pruebas no dependan de que estén instalados ni paguen su
    arranque: una suite que invoca procesos externos deja de ser rápida y
    empieza a fallar por motivos que no son el código.
    """
    salida = salida or sys.stdout
    try:
        argumentos = _parsear(argv if argv is not None else sys.argv[1:])
        if argumentos.comparar is not None:
            _modo_comparar(argumentos, salida)
        else:
            _modo_informe(argumentos, salida, ejecutar)
    except ErrorDeUso as error:
        print(f"Error: {error}", file=salida)
        return 1
    return 0


def _parsear(argv):
    analizador = argparse.ArgumentParser(
        prog="session_report",
        description="Analiza las sesiones de gbu de un proyecto y compara informes.",
    )
    analizador.add_argument("proyecto", nargs="?", help="ruta del proyecto a analizar")
    analizador.add_argument("--desde", help="fecha ISO o commit desde el que contar")
    analizador.add_argument("--hasta", help="fecha ISO hasta la que contar")
    analizador.add_argument("--version", help="analiza solo las sesiones de esta versión")
    analizador.add_argument("--salida", help="directorio donde archivar en vez del habitual")
    analizador.add_argument(
        "--comparar",
        nargs="*",
        metavar=("PROYECTO", "BASE NUEVA"),
        help="compara dos informes archivados de un proyecto",
    )
    analizador.add_argument(
        "--html", action="store_true", help="escribe además la página HTML"
    )
    analizador.add_argument("--archivo", help="raíz del archivo de informes")
    analizador.add_argument("--transcripts", help="raíz de los transcripts de Claude Code")
    argumentos = analizador.parse_args(argv)
    if argumentos.comparar is not None and argumentos.proyecto:
        raise ErrorDeUso(
            "--comparar y la ruta de proyecto no se usan a la vez: "
            "el modo comparación recibe el proyecto dentro de --comparar."
        )
    if argumentos.comparar is None and not argumentos.proyecto:
        raise ErrorDeUso("hace falta la ruta de un proyecto, o --comparar.")
    return argumentos


def _modo_informe(argumentos, salida, ejecutar=None):
    proyecto = Path(argumentos.proyecto)
    sesiones = _localizar(proyecto, argumentos.transcripts)
    instalada = version_instalada(proyecto, ejecutar)
    desde, hasta = _ventana(proyecto, argumentos, ejecutar)

    clasificadas = [
        clasificar(sesion, cargar_conversacion(sesion.fichero), instalada=instalada)
        for sesion in sesiones
    ]
    seleccion = seleccionar(clasificadas, desde=desde, hasta=hasta, version=argumentos.version)
    if not seleccion.incluidas:
        raise ErrorDeUso(
            f"ninguna de las {len(sesiones)} sesiones de {proyecto} entra en la ventana pedida."
        )

    analisis = []
    hallazgos = []
    for clasificada in seleccion.incluidas:
        analizada, encontrados = analizar_sesion(
            clasificada, _participantes(clasificada.sesion)
        )
        analisis.append(analizada)
        hallazgos.extend(encontrados)

    informe = componer(
        proyecto=proyecto,
        seleccion=seleccion,
        analisis=analisis,
        hallazgos=hallazgos,
        generado_en=_ahora(),
        ventana={"desde": _texto(desde), "hasta": _texto(hasta)},
    )
    destino = _archivar(informe, proyecto, argumentos, salida)
    if argumentos.html:
        pagina = destino.with_suffix(".html")
        pagina.write_text(generar_pagina(json.loads(a_json(informe))), encoding="utf-8")
        print(f"Página HTML en {pagina}", file=salida)
    _resumir(informe, destino, salida)


def _modo_comparar(argumentos, salida):
    if not argumentos.comparar:
        raise ErrorDeUso("--comparar necesita al menos el nombre del proyecto.")
    nombre = argumentos.comparar[0]
    peticiones = argumentos.comparar[1:]
    if len(peticiones) not in (0, 2):
        raise ErrorDeUso(
            "--comparar acepta el proyecto solo, o el proyecto y dos versiones "
            "(o dos ficheros)."
        )

    directorio = _raiz_archivo(argumentos) / _nombre_de_proyecto(nombre)
    if peticiones:
        base = _resolver_informe(peticiones[0], directorio)
        nueva = _resolver_informe(peticiones[1], directorio)
    else:
        base, nueva = _dos_mas_recientes(directorio)

    referencia = _leer_json(base)
    reciente = _leer_json(nueva)
    comparacion = comparar(referencia, reciente)
    print(f"Base:  {base}", file=salida)
    print(f"Nueva: {nueva}", file=salida)
    if argumentos.html:
        # La página va junto al informe nuevo, que es el que describe.
        pagina = nueva.with_name(f"{nueva.stem}-vs-{base.stem}.html")
        pagina.write_text(
            generar_pagina(reciente, comparacion=comparacion, referencia=referencia),
            encoding="utf-8",
        )
        print(f"Página HTML en {pagina}", file=salida)
    print(file=salida)
    print(comparacion_a_markdown(comparacion), file=salida)


def _localizar(proyecto, transcripts):
    try:
        sesiones = localizar_sesiones(proyecto, transcripts)
    except FileNotFoundError:
        raise ErrorDeUso(
            f"{proyecto} no tiene sesiones grabadas de Claude Code. "
            "¿Es la ruta correcta del proyecto?"
        )
    if not sesiones:
        raise ErrorDeUso(f"{proyecto} tiene el directorio de transcripts vacío.")
    return sesiones


def _ventana(proyecto, argumentos, ejecutar=None):
    desde = argumentos.desde
    if not desde:
        return resolver_ventana(hasta=argumentos.hasta)
    # Una fecha se reconoce sola; lo que no lo sea se prueba como commit del
    # repositorio del proyecto, que es la otra forma natural de decir "desde
    # que el patrón entró aquí". El orden importa: si se probara al revés,
    # un commit ilegible pasaría por "sin límite inferior" y el informe
    # incluiría en silencio sesiones anteriores al patrón.
    if parsear_instante(desde) is not None:
        return resolver_ventana(desde=desde, hasta=argumentos.hasta)
    if fecha_de_commit(proyecto, desde, ejecutar) is None:
        raise ErrorDeUso(
            f"«{desde}» no es una fecha ISO ni un commit de {proyecto}."
        )
    return resolver_ventana(
        ruta_repositorio=proyecto, commit=desde, hasta=argumentos.hasta, ejecutar=ejecutar
    )


def _participantes(sesion):
    participantes = [Participante(SHERIFF, cargar_conversacion(sesion.fichero))]
    for subagente in sesion.subagentes:
        participantes.append(
            Participante(
                rol=_rol(subagente.tipo_agente),
                conversacion=cargar_conversacion(subagente.fichero),
                modelo=subagente.modelo,
            )
        )
    return participantes


def _rol(tipo_agente):
    # `gbu:malo` y `malo` son el mismo rol: el prefijo solo dice que el
    # patrón está instalado como plugin.
    return (tipo_agente or "desconocido").split(":")[-1]


def _archivar(informe, proyecto, argumentos, salida):
    directorio = (
        Path(argumentos.salida)
        if argumentos.salida
        else _raiz_archivo(argumentos) / _nombre_de_proyecto(proyecto)
    )
    directorio.mkdir(parents=True, exist_ok=True)

    version = _version_dominante(informe)
    destino = _hueco_libre(directorio, version, salida)
    destino.write_text(a_json(informe), encoding="utf-8")
    destino.with_suffix(".md").write_text(a_markdown(informe), encoding="utf-8")
    return destino


def _hueco_libre(directorio, version, salida):
    """Busca un nombre libre para no pisar un informe anterior."""
    candidato = directorio / f"{version}.json"
    if not candidato.exists():
        return candidato
    numero = 2
    while (directorio / f"{version}-{numero}.json").exists():
        numero += 1
    candidato = directorio / f"{version}-{numero}.json"
    print(
        f"Aviso: ya había un informe de la versión {version}; el anterior se conserva "
        f"y este se archiva como {candidato.name}.",
        file=salida,
    )
    return candidato


def _version_dominante(informe):
    if not informe.versiones:
        return "sin-version"
    return max(sorted(informe.versiones), key=lambda v: informe.versiones[v])


def _resumir(informe, destino, salida):
    print(f"Informe archivado en {destino}", file=salida)
    print(f"           markdown en {destino.with_suffix('.md')}", file=salida)
    print(file=salida)
    for aviso in informe.avisos:
        print(f"⚠ {aviso}", file=salida)
    print(file=salida)
    print(
        f"{len(informe.sesiones)} sesiones, {informe.total.turnos} turnos, "
        f"{coste(informe.total, informe.pesos):,.0f} unidades de coste normalizado.",
        file=salida,
    )
    for rol, agregado in informe.coste_por_rol.items():
        print(
            f"  {rol:10} {agregado.turnos:5} turnos  {coste(agregado, informe.pesos):14,.0f}",
            file=salida,
        )
    print(file=salida)
    print(f"{len(informe.hallazgos)} hallazgos. Los más caros:", file=salida)
    for hallazgo in informe.hallazgos[:_HALLAZGOS_EN_PANTALLA]:
        print(
            f"  [{hallazgo.severidad:5}] {hallazgo.tokens:12,}  {hallazgo.titulo}",
            file=salida,
        )


def _resolver_informe(peticion, directorio):
    """Acepta una ruta de fichero o un nombre de versión archivada."""
    ruta = Path(peticion)
    if ruta.suffix == ".json" and ruta.exists():
        return ruta
    candidatos = sorted(
        directorio.glob(f"{peticion}.json"), key=lambda p: p.stat().st_mtime
    ) + sorted(directorio.glob(f"{peticion}-*.json"), key=lambda p: p.stat().st_mtime)
    if not candidatos:
        raise ErrorDeUso(
            f"no hay ningún informe archivado de la versión {peticion}. "
            f"Archivadas: {_versiones_archivadas(directorio)}."
        )
    return candidatos[-1]


def _dos_mas_recientes(directorio):
    informes = _informes_de(directorio)
    if len(informes) < 2:
        raise ErrorDeUso(
            f"hacen falta dos informes archivados para comparar, y en {directorio} "
            f"hay {len(informes)}. Genera uno con el modo informe."
        )
    return informes[-2], informes[-1]


def _informes_de(directorio):
    if not directorio.is_dir():
        raise ErrorDeUso(
            f"no hay informes archivados en {directorio}. Genera uno con el modo informe."
        )
    return sorted(directorio.glob("*.json"), key=lambda p: p.stat().st_mtime)


def _versiones_archivadas(directorio):
    nombres = [p.stem for p in _informes_de(directorio)]
    return ", ".join(nombres) if nombres else "ninguna"


def _leer_json(ruta):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError) as error:
        raise ErrorDeUso(f"no se pudo leer el informe {ruta}: {error}")


def _raiz_archivo(argumentos):
    return Path(argumentos.archivo) if argumentos.archivo else ARCHIVO_POR_DEFECTO


def _nombre_de_proyecto(proyecto):
    nombre = Path(proyecto).name or str(proyecto)
    return nombre.replace(":", "").strip() or "proyecto"


def _texto(instante):
    return instante.isoformat() if instante is not None else None


def _ahora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    sys.exit(main())
