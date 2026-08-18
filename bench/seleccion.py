"""Clasifica las sesiones de un proyecto y elige las que entran en el informe.

Dos preguntas por sesión: si la ejecutó el patrón, y con qué versión. La
segunda es la que hace posible comparar dos informes, y también la que
más fácil es contestar mal.

La versión se resuelve **en este orden, y el primero que responde gana**:

1. La marca `gbu vX.Y.Z` que la propia sesión dejó escrita.
2. La versión del plugin instalado hoy, preguntándole a `claude`.
3. La versión por defecto.

El orden no es negociable. La versión instalada hoy no tiene por qué ser
la que ejecutó la sesión: si el plugin se actualizó a mitad de la ventana,
etiquetar todo con la actual funde dos versiones en una y arruina
precisamente la comparación que se quería hacer. Por eso solo rellena las
sesiones sin marca, y por eso cada sesión registra por qué vía se le
atribuyó la versión. Que una ventana contenga varias versiones no se
promedia en silencio: se avisa.
"""

import re
import subprocess
from dataclasses import dataclass, field
from datetime import timezone

from eventos import parsear_instante

VERSION_POR_DEFECTO = "0.1.0"

VIA_MARCA = "marca"
VIA_INSTALADA = "instalada"
VIA_DEFECTO = "defecto"

MOTIVO_NO_GBU = "no es una sesión del patrón"
MOTIVO_FUERA_DE_VENTANA = "fuera de la ventana"
MOTIVO_OTRA_VERSION = "de otra versión del patrón"

# La marca que el patrón anuncia al arrancar.
_MARCA = re.compile(r"gbu\s+v(\d+\.\d+\.\d+)", re.IGNORECASE)

# Señal de que la conversación es la del Sheriff. Es la primera línea de su
# prompt, así que aparece literalmente en el transcript.
_SENAL_SHERIFF = "eres el sheriff"

# Tipos de subagente propios del patrón. El prefijo del plugin se ignora:
# `gbu:malo` y `malo` son el mismo rol, instalado de dos maneras.
_SUBAGENTES_DEL_PATRON = ("malo", "feo")

_SEMVER = re.compile(r"(\d+\.\d+\.\d+)")


@dataclass(frozen=True)
class SesionClasificada:
    """Una sesión con lo que se sabe de ella para decidir si entra."""

    sesion: object
    es_gbu: bool
    version: str | None = None
    via: str | None = None
    motivo: str | None = None

    @property
    def identificador(self):
        return self.sesion.identificador


@dataclass(frozen=True)
class Seleccion:
    """El resultado de filtrar las sesiones de un proyecto."""

    incluidas: tuple[SesionClasificada, ...] = field(default_factory=tuple)
    descartadas: tuple[SesionClasificada, ...] = field(default_factory=tuple)
    avisos: tuple[str, ...] = field(default_factory=tuple)

    @property
    def versiones(self):
        """Cuántas sesiones incluidas hay de cada versión."""
        cuenta = {}
        for clasificada in self.incluidas:
            cuenta[clasificada.version] = cuenta.get(clasificada.version, 0) + 1
        return dict(sorted(cuenta.items()))

    @property
    def vias(self):
        """Por qué vía se atribuyó la versión de cada sesión incluida.

        Es la diferencia entre un dato y una suposición, y por eso va en el
        informe.
        """
        cuenta = {}
        for clasificada in self.incluidas:
            cuenta[clasificada.via] = cuenta.get(clasificada.via, 0) + 1
        return dict(sorted(cuenta.items()))


def es_de_gbu(conversacion, tipos_de_subagente=()):
    """Decide si una sesión la ejecutó el patrón.

    Vale cualquiera de tres señales: que la sesión anunciara su versión,
    que aparezca el prompt del Sheriff, o que lanzara subagentes del
    patrón. Ninguna basta por sí sola en todos los casos: una sesión puede
    haber lanzado al Malo desde fuera del patrón, otra puede haber
    arrancado sin llegar a lanzar a nadie, y la marca solo existe desde la
    versión que la introdujo.
    """
    for tipo in tipos_de_subagente:
        if _rol_normalizado(tipo) in _SUBAGENTES_DEL_PATRON:
            return True
    texto = _texto_completo(conversacion)
    return bool(_MARCA.search(texto)) or _SENAL_SHERIFF in texto.lower()


def version_marcada(conversacion):
    """La versión que la propia sesión anunció, si la anunció."""
    encontrada = _MARCA.search(_texto_completo(conversacion))
    return encontrada.group(1) if encontrada else None


def version_instalada(ruta_proyecto=None, ejecutar=None):
    """Pregunta a `claude` qué versión del plugin hay instalada hoy.

    Devuelve None si `claude` no está, falla o no menciona el plugin: es un
    respaldo, no un requisito, y su ausencia no debe impedir un informe.
    """
    ejecutar = ejecutar or _ejecutar
    try:
        salida = ejecutar(["claude", "plugin", "list"], ruta_proyecto)
    except (OSError, subprocess.SubprocessError):
        return None
    return _version_de_listado(salida or "")


def resolver_version(conversacion, instalada=None, por_defecto=VERSION_POR_DEFECTO):
    """Devuelve la versión de una sesión y la vía por la que se supo."""
    marcada = version_marcada(conversacion)
    if marcada:
        return marcada, VIA_MARCA
    if instalada:
        return instalada, VIA_INSTALADA
    return por_defecto, VIA_DEFECTO


