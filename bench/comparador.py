"""Compara dos informes archivados y prepara el material para leerlos.

Este módulo no dice si la cosa ha mejorado. Cruza las cifras y los
hallazgos, señala lo que no cuadra, y deja la lectura para quien lea. Esa
división es deliberada: el veredicto necesita saber qué se tocó entre las
dos ventanas, y eso el JSON no lo sabe.

Lo que sí es responsabilidad de aquí es que el veredicto se pueda emitir
**sin volver a abrir los transcripts**, porque abrirlos cuesta justo lo
que esta herramienta existe para medir. Por eso la salida trae las cifras
de los dos lados, no solo la diferencia.

Dos ventanas casi nunca tienen el mismo tamaño, así que además de los
totales se comparan las cifras **por sesión y por turno**. Un total que
baja porque se trabajó menos no es una mejora del patrón, y sin las
cifras normalizadas esa confusión es indistinguible de un éxito.
"""

from dataclasses import dataclass, field

# Métricas que, cuando bajan, son buena noticia. Las demás se presentan
# sin juicio: más turnos no es mejor ni peor por sí mismo.
_MENOS_ES_MEJOR = (
    "coste_total",
    "coste_por_sesion",
    "coste_por_turno",
    "coste_por_paso",
    "rondas_de_malo_por_paso",
    "turn_tokens",
    "pensamiento",
    "hallazgos",
)

# Métricas fraccionarias: redondearlas a enteros en el cuadro las
# destrozaría (1,67 rondas y 2,4 rondas saldrían las dos como «2»).
_CON_DECIMALES = ("rondas_de_malo_por_paso",)

# A partir de qué proporción entre ventanas la comparación deja de ser
# directa. Con el doble de sesiones en un lado, los totales ya no se
# pueden leer uno contra otro.
_PROPORCION_SOSPECHOSA = 2.0


@dataclass(frozen=True)
class Variacion:
    """Una métrica en los dos informes, con su diferencia."""

    nombre: str
    antes: float
    despues: float
    familia: str = "general"

    @property
    def absoluta(self):
        return self.despues - self.antes

    @property
    def porcentaje(self):
        """Variación relativa, o None si no hay base con la que comparar."""
        if not self.antes:
            return None
        return (self.despues - self.antes) / self.antes * 100

    @property
    def mejora(self):
        """True si la variación es buena, False si es mala, None si no se juzga."""
        if self.nombre not in _MENOS_ES_MEJOR and self.familia not in _MENOS_ES_MEJOR:
            return None
        if self.absoluta == 0:
            return None
        return self.absoluta < 0


@dataclass(frozen=True)
class HallazgoComparado:
    """Un hallazgo visto en uno de los dos informes, o en los dos."""

    identificador: str
    categoria: str
    titulo: str
    severidad: str
    antes: int = 0
    despues: int = 0

    @property
    def absoluta(self):
        return self.despues - self.antes


@dataclass(frozen=True)
class Comparacion:
    """El cuadro de variación entre dos informes."""

    proyecto: str = ""
    version_antes: str = ""
    version_despues: str = ""
    metricas: tuple[Variacion, ...] = field(default_factory=tuple)
    resueltos: tuple[HallazgoComparado, ...] = field(default_factory=tuple)
    persistentes: tuple[HallazgoComparado, ...] = field(default_factory=tuple)
    nuevos: tuple[HallazgoComparado, ...] = field(default_factory=tuple)
    avisos: tuple[str, ...] = field(default_factory=tuple)


def comparar(referencia, nuevo):
    """Cruza dos informes ya cargados como diccionarios."""
    return Comparacion(
        proyecto=nuevo.get("proyecto") or referencia.get("proyecto") or "",
        version_antes=_versiones(referencia),
        version_despues=_versiones(nuevo),
        metricas=_metricas(referencia, nuevo),
        resueltos=_resueltos(referencia, nuevo),
        persistentes=_persistentes(referencia, nuevo),
        nuevos=_nuevos(referencia, nuevo),
        avisos=_avisos(referencia, nuevo),
    )


def _metricas(referencia, nuevo):
    antes = referencia.get("metricas") or {}
    despues = nuevo.get("metricas") or {}
    variaciones = [
        Variacion("sesiones", _numero(antes, "sesiones"), _numero(despues, "sesiones")),
        Variacion("turnos", _numero(antes, "turnos"), _numero(despues, "turnos")),
        Variacion("coste_total", _numero(antes, "coste_total"), _numero(despues, "coste_total")),
        Variacion(
            "coste_por_sesion",
            _por(antes, "coste_total", "sesiones"),
            _por(despues, "coste_total", "sesiones"),
        ),
        Variacion(
            "coste_por_turno",
            _por(antes, "coste_total", "turnos"),
            _por(despues, "coste_total", "turnos"),
        ),
        Variacion("pensamiento", _numero(antes, "pensamiento"), _numero(despues, "pensamiento")),
    ]
    variaciones += _flujo(antes, despues)
    variaciones += _por_clave(antes, despues, "por_rol", "coste", "rol")
    variaciones += _por_clave(antes, despues, "por_modelo", "coste", "modelo")
    variaciones += _turn_tokens(antes, despues)
    variaciones.append(
        Variacion(
            "hallazgos",
            len(referencia.get("hallazgos") or []),
            len(nuevo.get("hallazgos") or []),
        )
    )
    return tuple(variaciones)


