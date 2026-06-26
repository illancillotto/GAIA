#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/push-local-db-to-ced.sh

Copia il database PostgreSQL locale sul server CED, con backup preventivo locale e remoto.

Variabili:
  CED_SSH_HOST=serverCed          Alias/host SSH del server CED
  CED_PROJECT_DIR=/opt/gaia       Directory progetto sul server
  LOCAL_ENV_FILE=.env             Env locale (sorgente dump)
  REMOTE_ENV_FILE=.env            Env remoto (credenziali postgres sul server)
  LOCAL_BACKUP_DIR=./backups/db   Directory backup locale
  REMOTE_BACKUP_DIR=backups/db    Directory backup remota (relativa a CED_PROJECT_DIR)
  COMPOSE_PROJECT_NAME=gaia       Nome progetto compose
  SSH_OPTS=""                     Opzioni extra ssh/scp
  CONFIRM_PUSH=yes                Obbligatorio per eseguire il restore remoto
  SKIP_REMOTE_BACKUP=no           yes per saltare il backup remoto (sconsigliato)
  REMOTE_RECREATE_DB=yes          yes per droppare/ricreare il DB remoto prima del restore
  EXCLUDE_FIREWALL_DATA=yes       yes per escludere i dati Sophos/firewall dal dump inviato al CED
  RUN_SMOKE_TEST=yes              yes per verificare /api/health dopo il restore
  GAIA_PROD_NGINX_PORT=8080       Porta nginx interna per smoke test

Flusso:
  1. backup locale del DB
  2. backup remoto del DB attuale (salvato sul server)
  3. trasferimento dump locale -> server
  4. stop servizi che usano il DB
  5. restore del dump locale sul postgres remoto
  6. riavvio servizi + smoke test opzionale

Attenzione:
  - operazione distruttiva sul database remoto
  - se CREDENTIAL_MASTER_KEY locale e remota differiscono, le credenziali cifrate
    importate (Bonifica, SISTER, ecc.) potrebbero non decifrarsi sul server
  - dopo il restore potrebbe essere necessario un nuovo login JWT

Esempi:
  CONFIRM_PUSH=yes ./scripts/push-local-db-to-ced.sh
  LOCAL_BACKUP_DIR=~/Backups/GAIA CONFIRM_PUSH=yes ./scripts/push-local-db-to-ced.sh
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

prune_local_backups() {
  local backup_dir="$1"
  local pattern="$2"
  local keep_count="$3"
  mapfile -t backups_to_remove < <(
    find "$backup_dir" -maxdepth 1 -type f -name "$pattern" -printf '%T@ %p\n' \
      | sort -nr \
      | awk -v keep="$keep_count" 'NR > keep { sub(/^[^ ]+ /, ""); print }'
  )
  if [[ "${#backups_to_remove[@]}" -eq 0 ]]; then
    return
  fi
  rm -f "${backups_to_remove[@]}"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

CED_SSH_HOST="${CED_SSH_HOST:-serverCed}"
CED_PROJECT_DIR="${CED_PROJECT_DIR:-/opt/gaia}"
LOCAL_ENV_FILE="${LOCAL_ENV_FILE:-.env}"
REMOTE_ENV_FILE="${REMOTE_ENV_FILE:-.env}"
LOCAL_BACKUP_DIR="${LOCAL_BACKUP_DIR:-./backups/db}"
REMOTE_BACKUP_DIR="${REMOTE_BACKUP_DIR:-backups/db}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-gaia}"
SSH_OPTS="${SSH_OPTS:-}"
CONFIRM_PUSH="${CONFIRM_PUSH:-no}"
SKIP_REMOTE_BACKUP="${SKIP_REMOTE_BACKUP:-no}"
REMOTE_RECREATE_DB="${REMOTE_RECREATE_DB:-yes}"
EXCLUDE_FIREWALL_DATA="${EXCLUDE_FIREWALL_DATA:-yes}"
RUN_SMOKE_TEST="${RUN_SMOKE_TEST:-yes}"
GAIA_PROD_NGINX_PORT="${GAIA_PROD_NGINX_PORT:-8080}"
BACKUP_RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-2}"

