---
description: "👺 El Feo: Auditor estricto del código (se ejecuta como subagente aislado)"
argument-hint: "opcional: fichero de plan, paso implementado, fichero de diff, números de test/lint/build/tipos y tamaño"
---

Este fichero define **el encargo de El Feo**: qué datos hay que darle al lanzarlo. Es la única definición del encargo — `/gbu` la referencia en su FASE 3 en vez de repetirla.

El subagente en sí está definido en `.claude/agents/feo.md`.

---

# El encargo

Lanza el subagente `feo` con la herramienta de agentes.

No adoptes su rol tú: la auditoría debe hacerse en un contexto aislado, sin el historial de esta conversación.

En el encargo indícale únicamente estos campos:

- la ruta del fichero de plan (por defecto `PLAN.md`)
- el paso del plan que se acaba de implementar
- **la ruta de un fichero con el diff** del paso —que incluye los tests que haya dejado El Malo— y la lista de ficheros nuevos sin trackear (los *untracked* no salen en `git diff` sin un `git add -N` previo)
- los resultados de `test`, `lint`, `build` y chequeo de tipos, **con sus números**
- el tamaño del cambio en líneas de producción
- **la superficie de riesgo**: las etiquetas de la sección «La superficie de riesgo» de `gbu.md` y dónde está ese riesgo dentro del cambio

El diff y los números deben ser los **del momento del lanzamiento**: si ha habido una corrección desde que se generaron, regenéralos. Un diff obsoleto le hace re-reportar lo ya corregido.

Hay una excepción, y es legítima: cuando el cambio no ha podido alterar lo que un verificador mide —un paso de solo documentación, por ejemplo—, ese verificador no se ejecuta. Entonces le pasas los números de la última ejecución válida diciéndole **de cuándo son y por qué el paso no los ha vuelto a generar**. Con esa explicación el encargo está completo y El Feo audita con ellos; sin ella, unos números que no cuadran con el diff parecen un descuido y los reclamará.

Si es una **verificación** (relanzamiento tras un Informe de Desviaciones), añade además:

- el Informe de Desviaciones anterior íntegro
- la lista de archivos tocados por la corrección y, si alguno venía de un paso anterior del plan, **cuál y por qué hubo que tocarlo** (regla 14 de `bueno.md`): sin eso lo lee como alcance inventado y lo reporta
- **la ruta de un segundo fichero con el diff de la corrección**: solo lo que ha cambiado desde que se emitió ese informe

Sin ellos no puede acotar la verificación y repetirá la auditoría completa.

En la verificación le llegan por tanto **dos** diffs, y hay que decirle cuál es cuál: **audita el de la corrección**, y el del paso completo lo tiene solo como contexto, para detectar que la corrección no encaje con el resto del paso (un puerto que cambia y un consumidor que se queda atrás). Sin el segundo, una corrección coherente consigo misma pero incoherente con lo ya aprobado pasaría desapercibida.

**El Feo no ejecuta nada, y no tiene con qué hacerlo**: sus herramientas son de lectura. Si no le das el diff en un fichero y los números ya hechos, no puede auditar. Genera el diff antes de lanzarlo:

```bash
git add -N . && git diff > <ruta-temporal>/gbu-diff.txt
```

La `<ruta-temporal>` debe cumplir dos cosas: estar **fuera del repo** (un fichero dentro aparecería en el propio diff) y ser una ruta absoluta que la herramienta `Read` de El Feo pueda abrir tal cual. Pásale exactamente esa ruta.

No le resumas la implementación ni las decisiones tomadas: debe juzgar solo lo que hay en disco.

---

# Uso manual

Si has llegado aquí por `/gbu`, ignora esta sección: la orquestación (cuándo entra, cuántos lanzamientos, qué hacer con el veredicto) la lleva `gbu.md`.

Invocado a mano, sobre un cambio suelto:

1. Si se han proporcionado argumentos ($ARGUMENTS), inclúyelos en el encargo.
2. Reúne los campos de arriba —ejecutando `test`, `lint`, `build` y el chequeo de tipos si aún no tienes sus números— y lanza el subagente.
3. Cuando termine, muestra al usuario su respuesta íntegra: `APROBADO_POR_EL_FEO` o el Informe de Desviaciones.

Aquí no hay rondas automáticas: una invocación, un veredicto. Corregir es decisión del usuario.
