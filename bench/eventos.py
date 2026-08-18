"""Lee un transcript JSONL y lo normaliza a una conversación.

Un transcript es una línea JSON por evento, en orden cronológico. Este
módulo lo convierte en una secuencia de turnos, cada uno con sus bloques
—texto, pensamiento, llamadas a herramienta y sus resultados— y, en los
turnos de asistente, con el `usage` que declara lo que costó.

Aquí no se calcula ninguna métrica: solo se ordena el material para que
las capas de arriba lo hagan. Lo único que se estima es el tamaño en
tokens de cada bloque, y se hace con la aproximación grosera de dividir
los caracteres entre cuatro; sirve para repartir un contexto entre sus
bloques, nunca para sustituir a un `usage` real.
"""

import json
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

# Clases de bloque. El adjunto no es un bloque de mensaje: Claude Code
# emite los adjuntos como eventos propios, pero ocupan contexto igual que
# los demás y se modelan como un bloque para poder medirlos con la misma
# vara.
TEXTO = "texto"
PENSAMIENTO = "pensamiento"
USO_HERRAMIENTA = "uso_herramienta"
RESULTADO_HERRAMIENTA = "resultado_herramienta"
ADJUNTO = "adjunto"

# Papeles de un turno.
ASISTENTE = "asistente"
USUARIO = "usuario"
SISTEMA = "sistema"

_CARACTERES_POR_TOKEN = 4


def tokens_estimados(texto):
    """Aproxima los tokens de un texto por su longitud.

    Es deliberadamente burda. Solo se usa para repartir proporciones
    dentro de un contexto cuyo tamaño real ya se conoce por el `usage`.
    """
    return len(texto) // _CARACTERES_POR_TOKEN


@dataclass(frozen=True)
class Uso:
    """Lo que declara el `usage` de un turno de asistente."""

    entrada: int = 0
    creacion_cache: int = 0
    lectura_cache: int = 0
    salida: int = 0

    @property
    def contexto(self):
        """Tokens de entrada del turno, vengan de donde vengan.

        Es el tamaño del contexto que el modelo leyó para responder: lo que
        se escribió en caché, lo que se leyó de ella y lo que entró sin
        cachear.
        """
        return self.entrada + self.creacion_cache + self.lectura_cache


@dataclass(frozen=True)
class Bloque:
    """Una pieza de contenido dentro de un turno."""

    clase: str
    texto: str = ""
    nombre: str | None = None
    identificador: str | None = None
    identificacion: str | None = None
    es_error: bool = False

    @property
    def tokens(self):
        return tokens_estimados(self.texto)


@dataclass(frozen=True)
class Turno:
    """Un evento del transcript que aporta contenido a la conversación."""

    indice: int
    papel: str
    instante: datetime | None = None
    uso: Uso | None = None
    modelo: str | None = None
    identificador_mensaje: str | None = None
    bloques: tuple[Bloque, ...] = field(default_factory=tuple)

    @property
    def tokens_estimados(self):
        return sum(b.tokens for b in self.bloques)


@dataclass(frozen=True)
class Llamada:
    """Una llamada a herramienta con el resultado que produjo."""

    identificador: str
    nombre: str
    turno: int
    entrada: Bloque
    resultado: Bloque | None = None

    @property
    def tokens_resultado(self):
        return self.resultado.tokens if self.resultado else 0


@dataclass(frozen=True)
class Conversacion:
    """Un transcript ya normalizado."""

    identificador: str
    fichero: Path | None
    turnos: tuple[Turno, ...] = field(default_factory=tuple)
    llamadas: tuple[Llamada, ...] = field(default_factory=tuple)
    resultados_huerfanos: tuple[Bloque, ...] = field(default_factory=tuple)
    lineas_ilegibles: int = 0
    version_claude: str | None = None
    rama: str | None = None

    @property
    def turnos_de_asistente(self):
        return tuple(t for t in self.turnos if t.papel == ASISTENTE)

    def texto_del_asistente(self):
        """Concatena el texto visible que escribió el asistente.

        Es de donde se saca luego la marca de versión del patrón, así que
        el pensamiento no entra: no forma parte de lo que el asistente dijo.
        """
        return "\n".join(
            b.texto
            for t in self.turnos
            if t.papel == ASISTENTE
            for b in t.bloques
            if b.clase == TEXTO
        )


