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

## El Bueno arrastra el catálogo de herramientas entero

**Medido**: 2026-08-21, siete lanzamientos sobre `kdserver` con gbu v0.3.0.

El Bueno arranca en **38.745-39.233 tokens** antes de leer nada, y la cifra es constante
dentro de ±500 en los siete lanzamientos: casi nada de eso es el encargo, es coste fijo
por existir. El Feo, mismo mecanismo y mismo encargo, arranca en **~20.000**.

La diferencia son las herramientas. El Feo las tiene acotadas en su frontmatter (`Read`,
`Grep`, `Glob`); El Bueno y El Malo las llevan todas, incluido el servidor MCP del
navegador — 45 menciones a `mcp__claude-in-chrome` en el arranque de cada uno, cero en el
de El Feo.

**Por qué importa**: no son 18.000 tokens, son 18.000 **por turno**. Los Buenos de esa
noche duraron entre 30 y 150 turnos. En el de 150, el catálogo que no usó vale ~2,7 M de
turn-tokens: más que todo lo que ahorró adelgazar el prompt del Sheriff.

**Vías**: acotar las herramientas de El Bueno por frontmatter como ya hace El Feo; o
—mejor, porque a veces sí necesita el navegador— dárselas **según la clase del paso**, que
el Sheriff ya calcula para decidir qué verificadores entran (`DESIGN.md`, «Atajos para
pasos triviales»). Un paso sin interfaz no necesita Chrome cargado.

**Qué lo bloquea**: nada técnico. Encaja en el paso 2 del plan de adelgazamiento, que ya
es «la higiene de El Bueno», y conviene medirlo con su propia ventana porque compite con
las reglas de acotado de salida que ese mismo paso introduce.

Hay una tercera vía, mejor que las dos anteriores porque no sacrifica ninguna capacidad:
mover la verificación de interfaz a un rol propio, y con ella el navegador. Ver «Un rol
para la interfaz: El Elegante».

## El Bueno es la mitad del reloj, y no lo estábamos midiendo

**Medido**: 2026-08-21, reloj de pared de dos sesiones sobre `kdserver`.

| | Bloque seguido (4 subpasos) | Bloque con `clear` (2) |
| --- | ---: | ---: |
| Total | 136 min | 43 min |
| El Bueno | 60,1 min (44,1 %) | 23,6 min (54,5 %) |
| El Malo | 21,0 min (15,4 %) | 7,6 min (17,6 %) |
| El Feo | 3,7 min (2,7 %) | 2,6 min (6,0 %) |
| Resto (Sheriff y esperas) | 51,4 min (37,7 %) | 9,5 min (21,9 %) |

El patrón se percibe lento y el reparto dice dónde: **El Bueno**, con subagentes de 30 a
150 turnos. El Feo, al que ya se le dio un modelo rápido, es el 3 % — ahí no queda nada
que ganar, y bajarle más el modelo solo compraría peores auditorías.

**Cuidado al leer el «resto»**: incluye la espera humana. El plan de `kdserver` manda
parar y avisar al usuario entre pasos, así que buena parte de esos 51 min del bloque
seguido es el Sheriff esperándote, no trabajando. La cifra útil no es el porcentaje sino
que **cada turno de El Bueno se paga en reloj y en tokens a la vez**: reducir sus turnos
es la única palanca que mueve las dos.

**Vía**: el coste por turno ya lo ataca la entrada anterior. Lo que falta es reducir el
**número** de turnos, y eso enlaza con «El Listo produce pasos demasiado grandes»: un
checkbox más ancho no cuesta el doble, cuesta bastante más.

**Qué lo bloquea**: ya nada por el lado de la medida — desde el 2026-08-22
`session_report.py` informa el reloj de pared por rol en la sección «Flujo» (con el
«resto» del sheriff señalado como espera humana, no trabajo), y el comparador lo cruza
entre versiones. Lo que queda es la palanca en sí: reducir los turnos de El Bueno, que
enlaza con «El Listo produce pasos demasiado grandes» y espera a que cierre el plan de
adelgazamiento.