require_cmd ssh
require_cmd scp
require_cmd find

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$CONFIRM_PUSH" != "yes" ]]; then
  echo "Errore: operazione distruttiva. Imposta CONFIRM_PUSH=yes per procedere." >&2
  echo "Suggerimento: esegui prima un backup manuale su HDD:" >&2
  echo "  mkdir -p ~/Backups/GAIA" >&2
  echo "  ./scripts/backup-gaia-db.sh --output ~/Backups/GAIA --label manuale" >&2
  exit 1
fi

if [[ ! -f "$LOCAL_ENV_FILE" ]]; then
  echo "Errore: file env locale non trovato: $LOCAL_ENV_FILE" >&2
  exit 1
fi

LOCAL_CREDENTIAL_KEY="$(read_env_value "$LOCAL_ENV_FILE" "CREDENTIAL_MASTER_KEY" || true)"

echo "==> Step 1/6: backup preventivo locale"
LOCAL_BACKUP_OUTPUT="$(
  BACKUP_DIR="$LOCAL_BACKUP_DIR" \
    "$ROOT_DIR/scripts/backup-gaia-db.sh" \
    --env-file "$LOCAL_ENV_FILE" \
    --label pre-push
)"
LOCAL_BACKUP_PATH="$(printf '%s\n' "$LOCAL_BACKUP_OUTPUT" | tail -n1)"
if [[ -z "$LOCAL_BACKUP_PATH" || ! -f "$LOCAL_BACKUP_PATH" ]]; then
  echo "Errore: backup locale non valido o non trovato." >&2
  printf '%s\n' "$LOCAL_BACKUP_OUTPUT" >&2
  exit 1
fi
echo "    backup locale: $LOCAL_BACKUP_PATH"
prune_local_backups "$LOCAL_BACKUP_DIR" "gaia-*-pre-push.dump" "$BACKUP_RETENTION_COUNT"

TRANSFER_DUMP_PATH="$LOCAL_BACKUP_PATH"
if [[ "$EXCLUDE_FIREWALL_DATA" == "yes" ]]; then
  echo "==> Step 1b/6: dump di trasferimento senza dati firewall/Sophos"
  TRANSFER_DUMP_OUTPUT="$(
    BACKUP_DIR="$LOCAL_BACKUP_DIR" \
      "$ROOT_DIR/scripts/backup-gaia-db.sh" \
      --env-file "$LOCAL_ENV_FILE" \
      --label ced-push-slim \
      --exclude-table-data public.network_firewalls \
      --exclude-table-data public.network_firewall_events \
      --exclude-table-data public.network_firewall_metrics \
      --exclude-table-data public.network_firewall_hourly_rollups \
      --exclude-table-data public.network_detection_watchlist \
      --exclude-table-data public.network_sophos_config
  )"
  TRANSFER_DUMP_PATH="$(printf '%s\n' "$TRANSFER_DUMP_OUTPUT" | tail -n1)"
  if [[ -z "$TRANSFER_DUMP_PATH" || ! -f "$TRANSFER_DUMP_PATH" ]]; then
    echo "Errore: dump di trasferimento non valido o non trovato." >&2
    printf '%s\n' "$TRANSFER_DUMP_OUTPUT" >&2
    exit 1
  fi
  echo "    dump trasferimento: $TRANSFER_DUMP_PATH"
  prune_local_backups "$LOCAL_BACKUP_DIR" "gaia-*-ced-push-slim.dump" "$BACKUP_RETENTION_COUNT"
fi

echo "==> Step 2/6: verifica accesso server e env remoto"
REMOTE_CREDENTIAL_KEY="$(
  ssh $SSH_OPTS "$CED_SSH_HOST" "CED_PROJECT_DIR='$CED_PROJECT_DIR' REMOTE_ENV_FILE='$REMOTE_ENV_FILE' bash -s" <<'REMOTE_ENV'
set -Eeuo pipefail
cd "$CED_PROJECT_DIR"
if [[ ! -f "$REMOTE_ENV_FILE" ]]; then
  echo "Errore: env remoto non trovato: $CED_PROJECT_DIR/$REMOTE_ENV_FILE" >&2
  exit 1
fi
grep -E '^CREDENTIAL_MASTER_KEY=' "$REMOTE_ENV_FILE" | tail -n1 | cut -d= -f2- || true
REMOTE_ENV
)"

