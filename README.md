# GBU — El Bueno, el Feo y el Malo

Un patrón de orquestación multi-agente para desarrollar software con [Claude Code](https://claude.com/claude-code), inspirado en el western de Sergio Leone: un Sheriff coordina a cuatro especialistas que planifican, implementan, atacan y auditan el código, paso a paso, hasta completar la tarea.

La idea central: **separar quien escribe el código de quien lo juzga**. Quien implementa trabaja con todo el contexto; quienes verifican trabajan aislados, sin haber visto la implementación, para juzgar solo lo que hay en disco y sin el sesgo de aprobar su propio trabajo.

## Los personajes

| Personaje | Rol | Cómo se ejecuta |
|---|---|---|
| **El Sheriff** (`/gbu`) | Orquesta el patrón completo | Agente principal |
| 🥸 **El Listo** (`/listo`) | Convierte la tarea en un plan incremental (`PLAN.md`) | Rol adoptado por el Sheriff, solo al inicio |
| 🤠 **El Bueno** (`/bueno`) | Implementa el siguiente paso del plan y deja los tests en verde | Rol adoptado por el Sheriff, con todo el contexto |
| 🌵 **El Malo** (`/malo`) | QA adversario: intenta romper la implementación con casos hostiles | **Subagente aislado**, parte de cero |
| 👺 **El Feo** (`/feo`) | Auditor estricto: rechaza cualquier desviación de la especificación o las convenciones | **Subagente aislado**, parte de cero |

## El flujo

```text
FASE 0 (una sola vez)
  El Listo analiza el proyecto y los acuerdos del equipo
  y escribe PLAN.md: Tarea + Contexto + Pasos con checkboxes

Por cada paso pendiente del plan:

  FASE 1 — El Bueno implementa el paso y deja la suite de tests en verde
     │
  FASE 2 — El Malo (subagente) ataca los cambios: nulls, límites,
     │     datos corruptos, concurrencia... Sus tests quedan en la
     │     suite como regresión.
     │       ├─ SOBREVIVIO_AL_MALO → continúa
     │       └─ Informe de fallos → El Bueno corrige todo de una
     │          pasada y El Malo verifica (máx. 3 lanzamientos)
     │
  FASE 3 — El Feo (subagente) audita contra el plan y las convenciones
     │       ├─ APROBADO_POR_EL_FEO → continúa
     │       └─ Informe de Desviaciones → El Bueno corrige y El Feo
     │          verifica (máx. 3 lanzamientos). Si alguna desviación
     │          era funcional, El Malo da una última pasada acotada.
     │
  Fin del paso — checkbox marcado en PLAN.md y cambios a staging
                 (git add -A, sin commit: eso es decisión tuya)

Cuando no quedan pasos: COMPLETADO CON ÉXITO
```

Si algún verificador rechaza el trabajo tres veces seguidas, o un paso del plan ya no encaja con la realidad del código, el Sheriff se detiene y te pide ayuda en lugar de insistir a ciegas.

## Decisiones de diseño

- **`PLAN.md` es el único artefacto compartido.** El Listo es el único que lee la documentación del proyecto (`CLAUDE.md`, README, acuerdos de equipo): sintetiza todo lo relevante en la sección "Contexto" del plan, y el resto de agentes trabajan exclusivamente con el plan y el código en disco. Menos relecturas, menos tokens, arranques en frío baratos.
- **Malo antes que Feo.** Primero se estabiliza el comportamiento, después se pule la forma. Así los arreglos de estilo del bucle con El Feo no obligan a re-atacar: los tests adversarios de El Malo ya montan guardia en la suite, que El Bueno debe mantener en verde tras cada ajuste.
- **El staging de git marca la frontera entre pasos.** Lo aprobado se stagea; lo que está sin stagear es el paso en curso. Los verificadores solo miran lo sin stagear, así que nunca re-auditan trabajo ya validado. El patrón no hace commits: la historia del repositorio es tuya.
- **Informes agregados, verificaciones acotadas.** Malo y Feo completan su pasada entera y entregan todos los hallazgos de una vez (una corrección por iteración, no una por fallo). Cuando vuelven a entrar, solo verifican el informe anterior y lo tocado por la corrección.
- **Salida disciplinada.** Los verificadores no narran su proceso ni enumeran lo que está bien: responden con el token exacto de aprobación o con el informe de lo que falla. Nada más.
- **Modelos por rol.** El Feo corre en un modelo más rápido (`model: sonnet` en su frontmatter) porque su trabajo es contrastar contra una checklist. El Malo hereda el modelo de la sesión: diseñar buenos ataques es la parte difícil. Ajusta ambos a tu gusto.

## Instalación

Copia los dos directorios en la raíz de tu proyecto:

```text
tu-proyecto/
└── .claude/
    ├── commands/      # gbu.md, listo.md, bueno.md, feo.md, malo.md
    └── agents/        # feo.md, malo.md  (los subagentes aislados)
```

No hay nada que compilar ni configurar: son ficheros markdown que Claude Code carga automáticamente como comandos slash y subagentes.

## Uso

El modo normal es lanzar el patrón completo:

```text
/gbu implementa un endpoint REST para dar de alta usuarios con validación de email
```

- Si no existe `PLAN.md`, El Listo lo genera primero a partir de tu descripción (o de la ruta a un fichero/issue que le pases).
- Si ya existe, el Sheriff retoma directamente el primer checkbox sin marcar — puedes parar y relanzar `/gbu` cuando quieras: el plan en disco es el estado.

Consejos:

- **Revisa `PLAN.md` antes de dejar correr el ciclo.** Es el contrato que seguirán todos los agentes; dos minutos ahí valen más que cualquier corrección posterior.
- Si tienes acuerdos de equipo (un directorio de *agreements*, guías de estilo), díselo en el prompt inicial para que El Listo los sintetice en el plan.
- Los cambios aprobados quedan en staging: revisa y haz commit con la granularidad que prefieras.

También puedes invocar piezas sueltas:

```text
/listo <tarea>     # solo generar el plan
/bueno             # implementar el siguiente paso, sin verificación
/malo              # lanzar solo el ataque sobre los cambios actuales
/feo               # lanzar solo la auditoría sobre los cambios actuales
```

## Adáptalo a tu LLM favorito

Aquí no hay ni una línea de código: todo el patrón son prompts en markdown. Eres completamente libre de adaptarlo al LLM o herramienta que quieras — Gemini CLI, Codex, Cursor, aider, un orquestador propio... Los conceptos viajan bien:

- Los ficheros de `commands/` son prompts de sistema con un pequeño frontmatter; cualquier herramienta con comandos o plantillas de prompt los acepta casi tal cual.
- Los de `agents/` solo necesitan que tu herramienta pueda lanzar una sesión limpia e independiente (un subagente, otro proceso, otra llamada a la API) cuyo único canal de vuelta sea su respuesta final.
- Lo importante no es la sintaxis sino las reglas del juego: plan en disco como única memoria compartida, verificadores sin contexto de la implementación, tokens exactos de aprobación, informes solo de lo que falla y bucles con tope.

Si lo adaptas, mejoras o descubres que algún personaje necesita mano dura, adelante: el patrón es tuyo.
