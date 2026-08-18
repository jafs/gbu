"""Pinta un informe —o la comparación de dos— como una página autocontenida.

La página no calcula nada. Dibuja lo que los pasos anteriores ya
decidieron: si un dato no está en el JSON, no aparece. Esa regla es lo que
mantiene honesta la presentación, porque una gráfica siempre parece más
cierta que la tabla de la que salió.

Es un solo fichero, sin dependencias ni recursos remotos: el SVG se genera
aquí y el CSS va dentro. Se puede abrir sin conexión y se puede mandar por
correo.

La línea de tiempo va sobre el reloj, no sobre el número de turno: es la
única forma de poner en el mismo eje al Sheriff y a unos subagentes que
llevan su propia numeración. Cada conversación es una banda; una sesión
con ocho Malos enseña ocho.
"""

import html as _html
from datetime import datetime

# Colores por rol. Se eligen aquí y no en el CSS porque el SVG los
# necesita como atributos.
_COLORES = {
    "sheriff": "#b5651d",
    "malo": "#8b2f2f",
    "feo": "#4a6d8c",
}
_COLOR_POR_DEFECTO = "#6b6b6b"

_ANCHO = 900
_ALTO_CURVA = 180
_ALTO_BANDA = 14
_MARGEN = 40

_ESTILOS = """
:root { color-scheme: light dark; }
body {
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  margin: 0 auto; padding: 2rem 1.5rem; max-width: 1000px; line-height: 1.5;
  background: #fbfaf8; color: #23201d;
}
h1 { font-size: 1.7rem; margin: 0 0 .2rem; }
h2 { font-size: 1.25rem; margin: 2.2rem 0 .8rem; border-bottom: 1px solid #ddd6cc; padding-bottom: .3rem; }
h3 { font-size: 1rem; margin: 1.4rem 0 .5rem; }
.sub { color: #6b6259; margin: 0 0 1.5rem; }
.avisos { background: #fdf3e0; border-left: 4px solid #d99b3d; padding: .8rem 1rem; margin: 1rem 0; }
.avisos p { margin: .3rem 0; }
.tarjetas { display: flex; flex-wrap: wrap; gap: .8rem; margin: 1rem 0; }
.tarjeta { background: #fff; border: 1px solid #e6e0d6; border-radius: 6px; padding: .7rem 1rem; min-width: 8rem; }
.tarjeta .valor { font-size: 1.4rem; font-weight: 600; }
.tarjeta .clave { color: #6b6259; font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; }
table { border-collapse: collapse; width: 100%; margin: .5rem 0 1rem; font-size: .92rem; }
th, td { text-align: left; padding: .35rem .6rem; border-bottom: 1px solid #ece6dc; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.mejor { color: #2f6b3f; font-weight: 600; }
.peor { color: #97341f; font-weight: 600; }
.sesion { background: #fff; border: 1px solid #e6e0d6; border-radius: 6px; padding: 1rem; margin: 1rem 0; overflow-x: auto; }
.leyenda { font-size: .85rem; color: #6b6259; }
.leyenda span { margin-right: 1rem; }
.punto { display: inline-block; width: .7rem; height: .7rem; border-radius: 2px; vertical-align: middle; margin-right: .3rem; }
ul.hallazgos { list-style: none; padding: 0; }
ul.hallazgos li { border-bottom: 1px solid #ece6dc; padding: .45rem 0; }
code { background: #f0ebe3; padding: .05rem .3rem; border-radius: 3px; font-size: .85em; }
.alta { border-left: 3px solid #97341f; padding-left: .6rem; }
.media { border-left: 3px solid #d99b3d; padding-left: .6rem; }
.baja { border-left: 3px solid #c9c2b6; padding-left: .6rem; }
.vacio { color: #6b6259; font-style: italic; }
@media (prefers-color-scheme: dark) {
  body { background: #1a1815; color: #e8e2d9; }
  .tarjeta, .sesion { background: #232019; border-color: #3a352c; }
  h2 { border-color: #3a352c; }
  th, td, ul.hallazgos li { border-color: #322d25; }
  .avisos { background: #2e2617; border-color: #d99b3d; }
  code { background: #2c2820; }
  .sub, .leyenda, .tarjeta .clave, .vacio { color: #a89f93; }
}
"""


