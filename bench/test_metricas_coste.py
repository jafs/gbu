"""Tests de las métricas de coste por rol y modelo."""

import unittest

from eventos import conversacion_desde_eventos
from metricas_coste import (
    MODELO_DESCONOCIDO,
    PESOS_POR_DEFECTO,
    SHERIFF,
    Agregado,
    Participante,
    agregar_sesion,
    coste,
    reparto,
    resumir_conversacion,
    sumar,
)


def _turno(uso=None, modelo="claude-opus-5", identificador=None):
    mensaje = {"role": "assistant", "content": [{"type": "text", "text": "hola"}]}
    if modelo is not None:
        mensaje["model"] = modelo
    if identificador is not None:
        mensaje["id"] = identificador
    if uso is not None:
        mensaje["usage"] = {
            "input_tokens": uso[0],
            "cache_creation_input_tokens": uso[1],
            "cache_read_input_tokens": uso[2],
            "output_tokens": uso[3],
        }
    return {"type": "assistant", "message": mensaje}


def _conversacion(turnos):
    return conversacion_desde_eventos(turnos)


class TestAgregado(unittest.TestCase):
    def test_suma(self):
        a = Agregado(turnos=1, entrada=10, creacion_cache=20, lectura_cache=30, salida=40)
        b = Agregado(turnos=2, entrada=1, creacion_cache=2, lectura_cache=3, salida=4)

        total = a + b

        self.assertEqual(total.turnos, 3)
        self.assertEqual(total.entrada, 11)
        self.assertEqual(total.creacion_cache, 22)
        self.assertEqual(total.lectura_cache, 33)
        self.assertEqual(total.salida, 44)

    def test_contexto_suma_las_tres_clases_de_entrada(self):
        agregado = Agregado(entrada=10, creacion_cache=20, lectura_cache=30, salida=999)

        self.assertEqual(agregado.contexto, 60)

    def test_sumar_secuencia_vacia(self):
        self.assertEqual(sumar([]), Agregado())


class TestCoste(unittest.TestCase):
    def test_pesos_por_defecto(self):
        agregado = Agregado(entrada=100, creacion_cache=200, lectura_cache=1000, salida=50)

        # 100*1 + 200*1.25 + 1000*0.1 + 50*5 = 100 + 250 + 100 + 250
        self.assertEqual(coste(agregado), 700.0)
        self.assertEqual(coste(agregado, PESOS_POR_DEFECTO), 700.0)

    def test_pesos_alternativos(self):
        agregado = Agregado(entrada=100, creacion_cache=200, lectura_cache=1000, salida=50)
        pesos = {"entrada": 1.0, "creacion_cache": 1.0, "lectura_cache": 1.0, "salida": 1.0}

        self.assertEqual(coste(agregado, pesos), 1350.0)

    def test_pesos_incompletos_valen_cero(self):
        agregado = Agregado(entrada=100, salida=50)

        self.assertEqual(coste(agregado, {"entrada": 2.0}), 200.0)

    def test_agregado_nulo(self):
        self.assertEqual(coste(Agregado()), 0.0)


