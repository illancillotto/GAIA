#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/export-gaia-db-to-nas.sh
  ./scripts/export-gaia-db-to-nas.sh --label manuale
  ./scripts/export-gaia-db-to-nas.sh --remote-root /volume1/Backups/GAIA/db

Esporta un dump PostgreSQL locale su NAS via SSH/SFTP usando le credenziali NAS_*.

Opzioni:
  --env-file PATH         File env locale da cui leggere POSTGRES_* e NAS_*. Default: .env
  --local-output DIR      Directory locale in cui generare prima il dump. Default: ./backups/db
  --remote-root PATH      Root remota NAS. Default: NAS_DB_BACKUP_ROOT o /volume1/Backups/GAIA/db
  --label TEXT            Suffisso opzionale del dump
  --format FMT            custom|plain. Default: custom
  --retention-count N     Numero dump da mantenere sul NAS. Default: NAS_DB_BACKUP_RETENTION_COUNT o 14
  --exclude-table-data T  Ripetibile, inoltrato a backup-gaia-db.sh
  -h, --help              Mostra questo messaggio
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Errore: comando richiesto non trovato: $1" >&2
    exit 1
  fi
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=".env"
LOCAL_OUTPUT_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/db}"
REMOTE_ROOT="${NAS_DB_BACKUP_ROOT:-/volume1/Backups/GAIA/db}"
LABEL=""
FORMAT="custom"
RETENTION_COUNT="${NAS_DB_BACKUP_RETENTION_COUNT:-14}"
EXCLUDE_TABLE_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="${2:-}"
      shift 2
      ;;
    --local-output)
      LOCAL_OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --remote-root)
      REMOTE_ROOT="${2:-}"
      shift 2
      ;;
    --label)
      LABEL="${2:-}"
      shift 2
      ;;
    --format)
      FORMAT="${2:-}"
      shift 2
      ;;
    --retention-count)
      RETENTION_COUNT="${2:-}"
      shift 2
      ;;
    --exclude-table-data)
      table_name="${2:-}"
      if [[ -z "$table_name" ]]; then
        echo "Errore: --exclude-table-data richiede il nome tabella." >&2
        exit 1
      fi
      EXCLUDE_TABLE_ARGS+=("--exclude-table-data" "$table_name")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Errore: opzione sconosciuta: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

EFFECTIVE_LABEL="${LABEL:-nas-export}"

require_cmd docker
require_cmd python3

cd "$ROOT_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Errore: file env non trovato: $ENV_FILE" >&2
  exit 1
fi

echo "==> Step 1/2: dump locale PostgreSQL"
LOCAL_BACKUP_OUTPUT="$(
  BACKUP_DIR="$LOCAL_OUTPUT_DIR" \
    "$ROOT_DIR/scripts/backup-gaia-db.sh" \
    --env-file "$ENV_FILE" \
    --label "$EFFECTIVE_LABEL" \
    --format "$FORMAT" \
    "${EXCLUDE_TABLE_ARGS[@]}"
)"
LOCAL_BACKUP_PATH="$(printf '%s\n' "$LOCAL_BACKUP_OUTPUT" | tail -n1)"
if [[ -z "$LOCAL_BACKUP_PATH" || ! -f "$LOCAL_BACKUP_PATH" ]]; then
  echo "Errore: dump locale non valido o non trovato." >&2
  printf '%s\n' "$LOCAL_BACKUP_OUTPUT" >&2
  exit 1
fi
echo "    dump locale: $LOCAL_BACKUP_PATH"

echo "==> Step 2/2: upload dump su NAS"
NAS_MANIFEST_PATH="$(
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
  PYTHONPATH="$ROOT_DIR/backend" python3 -m app.scripts.nas_db_transfer export \
    --local-path "$LOCAL_BACKUP_PATH" \
    --remote-root "$REMOTE_ROOT" \
    --env-file "$ENV_FILE" \
    --label "$EFFECTIVE_LABEL" \
    --retention-count "$RETENTION_COUNT"
)"

cat <<EOF

==> Export database verso NAS completato

Dump locale creato:
  $LOCAL_BACKUP_PATH

Manifest remoto:
  $NAS_MANIFEST_PATH

EOF
