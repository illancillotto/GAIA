#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  CONFIRM_NAS_IMPORT=yes ./scripts/import-gaia-db-from-nas.sh
  CONFIRM_NAS_IMPORT=yes ./scripts/import-gaia-db-from-nas.sh --manifest-path /volume1/Backups/GAIA/db/archives/2026/06/gaia-20260619-120000.dump.manifest.json

Importa in locale un dump PostgreSQL conservato sul NAS.

Opzioni:
  --env-file PATH         File env locale di destinazione restore. Default: .env
  --remote-root PATH      Root remota NAS. Default: NAS_DB_BACKUP_ROOT o /volume1/Backups/GAIA/db
  --manifest-path PATH    Manifest remoto esplicito. Default: latest.json sotto remote root
  --download-dir DIR      Directory locale per dump/manifest scaricati. Default: ./backups/db/nas-imports
  --local-backup-dir DIR  Directory backup preventivo locale. Default: ./backups/db
  --recreate-db yes|no    Droppa e ricrea il DB prima del restore. Default: yes
  --run-smoke-test yes|no Esegue smoke test finali. Default: yes
  --local-nginx-port N    Porta nginx locale per smoke test. Default: 8080
  -h, --help              Mostra questo messaggio
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

wait_for_http() {
  local url="$1"
  local label="$2"
  local attempts="${3:-60}"
  local delay_sec="${4:-5}"
  local attempt=1

  while (( attempt <= attempts )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "Smoke test OK: $label"
      return 0
    fi
    sleep "$delay_sec"
    attempt=$((attempt + 1))
  done

  echo "Errore: endpoint non pronto dopo $((attempts * delay_sec))s: $label ($url)" >&2
  return 1
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=".env"
REMOTE_ROOT="${NAS_DB_BACKUP_ROOT:-/volume1/Backups/GAIA/db}"
MANIFEST_PATH=""
DOWNLOAD_DIR="$ROOT_DIR/backups/db/nas-imports"
LOCAL_BACKUP_DIR="$ROOT_DIR/backups/db"
RECREATE_DB="yes"
RUN_SMOKE_TEST="yes"
LOCAL_NGINX_PORT="${LOCAL_NGINX_PORT:-8080}"
CONFIRM_NAS_IMPORT="${CONFIRM_NAS_IMPORT:-no}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="${2:-}"
      shift 2
      ;;
    --remote-root)
      REMOTE_ROOT="${2:-}"
      shift 2
      ;;
    --manifest-path)
      MANIFEST_PATH="${2:-}"
      shift 2
      ;;
    --download-dir)
      DOWNLOAD_DIR="${2:-}"
      shift 2
      ;;
    --local-backup-dir)
      LOCAL_BACKUP_DIR="${2:-}"
      shift 2
      ;;
    --recreate-db)
      RECREATE_DB="${2:-}"
      shift 2
      ;;
    --run-smoke-test)
      RUN_SMOKE_TEST="${2:-}"
      shift 2
      ;;
    --local-nginx-port)
      LOCAL_NGINX_PORT="${2:-}"
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

require_cmd docker
require_cmd python3
require_cmd curl
require_cmd pg_restore
require_cmd psql

cd "$ROOT_DIR"

if [[ "$CONFIRM_NAS_IMPORT" != "yes" ]]; then
  echo "Errore: operazione distruttiva. Imposta CONFIRM_NAS_IMPORT=yes per procedere." >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Errore: file env locale non trovato: $ENV_FILE" >&2
  exit 1
fi

POSTGRES_DB="$(read_env_value "$ENV_FILE" "POSTGRES_DB" || true)"
POSTGRES_USER="$(read_env_value "$ENV_FILE" "POSTGRES_USER" || true)"
POSTGRES_DB="${POSTGRES_DB:-gaia}"
POSTGRES_USER="${POSTGRES_USER:-gaia_app}"

echo "==> Step 1/5: backup preventivo locale"
LOCAL_BACKUP_OUTPUT="$(
  BACKUP_DIR="$LOCAL_BACKUP_DIR" \
    "$ROOT_DIR/scripts/backup-gaia-db.sh" \
    --env-file "$ENV_FILE" \
    --label pre-nas-import
)"
LOCAL_BACKUP_PATH="$(printf '%s\n' "$LOCAL_BACKUP_OUTPUT" | tail -n1)"
if [[ -z "$LOCAL_BACKUP_PATH" || ! -f "$LOCAL_BACKUP_PATH" ]]; then
  echo "Errore: backup preventivo locale non valido o non trovato." >&2
  printf '%s\n' "$LOCAL_BACKUP_OUTPUT" >&2
  exit 1
