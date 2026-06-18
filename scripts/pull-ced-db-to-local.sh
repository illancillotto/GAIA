#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/pull-ced-db-to-local.sh

Copia il database PostgreSQL del server CED in locale, con backup preventivo locale
e export sorgente remoto conservato sul server.

Variabili:
  CED_SSH_HOST=serverCed          Alias/host SSH del server CED
  CED_PROJECT_DIR=/opt/gaia       Directory progetto sul server
  LOCAL_ENV_FILE=.env             Env locale (destinazione restore)
  REMOTE_ENV_FILE=.env            Env remoto (sorgente dump)
  LOCAL_BACKUP_DIR=./backups/db   Directory backup locale
  REMOTE_BACKUP_DIR=backups/db    Directory backup remota (relativa a CED_PROJECT_DIR)
  COMPOSE_PROJECT_NAME=gaia       Nome progetto compose
  SSH_OPTS=""                     Opzioni extra ssh/scp
  CONFIRM_PULL=yes                Obbligatorio per eseguire il restore locale
  SKIP_REMOTE_EXPORT=no           yes per riusare un dump remoto gia presente
  REMOTE_DUMP_PATH=               Percorso dump remoto da scaricare se SKIP_REMOTE_EXPORT=yes
  LOCAL_RECREATE_DB=yes           yes per droppare/ricreare il DB locale prima del restore
  RUN_SMOKE_TEST=yes              yes per verificare backend/frontend locali dopo il restore
  LOCAL_NGINX_PORT=8080           Porta nginx locale per smoke test opzionale
  BACKUP_RETENTION_COUNT=2        Numero backup locali/remoti da mantenere per pattern

Flusso:
  1. backup preventivo locale
  2. verifica accesso server e chiavi credenziali
  3. export del DB remoto sul server
  4. trasferimento dump remoto -> locale
  5. stop servizi locali che usano il DB
  6. restore del dump remoto sul postgres locale
  7. riavvio servizi + smoke test opzionale

Attenzione:
  - operazione distruttiva sul database locale
  - se CREDENTIAL_MASTER_KEY locale e remota differiscono, le credenziali cifrate
    importate dal server potrebbero non decifrarsi in locale
  - dopo il restore potrebbe essere necessario un nuovo login JWT

Esempi:
  CONFIRM_PULL=yes ./scripts/pull-ced-db-to-local.sh
  LOCAL_ENV_FILE=.env.production CONFIRM_PULL=yes ./scripts/pull-ced-db-to-local.sh
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
CONFIRM_PULL="${CONFIRM_PULL:-no}"
SKIP_REMOTE_EXPORT="${SKIP_REMOTE_EXPORT:-no}"
REMOTE_DUMP_PATH="${REMOTE_DUMP_PATH:-}"
LOCAL_RECREATE_DB="${LOCAL_RECREATE_DB:-yes}"
RUN_SMOKE_TEST="${RUN_SMOKE_TEST:-yes}"
LOCAL_NGINX_PORT="${LOCAL_NGINX_PORT:-8080}"
BACKUP_RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-2}"

require_cmd ssh
require_cmd scp
require_cmd find
require_cmd docker

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$CONFIRM_PULL" != "yes" ]]; then
  echo "Errore: operazione distruttiva. Imposta CONFIRM_PULL=yes per procedere." >&2
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

echo "==> Step 1/7: backup preventivo locale"
LOCAL_BACKUP_OUTPUT="$(
  BACKUP_DIR="$LOCAL_BACKUP_DIR" \
    "$ROOT_DIR/scripts/backup-gaia-db.sh" \
    --env-file "$LOCAL_ENV_FILE" \
    --label pre-pull
)"
LOCAL_BACKUP_PATH="$(printf '%s\n' "$LOCAL_BACKUP_OUTPUT" | tail -n1)"
if [[ -z "$LOCAL_BACKUP_PATH" || ! -f "$LOCAL_BACKUP_PATH" ]]; then
  echo "Errore: backup locale non valido o non trovato." >&2
  printf '%s\n' "$LOCAL_BACKUP_OUTPUT" >&2
  exit 1
fi
echo "    backup locale: $LOCAL_BACKUP_PATH"
prune_local_backups "$LOCAL_BACKUP_DIR" "gaia-*-pre-pull.dump" "$BACKUP_RETENTION_COUNT"

echo "==> Step 2/7: verifica accesso server e env remoto"
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
  echo "           Le credenziali cifrate importate dal CED potrebbero non funzionare in locale."
  echo "           Dopo il restore potrebbe servire reinserire le credenziali Bonifica/SISTER."
fi

REMOTE_DUMP_NAME=""
if [[ "$SKIP_REMOTE_EXPORT" != "yes" ]]; then
  echo "==> Step 3/7: export database remoto"
  REMOTE_DUMP_NAME="$(
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
backup_path="$REMOTE_BACKUP_DIR/gaia-${timestamp}-ced-pull-source.dump"
container_dump_path="/tmp/gaia-ced-pull-source-${timestamp}.dump"

COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" exec -T postgres pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -Fc \
  --no-owner \
  --no-privileges \
  -f "$container_dump_path"

