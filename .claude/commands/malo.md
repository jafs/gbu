---
description: "🌵 El Malo: QA adversario (se ejecuta como subagente aislado)"
argument-hint: "opcional: fichero de plan, paso implementado, archivos modificados y tamaño del cambio"
---

Este fichero define **el encargo de El Malo**: qué datos hay que darle al lanzarlo. Es la única definición del encargo — `/gbu` la referencia en su FASE 2 en vez de repetirla.

El subagente en sí está definido en `.claude/agents/malo.md`.

---

# El encargo

Lanza el subagente `malo` con la herramienta de agentes.

No adoptes su rol tú: el ataque debe hacerse en un contexto aislado, sin el historial de esta conversación.

En el encargo indícale únicamente estos campos:

- la ruta del fichero de plan (por defecto `PLAN.md`)
- el paso del plan que se acaba de implementar
- la lista de archivos modificados, **incluidos los nuevos sin trackear** (no salen en `git diff` sin un `git add -N` previo)
- el tamaño del cambio en líneas de producción

Si es una **verificación** (relanzamiento tras un informe de fallos, o pasada acotada tras una corrección funcional de la FASE 3), añade además:

- el informe que motiva la verificación, íntegro (el suyo anterior, o las desviaciones funcionales de El Feo)
- la lista de archivos tocados por la corrección
- el tamaño re-medido **sobre la corrección**, no sobre el paso entero

Sin el informe no puede acotar la verificación y repetirá la batería completa.

Si te falta alguno de los campos, **calcúlalo antes de lanzar**. No lo dejes a que lo deduzca él: un encargo incompleto le hace medir mal el esfuerzo y atacar de menos.

No le resumas la implementación ni las decisiones tomadas: debe atacar solo lo que hay en disco.

---

# Uso manual

Si has llegado aquí por `/gbu`, ignora esta sección: la orquestación (cuándo entra, cuántos lanzamientos, qué hacer con el veredicto) la lleva `gbu.md`.

Invocado a mano, sobre un cambio suelto:

1. Si se han proporcionado argumentos ($ARGUMENTS), inclúyelos en el encargo.
2. Reúne los campos de arriba y lanza el subagente.
3. Cuando termine, muestra al usuario su respuesta íntegra: `SOBREVIVIO_AL_MALO` o el informe de reproducción.

Aquí no hay rondas automáticas: una invocación, un veredicto. Corregir es decisión del usuario.