def _por_clave(antes, despues, seccion, campo, familia):
    """Compara un diccionario de agregados, clave a clave.

    Las claves que solo están en uno de los dos informes entran igual, con
    cero en el lado que falta: un rol que aparece o desaparece es
    exactamente el tipo de cambio que interesa ver.
    """
    izquierda = antes.get(seccion) or {}
    derecha = despues.get(seccion) or {}
    return [
        Variacion(
            nombre=clave,
            antes=_numero(izquierda.get(clave) or {}, campo),
            despues=_numero(derecha.get(clave) or {}, campo),
            familia=familia,
        )
        for clave in sorted(set(izquierda) | set(derecha))
    ]


def _turn_tokens(antes, despues):
    izquierda = antes.get("turn_tokens") or {}
    derecha = despues.get("turn_tokens") or {}
    return [
        Variacion(
            nombre=clase,
            antes=float(izquierda.get(clase) or 0),
            despues=float(derecha.get(clase) or 0),
            familia="turn_tokens",
        )
        for clase in sorted(set(izquierda) | set(derecha))
    ]


def _flujo(antes, despues):
    """Compara las métricas de flujo, si los dos informes las traen.

    Cuando falta en uno de los lados —un informe archivado con una versión
    anterior de la herramienta— no se compara contra ceros inventados: se
    omite la fila y `_avisos` lo dice.
    """
    izquierda = antes.get("flujo")
    derecha = despues.get("flujo")
    if not izquierda or not derecha:
        return []
    variaciones = [
        Variacion("pasos", _numero(izquierda, "pasos"), _numero(derecha, "pasos"), familia="flujo"),
        Variacion("coste_por_paso", _coste_por_paso(antes), _coste_por_paso(despues), familia="flujo"),
        Variacion(
            "rondas_de_malo_por_paso",
            _numero(izquierda, "rondas_de_malo_por_paso"),
            _numero(derecha, "rondas_de_malo_por_paso"),
            familia="flujo",
        ),
    ]
    reloj_antes = izquierda.get("reloj_segundos") or {}
    reloj_despues = derecha.get("reloj_segundos") or {}
    variaciones += [
        Variacion(
            nombre=f"reloj_{rol}",
            antes=float(reloj_antes.get(rol) or 0),
            despues=float(reloj_despues.get(rol) or 0),
            familia="reloj",
        )
        for rol in sorted(set(reloj_antes) | set(reloj_despues))
    ]
    return variaciones


def _coste_por_paso(metricas):
    pasos = _numero(metricas.get("flujo") or {}, "pasos")
    if not pasos:
        return 0.0
    return _numero(metricas, "coste_total") / pasos


def _resueltos(referencia, nuevo):
    presentes = {h["identificador"] for h in nuevo.get("hallazgos") or []}
    return tuple(
        _comparado(h, antes=h.get("tokens", 0), despues=0)
        for h in referencia.get("hallazgos") or []
        if h["identificador"] not in presentes
    )


def _persistentes(referencia, nuevo):
    anteriores = {h["identificador"]: h for h in referencia.get("hallazgos") or []}
    return tuple(
        _comparado(
            h,
            antes=anteriores[h["identificador"]].get("tokens", 0),
            despues=h.get("tokens", 0),
        )
        for h in nuevo.get("hallazgos") or []
        if h["identificador"] in anteriores
    )


def _nuevos(referencia, nuevo):
    anteriores = {h["identificador"] for h in referencia.get("hallazgos") or []}
    return tuple(
        _comparado(h, antes=0, despues=h.get("tokens", 0))
        for h in nuevo.get("hallazgos") or []
        if h["identificador"] not in anteriores
    )


def _comparado(hallazgo, antes, despues):
    return HallazgoComparado(
        identificador=hallazgo["identificador"],
        categoria=hallazgo.get("categoria", ""),
        titulo=hallazgo.get("titulo", ""),
        severidad=hallazgo.get("severidad", ""),
        antes=antes,
        despues=despues,
    )


