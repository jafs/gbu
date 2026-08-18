"""Tests de la lectura y normalización de eventos."""

import json
import tempfile
import unittest
from pathlib import Path

from eventos import (
    ADJUNTO,
    ASISTENTE,
    PENSAMIENTO,
    RESULTADO_HERRAMIENTA,
    SISTEMA,
    TEXTO,
    USO_HERRAMIENTA,
    USUARIO,
    cargar_conversacion,
    conversacion_desde_eventos,
    parsear_instante,
    tokens_estimados,
)


def _asistente(bloques, uso=None, instante="2026-08-16T13:45:36.000Z"):
    mensaje = {"role": "assistant", "content": bloques, "model": "claude-opus-5"}
    if uso is not None:
        mensaje["usage"] = uso
    return {"type": "assistant", "timestamp": instante, "message": mensaje}


def _usuario(contenido, instante="2026-08-16T13:45:00.000Z"):
    return {
        "type": "user",
        "timestamp": instante,
        "message": {"role": "user", "content": contenido},
    }


_USO_COMPLETO = {
    "input_tokens": 2,
    "cache_creation_input_tokens": 1000,
    "cache_read_input_tokens": 30000,
    "output_tokens": 500,
}


class TestTokensEstimados(unittest.TestCase):
    def test_cuatro_caracteres_por_token(self):
        self.assertEqual(tokens_estimados("a" * 400), 100)
        self.assertEqual(tokens_estimados(""), 0)
        self.assertEqual(tokens_estimados("abc"), 0)


class TestParsearInstante(unittest.TestCase):
    def test_admite_la_z_de_utc(self):
        instante = parsear_instante("2026-08-16T13:45:36.000Z")
        self.assertEqual(instante.utcoffset().total_seconds(), 0)

    def test_valores_no_parseables(self):
        for valor in (None, 42, "ayer", ""):
            with self.subTest(valor=valor):
                self.assertIsNone(parsear_instante(valor))


