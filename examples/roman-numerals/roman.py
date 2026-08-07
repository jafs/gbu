"""Conversor de números romanos en forma canónica estricta.

Solo se admite la notación sustractiva estándar (IV, IX, XL, XC, CD, CM),
en el rango 1-3999.
"""

import re

# Forma canónica estricta: como fullmatch acepta la cadena vacía,
# from_roman la rechaza aparte.
_CANONICO = re.compile(
    r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})"
)

_VALORES = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)


def to_roman(n):
    """Convierte un entero en su numeral romano canónico.

    Acepta únicamente enteros en el rango 1-3999. Fuera de rango lanza
    ValueError. Los tipos que no sean int (incluido bool) lanzan TypeError.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"se esperaba int, no {type(n).__name__}")
    if not 1 <= n <= 3999:
        raise ValueError(f"fuera del rango 1-3999: {n}")

    resultado = []
    restante = n
    for valor, simbolo in _VALORES:
        while restante >= valor:
            resultado.append(simbolo)
            restante -= valor
    return "".join(resultado)


def from_roman(s):
    """Convierte un numeral romano canónico en entero.

    Acepta únicamente cadenas en forma canónica estricta y en mayúsculas.
    Las cadenas malformadas o no canónicas lanzan ValueError. Los tipos
    que no sean str lanzan TypeError.
    """
    if not isinstance(s, str):
        raise TypeError(f"se esperaba str, no {type(s).__name__}")
    if not s or not _CANONICO.fullmatch(s):
        raise ValueError(f"numeral romano no canónico: {s!r}")

    resultado = 0
    restante = s
    for valor, simbolo in _VALORES:
        while restante.startswith(simbolo):
            resultado += valor
            restante = restante[len(simbolo):]
    return resultado
