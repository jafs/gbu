# Mejoras futuras

Registro de lo observado sobre el patrón que **no** se arregla en el momento. Es el
equivalente, para este repositorio, del `TECHNICAL_DEBT.md` que gbu deja en los proyectos
donde se ejecuta: lo que no entra ahora se anota en vez de secuestrar el trabajo en curso
(`DESIGN.md`, «Qué se corrige y qué se anota»).

No es una lista de deseos. Una entrada entra aquí cuando se ha **observado**, no cuando se
ha imaginado, y lleva escrito qué la bloquea. Cuando se salda, se borra.

---

## El Listo produce pasos demasiado grandes

**Observado**: 2026-08-21, ejecutando gbu v0.3.0 sobre `kdserver`.

`listo.md` ya lo prohíbe explícitamente —«Ante la duda, parte», más la heurística de
partir por bloques y dentro de cada bloque por capas— y aun así los checkboxes salen
anchos. La hipótesis es que las cuatro excepciones que siguen a esa regla («funde las
capas triviales», «no partas lo que no se sostiene solo», «no partas un paso que ya es
pequeño») son salidas razonables y justificables una por una, y el modelo las toma.

Dos vías, no excluyentes: **poder configurar el particionado**, o sustituir el juicio por
un criterio duro y comprobable (número de ficheros o de comportamientos por checkbox).

**Por qué importa**: el tamaño del paso es la palanca que más manda en el coste del ciclo.
Cada checkbox paga una verificación completa, y las rondas de corrección las dispara la
superficie del cambio, no su dificultad.

**Qué lo bloquea**: cambiar `listo.md` cambia el tamaño de los pasos, y «coste por paso»
es la métrica con la que se están juzgando las versiones del plan de adelgazamiento.
Tocarlo con una ventana de medición abierta invalida la ventana. Es una versión propia,
con su propia medición, después de cerrar ese plan.

## Una sesión que cruza un release se atribuye a una sola versión

**Observado**: 2026-08-19, al medir la v0.2.0.

La sesión `93da9ca9` lleva las dos marcas, `gbu v0.1.0` y `gbu v0.2.0`: empezó el 18 de
agosto y siguió hasta el 19 con el plugin actualizado a mitad. `session_report.py` la
atribuyó entera a la 0.1.0, con lo que el informe `0.1.0.json` archivado contiene ~7 pasos
ya ejecutados con el patrón nuevo —y son los más baratos del lote—. Cualquier comparación
contra ese archivado **infravalora** la mejora.

Arreglarlo bien exige **partir la sesión por la marca** y repartir sus turnos entre las
dos versiones.

**Mitigación mientras tanto**: no actualizar el plugin con una sesión abierta, y medir
siempre con `--desde` puesto a la fecha del tag.

## Las rondas de El Malo por paso no salen en el informe

**Observado**: 2026-08-19, redactando el plan de adelgazamiento.

Es **la señal roja del patrón**: si un cambio ahorra tokens pero sube las rondas de
ataque, ha salido caro, porque una ronda extra de El Malo cuesta más que casi cualquier
ahorro de contexto. Hoy hay que contarlas a mano leyendo la traza (1,67 por paso en la
v0.2.0), y es justo el número que decide si un paso del plan se revierte.

**Por qué importa**: sin esa cifra en el informe, la herramienta mide el coste pero no la
calidad, y la decisión de revertir vuelve a tomarse a ojo — que es lo que la herramienta
vino a evitar.
