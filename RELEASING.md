# Publicar una versión de gbu

Checklist para cuando cambies los prompts del patrón y quieras que los proyectos que lo tienen instalado se lo puedan traer con `/plugin update gbu`.

El patrón se distribuye como plugin de Claude Code. Los manifiestos viven en `.claude-plugin/`:

- `plugin.json` — el plugin en sí: `version` y las rutas a `commands` (directorio) y `agents` (lista explícita de ficheros).
- `marketplace.json` — el catálogo; apunta al propio repo con `source: "./"`.

## Pasos

1. **Haz los cambios** en `.claude/commands/*.md` y `.claude/agents/*.md`, como siempre.

2. **Sube `version` en `.claude-plugin/plugin.json`.** Versionado semántico, interpretado sobre el comportamiento del patrón:
   - *patch* — retoques de redacción que no cambian el flujo.
   - *minor* — reglas nuevas, fases o argumentos nuevos, topes distintos.
   - *major* — cambios que rompen planes o costumbres existentes (renombrar comandos, cambiar los tokens de aprobación, cambiar la estructura que espera `PLAN.md`).

3. **Actualiza la versión anunciada en `.claude/commands/gbu.md`.** Hay una línea con `gbu vX.Y.Z` que el Sheriff anuncia al arrancar; es la marca que deja constancia en la traza de la sesión de con qué versión se ejecutó. Si no la subes, el análisis posterior atribuirá las ejecuciones a la versión equivocada.

4. **Si añades o quitas ficheros de agente**, añádelos o quítalos de la lista `agents` de `plugin.json`. Los comandos no hace falta tocarlos: ahí se declara el directorio entero.

5. **Mide antes de publicar.** Archiva un informe de un proyecto que esté ejecutando la versión saliente, para tener contra qué comparar después:

   ```bash
   python bench/session_report.py <ruta-del-proyecto>
   ```

   Es lo que convierte el cambio de prompts en algo comprobable en vez de una impresión. Cómo se lee lo que sale: [`bench/README.md`](bench/README.md).

6. **Valida los manifiestos:**

   ```bash
   claude plugin validate .
   ```

7. **Commitea** los cambios (prompts + los dos manifiestos + `gbu.md`).

8. **Crea el tag de release:**

   ```bash
   claude plugin tag .
   ```

   Genera el tag `gbu--vX.Y.Z` comprobando que `plugin.json` y la entrada del marketplace concuerdan.

9. **Sube commit y tag:**

   ```bash
   git push && git push --tags
   ```

## Después

En cada proyecto que lo use: `/plugin update gbu`, y reiniciar Claude Code para que el cambio se aplique. `/plugin list` confirma la versión instalada.

Cuando lleve un tiempo corriendo, vuelve a medir y compara contra la línea base del paso 5:

```bash
python bench/session_report.py <ruta-del-proyecto> --version <la-nueva>
python bench/session_report.py --comparar <proyecto>
```

Un cambio cada vez: si tocas prompts y modelos a la vez, la comparación no distingue cuál hizo qué.

## Comprobación rápida

Si algo no cuadra, lo primero:

- `claude plugin validate .` — manifiestos.
- `grep -n "gbu v" .claude/commands/gbu.md` — que la versión anunciada sea la nueva.
- `git tag --list "gbu--v*"` — que el tag exista y no esté repetido.