def generar(informe, comparacion=None, referencia=None):
    """Devuelve la página completa.

    `informe` es el JSON del informe nuevo, ya cargado. `comparacion` es lo
    que devolvió el comparador, y `referencia` el JSON contra el que se
    comparó. Sin comparación, la página enseña solo la línea de tiempo y
    los hallazgos de un informe.
    """
    partes = [
        "<!doctype html>",
        '<html lang="es"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{_t(_titulo(informe))}</title>",
        f"<style>{_ESTILOS}</style></head><body>",
        f"<h1>{_t(_titulo(informe))}</h1>",
        f'<p class="sub">{_t(_subtitulo(informe, referencia))}</p>',
    ]
    partes += _avisos(informe, comparacion)
    partes += _resumen(informe)
    if comparacion is not None:
        partes += _comparacion(comparacion)
        partes += _hallazgos_comparados(comparacion)
    else:
        partes += _hallazgos(informe)
    partes += _timeline(informe)
    partes.append("</body></html>")
    return "\n".join(partes)


def _titulo(informe):
    proyecto = informe.get("proyecto") or "proyecto"
    return f"Coste de gbu — {proyecto}"


def _subtitulo(informe, referencia):
    versiones = ", ".join(sorted(informe.get("versiones") or {})) or "sin versión"
    generado = informe.get("generado_en") or "sin fecha"
    if referencia:
        anteriores = ", ".join(sorted(referencia.get("versiones") or {})) or "?"
        return f"versión {anteriores} → {versiones} · generado {generado}"
    return f"versión {versiones} · generado {generado}"


def _avisos(informe, comparacion):
    avisos = list(informe.get("avisos") or [])
    if comparacion is not None:
        avisos = list(comparacion.avisos) + avisos
    if not avisos:
        return []
    return ['<div class="avisos">'] + [f"<p>⚠ {_t(a)}</p>" for a in avisos] + ["</div>"]


def _resumen(informe):
    metricas = informe.get("metricas") or {}
    tarjetas = [
        ("sesiones", _numero(metricas.get("sesiones"))),
        ("turnos", _numero(metricas.get("turnos"))),
        ("coste normalizado", _numero(metricas.get("coste_total"))),
        ("hallazgos", _numero(len(informe.get("hallazgos") or []))),
        ("pensamiento", _numero(metricas.get("pensamiento"))),
    ]
    partes = ["<h2>Resumen</h2>", '<div class="tarjetas">']
    for clave, valor in tarjetas:
        partes.append(
            f'<div class="tarjeta"><div class="valor">{_t(valor)}</div>'
            f'<div class="clave">{_t(clave)}</div></div>'
        )
    partes.append("</div>")

    por_rol = metricas.get("por_rol") or {}
    if por_rol:
        total = _flotante(metricas.get("coste_total"))
        partes += [
            "<h3>Por rol</h3>",
            "<table><tr><th>Rol</th><th class='num'>Turnos</th>"
            "<th class='num'>Coste</th><th class='num'>%</th>"
            "<th class='num'>Lectura de caché</th></tr>",
        ]
        for rol, datos in por_rol.items():
            parte = _flotante(datos.get("coste"))
            porcentaje = (parte / total * 100) if total else 0.0
            partes.append(
                f"<tr><td>{_t(rol)}</td><td class='num'>{_numero(datos.get('turnos'))}</td>"
                f"<td class='num'>{_numero(parte)}</td><td class='num'>{porcentaje:.1f}%</td>"
                f"<td class='num'>{_numero(datos.get('lectura_cache'))}</td></tr>"
            )
        partes.append("</table>")
    return partes


def _comparacion(comparacion):
    partes = [
        "<h2>Qué cambió</h2>",
        "<table><tr><th>Métrica</th><th class='num'>Antes</th>"
        "<th class='num'>Después</th><th class='num'>Variación</th>"
        "<th class='num'>%</th></tr>",
    ]
    for variacion in comparacion.metricas:
        clase = "" if variacion.mejora is None else (" class='mejor'" if variacion.mejora else " class='peor'")
        porcentaje = "—" if variacion.porcentaje is None else f"{variacion.porcentaje:+.1f}%"
        partes.append(
            f"<tr><td{clase}>{_t(variacion.nombre)}</td>"
            f"<td class='num'>{_numero(variacion.antes)}</td>"
            f"<td class='num'>{_numero(variacion.despues)}</td>"
            f"<td class='num'>{variacion.absoluta:+,.0f}</td>"
            f"<td class='num'>{_t(porcentaje)}</td></tr>"
        )
    partes.append("</table>")
    return partes


