"""Tests de las métricas de contexto."""

import unittest

from eventos import ADJUNTO, RESULTADO_HERRAMIENTA, TEXTO, conversacion_desde_eventos
from metricas_contexto import (
    bloques_con_lecturas,
    bloques_mas_caros,
    curva_de_contexto,
    prelude_estimado,
    reparto_de_turn_tokens,
    texto_del_contexto,
    turn_tokens_totales,
)


def _asistente(texto, contexto=None, salida=0, identificador=None):
    mensaje = {
        "role": "assistant",
        "content": [{"type": "text", "text": texto}],
        "model": "claude-opus-5",
        "id": identificador or f"msg-{texto[:8]}",
    }
    if contexto is not None:
        mensaje["usage"] = {
            "input_tokens": contexto,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "output_tokens": salida,
        }
    return {"type": "assistant", "message": mensaje}


def _usuario(texto):
    return {"type": "user", "message": {"role": "user", "content": texto}}


def _lectura(ruta, contenido, identificador="t1"):
    """Una llamada a Read con su resultado, repartida en dos eventos."""
    return [
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "id": f"msg-{identificador}",
                "model": "claude-opus-5",
                "usage": {"input_tokens": 100, "output_tokens": 1},
                "content": [
                    {
                        "type": "tool_use",
                        "id": identificador,
                        "name": "Read",
                        "input": {"file_path": ruta},
                    }
                ],
            },
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": identificador,
                        "content": contenido,
                    }
                ],
            },
        },
    ]


class TestCurva(unittest.TestCase):
    def test_maximo_media_final_e_inicial(self):
        conversacion = conversacion_desde_eventos(
            [
                _asistente("uno", contexto=100, identificador="m1"),
                _asistente("dos", contexto=300, identificador="m2"),
                _asistente("tres", contexto=200, identificador="m3"),
            ]
        )

        curva = curva_de_contexto(conversacion)

        self.assertEqual(len(curva.puntos), 3)
        self.assertEqual(curva.maximo, 300)
        self.assertEqual(curva.media, 200.0)
        self.assertEqual(curva.inicial, 100)
        self.assertEqual(curva.final, 200)

    def test_los_turnos_sin_usage_no_entran_en_la_curva(self):
        conversacion = conversacion_desde_eventos(
            [
                _asistente("uno", contexto=100, identificador="m1"),
                _asistente("sin uso", identificador="m2"),
            ]
        )

        self.assertEqual(len(curva_de_contexto(conversacion).puntos), 1)

    def test_conversacion_vacia(self):
        curva = curva_de_contexto(conversacion_desde_eventos([]))

        self.assertEqual(curva.puntos, ())
        self.assertEqual(curva.maximo, 0)
        self.assertEqual(curva.media, 0.0)
        self.assertEqual(curva.final, 0)


class TestPrelude(unittest.TestCase):
    def test_sin_nada_antes_del_primer_turno(self):
        # Nada precede al primer turno, así que todo su contexto es fijo.
        conversacion = conversacion_desde_eventos(
            [_asistente("hola", contexto=46000, identificador="m1")]
        )

        self.assertEqual(prelude_estimado(conversacion), 46000)

    def test_descuenta_lo_que_ya_estaba_en_el_transcript(self):
        conversacion = conversacion_desde_eventos(
            [_usuario("x" * 4000), _asistente("hola", contexto=46000, identificador="m1")]
        )

        # 4000 caracteres son 1000 tokens estimados.
        self.assertEqual(prelude_estimado(conversacion), 45000)

    def test_nunca_es_negativo(self):
        conversacion = conversacion_desde_eventos(
            [_usuario("x" * 40000), _asistente("hola", contexto=100, identificador="m1")]
        )

        self.assertEqual(prelude_estimado(conversacion), 0)

    def test_sin_turnos_con_usage(self):
        self.assertEqual(prelude_estimado(conversacion_desde_eventos([_usuario("hola")])), 0)


