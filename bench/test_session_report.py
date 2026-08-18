"""Tests de la línea de comandos."""

import io
import json
import tempfile
import unittest
from pathlib import Path

from localizador import codificar_ruta
from session_report import main


def _evento_asistente(texto, identificador, contexto=1000):
    return {
        "type": "assistant",
        "timestamp": "2026-08-16T13:45:36.000Z",
        "message": {
            "role": "assistant",
            "id": f"msg-{identificador}",
            "model": "claude-opus-5",
            "usage": {
                "input_tokens": contexto,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "output_tokens": 20,
            },
            "content": [{"type": "text", "text": texto}],
        },
    }


class TestLineaDeComandos(unittest.TestCase):
    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporal.cleanup)
        self.raiz = Path(self._temporal.name)
        self.transcripts = self.raiz / "projects"
        self.archivo = self.raiz / "informes"
        self.proyecto = self.raiz / "kdserver"
        self.proyecto.mkdir()
        self.directorio = self.transcripts / codificar_ruta(self.proyecto)
        self.directorio.mkdir(parents=True)

    def _sesion(self, identificador, version="0.1.0", subagentes=()):
        eventos = [
            _evento_asistente(f"gbu v{version}", "m1"),
            _evento_asistente("x" * 4000, "m2"),
            _evento_asistente("fin", "m3"),
        ]
        fichero = self.directorio / f"{identificador}.jsonl"
        fichero.write_text(
            "\n".join(json.dumps(e) for e in eventos) + "\n", encoding="utf-8"
        )
        for nombre, tipo in subagentes:
            carpeta = self.directorio / identificador / "subagents"
            carpeta.mkdir(parents=True, exist_ok=True)
            (carpeta / f"agent-{nombre}.jsonl").write_text(
                json.dumps(_evento_asistente("atacando", "s1")) + "\n", encoding="utf-8"
            )
            (carpeta / f"agent-{nombre}.meta.json").write_text(
                json.dumps({"agentType": tipo, "model": "opus"}), encoding="utf-8"
            )
        return fichero

    def _ejecutar(self, *argv):
        salida = io.StringIO()
        # Ni `claude` ni `git` se invocan de verdad: la suite no debe
        # depender de que estén instalados.
        codigo = main(list(argv), salida=salida, ejecutar=lambda *_: None)
        return codigo, salida.getvalue()

    def _informe(self, *extra):
        return self._ejecutar(
            str(self.proyecto),
            "--transcripts",
            str(self.transcripts),
            "--archivo",
            str(self.archivo),
            *extra,
        )

    def test_modo_informe_archiva_json_y_markdown(self):
        self._sesion("aaa", subagentes=[("0011", "malo")])

        codigo, salida = self._informe()

        self.assertEqual(codigo, 0)
        destino = self.archivo / "kdserver" / "0.1.0.json"
        self.assertTrue(destino.exists())
        self.assertTrue(destino.with_suffix(".md").exists())
        self.assertIn("Informe archivado en", salida)
        self.assertIn("hallazgos", salida)

    def test_el_json_archivado_es_legible_y_trae_la_version(self):
        self._sesion("aaa")

        self._informe()

        datos = json.loads(
            (self.archivo / "kdserver" / "0.1.0.json").read_text(encoding="utf-8")
        )
        self.assertEqual(datos["versiones"], {"0.1.0": 1})
        self.assertEqual(len(datos["sesiones"]), 1)

    def test_un_informe_nuevo_no_pisa_el_anterior(self):
        self._sesion("aaa")

        self._informe()
        codigo, salida = self._informe()

        self.assertEqual(codigo, 0)
        self.assertTrue((self.archivo / "kdserver" / "0.1.0.json").exists())
        self.assertTrue((self.archivo / "kdserver" / "0.1.0-2.json").exists())
        self.assertIn("el anterior se conserva", salida)

    def test_escribe_la_pagina_html_si_se_pide(self):
        self._sesion("aaa")

        codigo, salida = self._informe("--html")

        pagina = self.archivo / "kdserver" / "0.1.0.html"
        self.assertEqual(codigo, 0)
        self.assertTrue(pagina.exists())
        self.assertIn("Página HTML en", salida)
        self.assertTrue(pagina.read_text(encoding="utf-8").startswith("<!doctype html>"))

    def test_sin_html_no_escribe_pagina(self):
        self._sesion("aaa")

        self._informe()

        self.assertFalse((self.archivo / "kdserver" / "0.1.0.html").exists())

    def test_filtra_por_version(self):
        self._sesion("aaa", version="0.1.0")
        self._sesion("bbb", version="0.2.0")

        self._informe("--version", "0.2.0")

        datos = json.loads(
            (self.archivo / "kdserver" / "0.2.0.json").read_text(encoding="utf-8")
        )
        self.assertEqual(datos["versiones"], {"0.2.0": 1})

    def test_proyecto_sin_sesiones_da_un_mensaje_entendible(self):
        codigo, salida = self._ejecutar(
            str(self.raiz / "otro"),
            "--transcripts",
            str(self.transcripts),
            "--archivo",
            str(self.archivo),
        )

        self.assertEqual(codigo, 1)
        self.assertIn("no tiene sesiones grabadas", salida)
        self.assertNotIn("Traceback", salida)

    def test_ninguna_sesion_en_la_ventana(self):
        self._sesion("aaa")

        codigo, salida = self._informe("--desde", "2030-01-01")

        self.assertEqual(codigo, 1)
        self.assertIn("entra en la ventana pedida", salida)

    def test_desde_que_no_es_ni_fecha_ni_commit(self):
        self._sesion("aaa")

        codigo, salida = self._informe("--desde", "ayer por la tarde")

        self.assertEqual(codigo, 1)
        self.assertIn("no es una fecha ISO ni un commit", salida)

    def test_argumentos_incompatibles(self):
        codigo, salida = self._ejecutar(str(self.proyecto), "--comparar", "kdserver")

        self.assertEqual(codigo, 1)
        self.assertIn("no se usan a la vez", salida)

    def test_sin_proyecto_ni_comparar(self):
        codigo, salida = self._ejecutar()

        self.assertEqual(codigo, 1)
        self.assertIn("hace falta la ruta de un proyecto", salida)


