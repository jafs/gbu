"""Tests del localizador de sesiones."""

import json
import tempfile
import unittest
from datetime import timezone
from pathlib import Path

from localizador import (
    Sesion,
    codificar_ruta,
    directorio_de_transcripts,
    localizar_sesiones,
)


def _linea(instante, texto="hola"):
    return json.dumps({"type": "user", "timestamp": instante, "texto": texto}) + "\n"


class TestCodificarRuta(unittest.TestCase):
    def test_ruta_de_windows(self):
        codificada = codificar_ruta(r"C:\Users\joanf\Proyectos\kdserver")
        self.assertEqual(codificada, "C--Users-joanf-Proyectos-kdserver")

    def test_sustituye_todo_lo_no_alfanumerico(self):
        # Los puntos y los guiones bajos también se sustituyen, no solo los
        # separadores: es lo que hace Claude Code al nombrar el directorio.
        codificada = codificar_ruta(r"C:\tmp\mi_proyecto.v2")
        self.assertTrue(codificada.endswith("mi-proyecto-v2"))
        self.assertNotIn("_", codificada)
        self.assertNotIn(".", codificada)

    def test_es_indiferente_a_la_barra_final(self):
        self.assertEqual(
            codificar_ruta(r"C:\Users\joanf\Proyectos\kdserver"),
            codificar_ruta("C:/Users/joanf/Proyectos/kdserver/"),
        )


