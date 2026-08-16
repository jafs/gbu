# Decisiones de diseño

Este documento explica **por qué** el patrón está montado como está. El [README](README.md) cuenta qué es y cómo se usa; aquí están las razones detrás de cada regla, que es lo que necesitas si vas a modificarlo, portarlo a otra herramienta o entender por qué algo que parece redundante no lo es.

El origen y la motivación del patrón están en dos artículos: [«cómo poner a pelear a tres agentes para que escriban tu código por ti»](https://jafs.github.io/articles/posts/20260802.html) y [«GBU con El Listo»](https://jafs.github.io/articles/posts/20260809.html).

---

## El flujo, fase a fase

```text
FASE 0 (una sola vez)
  El Listo analiza el proyecto y los acuerdos del equipo
  y escribe PLAN.md: Tarea + Contexto + Pasos con checkboxes
  (los pasos grandes van partidos en subpasos indentados, y cada
   uno trae rutas exactas, fichero modelo y verificación)
  Si el proyecto se contradice —dos formas de testear, dos maneras
  de construir lo mismo—, se detiene y te pregunta cuál es la buena

FASE 0b (una sola vez)
  El Sheriff te pregunta cómo quieres cerrar cada paso: ¿commit y
  push automáticos?, ¿con qué formato de mensaje?, ¿el plan entero
  de una tirada o parando al terminar cada paso? Lo anota en
  PLAN.md y no vuelve a preguntar.

Por cada unidad de trabajo pendiente (paso o subpaso):

  FASE 1 — El Bueno implementa el paso y deja la suite de tests en verde
     │
     │  (atajo: el Sheriff clasifica el diff —comentarios, tests,
     │   formateo automático, recursos estéticos— y de esa clase
     │   salen qué verificadores ejecuta y qué fases entran)
     │
  FASE 2 — El Malo (subagente, sin contexto de la sesión) lee el
     │     plan —el paso, su criterio de aceptación y la sección
     │     "Contexto"— y ataca los cambios: nulls, límites,
     │     datos corruptos, concurrencia... Sus tests quedan en la
     │     suite como regresión.
     │       ├─ SOBREVIVIO_AL_MALO → continúa
     │       └─ Informe de fallos → El Bueno corrige todo de una
     │          pasada y El Malo verifica (3 lanzamientos, o 4 si
     │          cada uno trae fallos nuevos y distintos; si el mismo
     │          fallo se reproduce dos veces seguidas el Sheriff se
     │          detiene). Lo que quede tras el tope se te entrega
     │          como observaciones y el paso sigue, salvo que sea
     │          grave: entonces también se detiene y pregunta.
     │
  FASE 3 — El Feo (subagente, sin contexto de la sesión) lee el
     │     plan y audita el diff contra el paso y las convenciones
     │       ├─ APROBADO_POR_EL_FEO (con observaciones o sin ellas)
     │       │  → continúa
     │       └─ Informe de Desviaciones → El Bueno corrige y El Feo
     │          verifica (máx. 3 lanzamientos). Si alguna desviación
     │          era funcional, El Malo da una última pasada acotada.
     │
  Fin del paso — checkbox marcado en PLAN.md (y el del paso padre
                 si era su último subpaso), desviaciones respecto
                 al plan anotadas en él, cambios a staging
                 y lo que diga el Modo de ejecución: commit y push,
                 solo commit, o nada. Si pediste parar entre pasos,
                 el Sheriff se detiene al cerrar el paso —no entre
                 subpasos— y espera, para que puedas hacer /clear
                 o darle indicaciones antes de seguir.

Cuando no quedan pasos: COMPLETADO CON ÉXITO
```

Si El Feo rechaza el trabajo tres veces seguidas, o un paso del plan ya no encaja con la realidad del código, el Sheriff se detiene y te pide ayuda en lugar de insistir a ciegas. El Malo no bloquea indefinidamente: si agota sus lanzamientos, lo pendiente se te entrega como observaciones, queda anotado en `TECHNICAL_DEBT.md` y el paso continúa — **salvo que lo pendiente sea grave** (pérdida de datos, un control de acceso evadible, una regresión), en cuyo caso también se detiene: el tope existe para que un paso no se atasque puliendo casos límite, no para cerrar un agujero anotándolo en un fichero.

---

## El plan y la memoria compartida

**`PLAN.md` es el único artefacto compartido.** El Listo es el único que lee la documentación del proyecto (`CLAUDE.md`, README, acuerdos de equipo): sintetiza todo lo relevante en la sección "Contexto" del plan, y el resto de agentes trabajan exclusivamente con el plan y el código en disco. Menos relecturas, menos tokens, arranques en frío baratos. Por eso Malo y Feo arrancan leyendo `PLAN.md`: de ahí sacan qué paso se acaba de implementar y su criterio de aceptación, y de la sección "Contexto" el framework de pruebas, el comando para ejecutarlo y las convenciones del proyecto. Con una consecuencia: **El Malo solo puede atacar con lo que el plan le cuenta y El Feo solo puede hacer valer lo que esté escrito ahí**, así que esa sección lleva las convenciones enunciadas como reglas comprobables leyendo, no como prosa.

**El plan tiene que estar terminado, no solo escrito.** Cada paso lleva las rutas exactas que toca, el fichero existente al que debe parecerse y dónde vive su test. Sin eso, los otros tres roles investigan por separado lo mismo —y a veces con resultados distintos—, el paso se cierra desviándose del plan y la desviación acaba solo en el mensaje del commit. Por la misma razón El Listo se detiene ante una **incongruencia** del proyecto (dos formas de testear conviviendo, dos maneras de construir el mismo objeto, una convención documentada que el código incumple) en lugar de elegir en silencio: su elección se convierte en la regla que El Feo hará valer en cada paso, así que elegir mal significa dedicar el plan entero a reproducir con rigor el error que se quería dejar atrás. Un hueco se resuelve con el supuesto más simple; una contradicción, preguntando.

**Lo que acabó distinto se escribe en el plan.** Al cerrar cada unidad, el Sheriff anota en una sección `## Desviaciones` qué decía el plan, qué se hizo y por qué. Sirve para dos cosas: el plan archivado es el historial del proyecto, y El Feo —que llega sin memoria a cada paso— deja de re-reportar en el paso cinco una decisión sancionada en el dos.

**El checkbox es la unidad de trabajo.** Cada checkbox recibe su propio ciclo completo —Bueno, Malo, Feo— y su propio commit. Por eso El Listo parte los pasos que abarcan varias unidades de comportamiento o varias capas en subpasos indentados (lógica pura → infraestructura → enlace), cada uno commiteable por sí solo y con la suite en verde; el checkbox del paso queda como *roll-up*. Un checkbox demasiado ancho produce commits difíciles de seguir, obliga a los verificadores a cubrir demasiada superficie de una sentada y mezcla las correcciones con trabajo ya aprobado. Los pasos que ya son pequeños no se parten.

**Los requisitos nuevos no entran en el paso en curso.** Si a mitad de plan pides algo imprevisto, el Sheriff cierra la unidad que tenía entre manos y vuelve a llamar a El Listo —la única vez que reaparece— para insertar el paso nuevo donde le toque por dependencias, con tu confirmación. Ampliar el paso vivo invalidaría el encargo ya dado y mezclaría trabajo sin planificar con trabajo ya atacado y auditado.

---

## El orden de los verificadores

**Malo antes que Feo.** Primero se estabiliza el comportamiento, después se pule la forma. Así los arreglos de estilo del bucle con El Feo no obligan a re-atacar: los tests adversarios de El Malo ya montan guardia en la suite, que El Bueno debe mantener en verde tras cada ajuste.

**El Feo lee, no ejecuta.** Sus herramientas son de solo lectura: el diff y los resultados de test, lint, build y tipos le llegan ya ejecutados en el encargo. Audita si el código cumple la especificación leyendo; que funciona ya lo demostraron los tests y El Malo.

**Informes agregados, verificaciones acotadas.** Malo y Feo completan su pasada entera y entregan todos los hallazgos de una vez (una corrección por iteración, no una por fallo). Cuando vuelven a entrar, solo verifican el informe anterior y lo tocado por la corrección: el Sheriff les pasa un diff que contiene **solo el arreglo** —congelando el estado previo en un índice de git aparte antes de corregir, para no tocar el staging real ni la frontera entre pasos— y re-mide el presupuesto sobre él, no sobre el paso entero.

**Salida disciplinada.** Los verificadores no narran su proceso ni enumeran lo que está bien: responden con el token exacto de aprobación o con el informe de lo que falla. La única concesión es una línea `Comprobado:` al principio de la respuesta de El Feo, con los ejes que revisó y los que dejó fuera: una aprobación sin traza no distingue «no había nada» de «no lo miré».

**El veredicto es excluyente.** Informe de Desviaciones **o** token de aprobación, nunca los dos: si El Feo emite ambos y el orquestador decide mirando la última línea, el informe entero se ignora y el paso se cierra con todo lo que encontró dentro. Por eso el prompt de El Feo lo prohíbe explícitamente y el del Sheriff comprueba primero si hay informe y solo después el token. Un veredicto ambiguo se resuelve siempre hacia el rechazo, que es el lado barato de equivocarse.

**Lo que no bloquea también tiene canal.** Todo lo que El Feo mete en el informe bloquea, y ahí entra casi todo lo que puede encontrar: solo reporta lo que incumple una regla escrita, y eso se corrige ahora, que es cuando es barato. La excepción es que **corregirlo se salga del plan** —un contrato con consumidores que el plan no cubre, un cambio con entidad de paso propio—: entonces va como observación, con su razón escrita, y acaba en `TECHNICAL_DEBT.md`. La regla que lo sostiene es que una desviación degradada a observación es una regla que nadie hace cumplir, así que la duda se resuelve hacia el informe.

**Los topes cuentan familias, no lanzamientos.** Tres rondas es el tope base de El Malo, pero no todas las rondas dicen lo mismo. Si un lanzamiento **reproduce** un fallo ya reportado, el parche no cerró nada; a la segunda reproducción seguida el Sheriff se detiene y pregunta, porque el tercer lanzamiento va a decir lo mismo por el mismo precio. Si en cambio cada ronda trae fallos **nuevos y distintos**, el ataque está siendo productivo y se concede un cuarto lanzamiento (techo duro). Y tres familias distintas en una misma unidad de trabajo son un diagnóstico sobre el plan, no sobre el código: el paso abarcaba demasiado, y eso se dice al cerrar para que el siguiente plan no se parta igual.

**Los topes se gastan en veredictos.** Si un verificador responde algo que no es ni su token de aprobación ni su informe (por ejemplo, le faltaba un dato del encargo), se completa el encargo y se relanza sin consumir el tope de tres lanzamientos: los topes miden rechazos del código, no defectos del encargo.

---

## El coste

**Presupuesto de esfuerzo.** El Sheriff mide cada paso en líneas de producción cambiadas y se lo dice a cada verificador en el encargo: un cambio de diez líneas recibe un barrido certero; uno que toca contratos o modelo de datos, barra libre. Un rol sin límites escala su esfuerzo a su propia ambición, no a la del cambio. Pero las líneas solas engañan, así que el encargo lleva también la **superficie de riesgo** del diff (red, sistema de ficheros, persistencia, concurrencia, control de acceso, entrada no confiable, solo delegación), que sube el presupuesto y nunca lo baja: cuarenta líneas que construyen una ruta de fichero esconden más ataque que cien de delegación trivial.

**Modelos por rol.** El Feo corre en un modelo más rápido (`model: sonnet` en su frontmatter) porque su trabajo es contrastar contra una checklist. El Malo hereda el modelo de la sesión: diseñar buenos ataques es la parte difícil, y por eso el Sheriff te avisa antes de lanzarlo si la sesión corre con un modelo pequeño — un `SOBREVIVIO_AL_MALO` de un modelo flojo vale menos. Ajusta ambos a tu gusto.

**Atajos para pasos triviales.** Antes de verificar nada, el Sheriff clasifica el diff del paso, y esa clase decide dos cosas: **qué verificadores se ejecutan** y **qué fases entran**. Un paso de solo documentación no ejecuta ninguno —no toca nada que `test`, `lint` o `build` puedan medir, y ejecutarlos cuesta minutos para producir números que nadie va a usar—; uno de solo formateo automático ejecuta `lint`; uno de solo tests, la suite. En cuanto a fases: El Malo no ataca comentarios y El Feo no audita la salida de un formateador, pero los tests nuevos sí pasan siempre por El Feo (un assert aflojado es una desviación). La clase es la del cambio **más exigente** del diff: si toca `PLAN.md` junto a código, manda el código. Lo que el atajo ahorra es *reejecutar*, nunca el estado verde: la suite debe estarlo igual, y ante la duda se ejecuta el flujo completo.

Y hay además una regla de **cuándo**: mientras se itera se usa el subconjunto afectado, y la suite completa se lanza una sola vez, justo antes del lanzamiento que va a usar sus números. En un proyecto mediano ese detalle es el que domina el reloj del paso.

---

## Qué se corrige y qué se anota

**Fallo u observación.** El Malo solo bloquea lo alcanzable con datos que el sistema produce de verdad; lo que exige forzar mocks, cambiar contratos fuera del paso o cuesta más que el riesgo real se entrega como observación al cerrar el paso. Tú decides si se corrige.

**Instancia o clase.** De cada fallo, El Malo dice si es un caso aislado o el síntoma de un modelo equivocado —una lista negra que enumera ortografías, una validación en una capa que se puede rodear—, y cuál es la familia. El Bueno corrige entonces al nivel correcto y no la ortografía reportada, porque un parche que solo tapa el payload garantiza otra ronda por la puerta de al lado.

**El límite de «al nivel correcto» es el plan, no el paso.** Ajustar código de un paso anterior del mismo plan es normal —los planes se parten por capas justamente para que el paso de enlace toque lo que dejaron los anteriores— y solo hay que declararlo, para que El Feo no lea ese código como alcance inventado. Se para y se pregunta únicamente cuando la corrección se sale del plan: rompe un contrato con consumidores que el plan no cubre, invalida un paso posterior, o es un cambio de diseño con entidad para ser un paso propio. Entonces se resuelve insertando un paso, no ampliando el abierto.

**La deuda técnica queda escrita.** Lo que El Malo encontró y no se corrigió —fallos degradados al agotar sus lanzamientos, observaciones que piden una decisión— no puede vivir solo en la conversación, que se pierde. El Sheriff lo anota en `TECHNICAL_DEBT.md`, junto al plan: cada entrada con su **severidad**, su reproducción, su test omitido (skip) que la reproduce y qué haría falta para saldarla. Reactivar el test es retomar la deuda; la severidad es lo que evita que un fichero de veinte entradas deje de leerse.

**La UI se ejerce antes de cerrar.** Si «funciona» lo demuestran los tests, una interfaz con comportamiento de cliente rompe la premisa: la suite puede estar verde con la pantalla rota. Un paso de UI interactiva no cierra sin un test de interacción, un arranque real de la aplicación o, en su defecto, una deuda anotada. Con una precisión que sale de usarlo: si la aplicación tiene sesión, el arranque real solo existe cuando el Contexto del plan dice **cómo llegar a un estado autenticado de desarrollo**. Si no lo dice, la opción desaparece —el Sheriff no improvisa accesos ni te pide credenciales— y el test de interacción pasa de preferible a obligatorio.

---

## Git y la frontera entre pasos

**El staging de git marca la frontera entre pasos.** Lo aprobado se stagea; lo que está sin stagear es el paso en curso. Los verificadores solo miran lo sin stagear, así que nunca re-auditan trabajo ya validado. En mitad de un paso nunca se commitea.

**El Malo escribe tests, no producción.** El Sheriff guarda una instantánea del diff de producción antes de lanzarlo y la compara al terminar: cualquier cambio de producción aparecido durante el ataque se revisa antes de seguir, porque El Feo audita justo después y no distingue la mano de El Malo de la de El Bueno.

**La historia del repositorio es tuya, pero puedes delegarla.** Por defecto el patrón no hace commits. Si al arrancar le dices que sí, cada paso aprobado se cierra con un commit —y un push si lo pides— usando el formato de mensaje que elijas. La respuesta vive en `## Modo de ejecución` dentro de `PLAN.md`, así que sobrevive entre sesiones y solo se pregunta una vez.

**Tú decides el ritmo.** Al arrancar el plan el Sheriff también te pregunta si quieres el plan entero de una tirada o que se detenga al terminar cada paso. Parar te devuelve el control en el momento natural para hacer `/clear` —la sesión se alarga tras varios ciclos de Malo y Feo— o para dar indicaciones. Ojo a la granularidad, que no es la misma que la del commit: **el commit va por unidad de trabajo y la parada por paso**, así que un paso con tres subpasos produce tres commits (y tres push, si los pediste) y una sola parada, al caer el tercero. Como el resto del Modo de ejecución, admite respuesta libre: agrupar los commits por paso, parar cada N pasos, parar solo en los que toquen cierta zona, o parar también entre subpasos.

---

## Lo que dejaron los ejemplos

Conclusiones de las tres ejecuciones de [`examples/`](examples/), más allá del código:

- **El plan es una red de seguridad.** Para provocar el bucle de corrección en `csv-line` hubo que degradar a El Bueno a un modelo pequeño *y aun así* sobrevivió a dos de los tres pasos: con un plan detallado de El Listo delante (contrato exacto, supuestos documentados, casos límite enumerados), hasta un implementador modesto acierta. El fallo apareció justo donde el diseño invitaba a duplicar estado — un problema de modelo, no de descuido.
- **El Malo aporta aunque no rompa.** En las ejecuciones sin fallos su huella quedó igualmente: casos adversarios montando guardia en la suite (`"XIV\n"`, entrada NFD, coerciones de tipo), observaciones que guiaron el diseño del paso siguiente (el orden de la normalización Unicode en `slugify` salió de su ataque al paso anterior) y deuda anotada para decidir después.
- **Sus diagnósticos de causa raíz valen tanto como sus fallos.** En `csv-line` advirtió dos veces que «el problema es del modelo, no del parche», y acertó las dos: el primer arreglo cambió un fallo por su espejo y solo la corrección estructural cerró el ciclo. Cuando El Malo señala la causa raíz, corregir el síntoma sale caro.
- **Malo antes que Feo funciona.** El Feo aprobó a la primera en todos los pasos: llegó siempre con el comportamiento ya estabilizado y los tests adversarios en verde, y pudo limitarse a contrastar contra la especificación. En proyectos con convenciones propias (arquitectura, acuerdos de equipo) su listón tiene más donde morder que en ejemplos autocontenidos como estos.
- **La asimetría de modelos es una palanca.** Bueno pequeño + Malo grande maximiza la caza (y abarata la implementación); Bueno grande + Malo grande maximiza que el paso sobreviva a la primera. Elegir modelo por rol es parte del ajuste del patrón, no un detalle de infraestructura.
