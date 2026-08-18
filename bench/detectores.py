"""Detectores de derroche: recorren una sesión y emiten hallazgos.

Cada detector busca un patrón concreto y estima lo que costó. La unidad
en la que estiman no son tokens sueltos sino **turn-tokens**: lo que costó
el bloque por quedarse en el contexto y releerse en cada turno posterior.
Contar solo los tokens del bloque diría que releer un fichero al principio
de la conversación cuesta lo mismo que releerlo al final, y no es verdad.

Los umbrales son parámetros, no constantes escondidas: lo que es mucho
depende del proyecto, y un umbral mal puesto convierte un informe en
ruido. Los valores por defecto salen de sesiones reales del patrón.

Un detector nunca decide qué hacer, solo señala. La lectura de si un
hallazgo merece un cambio en los prompts la hace quien lea el informe.
"""

from dataclasses import dataclass

from eventos import (
    ADJUNTO,
    RESULTADO_HERRAMIENTA,
    USO_HERRAMIENTA,
)
from hallazgos import ALTA, BAJA, MEDIA, Evidencia, Hallazgo, normalizar_clave
from metricas_contexto import (
    bloques_con_lecturas,
    curva_de_contexto,
    prelude_estimado,
)

# Herramientas que meten el contenido de un fichero en el contexto.
_HERRAMIENTAS_DE_LECTURA = ("Read", "NotebookRead")

# Herramientas que ejecutan una orden de consola.
_HERRAMIENTAS_DE_CONSOLA = ("Bash", "PowerShell")

CATEGORIA_RELECTURA = "relectura"
CATEGORIA_LECTURA_COMPARTIDA = "lectura-compartida"
CATEGORIA_COMANDO_REPETIDO = "comando-repetido"
CATEGORIA_RESULTADO_GIGANTE = "resultado-gigante"
CATEGORIA_BLOQUE_CARO = "bloque-caro"
CATEGORIA_CONTEXTO_DESBOCADO = "contexto-desbocado"
CATEGORIA_PRELUDE_EXCESIVO = "prelude-excesivo"


@dataclass(frozen=True)
class Umbrales:
    """A partir de dónde algo deja de ser normal y pasa a ser un hallazgo."""

    # Un resultado de herramienta por encima de esto entra entero en el
    # contexto y se relee en cada turno posterior.
    resultado_grande: int = 4_000
    # Turn-tokens de un solo bloque. Un bloque que supera esto pesa más que
    # muchas conversaciones enteras.
    bloque_caro: int = 250_000
    # Contexto de un turno. Por encima, la conversación debería haberse
    # cortado.
    contexto_maximo: int = 150_000
    # Prelude fijo de un rol. Se paga en cada turno, así que un prelude
    # grande multiplica por la longitud de la conversación.
    prelude_maximo: int = 40_000
    # Veces que hay que ver lo mismo para que cuente como repetición.
    repeticiones_minimas: int = 2


UMBRALES_POR_DEFECTO = Umbrales()


@dataclass(frozen=True)
class Vista:
    """Lo que un detector necesita de un participante de la sesión."""

    sesion: str
    rol: str
    conversacion: object

    def bloques(self):
        return bloques_con_lecturas(self.conversacion)


def detectar(vistas, umbrales=None):
    """Lanza todos los detectores sobre una sesión y devuelve sus hallazgos."""
    umbrales = umbrales or UMBRALES_POR_DEFECTO
    vistas = tuple(vistas)
    encontrados = []
    for detector in (
        ficheros_releidos,
        comandos_repetidos,
        resultados_gigantes,
        bloques_caros,
        contextos_desbocados,
        preludes_excesivos,
    ):
        for vista in vistas:
            encontrados.extend(detector(vista, umbrales))
    encontrados.extend(ficheros_compartidos(vistas, umbrales))
    return tuple(encontrados)


def ficheros_releidos(vista, umbrales=None):
    """Ficheros que el mismo rol se trajo al contexto más de una vez.

    Cuenta también los adjuntos, porque un fichero editado que Claude Code
    reinyecta ocupa igual que uno leído a mano.
    """
    umbrales = umbrales or UMBRALES_POR_DEFECTO
    encontrados = []
    for ruta, lecturas in _lecturas_por_fichero(vista).items():
        if len(lecturas) < umbrales.repeticiones_minimas:
            continue
        # La primera lectura era necesaria; lo que sobra son las demás.
        desperdicio = sum(b.turn_tokens for b in lecturas[1:])
        encontrados.append(
            Hallazgo(
                categoria=CATEGORIA_RELECTURA,
                severidad=_severidad(desperdicio, umbrales.bloque_caro),
                titulo=f"{vista.rol} trajo {_nombre_corto(ruta)} al contexto {len(lecturas)} veces",
                clave=f"{vista.rol}|{ruta}",
                tokens=desperdicio,
                evidencias=tuple(
                    Evidencia(
                        sesion=vista.sesion,
                        rol=vista.rol,
                        turno=bloque.turno,
                        fragmento=ruta,
                        detalle=f"{bloque.tokens} tokens releídos {bloque.lecturas} veces",
                    )
                    for bloque in lecturas
                ),
            )
        )
    return tuple(encontrados)


