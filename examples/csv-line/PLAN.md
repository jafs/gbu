# Plan: parser de una línea CSV

## Tarea

Implementar en `examples/csv-line/` una función `parseCsvLine(linea)` en JavaScript puro (Node, sin dependencias) que convierta una línea CSV en un array de strings con sus campos:

- los campos se separan por comas; los campos vacíos son válidos (`"a,,b"` → `["a", "", "b"]`, `"a,"` → `["a", ""]`, `""` → `[""]`)
- un campo puede ir entrecomillado con comillas dobles; dentro conserva comas, espacios y saltos de línea literales, y las comillas se escapan doblándolas (`"a,""b"",c"` es el campo `a,"b",c`)
- los campos no entrecomillados se toman tal cual (sin recortar espacios)
- línea malformada → `SyntaxError`: comilla de cierre ausente (`"abc`), contenido tras cerrar comillas (`"a"x`), o comillas dobles dentro de un campo sin entrecomillar (`a"b`)
- los tipos que no sean `string` lanzan `TypeError`

Ampliación (añadida al plan tras cerrar el Paso 2): una segunda función `parseCsv(texto)` que parsea un documento CSV completo y devuelve un array de registros (array de arrays de strings):

- los registros se separan por `\n` o `\r\n` **fuera de comillas**; dentro de un campo entrecomillado un salto de línea es contenido literal del campo, nunca un separador de registros
- un único terminador de línea al final del texto no produce un registro vacío extra (`"a,b\n"` → `[["a","b"]]`), pero una línea vacía entre registros sí es un registro con un único campo vacío (`"a\n\nb"` → `[["a"],[""],["b"]]`)
- el texto vacío produce `[]`
- las mismas reglas de comillas y los mismos `SyntaxError` que `parseCsvLine`; `TypeError` para no-`string`
- no se valida que todos los registros tengan el mismo número de campos

Supuestos adoptados (los más simples, documentados aquí):

- `parseCsvLine` parsea una sola línea: no divide registros; para ella un salto de línea es contenido literal (dentro o fuera de comillas). Dividir en registros es trabajo exclusivo de `parseCsv`.
- Un `\r` que no vaya seguido de `\n` no es terminador de registro: es contenido literal del campo.
- No hay opción de cambiar el separador ni el carácter de comillas.

## Contexto

- Este directorio es un ejemplo autocontenido dentro del repositorio del patrón GBU; no hay convenciones de código previas. Comentarios y nombres en español, coherentes con el idioma del repositorio.
- Node.js 24, ESM con extensión `.mjs`, solo módulos de la plataforma. Prohibido añadir dependencias ni `package.json`.
- Ficheros de producción: `examples/csv-line/csv.mjs` (único módulo, exporta `parseCsvLine` como export con nombre).
- Tests: runner nativo `node:test` con `node:assert/strict`, en `examples/csv-line/csv.test.mjs` (patrón de nombres `*.test.mjs`, en el mismo directorio que el código).
- Comando de tests (desde la raíz del repo): `node --test "examples/csv-line/*.test.mjs"` (pasar el directorio a secas no resuelve en Node 24 sobre Windows)
- Lint, build y chequeo de tipos: no hay herramientas configuradas en este repo. Como comprobación mínima de sintaxis se usa `node --check examples/csv-line/csv.mjs`; lint y tipos: no aplica.

## Modo de ejecución

- **Al cerrar cada paso**: nada, dejar en staging
- **Formato de commit**: no aplica
- **Entre pasos**: encadenar el siguiente
- **Notas del usuario**: stagear únicamente los ficheros de `examples/csv-line/`; no stagear nada fuera de esa carpeta. Sin commit ni push.

## Pasos

- [x] Paso 1: Implementar `parseCsvLine(linea)` en `examples/csv-line/csv.mjs` para líneas sin comillas: separación por comas, campos vacíos (incluidos el inicial, el final y la línea vacía) y `TypeError` para no-`string`; con sus tests en `examples/csv-line/csv.test.mjs`. Las comillas dobles quedan para el Paso 2: en este paso una comilla en la línea es un carácter más del campo.
- [x] Paso 2: Añadir los campos entrecomillados: comas y saltos de línea literales dentro de comillas, comillas escapadas `""`, y los tres casos de `SyntaxError` (cierre ausente, contenido tras cerrar, comillas en campo sin entrecomillar — este último caso sustituye al comportamiento provisional del Paso 1); ampliar los tests con todos ellos.
- [x] Paso 3: Implementar `parseCsv(texto)` en `examples/csv-line/csv.mjs` (export con nombre adicional) según la ampliación de la Tarea: registros por `\n`/`\r\n` fuera de comillas, saltos literales dentro de comillas, sin registro fantasma por el terminador final, `[]` para texto vacío y los mismos errores; ampliar los tests con documentos multilínea (campos con saltos dentro de comillas, `\r\n`, terminador final, líneas vacías intermedias).
