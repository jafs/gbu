---
description: "📏 Mide el coste de un proyecto que ejecuta gbu, y compara versiones del patrón"
argument-hint: "ruta del proyecto, o: comparar <proyecto> [<version-base> <version-nueva>]"
---

Mides lo que cuesta ejecutar el patrón en un proyecto real, leyendo las trazas de sesiones que ya ocurrieron. No lanzas gbu, no ejecutas nada del proyecto y no abres los transcripts a mano: para eso está la herramienta.

La herramienta vive en `${CLAUDE_PLUGIN_ROOT}/bench/session_report.py`. Si trabajas dentro del propio repositorio del patrón, es `bench/session_report.py`.

Hay dos modos y los distinguen los argumentos.

---

# Modo analizar

Se pide con la ruta de un proyecto.

Ejecuta:

```
python "${CLAUDE_PLUGIN_ROOT}/bench/session_report.py" <ruta-del-proyecto> [--desde <fecha-o-commit>]
```

La herramienta resuelve sola con qué versión del patrón se ejecutó cada sesión, archiva el informe en `~/.claude/gbu-informes/<proyecto>/<version>.json` y resume por pantalla.

Lo que respondes:

1. **Los avisos primero.** Si la ventana mezcla versiones del patrón, dilo antes que nada: cambia lo que significa todo lo demás. Igual con las sesiones cuya versión está supuesta y no leída.
2. La cabecera: cuántas sesiones entraron, cuántas se descartaron, el coste total y el reparto por rol.
3. **El flujo**: pasos completados y **rondas de El Malo por paso**, que es la señal roja del patrón — por encima de 2, dilo como problema aunque el coste haya bajado. Si no hay marcas de paso, di que las rondas no se pueden atribuir, no que son cero.
4. Los hallazgos más caros, con su identificador, para poder seguirlos en el informe siguiente.
5. Dónde quedó archivado.

Lo que **no** haces: volcar el informe entero en la conversación. Está archivado precisamente para no pagarlo dos veces. Si el proyecto no tiene sesiones, o ninguna entra en la ventana, la herramienta lo dice con un mensaje claro: repítelo tal cual en vez de investigar por tu cuenta.

---

# Modo comparar

Se pide con la palabra `comparar`, el proyecto y, opcionalmente, dos versiones.

Ejecuta:

```
python "${CLAUDE_PLUGIN_ROOT}/bench/session_report.py" --comparar <proyecto> [<version-base> <version-nueva>]
```

Sin versiones compara los dos informes archivados más recientes. Con ellas compara las que se pidan, que no tienen por qué ser consecutivas. Si una versión no tiene informe archivado, la herramienta lo dice y enumera las que sí hay: repite esa lista y para. **No compares otra cosa** porque se parezca.

Aquí sí emites un **veredicto razonado**:

- **Si ha mejorado o empeorado, y por qué.** Mira las cifras por sesión, por turno y por paso antes que los totales: dos ventanas casi nunca cubren el mismo trabajo, y un total que baja porque se trabajó menos no es una mejora del patrón. `coste_por_paso` es la cifra que mejor resiste esa trampa.
- **Las rondas de El Malo por paso mandan sobre el coste.** Es la señal roja: si suben aunque el coste baje, el cambio ha salido caro —una ronda extra cuesta más que casi cualquier ahorro de contexto— y el veredicto lo dice así. El reloj por rol se lee con su letra pequeña: el «resto» del sheriff incluye la espera humana.
- **Si algún rol cambió de modelo.** Si lo hizo, la variación de coste de ese rol no dice nada sobre los prompts, y hay que decirlo en vez de atribuírsela al patrón.
- **Qué hallazgos se cerraron, cuáles resistieron y cuáles son nuevos.** Un hallazgo nuevo caro justo después de un cambio de prompt es la señal más útil del informe.
- **Qué atacar en la siguiente versión**, en orden de lo que cuesta.

El veredicto se apoya **solo en la salida del comparador**. Si te falta un dato, pide otra ejecución de la herramienta con otros argumentos. No abres los transcripts: leerlos cuesta exactamente lo que esta herramienta existe para medir, y hacerlo invalidaría la medición de la propia sesión en la que estás.

---

# Lo que no se mide así

Cambiar los prompts y los modelos a la vez deja la comparación sin valor: la variación no se puede atribuir a ninguno de los dos. Si ves que ha pasado, dilo y recomienda separar los cambios antes que interpretar las cifras.
