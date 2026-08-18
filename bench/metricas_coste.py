"""Agrega el coste de una sesión por rol y por modelo.

Las funciones de este módulo son puras: reciben conversaciones ya
normalizadas y devuelven cifras. No abren ficheros ni miran el reloj.

El **coste normalizado** expresa en una sola cifra lo que costó un turno,
en unidades de token de entrada equivalente. Los tokens no valen todos lo
mismo: escribir en caché cuesta más que entrar sin cachear, leer de caché
cuesta mucho menos, y la salida cuesta varias veces la entrada. Los pesos
por defecto reflejan esa proporción y son ajustables, porque la
proporción exacta depende del modelo y de la tarifa vigente.

El **modelo** se atribuye a cada turno porque cada rol puede correr en uno
distinto y porque puede cambiar de una versión del patrón a la siguiente.
Sin ese desglose, un cambio de modelo se leería como una mejora o un
empeoramiento del patrón, que es justo la conclusión contraria a la
verdadera.
"""

from dataclasses import dataclass, field

from eventos import ASISTENTE

# Unidades de token de entrada equivalente. La entrada sin cachear es la
# unidad; los demás se expresan en relación a ella.
PESOS_POR_DEFECTO = {
    "entrada": 1.0,
    "creacion_cache": 1.25,
    "lectura_cache": 0.1,
    "salida": 5.0,
}

SHERIFF = "sheriff"

# Un turno puede no declarar modelo, y un subagente puede no traerlo en su
# `.meta.json`. Se le pone nombre en vez de dejarlo a None para que aparezca
# en el informe: un coste sin modelo atribuido es un hueco que conviene ver.
MODELO_DESCONOCIDO = "desconocido"


@dataclass(frozen=True)
class Agregado:
    """Recuento de turnos y tokens de un conjunto de turnos."""

    turnos: int = 0
    entrada: int = 0
    creacion_cache: int = 0
    lectura_cache: int = 0
    salida: int = 0
    pensamiento: int = 0
    turnos_sin_uso: int = 0

    @property
    def contexto(self):
        """Tokens de entrada acumulados en todos los turnos.

        Es una suma de contextos, no el tamaño de ninguno: crece con cada
        turno porque cada turno relee lo anterior. Sirve para comparar
        sesiones entre sí, no para saber cuánto ocupaba la conversación.
        """
        return self.entrada + self.creacion_cache + self.lectura_cache

    def __add__(self, otro):
        if not isinstance(otro, Agregado):
            return NotImplemented
        return Agregado(
            turnos=self.turnos + otro.turnos,
            entrada=self.entrada + otro.entrada,
            creacion_cache=self.creacion_cache + otro.creacion_cache,
            lectura_cache=self.lectura_cache + otro.lectura_cache,
            salida=self.salida + otro.salida,
            pensamiento=self.pensamiento + otro.pensamiento,
            turnos_sin_uso=self.turnos_sin_uso + otro.turnos_sin_uso,
        )


@dataclass(frozen=True)
class Participante:
    """Una conversación con el papel que jugó en la sesión."""

    rol: str
    conversacion: object
    modelo: str | None = None


@dataclass(frozen=True)
class CosteDeRol:
    """Lo que gastó un rol, con su desglose por modelo."""

    rol: str
    total: Agregado
    por_modelo: dict = field(default_factory=dict)
    conversaciones: int = 0


@dataclass(frozen=True)
class CosteDeSesion:
    """Lo que gastó una sesión entera, rol por rol."""

    identificador: str
    roles: tuple[CosteDeRol, ...] = field(default_factory=tuple)

    @property
    def total(self):
        return sumar(r.total for r in self.roles)

    @property
    def modelos(self):
        """Agregado por modelo, cruzando todos los roles."""
        acumulado = {}
        for rol in self.roles:
            for modelo, agregado in rol.por_modelo.items():
                acumulado[modelo] = acumulado.get(modelo, Agregado()) + agregado
        return acumulado


def sumar(agregados):
    """Suma una secuencia de agregados; la secuencia vacía da el agregado nulo."""
    total = Agregado()
    for agregado in agregados:
        total = total + agregado
    return total


def coste(agregado, pesos=None):
    """Coste normalizado de un agregado, en tokens de entrada equivalentes."""
    pesos = pesos or PESOS_POR_DEFECTO
    return (
        agregado.entrada * pesos.get("entrada", 0.0)
        + agregado.creacion_cache * pesos.get("creacion_cache", 0.0)
        + agregado.lectura_cache * pesos.get("lectura_cache", 0.0)
        + agregado.salida * pesos.get("salida", 0.0)
    )


def resumir_conversacion(conversacion, modelo_declarado=None):
    """Agrega una conversación entera y su desglose por modelo.

    Solo cuentan los turnos de asistente: son los únicos que declaran
    `usage`, porque son los únicos que hicieron gastar algo.
    """
    total = Agregado()
    por_modelo = {}
    for turno in conversacion.turnos:
        if turno.papel != ASISTENTE:
            continue
        agregado = _agregado_de_turno(turno)
        modelo = turno.modelo or modelo_declarado or MODELO_DESCONOCIDO
        total = total + agregado
        por_modelo[modelo] = por_modelo.get(modelo, Agregado()) + agregado
    return total, por_modelo


def agregar_sesion(participantes, identificador="sesion"):
    """Agrega una sesión completa: el principal y sus subagentes.

    Los participantes con el mismo rol se funden en una sola entrada —una
    sesión lanza varios Malos y varios Feos, y lo que interesa es lo que
    cuesta el rol, no cada instancia—. El orden de los roles se conserva
    tal como aparecieron.
    """
    totales = {}
    modelos = {}
    cuentas = {}
    orden = []

    for participante in participantes:
        rol = participante.rol
        if rol not in totales:
            orden.append(rol)
            totales[rol] = Agregado()
            modelos[rol] = {}
            cuentas[rol] = 0
        total, por_modelo = resumir_conversacion(
            participante.conversacion, participante.modelo
        )
        totales[rol] = totales[rol] + total
        cuentas[rol] += 1
        for modelo, agregado in por_modelo.items():
            modelos[rol][modelo] = modelos[rol].get(modelo, Agregado()) + agregado

    return CosteDeSesion(
        identificador=identificador,
        roles=tuple(
            CosteDeRol(
                rol=rol,
                total=totales[rol],
                por_modelo=modelos[rol],
                conversaciones=cuentas[rol],
            )
            for rol in orden
        ),
    )


def reparto(coste_de_sesion, pesos=None):
    """Fracción del coste total que se lleva cada rol, entre 0 y 1.

    Con coste total nulo devuelve todo a cero en vez de dividir: una sesión
    sin `usage` no reparte nada, y no es un error que deba abortar el informe.
    """
    total = coste(coste_de_sesion.total, pesos)
    if not total:
        return {rol.rol: 0.0 for rol in coste_de_sesion.roles}
    return {rol.rol: coste(rol.total, pesos) / total for rol in coste_de_sesion.roles}


def _agregado_de_turno(turno):
    if turno.uso is None:
        # El turno existió y ocupó su sitio en la conversación, así que se
        # cuenta; lo que no se puede es atribuirle tokens que no declaró.
        return Agregado(turnos=1, turnos_sin_uso=1)
    return Agregado(
        turnos=1,
        entrada=turno.uso.entrada,
        creacion_cache=turno.uso.creacion_cache,
        lectura_cache=turno.uso.lectura_cache,
        salida=turno.uso.salida,
        pensamiento=turno.uso.pensamiento,
    )
