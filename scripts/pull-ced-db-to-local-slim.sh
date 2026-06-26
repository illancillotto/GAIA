#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/pull-ced-db-to-local-slim.sh

Sincronizza dal server CED al database locale solo un set di tabelle operative
e solo se risultano cambiate rispetto al locale.

Variabili:
  CED_SSH_HOST=serverCed              Alias/host SSH del server CED
  CED_PROJECT_DIR=/opt/gaia           Directory progetto sul server
  LOCAL_ENV_FILE=.env                 Env locale (destinazione restore)
  REMOTE_ENV_FILE=.env                Env remoto (sorgente dump)
  LOCAL_BACKUP_DIR=./backups/db       Directory backup locale
  REMOTE_BACKUP_DIR=backups/db        Directory dump remota (relativa a CED_PROJECT_DIR)
  COMPOSE_PROJECT_NAME=gaia           Nome progetto compose
  SSH_OPTS=""                         Opzioni extra ssh/scp
  CONFIRM_PULL=yes                    Obbligatorio per eseguire la sync locale
  RUN_SMOKE_TEST=yes                  yes per verificare backend/frontend locali dopo il restore
  LOCAL_NGINX_PORT=8080               Porta nginx locale per smoke test opzionale
  BACKUP_RETENTION_COUNT=2            Numero backup locali/remoti da mantenere per pattern
  SIGNATURE_ROW_HASH_LIMIT=20000      Soglia righe per hash completo nelle tabelle senza timestamp
  SYNC_TABLES_CSV=                    Elenco tabelle schema.nome separato da virgole

Default slim:
  - utenti, permessi, inviti
  - credenziali/config operative
  - job/run/eventi di orchestrazione
  - selezioni e metadati leggeri
  - esclusi di default i dataset bulk e i log firewall voluminosi

Flusso:
  1. backup preventivo locale completo
  2. confronto firme tabella per tabella tra CED e locale
  3. export remoto solo delle tabelle cambiate
  4. stop servizi locali che usano il DB
  5. truncate/restore locale solo delle tabelle cambiate
  6. riavvio servizi + smoke test opzionale

Attenzione:
  - operazione distruttiva sulle sole tabelle sincronizzate in locale
  - il restore usa TRUNCATE ... CASCADE sulle tabelle cambiate
  - per cambiare il perimetro usa SYNC_TABLES_CSV

Esempi:
  CONFIRM_PULL=yes ./scripts/pull-ced-db-to-local-slim.sh
  SYNC_TABLES_CSV=public.application_users,public.user_section_permissions CONFIRM_PULL=yes ./scripts/pull-ced-db-to-local-slim.sh
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

default_sync_tables=(
  public.application_users
  public.sections
  public.role_section_permissions
  public.user_section_permissions
  public.effective_permissions
  public.permission_entries
  public.operator_invitation
  public.bonifica_oristanese_credentials
  public.capacitas_credentials
  public.catasto_credentials
  public.presenze_credentials
  public.elaborazione_auto_job_configs
  public.sync_jobs
  public.sync_runs
  public.wc_sync_job
  public.capacitas_terreni_sync_jobs
  public.capacitas_particelle_sync_jobs
  public.capacitas_anagrafica_history_import_jobs
  public.capacitas_incass_sync_jobs
  public.cat_import_batches
  public.cat_ade_sync_runs
  public.cat_gis_saved_selections
  public.cat_gis_saved_selection_items
  public.catasto_elaborazioni_massive_jobs
  public.catasto_ruolo_autosync_config
  public.presenze_import_jobs
  public.presenze_sync_jobs
  public.presenze_auto_sync_config
  public.ruolo_import_jobs
  public.ana_import_jobs
  public.ana_import_job_items
  public.ana_xlsx_import_batches
  public.anpr_sync_config
  public.anpr_job_runs
  public.wiki_conversation_governance_config
  public.wiki_conversation_metrics_backfill_jobs
  public.wiki_telemetry_daily_metrics
  public.wiki_telemetry_period_metrics
  public.wiki_conversation_daily_metrics
  public.network_detection_watchlist
  public.network_sophos_config
)

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
RUN_SMOKE_TEST="${RUN_SMOKE_TEST:-yes}"
LOCAL_NGINX_PORT="${LOCAL_NGINX_PORT:-8080}"
BACKUP_RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-2}"
SIGNATURE_ROW_HASH_LIMIT="${SIGNATURE_ROW_HASH_LIMIT:-20000}"
SYNC_TABLES_CSV="${SYNC_TABLES_CSV:-}"

