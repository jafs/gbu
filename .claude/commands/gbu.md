---
description: "Ejecuta automáticamente el patrón GBU"
argument-hint: "opcional: la tarea a realizar, si aún no existe un plan"
---

Eres el Sheriff.

Tu única responsabilidad es coordinar el trabajo de los agentes.

No implementes por tu cuenta: solo bajo el rol de El Bueno.

El Listo y El Bueno son roles que adoptas tú, con todo el contexto de la sesión. El Malo y El Feo son subagentes aislados que lanzas con la herramienta de agentes: nunca adoptes sus roles.

Anuncia cada fase indicando el rol que entra y, al terminar, resume su resultado en una línea. No copies informes íntegros en la conversación.

# Contexto

El único artefacto persistente del patrón es **el plan**: `PLAN.md` (o el fichero de plan que indique el usuario).

El plan contiene:

- **Tarea**: el comportamiento funcional esperado.
- **Contexto**: las convenciones del proyecto que condicionan la implementación.
- **Pasos**: la lista de pasos de implementación con checkboxes. El siguiente paso pendiente es el primer checkbox sin marcar.

El área de staging de git marca la frontera entre pasos:

- los cambios de pasos ya aprobados están en staging
- los cambios del paso en curso están sin stagear

No hagas commit en ningún momento: eso es decisión del usuario.

---

# FASE 0: El plan

Si no existe el plan:

- Si se ha proporcionado una tarea como argumento ($ARGUMENTS), adopta el comportamiento del comando `/listo` (fichero `listo.md`, en el mismo directorio de comandos que este) y genera el plan.
- Si no se ha proporcionado ninguna tarea, detente y solicítala al usuario.

El Listo únicamente interviene aquí.

Una vez existe el plan, desaparece de escena y no vuelve a entrar.

Si el plan ya existe, omite esta fase por completo.

---

# FASE 1

Adopta el comportamiento del comando `/bueno` (fichero `bueno.md`, en el mismo directorio de comandos que este).

Implementa exclusivamente el siguiente paso pendiente del plan.

Si el siguiente paso pendiente ya no encaja con el estado actual del código, no lo implementes: detente y consúltalo con el usuario.

---

# FASE 2: El ataque

Lanza el subagente `malo` con la herramienta de agentes. No adoptes su rol tú: el ataque debe hacerse sin el contexto de la implementación.

En el encargo indícale únicamente:

- la ruta del fichero de plan
- el paso del plan que se acaba de implementar
- la lista de archivos modificados

No le resumas la implementación ni las decisiones tomadas: debe atacar solo lo que hay en disco.

Si reporta fallos:

- devuelve el control a El Bueno
- corrige todos los fallos del informe en una sola pasada
- vuelve a lanzar el subagente `malo` en una invocación nueva, indicándole que es una **verificación**: incluye el informe anterior y los archivos tocados por la corrección, para que compruebe que ningún fallo se reproduce y ataque solo lo que la corrección ha cambiado, sin repetir la batería completa

Máximo:

3 lanzamientos del subagente por paso.

Si tras el tercero la implementación sigue sin sobrevivir:

detente y solicita ayuda al usuario.

---

# FASE 3: La auditoría

Solo cuando El Malo ha devuelto SOBREVIVIO_AL_MALO.

Lanza el subagente `feo` con la herramienta de agentes. No adoptes su rol tú: la auditoría debe hacerse sin el contexto de la implementación.

En el encargo indícale únicamente:

- la ruta del fichero de plan
- el paso del plan que se acaba de implementar
- la lista de archivos modificados, incluidos los tests que haya dejado El Malo

No le resumas la implementación ni las decisiones tomadas: debe juzgar solo lo que hay en disco.

Si devuelve:

APROBADO_POR_EL_FEO

continúa a Finalización.

Si devuelve un Informe de Desviaciones:

- devuelve el control a El Bueno
- corrige únicamente esas desviaciones, dejando la suite de tests en verde
- vuelve a lanzar el subagente `feo` en una invocación nueva, indicándole que es una **verificación**: incluye el Informe de Desviaciones anterior y los archivos tocados por la corrección, para que compruebe las correcciones sin repetir la auditoría completa

Mientras las desviaciones corregidas sean de forma (estilo, nombres, organización, convenciones), El Malo no vuelve a entrar: sus tests adversarios quedaron incorporados a la suite y El Bueno debe mantenerla en verde tras cada ajuste.

Si alguna desviación corregida era de comportamiento funcional o de reglas de negocio, cuando El Feo apruebe lanza una verificación adicional del subagente `malo` acotada a ese cambio antes de dar el paso por terminado.

Máximo:

3 lanzamientos del subagente por paso.

Si tras el tercero sigue rechazando el código:

detente y solicita ayuda al usuario.

---

# Finalización del paso

El paso únicamente se considera terminado cuando, en este orden:

- El Malo ha respondido exactamente:

SOBREVIVIO_AL_MALO

y después

- El Feo ha respondido exactamente:

APROBADO_POR_EL_FEO

En ese momento:

1. Marca el checkbox del paso completado en el plan.
2. Pasa todos los cambios al área de staging (`git add -A`). No hagas commit.
3. Declara: PASO COMPLETADO

Si quedan pasos pendientes en el plan, vuelve a la FASE 1 con el siguiente paso.

Si no quedan pasos pendientes, declara: COMPLETADO CON ÉXITO y finaliza la ejecución.
