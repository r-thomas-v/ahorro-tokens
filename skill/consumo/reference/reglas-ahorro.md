# Los hábitos que más tokens ahorran (de mayor a menor impacto)

1. **Una tarea = una sesión.** Cada mensaje re-envía todo el historial. Una sesión de 1.000 mensajes cuesta muchísimo más que 10 sesiones de 100.
2. **`/consumo guardar` → `/clear`** al terminar o cambiar de tarea. No pierdes nada: el estado queda en memoria.
3. **`/compact`** si la tarea sigue pero la conversación ya es larga (pico de contexto >150k).
4. **Pide cosas concretas**: "arregla el botón X en `src/Header.tsx`" gasta una fracción de "revisa todo el proyecto".
5. **Modelo proporcional a la tarea** (idea de Gentle-AI): `/model` → Sonnet para tareas rutinarias; Opus para diseño, depuración difícil y auditorías.
6. **No pegues archivos ni logs enteros**: pega solo el error o el fragmento relevante.
7. **Capturas de pantalla y navegador** pesan mucho: úsalas cuando de verdad aporten.
8. **`/consumo optimizar`** una vez: bloquea carpetas pesadas (node_modules, .next, lockfiles) y secretos.
9. **Revisa `/consumo` cada semana** para ver qué proyecto o hábito se está comiendo el límite.