def cargar_conversacion(fichero, identificador=None):
    """Lee un JSONL y devuelve la conversación normalizada.

    Nunca lanza por contenido: una línea corrupta o truncada se descarta y
    se cuenta en `lineas_ilegibles`. Es lo habitual al final de un
    transcript de una sesión todavía en marcha.
    """
    ruta = Path(fichero)
    eventos, ilegibles = _leer_eventos(ruta)
    return _normalizar(
        eventos,
        identificador=identificador or ruta.stem,
        fichero=ruta,
        ilegibles=ilegibles,
    )


def conversacion_desde_eventos(eventos, identificador="memoria"):
    """Normaliza una lista de eventos ya cargados, sin tocar disco.

    Existe para que las pruebas y las capas de arriba puedan trabajar con
    conversaciones construidas en memoria.
    """
    return _normalizar(list(eventos), identificador=identificador, fichero=None)


def _leer_eventos(ruta):
    eventos = []
    ilegibles = 0
    with ruta.open(encoding="utf-8", errors="replace") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                evento = json.loads(linea)
            except ValueError:
                ilegibles += 1
                continue
            if isinstance(evento, dict):
                eventos.append(evento)
            else:
                ilegibles += 1
    return eventos, ilegibles


def _normalizar(eventos, identificador, fichero, ilegibles=0):
    turnos = []
    # Una misma respuesta del modelo se graba como varios eventos
    # `assistant`, uno por bloque de contenido, y todos repiten el mismo
    # `usage`. Se fusionan por el identificador del mensaje: si no, cada
    # respuesta con pensamiento y llamada a herramienta contaría su coste
    # dos o tres veces.
    turno_por_mensaje = {}
    llamadas = {}
    huerfanos = []
    version_claude = None
    rama = None

    for evento in eventos:
        version_claude = version_claude or _cadena(evento.get("version"))
        rama = rama or _cadena(evento.get("gitBranch"))

        turno = _turno_de_evento(evento, len(turnos))
        if turno is None:
            continue

        bloques_nuevos = turno.bloques
        anterior = turno_por_mensaje.get(turno.identificador_mensaje)
        if turno.papel == ASISTENTE and anterior is not None:
            turnos[anterior] = replace(
                turnos[anterior], bloques=turnos[anterior].bloques + bloques_nuevos
            )
            indice = turnos[anterior].indice
        else:
            if turno.papel == ASISTENTE and turno.identificador_mensaje:
                turno_por_mensaje[turno.identificador_mensaje] = len(turnos)
            indice = turno.indice
            turnos.append(turno)

        # Solo se recorren los bloques que aporta este evento: al fusionar,
        # volver sobre los ya vistos desharía el emparejamiento hecho antes.
        for bloque in bloques_nuevos:
            if bloque.clase == USO_HERRAMIENTA and bloque.identificador:
                llamadas[bloque.identificador] = Llamada(
                    identificador=bloque.identificador,
                    nombre=bloque.nombre or "",
                    turno=indice,
                    entrada=bloque,
                )
            elif bloque.clase == RESULTADO_HERRAMIENTA:
                llamada = llamadas.get(bloque.identificador)
                # Un resultado sin llamada no se descarta: ocupa contexto
                # igual, y que aparezca suele significar que la sesión
                # continúa otra anterior.
                if llamada is None:
                    huerfanos.append(bloque)
                else:
                    llamadas[bloque.identificador] = Llamada(
                        identificador=llamada.identificador,
                        nombre=llamada.nombre,
                        turno=llamada.turno,
                        entrada=llamada.entrada,
                        resultado=bloque,
                    )

    return Conversacion(
        identificador=identificador,
        fichero=fichero,
        turnos=tuple(turnos),
        llamadas=tuple(llamadas.values()),
        resultados_huerfanos=tuple(huerfanos),
        lineas_ilegibles=ilegibles,
        version_claude=version_claude,
        rama=rama,
    )


def _turno_de_evento(evento, indice):
    tipo = evento.get("type")
    instante = parsear_instante(evento.get("timestamp"))

    if tipo == "attachment":
        bloque = _bloque_de_adjunto(evento.get("attachment"))
        if bloque is None:
            return None
        return Turno(
            indice=indice, papel=SISTEMA, instante=instante, bloques=(bloque,)
        )

    if tipo not in ("user", "assistant"):
        return None

    mensaje = evento.get("message")
    if not isinstance(mensaje, dict):
        return None

    return Turno(
        indice=indice,
        papel=ASISTENTE if tipo == "assistant" else USUARIO,
        instante=instante,
        uso=_uso(mensaje.get("usage")) if tipo == "assistant" else None,
        modelo=_cadena(mensaje.get("model")),
        identificador_mensaje=_cadena(mensaje.get("id")),
        bloques=tuple(_bloques(mensaje.get("content"))),
    )


