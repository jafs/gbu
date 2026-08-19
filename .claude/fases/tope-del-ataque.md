---
description: "El tope de lanzamientos de El Malo y qué hacer con lo que queda sin corregir"
---

Lo lee el Sheriff **la primera vez que El Malo reporta fallos en la sesión**. Un `SOBREVIVIO_AL_MALO` a la primera no lo abre.

El tope y su excepción están resumidos en `gbu.md`, que es lo que el Sheriff necesita para decidir si relanza. Aquí está cómo se clasifica cada informe, cuándo se detiene antes de tiempo y qué se hace con lo que queda sin corregir.

---

# Cuántos lanzamientos

El tope base son **3 lanzamientos** del subagente por unidad de trabajo. Pero no todos los lanzamientos significan lo mismo, así que cada vez que recibas un informe compáralo con los anteriores y clasifícalo:

- **Reproduce un fallo ya reportado** —el mismo fallo, o el mismo payload entrando por otra puerta—: la corrección no funcionó. **Si es la segunda reproducción seguida, detente y consulta al usuario**, sin gastar lo que quede del tope. Dos parches que no cierran el mismo agujero significan que se está corrigiendo el síntoma y no la clase, y el tercer lanzamiento va a decir exactamente lo mismo por 50.000 tokens más.
- **Trae solo fallos nuevos y distintos** de todos los anteriores: el ataque está siendo productivo, no atascado. Aquí, y solo aquí, **puedes conceder un cuarto lanzamiento**. Techo duro: 4. Nunca un quinto, por productivo que parezca.

El cuarto lanzamiento exige las dos condiciones a la vez: que ningún lanzamiento haya reproducido un fallo anterior **y** que el tercero solo trajera fallos nuevos. Si dudas, no lo concedas.

Y anota la señal: **tres familias distintas de fallo en la misma unidad de trabajo no hablan del código, hablan del paso.** Significan que la unidad abarca demasiada superficie o que el modelo sobre el que está construida está mal planteado. Dilo al usuario al cerrar, con las tres familias: es lo que evita que el plan siguiente vuelva a partirse igual de mal.

Si al agotar los lanzamientos siguen apareciendo fallos, no bloquees el paso: recoge lo que quede como **observaciones** para el usuario y continúa a la FASE 3. Los casos que el tipo de dominio declara imposibles son candidatos naturales a observación en vez de a corrección.

**Salvo que lo que quede sea grave.** Si al agotar los lanzamientos lo pendiente es pérdida de datos, un control de acceso evadible o una regresión en algo que ya funcionaba, no lo degrades a observación: detente y consúltalo con el usuario, como en la FASE 3. El tope existe para que un paso no se atasque puliendo casos límite, no para cerrar un agujero anotándolo en un fichero.

Al degradar un fallo, haz dos cosas para que no se pierda:

- **Anótalo en `TECHNICAL_DEBT.md`**, en el mismo directorio que el plan (créalo si no existe). Cada entrada lleva: la fecha, el paso, **la severidad**, el hallazgo de El Malo resumido con su reproducción, el test omitido que lo reproduce y qué haría falta para corregirlo. Es el registro durable de lo que El Malo vio y quedó fuera por agotar los lanzamientos: la conversación se pierde, el fichero no.

  La severidad es **alta** si alguien puede toparse con ello usando el sistema con normalidad, **media** si hace falta una combinación poco frecuente, y **baja** si solo se alcanza forzando entradas que el dominio casi nunca produce. Sin ella el fichero crece hasta que nadie lo lee: un plan largo puede dejar veinte entradas y todas parecen iguales. Escribe la severidad en la propia línea de cabecera de la entrada, para que se vea al ojear el fichero sin abrir cada una.
- **Ocúpate de su test**: El Malo lo dejó en rojo. No lo borres ni lo dejes en rojo — márcalo como omitido (skip, con la sintaxis del framework) con una referencia a su entrada en `TECHNICAL_DEBT.md`. La suite debe quedar en verde, que es de lo que parten El Feo y el paso siguiente, y el test queda listo para reactivarse si el usuario decide saldar la deuda.