fi
echo "    backup locale: $LOCAL_BACKUP_PATH"

echo "==> Step 2/5: download dump dal NAS"
DOWNLOADED_DUMP_PATH="$(
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
  PYTHONPATH="$ROOT_DIR/backend" python3 -m app.scripts.nas_db_transfer download \
    --output-dir "$DOWNLOAD_DIR" \
    --remote-root "$REMOTE_ROOT" \
    --manifest-path "$MANIFEST_PATH"
)"
if [[ -z "$DOWNLOADED_DUMP_PATH" || ! -f "$DOWNLOADED_DUMP_PATH" ]]; then
  echo "Errore: dump NAS scaricato non valido o non trovato." >&2
  exit 1
fi
echo "    dump scaricato: $DOWNLOADED_DUMP_PATH"

if [[ "$DOWNLOADED_DUMP_PATH" == *.dump ]]; then
  pg_restore --list "$DOWNLOADED_DUMP_PATH" >/dev/null
elif [[ "$DOWNLOADED_DUMP_PATH" == *.sql ]]; then
  head -n 20 "$DOWNLOADED_DUMP_PATH" | grep -Eq 'PostgreSQL database dump|Dumped by pg_dump' || {
    echo "Errore: il file SQL scaricato non sembra un dump PostgreSQL valido." >&2
    exit 1
  }
else
  echo "Errore: estensione dump non supportata: $DOWNLOADED_DUMP_PATH" >&2
  exit 1
fi

echo "==> Step 3/5: stop servizi locali che usano il database"
services_to_stop=(
  backend
  frontend
  elaborazioni-worker-runtime
  elaborazioni-worker-visure
  elaborazioni-worker-autodoc
  scanner
  arp-helper
  martin
)
services_to_start=(
  backend
  frontend
  elaborazioni-worker-runtime
  elaborazioni-worker-visure
  elaborazioni-worker-autodoc
  scanner
  arp-helper
  martin
)
docker compose stop "${services_to_stop[@]}" || true

restore_finished="no"
cleanup() {
  if [[ "$restore_finished" != "yes" ]]; then
    docker compose up -d --no-build --remove-orphans "${services_to_start[@]}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "==> Step 4/5: restore dump nel database locale"
postgres_container="$(docker compose ps -q postgres)"
if [[ -z "$postgres_container" ]]; then
  echo "Errore: impossibile risolvere il container postgres locale." >&2
  exit 1
fi

container_restore_path="/tmp/$(basename "$DOWNLOADED_DUMP_PATH")"
docker cp "$DOWNLOADED_DUMP_PATH" "$postgres_container:$container_restore_path"

if [[ "$RECREATE_DB" == "yes" ]]; then
  docker compose exec -T postgres \
    psql \
    -U "$POSTGRES_USER" \
    -d postgres \
    -v ON_ERROR_STOP=1 \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();"
  docker compose exec -T postgres dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB"
  docker compose exec -T postgres createdb -U "$POSTGRES_USER" "$POSTGRES_DB"
fi

if [[ "$DOWNLOADED_DUMP_PATH" == *.dump ]]; then
  docker compose exec -T postgres \
    pg_restore \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --no-owner \
    --no-privileges \
    --exit-on-error \
    "$container_restore_path"
else
  docker compose exec -T postgres \
    psql \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -v ON_ERROR_STOP=1 \
    -f "$container_restore_path"
fi
docker compose exec -T postgres rm -f "$container_restore_path"

echo "==> Step 5/5: riavvio servizi"
docker compose up -d --no-build --remove-orphans "${services_to_start[@]}"
restore_finished="yes"

if [[ "$RUN_SMOKE_TEST" == "yes" ]]; then
  wait_for_http "http://127.0.0.1:8000/health" "backend diretto /health"
  wait_for_http "http://127.0.0.1:3000/login" "frontend diretto /login"
  wait_for_http "http://127.0.0.1:${LOCAL_NGINX_PORT}/api/health" "nginx /api/health"
  wait_for_http "http://127.0.0.1:${LOCAL_NGINX_PORT}/login" "nginx /login"
fi

cat <<EOF

==> Import database da NAS completato

Backup preventivo locale:
  $LOCAL_BACKUP_PATH

Dump importato:
  $DOWNLOADED_DUMP_PATH

EOF
