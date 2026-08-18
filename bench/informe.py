"""Compone el informe de una ventana de sesiones y lo emite en dos formas.

El markdown es para leerlo; el JSON es para archivarlo y compararlo
después. Los dos llevan la misma información, salvo la serie por turno,
que solo va en el JSON: en markdown sería ilegible, y sin ella ninguna
línea de tiempo podría dibujarse más adelante sin volver a abrir los
transcripts, que cuesta justo lo que esta herramienta existe para evitar.

Dos advertencias que el informe lleva escritas, porque callarlas sería
mentir por omisión:

- **Los tokens de los hallazgos no se suman entre categorías.** Cada
  detector mira desde un ángulo distinto y varios señalan a la vez el
  mismo bloque. El total por categoría es legítimo; un total general no.
- **El pensamiento no se puede repartir por bloques.** Llega al transcript
  con el texto vacío y solo la firma, así que en el reparto de
  turn-tokens aparece como cero. Lo que sí consta es su total, que se
  toma del `usage` y se informa aparte.

Este módulo no lee ficheros ni mira el reloj: el instante de generación se
recibe como argumento.
"""

import json
from dataclasses import dataclass, field

from detectores import UMBRALES_POR_DEFECTO, Vista, detectar
from hallazgos import agrupar, fusionar, ordenar, resumen_por_severidad
from metricas_contexto import (
    curva_de_contexto,
    prelude_estimado,
    reparto_de_turn_tokens,
)
from metricas_coste import (
    PESOS_POR_DEFECTO,
    Agregado,
    agregar_sesion,
    coste,
    sumar,
)

VERSION_ESQUEMA = 1

AVISO_HALLAZGOS = (
    "Los tokens de los hallazgos no se suman entre categorías: varios "
    "detectores señalan el mismo bloque desde ángulos distintos."
)
AVISO_PENSAMIENTO = (
    "El pensamiento llega al transcript sin texto, así que en el reparto de "
    "turn-tokens cuenta como cero. Su total sale del `usage` y va aparte."
)


@dataclass(frozen=True)
class SesionAnalizada:
    """Una sesión con todo lo que el informe necesita de ella."""

    identificador: str
    version: str | None = None
    via: str | None = None
    inicio: object = None
    fin: object = None
    costes: object = None
    curvas: dict = field(default_factory=dict)
    preludes: dict = field(default_factory=dict)
    turn_tokens: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Informe:
    """El informe de una ventana de sesiones de un proyecto."""

    proyecto: str
    generado_en: str | None = None
    ventana: dict = field(default_factory=dict)
    versiones: dict = field(default_factory=dict)
    vias: dict = field(default_factory=dict)
    avisos: tuple[str, ...] = field(default_factory=tuple)
    sesiones: tuple[SesionAnalizada, ...] = field(default_factory=tuple)
    descartadas: tuple[dict, ...] = field(default_factory=tuple)
    hallazgos: tuple = field(default_factory=tuple)
    pesos: dict = field(default_factory=lambda: dict(PESOS_POR_DEFECTO))

    @property
    def coste_por_rol(self):
        """Agregado de cada rol, sumando todas las sesiones de la ventana."""
        acumulado = {}
        for sesion in self.sesiones:
            for rol in sesion.costes.roles if sesion.costes else ():
                acumulado[rol.rol] = acumulado.get(rol.rol, Agregado()) + rol.total
        return dict(
            sorted(acumulado.items(), key=lambda par: -coste(par[1], self.pesos))
        )

    @property
    def coste_por_modelo(self):
        acumulado = {}
        for sesion in self.sesiones:
            for modelo, agregado in (sesion.costes.modelos if sesion.costes else {}).items():
                acumulado[modelo] = acumulado.get(modelo, Agregado()) + agregado
        return dict(
            sorted(acumulado.items(), key=lambda par: -coste(par[1], self.pesos))
        )

    @property
    def total(self):
        return sumar(self.coste_por_rol.values())

    @property
    def turn_tokens(self):
        acumulado = {}
        for sesion in self.sesiones:
            for clase, tokens in sesion.turn_tokens.items():
                acumulado[clase] = acumulado.get(clase, 0) + tokens
        return dict(sorted(acumulado.items(), key=lambda par: -par[1]))