## El `clear` entre subpasos vale un 20 % y podría ser automático

**Medido**: 2026-08-21, comparando 4 subpasos seguidos contra 2 con `clear` en medio.

| Por paso | Seguido | Con `clear` | |
| --- | ---: | ---: | --- |
| Coste del Sheriff | 562.603 | 385.702 | −31 % |
| Coste total | 1.751.022 | 1.395.615 | **−20 %** |
| Reloj | ~34 min | ~21,7 min | **−36 %** |

Lo que el `clear` reinicia es **solo al Sheriff**: los picos de El Bueno en el bloque con
`clear` (154.081 y 139.923) fueron **más altos** que la media del bloque seguido (117.755).
No podía ser de otra manera — los subagentes ya arrancan limpios cada vez.

La idea: que el Sheriff **se reinicie solo entre unidades de trabajo**, en vez de depender
de que el usuario se acuerde de escribir `/clear`. Es arquitectónicamente sano, porque el
patrón ya guarda su estado en disco: el plan, los checkboxes y `## Desviaciones` son
precisamente la memoria compartida que sobrevive a un contexto que se va (`DESIGN.md`, «El
plan y la memoria compartida»).

**Qué lo bloquea**: hay que comprobar qué pierde el Sheriff al reiniciarse que no esté ya
en disco —las correcciones acordadas por `SendMessage` dentro de un paso, sobre todo— y si
la herramienta permite provocarlo desde el propio flujo. El −20 % está medido con n=2
subpasos y contra trabajo de otra naturaleza: orienta, no cierra.

## Descartado: paralelizar El Malo y El Feo

**Evaluado y rechazado**: 2026-08-21, con el reloj medido.

La idea era lanzar los dos verificadores a la vez sobre el mismo diff congelado, ya que El
Feo solo lee. **Los números no la sostienen**: El Feo es el 2,7 % del reloj (3,7 min de
136). Paralelizarlo ahorraría minutos sueltos a cambio de romper la razón por la que
`DESIGN.md` fija «Malo antes que Feo» — que los tests adversarios de El Malo montan
guardia mientras El Bueno aplica los arreglos de forma de El Feo.

Se anota para que no se vuelva a proponer.

## Un rol para la interfaz: El Elegante

**Propuesto**: 2026-08-22, a partir de los números de la ventana v0.3.0.

Hoy quien ejerce la interfaz es El Bueno: `bueno.md`, «La UI interactiva exige más», le
exige un test de interacción, un arranque real o una deuda anotada antes de entregar. La
doctrina es correcta —`DESIGN.md`, «La UI se ejerce antes de cerrar»— pero está en el peor
sitio posible, y se paga por dos vías distintas:

- **El catálogo del navegador viaja en todos los pasos**, también en los de backend puro,
  a 18.000 tokens por turno (ver «El Bueno arrastra el catálogo de herramientas entero»).
- **Una captura de pantalla no se lee una vez: se rearrastra en cada turno posterior.** Los
  2,2 M de turn-tokens en capturas y scrolls de la v0.2.0 son eso, amortizados sobre los
  30-150 turnos que dura un Bueno.

**La propuesta** tiene dos mitades. Primero, una rama de entrevista en la FASE 0b, que hoy
solo pregunta por el modo de ejecución:

1. ¿El proyecto tiene interfaz? Si no, la rama entera desaparece.
2. ¿Hay `DESIGN.md`? Si no lo hay, ofrecer generarlo —a partir del código si ya existe, o
   al vuelo si aún no—. El nombre es `DESIGN.md` y no otro **precisamente porque es la
   convención**: si el proyecto ya lo tiene, alguien escribió allí las pautas y hay que
   leerlas; inventar un fichero paralelo sería saltárselas.
3. ¿Hace falta un design system sencillo? Un HTML estático con la paleta y los elementos
   habituales —botones, diálogos, secciones— sobre variables CSS, para que el usuario
   ajuste colores y espaciados en un sitio y lo vea.
