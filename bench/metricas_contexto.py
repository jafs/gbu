"""Mide qué ocupa el contexto de una conversación y cuánto cuesta releerlo.

El coste del Paso 3 dice cuánto se gastó; este módulo dice en qué. La
pieza central son los **turn-tokens**: los tokens de un bloque
multiplicados por el número de turnos de asistente que lo releerán. Un
fichero de mil tokens que entra al principio de una conversación de cien
turnos cuesta cien mil; el mismo fichero al final no cuesta casi nada. Es
la métrica que explica por qué una conversación larga se encarece sola
sin que nadie haga nada especialmente caro.

Un matiz sobre quién relee qué: un bloque que escribe el asistente lo
releen los turnos siguientes, no el suyo, porque en su turno todavía no
existía. Un bloque que llega del usuario o del sistema sí lo lee ya el
turno que responde a él, porque formaba parte de su entrada.

Las funciones son puras: reciben conversaciones normalizadas y devuelven
cifras. El prelude es la única que devuelve una estimación declarada como
tal, y va marcada en su nombre y en su documentación.
"""

from dataclasses import dataclass, field

from eventos import ASISTENTE


@dataclass(frozen=True)
class PuntoDeContexto:
    """El contexto que leyó un turno de asistente."""

    turno: int
    instante: object = None
    contexto: int = 0
    salida: int = 0
    modelo: str | None = None


@dataclass(frozen=True)
class Curva:
    """La evolución del contexto a lo largo de una conversación."""

    puntos: tuple[PuntoDeContexto, ...] = field(default_factory=tuple)

    @property
    def maximo(self):
        return max((p.contexto for p in self.puntos), default=0)

    @property
    def media(self):
        if not self.puntos:
            return 0.0
        return sum(p.contexto for p in self.puntos) / len(self.puntos)

    @property
    def final(self):
        return self.puntos[-1].contexto if self.puntos else 0

    @property
    def inicial(self):
        return self.puntos[0].contexto if self.puntos else 0


@dataclass(frozen=True)
class BloqueCaro:
    """Un bloque con lo que costó su permanencia en el contexto."""

    clase: str
    nombre: str | None
    identificacion: str | None
    turno: int
    tokens: int
    lecturas: int

    @property
    def turn_tokens(self):
        return self.tokens * self.lecturas


def curva_de_contexto(conversacion):
    """Contexto turno a turno, solo de los turnos que declararon `usage`."""
    return Curva(
        puntos=tuple(
            PuntoDeContexto(
                turno=turno.indice,
                instante=turno.instante,
                contexto=turno.uso.contexto,
                salida=turno.uso.salida,
                modelo=turno.modelo,
            )
            for turno in conversacion.turnos
            if turno.papel == ASISTENTE and turno.uso is not None
        )
    )


def prelude_estimado(conversacion):
    """Aproxima lo que ocupa el contexto fijo de la conversación.

    Es el contexto del primer turno menos lo que el transcript había
    escrito hasta entonces. Lo que queda es lo que no aparece en el
    transcript y sin embargo se paga en cada turno: el prompt de sistema,
    las definiciones de las herramientas y los ficheros de contexto del
    proyecto.

    Es una resta entre una cifra real y una estimada, así que nunca es
    exacta; se recorta a cero porque un prelude negativo solo significa
    que la estimación se pasó de larga.
    """
    primero = next(
        (
            t
            for t in conversacion.turnos
            if t.papel == ASISTENTE and t.uso is not None
        ),
        None,
    )
    if primero is None:
        return 0
    previos = sum(
        t.tokens_estimados for t in conversacion.turnos if t.indice < primero.indice
    )
    return max(0, primero.uso.contexto - previos)


def bloques_con_lecturas(conversacion):
    """Cada bloque con el número de turnos de asistente que lo releerán."""
    indices = [
        t.indice
        for t in conversacion.turnos
        if t.papel == ASISTENTE and t.uso is not None
    ]
    caros = []
    for turno in conversacion.turnos:
        propio = turno.papel == ASISTENTE
        for bloque in turno.bloques:
            caros.append(
                BloqueCaro(
                    clase=bloque.clase,
                    nombre=bloque.nombre,
                    identificacion=bloque.identificacion,
                    turno=turno.indice,
                    tokens=bloque.tokens,
                    lecturas=_lecturas(indices, turno.indice, propio),
                )
            )
    return tuple(caros)


def reparto_de_turn_tokens(conversacion):
    """Turn-tokens agrupados por clase de bloque."""
    reparto = {}
    for bloque in bloques_con_lecturas(conversacion):
        reparto[bloque.clase] = reparto.get(bloque.clase, 0) + bloque.turn_tokens
    return reparto


def bloques_mas_caros(conversacion, limite=20):
    """Los bloques que más caro salieron por permanecer en el contexto."""
    caros = [b for b in bloques_con_lecturas(conversacion) if b.turn_tokens]
    caros.sort(key=lambda b: (-b.turn_tokens, b.turno))
    return tuple(caros[:limite])


def turn_tokens_totales(conversacion):
    return sum(b.turn_tokens for b in bloques_con_lecturas(conversacion))


def texto_del_contexto(conversacion):
    """Tokens estimados de todo lo que el transcript aportó al contexto.

    Es el contrapeso del prelude: lo que sí se ve en el transcript.
    """
    return sum(t.tokens_estimados for t in conversacion.turnos)


def _lecturas(indices_de_asistente, indice, es_del_asistente):
    """Cuántos turnos de asistente leerán un bloque situado en `indice`.

    Lo que escribe el asistente lo releen los turnos posteriores; lo que
    llega del usuario o del sistema lo lee ya el turno que responde.
    """
    if es_del_asistente:
        return sum(1 for i in indices_de_asistente if i > indice)
    return sum(1 for i in indices_de_asistente if i >= indice)