def analizar_sesion(clasificada, participantes, umbrales=None):
    """Calcula todo lo que se sabe de una sesión y emite sus hallazgos.

    Devuelve el análisis y los hallazgos por separado porque los hallazgos
    se funden después entre sesiones y el análisis no.
    """
    umbrales = umbrales or UMBRALES_POR_DEFECTO
    sesion = clasificada.sesion
    identificador = clasificada.identificador
    vistas = [
        Vista(sesion=identificador, rol=p.rol, conversacion=p.conversacion)
        for p in participantes
    ]
    curvas = {}
    preludes = {}
    turn_tokens = {}
    for participante in participantes:
        rol = participante.rol
        curva = curva_de_contexto(participante.conversacion)
        # Del mismo rol puede haber varias conversaciones: se guarda la más
        # larga, que es la que manda al hablar de contextos desbocados.
        if rol not in curvas or len(curva.puntos) > len(curvas[rol].puntos):
            curvas[rol] = curva
            preludes[rol] = prelude_estimado(participante.conversacion)
        for clase, tokens in reparto_de_turn_tokens(participante.conversacion).items():
            turn_tokens[clase] = turn_tokens.get(clase, 0) + tokens

    analisis = SesionAnalizada(
        identificador=identificador,
        version=clasificada.version,
        via=clasificada.via,
        inicio=getattr(sesion, "inicio", None),
        fin=getattr(sesion, "fin", None),
        costes=agregar_sesion(participantes, identificador),
        curvas=curvas,
        preludes=preludes,
        turn_tokens=turn_tokens,
    )
    return analisis, detectar(vistas, umbrales)


def componer(proyecto, seleccion, analisis, hallazgos, generado_en=None, ventana=None, pesos=None):
    """Reúne los análisis y los hallazgos en un informe."""
    return Informe(
        proyecto=str(proyecto),
        generado_en=generado_en,
        ventana=dict(ventana or {}),
        versiones=seleccion.versiones,
        vias=seleccion.vias,
        avisos=tuple(seleccion.avisos) + (AVISO_HALLAZGOS, AVISO_PENSAMIENTO),
        sesiones=tuple(analisis),
        descartadas=tuple(
            {"sesion": c.identificador, "motivo": c.motivo}
            for c in seleccion.descartadas
        ),
        hallazgos=ordenar(fusionar(hallazgos)),
        pesos=dict(pesos or PESOS_POR_DEFECTO),
    )


def a_json(informe):
    """Serializa el informe, incluida la serie por turno de cada sesión."""
    return json.dumps(_estructura(informe), ensure_ascii=False, indent=2)


def _estructura(informe):
    return {
        "esquema": VERSION_ESQUEMA,
        "proyecto": informe.proyecto,
        "generado_en": informe.generado_en,
        "ventana": informe.ventana,
        "versiones": informe.versiones,
        "vias": informe.vias,
        "avisos": list(informe.avisos),
        "pesos": informe.pesos,
        "metricas": {
            "coste_total": round(coste(informe.total, informe.pesos), 2),
            "turnos": informe.total.turnos,
            "sesiones": len(informe.sesiones),
            "pensamiento": informe.total.pensamiento,
            "por_rol": {
                rol: _agregado(agregado, informe.pesos)
                for rol, agregado in informe.coste_por_rol.items()
            },
            "por_modelo": {
                modelo: _agregado(agregado, informe.pesos)
                for modelo, agregado in informe.coste_por_modelo.items()
            },
            "turn_tokens": informe.turn_tokens,
        },
        "sesiones": [_sesion(s, informe.pesos) for s in informe.sesiones],
        "descartadas": [dict(d) for d in informe.descartadas],
        "hallazgos": [_hallazgo(h) for h in informe.hallazgos],
    }


