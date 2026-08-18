"""El hallazgo: la pieza que emiten todos los detectores.

Un informe de esta herramienta no es solo un puñado de cifras. Las cifras
dicen si la cosa va a mejor; los hallazgos dicen qué tocar. Cada patrón de
derroche que se detecta se anota como un hallazgo con su categoría, su
severidad, la evidencia que lo respalda y los tokens que costó.

Lo delicado aquí es el **identificador**. Se deriva del contenido del
hallazgo —su categoría y su clave—, nunca de su posición en la lista ni
del orden en que se detectó. Es lo que permite cruzar dos informes y
distinguir un problema resuelto de uno que simplemente cambió de sitio.
Por la misma razón el título no entra en el identificador: reescribir un
título es cosa de esta herramienta, no del problema, y no debería
convertir un hallazgo persistente en uno nuevo.
"""

import hashlib
import re
from dataclasses import dataclass, field, replace

ALTA = "alta"
MEDIA = "media"
BAJA = "baja"

_ORDEN_SEVERIDAD = {ALTA: 0, MEDIA: 1, BAJA: 2}

# Longitud del resumen del identificador. Ocho caracteres hexadecimales
# bastan de sobra para los pocos cientos de hallazgos de un informe, y son
# cortos para citarlos en una conversación.
_LONGITUD_RESUMEN = 8

_ESPACIOS = re.compile(r"\s+")


@dataclass(frozen=True)
class Evidencia:
    """Dónde se observó un hallazgo."""

    sesion: str | None = None
    rol: str | None = None
    turno: int | None = None
    fragmento: str | None = None
    detalle: str | None = None


@dataclass(frozen=True)
class Hallazgo:
    """Un problema detectado, con lo que lo respalda y lo que costó."""

    categoria: str
    severidad: str
    titulo: str
    clave: str
    tokens: int = 0
    evidencias: tuple[Evidencia, ...] = field(default_factory=tuple)

    @property
    def identificador(self):
        """Identificador estable, derivado de la categoría y la clave."""
        resumen = hashlib.sha256(
            f"{self.categoria}|{normalizar_clave(self.clave)}".encode("utf-8")
        ).hexdigest()[:_LONGITUD_RESUMEN]
        return f"{self.categoria}-{resumen}"

    @property
    def orden_de_severidad(self):
        # Una severidad desconocida va al final en vez de reventar: un
        # detector nuevo mal escrito no debe tumbar el informe entero.
        return _ORDEN_SEVERIDAD.get(self.severidad, len(_ORDEN_SEVERIDAD))


def normalizar_clave(clave):
    """Normaliza una clave para que la misma cosa dé siempre lo mismo.

    Unifica los separadores de ruta porque el mismo fichero aparece en los
    transcripts escrito de las dos maneras, según lo escribiera una
    herramienta o el propio modelo, y son el mismo fichero.
    """
    if not clave:
        return ""
    texto = str(clave).replace("\\", "/").strip().lower()
    return _ESPACIOS.sub(" ", texto)


def ordenar(hallazgos):
    """De más severo a menos, y dentro de cada severidad, de más caro a menos."""
    return tuple(
        sorted(
            hallazgos,
            key=lambda h: (h.orden_de_severidad, -h.tokens, h.identificador),
        )
    )


def fusionar(hallazgos):
    """Funde los hallazgos que son el mismo problema visto en varios sitios.

    Los detectores trabajan sesión a sesión, así que el mismo problema
    aparece una vez por sesión. Al fundirlos, los tokens se suman —es lo
    que costó en total— y las evidencias se concatenan conservando el
    orden en que se observaron. La severidad que gana es la más alta: si
    en una sesión el problema fue grave, el problema es grave.
    """
    fundidos = {}
    orden = []
    for hallazgo in hallazgos:
        clave = hallazgo.identificador
        anterior = fundidos.get(clave)
        if anterior is None:
            orden.append(clave)
            fundidos[clave] = hallazgo
            continue
        severidad = (
            anterior.severidad
            if anterior.orden_de_severidad <= hallazgo.orden_de_severidad
            else hallazgo.severidad
        )
        fundidos[clave] = replace(
            anterior,
            severidad=severidad,
            tokens=anterior.tokens + hallazgo.tokens,
            evidencias=anterior.evidencias + hallazgo.evidencias,
        )
    return tuple(fundidos[clave] for clave in orden)


def agrupar(hallazgos):
    """Agrupa por categoría, con las categorías más costosas delante."""
    grupos = {}
    for hallazgo in hallazgos:
        grupos.setdefault(hallazgo.categoria, []).append(hallazgo)
    return {
        categoria: ordenar(grupos[categoria])
        for categoria in sorted(
            grupos, key=lambda c: (-sum(h.tokens for h in grupos[c]), c)
        )
    }


def tokens_totales(hallazgos):
    return sum(h.tokens for h in hallazgos)


def resumen_por_severidad(hallazgos):
    """Cuántos hallazgos hay de cada severidad, de la más alta a la más baja."""
    cuenta = {}
    for hallazgo in hallazgos:
        cuenta[hallazgo.severidad] = cuenta.get(hallazgo.severidad, 0) + 1
    return {
        severidad: cuenta[severidad]
        for severidad in sorted(
            cuenta, key=lambda s: _ORDEN_SEVERIDAD.get(s, len(_ORDEN_SEVERIDAD))
        )
    }