class TestTurnTokens(unittest.TestCase):
    def test_calculo_a_mano_en_una_conversacion_corta(self):
        # Tres turnos de asistente. El resultado de la lectura llega en el
        # turno 1 (papel usuario) y lo leen los turnos de asistente 2 y 3:
        # sus índices son 0, 2 y 3, así que quedan dos con índice >= 1.
        eventos = _lectura("a.py", "x" * 400)
        eventos.append(_asistente("dos", contexto=200, identificador="m2"))
        eventos.append(_asistente("tres", contexto=300, identificador="m3"))
        conversacion = conversacion_desde_eventos(eventos)

        resultado = next(
            b for b in bloques_con_lecturas(conversacion) if b.clase == RESULTADO_HERRAMIENTA
        )

        self.assertEqual(resultado.tokens, 100)
        self.assertEqual(resultado.lecturas, 2)
        self.assertEqual(resultado.turn_tokens, 200)

    def test_un_bloque_del_asistente_no_lo_relee_su_propio_turno(self):
        conversacion = conversacion_desde_eventos(
            [
                _asistente("x" * 400, contexto=100, identificador="m1"),
                _asistente("dos", contexto=200, identificador="m2"),
            ]
        )

        primero = next(b for b in bloques_con_lecturas(conversacion) if b.tokens == 100)

        self.assertEqual(primero.lecturas, 1)
        self.assertEqual(primero.turn_tokens, 100)

    def test_bloque_que_entra_en_el_ultimo_turno(self):
        # Lo que escribe el asistente en el último turno ya no lo relee
        # nadie: su permanencia en el contexto no cuesta nada.
        conversacion = conversacion_desde_eventos(
            [
                _asistente("uno", contexto=100, identificador="m1"),
                _asistente("x" * 400, contexto=200, identificador="m2"),
            ]
        )

        ultimo = next(b for b in bloques_con_lecturas(conversacion) if b.tokens == 100)

        self.assertEqual(ultimo.lecturas, 0)
        self.assertEqual(ultimo.turn_tokens, 0)

    def test_conversacion_de_un_solo_turno(self):
        conversacion = conversacion_desde_eventos(
            [_asistente("x" * 400, contexto=100, identificador="m1")]
        )

        self.assertEqual(turn_tokens_totales(conversacion), 0)
        self.assertEqual(bloques_mas_caros(conversacion), ())

    def test_reparto_por_clase_de_bloque(self):
        eventos = _lectura("a.py", "x" * 4000)
        eventos.append(_asistente("y" * 400, contexto=200, identificador="m2"))
        eventos.append(_asistente("fin", contexto=300, identificador="m3"))
        conversacion = conversacion_desde_eventos(eventos)

        reparto = reparto_de_turn_tokens(conversacion)

        self.assertEqual(reparto[RESULTADO_HERRAMIENTA], 2000)
        self.assertEqual(reparto[TEXTO], 100)
        self.assertEqual(sum(reparto.values()), turn_tokens_totales(conversacion))

    def test_los_adjuntos_cuentan_como_cualquier_otro_bloque(self):
        conversacion = conversacion_desde_eventos(
            [
                {
                    "type": "attachment",
                    "attachment": {"type": "edited_text_file", "filename": "a.ts", "snippet": "z" * 4000},
                },
                _asistente("uno", contexto=100, identificador="m1"),
                _asistente("dos", contexto=200, identificador="m2"),
            ]
        )

        reparto = reparto_de_turn_tokens(conversacion)

        self.assertGreaterEqual(reparto[ADJUNTO], 2000)

    def test_bloques_mas_caros_ordenados_y_con_identificacion(self):
        eventos = _lectura("grande.md", "x" * 40000, identificador="t1")
        eventos += _lectura("pequeno.md", "y" * 400, identificador="t2")
        eventos.append(_asistente("fin", contexto=300, identificador="m9"))
        conversacion = conversacion_desde_eventos(eventos)

        caros = bloques_mas_caros(conversacion, limite=2)

        self.assertEqual(len(caros), 2)
        self.assertGreater(caros[0].turn_tokens, caros[1].turn_tokens)
        # La llamada conserva sobre qué fichero actuó, que es lo que permite
        # reconocer después una relectura.
        llamadas = [b.identificacion for b in bloques_con_lecturas(conversacion)]
        self.assertIn("grande.md", llamadas)

    def test_limite_de_bloques(self):
        eventos = []
        for i in range(10):
            eventos += _lectura(f"f{i}.py", "x" * 400, identificador=f"t{i}")
        eventos.append(_asistente("fin", contexto=100, identificador="m9"))
        conversacion = conversacion_desde_eventos(eventos)

        self.assertEqual(len(bloques_mas_caros(conversacion, limite=3)), 3)


class TestTextoDelContexto(unittest.TestCase):
    def test_suma_los_tokens_estimados_de_todos_los_turnos(self):
        conversacion = conversacion_desde_eventos(
            [_usuario("x" * 400), _asistente("y" * 400, contexto=100, identificador="m1")]
        )

        self.assertEqual(texto_del_contexto(conversacion), 200)


if __name__ == "__main__":
    unittest.main()