def _avisos(referencia, nuevo):
    avisos = []
    if referencia.get("esquema") != nuevo.get("esquema"):
        avisos.append(
            f"Los informes usan esquemas distintos ({referencia.get('esquema')} y "
            f"{nuevo.get('esquema')}): puede que no todas las cifras sean equivalentes."
        )

    versiones_antes = set(referencia.get("versiones") or {})
    versiones_despues = set(nuevo.get("versiones") or {})
    comunes = versiones_antes & versiones_despues
    if comunes:
        avisos.append(
            "Los dos informes cubren la versión "
            + ", ".join(sorted(comunes))
            + ": comparar una versión consigo misma casi siempre significa que el "
            "filtro estaba mal puesto."
        )
    if len(versiones_antes) > 1 or len(versiones_despues) > 1:
        avisos.append(
            "Alguna de las dos ventanas mezcla varias versiones del patrón, así que "
            "la variación no se puede atribuir a un solo cambio."
        )

    flujo_antes = bool((referencia.get("metricas") or {}).get("flujo"))
    flujo_despues = bool((nuevo.get("metricas") or {}).get("flujo"))
    if flujo_antes != flujo_despues:
        avisos.append(
            "Solo uno de los dos informes trae métricas de flujo (el otro se "
            "archivó con una versión anterior de la herramienta): pasos, rondas "
            "y reloj no se comparan."
        )

    sesiones_antes = _numero(referencia.get("metricas") or {}, "sesiones")
    sesiones_despues = _numero(nuevo.get("metricas") or {}, "sesiones")
    if not sesiones_antes or not sesiones_despues:
        avisos.append(
            "Una de las dos ventanas no tiene sesiones: no hay nada que comparar."
        )
    elif _proporcion(sesiones_antes, sesiones_despues) >= _PROPORCION_SOSPECHOSA:
        avisos.append(
            f"Las ventanas son de tamaño muy distinto ({sesiones_antes:.0f} sesiones "
            f"frente a {sesiones_despues:.0f}): los totales no se pueden leer uno "
            "contra otro, hay que mirar las cifras por sesión y por turno."
        )
    return tuple(avisos)


def _proporcion(a, b):
    mayor, menor = max(a, b), min(a, b)
    return mayor / menor if menor else float("inf")


def _numero(diccionario, clave):
    valor = diccionario.get(clave)
    return float(valor) if isinstance(valor, (int, float)) else 0.0


def _por(metricas, numerador, denominador):
    divisor = _numero(metricas, denominador)
    if not divisor:
        return 0.0
    return _numero(metricas, numerador) / divisor


def _versiones(informe):
    versiones = informe.get("versiones") or {}
    return ", ".join(sorted(versiones)) or "?"


def a_markdown(comparacion):
    """Redacta el cuadro de variación, con las cifras de los dos lados."""
    lineas = [
        f"# Comparación — {comparacion.proyecto}",
        "",
        f"- **Antes**: versión {comparacion.version_antes}",
        f"- **Después**: versión {comparacion.version_despues}",
        "",
    ]
    if comparacion.avisos:
        lineas += ["## Avisos", ""] + [f"- {a}" for a in comparacion.avisos] + [""]

    lineas += ["## Métricas", "", "| Métrica | Antes | Después | Variación | % |", "| --- | ---: | ---: | ---: | ---: |"]
    for variacion in comparacion.metricas:
        lineas.append(
            f"| {_marca(variacion)}{variacion.nombre} | {_cifra(variacion, variacion.antes)} "
            f"| {_cifra(variacion, variacion.despues)} "
            f"| {_cifra(variacion, variacion.absoluta, signo=True)} | {_porcentaje(variacion)} |"
        )

    lineas += [
        "",
        "## Hallazgos",
        "",
        f"- **Resueltos**: {len(comparacion.resueltos)}",
        f"- **Persistentes**: {len(comparacion.persistentes)}",
        f"- **Nuevos**: {len(comparacion.nuevos)}",
        "",
    ]
    lineas += _lista("Resueltos", comparacion.resueltos, lambda h: f"costaban {h.antes:,} turn-tokens")
    lineas += _lista(
        "Persistentes",
        sorted(comparacion.persistentes, key=lambda h: -abs(h.absoluta)),
        lambda h: f"{h.antes:,} → {h.despues:,} turn-tokens ({h.absoluta:+,})",
    )
    lineas += _lista("Nuevos", comparacion.nuevos, lambda h: f"{h.despues:,} turn-tokens")
    return "\n".join(lineas).rstrip() + "\n"


def _lista(titulo, hallazgos, describir):
    if not hallazgos:
        return [f"### {titulo}", "", "Ninguno.", ""]
    lineas = [f"### {titulo}", ""]
    for hallazgo in hallazgos:
        lineas.append(
            f"- `{hallazgo.identificador}` **[{hallazgo.severidad}]** "
            f"{hallazgo.titulo} — {describir(hallazgo)}"
        )
    lineas.append("")
    return lineas


def _cifra(variacion, valor, signo=False):
    decimales = 2 if variacion.nombre in _CON_DECIMALES else 0
    return f"{valor:{'+' if signo else ''},.{decimales}f}"


def _marca(variacion):
    if variacion.mejora is None:
        return ""
    return "↓ " if variacion.mejora else "↑ "


def _porcentaje(variacion):
    if variacion.porcentaje is None:
        return "—"
    return f"{variacion.porcentaje:+.1f}%"
