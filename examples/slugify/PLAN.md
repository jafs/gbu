# Plan: slugify para URLs

## Tarea

Implementar en `examples/slugify/` una función `slugify(texto)` en JavaScript puro (Node, sin dependencias) que convierta un texto arbitrario en un slug apto para URLs:

- minúsculas; letras latinas con diacríticos reducidas a su base ASCII (`"Café"` → `"cafe"`, `"añejo"` → `"anejo"`)
- toda secuencia de caracteres no alfanuméricos (espacios, puntuación, símbolos, emoji…) se convierte en un único guion `-`
- sin guiones al principio ni al final; nunca guiones consecutivos
- la cadena vacía o sin ningún carácter alfanumérico produce `""`
- los tipos que no sean `string` lanzan `TypeError`

Supuestos adoptados (los más simples, documentados aquí):

- Solo se transliteran los diacríticos latinos separables por normalización Unicode NFKD (más el caso `ß` → `ss` no cubierto por NFKD); los caracteres de otros alfabetos (cirílico, CJK, emoji) no se transliteran: se tratan como no alfanuméricos y colapsan en guion.
- «Alfanumérico» significa ASCII `[a-z0-9]` tras la normalización.

## Contexto

- Este directorio es un ejemplo autocontenido dentro del repositorio del patrón GBU; no hay convenciones de código previas. Comentarios y nombres en español, coherentes con el idioma del repositorio.
- Node.js 24, ESM con extensión `.mjs`, solo módulos de la plataforma. Prohibido añadir dependencias ni `package.json`.
- Ficheros de producción: `examples/slugify/slugify.mjs` (único módulo, exporta `slugify` como export con nombre).
- Tests: runner nativo `node:test` con `node:assert/strict`, en `examples/slugify/slugify.test.mjs` (patrón de nombres `*.test.mjs`, en el mismo directorio que el código).
- Comando de tests (desde la raíz del repo): `node --test "examples/slugify/*.test.mjs"` (pasar el directorio a secas no resuelve en Node 24 sobre Windows)
- Lint, build y chequeo de tipos: no hay herramientas configuradas en este repo. Como comprobación mínima de sintaxis se usa `node --check examples/slugify/slugify.mjs`; lint y tipos: no aplica.

## Modo de ejecución

- **Al cerrar cada paso**: nada, dejar en staging
- **Formato de commit**: no aplica
- **Entre pasos**: encadenar el siguiente
- **Notas del usuario**: stagear únicamente los ficheros de `examples/slugify/`; no stagear nada fuera de esa carpeta. Sin commit ni push.

## Pasos

- [x] Paso 1: Implementar `slugify(texto)` en `examples/slugify/slugify.mjs` para entrada ASCII: minúsculas, colapso de no alfanuméricos en un solo guion, recorte de guiones extremos, `""` para entradas sin alfanuméricos y `TypeError` para no-`string`; con sus tests en `examples/slugify/slugify.test.mjs` (frases con espacios y puntuación, guiones repetidos, extremos, cadena vacía, tipos inválidos).
- [x] Paso 2: Añadir la transliteración de diacríticos latinos vía NFKD (y `ß` → `ss`) antes del colapso, y ampliar los tests: acentos y eñes, ligaduras, textos mixtos con emoji y alfabetos no latinos que colapsan en guion.