def _agregado(agregado, pesos):
    return {
        "turnos": agregado.turnos,
        "entrada": agregado.entrada,
        "creacion_cache": agregado.creacion_cache,
        "lectura_cache": agregado.lectura_cache,
        "salida": agregado.salida,
        "pensamiento": agregado.pensamiento,
        "turnos_sin_uso": agregado.turnos_sin_uso,
        "coste": round(coste(agregado, pesos), 2),
    }


def _sesion(sesion, pesos):
    return {
        "identificador": sesion.identificador,
        "version": sesion.version,
        "via": sesion.via,
        "inicio": _instante(sesion.inicio),
        "fin": _instante(sesion.fin),
        "coste": round(coste(sesion.costes.total, pesos), 2) if sesion.costes else 0,
        "por_rol": {
            rol.rol: _agregado(rol.total, pesos)
            for rol in (sesion.costes.roles if sesion.costes else ())
        },
        "preludes": dict(sesion.preludes),
        "turn_tokens": dict(sesion.turn_tokens),
        "contexto": {
            rol: {
                "maximo": curva.maximo,
                "media": round(curva.media, 2),
                "final": curva.final,
                "turnos": len(curva.puntos),
            }
            for rol, curva in sesion.curvas.items()
        },
        # La serie es lo que permite dibujar después una línea de tiempo sin
        # volver a los transcripts.
        "serie": {
            rol: [
                {
                    "turno": punto.turno,
                    "instante": _instante(punto.instante),
                    "contexto": punto.contexto,
                    "salida": punto.salida,
                    "modelo": punto.modelo,
                }
                for punto in curva.puntos
            ]
            for rol, curva in sesion.curvas.items()
        },
    }


def _hallazgo(hallazgo):
    return {
        "identificador": hallazgo.identificador,
        "categoria": hallazgo.categoria,
        "severidad": hallazgo.severidad,
        "titulo": hallazgo.titulo,
        "clave": hallazgo.clave,
        "tokens": hallazgo.tokens,
        "evidencias": [
            {
                "sesion": e.sesion,
                "rol": e.rol,
                "turno": e.turno,
                "fragmento": e.fragmento,
                "detalle": e.detalle,
            }
            for e in hallazgo.evidencias
        ],
    }


def _instante(valor):
    return valor.isoformat() if hasattr(valor, "isoformat") else valor


def a_markdown(informe):
    """Redacta el informe legible, por secciones."""
    lineas = [f"# Informe de sesiones — {informe.proyecto}", ""]
    lineas += _cabecera(informe)
    lineas += _seccion_avisos(informe)
    lineas += _seccion_coste(informe)
    lineas += _seccion_contexto(informe)
    lineas += _seccion_hallazgos(informe)
    lineas += _seccion_descartadas(informe)
    return "\n".join(lineas).rstrip() + "\n"


def _cabecera(informe):
    versiones = ", ".join(f"{v} ({n})" for v, n in informe.versiones.items()) or "ninguna"
    vias = ", ".join(f"{v}: {n}" for v, n in informe.vias.items()) or "ninguna"
    ventana = ", ".join(f"{k} {v}" for k, v in informe.ventana.items() if v) or "sin límites"
    return [
        f"- **Generado**: {informe.generado_en or 'sin fecha'}",
        f"- **Ventana**: {ventana}",
        f"- **Sesiones**: {len(informe.sesiones)} incluidas, {len(informe.descartadas)} descartadas",
        f"- **Versiones del patrón**: {versiones}",
        f"- **Vía de atribución**: {vias}",
        "",
    ]


