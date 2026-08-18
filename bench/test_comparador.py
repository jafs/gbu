"""Tests de la comparación entre dos informes archivados."""

import unittest

from comparador import a_markdown, comparar


def _informe(
    esquema=1,
    sesiones=6,
    turnos=600,
    coste=1_000_000,
    pensamiento=1000,
    versiones=None,
    por_rol=None,
    turn_tokens=None,
    hallazgos=(),
):
    return {
        "esquema": esquema,
        "proyecto": "C:/proyectos/x",
        "versiones": versiones if versiones is not None else {"0.1.0": sesiones},
        "metricas": {
            "sesiones": sesiones,
            "turnos": turnos,
            "coste_total": coste,
            "pensamiento": pensamiento,
            "por_rol": por_rol or {"sheriff": {"coste": coste, "turnos": turnos}},
            "por_modelo": {"claude-opus-5": {"coste": coste, "turnos": turnos}},
            "turn_tokens": turn_tokens or {"texto": 500},
        },
        "hallazgos": list(hallazgos),
    }


def _hallazgo(identificador, tokens=100, categoria="relectura", severidad="alta"):
    return {
        "identificador": identificador,
        "categoria": categoria,
        "severidad": severidad,
        "titulo": f"titulo de {identificador}",
        "tokens": tokens,
    }


def _metrica(comparacion, nombre):
    return next(v for v in comparacion.metricas if v.nombre == nombre)


class TestMetricas(unittest.TestCase):
    def test_una_metrica_que_mejora(self):
        comparacion = comparar(_informe(coste=1_000_000), _informe(coste=750_000, versiones={"0.2.0": 6}))

        variacion = _metrica(comparacion, "coste_total")
        self.assertEqual(variacion.absoluta, -250_000)
        self.assertAlmostEqual(variacion.porcentaje, -25.0)
        self.assertTrue(variacion.mejora)

    def test_una_metrica_que_empeora(self):
        comparacion = comparar(_informe(coste=1_000_000), _informe(coste=1_500_000, versiones={"0.2.0": 6}))

        variacion = _metrica(comparacion, "coste_total")
        self.assertEqual(variacion.absoluta, 500_000)
        self.assertFalse(variacion.mejora)

    def test_las_cifras_normalizadas_por_sesion_y_por_turno(self):
        # La ventana nueva es la mitad de larga y gasta la mitad: el total
        # baja, pero el patrón cuesta exactamente lo mismo.
        comparacion = comparar(
            _informe(sesiones=6, turnos=600, coste=1_200_000),
            _informe(sesiones=3, turnos=300, coste=600_000, versiones={"0.2.0": 3}),
        )

        self.assertEqual(_metrica(comparacion, "coste_total").absoluta, -600_000)
        self.assertEqual(_metrica(comparacion, "coste_por_sesion").absoluta, 0)
        self.assertEqual(_metrica(comparacion, "coste_por_turno").absoluta, 0)

    def test_una_metrica_presente_solo_en_uno_de_los_dos(self):
        comparacion = comparar(
            _informe(por_rol={"sheriff": {"coste": 100}}),
            _informe(
                por_rol={"sheriff": {"coste": 100}, "listo": {"coste": 50}},
                versiones={"0.2.0": 6},
            ),
        )

        variacion = _metrica(comparacion, "listo")
        self.assertEqual(variacion.antes, 0)
        self.assertEqual(variacion.despues, 50)
        self.assertIsNone(variacion.porcentaje)

    def test_divisor_cero_no_revienta(self):
        comparacion = comparar(
            _informe(sesiones=0, turnos=0, coste=0, versiones={}),
            _informe(versiones={"0.2.0": 6}),
        )

        self.assertIsNone(_metrica(comparacion, "coste_total").porcentaje)
        self.assertEqual(_metrica(comparacion, "coste_por_sesion").antes, 0)

    def test_los_turnos_no_se_juzgan(self):
        comparacion = comparar(_informe(turnos=600), _informe(turnos=700, versiones={"0.2.0": 6}))

        self.assertIsNone(_metrica(comparacion, "turnos").mejora)

    def test_una_metrica_igual_no_se_juzga(self):
        comparacion = comparar(_informe(), _informe(versiones={"0.2.0": 6}))

        self.assertIsNone(_metrica(comparacion, "coste_total").mejora)


