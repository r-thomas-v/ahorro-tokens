# Instala la skill /consumo en ~/.claude/skills/consumo (Windows / PowerShell)
# Seguro: si ya existe una versión, la respalda antes de reemplazarla. No toca settings.json.
$ErrorActionPreference = "Stop"
$origen = Join-Path $PSScriptRoot "skill\consumo"
$base = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $HOME ".claude" }
$destino = Join-Path $base "skills\consumo"

if (Test-Path $destino) {
    # La copia va FUERA de skills\: dentro, Claude la cargaria como una skill duplicada.
    $carpetaBak = Join-Path $base "skills-backup"
    New-Item -ItemType Directory -Force $carpetaBak | Out-Null
    $bak = Join-Path $carpetaBak "consumo.bak-$(Get-Date -Format yyyyMMdd-HHmmss)"
    Move-Item $destino $bak
    Write-Host "Versión anterior respaldada en $bak"
}
New-Item -ItemType Directory -Force (Split-Path $destino) | Out-Null
Copy-Item $origen $destino -Recurse
Write-Host "Listo: skill instalada en $destino"
Write-Host "Abre Claude Code y escribe /consumo"
