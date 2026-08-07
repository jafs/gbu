# Ejemplo: conversor de números romanos (Python)

Código generado ejecutando `/gbu` con esta tarea:

> implementa en `examples/roman-numerals/` un conversor de números romanos en Python puro (sin dependencias): `to_roman(n)` y `from_roman(s)` con validación estricta (rangos 1–3999, romanos malformados rechazados con `ValueError`). Tests con `unittest` de la biblioteca estándar.

El plan que generó El Listo, con sus checkboxes ya marcados, está en [`PLAN.md`](PLAN.md). Los tests se ejecutan desde la raíz del repo con:

```bash
python -m unittest discover -s examples/roman-numerals -v
```

## Traza de la ejecución

- 🥸 **El Listo** genera el plan: 2 pasos (`to_roman` con validación de tipo y rango; `from_roman` con validación canónica estricta más el test de ida y vuelta 1–3999). El modo de ejecución venía decidido en el prompt (sin commit, dejar en staging, encadenar), así que el Sheriff no pregunta.

### Paso 1 — `to_roman`

- 🤠 **El Bueno** implementa `to_roman` con algoritmo greedy sobre una tabla de valores (41 líneas de producción) y 4 tests: valores representativos, límites 1/3999, fuera de rango, tipos inválidos. Suite en verde.
- 🌵 **El Malo** (lanzamiento 1/3) ataca: verifica las 3999 salidas con un decodificador independiente y una regex canónica, prueba tipos hostiles (`Fraction`, `Decimal`, `complex`, `nan`/`inf`, objetos con `__index__`, `True`/`False`) y rangos absurdos (`±10^18`). No encuentra nada: `SOBREVIVIO_AL_MALO`. Deja una **observación**: las subclases de `int` (p. ej. `IntEnum`) se aceptan — coherente con el contrato, no bloquea.
- 👺 **El Feo** (lanzamiento 1/3) audita el diff contra el plan: validación conforme al contrato, docstrings en el idioma del repo, tests sin asertos tautológicos. `APROBADO_POR_EL_FEO`.
- Paso cerrado: checkbox marcado, cambios a staging, sin commit.

### Paso 2 — `from_roman` + ida y vuelta

- 🤠 **El Bueno** implementa `from_roman` validando con una regex de forma canónica estricta antes de parsear (29 líneas de producción), amplía los tests con malformados (`IIII`, `VX`, `IC`, minúsculas, espacios…) y añade la ida y vuelta exhaustiva 1–3999. Suite en verde (8 tests).
- 🌵 **El Malo** (lanzamiento 1/3) ataca: la trampa del `$` con salto de línea final (`"XIV\n"`), Unicode adversario (numeral romano `Ⅻ`, letras de ancho completo `ＩＶ`), subclases de `str`, ReDoS con `"M" × 1 000 000`, y enumera **todas** las cadenas que la regex puede aceptar para comprobar que son exactamente las 3999 canónicas. No encuentra fallos: `SOBREVIVIO_AL_MALO`. Deja dos casos como **regresión en la suite** (`"XIV\n"` y `"Ⅻ"`), que es su única escritura permitida: tests, nunca producción.
- 👺 **El Feo** (lanzamiento 1/3): implementación conforme a la especificación, tests de regresión del QA adversario bien anotados. `APROBADO_POR_EL_FEO`.
- Paso cerrado: checkbox marcado, cambios a staging, sin commit.

**COMPLETADO CON ÉXITO** — 2 pasos, 8 tests, un solo lanzamiento de cada verificador por paso. En esta ejecución El Bueno sobrevivió a la primera en ambos pasos; las observaciones de El Malo quedaron registradas arriba y sus casos adversarios montaron guardia en la suite.
