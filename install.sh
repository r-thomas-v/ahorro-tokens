#!/usr/bin/env sh
# Instala la skill /consumo en ~/.claude/skills/consumo (macOS / Linux / Git Bash)
# Seguro: si ya existe una versión, la respalda antes de reemplazarla. No toca settings.json.
set -e
ORIGEN="$(cd "$(dirname "$0")" && pwd)/skill/consumo"
BASE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
DESTINO="$BASE/skills/consumo"
if [ -e "$DESTINO" ]; then
  # La copia va FUERA de skills/: dentro, Claude la cargaría como una skill duplicada.
  mkdir -p "$BASE/skills-backup"
  BAK="$BASE/skills-backup/consumo.bak-$(date +%Y%m%d-%H%M%S)"
  mv "$DESTINO" "$BAK"
  echo "Versión anterior respaldada en $BAK"
fi
mkdir -p "$BASE/skills"
cp -R "$ORIGEN" "$DESTINO"
echo "Listo: skill instalada en $DESTINO"
echo "Abre Claude Code y escribe /consumo"