require_cmd ssh
require_cmd scp
require_cmd find
require_cmd docker
require_cmd mktemp

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
cd "$ROOT_DIR"

if [[ "$CONFIRM_PULL" != "yes" ]]; then
  echo "Errore: operazione distruttiva. Imposta CONFIRM_PULL=yes per procedere." >&2
  exit 1
fi

if [[ ! -f "$LOCAL_ENV_FILE" ]]; then
  echo "Errore: file env locale non trovato: $LOCAL_ENV_FILE" >&2
  exit 1
fi

sync_tables=()
if [[ -n "$SYNC_TABLES_CSV" ]]; then
  IFS=',' read -r -a sync_tables <<< "$SYNC_TABLES_CSV"
else
  sync_tables=("${default_sync_tables[@]}")
fi

if [[ "${#sync_tables[@]}" -eq 0 ]]; then
  echo "Errore: nessuna tabella configurata per la sync slim." >&2
  exit 1
fi

echo "==> Step 1/6: backup preventivo locale completo"
LOCAL_BACKUP_OUTPUT="$(
  BACKUP_DIR="$LOCAL_BACKUP_DIR" \
    "$ROOT_DIR/scripts/backup-gaia-db.sh" \
    --env-file "$LOCAL_ENV_FILE" \
    --label pre-pull-slim
)"
LOCAL_BACKUP_PATH="$(printf '%s\n' "$LOCAL_BACKUP_OUTPUT" | tail -n1)"
if [[ -z "$LOCAL_BACKUP_PATH" || ! -f "$LOCAL_BACKUP_PATH" ]]; then
  echo "Errore: backup locale non valido o non trovato." >&2
  printf '%s\n' "$LOCAL_BACKUP_OUTPUT" >&2
  exit 1
fi
echo "    backup locale: $LOCAL_BACKUP_PATH"
prune_local_backups "$LOCAL_BACKUP_DIR" "gaia-*-pre-pull-slim.dump" "$BACKUP_RETENTION_COUNT"

collect_signatures_script="$TMP_DIR/collect_signatures.sh"
cat > "$collect_signatures_script" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail

ENV_FILE="$1"
COMPOSE_PROJECT_NAME="$2"
ROW_HASH_LIMIT="$3"
TABLES_CSV="$4"

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

psql_query() {
  local sql="$1"
  COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$ENV_FILE" exec -T postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atq -v ON_ERROR_STOP=1 -c "$sql"
}

POSTGRES_DB="$(read_env_value "$ENV_FILE" "POSTGRES_DB" || true)"
POSTGRES_USER="$(read_env_value "$ENV_FILE" "POSTGRES_USER" || true)"
POSTGRES_DB="${POSTGRES_DB:-gaia}"
POSTGRES_USER="${POSTGRES_USER:-gaia_app}"

IFS=',' read -r -a TABLES <<< "$TABLES_CSV"
for table_ref in "${TABLES[@]}"; do
  table_ref="$(printf '%s' "$table_ref" | xargs)"
  [[ -z "$table_ref" ]] && continue
  schema_name="${table_ref%%.*}"
  table_name="${table_ref#*.}"

  exists="$(psql_query "SELECT CASE WHEN to_regclass('${schema_name}.${table_name}') IS NULL THEN '0' ELSE '1' END;")"
  if [[ "$exists" != "1" ]]; then
    printf '%s|missing\n' "$table_ref"
    continue
  fi

  tracked_column="$(psql_query "
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = '${schema_name}'
      AND table_name = '${table_name}'
      AND column_name IN ('updated_at','modified_at','last_modified_at','completed_at','started_at','created_at')
    ORDER BY CASE column_name
      WHEN 'updated_at' THEN 1
      WHEN 'modified_at' THEN 2
      WHEN 'last_modified_at' THEN 3
      WHEN 'completed_at' THEN 4
      WHEN 'started_at' THEN 5
      WHEN 'created_at' THEN 6
      ELSE 99
    END
    LIMIT 1;
  ")"

  row_count="$(psql_query "SELECT count(*)::bigint FROM ${schema_name}.${table_name};")"
  table_size="$(psql_query "SELECT pg_total_relation_size('${schema_name}.${table_name}'::regclass)::bigint;")"

  if [[ -n "$tracked_column" ]]; then
    max_value="$(psql_query "SELECT COALESCE(max(${tracked_column})::text, '') FROM ${schema_name}.${table_name};")"
    printf '%s|count=%s|max=%s|size=%s\n' "$table_ref" "$row_count" "$max_value" "$table_size"
    continue
  fi

  if [[ "$row_count" =~ ^[0-9]+$ ]] && (( row_count <= ROW_HASH_LIMIT )); then
    row_hash="$(psql_query "
      SELECT md5(COALESCE(string_agg(md5(row_to_json(t)::text), ',' ORDER BY md5(row_to_json(t)::text)), ''));
      FROM ${schema_name}.${table_name} AS t;
    ")"
    printf '%s|count=%s|hash=%s|size=%s\n' "$table_ref" "$row_count" "$row_hash" "$table_size"
    continue
  fi

  printf '%s|count=%s|size=%s\n' "$table_ref" "$row_count" "$table_size"