if [[ -n "$LOCAL_CREDENTIAL_KEY" && -n "$REMOTE_CREDENTIAL_KEY" && "$LOCAL_CREDENTIAL_KEY" != "$REMOTE_CREDENTIAL_KEY" ]]; then
  echo "ATTENZIONE: CREDENTIAL_MASTER_KEY locale e remota differiscono."
  echo "           Le credenziali cifrate nel dump potrebbero non funzionare sul server."
  echo "           Dopo il restore potrebbe servire reinserire le credenziali Bonifica/SISTER."
fi

REMOTE_BACKUP_NAME=""
if [[ "$SKIP_REMOTE_BACKUP" != "yes" ]]; then
  echo "==> Step 3/6: backup preventivo remoto"
  REMOTE_BACKUP_NAME="$(
    ssh $SSH_OPTS "$CED_SSH_HOST" \
      "CED_PROJECT_DIR='$CED_PROJECT_DIR' REMOTE_ENV_FILE='$REMOTE_ENV_FILE' REMOTE_BACKUP_DIR='$REMOTE_BACKUP_DIR' COMPOSE_PROJECT_NAME='$COMPOSE_PROJECT_NAME' BACKUP_RETENTION_COUNT='$BACKUP_RETENTION_COUNT' bash -s" <<'REMOTE_BACKUP'
set -Eeuo pipefail
cd "$CED_PROJECT_DIR"

read_env_value() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" "$REMOTE_ENV_FILE" | tail -n1 || true)"
  if [[ -z "$line" ]]; then
    return 1
  fi
  printf '%s' "${line#*=}"
}

prune_remote_backups() {
  local backup_dir="$1"
  local pattern="$2"
  local keep_count="$3"
  mapfile -t backups_to_remove < <(
    find "$backup_dir" -maxdepth 1 -type f -name "$pattern" -printf '%T@ %p\n' \
      | sort -nr \
      | awk -v keep="$keep_count" 'NR > keep { sub(/^[^ ]+ /, ""); print }'
  )
  if [[ "${#backups_to_remove[@]}" -eq 0 ]]; then
    return
  fi
  rm -f "${backups_to_remove[@]}"
}

POSTGRES_DB="$(read_env_value POSTGRES_DB || true)"
POSTGRES_USER="$(read_env_value POSTGRES_USER || true)"
POSTGRES_DB="${POSTGRES_DB:-gaia}"
POSTGRES_USER="${POSTGRES_USER:-gaia_app}"

if ! COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" ps --status running --services 2>/dev/null | grep -qx "postgres"; then
  echo "Errore: postgres remoto non in esecuzione in $CED_PROJECT_DIR" >&2
  exit 1
fi

postgres_container="$(COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" ps -q postgres)"
mkdir -p "$REMOTE_BACKUP_DIR"
timestamp="$(date +%Y%m%d-%H%M%S)"
backup_path="$REMOTE_BACKUP_DIR/gaia-${timestamp}-pre-restore.dump"
container_dump_path="/tmp/gaia-pre-restore-${timestamp}.dump"

COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" exec -T postgres pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -Fc \
  --no-owner \
  --no-privileges \
  -f "$container_dump_path"

docker cp "$postgres_container:$container_dump_path" "$backup_path"
COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" exec -T postgres rm -f "$container_dump_path"
prune_remote_backups "$REMOTE_BACKUP_DIR" "gaia-*-pre-restore.dump" "$BACKUP_RETENTION_COUNT"

printf '%s' "$backup_path"
REMOTE_BACKUP
  )"
  echo "    backup remoto: $CED_SSH_HOST:$CED_PROJECT_DIR/$REMOTE_BACKUP_NAME"
else
  echo "==> Step 3/6: backup remoto saltato (SKIP_REMOTE_BACKUP=yes)"
fi

echo "==> Step 4/6: trasferimento dump locale sul server"
remote_dump_name="$(basename "$TRANSFER_DUMP_PATH")"
scp $SSH_OPTS "$TRANSFER_DUMP_PATH" "$CED_SSH_HOST:$CED_PROJECT_DIR/releases/$remote_dump_name"
echo "    dump trasferito: $CED_SSH_HOST:$CED_PROJECT_DIR/releases/$remote_dump_name"

