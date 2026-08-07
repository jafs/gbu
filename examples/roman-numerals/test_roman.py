"""Tests de to_roman y from_roman."""

import unittest

from roman import from_roman, to_roman


class TestToRoman(unittest.TestCase):
    def test_valores_representativos(self):
        casos = {
            1: "I",
            4: "IV",
            9: "IX",
            14: "XIV",
            40: "XL",
            90: "XC",
            400: "CD",
            900: "CM",
            1994: "MCMXCIV",
            2026: "MMXXVI",
            3888: "MMMDCCCLXXXVIII",
        }
        for n, esperado in casos.items():
            with self.subTest(n=n):
                self.assertEqual(to_roman(n), esperado)

    def test_limites_del_rango(self):
        self.assertEqual(to_roman(1), "I")
        self.assertEqual(to_roman(3999), "MMMCMXCIX")

    def test_fuera_de_rango_lanza_valueerror(self):
        for n in (0, -1, 4000, 10_000):
            with self.subTest(n=n):
                with self.assertRaises(ValueError):
                    to_roman(n)

    def test_tipos_invalidos_lanzan_typeerror(self):
        for valor in (True, False, 3.0, "10", None, [7]):
            with self.subTest(valor=valor):
                with self.assertRaises(TypeError):
                    to_roman(valor)


class TestFromRoman(unittest.TestCase):
    def test_valores_representativos(self):
        casos = {
            "I": 1,
            "IV": 4,
            "IX": 9,
            "XIV": 14,
            "XL": 40,
            "XC": 90,
            "CD": 400,
            "CM": 900,
            "MCMXCIV": 1994,
            "MMXXVI": 2026,
            "MMMCMXCIX": 3999,
        }
        for s, esperado in casos.items():
            with self.subTest(s=s):
                self.assertEqual(from_roman(s), esperado)

    def test_malformados_y_no_canonicos_lanzan_valueerror(self):
        casos = (
            "",
            "IIII",
            "VX",
            "IC",
            "XM",
            "IXIX",
            "MMMM",
            "VV",
            "LL",
            "DD",
            "CMCM",
            "IVI",
            "xiv",
            "XIu",
            " XIV",
            "XIV ",
            "X IV",
            "XIV\n",
            "Ⅻ",
        )
        for s in casos:
            with self.subTest(s=s):
                with self.assertRaises(ValueError):
                    from_roman(s)

    def test_tipos_invalidos_lanzan_typeerror(self):
        for valor in (None, 14, 3.0, b"XIV", ["X"], True):
            with self.subTest(valor=valor):
                with self.assertRaises(TypeError):
                    from_roman(valor)


class TestIdaYVuelta(unittest.TestCase):
    def test_rango_completo(self):
        for n in range(1, 4000):
            with self.subTest(n=n):
                self.assertEqual(from_roman(to_roman(n)), n)


if __name__ == "__main__":
    unittest.main()
