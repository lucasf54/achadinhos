#!/usr/bin/env bash
# Backup diário do banco luachadinhos. Chamado pelo cron 1x/dia (madrugada).
# Gera um dump comprimido e, se a OCI CLI estiver configurada, envia pro
# Oracle Object Storage. Mantém os últimos 7 dumps locais.
set -euo pipefail

PROJ="$HOME/achadinhos"
BKP_DIR="$PROJ/data/backups"
mkdir -p "$BKP_DIR"
TS="$(date +%Y%m%d_%H%M)"
DUMP="$BKP_DIR/luachadinhos_${TS}.sql.gz"

# 1. Dump comprimido
PGPASSWORD=lu pg_dump -h localhost -U lu luachadinhos | gzip > "$DUMP"
echo "Backup gerado: $DUMP ($(du -h "$DUMP" | cut -f1))"

# 2. Upload pro Oracle Object Storage (se OCI CLI configurada)
#    Preencher BUCKET e descomentar quando a OCI CLI estiver pronta.
# BUCKET="achadinhos-backups"
# if command -v oci >/dev/null 2>&1; then
#     oci os object put --bucket-name "$BUCKET" --file "$DUMP" \
#         --name "$(basename "$DUMP")" --force && echo "Enviado ao Object Storage"
# fi

# 3. Mantém só os 7 backups locais mais recentes
ls -1t "$BKP_DIR"/luachadinhos_*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm -f
echo "Backups locais mantidos: $(ls -1 "$BKP_DIR"/*.sql.gz 2>/dev/null | wc -l)"