echo "==> Step 5/6: restore database remoto"
ssh $SSH_OPTS "$CED_SSH_HOST" \
  "CED_PROJECT_DIR='$CED_PROJECT_DIR' REMOTE_ENV_FILE='$REMOTE_ENV_FILE' COMPOSE_PROJECT_NAME='$COMPOSE_PROJECT_NAME' REMOTE_DUMP='releases/$remote_dump_name' REMOTE_RECREATE_DB='$REMOTE_RECREATE_DB' bash -s" <<'REMOTE_RESTORE'
set -Eeuo pipefail
cd "$CED_PROJECT_DIR"

read_env_value() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" "$REMOTE_ENV_FILE" | tail -n1 || true)"
  if [[ -z "$line" ]]; then
    return 1
  fi
  printf '%s' "${line#*=}"
}

POSTGRES_DB="$(read_env_value POSTGRES_DB || true)"
POSTGRES_USER="$(read_env_value POSTGRES_USER || true)"
POSTGRES_DB="${POSTGRES_DB:-gaia}"
POSTGRES_USER="${POSTGRES_USER:-gaia_app}"

if [[ ! -f "$REMOTE_DUMP" ]]; then
  echo "Errore: dump remoto non trovato: $CED_PROJECT_DIR/$REMOTE_DUMP" >&2
  exit 1
fi

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
echo "==> Stop servizi che usano il database"
COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" stop "${services_to_stop[@]}" || true

container_restore_path="/tmp/gaia-restore.dump"
postgres_container="$(COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" ps -q postgres)"

echo "==> Restore dump in $POSTGRES_DB"
docker cp "$REMOTE_DUMP" "$postgres_container:$container_restore_path"

if [[ "$REMOTE_RECREATE_DB" == "yes" ]]; then
  echo "==> Recreate remote database $POSTGRES_DB"
  COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" exec -T postgres \
    psql \
    -U "$POSTGRES_USER" \
    -d postgres \
    -v ON_ERROR_STOP=1 \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();"
  COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" exec -T postgres \
    dropdb \
    -U "$POSTGRES_USER" \
    --if-exists \
    "$POSTGRES_DB"
  COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" exec -T postgres \
    createdb \
    -U "$POSTGRES_USER" \
    "$POSTGRES_DB"
fi

COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" exec -T postgres \
  pg_restore \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --no-owner \
  --no-privileges \
  --exit-on-error \
  "$container_restore_path"
COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" exec -T postgres rm -f "$container_restore_path"

echo "==> Riavvio servizi"
COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" up -d --no-build --remove-orphans "${services_to_start[@]}"
REMOTE_RESTORE

if [[ "$RUN_SMOKE_TEST" == "yes" ]]; then
  echo "==> Step 6/6: smoke test"
  ssh $SSH_OPTS "$CED_SSH_HOST" \
    "GAIA_PROD_NGINX_PORT='$GAIA_PROD_NGINX_PORT' bash -s" <<'REMOTE_SMOKE'
set -Eeuo pipefail
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

wait_for_http "http://127.0.0.1:8000/health" "backend diretto /health"
wait_for_http "http://127.0.0.1:3000/login" "frontend diretto /login"
wait_for_http "http://127.0.0.1:${GAIA_PROD_NGINX_PORT}/api/health" "nginx /api/health"
wait_for_http "http://127.0.0.1:${GAIA_PROD_NGINX_PORT}/login" "nginx /login"
REMOTE_SMOKE
else
  echo "==> Step 6/6: smoke test saltato"
fi

cat <<EOF

==> Push database completato

Backup locale:
  $LOCAL_BACKUP_PATH

Dump trasferimento applicato:
  $TRANSFER_DUMP_PATH

Backup remoto pre-restore:
  ${REMOTE_BACKUP_NAME:+$CED_SSH_HOST:$CED_PROJECT_DIR/$REMOTE_BACKUP_NAME}
  ${REMOTE_BACKUP_NAME:-<saltato>}

Dump applicato sul server:
  $CED_SSH_HOST:$CED_PROJECT_DIR/releases/$remote_dump_name

Verifica manuale consigliata:
  - login su GAIA
  - pagina /organigramma o /presenze/organigramma
  - eventuale re-sync Bonifica se le credenziali cifrate non funzionano

EOF