def _hallazgos_comparados(comparacion):
    partes = ["<h2>Hallazgos</h2>"]
    for titulo, lista, describir in (
        ("Resueltos", comparacion.resueltos, lambda h: f"costaban {h.antes:,} turn-tokens"),
        (
            "Persistentes",
            sorted(comparacion.persistentes, key=lambda h: -abs(h.absoluta)),
            lambda h: f"{h.antes:,} → {h.despues:,} ({h.absoluta:+,})",
        ),
        ("Nuevos", comparacion.nuevos, lambda h: f"{h.despues:,} turn-tokens"),
    ):
        partes.append(f"<h3>{_t(titulo)} — {len(lista)}</h3>")
        if not lista:
            partes.append('<p class="vacio">Ninguno.</p>')
            continue
        partes.append('<ul class="hallazgos">')
        for hallazgo in lista:
            partes.append(
                f'<li class="{_t(hallazgo.severidad or "baja")}">'
                f"<code>{_t(hallazgo.identificador)}</code> {_t(hallazgo.titulo)} "
                f"— {_t(describir(hallazgo))}</li>"
            )
        partes.append("</ul>")
    return partes


def _hallazgos(informe):
    hallazgos = informe.get("hallazgos") or []
    partes = [f"<h2>Hallazgos — {len(hallazgos)}</h2>"]
    if not hallazgos:
        partes.append('<p class="vacio">Ninguno.</p>')
        return partes
    por_categoria = {}
    for hallazgo in hallazgos:
        por_categoria.setdefault(hallazgo.get("categoria", "?"), []).append(hallazgo)
    for categoria, lista in sorted(
        por_categoria.items(), key=lambda par: -sum(h.get("tokens", 0) for h in par[1])
    ):
        subtotal = sum(h.get("tokens", 0) for h in lista)
        partes.append(f"<h3>{_t(categoria)} — {len(lista)}, {_numero(subtotal)} turn-tokens</h3>")
        partes.append('<ul class="hallazgos">')
        for hallazgo in lista:
            partes.append(
                f'<li class="{_t(hallazgo.get("severidad", "baja"))}">'
                f'<code>{_t(hallazgo.get("identificador", ""))}</code> '
                f'{_t(hallazgo.get("titulo", ""))} — {_numero(hallazgo.get("tokens"))} turn-tokens</li>'
            )
        partes.append("</ul>")
    return partes


def _timeline(informe):
    sesiones = informe.get("sesiones") or []
    partes = ["<h2>Línea de tiempo</h2>"]
    if not sesiones:
        partes.append('<p class="vacio">Sin sesiones que dibujar.</p>')
        return partes
    partes.append(
        '<p class="leyenda">El eje horizontal es el reloj, no el número de turno: '
        "es lo que permite poner en la misma escala al Sheriff y a unos subagentes "
        "con su propia numeración. La curva es el contexto de cada turno.</p>"
    )
    for sesion in sesiones:
        partes += _sesion(sesion)
    return partes


def _sesion(sesion):
    series = [s for s in (sesion.get("serie") or []) if s.get("puntos")]
    cabecera = (
        f'<div class="sesion"><h3>{_t(sesion.get("identificador", "")[:8])} '
        f'— versión {_t(sesion.get("version") or "?")} '
        f'({_t(sesion.get("via") or "?")}), {_numero(sesion.get("coste"))} unidades</h3>'
    )
    if not series:
        return [cabecera, '<p class="vacio">Sin serie que dibujar.</p>', "</div>"]
    return [cabecera, _svg(series), _leyenda(series), "</div>"]


