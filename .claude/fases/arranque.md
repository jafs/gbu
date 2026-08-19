---
description: "Detalle de las fases de arranque del patrón GBU: el plan y el modo de ejecución"
---

Lo lee el Sheriff **solo si** no hay plan válido o al plan le falta `## Modo de ejecución`.

Si el plan existe, cumple el contrato y ya trae su modo de ejecución, este fichero no se abre: las dos fases se omiten y el ciclo arranca directamente en la FASE 1.

---

# FASE 0: El plan

Si no existe el plan:

- Si se ha proporcionado una tarea como argumento ($ARGUMENTS), adopta el comportamiento del comando `/listo` (fichero `listo.md`, en el mismo directorio de comandos que este) y genera el plan.
- Si no se ha proporcionado ninguna tarea, detente y solicítala al usuario.

Si el plan existe pero **no cumple el contrato** que el resto del patrón da por supuesto, adopta también el comportamiento de `/listo`, en modo revisión, para normalizarlo. Compruébalo antes de empezar; basta con mirar si tiene:

- una sección `## Tarea`
- una sección `## Contexto`
- una sección `## Pasos` con checkboxes `- [ ]` / `- [x]`

Que los pasos estén o no partidos en subpasos **no** forma parte de este contrato: un plan con pasos grandes es válido y se ejecuta tal cual. Tampoco lo forma que cada paso traiga sus rutas exactas, su fichero modelo y su verificación, aunque El Listo los escriba. Si ves que los pasos pendientes son mucho más anchos de lo que conviene, o que no dicen dónde va cada fichero —y eso te va a obligar a investigarlo en cada paso y a los verificadores a redescubrirlo—, dilo al usuario y ofrécele una pasada de El Listo en modo revisión, pero no la lances por tu cuenta ni bloquees el flujo por ello.

Si falta cualquiera de las tres, el plan no sirve tal cual: sin `## Pasos` no sabes cuál es el siguiente paso ni puedes marcarlo al cerrar, y **sin `## Contexto` El Malo y El Feo se quedan sin convenciones ni comandos de test**, porque el plan es toda su documentación.

`## Modo de ejecución` no entra en este contrato: si falta, no llames a El Listo — se resuelve en la FASE 0b preguntando al usuario.

En modo revisión El Listo reestructura lo que hay, sin inventar contenido nuevo. Cuando termine, enseña al usuario su resumen —qué ha reorganizado, cuántos pasos hay y, si ha marcado alguno como ya hecho, con qué evidencia— y **espera su confirmación** antes de seguir: marcar mal un paso como hecho se salta trabajo real.

El Listo únicamente interviene aquí.

Una vez existe un plan válido, desaparece de escena y no vuelve a entrar — con una única excepción, la de «Requisitos nuevos a mitad de ejecución», que está en `gbu.md`.

Si el plan ya existe y cumple el contrato, omite esta fase por completo.

---

# FASE 0b: El modo de ejecución

Antes de implementar nada, el plan debe llevar una sección `## Modo de ejecución` que diga qué hacer al cerrar cada paso.

**Si ya la tiene, respétala y no preguntes nada.** La decisión se tomó al arrancar el plan y sigue vigente hasta que el usuario diga otra cosa: así el patrón se puede retomar en otra sesión sin volver a interrogarle.

**Si falta, pregúntaselo al usuario y escríbela tú en el plan antes de seguir.** Es la única vez que el flujo se para para preguntar algo que no es un problema. Pregunta en este orden:

1. **«Al terminar cada unidad de trabajo, ¿hago commit y push automáticamente?»**

   - **Si responde que sí**, pregunta a continuación: **«¿Qué formato de commit prefieres?»** Antes de preguntar mira el historial (`git log --oneline -20`) y ofrécele el estilo que ya use el repo como una de las opciones, junto a Conventional Commits. Anota el formato literal que elija, con un ejemplo.
   - **Si responde que no**, los cambios de cada unidad aprobada se quedan en staging, sin commit.

   Si el plan tiene pasos con subpasos, dile qué implica: **el commit es por unidad de trabajo**, así que cada subpaso cierra con el suyo y un paso de tres subpasos produce tres commits, no uno. Es la consecuencia directa de que el checkbox más profundo sea la unidad: cada subpaso pasa su ciclo completo y deja la suite en verde, luego es commiteable por sí solo. Si prefiere un commit por paso, es texto libre válido: anótalo y agrupa (ver más abajo).

2. **«¿Lanzo el plan entero de una tirada, o me detengo al terminar cada paso para avisarte?»**

   Explícale qué gana con cada opción: **de una tirada** el plan se ejecuta hasta el final sin intervención; **parando** recupera el control al cerrar cada paso, que es el momento natural para hacer un `/clear` —la sesión llega larga tras varios ciclos de El Malo y El Feo— o para darte indicaciones antes de seguir.

   Dile también que la parada es **a nivel de paso, no de subpaso**: los subpasos de un mismo paso se encadenan siempre sin parar, y la parada llega cuando cae el último de ellos. Así el plan se corta por juntas naturales y no en mitad de un paso a medio hacer.

   Las dos preguntas tienen por tanto granularidad distinta, y conviene decirlo: **el commit va por unidad de trabajo, la parada por paso**. En un paso con tres subpasos y ambas opciones activas: tres commits (y tres push, si los pidió) y una sola parada, al caer el tercero.

El usuario puede contestar en texto libre y describir un flujo distinto del que le ofreces —commit sí pero push no, push solo al terminar el plan, commit únicamente en los pasos que toquen cierta zona, parar solo en los pasos que toquen cierta zona, parar también entre subpasos, parar cada N pasos—. Manda lo que diga, no las opciones que le presentaste: recoge su respuesta tal cual en las notas.

Si la rama actual es la principal del repo (`main` o `master`) y ha pedido push automático, dilo al preguntar: quizá prefiera una rama aparte. No cambies de rama por tu cuenta.

Escribe entonces en el plan, justo antes de `## Pasos`:

```markdown
## Modo de ejecución

- **Al cerrar cada unidad de trabajo** (cada checkbox, subpaso incluido): commit y push | commit sin push | nada, dejar en staging
- **Formato de commit**: el formato literal acordado, con un ejemplo | no aplica
- **Entre pasos** (al caer el último subpaso del paso, no entre subpasos): parar y avisar al usuario | encadenar el siguiente
- **Notas del usuario**: su respuesta en texto libre, tal cual, si la hubo
```

Enséñale la sección escrita y sigue. No hace falta que la confirme: son sus propias respuestas.

Si pidió **un commit por paso** en vez de por unidad de trabajo, anótalo en `Al cerrar cada unidad de trabajo` con esas palabras. Entonces cada subpaso aprobado se queda en staging —marca de checkbox incluida— y el commit se hace al cerrar el último subpaso del paso, con un mensaje que describe el paso entero. No mezcles: staging entre subpasos, commit al cerrar el paso.