class TestLocalizarSesiones(unittest.TestCase):
    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporal.cleanup)
        self.raiz = Path(self._temporal.name) / "projects"
        self.proyecto = Path(self._temporal.name) / "proyecto"
        self.proyecto.mkdir()
        self.transcripts = self.raiz / codificar_ruta(self.proyecto)
        self.transcripts.mkdir(parents=True)

    def _escribir_sesion(self, identificador, instantes):
        fichero = self.transcripts / f"{identificador}.jsonl"
        fichero.write_text(
            "".join(_linea(i) for i in instantes), encoding="utf-8"
        )
        return fichero

    def _escribir_subagente(self, sesion, identificador, tipo):
        directorio = self.transcripts / sesion / "subagents"
        directorio.mkdir(parents=True, exist_ok=True)
        (directorio / f"agent-{identificador}.jsonl").write_text(
            _linea("2026-08-16T14:00:00.000Z"), encoding="utf-8"
        )
        if tipo is not None:
            (directorio / f"agent-{identificador}.meta.json").write_text(
                json.dumps({"agentType": tipo, "spawnDepth": 1}), encoding="utf-8"
            )
        return directorio

    def test_directorio_de_transcripts_cuelga_de_la_raiz(self):
        esperado = self.raiz / codificar_ruta(self.proyecto)
        self.assertEqual(
            directorio_de_transcripts(self.proyecto, self.raiz), esperado
        )

    def test_sesion_con_subagentes(self):
        self._escribir_sesion(
            "aaa", ["2026-08-16T13:45:36.000Z", "2026-08-16T15:10:00.000Z"]
        )
        self._escribir_subagente("aaa", "0011", "malo")
        self._escribir_subagente("aaa", "0022", "feo")

        sesiones = localizar_sesiones(self.proyecto, self.raiz)

        self.assertEqual(len(sesiones), 1)
        sesion = sesiones[0]
        self.assertEqual(sesion.identificador, "aaa")
        self.assertEqual(
            [s.identificador for s in sesion.subagentes], ["0011", "0022"]
        )
        self.assertEqual([s.tipo_agente for s in sesion.subagentes], ["malo", "feo"])
        self.assertEqual(sesion.tamano, sesion.fichero.stat().st_size)
        self.assertEqual(
            sesion.tamano_total,
            sesion.tamano + sum(s.tamano for s in sesion.subagentes),
        )

    def test_sesion_sin_subagentes(self):
        self._escribir_sesion("bbb", ["2026-08-16T13:45:36.000Z"])

        (sesion,) = localizar_sesiones(self.proyecto, self.raiz)

        self.assertEqual(sesion.subagentes, ())

    def test_subagente_sin_meta_json(self):
        self._escribir_sesion("ccc", ["2026-08-16T13:45:36.000Z"])
        self._escribir_subagente("ccc", "0033", None)

        (sesion,) = localizar_sesiones(self.proyecto, self.raiz)

        self.assertEqual(len(sesion.subagentes), 1)
        self.assertIsNone(sesion.subagentes[0].tipo_agente)

    def test_meta_json_corrupto_no_aborta(self):
        self._escribir_sesion("ddd", ["2026-08-16T13:45:36.000Z"])
        directorio = self._escribir_subagente("ddd", "0044", "malo")
        (directorio / "agent-0044.meta.json").write_text("{no es json", encoding="utf-8")

        (sesion,) = localizar_sesiones(self.proyecto, self.raiz)

        self.assertIsNone(sesion.subagentes[0].tipo_agente)

    def test_instantes_de_inicio_y_fin(self):
        self._escribir_sesion(
            "eee", ["2026-08-16T13:45:36.000Z", "2026-08-16T15:10:00.000Z"]
        )

        (sesion,) = localizar_sesiones(self.proyecto, self.raiz)

        self.assertEqual(sesion.inicio.astimezone(timezone.utc).hour, 13)
        self.assertEqual(sesion.fin.astimezone(timezone.utc).hour, 15)
        self.assertEqual(sesion.inicio.tzinfo.utcoffset(sesion.inicio).total_seconds(), 0)

    def test_lineas_corruptas_y_sin_timestamp_no_abortan(self):
        fichero = self.transcripts / "fff.jsonl"
        fichero.write_text(
            "{a medio escribir\n"
            + json.dumps({"type": "system"})
            + "\n"
            + _linea("2026-08-16T13:45:36.000Z")
            + "\n"
            + _linea("no es una fecha"),
            encoding="utf-8",
        )

        (sesion,) = localizar_sesiones(self.proyecto, self.raiz)

        # El único timestamp legible es a la vez el primero y el último.
        self.assertIsNotNone(sesion.inicio)
        self.assertEqual(sesion.inicio, sesion.fin)

    def test_sesion_sin_ningun_timestamp(self):
        self.transcripts.joinpath("ggg.jsonl").write_text("", encoding="utf-8")

        (sesion,) = localizar_sesiones(self.proyecto, self.raiz)

        self.assertIsNone(sesion.inicio)
        self.assertIsNone(sesion.fin)

    def test_orden_cronologico_y_sesiones_sin_fecha_al_final(self):
        self._escribir_sesion("tarde", ["2026-08-17T09:00:00.000Z"])
        self._escribir_sesion("pronto", ["2026-08-16T09:00:00.000Z"])
        self.transcripts.joinpath("sin-fecha.jsonl").write_text("", encoding="utf-8")

        sesiones = localizar_sesiones(self.proyecto, self.raiz)

        self.assertEqual(
            [s.identificador for s in sesiones], ["pronto", "tarde", "sin-fecha"]
        )

    def test_proyecto_sin_directorio_de_transcripts(self):
        with self.assertRaises(FileNotFoundError):
            localizar_sesiones(Path(self._temporal.name) / "otro", self.raiz)

    def test_proyecto_con_directorio_vacio(self):
        # Tener el directorio y no tener sesiones es un caso legítimo: no es
        # un error, es un proyecto en el que aún no se ha trabajado.
        self.assertEqual(localizar_sesiones(self.proyecto, self.raiz), [])

    def test_no_escribe_en_el_directorio_de_transcripts(self):
        self._escribir_sesion("hhh", ["2026-08-16T13:45:36.000Z"])
        antes = sorted(p.name for p in self.transcripts.rglob("*"))

        localizar_sesiones(self.proyecto, self.raiz)

        self.assertEqual(sorted(p.name for p in self.transcripts.rglob("*")), antes)

    def test_devuelve_sesiones(self):
        self._escribir_sesion("iii", ["2026-08-16T13:45:36.000Z"])

        (sesion,) = localizar_sesiones(self.proyecto, self.raiz)

        self.assertIsInstance(sesion, Sesion)


if __name__ == "__main__":
    unittest.main()