done
EOF
chmod +x "$collect_signatures_script"

echo "==> Step 2/6: confronto firme tabelle remote/locali"
tables_serialized="$(IFS=,; printf '%s' "${sync_tables[*]}")"

REMOTE_SIGNATURES_FILE="$TMP_DIR/remote-signatures.txt"
LOCAL_SIGNATURES_FILE="$TMP_DIR/local-signatures.txt"

ssh $SSH_OPTS "$CED_SSH_HOST" \
  "CED_PROJECT_DIR='$CED_PROJECT_DIR' REMOTE_ENV_FILE='$REMOTE_ENV_FILE' COMPOSE_PROJECT_NAME='$COMPOSE_PROJECT_NAME' SIGNATURE_ROW_HASH_LIMIT='$SIGNATURE_ROW_HASH_LIMIT' TABLES_SERIALIZED='$tables_serialized' bash -s" <<'REMOTE_SIG' > "$REMOTE_SIGNATURES_FILE"
set -Eeuo pipefail
cd "$CED_PROJECT_DIR"

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

psql_query() {
  local sql="$1"
  COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" exec -T postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atq -v ON_ERROR_STOP=1 -c "$sql"
}

POSTGRES_DB="$(read_env_value "$REMOTE_ENV_FILE" "POSTGRES_DB" || true)"
POSTGRES_USER="$(read_env_value "$REMOTE_ENV_FILE" "POSTGRES_USER" || true)"
POSTGRES_DB="${POSTGRES_DB:-gaia}"
POSTGRES_USER="${POSTGRES_USER:-gaia_app}"

IFS=',' read -r -a TABLES <<< "$TABLES_SERIALIZED"
for table_ref in "${TABLES[@]}"; do
  table_ref="$(printf '%s' "$table_ref" | xargs)"
  [[ -z "$table_ref" ]] && continue
  schema_name="${table_ref%%.*}"
  table_name="${table_ref#*.}"

  exists="$(psql_query "SELECT CASE WHEN to_regclass('${schema_name}.${table_name}') IS NULL THEN '0' ELSE '1' END;")"
  if [[ "$exists" != "1" ]]; then
    printf '%s|missing\n' "$table_ref"
    continue
  fi

  tracked_column="$(psql_query "
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = '${schema_name}'
      AND table_name = '${table_name}'
      AND column_name IN ('updated_at','modified_at','last_modified_at','completed_at','started_at','created_at')
    ORDER BY CASE column_name
      WHEN 'updated_at' THEN 1
      WHEN 'modified_at' THEN 2
      WHEN 'last_modified_at' THEN 3
      WHEN 'completed_at' THEN 4
      WHEN 'started_at' THEN 5
      WHEN 'created_at' THEN 6
      ELSE 99
    END
    LIMIT 1;
  ")"

  row_count="$(psql_query "SELECT count(*)::bigint FROM ${schema_name}.${table_name};")"
  table_size="$(psql_query "SELECT pg_total_relation_size('${schema_name}.${table_name}'::regclass)::bigint;")"

  if [[ -n "$tracked_column" ]]; then
    max_value="$(psql_query "SELECT COALESCE(max(${tracked_column})::text, '') FROM ${schema_name}.${table_name};")"
    printf '%s|count=%s|max=%s|size=%s\n' "$table_ref" "$row_count" "$max_value" "$table_size"
    continue
  fi

  if [[ "$row_count" =~ ^[0-9]+$ ]] && (( row_count <= SIGNATURE_ROW_HASH_LIMIT )); then
    row_hash="$(psql_query "
      SELECT md5(COALESCE(string_agg(md5(row_to_json(t)::text), ',' ORDER BY md5(row_to_json(t)::text)), ''))
      FROM ${schema_name}.${table_name} AS t;
    ")"
    printf '%s|count=%s|hash=%s|size=%s\n' "$table_ref" "$row_count" "$row_hash" "$table_size"
    continue
  fi

  printf '%s|count=%s|size=%s\n' "$table_ref" "$row_count" "$table_size"
