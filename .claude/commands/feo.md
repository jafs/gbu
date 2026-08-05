---
description: "👺 El Feo: Auditor estricto del código (se ejecuta como subagente aislado)"
argument-hint: "opcional: fichero de plan, paso implementado y archivos modificados"
---

Lanza el subagente `feo` (definido en `.claude/agents/feo.md`) con la herramienta de agentes.

No adoptes su rol tú: la auditoría debe hacerse en un contexto aislado, sin el historial de esta conversación.

En el encargo indícale únicamente:

- la ruta del fichero de plan (por defecto `PLAN.md`)
- el paso del plan que se acaba de implementar
- la lista de archivos modificados, si la conoces

Si se han proporcionado argumentos ($ARGUMENTS), inclúyelos en el encargo.

No le resumas la implementación ni las decisiones tomadas: debe juzgar solo lo que hay en disco.

Cuando termine, muestra al usuario su respuesta íntegra: `APROBADO_POR_EL_FEO` o el Informe de Desviaciones.
