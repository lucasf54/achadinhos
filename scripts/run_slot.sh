#!/usr/bin/env bash
# Executa um disparo do Lu Achadinhos. Chamado pelo cron 3x/dia.
# Uso: run_slot.sh <slot>   (slot = manha | almoco | noite)
set -euo pipefail

SLOT="${1:-dev}"
PROJ="$HOME/achadinhos"
LOG_DIR="$PROJ/data/logs"
mkdir -p "$LOG_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
LOG="$LOG_DIR/slot_${SLOT}_${TS}.log"

cd "$PROJ"
echo "=== Disparo $SLOT em $(date) ===" >> "$LOG"

# Roda o disparo real (grava no banco + publica via PUBLISH_VIA)
.venv/bin/python -m luachadinhos run-slot --slot "$SLOT" --publicar >> "$LOG" 2>&1

echo "=== Fim em $(date) ===" >> "$LOG"

# Limpa logs com mais de 14 dias
find "$LOG_DIR" -name "slot_*.log" -mtime +14 -delete 2>/dev/null || true