def ficheros_compartidos(vistas, umbrales=None):
    """Ficheros que varios roles de la misma sesión se trajeron por su cuenta.

    No es un error: el Malo y el Feo arrancan sin contexto a propósito. Es
    una medida de lo que cuesta ese aislamiento, para poder decidir si sale
    a cuenta pasarles un extracto en vez de dejar que lean el fichero
    entero.
    """
    umbrales = umbrales or UMBRALES_POR_DEFECTO
    por_fichero = {}
    for vista in vistas:
        for ruta, lecturas in _lecturas_por_fichero(vista).items():
            por_fichero.setdefault(ruta, {}).setdefault(vista.rol, []).extend(lecturas)

    encontrados = []
    for ruta, por_rol in por_fichero.items():
        if len(por_rol) < umbrales.repeticiones_minimas:
            continue
        bloques = [b for lecturas in por_rol.values() for b in lecturas]
        # Alguien tenía que leerlo: se descuenta la lectura más barata.
        desperdicio = sum(b.turn_tokens for b in bloques) - min(
            b.turn_tokens for b in bloques
        )
        sesion = vistas[0].sesion if vistas else None
        encontrados.append(
            Hallazgo(
                categoria=CATEGORIA_LECTURA_COMPARTIDA,
                severidad=_severidad(desperdicio, umbrales.bloque_caro),
                titulo=(
                    f"{_nombre_corto(ruta)} lo leyeron {len(por_rol)} roles por separado"
                ),
                clave=ruta,
                tokens=desperdicio,
                evidencias=tuple(
                    Evidencia(
                        sesion=sesion,
                        rol=rol,
                        turno=lecturas[0].turno,
                        fragmento=ruta,
                        detalle=f"{len(lecturas)} lecturas",
                    )
                    for rol, lecturas in por_rol.items()
                ),
            )
        )
    return tuple(encontrados)


def comandos_repetidos(vista, umbrales=None):
    """Órdenes de consola ejecutadas literalmente igual más de una vez."""
    umbrales = umbrales or UMBRALES_POR_DEFECTO
    por_comando = {}
    for bloque in vista.bloques():
        if bloque.clase != USO_HERRAMIENTA or bloque.nombre not in _HERRAMIENTAS_DE_CONSOLA:
            continue
        if not bloque.identificacion:
            continue
        por_comando.setdefault(normalizar_clave(bloque.identificacion), []).append(bloque)

    resultados = _resultados_por_identificador(vista)
    encontrados = []
    for comando, bloques in por_comando.items():
        if len(bloques) < umbrales.repeticiones_minimas:
            continue
        desperdicio = sum(
            b.turn_tokens + resultados.get(b.identificador, 0) for b in bloques[1:]
        )
        encontrados.append(
            Hallazgo(
                categoria=CATEGORIA_COMANDO_REPETIDO,
                severidad=_severidad(desperdicio, umbrales.bloque_caro),
                titulo=f"{vista.rol} repitió {len(bloques)} veces `{_recortar(comando)}`",
                clave=f"{vista.rol}|{comando}",
                tokens=desperdicio,
                evidencias=tuple(
                    Evidencia(
                        sesion=vista.sesion,
                        rol=vista.rol,
                        turno=bloque.turno,
                        fragmento=_recortar(comando),
                    )
                    for bloque in bloques
                ),
            )
        )
    return tuple(encontrados)


def resultados_gigantes(vista, umbrales=None):
    """Resultados de herramienta tan grandes que ensucian el contexto solos."""
    umbrales = umbrales or UMBRALES_POR_DEFECTO
    llamadas = _llamadas_por_identificador(vista)
    encontrados = []
    for bloque in vista.bloques():
        if bloque.clase != RESULTADO_HERRAMIENTA or bloque.tokens < umbrales.resultado_grande:
            continue
        origen = llamadas.get(bloque.identificador)
        fragmento = (origen.identificacion if origen else None) or (
            origen.nombre if origen else "resultado"
        )
        encontrados.append(
            Hallazgo(
                categoria=CATEGORIA_RESULTADO_GIGANTE,
                severidad=_severidad(bloque.turn_tokens, umbrales.bloque_caro),
                titulo=f"Resultado de {bloque.tokens} tokens en {vista.rol}",
                clave=f"{vista.rol}|{fragmento}",
                tokens=bloque.turn_tokens,
                evidencias=(
                    Evidencia(
                        sesion=vista.sesion,
                        rol=vista.rol,
                        turno=bloque.turno,
                        fragmento=_recortar(str(fragmento)),
                        detalle=f"{bloque.tokens} tokens releídos {bloque.lecturas} veces",
                    ),
                ),
            )
        )
    return tuple(encontrados)


