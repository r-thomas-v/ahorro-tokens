#!/usr/bin/env python3
"""
aviso_contexto.py - Hook UserPromptSubmit de la skill /consumo.

Antes de cada mensaje del usuario mira cuánto contexto lleva la sesión (último
'usage' del transcript) y, si pasa del umbral, avisa al usuario y a Claude para
que proponga '/consumo guardar' + '/clear'.

SEGURO: solo lee el final del transcript de la sesión actual; no escribe nada,
no usa internet. Si algo falla, sale en silencio (nunca bloquea el mensaje).

Umbral: variable de entorno CONSUMO_AVISO (tokens, por defecto 150000).
"""
import json
import os
import sys


def contexto_actual(ruta):
    with open(ruta, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 400_000))
        lineas = f.read().decode("utf-8", "replace").splitlines()
    for linea in reversed(lineas):
        if '"usage"' not in linea or '"isSidechain":true' in linea:
            continue
        try:
            u = json.loads(linea)["message"]["usage"]
        except Exception:
            continue
        return (u.get("input_tokens", 0) or 0) + (u.get("cache_creation_input_tokens", 0) or 0) \
            + (u.get("cache_read_input_tokens", 0) or 0)
    return 0


def main():
    try:
        datos = json.load(sys.stdin)
        umbral = int(os.environ.get("CONSUMO_AVISO", "150000"))
        ctx = contexto_actual(datos["transcript_path"])
    except Exception:
        return 0
    if ctx < umbral:
        return 0
    k = f"{ctx // 1000}k"
    print(json.dumps({
        "systemMessage": f"⚠ Contexto en {k} tokens: cada mensaje re-lee todo eso. "
                         "Si cambias de tarea: /consumo guardar y luego /clear.",
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": f"[consumo] El contexto de esta sesión ya es de {k} tokens. "
                                 "Al terminar tu respuesta, en UNA línea, sugiere al usuario '/consumo guardar' "
                                 "y luego '/clear' (o '/compact' si la tarea sigue a medias).",
        },
    }))  # ASCII puro: evita errores de codificacion en la consola de Windows
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # nunca bloquear el mensaje del usuario