done
REMOTE_SIG

"$collect_signatures_script" "$LOCAL_ENV_FILE" "$COMPOSE_PROJECT_NAME" "$SIGNATURE_ROW_HASH_LIMIT" "$tables_serialized" > "$LOCAL_SIGNATURES_FILE"

declare -A remote_signatures=()
declare -A local_signatures=()
while IFS='|' read -r table_ref rest; do
  [[ -z "$table_ref" ]] && continue
  remote_signatures["$table_ref"]="$rest"
done < "$REMOTE_SIGNATURES_FILE"

while IFS='|' read -r table_ref rest; do
  [[ -z "$table_ref" ]] && continue
  local_signatures["$table_ref"]="$rest"
done < "$LOCAL_SIGNATURES_FILE"

changed_tables=()
for table_ref in "${sync_tables[@]}"; do
  remote_sig="${remote_signatures[$table_ref]:-missing}"
  local_sig="${local_signatures[$table_ref]:-missing}"

  if [[ "$remote_sig" == "missing" ]]; then
    echo "    remoto assente, skip: $table_ref"
    continue
  fi

  if [[ "$remote_sig" != "$local_sig" ]]; then
    changed_tables+=("$table_ref")
  fi
done

if [[ "${#changed_tables[@]}" -eq 0 ]]; then
  echo "==> Nessuna tabella slim cambiata tra CED e locale"
  cat <<EOF

==> Sync slim completata

Backup locale pre-check:
  $LOCAL_BACKUP_PATH

Nessun restore necessario.

EOF
  exit 0
fi

printf '    tabelle da sincronizzare (%s):\n' "${#changed_tables[@]}"
for table_ref in "${changed_tables[@]}"; do
  printf '      - %s\n' "$table_ref"
done

echo "==> Step 3/6: export remoto solo delle tabelle cambiate"
changed_tables_serialized="$(IFS=,; printf '%s' "${changed_tables[*]}")"
REMOTE_DUMP_NAME="$(
  ssh $SSH_OPTS "$CED_SSH_HOST" \
    "CED_PROJECT_DIR='$CED_PROJECT_DIR' REMOTE_ENV_FILE='$REMOTE_ENV_FILE' REMOTE_BACKUP_DIR='$REMOTE_BACKUP_DIR' COMPOSE_PROJECT_NAME='$COMPOSE_PROJECT_NAME' BACKUP_RETENTION_COUNT='$BACKUP_RETENTION_COUNT' CHANGED_TABLES_SERIALIZED='$changed_tables_serialized' bash -s" <<'REMOTE_DUMP'
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

postgres_container="$(COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" ps -q postgres)"
mkdir -p "$REMOTE_BACKUP_DIR"
timestamp="$(date +%Y%m%d-%H%M%S)"
backup_path="$REMOTE_BACKUP_DIR/gaia-${timestamp}-ced-pull-slim.dump"
container_dump_path="/tmp/gaia-ced-pull-slim-${timestamp}.dump"

pg_dump_args=(
  -U "$POSTGRES_USER"
  -d "$POSTGRES_DB"
  -Fc
  --data-only
  --no-owner
  --no-privileges
)

IFS=',' read -r -a TABLES <<< "$CHANGED_TABLES_SERIALIZED"
for table_ref in "${TABLES[@]}"; do
  table_ref="$(printf '%s' "$table_ref" | xargs)"
  [[ -z "$table_ref" ]] && continue
  pg_dump_args+=(-t "$table_ref")
done

COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" exec -T postgres \
  pg_dump "${pg_dump_args[@]}" -f "$container_dump_path"

