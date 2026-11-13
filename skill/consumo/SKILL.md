---
name: consumo
description: Mide y reduce el consumo de tokens de Claude Code de forma segura. Úsala cuando el usuario escriba /consumo, pregunte cuántos tokens gasta, por qué se le acaba el límite, quiera ahorrar tokens, guardar el estado antes de /clear o /compact, u optimizar su configuración para gastar menos. Subcomandos: (vacío) informe 7 días, "sesion", "30" u otro número de días, "proyecto <nombre>", "guardar", "optimizar", "deshacer", "reglas".
---

# /consumo — ahorro real de tokens, sin riesgos

Principios que NO se rompen:
1. **Solo lectura por defecto.** El informe nunca escribe, borra ni envía nada. Sin internet, sin telemetría.
2. **Nada se cambia sin confirmación** del usuario, y todo cambio deja **copia de seguridad** con fecha y es reversible con `/consumo deshacer`.
3. **Nunca** se muestran, copian ni guardan secretos (`.env`, claves, tokens, contraseñas).
4. Sé breve: esta skill existe para ahorrar tokens, no para gastarlos. Respuestas cortas, sin repetir el informe.

El script está en `scripts/consumo.py` (junto a este archivo). Ejecútalo con `python -I "<ruta-de-esta-skill>/scripts/consumo.py" ...`.

## Subcomandos

### `/consumo` · `/consumo 30` · `/consumo proyecto <nombre>`
1. Ejecuta el script (`--dias 7` por defecto, o el número que dé el usuario; `--proyecto <nombre>` si lo pide) con `--top 5`.
2. Muestra la salida tal cual en un bloque de código.
3. Debajo, **máximo 3 líneas**: la acción concreta que más ahorraría según esos datos (ej. "tu sesión X de DIMA tuvo 961k de contexto: divide en tareas y usa `/consumo guardar` + `/clear`").

### `/consumo sesion`
Ejecuta con `--sesion actual`. Si el pico de contexto supera ~150k, recomienda `/consumo guardar` y luego `/clear` (o `/compact` si la tarea sigue a medias).

### `/consumo guardar`  (memoria entre sesiones, idea tomada de Engram/Gentle-AI)
Objetivo: que el usuario pueda hacer `/clear` sin perder nada y sin re-explicar el proyecto en la siguiente sesión.
1. Redacta una nota de traspaso de **máximo 25 líneas**: objetivo actual, qué se hizo, decisiones tomadas y por qué, archivos clave (rutas), próximos pasos exactos, comandos útiles. **Sin secretos.**
2. Guárdala en el sistema de memoria del usuario (el directorio de memoria indicado en tu prompt de sistema) como memoria de tipo `project`, con nombre `traspaso-<proyecto>`. Si ya existe, **actualízala** (no dupliques). Añade/actualiza su línea en `MEMORY.md`.
3. Responde en 2 líneas: dónde quedó guardada y "ya puedes usar `/clear`; en la próxima sesión di 'continúa con <proyecto>'".

### `/consumo optimizar`  (configuración ahorradora, inspirada en la deny-list de Gentle-AI)
1. Lee `reference/settings-ahorro.json` y el `settings.json` del usuario (`~/.claude/settings.json`).
2. Muestra en una lista corta qué reglas `permissions.deny` faltan y para qué sirve cada grupo:
   - **Pesados** (node_modules, .next, dist, build, lockfiles, .git, minificados): evitan que Claude lea miles de líneas inútiles. Ahorro directo.
   - **Secretos** (.env, claves): seguridad; Claude no podrá leerlos con Read.
   - **Aviso de contexto** (hook): antes de cada mensaje mide el contexto y, si pasa de 150k, avisa para hacer `/consumo guardar` + `/clear`. Es el que más ahorra: ataca la causa de la caché leída.
3. Pregunta con AskUserQuestion qué grupos aplicar (Aviso de contexto recomendado; Pesados recomendado; Secretos recomendado; también "Reglas de trabajo en CLAUDE.md").
4. Antes de escribir: copia `settings.json` a `settings.json.bak-AAAAMMDD-HHMMSS` en la misma carpeta.
5. **Solo AÑADE** entradas a `permissions.deny` (no borres ni cambies nada existente; no dupliques). Verifica que el JSON resultante es válido (`python -c "import json;json.load(open(...))"`). Si algo falla, restaura la copia.
6. Si eligió "Aviso de contexto": añade en `hooks.UserPromptSubmit` del `settings.json` (sin tocar hooks existentes; si ya hay uno con `aviso_contexto.py`, no lo dupliques) la entrada de `reference/settings-ahorro.json` → `aviso`, sustituyendo `<RUTA_SKILL>` por la ruta absoluta de esta skill con barras `/`. Prueba el comando una vez pasándole `{"transcript_path": "<un .jsonl real>"}` por stdin con `CONSUMO_AVISO=1000` y comprueba que imprime JSON. Umbral configurable con la variable de entorno `CONSUMO_AVISO` (en `env` del settings).
7. Si eligió "Reglas en CLAUDE.md": añade al final de `~/.claude/CLAUDE.md` (créalo si no existe; si existe, cópialo antes a `.bak-…`) el bloque de `reference/claude-md-ahorro.md` **incluyendo sus marcadores** `<!-- consumo:inicio -->` / `<!-- consumo:fin -->`. Si los marcadores ya existen, reemplaza solo lo que hay entre ellos.
8. Avisa honestamente: la regla Read no impide que un comando de Bash lea esos archivos; es una barrera de ahorro y de buenas prácticas, no una caja fuerte.

### `/consumo deshacer`
Lista las copias `settings.json.bak-*` y `CLAUDE.md.bak-*`, pregunta cuál restaurar, y restaura copiando la copia encima (dejando a su vez una copia del estado actual). Para el bloque de CLAUDE.md basta con borrar lo que hay entre los marcadores `consumo`.

### `/consumo reglas`
Muestra `reference/reglas-ahorro.md` (los hábitos que más ahorran).

## Cómo leer los números (para explicarlo si preguntan)
- **Caché leída**: cada mensaje vuelve a enviar TODO el historial de la sesión. Suele ser >90% de los tokens, pero ya va con 90% de descuento; sin caché costaría 10x más. **No es el problema, es el síntoma**: no se "apaga", se reduce achicando el contexto (sesiones cortas, `/clear`, `/compact`, el aviso de contexto).
- **Gasto real (ponderado)**: pesa cada tipo como la API (leída 0,1x, escrita 1,25x, salida 5x). Muestra qué cuesta de verdad.
- **Base fija**: contexto del primer mensaje (prompt, herramientas, CLAUDE.md, memoria). Se paga en cada mensaje; se baja quitando conectores MCP que no uses.
- **Ahorro con /clear**: simulación de cuánto menos se habría gastado volviendo a la base cada vez que el contexto pasaba de 150k.
- **Recargas de caché**: tras ~5 min sin actividad la caché caduca y se re-escribe todo el historial a 1,25x. Tras una pausa, mejor sesión nueva con la nota de traspaso.
- **Pico de contexto**: lo grande que llegó a ser la conversación. >150k = cada mensaje cuesta muchísimo.
- **Resultados pesados**: lecturas/capturas/herramientas que metieron mucho texto de golpe.
- No se muestran precios en dinero: dependen del plan y del modelo, y el script no inventa cifras.