def _uso(datos):
    if not isinstance(datos, dict):
        return None
    return Uso(
        entrada=_entero(datos.get("input_tokens")),
        creacion_cache=_entero(datos.get("cache_creation_input_tokens")),
        lectura_cache=_entero(datos.get("cache_read_input_tokens")),
        salida=_entero(datos.get("output_tokens")),
    )


def _bloques(contenido):
    if isinstance(contenido, str):
        return [Bloque(clase=TEXTO, texto=contenido)]
    if not isinstance(contenido, list):
        return []
    bloques = []
    for bruto in contenido:
        bloque = _bloque(bruto)
        if bloque is not None:
            bloques.append(bloque)
    return bloques


def _bloque(bruto):
    if isinstance(bruto, str):
        return Bloque(clase=TEXTO, texto=bruto)
    if not isinstance(bruto, dict):
        return None

    tipo = bruto.get("type")
    if tipo == "text":
        return Bloque(clase=TEXTO, texto=_cadena(bruto.get("text")) or "")
    if tipo == "thinking":
        return Bloque(clase=PENSAMIENTO, texto=_cadena(bruto.get("thinking")) or "")
    if tipo == "tool_use":
        return Bloque(
            clase=USO_HERRAMIENTA,
            # La entrada de la llamada es lo que ocupa contexto, y puede ser
            # tan grande como el contenido de un fichero que se escribe.
            texto=_texto_libre(bruto.get("input")),
            nombre=_cadena(bruto.get("name")),
            identificador=_cadena(bruto.get("id")),
            identificacion=_identificacion(bruto.get("input")),
        )
    if tipo == "tool_result":
        return Bloque(
            clase=RESULTADO_HERRAMIENTA,
            texto=_texto_de_resultado(bruto.get("content")),
            identificador=_cadena(bruto.get("tool_use_id")),
            es_error=bool(bruto.get("is_error")),
        )
    return None


# Argumentos que dicen sobre qué actuó una llamada, en orden de
# preferencia. Es lo que permite reconocer que dos llamadas distintas
# tocaron el mismo fichero o repitieron el mismo comando.
_ARGUMENTOS_IDENTIFICATIVOS = (
    "file_path",
    "notebook_path",
    "path",
    "command",
    "pattern",
    "url",
    "skill",
)


def _identificacion(entrada):
    """Extrae de la entrada de una llamada el dato que la identifica.

    Devuelve None si la llamada no actúa sobre nada nombrable, como un
    subagente lanzado con un prompt libre: ahí no hay objeto que comparar.
    """
    if not isinstance(entrada, dict):
        return None
    for clave in _ARGUMENTOS_IDENTIFICATIVOS:
        valor = entrada.get(clave)
        if isinstance(valor, str) and valor:
            return valor
    return None


def _bloque_de_adjunto(adjunto):
    if not isinstance(adjunto, dict):
        return None
    return Bloque(
        clase=ADJUNTO,
        # El adjunto se mide por su serialización completa: sus campos
        # varían según el subtipo y no hay uno solo que sea "el contenido".
        texto=_texto_libre(adjunto),
        nombre=_cadena(adjunto.get("type")),
        identificacion=_cadena(adjunto.get("filename")),
    )


def _texto_de_resultado(contenido):
    """Aplana el contenido de un `tool_result`, que unas veces es cadena y otras bloques."""
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        partes = []
        for bruto in contenido:
            if isinstance(bruto, str):
                partes.append(bruto)
            elif isinstance(bruto, dict):
                partes.append(_cadena(bruto.get("text")) or _texto_libre(bruto))
        return "\n".join(p for p in partes if p)
    if contenido is None:
        return ""
    return _texto_libre(contenido)


def _texto_libre(valor):
    if isinstance(valor, str):
        return valor
    if valor is None:
        return ""
    try:
        return json.dumps(valor, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(valor)


def _cadena(valor):
    return valor if isinstance(valor, str) else None


def _entero(valor):
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else 0


def parsear_instante(texto):
    """Convierte un timestamp ISO 8601 en datetime.

    Los transcripts usan la `Z` de UTC, que `fromisoformat` no admite hasta
    Python 3.11; se traduce a su desplazamiento explicito.
    """
    if not isinstance(texto, str):
        return None
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(texto)
    except ValueError:
        return None