4. ¿Se va a verificar la interfaz con algún MCP? Chrome, otro, o ninguno.

Segundo, **El Elegante**: un quinto rol que entra tras El Feo y audita lo que El Feo no
puede —que los componentes y estilos usados son los del design system, que la pantalla es
coherente y usable—, ejercitando la interfaz con el MCP si lo hay.

**Por qué merece la pena**: resuelve el dilema del catálogo de herramientas sin sacrificar
nada. En vez de quitarle el navegador a El Bueno y perder la verificación de UI, se
reubica en un agente que vive quince turnos y muere. Las capturas se amortizan sobre esos
quince en vez de sobre ciento cincuenta.

**Las cuatro cosas que hay que atar antes de escribir una línea:**

1. **«No vuelven a entrar El Malo y El Feo» no puede ser absoluto.** Si El Elegante
   encuentra que un botón no abre su diálogo, eso es comportamiento, y cerrarlo sin El Malo
   rompe la garantía del patrón. La regla que sí funciona: *sus hallazgos son de forma
   visual por definición; si topa con un fallo de comportamiento no lo arregla — es un
   fallo que se le escapó a El Malo y entra por el bucle de corrección normal*.
2. **Rompe «El Feo lee, no ejecuta», y hay que escribirlo.** El Elegante es el primer
   verificador que ejecuta. Es legítimo —su objeto de auditoría no es texto—, pero si no se
   dice en `DESIGN.md` queda como una contradicción que alguien «arreglará» mal más tarde.
3. **El Bueno no puede soltar el test de interacción.** La tentación es «ya lo mirará El
   Elegante», y sería un retroceso: el test queda en la suite montando guardia para
   siempre, la pasada de navegador no deja nada detrás. El reparto limpio es que El Bueno
   conserve el test y pierda el navegador; El Elegante aporta el ojo, no la red.
4. **El design system tiene que mantenerse honesto.** Es la fuente de verdad de los tokens
   y la aplicación consume esas variables; un color definido fuera de ahí es un hallazgo de
   El Elegante. Sin esa regla, en tres pasos el HTML es decoración y él audita contra una
   mentira.

Dos detalles menores. Las respuestas de la entrevista tienen que vivir **en el plan**, en
una sección `## Interfaz` propia y no dentro de `## Contexto`, que releen los cuatro roles
en cada invocación. Y El Malo también debería soltar el navegador: él escribe tests, no
explora, así que un ataque suyo a la interfaz es un test de interacción.

**Lo que esto no arregla**: los pasos de frontend no se acelerarán. El Bueno ahorra minutos
de navegador y El Elegante se los gasta; puede incluso subir algo su reloj. Lo que gana es
tokens en todas partes y reloj en los pasos y proyectos **sin** interfaz, que hoy pagan un
MCP que no usan. El problema de velocidad sigue siendo el tamaño del paso.

**Qué lo bloquea**: el tamaño. Es más trabajo que los pasos 2 y 3 del plan de
adelgazamiento juntos, y montarlo sobre cambios aún sin medir contamina las dos medidas.
Va después. Tiene además una novedad estructural que conviene resolver como se resolvió
`fases/` en la v0.3.0: es **el primer rol condicional al tipo de proyecto**, así que sus
instrucciones deben vivir en un fichero que no se abre nunca cuando no hay interfaz, en
vez de ser una fase que se omite en ejecución.

Sobre los nombres: **El Elegante** para el auditor de estilos. Se barajó **El Modista**
como adversario de interfaz —la versión UI de El Malo— y **se descarta**: El Malo ataca la
lógica, y la lógica de una interfaz se ataca con tests de interacción, que él ya sabe
escribir y que además se quedan en la suite. Lo que solo aparece levantando la pantalla
—foco, estados deshabilitados, un layout que se rompe estrecho— es forma visual, y de eso
responde El Elegante. Un sexto rol no cubriría ningún hueco real.
