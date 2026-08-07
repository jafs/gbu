# Ejemplo: slugify (JavaScript)

Código generado ejecutando `/gbu` con esta tarea:

> implementa en `examples/slugify/` una función `slugify(texto)` en JavaScript puro (Node, sin dependencias) que convierta un texto arbitrario en un slug apto para URLs, con transliteración de diacríticos latinos y `TypeError` para tipos que no sean string. Tests con el runner nativo `node:test`.

El plan que generó El Listo, con sus checkboxes ya marcados, está en [`PLAN.md`](PLAN.md). Los tests se ejecutan desde la raíz del repo con:

```bash
node --test "examples/slugify/*.test.mjs"
```

## Traza de la ejecución

- 🥸 **El Listo** genera el plan: 2 pasos (slugify para entrada ASCII; transliteración de diacríticos vía NFKD). Documenta los supuestos: solo se transliteran los diacríticos separables por NFKD más `ß` → `ss`; el resto de alfabetos colapsa en guion.

### Paso 1 — slugify ASCII

- 🤠 **El Bueno** implementa `slugify` (12 líneas de producción: minúsculas, colapso de no alfanuméricos en un guion, recorte de extremos, `TypeError` para no-string) y 5 tests. Al ejecutar la suite descubre que el comando del Contexto (`node --test examples/slugify/`) no resuelve en Node 24 sobre Windows; el Sheriff corrige el comando en el plan por el glob equivalente antes de lanzar a los verificadores.
- 🌵 **El Malo** (lanzamiento 1/3) ataca: tipos hostiles (`function`, `bigint`, `new String("a")`), rendimiento con 4 millones de caracteres y 2 millones de separadores (sin backtracking patológico). No cae nada dentro del alcance del paso: `SOBREVIVIO_AL_MALO`. Deja tres **observaciones** sobre entrada no-ASCII que condicionan el diseño del Paso 2: `"İstanbul"` → `"i-stanbul"` (el combinante que suelta `toLowerCase` genera un guion espurio), el signo Kelvin `K` colándose como `k`, y `"Straße"` → `"stra-e"` como comportamiento provisional que el Paso 2 debe redefinir.
- 👺 **El Feo** (lanzamiento 1/3) audita: implementación y tests exactamente los del paso, transliteración correctamente diferida. `APROBADO_POR_EL_FEO`.
- Paso cerrado: checkbox marcado, cambios a staging, sin commit.

### Paso 2 — diacríticos vía NFKD

- 🤠 **El Bueno** añade la normalización guiándose por las observaciones de El Malo: NFKD y eliminación de marcas combinantes **antes** de minusculizar (evita el `"i-stanbul"`), después `ß` → `ss` y el colapso. Amplía los tests: acentos, `İstanbul`, `Straße`/`STRAẞE`, ligaduras (`ﬁle`, `Ǳ`, `№`), emoji y alfabetos no latinos. Suite en verde (8 tests).
- 🌵 **El Malo** (lanzamiento 1/3) ataca: entrada ya descompuesta (NFD), marcas combinantes apiladas, ligaduras de anchura completa, superíndices y fracciones, surrogates sueltos, soft hyphen, ZWJ, dígrafos titlecase. Nada contradice el contrato: `SOBREVIVIO_AL_MALO`. Deja 4 aserciones como **regresión en la suite** (entrada NFD, marcas apiladas, `"ＡＢＣ１２"` → `"abc12"`) y dos **observaciones**: las letras sin descomposición NFKD (`ø`, `œ`, `ł`…) colapsan en guion (`"søren"` → `"s-ren"`, exactamente lo que declara el supuesto del plan, pero un slug pobre — corregirlo exigiría una tabla de transliteración, es decir, cambiar el supuesto), y la compatibilidad NFKD funde símbolos como `™` con la palabra adyacente (`"producto™"` → `"productotm"`).
- 👺 **El Feo** (lanzamiento 1/3): `APROBADO_POR_EL_FEO`, sin más comentario.
- Paso cerrado: checkbox marcado, cambios a staging, sin commit.

**COMPLETADO CON ÉXITO** — 2 pasos, 8 tests, un solo lanzamiento de cada verificador por paso. Lo más ilustrativo de esta ejecución: las observaciones que El Malo dejó al atacar el Paso 1 (sin bloquearlo, porque quedaban fuera de su alcance) guiaron el diseño del Paso 2, y sus casos adversarios quedaron montando guardia en la suite.
