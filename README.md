# ahorro-tokens · skill `/consumo` para Claude Code

Mide en qué se van tus tokens y te ayuda a gastar menos. Es seguro y no pierdes nada.
Toma lo mejor de [Gentle-AI](https://github.com/Gentleman-Programming/gentle-ai) (memoria entre sesiones, modelo según la tarea, lista de bloqueo, copias antes de escribir) y le suma un informe de consumo con tus datos reales. **No tiene telemetría ni dependencias, y no usa internet.**

## Instalar (1 minuto)
Necesitas [Claude Code](https://claude.com/claude-code) y Python 3.8 o superior.

```sh
git clone https://github.com/r-thomas-v/ahorro-tokens.git
cd ahorro-tokens
```
```powershell
# Windows
powershell -ExecutionPolicy Bypass -File install.ps1
```
```sh
# macOS / Linux
sh install.sh
```
Sin git: botón verde **Code → Download ZIP**, descomprime y ejecuta el instalador.
Luego abre Claude Code y escribe `/consumo`.

## Comandos
| Comando | Qué hace | ¿Modifica algo? |
|---|---|---|
| `/consumo` | Informe de los últimos 7 días: por proyecto, día, modelo, herramienta y sesión, con consejos | No |
| `/consumo 30` / `/consumo proyecto web` | Otra ventana de tiempo o un solo proyecto | No |
| `/consumo sesion` | Cuánto pesa la sesión actual | No |
| `/consumo guardar` | Guarda una nota de traspaso en memoria para hacer `/clear` sin perder nada | Escribe 1 nota de memoria |
| `/consumo optimizar` | Bloquea la lectura de carpetas pesadas y secretos, y añade reglas de ahorro | Sí, **con confirmación y copia de seguridad** |
| `/consumo deshacer` | Restaura cualquier copia de seguridad | Restaura |
| `/consumo reglas` | Los 9 hábitos que más ahorran | No |

## Seguridad
- El informe **solo lee** `~/.claude/projects/*.jsonl`. No imprime el contenido de tus conversaciones, solo números, nombres de proyecto, herramientas y rutas.
- Usa solo la librería estándar de Python. No hace llamadas de red ni tiene telemetría.
- `optimizar` **solo añade** reglas, hace copia antes (`settings.json.bak-FECHA`) y valida el JSON resultante. Si falla, restaura la copia.
- Usa solo funciones oficiales de Claude Code (skills, `permissions.deny`, CLAUDE.md, memoria). No intercepta tráfico ni toca tu cuenta, así que no hay riesgo con Anthropic.

## Ejemplo real (30 días de uso, un estudiante)
```
DE QUÉ ESTÁ HECHO EL GASTO
  Caché leída (historial re-leído)     835.3M   97.7%  ███████████████████████·
  Caché escrita (contexto nuevo)        17.3M    2.0%  ························
  Salida (lo que escribe Claude)         2.4M    0.3%  ························

SESIONES MÁS CARAS
  sesión    total  pico ctx  turnos
  37a5568e  604.3M    961.3k    1490  ⚠ larga
```
Una sola sesión demasiado larga se llevó el 71% del mes.

## Por qué ahorra de verdad
En Claude Code, **más del 90% del gasto suele ser "caché leída"**: cada mensaje re-envía todo el historial de la sesión. Por eso lo que más ahorra no es escribir menos, sino **tener sesiones cortas**. `/consumo` te muestra qué sesiones se pasaron, y `guardar` + `/clear` te permite cortarlas sin perder el hilo.

## Licencia
MIT. Úsalo, cópialo y adáptalo libremente.