class TestHallazgos(unittest.TestCase):
    def _comparacion(self):
        antes = _informe(hallazgos=[_hallazgo("a-1", 500), _hallazgo("a-2", 300)])
        despues = _informe(
            versiones={"0.2.0": 6},
            hallazgos=[_hallazgo("a-2", 1200), _hallazgo("a-3", 80)],
        )
        return comparar(antes, despues)

    def test_resuelto(self):
        comparacion = self._comparacion()

        self.assertEqual([h.identificador for h in comparacion.resueltos], ["a-1"])
        self.assertEqual(comparacion.resueltos[0].antes, 500)
        self.assertEqual(comparacion.resueltos[0].despues, 0)

    def test_persistente_con_su_variacion(self):
        comparacion = self._comparacion()

        (persistente,) = comparacion.persistentes
        self.assertEqual(persistente.identificador, "a-2")
        self.assertEqual(persistente.antes, 300)
        self.assertEqual(persistente.despues, 1200)
        self.assertEqual(persistente.absoluta, 900)

    def test_nuevo(self):
        comparacion = self._comparacion()

        self.assertEqual([h.identificador for h in comparacion.nuevos], ["a-3"])
        self.assertEqual(comparacion.nuevos[0].antes, 0)

    def test_sin_hallazgos_en_ninguno(self):
        comparacion = comparar(_informe(), _informe(versiones={"0.2.0": 6}))

        self.assertEqual(comparacion.resueltos, ())
        self.assertEqual(comparacion.persistentes, ())
        self.assertEqual(comparacion.nuevos, ())


class TestAvisos(unittest.TestCase):
    def test_esquemas_distintos(self):
        comparacion = comparar(_informe(esquema=1), _informe(esquema=2, versiones={"0.2.0": 6}))

        self.assertTrue(any("esquemas distintos" in a for a in comparacion.avisos))

    def test_la_misma_version_en_los_dos(self):
        comparacion = comparar(_informe(), _informe())

        self.assertTrue(any("consigo misma" in a for a in comparacion.avisos))

    def test_una_ventana_con_varias_versiones(self):
        comparacion = comparar(
            _informe(versiones={"0.1.0": 3, "0.2.0": 3}), _informe(versiones={"0.3.0": 6})
        )

        self.assertTrue(any("mezcla varias versiones" in a for a in comparacion.avisos))

    def test_ventanas_de_tamano_muy_distinto(self):
        comparacion = comparar(
            _informe(sesiones=6), _informe(sesiones=2, versiones={"0.2.0": 2})
        )

        self.assertTrue(any("tamaño muy distinto" in a for a in comparacion.avisos))

    def test_una_ventana_vacia(self):
        comparacion = comparar(
            _informe(sesiones=0, versiones={}), _informe(versiones={"0.2.0": 6})
        )

        self.assertTrue(any("no tiene sesiones" in a for a in comparacion.avisos))

    def test_una_comparacion_limpia_no_avisa(self):
        comparacion = comparar(
            _informe(sesiones=6, versiones={"0.1.0": 6}),
            _informe(sesiones=5, versiones={"0.2.0": 5}),
        )

        self.assertEqual(comparacion.avisos, ())


class TestMarkdown(unittest.TestCase):
    def test_trae_las_cifras_de_los_dos_lados(self):
        # El veredicto tiene que poder emitirse sin volver a los
        # transcripts, así que la diferencia sola no basta.
        texto = a_markdown(
            comparar(_informe(coste=1_000_000), _informe(coste=750_000, versiones={"0.2.0": 6}))
        )

        self.assertIn("1,000,000", texto)
        self.assertIn("750,000", texto)
        self.assertIn("-250,000", texto)
        self.assertIn("-25.0%", texto)

    def test_lleva_las_tres_listas_de_hallazgos(self):
        texto = a_markdown(
            comparar(
                _informe(hallazgos=[_hallazgo("a-1")]),
                _informe(versiones={"0.2.0": 6}, hallazgos=[_hallazgo("a-2")]),
            )
        )

        for seccion in ("### Resueltos", "### Persistentes", "### Nuevos"):
            self.assertIn(seccion, texto)
        self.assertIn("Ninguno.", texto)

    def test_los_avisos_salen_arriba(self):
        texto = a_markdown(comparar(_informe(), _informe()))

        self.assertIn("## Avisos", texto)
        self.assertLess(texto.index("## Avisos"), texto.index("## Métricas"))

    def test_termina_en_salto_de_linea(self):
        texto = a_markdown(comparar(_informe(), _informe(versiones={"0.2.0": 6})))

        self.assertTrue(texto.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
