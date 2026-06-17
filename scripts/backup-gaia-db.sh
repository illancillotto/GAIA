#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/backup-gaia-db.sh
  ./scripts/backup-gaia-db.sh --output ~/Backups/GAIA
  ./scripts/backup-gaia-db.sh --output ./backups/db --label pre-push

Opzioni:
  --output DIR     Directory di destinazione. Default: ./backups/db
  --label TEXT     Suffisso opzionale nel nome file (es. pre-push, manuale)
  --env-file PATH  File env da cui leggere POSTGRES_*. Default: .env
  --format FMT     Formato dump: custom|plain. Default: custom
  --exclude-table-data TABLE
                   Esclude i dati della tabella indicata mantenendo lo schema.
                   Opzione ripetibile; formato consigliato: public.nome_tabella
  -h, --help       Mostra questo messaggio

Il dump viene salvato come:
  gaia-YYYYMMDD-HHMMSS[(-label)].dump   (custom)
  gaia-YYYYMMDD-HHMMSS[(-label)].sql     (plain)

Esempio backup manuale su HDD esterno:
  mkdir -p /mnt/hdd/Backups/GAIA
  ./scripts/backup-gaia-db.sh --output /mnt/hdd/Backups/GAIA --label manuale
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Errore: comando richiesto non trovato: $1" >&2
    exit 1
  fi
}

read_env_value() {
  local env_file="$1"
  local key="$2"
  local line
  line="$(grep -E "^${key}=" "$env_file" | tail -n1 || true)"
  if [[ -z "$line" ]]; then
    return 1
  fi
  printf '%s' "${line#*=}"
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/db}"
LABEL=""
ENV_FILE=".env"
FORMAT="custom"
EXCLUDE_TABLE_DATA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --label)
      LABEL="${2:-}"
      shift 2
      ;;
    --env-file)
      ENV_FILE="${2:-}"
      shift 2
      ;;
    --format)
      FORMAT="${2:-}"
      shift 2
      ;;
    --exclude-table-data)
      table_name="${2:-}"
      if [[ -z "$table_name" ]]; then
        echo "Errore: --exclude-table-data richiede il nome tabella." >&2
        exit 1
      fi
      EXCLUDE_TABLE_DATA_ARGS+=("--exclude-table-data=$table_name")
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

if [[ "$FORMAT" != "custom" && "$FORMAT" != "plain" ]]; then
  echo "Errore: --format deve essere custom o plain." >&2
  exit 1
fi

require_cmd docker

cd "$ROOT_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Errore: file env non trovato: $ENV_FILE" >&2
  exit 1
fi

POSTGRES_DB="$(read_env_value "$ENV_FILE" "POSTGRES_DB" || true)"
POSTGRES_USER="$(read_env_value "$ENV_FILE" "POSTGRES_USER" || true)"
POSTGRES_DB="${POSTGRES_DB:-gaia}"
POSTGRES_USER="${POSTGRES_USER:-gaia_app}"

if ! docker compose ps --status running --services 2>/dev/null | grep -qx "postgres"; then
  echo "Errore: il container postgres non risulta in esecuzione. Avvia lo stack con: make up" >&2
  exit 1
fi

postgres_container="$(docker compose ps -q postgres)"
if [[ -z "$postgres_container" ]]; then
  echo "Errore: impossibile risolvere il container postgres." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

timestamp="$(date +%Y%m%d-%H%M%S)"
if [[ -n "$LABEL" ]]; then
  safe_label="$(printf '%s' "$LABEL" | tr ' /:' '---')"
  base_name="gaia-${timestamp}-${safe_label}"
else
  base_name="gaia-${timestamp}"
fi

if [[ "$FORMAT" == "custom" ]]; then
  backup_path="$OUTPUT_DIR/${base_name}.dump"
  container_dump_path="/tmp/${base_name}.dump"
  echo "==> Backup PostgreSQL locale (formato custom)"
  echo "    database: $POSTGRES_DB"
  echo "    utente:     $POSTGRES_USER"
  echo "    output:     $backup_path"
  docker compose exec -T postgres pg_dump \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -Fc \
    --no-owner \
    --no-privileges \
    "${EXCLUDE_TABLE_DATA_ARGS[@]}" \
    -f "$container_dump_path"
  docker cp "$postgres_container:$container_dump_path" "$backup_path"
  docker compose exec -T postgres rm -f "$container_dump_path"
else
  backup_path="$OUTPUT_DIR/${base_name}.sql"
  container_sql_path="/tmp/${base_name}.sql"
  echo "==> Backup PostgreSQL locale (formato plain SQL)"
  echo "    database: $POSTGRES_DB"
  echo "    utente:     $POSTGRES_USER"
  echo "    output:     $backup_path"
  docker compose exec -T postgres pg_dump \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --no-owner \
    --no-privileges \
    "${EXCLUDE_TABLE_DATA_ARGS[@]}" \
    -f "$container_sql_path"
  docker cp "$postgres_container:$container_sql_path" "$backup_path"
  docker compose exec -T postgres rm -f "$container_sql_path"
fi

bytes="$(wc -c < "$backup_path" | tr -d ' ')"
echo "==> Backup completato: $backup_path ($bytes byte)"
printf '%s\n' "$backup_path"