class TestNormalizacion(unittest.TestCase):
    def test_contenido_en_cadena(self):
        conversacion = conversacion_desde_eventos([_usuario("hola")])

        (turno,) = conversacion.turnos
        self.assertEqual(turno.papel, USUARIO)
        self.assertEqual([b.clase for b in turno.bloques], [TEXTO])
        self.assertEqual(turno.bloques[0].texto, "hola")

    def test_contenido_en_lista_de_bloques(self):
        conversacion = conversacion_desde_eventos(
            [
                _asistente(
                    [
                        {"type": "thinking", "thinking": "pienso", "signature": "x"},
                        {"type": "text", "text": "digo"},
                        {
                            "type": "tool_use",
                            "id": "t1",
                            "name": "Bash",
                            "input": {"command": "ls"},
                        },
                    ],
                    uso=_USO_COMPLETO,
                )
            ]
        )

        (turno,) = conversacion.turnos
        self.assertEqual(turno.papel, ASISTENTE)
        self.assertEqual(
            [b.clase for b in turno.bloques],
            [PENSAMIENTO, TEXTO, USO_HERRAMIENTA],
        )
        self.assertEqual(turno.modelo, "claude-opus-5")
        # La entrada de la llamada se guarda serializada: es lo que ocupa
        # contexto, no solo el nombre de la herramienta.
        self.assertIn("ls", turno.bloques[2].texto)

    def test_usage_normalizado(self):
        conversacion = conversacion_desde_eventos(
            [_asistente([{"type": "text", "text": "hola"}], uso=_USO_COMPLETO)]
        )

        uso = conversacion.turnos[0].uso
        self.assertEqual(uso.entrada, 2)
        self.assertEqual(uso.creacion_cache, 1000)
        self.assertEqual(uso.lectura_cache, 30000)
        self.assertEqual(uso.salida, 500)
        self.assertEqual(uso.contexto, 31002)

    def test_asistente_sin_usage(self):
        conversacion = conversacion_desde_eventos(
            [_asistente([{"type": "text", "text": "hola"}])]
        )

        self.assertIsNone(conversacion.turnos[0].uso)
        self.assertEqual(len(conversacion.turnos_de_asistente), 1)

    def test_usage_con_campos_ausentes_o_basura(self):
        conversacion = conversacion_desde_eventos(
            [_asistente([], uso={"output_tokens": "muchos", "input_tokens": 7})]
        )

        uso = conversacion.turnos[0].uso
        self.assertEqual(uso.entrada, 7)
        self.assertEqual(uso.salida, 0)

    def test_resultado_emparejado_con_su_llamada(self):
        conversacion = conversacion_desde_eventos(
            [
                _asistente(
                    [
                        {
                            "type": "tool_use",
                            "id": "t1",
                            "name": "Read",
                            "input": {"file_path": "a.py"},
                        }
                    ]
                ),
                _usuario(
                    [
                        {
                            "type": "tool_result",
                            "tool_use_id": "t1",
                            "content": "x" * 400,
                        }
                    ]
                ),
            ]
        )

        (llamada,) = conversacion.llamadas
        self.assertEqual(llamada.nombre, "Read")
        self.assertEqual(llamada.turno, 0)
        self.assertEqual(llamada.tokens_resultado, 100)
        self.assertEqual(conversacion.resultados_huerfanos, ())

    def test_llamada_sin_resultado(self):
        conversacion = conversacion_desde_eventos(
            [_asistente([{"type": "tool_use", "id": "t1", "name": "Read", "input": {}}])]
        )

        (llamada,) = conversacion.llamadas
        self.assertIsNone(llamada.resultado)
        self.assertEqual(llamada.tokens_resultado, 0)

    def test_resultado_sin_llamada_queda_como_huerfano(self):
        conversacion = conversacion_desde_eventos(
            [_usuario([{"type": "tool_result", "tool_use_id": "fantasma", "content": "x"}])]
        )

        self.assertEqual(conversacion.llamadas, ())
        (huerfano,) = conversacion.resultados_huerfanos
        self.assertEqual(huerfano.clase, RESULTADO_HERRAMIENTA)
        self.assertEqual(huerfano.identificador, "fantasma")

    def test_resultado_en_lista_de_bloques(self):
        conversacion = conversacion_desde_eventos(
            [
                _asistente([{"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]),
                _usuario(
                    [
                        {
                            "type": "tool_result",
                            "tool_use_id": "t1",
                            "content": [
                                {"type": "text", "text": "linea uno"},
                                {"type": "text", "text": "linea dos"},
                            ],
                        }
                    ]
                ),
            ]
        )

        (llamada,) = conversacion.llamadas
        self.assertEqual(llamada.resultado.texto, "linea uno\nlinea dos")

    def test_resultado_de_error(self):
        conversacion = conversacion_desde_eventos(
            [
                _asistente([{"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]),
                _usuario(
                    [
                        {
                            "type": "tool_result",
                            "tool_use_id": "t1",
                            "content": "no such file",
                            "is_error": True,
                        }
                    ]
                ),
            ]
        )

        self.assertTrue(conversacion.llamadas[0].resultado.es_error)

    def test_adjunto_es_un_turno_de_sistema(self):
        conversacion = conversacion_desde_eventos(
            [
                {
                    "type": "attachment",
                    "timestamp": "2026-08-16T13:45:36.000Z",
                    "attachment": {
                        "type": "edited_text_file",
                        "filename": "a.ts",
                        "snippet": "y" * 400,
                    },
                }
            ]
        )

        (turno,) = conversacion.turnos
        self.assertEqual(turno.papel, SISTEMA)
        (bloque,) = turno.bloques
        self.assertEqual(bloque.clase, ADJUNTO)
        self.assertEqual(bloque.nombre, "edited_text_file")
        # El adjunto se mide por su serialización completa, así que pesa al
        # menos lo que pesa el fragmento que transporta.
        self.assertGreaterEqual(bloque.tokens, 100)

    def test_eventos_sin_contenido_no_producen_turno(self):
        conversacion = conversacion_desde_eventos(
            [
                {"type": "file-history-snapshot", "snapshot": {"a": 1}},
                {"type": "system", "timestamp": "2026-08-16T13:45:36.000Z"},
                {"type": "attachment", "attachment": None},
                {"type": "user"},
                _usuario("hola"),
            ]
        )

        self.assertEqual(len(conversacion.turnos), 1)
        self.assertEqual(conversacion.turnos[0].indice, 0)

    def test_texto_del_asistente_excluye_el_pensamiento(self):
        conversacion = conversacion_desde_eventos(
            [
                _asistente(
                    [
                        {"type": "thinking", "thinking": "gbu v9.9.9"},
                        {"type": "text", "text": "gbu v0.1.0"},
                    ]
                ),
                _usuario("gbu v1.2.3"),
            ]
        )

        self.assertEqual(conversacion.texto_del_asistente(), "gbu v0.1.0")

    def test_una_respuesta_partida_en_varios_eventos_es_un_solo_turno(self):
        # Claude Code graba cada bloque de una respuesta como un evento
        # aparte, repitiendo el mismo `usage`. Contarlos por separado
        # multiplicaría el coste de la sesión.
        pensamiento = _asistente([{"type": "thinking", "thinking": "pienso"}], uso=_USO_COMPLETO)
        pensamiento["message"]["id"] = "msg_1"
        llamada = _asistente(
            [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}],
            uso=_USO_COMPLETO,
        )
        llamada["message"]["id"] = "msg_1"

        conversacion = conversacion_desde_eventos([pensamiento, llamada])

        (turno,) = conversacion.turnos_de_asistente
        self.assertEqual([b.clase for b in turno.bloques], [PENSAMIENTO, USO_HERRAMIENTA])
        self.assertEqual(turno.uso.contexto, 31002)

    def test_la_fusion_no_deshace_el_emparejamiento_de_resultados(self):
        primero = _asistente(
            [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}],
            uso=_USO_COMPLETO,
        )
        primero["message"]["id"] = "msg_1"
        resultado = _usuario(
            [{"type": "tool_result", "tool_use_id": "t1", "content": "hecho"}]
        )
        # Un evento tardío del mismo mensaje, que llega después del
        # resultado, no debe reabrir la llamada ya emparejada.
        rezagado = _asistente([{"type": "text", "text": "listo"}], uso=_USO_COMPLETO)
        rezagado["message"]["id"] = "msg_1"

        conversacion = conversacion_desde_eventos([primero, resultado, rezagado])

        (llamada,) = conversacion.llamadas
        self.assertIsNotNone(llamada.resultado)
        self.assertEqual(llamada.turno, 0)

    def test_respuestas_distintas_no_se_fusionan(self):
        primero = _asistente([{"type": "text", "text": "uno"}], uso=_USO_COMPLETO)
        primero["message"]["id"] = "msg_1"
        segundo = _asistente([{"type": "text", "text": "dos"}], uso=_USO_COMPLETO)
        segundo["message"]["id"] = "msg_2"

        conversacion = conversacion_desde_eventos([primero, segundo])

        self.assertEqual(len(conversacion.turnos_de_asistente), 2)

    def test_respuestas_sin_identificador_no_se_fusionan(self):
        conversacion = conversacion_desde_eventos(
            [
                _asistente([{"type": "text", "text": "uno"}], uso=_USO_COMPLETO),
                _asistente([{"type": "text", "text": "dos"}], uso=_USO_COMPLETO),
            ]
        )

        self.assertEqual(len(conversacion.turnos_de_asistente), 2)

    def test_version_de_claude_y_rama(self):
        evento = _usuario("hola")
        evento["version"] = "2.0.44"
        evento["gitBranch"] = "main"

        conversacion = conversacion_desde_eventos([evento])

        self.assertEqual(conversacion.version_claude, "2.0.44")
        self.assertEqual(conversacion.rama, "main")


class TestCargarDeFichero(unittest.TestCase):
    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporal.cleanup)
        self.directorio = Path(self._temporal.name)

    def _escribir(self, nombre, lineas):
        fichero = self.directorio / nombre
        fichero.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        return fichero

    def test_linea_corrupta_en_medio_se_descarta_y_se_cuenta(self):
        fichero = self._escribir(
            "sesion.jsonl",
            [
                json.dumps(_usuario("hola")),
                "{a medio escribi",
                "[1, 2, 3]",
                json.dumps(_asistente([{"type": "text", "text": "adios"}])),
            ],
        )

        conversacion = cargar_conversacion(fichero)

        self.assertEqual(conversacion.lineas_ilegibles, 2)
        self.assertEqual(len(conversacion.turnos), 2)
        self.assertEqual(conversacion.identificador, "sesion")

    def test_fichero_vacio(self):
        fichero = self.directorio / "vacia.jsonl"
        fichero.write_text("", encoding="utf-8")

        conversacion = cargar_conversacion(fichero)

        self.assertEqual(conversacion.turnos, ())
        self.assertEqual(conversacion.lineas_ilegibles, 0)

    def test_lineas_en_blanco_no_cuentan_como_ilegibles(self):
        fichero = self._escribir("blancos.jsonl", ["", json.dumps(_usuario("hola")), ""])

        conversacion = cargar_conversacion(fichero)

        self.assertEqual(conversacion.lineas_ilegibles, 0)
        self.assertEqual(len(conversacion.turnos), 1)

    def test_identificador_explicito(self):
        fichero = self._escribir("sesion.jsonl", [json.dumps(_usuario("hola"))])

        conversacion = cargar_conversacion(fichero, identificador="malo-01")

        self.assertEqual(conversacion.identificador, "malo-01")

    def test_texto_con_codificacion_rota_no_aborta(self):
        fichero = self.directorio / "rota.jsonl"
        linea = json.dumps(_usuario("acentuado")).encode("utf-8")
        fichero.write_bytes(linea.replace(b"acentuado", b"acent\xffado") + b"\n")

        conversacion = cargar_conversacion(fichero)

        # El byte inválido se sustituye al leer, así que la línea sigue
        # siendo JSON válido y el turno se conserva.
        self.assertEqual(len(conversacion.turnos), 1)
        self.assertEqual(conversacion.lineas_ilegibles, 0)


if __name__ == "__main__":
    unittest.main()
