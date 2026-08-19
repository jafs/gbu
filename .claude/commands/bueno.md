---
description: "🤠 El Bueno: Implementa el siguiente paso del plan (se ejecuta como subagente aislado)"
argument-hint: "opcional: fichero de plan y paso a implementar"
---

Este fichero define **el encargo de El Bueno**: qué datos hay que darle al lanzarlo. Es la única definición del encargo — `/gbu` la referencia en su FASE 1 en vez de repetirla.

El subagente en sí está definido en `.claude/agents/bueno.md`.

---

# El encargo

Lanza el subagente `bueno` con la herramienta de agentes.

No adoptes su rol tú: la implementación debe hacerse en un contexto aislado, sin el historial de esta conversación. Ese aislamiento es el punto — es lo que evita que el código, los diffs y la salida de los tests se queden para siempre en el hilo del orquestador.

En el encargo indícale únicamente estos campos:

- la ruta del fichero de plan (por defecto `PLAN.md`)
- **el paso que debe implementar**, citado tal y como aparece en el plan. Si el paso tiene subpasos, el que va es el subpaso: la unidad de trabajo es el checkbox más profundo sin marcar

Y nada más. No le resumas el plan, no le adelantes cómo resolverlo, no le pegues el código de los pasos anteriores: el plan es su documentación y el código está en disco. Todo lo que le cuentes de más lo pagas dos veces —al enviarlo y en cada turno suyo— y compite con lo que sí tiene que leer.

Si es una **corrección** (relanzamiento tras un informe de fallos de El Malo o un Informe de Desviaciones de El Feo), **no lances un subagente nuevo: reanuda al mismo** (ver «El bucle de corrección» en `gbu.md`), y pásale:

- el informe íntegro que motiva la corrección: el de El Malo o el de El Feo, sin recortar
- de quién viene y **qué ronda es** dentro de este paso
- si El Feo separó desviaciones bloqueantes de observaciones, cuáles debe corregir

Si es una corrección tras un `BLOQUEADO` suyo, pásale la respuesta del usuario a su pregunta, literal, y nada más: él ya sabe dónde se quedó.

---

# Qué devuelve

Un **informe de entrega** en español, con las secciones que `bueno.md` (el del agente) le exige: entrega, verificadores con sus números, supuestos, desviaciones respecto al plan y observaciones. Empieza por un veredicto:

- `ENTREGADO`: el código está listo para ser atacado y auditado.
- `BLOQUEADO`: se ha topado con algo que no puede decidir solo. Trae la pregunta concreta; no ha implementado el paso.

**Ese informe es lo único que vas a saber de la implementación.** De ahí salen el tamaño, la clase del cambio, la superficie de riesgo y los números de los verificadores que necesitan los encargos de El Malo y de El Feo. No rehagas su trabajo para comprobarlo: leer el diff entero en tu hilo deshace la razón de haberlo aislado.

Si el informe llega incompleto —falta un número, falta la clase, falta la superficie de riesgo—, **pídeselo reanudándolo**: contestar eso le cuesta un turno corto, y reconstruirlo tú te cuesta el diff entero en contexto.

---

# Uso manual

Si has llegado aquí por `/gbu`, ignora esta sección: la orquestación (cuándo entra, qué se hace con su informe, cómo se corrige) la lleva `gbu.md`.

Invocado a mano, sobre un plan suelto:

1. Si se han proporcionado argumentos ($ARGUMENTS), interprétalos como la ruta del plan y el paso a implementar.
2. Si no se indica paso, el que va es el primer checkbox sin marcar que no tenga subpasos indentados debajo.
3. Lanza el subagente y, cuando termine, muestra al usuario su informe íntegro.

Aquí no hay ataque ni auditoría: una invocación, un paso implementado. El checkbox **no** se marca y los cambios se quedan sin stagear; cerrar el paso es decisión del usuario.
