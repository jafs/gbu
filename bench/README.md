# Medir lo que cuesta el patrón

Herramienta de línea de comandos que lee las trazas que Claude Code ya guarda de un proyecto y dice **en qué se van los tokens**: qué reparte cada rol, cuánto pesa el contexto que se relee en cada turno, qué trabajo se repite y qué resultados de herramienta engordan la conversación.

No lanza gbu ni ejecuta nada del proyecto. Solo lee sesiones que ya ocurrieron, en `~/.claude/projects/`, y nunca escribe ahí.

Python 3.10, biblioteca estándar, sin dependencias.

## Los dos comandos

```bash
# Analizar un proyecto y archivar su informe
python bench/session_report.py C:\ruta\al\proyecto --desde <fecha-o-commit>

# Comparar dos informes ya archivados
python bench/session_report.py --comparar <proyecto> [<version-base> <version-nueva>]
```

Desde un proyecto con el plugin instalado, el comando `/gbu:medir` hace lo mismo y además interpreta el resultado.

## El ciclo

1. **Archiva la línea base** antes de tocar nada. `--desde` acepta una fecha ISO o un commit del repositorio del proyecto, que es la forma precisa de decir «desde que el patrón entró aquí».
2. **Lee los hallazgos** y cambia los prompts. Un cambio cada vez: si mueves prompts y modelos a la vez, la comparación no distingue cuál hizo qué.
3. **Publica la versión** (ver [`../RELEASING.md`](../RELEASING.md)) y trabaja un tiempo con ella.
4. **Vuelve a analizar**, filtrando con `--version` la versión nueva, y archiva el segundo informe.
5. **Compara**. El comparador cruza métricas y hallazgos; la lectura la hace Claude con `/gbu:medir comparar`.

Los informes van a `~/.claude/gbu-informes/<proyecto>/<version>.json`, con su markdown al lado. Están **fuera de todo repositorio a propósito**: nombran rutas, ficheros y comandos de proyectos que pueden ser privados. Un informe nunca pisa a otro; si ya hay uno de esa versión, el nuevo se archiva al lado y se avisa.

## Cómo se leen las métricas

Dos no son obvias, y sin entenderlas el informe se malinterpreta.

### Coste normalizado

Los tokens no valen todos lo mismo. El coste se expresa en **unidades de token de entrada equivalente**:

```
entrada × 1  +  escritura de caché × 1,25  +  lectura de caché × 0,1  +  salida × 5
```

Sirve para comparar sesiones entre sí, no para calcular una factura. Los pesos son ajustables porque la proporción real depende del modelo y de la tarifa.

### Turn-tokens

Los tokens de un bloque **multiplicados por los turnos que lo releerán**. Es la métrica que explica por qué una conversación larga se encarece sola.

Un fichero de mil tokens leído en el turno 5 de una conversación de cien turnos cuesta noventa y cinco mil turn-tokens. El mismo fichero leído en el turno 98 cuesta dos mil. **El mismo contenido, cuarenta veces más caro por haber entrado antes.** Por eso los detectores estiman el derroche en turn-tokens y no en tokens sueltos: dónde entra algo importa tanto como su tamaño.

### Prelude fijo

El contexto del primer turno menos lo que el transcript había escrito hasta entonces. Aproxima lo que no aparece en la traza y sin embargo se paga en cada turno: el prompt de sistema, las definiciones de las herramientas y los ficheros de contexto del proyecto. Es una resta entre una cifra real y una estimada, así que es orientativa.

### Flujo

Pasos cerrados, lanzamientos de subagente y reloj de pared por rol. Los pasos se cuentan por la marca `PASO COMPLETADO` que el Sheriff declara al cerrar cada unidad de trabajo — si una sesión se corta a mitad de paso, ese paso no cuenta. De ahí sale **la señal roja del patrón: las rondas de El Malo por paso** (lanzamientos de `malo` ÷ pasos). Un cambio que ahorra tokens pero sube las rondas ha salido caro, y el comparador la cruza entre versiones junto al `coste_por_paso`. El reloj del sheriff incluye la espera humana —las paradas entre pasos viven en su transcript—, así que el informe lo presenta como «resto», no como trabajo.

## Lo que el informe no puede decir

- **Los tokens de los hallazgos no se suman entre categorías.** Cada detector mira desde un ángulo distinto y varios señalan a la vez el mismo bloque. El total por categoría es legítimo; un total general sería mentira.
- **El pensamiento no se reparte por bloques.** Llega al transcript con el texto vacío y solo la firma, así que en el reparto de turn-tokens cuenta como cero. Su total sí consta, sale del `usage` y se informa aparte.
- **La versión de una sesión puede estar supuesta.** Se resuelve por la marca `gbu vX.Y.Z` que la sesión dejó escrita; si no la lleva, por la versión instalada hoy, y si no, por la de por defecto. El informe dice por qué vía se atribuyó cada una, porque no es lo mismo un dato que una suposición.

## Los detectores

| Categoría | Qué señala |
| --- | --- |
| `relectura` | El mismo rol se trajo el mismo fichero al contexto más de una vez |
| `lectura-compartida` | Varios roles leyeron el mismo fichero por separado; mide lo que cuesta el aislamiento |
| `comando-repetido` | La misma orden de consola ejecutada literalmente igual |
| `resultado-gigante` | Un resultado de herramienta que entra entero y se relee en cada turno |
| `bloque-caro` | Un bloque cuya permanencia en el contexto supera el umbral |
| `contexto-desbocado` | Una conversación que pasó del umbral sin cortarse |
| `prelude-excesivo` | Contexto fijo por encima de lo esperable para el rol |

Los umbrales son parámetros con valores sacados de sesiones reales, no constantes escondidas: lo que es mucho depende del proyecto.

Cada hallazgo lleva un **identificador estable**, derivado de su contenido y no de su posición ni de su título. Es lo que permite cruzar dos informes y distinguir un problema resuelto de uno que solo cambió de sitio.

## Las pruebas

```bash
python -m unittest discover -s bench -p "test_*.py"
```

La suite entera tarda menos de un segundo y no invoca `claude` ni `git`: los procesos externos entran por una costura que las pruebas sustituyen.
