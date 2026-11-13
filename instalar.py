#!/usr/bin/env python3
"""Instalación en 1 paso de /consumo para Claude Code (Windows, macOS y Linux).

Uso:   python instalar.py              (Windows)
       python3 instalar.py             (macOS / Linux)
Opciones:
  --simular         muestra lo que haría sin tocar nada
  --solo-skill      copia la skill y no toca settings.json ni CLAUDE.md
  --sin-conectores  además apaga los conectores de claude.ai (Drive, Canva...) dentro de Claude Code

Seguro: solo AÑADE reglas (nunca borra), hace copia .bak-FECHA de cada archivo que toca
y se deshace con /consumo deshacer. No usa internet.
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
ORIGEN = REPO / "skill" / "consumo"
BASE = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
DESTINO = BASE / "skills" / "consumo"
SELLO = time.strftime("%Y%m%d-%H%M%S")
args = set(sys.argv[1:])
SIMULAR = "--simular" in args
try:
    sys.stdout.reconfigure(encoding="utf-8")  # acentos bien en la consola de Windows
except Exception:
    pass


def paso(msg):
    print(("[simulación] " if SIMULAR else "") + msg)


def respaldar(archivo: Path):
    if archivo.exists() and not SIMULAR:
        shutil.copy2(archivo, archivo.with_name(f"{archivo.name}.bak-{SELLO}"))


def instalar_skill():
    if DESTINO.exists():
        # La copia va FUERA de skills/: dentro, Claude la cargaría como skill duplicada.
        bak = BASE / "skills-backup" / f"consumo.bak-{SELLO}"
        paso(f"Versión anterior respaldada en {bak}")
        if not SIMULAR:
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(DESTINO), str(bak))
    paso(f"Skill instalada en {DESTINO}")
    if not SIMULAR:
        DESTINO.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ORIGEN, DESTINO)


def configurar_settings():
    ruta = BASE / "settings.json"
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    except json.JSONDecodeError:
        print(f"AVISO: {ruta} no es JSON válido; no lo toco. Arréglalo y repite.")
        return
    plantilla = json.loads((ORIGEN / "reference" / "settings-ahorro.json").read_text(encoding="utf-8"))
    deny = datos.setdefault("permissions", {}).setdefault("deny", [])
    nuevas = [r for r in plantilla["pesados"] + plantilla["secretos"] if r not in deny]
    deny.extend(nuevas)
    if nuevas:
        paso(f"{len(nuevas)} reglas de lectura bloqueada añadidas (node_modules, lockfiles, .env...)")

    # Hook de aviso de contexto, con la ruta y el comando de Python correctos para este equipo.
    py = "python" if os.name == "nt" else "python3"
    script = (DESTINO / "scripts" / "aviso_contexto.py").as_posix()
    eventos = datos.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
    ya = any("aviso_contexto.py" in h.get("command", "") for e in eventos for h in e.get("hooks", []))
    if not ya:
        eventos.append({"hooks": [{"type": "command", "command": f'{py} -I "{script}"', "timeout": 10}]})
        paso("Aviso de contexto activado (avisa al pasar de 150k para hacer /clear)")

    env = datos.setdefault("env", {})
    if "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE" not in env:
        env["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"] = "25"
        paso("Auto-compactado más temprano (25%)")
    if "--sin-conectores" in args and env.get("ENABLE_CLAUDEAI_MCP_SERVERS") != "false":
        env["ENABLE_CLAUDEAI_MCP_SERVERS"] = "false"
        paso("Conectores de claude.ai apagados en Claude Code")

    if not SIMULAR:
        respaldar(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        json.loads(ruta.read_text(encoding="utf-8"))  # verificación


def configurar_claude_md():
    ruta = BASE / "CLAUDE.md"
    bloque = (ORIGEN / "reference" / "claude-md-ahorro.md").read_text(encoding="utf-8").strip()
    actual = ruta.read_text(encoding="utf-8") if ruta.exists() else ""
    ini, fin = "<!-- consumo:inicio -->", "<!-- consumo:fin -->"
    if ini in actual and fin in actual:
        nuevo = actual[: actual.index(ini)] + bloque + actual[actual.index(fin) + len(fin):]
    else:
        nuevo = (actual.rstrip() + "\n\n" if actual.strip() else "") + bloque + "\n"
    if nuevo == actual:
        return
    paso("Reglas de ahorro añadidas a CLAUDE.md")
    if not SIMULAR:
        respaldar(ruta)
        ruta.write_text(nuevo, encoding="utf-8")


def main():
    if not ORIGEN.exists():
        sys.exit("No encuentro skill/consumo: ejecuta este archivo desde la carpeta del repo.")
    instalar_skill()
    if "--solo-skill" not in args:
        configurar_settings()
        configurar_claude_md()
    print("\nListo. Cierra y abre Claude Code y escribe /consumo")
    print("Para deshacer: /consumo deshacer (las copias .bak-%s están junto a cada archivo)." % SELLO)


if __name__ == "__main__":
    main()
