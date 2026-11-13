# Guía rápida: gastar menos límite de Claude

Por qué se acaba: **cada mensaje vuelve a enviar toda la conversación**. Un chat largo hace que el mensaje 40 cueste muchísimo más que el mensaje 1. La regla de oro: **chats cortos, uno por tarea.**

## Si usas claude.ai (web o app)
1. **Un chat nuevo por tarea.** Terminaste un ejercicio → chat nuevo. No sigas en el mismo "porque ya tiene contexto".
2. **Antes de cambiar de chat**, pide: *"Resúmeme en 10 líneas lo que hemos decidido"* y pega ese resumen en el chat nuevo.
3. **Edita tu mensaje en vez de corregir** (lápiz ✏️): si Claude entendió mal, edita la pregunta; no añadas "no, me refería a…".
4. **Usa Proyectos** para el material de la asignatura (enunciado, apuntes): se sube una vez y no lo pegas en cada chat.
5. **No subas PDFs enteros** si solo necesitas un capítulo: recorta o copia la parte útil.
6. **Apaga lo que no uses** (botón de herramientas / conectores: búsqueda web, Drive, etc.). Cada herramienta activa ocupa espacio en cada mensaje.
7. **Pide respuestas cortas**: "responde en 5 líneas" o "solo el código, sin explicación".
8. Para preguntas simples, elige un **modelo más ligero** (Haiku/Sonnet) si tu plan lo permite.

## Si usas Claude Code (terminal)
1. Instala una vez: descarga el repo y ejecuta `python instalar.py` (Windows) o `python3 instalar.py` (Mac/Linux). Te avisará cuando la conversación crezca demasiado.
2. `/consumo` te dice cuánto gastas y qué te ahorraría más.
3. Al terminar una tarea: `/consumo guardar` y luego `/clear`.
4. En el repo del trabajo en grupo, copiad la carpeta `plantilla-proyecto/` (ver su `LEEME.md`).

## Lo que NO hace falta
- No hace falta escribir "por favor" ni ser escueto contigo mismo: lo caro es el **historial largo**, no tus frases.
- Pagar más no lo arregla: con un chat de 100 mensajes también se acaba el plan Max.
