"""Mide el flujo del patrón: pasos cerrados, lanzamientos y reloj de pared.

Hasta ahora estas cifras se contaban a mano leyendo la traza, y una de
ellas es **la señal roja del patrón**: las rondas de El Malo por paso. Un
cambio que ahorra tokens pero sube las rondas ha salido caro, porque una
ronda extra de ataque cuesta más que casi cualquier ahorro de contexto.
Sin esta cifra en el informe, la herramienta medía el coste pero no la
calidad, y la decisión de revertir volvía a tomarse a ojo.

Dos advertencias que quien lea estas cifras debe conocer:

- **Los pasos se cuentan por la marca `PASO COMPLETADO`** que el Sheriff
  declara al cerrar cada unidad de trabajo, igual que la versión se lee de
  su marca `gbu vX.Y.Z`. Si el Sheriff no la emite —una sesión
  interrumpida a mitad de paso, una ejecución sin el patrón—, el paso no
  se cuenta. Es una aproximación honesta, no un registro exacto.
- **El reloj del sheriff incluye la espera humana.** Su transcript abarca
  la sesión entera, con las paradas entre pasos y las confirmaciones del
  usuario dentro. El reloj de un subagente sí es tiempo de trabajo: su
  transcript arranca al lanzarlo y termina al entregar.

Como el resto de módulos de métricas, este es puro: recibe conversaciones
ya normalizadas y devuelve cifras. No abre ficheros ni mira el reloj.
"""

from dataclasses import dataclass, field

from eventos import ASISTENTE, TEXTO
from metricas_coste import SHERIFF

# La marca con la que el Sheriff cierra cada unidad de trabajo. Está
# fijada en `gbu.md` («Declara: PASO COMPLETADO») desde la v0.1.0.
MARCA_PASO = "PASO COMPLETADO"

# El rol cuyas rondas son la señal roja del patrón.
MALO = "malo"


@dataclass(frozen=True)
class Flujo:
    """Las cifras de flujo de una sesión, o de una ventana de sesiones."""

    pasos: int = 0
    # Conversaciones lanzadas por rol, sin contar al sheriff: él no se
    # lanza, es la sesión.
    lanzamientos: dict = field(default_factory=dict)
    # Segundos de reloj de pared por rol. El del sheriff incluye la espera
    # humana; ver la advertencia del módulo.
    reloj: dict = field(default_factory=dict)

    @property
    def rondas_de_malo_por_paso(self):
        """Lanzamientos de El Malo por paso cerrado, o None sin pasos.

        None y no cero: una sesión sin marcas de paso no dice que las
        rondas fueran cero, dice que no se pueden atribuir.
        """
        if not self.pasos:
            return None
        return self.lanzamientos.get(MALO, 0) / self.pasos


def medir_flujo(participantes):
    """Calcula el flujo de una sesión a partir de sus participantes."""
    pasos = 0
    lanzamientos = {}
    reloj = {}
    for participante in participantes:
        rol = participante.rol
        if rol == SHERIFF:
            pasos += contar_pasos(participante.conversacion)
        else:
            lanzamientos[rol] = lanzamientos.get(rol, 0) + 1
        reloj[rol] = reloj.get(rol, 0.0) + duracion(participante.conversacion)
    return Flujo(pasos=pasos, lanzamientos=lanzamientos, reloj=reloj)


def sumar_flujos(flujos):
    """Agrega los flujos de varias sesiones; la secuencia vacía da el nulo."""
    pasos = 0
    lanzamientos = {}
    reloj = {}
    for flujo in flujos:
        pasos += flujo.pasos
        for rol, cuenta in flujo.lanzamientos.items():
            lanzamientos[rol] = lanzamientos.get(rol, 0) + cuenta
        for rol, segundos in flujo.reloj.items():
            reloj[rol] = reloj.get(rol, 0.0) + segundos
    return Flujo(pasos=pasos, lanzamientos=lanzamientos, reloj=reloj)


def contar_pasos(conversacion):
    """Cuenta las marcas `PASO COMPLETADO` en el texto del asistente.

    Solo el texto visible: si la marca apareciera en el pensamiento o en
    el resultado de una herramienta, no sería la declaración del Sheriff.
    """
    return sum(
        bloque.texto.count(MARCA_PASO)
        for turno in conversacion.turnos
        if turno.papel == ASISTENTE
        for bloque in turno.bloques
        if bloque.clase == TEXTO
    )


def duracion(conversacion):
    """Segundos entre el primer y el último instante de la conversación.

    Devuelve 0.0 cuando no hay dos instantes comparables: una conversación
    sin timestamps no duró cero segundos, pero tampoco se puede medir, y
    en una suma por rol el cero es el único valor que no inventa nada.
    """
    instantes = [t.instante for t in conversacion.turnos if t.instante is not None]
    if len(instantes) < 2:
        return 0.0
    primero, ultimo = instantes[0], instantes[-1]
    # Mezclar instantes con y sin zona horaria hace que restar lance
    # TypeError; en un transcript sano no pasa, pero un transcript no
    # tiene por qué estar sano.
    if (primero.tzinfo is None) != (ultimo.tzinfo is None):
        return 0.0
    return max((ultimo - primero).total_seconds(), 0.0)
