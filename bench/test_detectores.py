"""Tests de los detectores de derroche."""

import unittest

from detectores import (
    CATEGORIA_BLOQUE_CARO,
    CATEGORIA_COMANDO_REPETIDO,
    CATEGORIA_CONTEXTO_DESBOCADO,
    CATEGORIA_LECTURA_COMPARTIDA,
    CATEGORIA_PRELUDE_EXCESIVO,
    CATEGORIA_RELECTURA,
    CATEGORIA_RESULTADO_GIGANTE,
    Umbrales,
    Vista,
    bloques_caros,
    comandos_repetidos,
    contextos_desbocados,
    detectar,
    ficheros_compartidos,
    ficheros_releidos,
    preludes_excesivos,
    resultados_gigantes,
)
from eventos import conversacion_desde_eventos

_UMBRALES = Umbrales(
    resultado_grande=100,
    bloque_caro=1_000,
    contexto_maximo=1_000,
    prelude_maximo=1_000,
)


def _llamada(nombre, entrada, contenido, identificador, contexto=100):
    """Una llamada a herramienta con su resultado, en dos eventos."""
    return [
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "id": f"msg-{identificador}",
                "model": "claude-opus-5",
                "usage": {"input_tokens": contexto, "output_tokens": 1},
                "content": [
                    {
                        "type": "tool_use",
                        "id": identificador,
                        "name": nombre,
                        "input": entrada,
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


def _turno(texto="ok", contexto=100, identificador="fin"):
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "id": f"msg-{identificador}",
            "model": "claude-opus-5",
            "usage": {"input_tokens": contexto, "output_tokens": 1},
            "content": [{"type": "text", "text": texto}],
        },
    }


def _vista(eventos, rol="sheriff", sesion="s1"):
    return Vista(sesion=sesion, rol=rol, conversacion=conversacion_desde_eventos(eventos))


def _leer(ruta, tamano=400, identificador="t1", contexto=100):
    return _llamada("Read", {"file_path": ruta}, "x" * tamano, identificador, contexto)


class TestFicherosReleidos(unittest.TestCase):
    def test_dispara_cuando_el_mismo_rol_lee_dos_veces(self):
        eventos = _leer("a.py", identificador="t1") + _leer("a.py", identificador="t2")
        eventos.append(_turno())

        (hallazgo,) = ficheros_releidos(_vista(eventos), _UMBRALES)

        self.assertEqual(hallazgo.categoria, CATEGORIA_RELECTURA)
        self.assertIn("2 veces", hallazgo.titulo)
        self.assertGreater(hallazgo.tokens, 0)
        self.assertEqual(len(hallazgo.evidencias), 2)

    def test_no_dispara_con_una_sola_lectura(self):
        eventos = _leer("a.py") + [_turno()]

        self.assertEqual(ficheros_releidos(_vista(eventos), _UMBRALES), ())

    def test_la_misma_ruta_con_separadores_distintos_es_el_mismo_fichero(self):
        eventos = _leer("src/a.ts", identificador="t1") + _leer(
            "src\\a.ts", identificador="t2"
        )
        eventos.append(_turno())

        (hallazgo,) = ficheros_releidos(_vista(eventos), _UMBRALES)

        self.assertIn("2 veces", hallazgo.titulo)

    def test_los_adjuntos_cuentan_como_lectura(self):
        eventos = _leer("a.ts", identificador="t1")
        eventos.append(
            {
                "type": "attachment",
                "attachment": {"type": "edited_text_file", "filename": "a.ts", "snippet": "z" * 400},
            }
        )
        eventos.append(_turno())

        (hallazgo,) = ficheros_releidos(_vista(eventos), _UMBRALES)

        self.assertIn("2 veces", hallazgo.titulo)

    def test_ficheros_distintos_no_se_mezclan(self):
        eventos = _leer("a.py", identificador="t1") + _leer("b.py", identificador="t2")
        eventos.append(_turno())

        self.assertEqual(ficheros_releidos(_vista(eventos), _UMBRALES), ())

    def test_el_desperdicio_no_cuenta_la_primera_lectura(self):
        una = _leer("a.py", identificador="t1") + [_turno()]
        dos = _leer("a.py", identificador="t1") + _leer("a.py", identificador="t2") + [_turno()]

        (hallazgo,) = ficheros_releidos(_vista(dos), _UMBRALES)
        bloques = [b for b in _vista(dos).bloques() if b.clase == "resultado_herramienta"]

        self.assertEqual(hallazgo.tokens, bloques[1].turn_tokens)
        self.assertEqual(ficheros_releidos(_vista(una), _UMBRALES), ())


class TestFicherosCompartidos(unittest.TestCase):
    def test_dispara_cuando_dos_roles_leen_el_mismo_fichero(self):
        sheriff = _vista(_leer("PLAN.md", identificador="t1") + [_turno()], rol="sheriff")
        malo = _vista(_leer("PLAN.md", identificador="t9") + [_turno()], rol="malo")

        (hallazgo,) = ficheros_compartidos([sheriff, malo], _UMBRALES)

        self.assertEqual(hallazgo.categoria, CATEGORIA_LECTURA_COMPARTIDA)
        self.assertEqual({e.rol for e in hallazgo.evidencias}, {"sheriff", "malo"})

    def test_no_dispara_si_solo_lo_lee_un_rol(self):
        sheriff = _vista(_leer("PLAN.md") + [_turno()], rol="sheriff")
        malo = _vista(_leer("otro.md") + [_turno()], rol="malo")

        self.assertEqual(ficheros_compartidos([sheriff, malo], _UMBRALES), ())

    def test_descuenta_la_lectura_mas_barata(self):
        # Alguien tenía que leerlo: el desperdicio es lo que cuestan las
        # demás copias, no todas.
        sheriff = _vista(_leer("PLAN.md", tamano=4000, identificador="t1") + [_turno()], rol="sheriff")
        malo = _vista(_leer("PLAN.md", tamano=4000, identificador="t9") + [_turno()], rol="malo")

        (hallazgo,) = ficheros_compartidos([sheriff, malo], _UMBRALES)
        bloques = [
            b
            for vista in (sheriff, malo)
            for b in vista.bloques()
            if b.clase == "resultado_herramienta"
        ]

        self.assertEqual(
            hallazgo.tokens, sum(b.turn_tokens for b in bloques) - min(b.turn_tokens for b in bloques)
        )


class TestComandosRepetidos(unittest.TestCase):
    def test_dispara_con_el_comando_literalmente_repetido(self):
        eventos = _llamada("Bash", {"command": "git status --short"}, "ok", "t1")
        eventos += _llamada("Bash", {"command": "git status --short"}, "ok", "t2")
        eventos.append(_turno())

        (hallazgo,) = comandos_repetidos(_vista(eventos), _UMBRALES)

        self.assertEqual(hallazgo.categoria, CATEGORIA_COMANDO_REPETIDO)
        self.assertIn("git status --short", hallazgo.titulo)

    def test_no_dispara_con_comandos_distintos(self):
        eventos = _llamada("Bash", {"command": "ls"}, "ok", "t1")
        eventos += _llamada("Bash", {"command": "pwd"}, "ok", "t2")
        eventos.append(_turno())

        self.assertEqual(comandos_repetidos(_vista(eventos), _UMBRALES), ())

    def test_las_lecturas_no_cuentan_como_comandos(self):
        eventos = _leer("a.py", identificador="t1") + _leer("a.py", identificador="t2")
        eventos.append(_turno())

        self.assertEqual(comandos_repetidos(_vista(eventos), _UMBRALES), ())


class TestResultadosGigantes(unittest.TestCase):
    def test_justo_por_encima_del_umbral(self):
        # 404 caracteres son 101 tokens estimados, uno más que el umbral.
        eventos = _leer("a.py", tamano=404) + [_turno()]

        (hallazgo,) = resultados_gigantes(_vista(eventos), _UMBRALES)

        self.assertEqual(hallazgo.categoria, CATEGORIA_RESULTADO_GIGANTE)
        self.assertIn("a.py", hallazgo.evidencias[0].fragmento)

    def test_justo_por_debajo_del_umbral(self):
        # 396 caracteres son 99 tokens estimados, uno menos que el umbral.
        eventos = _leer("a.py", tamano=396) + [_turno()]

        self.assertEqual(resultados_gigantes(_vista(eventos), _UMBRALES), ())

    def test_justo_en_el_umbral_dispara(self):
        eventos = _leer("a.py", tamano=400) + [_turno()]

        self.assertEqual(len(resultados_gigantes(_vista(eventos), _UMBRALES)), 1)


class TestBloquesCaros(unittest.TestCase):
    def test_dispara_por_permanencia_no_por_tamano(self):
        # Un bloque mediano leído por muchos turnos supera el umbral de
        # turn-tokens aunque no sea grande.
        eventos = _leer("a.py", tamano=2000)
        for i in range(6):
            eventos.append(_turno(identificador=f"m{i}"))

        hallazgos = bloques_caros(_vista(eventos), _UMBRALES)

        self.assertTrue(hallazgos)
        self.assertEqual(hallazgos[0].categoria, CATEGORIA_BLOQUE_CARO)

    def test_un_bloque_de_texto_se_identifica_por_su_contenido(self):
        # Sin esto, el hallazgo diría solo que "un texto" costó mucho, y no
        # habría forma de saber cuál para poder recortarlo.
        eventos = [_turno(texto="Eres el Sheriff. " * 200, identificador="m0")]
        for i in range(6):
            eventos.append(_turno(identificador=f"m{i + 1}"))

        hallazgos = bloques_caros(_vista(eventos), _UMBRALES)

        self.assertTrue(hallazgos)
        self.assertIn("Eres el Sheriff", hallazgos[0].titulo)

    def test_no_dispara_en_una_conversacion_corta(self):
        eventos = _leer("a.py", tamano=2000) + [_turno()]

        self.assertEqual(bloques_caros(_vista(eventos), _UMBRALES), ())


class TestContextosDesbocados(unittest.TestCase):
    def test_suma_solo_el_exceso_sobre_el_umbral(self):
        eventos = [
            _turno(contexto=900, identificador="m1"),
            _turno(contexto=1200, identificador="m2"),
            _turno(contexto=1500, identificador="m3"),
        ]

        (hallazgo,) = contextos_desbocados(_vista(eventos), _UMBRALES)

        self.assertEqual(hallazgo.categoria, CATEGORIA_CONTEXTO_DESBOCADO)
        self.assertEqual(hallazgo.tokens, 200 + 500)
        self.assertIn("2 turnos por encima", hallazgo.evidencias[0].detalle)

    def test_no_dispara_por_debajo_del_umbral(self):
        eventos = [_turno(contexto=1000, identificador="m1")]

        self.assertEqual(contextos_desbocados(_vista(eventos), _UMBRALES), ())


class TestPreludesExcesivos(unittest.TestCase):
    def test_multiplica_el_exceso_por_los_turnos(self):
        eventos = [
            _turno(contexto=1500, identificador="m1"),
            _turno(contexto=1500, identificador="m2"),
        ]

        (hallazgo,) = preludes_excesivos(_vista(eventos), _UMBRALES)

        self.assertEqual(hallazgo.categoria, CATEGORIA_PRELUDE_EXCESIVO)
        self.assertEqual(hallazgo.tokens, 500 * 2)

    def test_no_dispara_con_prelude_en_el_umbral(self):
        eventos = [_turno(contexto=1000, identificador="m1")]

        self.assertEqual(preludes_excesivos(_vista(eventos), _UMBRALES), ())


class TestDetectar(unittest.TestCase):
    def test_una_sesion_limpia_no_produce_ningun_hallazgo(self):
        vista = _vista(_leer("a.py", tamano=40, contexto=100) + [_turno(contexto=200)])

        self.assertEqual(detectar([vista], _UMBRALES), ())

    def test_reune_los_hallazgos_de_todos_los_detectores(self):
        eventos = _leer("PLAN.md", tamano=4000, identificador="t1")
        eventos += _leer("PLAN.md", tamano=4000, identificador="t2")
        eventos += _llamada("Bash", {"command": "ls"}, "ok", "t3")
        eventos += _llamada("Bash", {"command": "ls"}, "ok", "t4")
        eventos.append(_turno(contexto=5000))
        malo = _vista(_leer("PLAN.md", tamano=4000, identificador="t9") + [_turno()], rol="malo")

        hallazgos = detectar([_vista(eventos), malo], _UMBRALES)
        categorias = {h.categoria for h in hallazgos}

        self.assertIn(CATEGORIA_RELECTURA, categorias)
        self.assertIn(CATEGORIA_COMANDO_REPETIDO, categorias)
        self.assertIn(CATEGORIA_RESULTADO_GIGANTE, categorias)
        self.assertIn(CATEGORIA_LECTURA_COMPARTIDA, categorias)
        self.assertIn(CATEGORIA_CONTEXTO_DESBOCADO, categorias)

    def test_los_identificadores_son_estables_entre_ejecuciones(self):
        eventos = _leer("a.py", identificador="t1") + _leer("a.py", identificador="t2")
        eventos.append(_turno())

        primeros = [h.identificador for h in detectar([_vista(eventos)], _UMBRALES)]
        segundos = [h.identificador for h in detectar([_vista(eventos)], _UMBRALES)]

        self.assertEqual(primeros, segundos)

    def test_sin_vistas(self):
        self.assertEqual(detectar([], _UMBRALES), ())


if __name__ == "__main__":
    unittest.main()