def bloques_caros(vista, umbrales=None):
    """Bloques cuya permanencia en el contexto supera el umbral."""
    umbrales = umbrales or UMBRALES_POR_DEFECTO
    encontrados = []
    for bloque in vista.bloques():
        if bloque.turn_tokens < umbrales.bloque_caro:
            continue
        fragmento = bloque.identificacion or bloque.resumen or bloque.nombre or bloque.clase
        encontrados.append(
            Hallazgo(
                categoria=CATEGORIA_BLOQUE_CARO,
                severidad=_severidad(bloque.turn_tokens, umbrales.bloque_caro * 4),
                titulo=(
                    f"{_recortar(str(fragmento))} costó {bloque.turn_tokens} turn-tokens en {vista.rol}"
                ),
                clave=f"{vista.rol}|{bloque.clase}|{fragmento}",
                tokens=bloque.turn_tokens,
                evidencias=(
                    Evidencia(
                        sesion=vista.sesion,
                        rol=vista.rol,
                        turno=bloque.turno,
                        fragmento=_recortar(str(fragmento)),
                        detalle=f"{bloque.tokens} tokens releídos {bloque.lecturas} veces",
                    ),
                ),
            )
        )
    return tuple(encontrados)


def contextos_desbocados(vista, umbrales=None):
    """Conversaciones que pasaron del umbral de contexto sin cortarse.

    Lo que se estima como desperdicio es lo que se pagó **por encima** de
    la línea, turno a turno: es lo que se habría ahorrado cortando ahí.
    """
    umbrales = umbrales or UMBRALES_POR_DEFECTO
    curva = curva_de_contexto(vista.conversacion)
    exceso = sum(max(0, p.contexto - umbrales.contexto_maximo) for p in curva.puntos)
    if not exceso:
        return ()
    turnos_por_encima = sum(1 for p in curva.puntos if p.contexto > umbrales.contexto_maximo)
    return (
        Hallazgo(
            categoria=CATEGORIA_CONTEXTO_DESBOCADO,
            severidad=_severidad(exceso, umbrales.contexto_maximo * 10),
            titulo=(
                f"{vista.rol} llegó a {curva.maximo} tokens de contexto en {len(curva.puntos)} turnos"
            ),
            clave=f"{vista.sesion}|{vista.rol}",
            tokens=exceso,
            evidencias=(
                Evidencia(
                    sesion=vista.sesion,
                    rol=vista.rol,
                    turno=curva.puntos[-1].turno,
                    fragmento=f"máximo {curva.maximo}",
                    detalle=f"{turnos_por_encima} turnos por encima del umbral",
                ),
            ),
        ),
    )


def preludes_excesivos(vista, umbrales=None):
    """Contexto fijo por encima de lo esperable para el rol.

    El prelude no aparece en el transcript pero se paga en cada turno, así
    que su coste es el exceso multiplicado por la longitud de la
    conversación.
    """
    umbrales = umbrales or UMBRALES_POR_DEFECTO
    prelude = prelude_estimado(vista.conversacion)
    if prelude <= umbrales.prelude_maximo:
        return ()
    turnos = len(curva_de_contexto(vista.conversacion).puntos)
    desperdicio = (prelude - umbrales.prelude_maximo) * turnos
    return (
        Hallazgo(
            categoria=CATEGORIA_PRELUDE_EXCESIVO,
            severidad=_severidad(desperdicio, umbrales.bloque_caro),
            titulo=f"{vista.rol} arrastra un contexto fijo de {prelude} tokens",
            clave=f"{vista.rol}",
            tokens=desperdicio,
            evidencias=(
                Evidencia(
                    sesion=vista.sesion,
                    rol=vista.rol,
                    turno=0,
                    fragmento=f"prelude {prelude}",
                    detalle=f"pagado en {turnos} turnos",
                ),
            ),
        ),
    )


def _lecturas_por_fichero(vista):
    """Bloques que metieron un fichero en el contexto, agrupados por ruta.

    El bloque que se cuenta es el resultado, no la llamada: lo que ocupa es
    el contenido del fichero, no la orden de leerlo.
    """
    llamadas = _llamadas_por_identificador(vista)
    por_fichero = {}
    for bloque in vista.bloques():
        ruta = None
        if bloque.clase == RESULTADO_HERRAMIENTA:
            origen = llamadas.get(bloque.identificador)
            if origen and origen.nombre in _HERRAMIENTAS_DE_LECTURA:
                ruta = origen.identificacion
        elif bloque.clase == ADJUNTO and bloque.identificacion:
            ruta = bloque.identificacion
        if ruta:
            por_fichero.setdefault(normalizar_clave(ruta), []).append(bloque)
    return por_fichero


def _llamadas_por_identificador(vista):
    return {
        b.identificador: b
        for b in vista.bloques()
        if b.clase == USO_HERRAMIENTA and b.identificador
    }


def _resultados_por_identificador(vista):
    return {
        b.identificador: b.turn_tokens
        for b in vista.bloques()
        if b.clase == RESULTADO_HERRAMIENTA and b.identificador
    }


def _severidad(tokens, referencia):
    """Gradúa la severidad por lo que costó, en relación a una referencia."""
    if tokens >= referencia:
        return ALTA
    if tokens >= referencia / 4:
        return MEDIA
    return BAJA


def _nombre_corto(ruta):
    return ruta.rsplit("/", 1)[-1] or ruta


def _recortar(texto, limite=60):
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"
