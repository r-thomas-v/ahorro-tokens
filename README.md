# ahorro-tokens · skill `/consumo` para Claude Code

Mide en qué se van tus tokens y te ayuda a gastar menos. Es seguro y no pierdes nada.
Toma lo mejor de [Gentle-AI](https://github.com/Gentleman-Programming/gentle-ai) (memoria entre sesiones, modelo según la tarea, lista de bloqueo, copias antes de escribir) y le suma un informe de consumo con tus datos reales. **No tiene telemetría ni dependencias, y no usa internet.**

## Instalar (1 minuto)
Necesitas [Claude Code](https://claude.com/claude-code) y Python 3.8 o superior.

```sh
git clone https://github.com/r-thomas-v/ahorro-tokens.git
cd ahorro-tokens
```
```sh
python instalar.py      # Windows
python3 instalar.py     # macOS / Linux
```
Un solo paso: instala la skill **y** deja activo el ahorro (aviso de contexto con la ruta correcta de tu sistema, bloqueo de lectura de `node_modules`/lockfiles/`.env`, auto-compactado al 25 % y reglas en `CLAUDE.md`). Solo añade, hace copias `.bak-FECHA` y se deshace con `/consumo deshacer`.
Opciones: `--simular` (ver sin tocar nada), `--solo-skill` (solo copiar la skill, como `install.ps1`/`install.sh`), `--sin-conectores` (apagar Drive/Canva/etc. dentro de Claude Code).

Sin git: botón verde **Code → Download ZIP**, descomprime y ejecuta el instalador.
Luego cierra y abre Claude Code y escribe `/consumo`.

**¿Equipo o clase?** Lee [GUIA-EQUIPO.md](GUIA-EQUIPO.md) (sirve también para quien usa claude.ai web) y copia [`plantilla-proyecto/`](plantilla-proyecto/) al repo del trabajo en grupo.

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
En Claude Code, **más del 90% de los tokens suele ser "caché leída"**: cada mensaje re-envía todo el historial de la sesión. Esa caché **no es el problema** (ya va con 90% de descuento; sin ella pagarías 10x): es el síntoma de un **contexto demasiado grande**. Una sesión de 500k de contexto re-lee 500k en *cada* mensaje.

Por eso `/consumo`:
- muestra el **gasto real ponderado** (caché leída 0,1x, escrita 1,25x, salida 5x), la **base fija** de cada sesión y el **contexto medio** por mensaje;
- **simula cuánto habrías ahorrado** haciendo `/clear` al pasar de 150k (en el ejemplo real: **-65%**);
- instala un **aviso automático** (hook, opcional) que te avisa cuando el contexto pasa de 150k;
- y `guardar` + `/clear` te deja cortar la sesión sin perder el hilo.

## Licencia
MIT. Úsalo, cópialo y adáptalo libremente.