def _svg(series):
    instantes = [
        _segundos(punto.get("instante"))
        for serie in series
        for punto in serie["puntos"]
        if _segundos(punto.get("instante")) is not None
    ]
    contextos = [punto.get("contexto") or 0 for serie in series for punto in serie["puntos"]]
    if not instantes or not contextos:
        return '<p class="vacio">Los turnos no traen instante: no hay eje que dibujar.</p>'

    inicio, fin = min(instantes), max(instantes)
    techo = max(contextos) or 1
    bandas = [s for s in series if s.get("rol") != _rol_principal(series)]
    alto = _ALTO_CURVA + _MARGEN + max(1, len(bandas)) * (_ALTO_BANDA + 4) + 20

    piezas = [
        f'<svg viewBox="0 0 {_ANCHO} {alto}" width="100%" height="{alto}" '
        'role="img" aria-label="Contexto a lo largo de la sesión">'
    ]
    piezas.append(
        f'<line x1="{_MARGEN}" y1="{_ALTO_CURVA}" x2="{_ANCHO - 10}" y2="{_ALTO_CURVA}" '
        'stroke="#c9c2b6" stroke-width="1"/>'
    )
    piezas.append(
        f'<text x="{_MARGEN}" y="14" font-size="11" fill="#6b6259">'
        f"máximo {techo:,} tokens de contexto</text>"
    )

    principal = _rol_principal(series)
    for serie in series:
        color = _COLORES.get(serie.get("rol"), _COLOR_POR_DEFECTO)
        if serie.get("rol") == principal:
            puntos = " ".join(
                f"{_x(_segundos(p.get('instante')), inicio, fin):.1f},"
                f"{_y(p.get('contexto') or 0, techo):.1f}"
                for p in serie["puntos"]
                if _segundos(p.get("instante")) is not None
            )
            piezas.append(
                f'<polyline points="{puntos}" fill="none" stroke="{color}" stroke-width="2"/>'
            )
    for numero, serie in enumerate(bandas):
        color = _COLORES.get(serie.get("rol"), _COLOR_POR_DEFECTO)
        marcas = [
            _x(_segundos(p.get("instante")), inicio, fin)
            for p in serie["puntos"]
            if _segundos(p.get("instante")) is not None
        ]
        if not marcas:
            continue
        y = _ALTO_CURVA + 24 + numero * (_ALTO_BANDA + 4)
        ancho = max(2.0, max(marcas) - min(marcas))
        piezas.append(
            f'<rect x="{min(marcas):.1f}" y="{y}" width="{ancho:.1f}" height="{_ALTO_BANDA}" '
            f'fill="{color}" opacity="0.75" rx="3"><title>{_t(serie.get("rol", ""))}: '
            f'{len(serie["puntos"])} turnos</title></rect>'
        )
    piezas.append("</svg>")
    return "".join(piezas)


def _leyenda(series):
    vistos = []
    for serie in series:
        rol = serie.get("rol")
        if rol not in vistos:
            vistos.append(rol)
    partes = ['<p class="leyenda">']
    for rol in vistos:
        color = _COLORES.get(rol, _COLOR_POR_DEFECTO)
        cuantas = sum(1 for s in series if s.get("rol") == rol)
        sufijo = f" ×{cuantas}" if cuantas > 1 else ""
        partes.append(
            f'<span><i class="punto" style="background:{color}"></i>{_t(str(rol))}{sufijo}</span>'
        )
    partes.append("</p>")
    return "".join(partes)


def _rol_principal(series):
    """El rol que lleva la curva: el que más turnos tiene.

    Se deduce y no se fija a "sheriff" porque un informe puede venir de un
    proyecto con otros nombres de rol.
    """
    return max(series, key=lambda s: len(s["puntos"])).get("rol")


def _x(segundos, inicio, fin):
    if segundos is None:
        return _MARGEN
    if fin == inicio:
        return _MARGEN
    ancho = _ANCHO - _MARGEN - 10
    return _MARGEN + (segundos - inicio) / (fin - inicio) * ancho


def _y(contexto, techo):
    alto = _ALTO_CURVA - 20
    return _ALTO_CURVA - (contexto / techo) * alto


def _segundos(texto):
    if not isinstance(texto, str):
        return None
    limpio = texto[:-1] + "+00:00" if texto.endswith("Z") else texto
    try:
        return datetime.fromisoformat(limpio).timestamp()
    except ValueError:
        return None


def _numero(valor):
    if isinstance(valor, (int, float)):
        return f"{valor:,.0f}"
    return "0"


def _flotante(valor):
    return float(valor) if isinstance(valor, (int, float)) else 0.0


def _t(texto):
    """Escapa lo que venga del informe.

    Los títulos de los hallazgos llevan fragmentos de ficheros y comandos
    del proyecto analizado, así que pueden traer cualquier cosa.
    """
    return _html.escape(str(texto), quote=True)
