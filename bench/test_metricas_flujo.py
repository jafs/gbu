"""Tests de las métricas de flujo: pasos, lanzamientos y reloj de pared."""

import unittest

from eventos import conversacion_desde_eventos
from metricas_coste import SHERIFF, Participante
from metricas_flujo import (
    MARCA_PASO,
    Flujo,
    contar_pasos,
    duracion,
    medir_flujo,
    sumar_flujos,
)


def _asistente(texto, instante=None, identificador=None):
    evento = {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": texto}]},
    }
    if identificador is not None:
        evento["message"]["id"] = identificador
    if instante is not None:
        evento["timestamp"] = instante
    return evento


def _pensamiento(texto):
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{"type": "thinking", "thinking": texto}],
        },
    }


def _resultado_de_herramienta(texto):
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": texto}
            ],
        },
    }


def _conversacion(eventos):
    return conversacion_desde_eventos(eventos)


class TestContarPasos(unittest.TestCase):
    def test_cuenta_las_marcas_del_texto_del_asistente(self):
        conversacion = _conversacion(
            [
                _asistente(f"{MARCA_PASO} — cerrado el subpaso 1.1", identificador="m1"),
                _asistente("sigo con el siguiente", identificador="m2"),
                _asistente(f"{MARCA_PASO} — cerrado el subpaso 1.2", identificador="m3"),
            ]
        )

        self.assertEqual(contar_pasos(conversacion), 2)

    def test_la_marca_en_el_pensamiento_no_cuenta(self):
        conversacion = _conversacion([_pensamiento(f"voy a declarar {MARCA_PASO}")])

        self.assertEqual(contar_pasos(conversacion), 0)

    def test_la_marca_en_un_resultado_de_herramienta_no_cuenta(self):
        conversacion = _conversacion([_resultado_de_herramienta(MARCA_PASO)])

        self.assertEqual(contar_pasos(conversacion), 0)

    def test_conversacion_vacia(self):
        self.assertEqual(contar_pasos(_conversacion([])), 0)


class TestDuracion(unittest.TestCase):
    def test_entre_el_primer_y_el_ultimo_instante(self):
        conversacion = _conversacion(
            [
                _asistente("a", instante="2026-08-21T10:00:00Z", identificador="m1"),
                _asistente("b", instante="2026-08-21T10:01:00Z", identificador="m2"),
                _asistente("c", instante="2026-08-21T10:05:30Z", identificador="m3"),
            ]
        )

        self.assertEqual(duracion(conversacion), 330.0)

    def test_un_solo_instante_no_mide_nada(self):
        conversacion = _conversacion(
            [_asistente("a", instante="2026-08-21T10:00:00Z", identificador="m1")]
        )

        self.assertEqual(duracion(conversacion), 0.0)

    def test_sin_instantes(self):
        conversacion = _conversacion([_asistente("a", identificador="m1")])

        self.assertEqual(duracion(conversacion), 0.0)

    def test_zonas_horarias_mezcladas_no_lanzan(self):
        # Un transcript no tiene por qué estar sano: un instante con zona y
        # otro sin ella no se pueden restar, y la duración se rinde a 0.
        conversacion = _conversacion(
            [
                _asistente("a", instante="2026-08-21T10:00:00Z", identificador="m1"),
                _asistente("b", instante="2026-08-21T11:00:00", identificador="m2"),
            ]
        )

        self.assertEqual(duracion(conversacion), 0.0)


class TestMedirFlujo(unittest.TestCase):
    def _participantes(self):
        return [
            Participante(
                SHERIFF,
                _conversacion(
                    [
                        _asistente(
                            f"{MARCA_PASO} — 1.1",
                            instante="2026-08-21T10:00:00Z",
                            identificador="s1",
                        ),
                        _asistente(
                            f"{MARCA_PASO} — 1.2",
                            instante="2026-08-21T10:40:00Z",
                            identificador="s2",
                        ),
                    ]
                ),
            ),
            Participante(
                "malo",
                _conversacion(
                    [
                        _asistente("ataque", instante="2026-08-21T10:10:00Z", identificador="b1"),
                        _asistente("fin", instante="2026-08-21T10:15:00Z", identificador="b2"),
                    ]
                ),
            ),
            Participante(
                "malo",
                _conversacion(
                    [
                        _asistente("verifico", instante="2026-08-21T10:20:00Z", identificador="c1"),
                        _asistente("fin", instante="2026-08-21T10:22:00Z", identificador="c2"),
                    ]
                ),
            ),
            Participante("feo", _conversacion([_asistente("audito", identificador="f1")])),
        ]

    def test_pasos_lanzamientos_y_rondas(self):
        flujo = medir_flujo(self._participantes())

        self.assertEqual(flujo.pasos, 2)
        self.assertEqual(flujo.lanzamientos, {"malo": 2, "feo": 1})
        self.assertEqual(flujo.rondas_de_malo_por_paso, 1.0)

    def test_el_sheriff_no_cuenta_como_lanzamiento(self):
        flujo = medir_flujo(self._participantes())

        self.assertNotIn(SHERIFF, flujo.lanzamientos)

    def test_el_reloj_suma_las_conversaciones_del_rol(self):
        flujo = medir_flujo(self._participantes())

        self.assertEqual(flujo.reloj[SHERIFF], 2400.0)
        self.assertEqual(flujo.reloj["malo"], 300.0 + 120.0)
        self.assertEqual(flujo.reloj["feo"], 0.0)

    def test_sin_pasos_las_rondas_no_se_atribuyen(self):
        # None y no cero: sin marcas de paso no se sabe entre cuántos
        # repartir los lanzamientos.
        flujo = medir_flujo(
            [Participante("malo", _conversacion([_asistente("a", identificador="b1")]))]
        )

        self.assertEqual(flujo.pasos, 0)
        self.assertIsNone(flujo.rondas_de_malo_por_paso)

    def test_sin_participantes(self):
        self.assertEqual(medir_flujo([]), Flujo())


class TestSumarFlujos(unittest.TestCase):
    def test_agrega_pasos_lanzamientos_y_reloj(self):
        total = sumar_flujos(
            [
                Flujo(pasos=2, lanzamientos={"malo": 3}, reloj={SHERIFF: 100.0}),
                Flujo(
                    pasos=1,
                    lanzamientos={"malo": 1, "feo": 2},
                    reloj={SHERIFF: 50.0, "feo": 10.0},
                ),
            ]
        )

        self.assertEqual(total.pasos, 3)
        self.assertEqual(total.lanzamientos, {"malo": 4, "feo": 2})
        self.assertEqual(total.reloj, {SHERIFF: 150.0, "feo": 10.0})
        self.assertAlmostEqual(total.rondas_de_malo_por_paso, 4 / 3)

    def test_secuencia_vacia_da_el_flujo_nulo(self):
        self.assertEqual(sumar_flujos([]), Flujo())


if __name__ == "__main__":
    unittest.main()
