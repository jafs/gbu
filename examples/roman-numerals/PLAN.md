# Plan: Conversor de números romanos

## Tarea

Implementar en `examples/roman-numerals/` un conversor de números romanos en Python puro, sin dependencias externas, con dos funciones públicas:

- `to_roman(n)`: convierte un entero en su numeral romano canónico. Acepta únicamente enteros en el rango 1–3999; fuera de rango lanza `ValueError`. Los tipos que no sean `int` (incluido `bool`, que en Python es subclase de `int` pero no representa una cantidad) lanzan `TypeError`.
- `from_roman(s)`: convierte un numeral romano en entero. Acepta únicamente cadenas en forma canónica estricta y en mayúsculas (`"XIV"` sí; `"xiv"`, `"IIII"`, `"IXIX"`, `""` no); cualquier cadena malformada o no canónica lanza `ValueError`. Los tipos que no sean `str` lanzan `TypeError`.

Propiedad de ida y vuelta: `from_roman(to_roman(n)) == n` para todo `n` en 1–3999.

Supuestos adoptados (los más simples, documentados aquí):

- «Forma canónica estricta» significa exactamente la cadena que produce `to_roman`: notación sustractiva estándar (IV, IX, XL, XC, CD, CM), sin repeticiones de más de tres símbolos ni formas alternativas equivalentes.
- No se aceptan espacios ni caracteres de relleno alrededor del numeral: la validación es sobre la cadena exacta.

## Contexto

- Este directorio es un ejemplo autocontenido dentro del repositorio del patrón GBU; el resto del repo son ficheros markdown sin código. No hay `CLAUDE.md` ni convenciones de código previas: se aplica PEP 8 y docstrings en español, coherentes con el idioma del repositorio.
- Python 3.10, solo biblioteca estándar. Prohibido añadir dependencias.
- Ficheros de producción: `examples/roman-numerals/roman.py` (único módulo).
- Tests: framework `unittest` de la biblioteca estándar, en `examples/roman-numerals/test_roman.py` (patrón de nombres `test_*.py`, en el mismo directorio que el código).
- Comando de tests (desde la raíz del repo): `python -m unittest discover -s examples/roman-numerals -v`
- Lint, build y chequeo de tipos: no hay herramientas configuradas en este repo. Como comprobación mínima de sintaxis se usa `python -m py_compile examples/roman-numerals/roman.py`; lint y tipos: no aplica.

## Modo de ejecución

- **Al cerrar cada paso**: nada, dejar en staging
- **Formato de commit**: no aplica
- **Entre pasos**: encadenar el siguiente
- **Notas del usuario**: stagear únicamente los ficheros de `examples/roman-numerals/`; no stagear nada fuera de esa carpeta. Sin commit ni push.

## Pasos

- [x] Paso 1: Implementar `to_roman(n)` en `examples/roman-numerals/roman.py` con validación de tipo (`TypeError` para no-`int` y `bool`) y de rango (`ValueError` fuera de 1–3999), junto con sus tests en `examples/roman-numerals/test_roman.py` (valores representativos, límites 1 y 3999, fuera de rango, tipos inválidos).
- [x] Paso 2: Implementar `from_roman(s)` en el mismo módulo con validación estricta de forma canónica (`ValueError` para malformados o no canónicos, `TypeError` para no-`str`), ampliar `test_roman.py` (casos válidos, malformados, no canónicos como `"IIII"` o `"VX"`, cadena vacía, minúsculas) y añadir el test de ida y vuelta completo 1–3999.
