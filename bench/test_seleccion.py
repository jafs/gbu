"""Tests de la clasificación de sesiones y del filtro por versión y ventana."""

import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from eventos import conversacion_desde_eventos
from seleccion import (
    MOTIVO_FUERA_DE_VENTANA,
    MOTIVO_NO_GBU,
    MOTIVO_OTRA_VERSION,
    VERSION_POR_DEFECTO,
    VIA_DEFECTO,
    VIA_INSTALADA,
    VIA_MARCA,
    clasificar,
    es_de_gbu,
    fecha_de_commit,
    resolver_ventana,
    resolver_version,
    seleccionar,
    version_instalada,
    version_marcada,
)

_LISTADO = """Installed plugins:

  ❯ gbu@gbu
    Version: 0.2.3
    Scope: user
    Status: enabled
"""


class _Sesion:
    """Lo poco que el filtro necesita de una sesión."""

    def __init__(self, identificador, inicio=None, subagentes=()):
        self.identificador = identificador
        self.inicio = inicio
        self.subagentes = subagentes


class _Subagente:
    def __init__(self, tipo_agente):
        self.tipo_agente = tipo_agente


def _instante(texto):
    return datetime.fromisoformat(texto).replace(tzinfo=timezone.utc)


def _conversacion(textos, papel="assistant"):
    return conversacion_desde_eventos(
        [
            {
                "type": papel,
                "message": {
                    "role": "user" if papel == "user" else "assistant",
                    "id": f"m{i}",
                    "content": [{"type": "text", "text": texto}],
                },
            }
            for i, texto in enumerate(textos)
        ]
    )


class TestEsDeGbu(unittest.TestCase):
    def test_por_el_prompt_del_sheriff(self):
        self.assertTrue(es_de_gbu(_conversacion(["Eres el Sheriff.\n\nTu única..."], "user")))

    def test_por_los_subagentes(self):
        self.assertTrue(es_de_gbu(_conversacion(["nada que ver"]), ["malo"]))
        self.assertTrue(es_de_gbu(_conversacion(["nada que ver"]), ["gbu:feo"]))

    def test_por_la_marca_de_version(self):
        # La marca la escribe el propio patrón al arrancar, así que basta
        # por sí sola aunque no se vea el prompt ni haya subagentes.
        self.assertTrue(es_de_gbu(_conversacion(["gbu v0.1.0"])))

    def test_una_sesion_cualquiera_no_lo_es(self):
        self.assertFalse(es_de_gbu(_conversacion(["arregla este bug"]), ["general-purpose"]))


class TestVersionMarcada(unittest.TestCase):
    def test_lee_la_marca(self):
        self.assertEqual(version_marcada(_conversacion(["gbu v1.2.3", "..."])), "1.2.3")

    def test_sin_marca(self):
        self.assertIsNone(version_marcada(_conversacion(["hola"])))

    def test_se_queda_con_la_primera(self):
        self.assertEqual(version_marcada(_conversacion(["gbu v1.0.0", "gbu v9.9.9"])), "1.0.0")


class TestVersionInstalada(unittest.TestCase):
    def test_lee_el_listado_de_claude(self):
        self.assertEqual(version_instalada(ejecutar=lambda *_: _LISTADO), "0.2.3")

    def test_otro_plugin_no_cuenta(self):
        listado = _LISTADO.replace("gbu@gbu", "otro@otro")

        self.assertIsNone(version_instalada(ejecutar=lambda *_: listado))

    def test_claude_no_disponible(self):
        def explota(*_):
            raise OSError("no such file")

        self.assertIsNone(version_instalada(ejecutar=explota))

    def test_claude_falla(self):
        self.assertIsNone(version_instalada(ejecutar=lambda *_: None))


class TestResolverVersion(unittest.TestCase):
    def test_la_marca_manda_sobre_la_instalada(self):
        # Lo contrario fundiría dos versiones en una si el plugin se
        # actualizó a mitad de la ventana.
        version, via = resolver_version(_conversacion(["gbu v1.0.0"]), instalada="9.9.9")

        self.assertEqual((version, via), ("1.0.0", VIA_MARCA))

    def test_sin_marca_vale_la_instalada(self):
        version, via = resolver_version(_conversacion(["hola"]), instalada="0.2.0")

        self.assertEqual((version, via), ("0.2.0", VIA_INSTALADA))

    def test_sin_marca_ni_instalada_cae_al_defecto(self):
        version, via = resolver_version(_conversacion(["hola"]))

        self.assertEqual((version, via), (VERSION_POR_DEFECTO, VIA_DEFECTO))


class TestFechaDeCommit(unittest.TestCase):
    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporal.cleanup)
        self.repositorio = Path(self._temporal.name)
        fecha = "2026-08-16T13:45:36+02:00"
        entorno = {
            "GIT_AUTHOR_DATE": fecha,
            "GIT_COMMITTER_DATE": fecha,
            "GIT_AUTHOR_NAME": "prueba",
            "GIT_AUTHOR_EMAIL": "prueba@example.com",
            "GIT_COMMITTER_NAME": "prueba",
            "GIT_COMMITTER_EMAIL": "prueba@example.com",
        }
        self._git(["init", "-q"])
        (self.repositorio / "a.txt").write_text("hola", encoding="utf-8")
        self._git(["add", "a.txt"])
        self._git(["commit", "-q", "-m", "primero"], entorno)
        self.commit = self._git(["rev-parse", "HEAD"]).strip()

    def _git(self, orden, entorno=None):
        import os

        completo = dict(os.environ)
        completo.update(entorno or {})
        resultado = subprocess.run(
            ["git", "-C", str(self.repositorio)] + orden,
            capture_output=True,
            text=True,
            env=completo,
        )
        return resultado.stdout

    def test_resuelve_un_commit_real(self):
        instante = fecha_de_commit(self.repositorio, self.commit)

        self.assertIsNotNone(instante)
        self.assertEqual(instante.astimezone(timezone.utc).hour, 11)

    def test_commit_inexistente(self):
        self.assertIsNone(fecha_de_commit(self.repositorio, "0" * 40))

    def test_ventana_desde_commit(self):
        desde, hasta = resolver_ventana(
            ruta_repositorio=self.repositorio, commit=self.commit
        )

        self.assertIsNotNone(desde)
        self.assertIsNone(hasta)

    def test_ventana_con_commit_inexistente_falla(self):
        with self.assertRaises(ValueError):
            resolver_ventana(ruta_repositorio=self.repositorio, commit="0" * 40)