class TestResumirConversacion(unittest.TestCase):
    def test_solo_cuentan_los_turnos_de_asistente(self):
        conversacion = conversacion_desde_eventos(
            [
                {"type": "user", "message": {"role": "user", "content": "hola"}},
                _turno((2, 1000, 30000, 500), identificador="m1"),
            ]
        )

        total, _ = resumir_conversacion(conversacion)

        self.assertEqual(total.turnos, 1)
        self.assertEqual(total.entrada, 2)
        self.assertEqual(total.salida, 500)

    def test_conversacion_sin_ningun_usage(self):
        conversacion = _conversacion([_turno(identificador="m1"), _turno(identificador="m2")])

        total, por_modelo = resumir_conversacion(conversacion)

        self.assertEqual(total.turnos, 2)
        self.assertEqual(total.turnos_sin_uso, 2)
        self.assertEqual(coste(total), 0.0)
        # El turno existió aunque no declarase tokens, así que su modelo
        # aparece igualmente en el desglose.
        self.assertEqual(por_modelo["claude-opus-5"].turnos, 2)

    def test_un_rol_en_dos_modelos_distintos(self):
        conversacion = _conversacion(
            [
                _turno((0, 0, 0, 100), modelo="claude-opus-5", identificador="m1"),
                _turno((0, 0, 0, 10), modelo="claude-sonnet-5", identificador="m2"),
            ]
        )

        total, por_modelo = resumir_conversacion(conversacion)

        self.assertEqual(total.salida, 110)
        self.assertEqual(sorted(por_modelo), ["claude-opus-5", "claude-sonnet-5"])
        self.assertEqual(por_modelo["claude-opus-5"].salida, 100)
        self.assertEqual(por_modelo["claude-sonnet-5"].salida, 10)

    def test_turno_sin_modelo_cae_en_el_declarado(self):
        conversacion = _conversacion([_turno((0, 0, 0, 7), modelo=None, identificador="m1")])

        _, por_modelo = resumir_conversacion(conversacion, modelo_declarado="sonnet")

        self.assertEqual(por_modelo["sonnet"].salida, 7)

    def test_turno_sin_modelo_ni_declarado(self):
        conversacion = _conversacion([_turno((0, 0, 0, 7), modelo=None, identificador="m1")])

        _, por_modelo = resumir_conversacion(conversacion)

        self.assertEqual(list(por_modelo), [MODELO_DESCONOCIDO])


class TestAgregarSesion(unittest.TestCase):
    def _sesion(self):
        return agregar_sesion(
            [
                Participante(
                    SHERIFF,
                    _conversacion([_turno((0, 0, 0, 100), identificador="s1")]),
                ),
                Participante(
                    "malo",
                    _conversacion([_turno((0, 0, 0, 40), identificador="b1")]),
                    modelo="opus",
                ),
                Participante(
                    "malo",
                    _conversacion([_turno((0, 0, 0, 20), identificador="b2")]),
                    modelo="opus",
                ),
                Participante(
                    "feo",
                    _conversacion(
                        [_turno((0, 0, 0, 40), modelo="claude-sonnet-5", identificador="f1")]
                    ),
                    modelo="sonnet",
                ),
            ],
            identificador="sesion-1",
        )

    def test_reparto_entre_sheriff_y_subagentes(self):
        sesion = self._sesion()

        self.assertEqual([r.rol for r in sesion.roles], [SHERIFF, "malo", "feo"])
        self.assertEqual(sesion.total.salida, 200)
        self.assertEqual(coste(sesion.total), 1000.0)

    def test_los_participantes_del_mismo_rol_se_funden(self):
        sesion = self._sesion()

        malo = next(r for r in sesion.roles if r.rol == "malo")
        self.assertEqual(malo.conversaciones, 2)
        self.assertEqual(malo.total.salida, 60)
        self.assertEqual(malo.total.turnos, 2)

    def test_desglose_por_modelo_dentro_del_rol(self):
        sesion = self._sesion()

        feo = next(r for r in sesion.roles if r.rol == "feo")
        # El modelo del turno manda sobre el declarado en el `.meta.json`.
        self.assertEqual(list(feo.por_modelo), ["claude-sonnet-5"])

    def test_modelos_cruzando_todos_los_roles(self):
        sesion = self._sesion()

        modelos = sesion.modelos
        self.assertEqual(modelos["claude-opus-5"].salida, 160)
        self.assertEqual(modelos["claude-sonnet-5"].salida, 40)

    def test_reparto_en_fracciones(self):
        sesion = self._sesion()

        fracciones = reparto(sesion)

        self.assertAlmostEqual(fracciones[SHERIFF], 0.5)
        self.assertAlmostEqual(fracciones["malo"], 0.3)
        self.assertAlmostEqual(fracciones["feo"], 0.2)
        self.assertAlmostEqual(sum(fracciones.values()), 1.0)

    def test_reparto_con_coste_nulo_no_divide_por_cero(self):
        sesion = agregar_sesion(
            [Participante(SHERIFF, _conversacion([_turno(identificador="s1")]))]
        )

        self.assertEqual(reparto(sesion), {SHERIFF: 0.0})

    def test_sesion_sin_participantes(self):
        sesion = agregar_sesion([])

        self.assertEqual(sesion.roles, ())
        self.assertEqual(sesion.total, Agregado())
        self.assertEqual(sesion.modelos, {})


if __name__ == "__main__":
    unittest.main()
