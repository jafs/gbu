"""Localiza las sesiones de Claude Code grabadas para un proyecto.

Claude Code guarda cada sesión como un JSONL en
`~/.claude/projects/<ruta-codificada>/<id-de-sesion>.jsonl`, y los
subagentes que esa sesión lanzó en un directorio hermano
`<id-de-sesion>/subagents/agent-<id>.jsonl`, cada uno con un
`.meta.json` al lado que declara de qué tipo de agente se trata.

Este módulo solo enumera: traduce la ruta del proyecto a su directorio de
transcripts y describe lo que hay dentro. De los eventos no lee nada más
que los `timestamp`, que son lo único necesario para situar la sesión en
el tiempo.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Claude Code codifica la ruta del proyecto sustituyendo por un guion todo
# carácter que no sea alfanumérico, incluidos el separador, los dos puntos
# de la unidad, los puntos y los guiones bajos. La codificación es lo
# bastante destructiva como para que dos rutas distintas puedan colisionar;
# se asume que no ocurre, porque es la propia convención de Claude Code y no
# hay forma de deshacerla.
_NO_ALFANUMERICO = re.compile(r"[^a-zA-Z0-9]")

_RAIZ_POR_DEFECTO = Path.home() / ".claude" / "projects"

_PREFIJO_SUBAGENTE = "agent-"


@dataclass(frozen=True)
class Subagente:
    """Un subagente lanzado desde una sesión."""

    identificador: str
    tipo_agente: str | None
    fichero: Path
    tamano: int


@dataclass(frozen=True)
class Sesion:
    """Una sesión de Claude Code y los subagentes que lanzó."""

    identificador: str
    fichero: Path
    tamano: int
    inicio: datetime | None
    fin: datetime | None
    subagentes: tuple[Subagente, ...] = field(default_factory=tuple)

    @property
    def tamano_total(self):
        """Bytes de la sesión más los de todos sus subagentes."""
        return self.tamano + sum(s.tamano for s in self.subagentes)


def codificar_ruta(ruta):
    """Traduce una ruta de proyecto al nombre de su directorio de transcripts.

    La ruta se normaliza a absoluta antes de codificar, porque Claude Code
    guarda siempre el directorio de trabajo absoluto.
    """
    absoluta = str(Path(ruta).expanduser().resolve())
    return _NO_ALFANUMERICO.sub("-", absoluta)


def directorio_de_transcripts(ruta_proyecto, raiz=None):
    """Devuelve el directorio donde viven los transcripts de un proyecto.

    No comprueba que exista: eso lo decide quien lo use.
    """
    base = Path(raiz) if raiz is not None else _RAIZ_POR_DEFECTO
    return base / codificar_ruta(ruta_proyecto)


def localizar_sesiones(ruta_proyecto, raiz=None):
    """Enumera las sesiones grabadas para un proyecto, de la más antigua a la más reciente.

    Lanza FileNotFoundError si el proyecto no tiene directorio de
    transcripts, que es distinto de tenerlo vacío: lo primero suele ser una
    ruta mal escrita y conviene que se note.
    """
    directorio = directorio_de_transcripts(ruta_proyecto, raiz)
    if not directorio.is_dir():
        raise FileNotFoundError(
            f"el proyecto no tiene sesiones grabadas en {directorio}"
        )

    sesiones = [
        _describir_sesion(fichero) for fichero in sorted(directorio.glob("*.jsonl"))
    ]
    # Las sesiones sin ningún timestamp legible van al final: no se pueden
    # ordenar en el tiempo y estorban menos ahí que encabezando la lista.
    # Se ordena por el instante convertido a epoch y no por el datetime para
    # no comparar nunca uno con zona horaria contra uno sin ella, que en
    # Python lanza TypeError.
    return sorted(
        sesiones,
        key=lambda s: (
            s.inicio is None,
            s.inicio.timestamp() if s.inicio else 0.0,
            s.identificador,
        ),
    )


def _describir_sesion(fichero):
    inicio, fin = _extremos_temporales(fichero)
    return Sesion(
        identificador=fichero.stem,
        fichero=fichero,
        tamano=fichero.stat().st_size,
        inicio=inicio,
        fin=fin,
        subagentes=_localizar_subagentes(fichero.with_suffix("")),
    )


def _localizar_subagentes(directorio_sesion):
    subagentes = directorio_sesion / "subagents"
    if not subagentes.is_dir():
        return ()
    return tuple(
        _describir_subagente(fichero) for fichero in sorted(subagentes.glob("*.jsonl"))
    )


def _describir_subagente(fichero):
    identificador = fichero.stem
    if identificador.startswith(_PREFIJO_SUBAGENTE):
        identificador = identificador[len(_PREFIJO_SUBAGENTE):]
    return Subagente(
        identificador=identificador,
        tipo_agente=_tipo_de_agente(fichero.with_suffix(".meta.json")),
        fichero=fichero,
        tamano=fichero.stat().st_size,
    )


def _tipo_de_agente(meta):
    """Lee el `agentType` del `.meta.json` de un subagente.

    Devuelve None si el fichero no está o no se deja leer: un subagente sin
    tipo sigue siendo un subagente y su coste cuenta igual, así que no se
    descarta por esto.
    """
    try:
        datos = json.loads(meta.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return None
    tipo = datos.get("agentType") if isinstance(datos, dict) else None
    return tipo if isinstance(tipo, str) else None


def _extremos_temporales(fichero):
    """Devuelve el primer y el último `timestamp` legibles del JSONL.

    Recorre el fichero entero porque el último evento puede no llevar
    timestamp y hay que quedarse con el último que sí lo lleve. Las líneas
    corruptas o truncadas se ignoran sin más: en un transcript en curso, la
    última línea suele estar a medio escribir.
    """
    primero = None
    ultimo = None
    try:
        with fichero.open(encoding="utf-8", errors="replace") as f:
            for linea in f:
                instante = _instante_de_linea(linea)
                if instante is None:
                    continue
                if primero is None:
                    primero = instante
                ultimo = instante
    except OSError:
        return None, None
    return primero, ultimo


def _instante_de_linea(linea):
    linea = linea.strip()
    if not linea:
        return None
    try:
        evento = json.loads(linea)
    except ValueError:
        return None
    if not isinstance(evento, dict):
        return None
    return _parsear_instante(evento.get("timestamp"))


def _parsear_instante(texto):
    """Convierte un timestamp ISO 8601 en datetime.

    Los transcripts usan la `Z` de UTC, que `fromisoformat` no admite hasta
    Python 3.11; se traduce a su desplazamiento explícito.
    """
    if not isinstance(texto, str):
        return None
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(texto)
    except ValueError:
        return None