class TestResolverVentana(unittest.TestCase):
    def test_fechas_iso(self):
        desde, hasta = resolver_ventana(desde="2026-08-16", hasta="2026-08-18T23:59:59Z")

        self.assertEqual(desde.year, 2026)
        self.assertEqual(hasta.day, 18)

    def test_sin_limites(self):
        self.assertEqual(resolver_ventana(), (None, None))

    def test_el_commit_manda_sobre_la_fecha(self):
        desde, _ = resolver_ventana(
            desde="1999-01-01",
            ruta_repositorio="/lo/que/sea",
            commit="abc",
            ejecutar=lambda *_: "2026-08-16T13:45:36+02:00\n",
        )

        self.assertEqual(desde.year, 2026)


class TestSeleccionar(unittest.TestCase):
    def _clasificada(self, identificador, inicio, textos, subagentes=(), instalada=None):
        return clasificar(
            _Sesion(identificador, _instante(inicio), subagentes),
            _conversacion(textos),
            instalada=instalada,
        )

    def test_descarta_las_que_no_son_de_gbu(self):
        clasificada = self._clasificada("x", "2026-08-16T12:00:00", ["arregla el bug"])

        seleccion = seleccionar([clasificada])

        self.assertEqual(seleccion.incluidas, ())
        self.assertEqual(seleccion.descartadas[0].motivo, MOTIVO_NO_GBU)

    def test_filtra_por_ventana(self):
        dentro = self._clasificada("dentro", "2026-08-17T12:00:00", ["gbu v0.1.0"])
        antes = self._clasificada("antes", "2026-08-15T12:00:00", ["gbu v0.1.0"])

        seleccion = seleccionar([dentro, antes], desde=_instante("2026-08-16T00:00:00"))

        self.assertEqual([c.identificador for c in seleccion.incluidas], ["dentro"])
        self.assertEqual(seleccion.descartadas[0].motivo, MOTIVO_FUERA_DE_VENTANA)

    def test_filtra_por_version(self):
        vieja = self._clasificada("vieja", "2026-08-17T12:00:00", ["gbu v0.1.0"])
        nueva = self._clasificada("nueva", "2026-08-17T13:00:00", ["gbu v0.2.0"])

        seleccion = seleccionar([vieja, nueva], version="0.2.0")

        self.assertEqual([c.identificador for c in seleccion.incluidas], ["nueva"])
        self.assertEqual(seleccion.descartadas[0].motivo, MOTIVO_OTRA_VERSION)

    def test_avisa_de_versiones_mezcladas(self):
        vieja = self._clasificada("vieja", "2026-08-17T12:00:00", ["gbu v0.1.0"])
        nueva = self._clasificada("nueva", "2026-08-17T13:00:00", ["gbu v0.2.0"])

        seleccion = seleccionar([vieja, nueva])

        self.assertEqual(seleccion.versiones, {"0.1.0": 1, "0.2.0": 1})
        self.assertTrue(any("mezcla varias versiones" in a for a in seleccion.avisos))

    def test_avisa_de_versiones_supuestas(self):
        sin_marca = self._clasificada(
            "sin-marca", "2026-08-17T12:00:00", ["Eres el Sheriff."], instalada="0.2.0"
        )

        seleccion = seleccionar([sin_marca])

        self.assertEqual(seleccion.vias, {VIA_INSTALADA: 1})
        self.assertTrue(any("no llevaban marca" in a for a in seleccion.avisos))

    def test_una_ventana_limpia_no_avisa(self):
        una = self._clasificada("una", "2026-08-17T12:00:00", ["gbu v0.2.0"])
        otra = self._clasificada("otra", "2026-08-17T13:00:00", ["gbu v0.2.0"])

        seleccion = seleccionar([una, otra])

        self.assertEqual(seleccion.avisos, ())
        self.assertEqual(seleccion.versiones, {"0.2.0": 2})

    def test_sesion_sin_instante_queda_fuera_de_cualquier_ventana(self):
        clasificada = clasificar(_Sesion("sin-fecha"), _conversacion(["gbu v0.1.0"]))

        seleccion = seleccionar([clasificada], desde=_instante("2026-08-16T00:00:00"))

        self.assertEqual(seleccion.descartadas[0].motivo, MOTIVO_FUERA_DE_VENTANA)

    def test_los_subagentes_bastan_para_reconocer_la_sesion(self):
        clasificada = clasificar(
            _Sesion("s", _instante("2026-08-17T12:00:00"), [_Subagente("gbu:malo")]),
            _conversacion(["nada reconocible"]),
        )

        self.assertTrue(clasificada.es_gbu)
        self.assertEqual(clasificada.via, VIA_DEFECTO)

    def test_sin_sesiones(self):
        seleccion = seleccionar([])

        self.assertEqual(seleccion.incluidas, ())
        self.assertEqual(seleccion.avisos, ())


if __name__ == "__main__":
    unittest.main()
