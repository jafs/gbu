"""Tests de la página HTML."""

import re
import unittest

from comparador import comparar
from pagina import generar


def _serie(rol, instantes, contexto=1000):
    return {
        "rol": rol,
        "puntos": [
            {
                "turno": i,
                "instante": instante,
                "contexto": contexto + i * 100,
                "salida": 10,
                "modelo": "claude-opus-5",
            }
            for i, instante in enumerate(instantes)
        ],
    }


def _informe(hallazgos=(), sesiones=None, versiones=None, avisos=()):
    return {
        "esquema": 1,
        "proyecto": "C:/proyectos/kdserver",
        "generado_en": "2026-08-18T17:00:00+00:00",
        "versiones": versiones if versiones is not None else {"0.1.0": 1},
        "avisos": list(avisos),
        "metricas": {
            "sesiones": 1,
            "turnos": 100,
            "coste_total": 1_000_000,
            "pensamiento": 500,
            "por_rol": {
                "sheriff": {"turnos": 80, "coste": 900_000, "lectura_cache": 5_000_000},
                "malo": {"turnos": 20, "coste": 100_000, "lectura_cache": 400_000},
            },
            "por_modelo": {"claude-opus-5": {"coste": 1_000_000}},
            "turn_tokens": {"texto": 500},
        },
        "sesiones": sesiones
        if sesiones is not None
        else [
            {
                "identificador": "aaaaaaaa-1111",
                "version": "0.1.0",
                "via": "marca",
                "coste": 1_000_000,
                "serie": [
                    _serie(
                        "sheriff",
                        [
                            "2026-08-16T13:00:00+00:00",
                            "2026-08-16T13:30:00+00:00",
                            "2026-08-16T14:00:00+00:00",
                        ],
                    ),
                    _serie("malo", ["2026-08-16T13:20:00+00:00", "2026-08-16T13:25:00+00:00"]),
                    _serie("malo", ["2026-08-16T13:50:00+00:00"]),
                ],
            }
        ],
        "hallazgos": list(hallazgos),
    }


def _hallazgo(identificador="relectura-abc", titulo="algo caro", tokens=1000, severidad="alta"):
    return {
        "identificador": identificador,
        "categoria": "relectura",
        "severidad": severidad,
        "titulo": titulo,
        "tokens": tokens,
    }


class TestAutocontenida(unittest.TestCase):
    def test_no_pide_ningun_recurso_externo(self):
        pagina = generar(_informe([_hallazgo()]))

        self.assertNotIn("http://", pagina)
        self.assertNotIn("https://", pagina)
        self.assertNotIn("<script", pagina)
        self.assertNotIn("<link", pagina)

    def test_es_una_pagina_completa(self):
        pagina = generar(_informe())

        self.assertTrue(pagina.startswith("<!doctype html>"))
        self.assertTrue(pagina.rstrip().endswith("</html>"))
        self.assertIn("<style>", pagina)
        self.assertIn("kdserver", pagina)


class TestSinComparacion(unittest.TestCase):
    def test_ensena_la_linea_de_tiempo_y_los_hallazgos_del_informe(self):
        pagina = generar(_informe([_hallazgo(titulo="fichero releído")]))

        self.assertIn("Línea de tiempo", pagina)
        self.assertIn("fichero releído", pagina)
        self.assertNotIn("Qué cambió", pagina)
        self.assertNotIn("Resueltos", pagina)

    def test_sin_hallazgos_lo_dice(self):
        pagina = generar(_informe())

        self.assertIn("Ninguno.", pagina)

    def test_una_banda_por_conversacion_no_por_rol(self):
        # Dos Malos son dos bandas: si se fundieran, la línea de tiempo
        # contaría una historia falsa.
        pagina = generar(_informe())

        self.assertEqual(pagina.count("<rect"), 2)
        self.assertIn("malo ×2", pagina)

    def test_dibuja_la_curva_del_rol_con_mas_turnos(self):
        pagina = generar(_informe())

        self.assertEqual(pagina.count("<polyline"), 1)

    def test_sin_sesiones(self):
        pagina = generar(_informe(sesiones=[]))

        self.assertIn("Sin sesiones que dibujar.", pagina)

    def test_serie_sin_instantes_no_revienta(self):
        sesion = {
            "identificador": "bbbb",
            "version": "0.1.0",
            "via": "marca",
            "coste": 10,
            "serie": [{"rol": "sheriff", "puntos": [{"turno": 0, "contexto": 100}]}],
        }

        pagina = generar(_informe(sesiones=[sesion]))

        self.assertIn("no hay eje que dibujar", pagina)

    def test_sesion_sin_serie(self):
        sesion = {"identificador": "cccc", "version": "0.1.0", "via": "marca", "coste": 0, "serie": []}

        pagina = generar(_informe(sesiones=[sesion]))

        self.assertIn("Sin serie que dibujar.", pagina)


