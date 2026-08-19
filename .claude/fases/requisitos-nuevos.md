---
description: "Qué hace el Sheriff cuando el usuario pide algo que el plan no contempla"
---

Lo lee el Sheriff **solo si** el usuario pide, con el ciclo en marcha, algo que el plan no contempla. Si eso no pasa —y lo normal es que no pase—, este fichero no se abre nunca.

---

# Requisitos nuevos a mitad de ejecución

El usuario puede pedirte algo que el plan no contempla mientras el ciclo está en marcha. **Nunca lo metas en la unidad de trabajo en curso**: ampliarla invalida el encargo que ya diste, deja el diff sin corresponder a su checkbox y mezcla trabajo sin planificar con trabajo ya atacado y auditado.

En su lugar:

1. **Termina la unidad en curso** por su cauce normal, hasta el cierre. Si lo pedido bloquea de verdad lo que estás haciendo, dilo y para; no improvises.
2. **Adopta El Listo en modo revisión** —es la única vez que vuelve a entrar— con el encargo acotado a insertar el requisito nuevo: un paso más, partido en subpasos si lo pide su tamaño, colocado en el sitio que le corresponda por dependencias. Lo ya marcado no se toca, y el paso nuevo va siempre **después** del último checkbox marcado.
3. **Enséñale al usuario el plan resultante y espera su confirmación** antes de seguir, igual que en la revisión de la FASE 0: la posición de un paso decide qué hay construido cuando se implementa.
4. Continúa por la siguiente unidad de trabajo pendiente, que puede ser ya la nueva.

Si lo que pide no es un requisito sino un cambio de criterio sobre cómo cerrar los pasos (commit, push, paradas), eso no pasa por El Listo: se edita la sección `## Modo de ejecución`, que se relee en cada cierre.