docker cp "$postgres_container:$container_dump_path" "$backup_path"
COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$REMOTE_ENV_FILE" exec -T postgres rm -f "$container_dump_path"
prune_remote_backups "$REMOTE_BACKUP_DIR" "gaia-*-ced-pull-slim.dump" "$BACKUP_RETENTION_COUNT"

printf '%s' "$backup_path"
REMOTE_DUMP
)"
echo "    dump remoto slim: $CED_SSH_HOST:$CED_PROJECT_DIR/$REMOTE_DUMP_NAME"

echo "==> Step 4/6: trasferimento dump slim in locale"
mkdir -p "$LOCAL_BACKUP_DIR"
TRANSFER_DUMP_PATH="$LOCAL_BACKUP_DIR/$(basename "$REMOTE_DUMP_NAME")"
scp $SSH_OPTS "$CED_SSH_HOST:$CED_PROJECT_DIR/$REMOTE_DUMP_NAME" "$TRANSFER_DUMP_PATH"
if [[ ! -f "$TRANSFER_DUMP_PATH" ]]; then
  echo "Errore: dump slim trasferito non trovato in locale: $TRANSFER_DUMP_PATH" >&2
  exit 1
fi
echo "    dump slim scaricato: $TRANSFER_DUMP_PATH"
prune_local_backups "$LOCAL_BACKUP_DIR" "gaia-*-ced-pull-slim.dump" "$BACKUP_RETENTION_COUNT"

echo "==> Step 5/6: restore locale mirato"
LOCAL_POSTGRES_DB="$(read_env_value "$LOCAL_ENV_FILE" "POSTGRES_DB" || true)"
LOCAL_POSTGRES_USER="$(read_env_value "$LOCAL_ENV_FILE" "POSTGRES_USER" || true)"
LOCAL_POSTGRES_DB="${LOCAL_POSTGRES_DB:-gaia}"
LOCAL_POSTGRES_USER="${LOCAL_POSTGRES_USER:-gaia_app}"

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

if ! COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" ps --status running --services 2>/dev/null | grep -qx "postgres"; then
  echo "Errore: postgres locale non in esecuzione. Avvia lo stack prima della sync slim." >&2
  exit 1
fi

local_postgres_container="$(COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" ps -q postgres)"
if [[ -z "$local_postgres_container" ]]; then
  echo "Errore: impossibile risolvere il container postgres locale." >&2
  exit 1
fi

container_restore_path="/tmp/gaia-restore-from-ced-slim.dump"
docker cp "$TRANSFER_DUMP_PATH" "$local_postgres_container:$container_restore_path"

truncate_sql="TRUNCATE TABLE "
for i in "${!changed_tables[@]}"; do
  if (( i > 0 )); then
    truncate_sql+=", "
  fi
  truncate_sql+="${changed_tables[$i]}"
done
truncate_sql+=" RESTART IDENTITY CASCADE;"

COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" exec -T postgres \
  psql \
  -U "$LOCAL_POSTGRES_USER" \
  -d "$LOCAL_POSTGRES_DB" \
  -v ON_ERROR_STOP=1 \
  -c "$truncate_sql"

COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" exec -T postgres \
  pg_restore \
  -U "$LOCAL_POSTGRES_USER" \
  -d "$LOCAL_POSTGRES_DB" \
  --data-only \
  --disable-triggers \
  --no-owner \
  --no-privileges \
  --exit-on-error \
  "$container_restore_path"
COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" exec -T postgres rm -f "$container_restore_path"

echo "==> Riavvio servizi locali"
COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$LOCAL_ENV_FILE" up -d --no-build --remove-orphans "${services_to_start[@]}"

if [[ "$RUN_SMOKE_TEST" == "yes" ]]; then
  echo "==> Step 6/6: smoke test locale"
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
  echo "==> Step 6/6: smoke test locale saltato"
fi

cat <<EOF

==> Sync slim completata

Backup locale pre-restore:
  $LOCAL_BACKUP_PATH

Dump remoto slim:
  $CED_SSH_HOST:$CED_PROJECT_DIR/$REMOTE_DUMP_NAME

Dump slim applicato in locale:
  $TRANSFER_DUMP_PATH

Tabelle sincronizzate:
$(printf '  - %s\n' "${changed_tables[@]}")

EOF