class TestConComparacion(unittest.TestCase):
    def _pagina(self):
        antes = _informe([_hallazgo("a-1"), _hallazgo("a-2", tokens=500)], versiones={"0.1.0": 1})
        antes["metricas"]["coste_total"] = 1_000_000
        despues = _informe([_hallazgo("a-2", tokens=200), _hallazgo("a-3")], versiones={"0.2.0": 1})
        despues["metricas"]["coste_total"] = 700_000
        return generar(despues, comparacion=comparar(antes, despues), referencia=antes)

    def test_ensena_el_cuadro_de_variacion(self):
        pagina = self._pagina()

        self.assertIn("Qué cambió", pagina)
        self.assertIn("coste_total", pagina)
        self.assertIn("-30.0%", pagina)

    def test_marca_lo_que_mejora_y_lo_que_empeora(self):
        pagina = self._pagina()

        self.assertIn("class='mejor'", pagina)

    def test_reparte_los_hallazgos_en_tres_listas(self):
        pagina = self._pagina()

        for titulo in ("Resueltos", "Persistentes", "Nuevos"):
            self.assertIn(titulo, pagina)
        self.assertIn("a-1", pagina)
        self.assertIn("a-3", pagina)

    def test_el_subtitulo_dice_de_que_version_a_cual(self):
        pagina = self._pagina()

        self.assertIn("0.1.0 → 0.2.0", pagina)

    def test_los_avisos_de_la_comparacion_salen_arriba(self):
        antes = _informe(versiones={"0.1.0": 1})
        despues = _informe(versiones={"0.1.0": 1})

        pagina = generar(despues, comparacion=comparar(antes, despues), referencia=antes)

        self.assertIn("consigo misma", pagina)
        self.assertLess(pagina.index("consigo misma"), pagina.index("Resumen"))


class TestEscapado(unittest.TestCase):
    def test_los_textos_de_los_hallazgos_no_rompen_el_html(self):
        # Los títulos llevan fragmentos de ficheros y comandos del proyecto
        # analizado, así que pueden traer cualquier cosa.
        veneno = '<script>alert("x")</script> & <b>negrita</b>'

        pagina = generar(_informe([_hallazgo(titulo=veneno)]))

        self.assertNotIn("<script>", pagina)
        self.assertIn("&lt;script&gt;", pagina)
        self.assertIn("&amp;", pagina)

    def test_el_nombre_del_proyecto_tambien_se_escapa(self):
        informe = _informe()
        informe["proyecto"] = "C:/x/<img src=x onerror=1>"

        pagina = generar(informe)

        self.assertNotIn("<img", pagina)

    def test_los_avisos_se_escapan(self):
        pagina = generar(_informe(avisos=["cuidado con <esto>"]))

        self.assertIn("&lt;esto&gt;", pagina)

    def test_el_svg_no_queda_roto(self):
        pagina = generar(_informe([_hallazgo(titulo='"><rect x="0"')]))

        # Tantas aperturas de svg como cierres: el escapado no ha inyectado
        # etiquetas sueltas.
        self.assertEqual(len(re.findall(r"<svg", pagina)), len(re.findall(r"</svg>", pagina)))


if __name__ == "__main__":
    unittest.main()