class TestModoComparar(unittest.TestCase):
    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporal.cleanup)
        self.archivo = Path(self._temporal.name) / "informes"
        self.directorio = self.archivo / "kdserver"
        self.directorio.mkdir(parents=True)

    def _archivar(self, version, coste=1_000_000, hallazgos=()):
        datos = {
            "esquema": 1,
            "proyecto": "kdserver",
            "versiones": {version: 3},
            "metricas": {
                "sesiones": 3,
                "turnos": 300,
                "coste_total": coste,
                "pensamiento": 0,
                "por_rol": {"sheriff": {"coste": coste}},
                "por_modelo": {"claude-opus-5": {"coste": coste}},
                "turn_tokens": {"texto": 100},
            },
            "hallazgos": [
                {
                    "identificador": h,
                    "categoria": "relectura",
                    "severidad": "alta",
                    "titulo": f"titulo {h}",
                    "tokens": 10,
                }
                for h in hallazgos
            ],
        }
        ruta = self.directorio / f"{version}.json"
        ruta.write_text(json.dumps(datos), encoding="utf-8")
        # El orden de archivo se resuelve por fecha de modificación, así que
        # se separan explícitamente para que la prueba no dependa de la
        # resolución del reloj del sistema de ficheros.
        import os
        import time

        marca = time.time() + len(list(self.directorio.glob("*.json")))
        os.utime(ruta, (marca, marca))
        return ruta

    def _ejecutar(self, *peticiones):
        salida = io.StringIO()
        codigo = main(
            ["--comparar", "kdserver", *peticiones, "--archivo", str(self.archivo)],
            salida=salida,
        )
        return codigo, salida.getvalue()

    def test_resuelve_las_dos_mas_recientes(self):
        self._archivar("0.1.0", coste=1_000_000, hallazgos=["a-1"])
        self._archivar("0.2.0", coste=800_000, hallazgos=["a-2"])

        codigo, salida = self._ejecutar()

        self.assertEqual(codigo, 0)
        self.assertIn("0.1.0.json", salida)
        self.assertIn("0.2.0.json", salida)
        self.assertIn("Resueltos", salida)

    def test_la_comparacion_tambien_puede_dar_pagina(self):
        self._archivar("0.1.0")
        self._archivar("0.2.0")

        codigo, salida = self._ejecutar("--html")

        self.assertEqual(codigo, 0)
        self.assertTrue((self.directorio / "0.2.0-vs-0.1.0.html").exists())
        self.assertIn("Página HTML en", salida)

    def test_compara_dos_versiones_no_consecutivas_pedidas_a_mano(self):
        self._archivar("0.1.0")
        self._archivar("0.2.0")
        self._archivar("0.3.0")

        codigo, salida = self._ejecutar("0.1.0", "0.3.0")

        self.assertEqual(codigo, 0)
        self.assertIn("0.1.0.json", salida)
        self.assertIn("0.3.0.json", salida)
        self.assertNotIn("0.2.0.json", salida)

    def test_acepta_rutas_de_fichero(self):
        primera = self._archivar("0.1.0")
        segunda = self._archivar("0.2.0")

        codigo, salida = self._ejecutar(str(primera), str(segunda))

        self.assertEqual(codigo, 0)
        self.assertIn("Comparación", salida)

    def test_version_que_no_existe_dice_cuales_hay(self):
        self._archivar("0.1.0")
        self._archivar("0.2.0")

        codigo, salida = self._ejecutar("0.1.0", "9.9.9")

        self.assertEqual(codigo, 1)
        self.assertIn("no hay ningún informe archivado de la versión 9.9.9", salida)
        self.assertIn("0.1.0", salida)

    def test_proyecto_sin_informes_archivados(self):
        codigo, salida = self._ejecutar()

        self.assertEqual(codigo, 1)
        self.assertIn("hacen falta dos informes", salida)

    def test_un_solo_informe_no_basta(self):
        self._archivar("0.1.0")

        codigo, salida = self._ejecutar()

        self.assertEqual(codigo, 1)
        self.assertIn("hay 1", salida)

    def test_numero_de_peticiones_invalido(self):
        self._archivar("0.1.0")

        codigo, salida = self._ejecutar("0.1.0")

        self.assertEqual(codigo, 1)
        self.assertIn("acepta el proyecto solo", salida)


if __name__ == "__main__":
    unittest.main()