def _seccion_avisos(informe):
    if not informe.avisos:
        return []
    return ["## Avisos", ""] + [f"- {aviso}" for aviso in informe.avisos] + [""]


def _seccion_coste(informe):
    total = coste(informe.total, informe.pesos)
    lineas = [
        "## Coste",
        "",
        f"Coste normalizado total: **{total:,.0f}** unidades en {informe.total.turnos} turnos.",
        "",
        "| Rol | Turnos | Coste | % | Lectura de caché | Salida |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rol, agregado in informe.coste_por_rol.items():
        parte = coste(agregado, informe.pesos)
        porcentaje = (parte / total * 100) if total else 0.0
        lineas.append(
            f"| {rol} | {agregado.turnos} | {parte:,.0f} | {porcentaje:.1f}% "
            f"| {agregado.lectura_cache:,} | {agregado.salida:,} |"
        )
    lineas += ["", "| Modelo | Turnos | Coste |", "| --- | ---: | ---: |"]
    for modelo, agregado in informe.coste_por_modelo.items():
        lineas.append(
            f"| {modelo} | {agregado.turnos} | {coste(agregado, informe.pesos):,.0f} |"
        )
    lineas += [
        "",
        f"Tokens de pensamiento declarados: **{informe.total.pensamiento:,}**.",
        "",
    ]
    return lineas


def _seccion_contexto(informe):
    lineas = [
        "## Contexto",
        "",
        "| Sesión | Versión | Rol | Turnos | Contexto máximo | Media | Prelude |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for sesion in informe.sesiones:
        for rol, curva in sesion.curvas.items():
            lineas.append(
                f"| {sesion.identificador[:8]} | {sesion.version or '?'} | {rol} "
                f"| {len(curva.puntos)} | {curva.maximo:,} | {curva.media:,.0f} "
                f"| {sesion.preludes.get(rol, 0):,} |"
            )
    lineas += ["", "| Clase de bloque | Turn-tokens |", "| --- | ---: |"]
    for clase, tokens in informe.turn_tokens.items():
        lineas.append(f"| {clase} | {tokens:,} |")
    lineas.append("")
    return lineas


def _seccion_hallazgos(informe):
    if not informe.hallazgos:
        return ["## Hallazgos", "", "Ninguno.", ""]
    severidades = ", ".join(f"{s}: {n}" for s, n in resumen_por_severidad(informe.hallazgos).items())
    lineas = ["## Hallazgos", "", f"{len(informe.hallazgos)} hallazgos ({severidades}).", ""]
    for categoria, hallazgos in agrupar(informe.hallazgos).items():
        subtotal = sum(h.tokens for h in hallazgos)
        lineas += [
            f"### {categoria} — {len(hallazgos)} hallazgos, {subtotal:,} turn-tokens",
            "",
        ]
        for hallazgo in hallazgos:
            lineas.append(
                f"- `{hallazgo.identificador}` **[{hallazgo.severidad}]** "
                f"{hallazgo.titulo} — {hallazgo.tokens:,} turn-tokens"
            )
            for evidencia in hallazgo.evidencias[:3]:
                lineas.append(
                    f"  - {evidencia.sesion or '?'} / {evidencia.rol or '?'} "
                    f"/ turno {evidencia.turno} — {evidencia.detalle or evidencia.fragmento or ''}"
                )
            if len(hallazgo.evidencias) > 3:
                lineas.append(f"  - … y {len(hallazgo.evidencias) - 3} evidencias más")
        lineas.append("")
    return lineas


def _seccion_descartadas(informe):
    if not informe.descartadas:
        return []
    motivos = {}
    for descartada in informe.descartadas:
        motivos[descartada["motivo"]] = motivos.get(descartada["motivo"], 0) + 1
    return (
        ["## Sesiones descartadas", ""]
        + [f"- {motivo}: {cuenta}" for motivo, cuenta in sorted(motivos.items())]
        + [""]
    )
