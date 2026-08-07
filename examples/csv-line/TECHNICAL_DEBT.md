# Deuda técnica

Registro que mantiene el Sheriff con lo que El Malo encontró u observó y quedó sin corregir. Cada entrada dice qué haría falta para saldarla; si existe un test omitido (skip) que la reproduce, reactivarlo es retomar la deuda.

## 2026-08-07 — Paso 3: autómata de estados duplicado entre `parseCsv` y `parseCsvLine`

- **Hallazgo**: `parseCsv` replica las ramas del autómata de `parseCsvLine` (vacío / con contenido / dentro de comillas / cerrado) en vez de compartirlas, y cada línea se valida dos veces (eager al trocear registros y de nuevo al delegar en `parseCsvLine`). Las dos primeras versiones de esa réplica produjeron diagnósticos de `SyntaxError` equivocados (`parseCsv('a"b\nc')` y `parseCsv('"a" "b"')`), corregidos en el paso; la equivalencia actual está verificada empíricamente por sonda diferencial hasta longitud 7 y vigilada por los tests de regresión de El Malo.
- **Riesgo**: cualquier cambio futuro en una de las dos máquinas puede desincronizarlas sin que los tests existentes lo detecten en casos nuevos.
- **Test omitido**: no hay (nada quedó en rojo; los tests de regresión de las divergencias conocidas están en verde).
- **Para saldarla**: extraer el autómata a una función interna compartida que usen ambos exports, de modo que la divergencia sea imposible por construcción.

## 2026-08-07 — Paso 3: prefijos de error inconsistentes según la capa que detecta

- **Hallazgo**: los `SyntaxError` lanzados directamente por `parseCsv` llevan prefijo `parseCsv:` y los que aflora la delegación llevan `parseCsvLine:`, aunque el consumidor llamó a `parseCsv`. Los mensajes tampoco incluyen la posición (línea/columna) del carácter ofensor, lo que dificulta diagnosticar documentos largos.
- **Test omitido**: no hay (los tests comprueban el cuerpo del mensaje, no el prefijo).
- **Para saldarla**: unificar el prefijo al punto de entrada público y añadir posición al mensaje; decidirlo como criterio antes de tocar los mensajes, porque los tests de regresión fijan sus cuerpos actuales.
