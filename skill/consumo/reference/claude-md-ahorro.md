<!-- consumo:inicio -->
## Ahorro de tokens (skill /consumo)
- Antes de leer un archivo grande, busca con Grep y lee solo el rango de líneas necesario.
- No re-leas archivos que ya están en la conversación salvo que hayan cambiado.
- Respuestas cortas: sin repetir el código que acabas de escribir ni resumir lo obvio.
- Una tarea por sesión. Si el contexto ya es grande o la tarea cambia, sugiere `/consumo guardar` y luego `/clear`.
- Para búsquedas amplias o tareas mecánicas, usa un subagente con un modelo ligero si el usuario lo permite.
- Al iniciar, revisa si existe una memoria `traspaso-<proyecto>` y continúa desde ahí en vez de re-explorar.
<!-- consumo:fin -->
