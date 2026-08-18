"""Tests del tipo hallazgo y de sus funciones de orden y agrupación."""

import unittest

from hallazgos import (
    ALTA,
    BAJA,
    MEDIA,
    Evidencia,
    Hallazgo,
    agrupar,
    fusionar,
    normalizar_clave,
    ordenar,
    resumen_por_severidad,
    tokens_totales,
)


def _hallazgo(categoria="relectura", severidad=MEDIA, clave="a.py", tokens=100, titulo="t", evidencias=()):
    return Hallazgo(
        categoria=categoria,
        severidad=severidad,
        titulo=titulo,
        clave=clave,
        tokens=tokens,
        evidencias=tuple(evidencias),
    )


class TestIdentificador(unittest.TestCase):
    def test_dos_hallazgos_equivalentes_reciben_el_mismo_identificador(self):
        # Mismo problema detectado en dos ejecuciones distintas: cambia lo
        # que costó, cambia dónde se vio, cambia hasta el título; el
        # problema es el mismo.
        primero = _hallazgo(tokens=100, titulo="Fichero releído 3 veces")
        segundo = _hallazgo(
            tokens=250,
            titulo="Fichero releído 5 veces",
            evidencias=[Evidencia(sesion="otra", turno=99)],
        )

        self.assertEqual(primero.identificador, segundo.identificador)

    def test_hallazgos_distintos_no_colisionan(self):
        identificadores = {
            _hallazgo(clave="a.py").identificador,
            _hallazgo(clave="b.py").identificador,
            _hallazgo(categoria="comando", clave="a.py").identificador,
        }

        self.assertEqual(len(identificadores), 3)

    def test_el_identificador_no_depende_de_la_posicion(self):
        lista = [_hallazgo(clave="a.py"), _hallazgo(clave="b.py"), _hallazgo(clave="c.py")]

        antes = [h.identificador for h in lista]
        despues = [h.identificador for h in reversed(list(reversed(lista)))]

        self.assertEqual(antes, despues)
        self.assertEqual(
            {h.identificador for h in lista},
            {h.identificador for h in ordenar(lista)},
        )

    def test_lleva_la_categoria_delante(self):
        self.assertTrue(_hallazgo(categoria="relectura").identificador.startswith("relectura-"))

    def test_la_misma_ruta_con_separadores_distintos_es_el_mismo_hallazgo(self):
        unix = _hallazgo(clave="src/modules/a.ts")
        windows = _hallazgo(clave="src\\modules\\a.ts")

        self.assertEqual(unix.identificador, windows.identificador)


class TestNormalizarClave(unittest.TestCase):
    def test_unifica_separadores_mayusculas_y_espacios(self):
        self.assertEqual(normalizar_clave("  C:\\Tmp\\A.py  "), "c:/tmp/a.py")
        self.assertEqual(normalizar_clave("git   status\n--short"), "git status --short")

    def test_clave_vacia(self):
        self.assertEqual(normalizar_clave(""), "")
        self.assertEqual(normalizar_clave(None), "")


class TestOrdenar(unittest.TestCase):
    def test_por_severidad_y_luego_por_coste(self):
        baja = _hallazgo(severidad=BAJA, clave="baja", tokens=9999)
        media_cara = _hallazgo(severidad=MEDIA, clave="media-cara", tokens=500)
        media_barata = _hallazgo(severidad=MEDIA, clave="media-barata", tokens=10)
        alta = _hallazgo(severidad=ALTA, clave="alta", tokens=1)

        ordenados = ordenar([baja, media_barata, alta, media_cara])

        self.assertEqual(
            [h.clave for h in ordenados], ["alta", "media-cara", "media-barata", "baja"]
        )

    def test_severidad_desconocida_va_al_final(self):
        raro = _hallazgo(severidad="rarisima", clave="raro", tokens=9999)
        baja = _hallazgo(severidad=BAJA, clave="baja", tokens=1)

        self.assertEqual([h.clave for h in ordenar([raro, baja])], ["baja", "raro"])

    def test_lista_vacia(self):
        self.assertEqual(ordenar([]), ())


class TestFusionar(unittest.TestCase):
    def test_suma_tokens_y_concatena_evidencias(self):
        primero = _hallazgo(tokens=100, evidencias=[Evidencia(sesion="s1", turno=3)])
        segundo = _hallazgo(tokens=250, evidencias=[Evidencia(sesion="s2", turno=7)])

        (fundido,) = fusionar([primero, segundo])

        self.assertEqual(fundido.tokens, 350)
        self.assertEqual([e.sesion for e in fundido.evidencias], ["s1", "s2"])

    def test_gana_la_severidad_mas_alta(self):
        (fundido,) = fusionar(
            [_hallazgo(severidad=BAJA, tokens=1), _hallazgo(severidad=ALTA, tokens=1)]
        )

        self.assertEqual(fundido.severidad, ALTA)

    def test_no_funde_hallazgos_distintos(self):
        fundidos = fusionar([_hallazgo(clave="a.py"), _hallazgo(clave="b.py")])

        self.assertEqual(len(fundidos), 2)

    def test_conserva_el_orden_de_primera_aparicion(self):
        fundidos = fusionar(
            [_hallazgo(clave="b.py"), _hallazgo(clave="a.py"), _hallazgo(clave="b.py")]
        )

        self.assertEqual([h.clave for h in fundidos], ["b.py", "a.py"])

    def test_lista_vacia(self):
        self.assertEqual(fusionar([]), ())


class TestAgrupar(unittest.TestCase):
    def test_categorias_mas_costosas_delante(self):
        grupos = agrupar(
            [
                _hallazgo(categoria="barata", clave="x", tokens=10),
                _hallazgo(categoria="cara", clave="y", tokens=1000),
                _hallazgo(categoria="cara", clave="z", tokens=5),
            ]
        )

        self.assertEqual(list(grupos), ["cara", "barata"])
        self.assertEqual([h.clave for h in grupos["cara"]], ["y", "z"])

    def test_sin_hallazgos(self):
        self.assertEqual(agrupar([]), {})


class TestResumenes(unittest.TestCase):
    def test_tokens_totales(self):
        self.assertEqual(tokens_totales([_hallazgo(tokens=100), _hallazgo(tokens=5)]), 105)

    def test_resumen_por_severidad_ordenado(self):
        resumen = resumen_por_severidad(
            [
                _hallazgo(severidad=BAJA, clave="a"),
                _hallazgo(severidad=ALTA, clave="b"),
                _hallazgo(severidad=BAJA, clave="c"),
            ]
        )

        self.assertEqual(list(resumen), [ALTA, BAJA])
        self.assertEqual(resumen[BAJA], 2)


if __name__ == "__main__":
    unittest.main()
