---
description: "Cómo corrige el Sheriff: reanudar a El Bueno y acotar el diff de la corrección"
---

Lo lee el Sheriff **la primera vez que hay que corregir en la sesión**, venga el informe de El Malo (FASE 2) o de El Feo (FASE 3). Una vez leído, no se vuelve a abrir: releerlo en cada corrección costaría más que haberlo tenido delante desde el principio.

Un paso que atraviesa el ciclo sin una sola corrección no abre este fichero.

---

# El bucle de corrección

Cuando El Malo reporte fallos o El Feo devuelva un Informe de Desviaciones, **corrige reanudando al mismo Bueno** —el que lanzaste en la FASE 1, cuya referencia guardaste— con la herramienta de mensajes a subagentes. **Nunca lances un Bueno nuevo dentro del mismo paso.** Pásale los campos que `bueno.md` define para una corrección: el informe íntegro, de quién viene y qué ronda es.

El porqué, para que nadie lo «optimice» más tarde: **reanudar conserva su contexto**. Acaba de escribir ese código y lo recuerda, así que corrige sin releerlo y sin reconstruir el paso — que es justo lo que le cuesta caro a un agente sin memoria. A cambio, reanudar reenvía todo su historial, así que su coste crece con cada ronda igual que el de una conversación larga. Dentro del paso sale a cuenta y el tope de lanzamientos de El Malo lo mantiene acotado; **fuera del paso no**: la referencia se descarta al cerrar la unidad de trabajo y la siguiente estrena Bueno.

De ese coste sale el tope: **4 reanudaciones de corrección por unidad de trabajo**, el mismo techo que los lanzamientos de El Malo — cada informe suyo genera como mucho una corrección, así que un paso que respeta aquel tope cabe en este. Cuentan las correcciones, vengan de El Malo o de El Feo; no cuentan los turnos cortos —pedir un dato que faltaba en un informe— ni la respuesta a un `BLOQUEADO`, que es la continuación del paso, no una ronda. Si el tope se alcanza y algo sigue exigiendo corrección, no reanudes más: detente y consúltalo con el usuario. Un paso que pide una quinta ronda no es mala suerte: es la señal de que está mal partido, y la respuesta es replantearlo, no seguir pagando historial.

Si por lo que sea has perdido la referencia, lanza uno nuevo y **dile en el encargo que el trabajo previo no es suyo**, además de pasarle el informe: sin ese aviso leerá su propio código como ajeno y tenderá a rehacerlo.

De cada corrección espera un informe con lo mismo que el de entrega, acotado al arreglo: qué tocó, **el tamaño de la corrección** (no el del paso), los números de los verificadores que la clase pida y regenerados tras corregir, y si tocó código de pasos anteriores. Esos son los campos que necesitan las verificaciones de El Malo y de El Feo; si no vienen, pídeselos reanudándolo otra vez, sin consumir lanzamientos.

---

# El diff de la corrección

Las verificaciones —de El Malo y de El Feo— se acotan con un diff que contiene **solo la corrección**, no el paso entero. Producirlo es cosa tuya; `malo.md` y `feo.md` solo declaran que lo esperan como campo del encargo. Es una operación de git que escribe a un fichero: no te obliga a leer el código, y por eso sigue siendo tuya.

Se obtiene congelando el estado previo **antes** de que El Bueno toque nada, de modo que al terminar la corrección el diff contra esa foto sea exactamente ella.

**No lo congeles con `git add -A` sobre el índice real.** El área de staging es la frontera entre pasos: si el modo de ejecución deja ahí trabajo aprobado sin commitear, stagear ahora lo mezcla con el paso en curso, y el `git reset` que vendría después tira la frontera entera y te deja un diff del paso completo en vez de la corrección. Congela contra un **índice aparte**, que no toca el de verdad:

```bash
# nada más recibir el informe de fallos o el Informe de Desviaciones
export GIT_INDEX_FILE=<ruta-temporal>/gbu-prev.index
git read-tree HEAD && git add -A
unset GIT_INDEX_FILE

# cuando El Bueno haya terminado de corregir
GIT_INDEX_FILE=<ruta-temporal>/gbu-prev.index git diff > <ruta-temporal>/gbu-fix.diff
```

`read-tree HEAD` siembra el índice temporal con el último commit y `add -A` le añade todo lo que hay en disco en ese instante: la foto del «antes». Al terminar la corrección, `git diff` contra ese índice devuelve exactamente lo que ha cambiado desde entonces. El índice real no se toca en ningún momento, así que no hay `git reset` que deshacer y la frontera entre pasos sobrevive sola, funcione el modo de ejecución como funcione.

Dos cuidados:

- **Comprueba que el índice real sigue intacto** (`git status --short`) antes de continuar: si `GIT_INDEX_FILE` se te escapó de alguna orden, lo verás ahí.
- La `<ruta-temporal>` va **fuera del repo**, o los ficheros aparecerían dentro del propio diff. En Windows, ruta absoluta nativa (`$env:TEMP\…`), no `/tmp`; en PowerShell la variable se pone con `$env:GIT_INDEX_FILE = "…"` y se quita con `Remove-Item Env:GIT_INDEX_FILE`.

**Atajo para correcciones pequeñas.** Si sabes exactamente qué ficheros toca la corrección —El Bueno los lista en su informe de corrección— y son unos pocos, no hace falta ceremonia: acota el diff a esos ficheros y sáltate el índice aparte. La diferencia con antes es de dónde sale la lista: ya no de tu memoria de haberlo hecho, sino de su informe.

```bash
git add -N . && git diff -- <fichero> <fichero> > <ruta-temporal>/gbu-fix.diff
```

El índice aparte es para cuando la corrección es amplia, incierta, o crea ficheros que no tienes listados: entonces una foto del «antes» es más fiable que tu memoria. Si usas el atajo y luego descubres que la corrección tocó algo que no habías previsto, regenera el diff con todos los ficheros afectados y dilo: un diff de la corrección incompleto hace que el verificador audite media corrección creyendo que la ve entera, que es peor que no acotarla.

---

# Si las correcciones tocaron comportamiento

Mientras las desviaciones corregidas sean de forma (estilo, nombres, organización, convenciones), El Malo no vuelve a entrar: sus tests adversarios quedaron incorporados a la suite y El Bueno debe mantenerla en verde tras cada ajuste.

Si alguna desviación corregida era de comportamiento funcional o de reglas de negocio, cuando El Feo apruebe lanza **una única verificación** del subagente `malo` acotada a ese cambio, con la misma patrulla de instantáneas de la FASE 2, antes de dar el paso por terminado. Es una verificación, no una ronda nueva: no reabre el ciclo.

- Si sobrevive: cierra el paso.
- Si encuentra algo: **no vuelvas a la FASE 2**. Recógelo como observación para el usuario y cierra el paso diciéndolo, tratando su hallazgo como en la FASE 2: entrada en `TECHNICAL_DEBT.md` y test omitido con referencia a ella, nunca en rojo. Si lo que encuentra es grave —pérdida de datos, un contrato roto, una regresión en algo que ya funcionaba—, detente y consúltalo en vez de cerrar.

Sin este tope, corregir para El Feo podría reabrir a El Malo indefinidamente.
