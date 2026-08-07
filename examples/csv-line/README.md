# Ejemplo: parser CSV (JavaScript) — con El Malo cazando de verdad

Código generado ejecutando `/gbu` con esta tarea:

> implementa en `examples/csv-line/` un parser CSV en JavaScript puro (Node, sin dependencias): `parseCsvLine(linea)` con campos entrecomillados, comillas escapadas `""` y errores de malformación, y `parseCsv(texto)` multilínea. Tests con el runner nativo `node:test`.

El plan está en [`PLAN.md`](PLAN.md) y la deuda pendiente en [`TECHNICAL_DEBT.md`](TECHNICAL_DEBT.md). Los tests se ejecutan desde la raíz del repo con:

```bash
node --test "examples/csv-line/*.test.mjs"
```

**Nota sobre este ejemplo**: en los otros dos ejemplos El Bueno sobrevivió a la primera y el bucle de corrección no llegó a verse. Aquí se forzó deliberadamente — y de forma honesta — combinando un dominio traicionero (parsear CSV con comillas es terreno clásico de fallos de borde) con **El Bueno corriendo en un modelo pequeño (Haiku) como subagente**, mientras El Malo conservaba el modelo grande de la sesión. Es la asimetría que el README del patrón describe en «Modelos por rol», usada al revés: un implementador modesto y un atacante fuerte. Ningún bug fue plantado: los que verás abajo los cometió Haiku de verdad y El Malo los encontró de verdad.

## Traza de la ejecución

- 🥸 **El Listo** genera el plan: 2 pasos (línea sin comillas; campos entrecomillados). Tras cerrarlos, el plan se amplió con un Paso 3 (`parseCsv` multilínea), que es donde saltó la liebre.

### Paso 1 — campos sin comillas

- 🤠 **El Bueno** (Haiku) implementa `parseCsvLine` para líneas sin comillas (26 líneas) y 7 tests. Suite en verde.
- 🌵 **El Malo** (lanzamiento 1/3) ataca tipos degenerados, coma fullwidth `，`, NUL, CRLF literal y 10.001 campos: `SOBREVIVIO_AL_MALO`. Deja 4 aserciones de regresión (solo strings primitivos, sin coerción) y observa que el `\r` final de un fichero CRLF queda como contenido — responsabilidad del llamante.
- 👺 **El Feo** (lanzamiento 1/3): `APROBADO_POR_EL_FEO`.

### Paso 2 — campos entrecomillados

- 🤠 **El Bueno** (Haiku) reescribe el parser como máquina de estados con comillas escapadas `""` y los tres `SyntaxError` (68 líneas). Suite en verde (14 tests).
- 🌵 **El Malo** (lanzamiento 1/3) ataca los clásicos: `'"""a"'`, recuentos impares de comillas, basura tras el cierre, comilla precedida de espacio, subrogados, `\r\n` dentro de comillas. Aguanta todo: `SOBREVIVIO_AL_MALO`, con 5 bloques adversarios de regresión.
- 👺 **El Feo** (lanzamiento 1/3): `APROBADO_POR_EL_FEO`.

### Paso 3 — `parseCsv` multilínea: el bucle de corrección

- 🤠 **El Bueno** (Haiku) implementa `parseCsv` troceando registros con su propio seguimiento de comillas y delegando cada línea en `parseCsvLine` (97 líneas). Suite en verde (27 tests).
- 🌵 **El Malo** (lanzamiento 1/3) **encuentra un fallo real**: `parseCsv('a"b\nc')` lanza el `SyntaxError` equivocado («comilla de cierre ausente» en vez de «comilla en campo sin entrecomillar»). Causa: `parseCsv` abría comillas ante cualquier `"` sin comprobar si el campo tenía contenido — un estado de comillas **duplicado y divergente** del de `parseCsvLine`. Deja el test de regresión en rojo y advierte: «si solo se parchea el mensaje, el modelo seguirá roto».
- 🤠 **El Bueno** corrige con un contador de caracteres desde la última frontera de campo. Suite en verde (33 tests).
- 🌵 **El Malo** (lanzamiento 2/3, verificación) confirma que lo reportado ya no se reproduce… **y caza el defecto espejo** que el parche acababa de abrir: `parseCsv('"a" "b"')` da ahora «sin entrecomillar» donde corresponde «contenido después de comilla de cierre», porque el contador no distinguía «campo con contenido» de «campo ya cerrado». Nuevo test de regresión en rojo. Segunda advertencia: «el problema es del modelo, no del parche».
- 🤠 **El Bueno** corrige de raíz esta vez: sustituye el contador por un autómata de 4 estados (vacío / con contenido / dentro / cerrado) que replica las ramas de `parseCsvLine`. Suite en verde (34 tests).
- 🌵 **El Malo** (lanzamiento 3/3, verificación): sonda diferencial exhaustiva — todas las cadenas hasta longitud 7 sobre el alfabeto conflictivo, 97.656 casos comparando `parseCsv` contra `parseCsvLine` en valor y diagnóstico. Sin divergencias: `SOBREVIVIO_AL_MALO`. Observación final: el autómata sigue **duplicado** (replicado, no compartido); hoy equivalente, mañana quién sabe.
- 👺 **El Feo** (lanzamiento 1/3) audita el paso completo tras las dos correcciones: `APROBADO_POR_EL_FEO`.
- El Sheriff anota en [`TECHNICAL_DEBT.md`](TECHNICAL_DEBT.md) las observaciones que piden decisión: el autómata duplicado y los prefijos de error inconsistentes.

**COMPLETADO CON ÉXITO** — 3 pasos, 34 tests, y en el Paso 3 el ciclo completo que da sentido al patrón: El Malo rompe, El Bueno parchea, El Malo rompe el parche, El Bueno corrige el modelo, El Malo lo machaca con 97.656 casos y firma. Las dos advertencias de El Malo sobre la causa raíz («el problema es del modelo, no del parche») resultaron proféticas: el primer arreglo cambió un fallo por su espejo, y solo la corrección estructural cerró el ciclo. Lo que quedó sin corregir no se perdió: está en la deuda técnica.