def fecha_de_commit(ruta_repositorio, commit, ejecutar=None):
    """Fecha de un commit, preguntándole a git.

    Devuelve None si el commit no existe o el directorio no es un
    repositorio; quien llame decide si eso es un error.
    """
    ejecutar = ejecutar or _ejecutar
    try:
        salida = ejecutar(
            ["git", "-C", str(ruta_repositorio), "show", "-s", "--format=%cI", str(commit)],
            None,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return parsear_instante((salida or "").strip().splitlines()[0]) if salida else None


def resolver_ventana(desde=None, hasta=None, ruta_repositorio=None, commit=None, ejecutar=None):
    """Traduce los límites pedidos a instantes.

    El commit y la fecha de inicio no compiten: si se dan los dos, manda el
    commit, porque es la forma precisa de decir "desde que el patrón entró
    en este proyecto".
    """
    if commit:
        instante = fecha_de_commit(ruta_repositorio, commit, ejecutar)
        if instante is None:
            raise ValueError(f"no se pudo resolver el commit {commit}")
        return instante, parsear_instante(hasta) if hasta else None
    return (
        parsear_instante(desde) if desde else None,
        parsear_instante(hasta) if hasta else None,
    )


def clasificar(sesion, conversacion, instalada=None, por_defecto=VERSION_POR_DEFECTO):
    """Clasifica una sesión sin decidir todavía si entra en la ventana."""
    tipos = [s.tipo_agente for s in getattr(sesion, "subagentes", ()) if s.tipo_agente]
    if not es_de_gbu(conversacion, tipos):
        return SesionClasificada(sesion=sesion, es_gbu=False, motivo=MOTIVO_NO_GBU)
    version, via = resolver_version(conversacion, instalada, por_defecto)
    return SesionClasificada(sesion=sesion, es_gbu=True, version=version, via=via)


def seleccionar(clasificadas, desde=None, hasta=None, version=None):
    """Reparte las sesiones clasificadas entre incluidas y descartadas."""
    incluidas = []
    descartadas = []
    for clasificada in clasificadas:
        motivo = _motivo_de_descarte(clasificada, desde, hasta, version)
        if motivo is None:
            incluidas.append(clasificada)
        else:
            descartadas.append(
                clasificada
                if clasificada.motivo
                else SesionClasificada(
                    sesion=clasificada.sesion,
                    es_gbu=clasificada.es_gbu,
                    version=clasificada.version,
                    via=clasificada.via,
                    motivo=motivo,
                )
            )
    seleccion = Seleccion(
        incluidas=tuple(incluidas), descartadas=tuple(descartadas)
    )
    return Seleccion(
        incluidas=seleccion.incluidas,
        descartadas=seleccion.descartadas,
        avisos=_avisos(seleccion),
    )


def _avisos(seleccion):
    avisos = []
    versiones = seleccion.versiones
    if len(versiones) > 1:
        detalle = ", ".join(f"{v} ({n} sesiones)" for v, n in versiones.items())
        avisos.append(
            "La ventana mezcla varias versiones del patrón: "
            f"{detalle}. Las cifras agregadas no describen ninguna de ellas."
        )
    vias = seleccion.vias
    supuestas = vias.get(VIA_INSTALADA, 0) + vias.get(VIA_DEFECTO, 0)
    if supuestas:
        avisos.append(
            f"{supuestas} de {len(seleccion.incluidas)} sesiones no llevaban marca de "
            "versión: la suya está supuesta, no leída."
        )
    return tuple(avisos)


def _motivo_de_descarte(clasificada, desde, hasta, version):
    if clasificada.motivo:
        return clasificada.motivo
    if not clasificada.es_gbu:
        return MOTIVO_NO_GBU
    if version and clasificada.version != version:
        return MOTIVO_OTRA_VERSION
    inicio = getattr(clasificada.sesion, "inicio", None)
    if desde is not None and (inicio is None or _instante(inicio) < _instante(desde)):
        return MOTIVO_FUERA_DE_VENTANA
    if hasta is not None and (inicio is None or _instante(inicio) > _instante(hasta)):
        return MOTIVO_FUERA_DE_VENTANA
    return None


def _instante(valor):
    """Segundos desde epoch, tratando como UTC lo que no traiga zona."""
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.timestamp()


def _texto_completo(conversacion):
    return "\n".join(
        bloque.texto for turno in conversacion.turnos for bloque in turno.bloques
    )


def _version_de_listado(salida):
    """Extrae del listado de `claude plugin list` la versión del plugin gbu."""
    actual = None
    for linea in salida.splitlines():
        limpia = linea.strip().lstrip("❯>*-").strip()
        if "@" in limpia and " " not in limpia:
            actual = limpia.split("@", 1)[0].strip()
            continue
        if actual == "gbu" and limpia.lower().startswith("version"):
            encontrada = _SEMVER.search(limpia)
            if encontrada:
                return encontrada.group(1)
    return None


def _rol_normalizado(tipo):
    return (tipo or "").split(":")[-1].strip().lower()


def _ejecutar(orden, directorio):
    completado = subprocess.run(
        orden,
        cwd=directorio,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if completado.returncode != 0:
        return None
    return completado.stdout