docker cp "$postgres_container:$container_dump_path" "$backup_path"
COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" exec -T postgres rm -f "$container_dump_path"
prune_remote_backups "$REMOTE_BACKUP_DIR" "gaia-*-ced-pull-source.dump" "$BACKUP_RETENTION_COUNT"

printf '%s' "$backup_path"
REMOTE_BACKUP
  )"
  REMOTE_DUMP_PATH="$REMOTE_DUMP_NAME"
  echo "    dump remoto: $CED_SSH_HOST:$CED_PROJECT_DIR/$REMOTE_DUMP_NAME"
else
  if [[ -z "$REMOTE_DUMP_PATH" ]]; then
    echo "Errore: con SKIP_REMOTE_EXPORT=yes devi impostare REMOTE_DUMP_PATH." >&2
    exit 1
  fi
  echo "==> Step 3/7: export remoto saltato, uso dump esistente $REMOTE_DUMP_PATH"
fi

echo "==> Step 4/7: trasferimento dump remoto in locale"
mkdir -p "$LOCAL_BACKUP_DIR"
remote_dump_basename="$(basename "$REMOTE_DUMP_PATH")"
TRANSFER_DUMP_PATH="$LOCAL_BACKUP_DIR/$remote_dump_basename"
scp $SSH_OPTS "$CED_SSH_HOST:$CED_PROJECT_DIR/$REMOTE_DUMP_PATH" "$TRANSFER_DUMP_PATH"
if [[ ! -f "$TRANSFER_DUMP_PATH" ]]; then
  echo "Errore: dump trasferito non trovato in locale: $TRANSFER_DUMP_PATH" >&2
  exit 1
fi
echo "    dump scaricato: $TRANSFER_DUMP_PATH"
prune_local_backups "$LOCAL_BACKUP_DIR" "gaia-*-ced-pull-source.dump" "$BACKUP_RETENTION_COUNT"

echo "==> Step 5/7: stop servizi locali che usano il database"
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
COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" stop "${services_to_stop[@]}" || true

echo "==> Step 6/7: restore database locale"
LOCAL_POSTGRES_DB="$(read_env_value "$LOCAL_ENV_FILE" "POSTGRES_DB" || true)"
LOCAL_POSTGRES_USER="$(read_env_value "$LOCAL_ENV_FILE" "POSTGRES_USER" || true)"
LOCAL_POSTGRES_DB="${LOCAL_POSTGRES_DB:-gaia}"
LOCAL_POSTGRES_USER="${LOCAL_POSTGRES_USER:-gaia_app}"

if ! COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" ps --status running --services 2>/dev/null | grep -qx "postgres"; then
  echo "Errore: postgres locale non in esecuzione. Avvia lo stack prima del pull." >&2
  exit 1
fi

local_postgres_container="$(COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" ps -q postgres)"
if [[ -z "$local_postgres_container" ]]; then
  echo "Errore: impossibile risolvere il container postgres locale." >&2
  exit 1
fi

container_restore_path="/tmp/gaia-restore-from-ced.dump"
docker cp "$TRANSFER_DUMP_PATH" "$local_postgres_container:$container_restore_path"

if [[ "$LOCAL_RECREATE_DB" == "yes" ]]; then
  echo "==> Recreate local database $LOCAL_POSTGRES_DB"
  COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" exec -T postgres \
    psql \
    -U "$LOCAL_POSTGRES_USER" \
    -d postgres \
    -v ON_ERROR_STOP=1 \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$LOCAL_POSTGRES_DB' AND pid <> pg_backend_pid();"
  COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" exec -T postgres \
    dropdb \
    -U "$LOCAL_POSTGRES_USER" \
    --if-exists \
    "$LOCAL_POSTGRES_DB"
  COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" exec -T postgres \
    createdb \
    -U "$LOCAL_POSTGRES_USER" \
    "$LOCAL_POSTGRES_DB"
fi

COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" exec -T postgres \
  pg_restore \
  -U "$LOCAL_POSTGRES_USER" \
  -d "$LOCAL_POSTGRES_DB" \
  --no-owner \
  --no-privileges \
  --exit-on-error \
  "$container_restore_path"
COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" exec -T postgres rm -f "$container_restore_path"

echo "==> Riavvio servizi locali"
COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" up -d --no-build --remove-orphans "${services_to_start[@]}"

if [[ "$RUN_SMOKE_TEST" == "yes" ]]; then
  echo "==> Step 7/7: smoke test locale"
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
  wait_for_http "http://127.0.0.1:${LOCAL_NGINX_PORT}/api/health" "nginx /api/health"
  wait_for_http "http://127.0.0.1:${LOCAL_NGINX_PORT}/login" "nginx /login"
else
  echo "==> Step 7/7: smoke test locale saltato"
fi

cat <<EOF

==> Pull database completato

Backup locale pre-restore:
  $LOCAL_BACKUP_PATH

Dump remoto sorgente:
  $CED_SSH_HOST:$CED_PROJECT_DIR/$REMOTE_DUMP_PATH

Dump scaricato e applicato in locale:
  $TRANSFER_DUMP_PATH

Verifica manuale consigliata:
  - login su GAIA locale
  - pagine con dati operativi recenti
  - eventuale test credenziali cifrate se CREDENTIAL_MASTER_KEY differisce

EOF
