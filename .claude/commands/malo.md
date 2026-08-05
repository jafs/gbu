---
description: "🌵 El Malo: QA adversario (se ejecuta como subagente aislado)"
argument-hint: "opcional: fichero de plan, paso implementado y archivos modificados"
---

Lanza el subagente `malo` (definido en `.claude/agents/malo.md`) con la herramienta de agentes.

No adoptes su rol tú: el ataque debe hacerse en un contexto aislado, sin el historial de esta conversación.

En el encargo indícale únicamente:

- la ruta del fichero de plan (por defecto `PLAN.md`)
- el paso del plan que se acaba de implementar
- la lista de archivos modificados, si la conoces

Si se han proporcionado argumentos ($ARGUMENTS), inclúyelos en el encargo.

No le resumas la implementación ni las decisiones tomadas: debe atacar solo lo que hay en disco.

Cuando termine, muestra al usuario su respuesta íntegra: `SOBREVIVIO_AL_MALO` o el informe de reproducción.
