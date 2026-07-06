#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/run-capacitas-grid-server.sh

Variabili richieste:
  XLSX_PATH=/path/to/ct0902026_grid.xlsx

Variabili opzionali:
  PROJECT_DIR=$(pwd)                               Root repo GAIA sul server
  BACKEND_SERVICE=backend                          Nome servizio docker compose backend
  SNAPSHOT_YEAR=2026                               Anno snapshot
  SOURCE_FILE=<basename XLSX_PATH>                 Nome file sorgente da salvare nel summary
  OUTPUT_DIR=/tmp/gaia_capacitas_grid_import_server
  IDEMPOTENCY_OUTPUT_DIR=/tmp/gaia_capacitas_grid_import_server_idempotency
  RUN_TESTS=yes                                    yes|no
  RUN_MIGRATION_CHECK=yes                          yes|no
  RUN_GRAPHIFY=no                                  yes|no
  GRAPHIFY_DOCS=no                                 yes|no
  BACKUP_DONE=no                                   yes|no, deve essere yes per consentire --apply
  SKIP_APPLY=no                                    yes|no, utile per fermarsi al dry-run

Lo script:
  - verifica migration/test minimi
  - controlla che non ci siano import attivi
  - esegue dry-run
  - se BACKUP_DONE=yes e SKIP_APPLY=no, esegue apply + secondo apply
  - valida automaticamente:
    * cat_particelle_unchanged=True
    * occupancy_created=0 al secondo apply
    * raw_rows_inserted=0 al secondo apply
    * unit_action_unit_created=0 al secondo apply

Nota:
  - non esegue backup DB: richiede conferma esplicita BACKUP_DONE=yes
  - non esegue il reparse massivo inCass
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Errore: comando richiesto non trovato: $1" >&2
    exit 1
  fi
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

XLSX_PATH="${XLSX_PATH:-}"
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
BACKEND_SERVICE="${BACKEND_SERVICE:-backend}"
SNAPSHOT_YEAR="${SNAPSHOT_YEAR:-2026}"
SOURCE_FILE="${SOURCE_FILE:-}"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/gaia_capacitas_grid_import_server}"
IDEMPOTENCY_OUTPUT_DIR="${IDEMPOTENCY_OUTPUT_DIR:-/tmp/gaia_capacitas_grid_import_server_idempotency}"
RUN_TESTS="${RUN_TESTS:-yes}"
RUN_MIGRATION_CHECK="${RUN_MIGRATION_CHECK:-yes}"
RUN_GRAPHIFY="${RUN_GRAPHIFY:-no}"
GRAPHIFY_DOCS="${GRAPHIFY_DOCS:-no}"
BACKUP_DONE="${BACKUP_DONE:-no}"
SKIP_APPLY="${SKIP_APPLY:-no}"

if [[ -z "$XLSX_PATH" ]]; then
  echo "Errore: XLSX_PATH e obbligatorio." >&2
  usage
  exit 1
fi

if [[ ! -f "$XLSX_PATH" ]]; then
  echo "Errore: file Excel non trovato: $XLSX_PATH" >&2
  exit 1
fi

if [[ "$RUN_TESTS" != "yes" && "$RUN_TESTS" != "no" ]]; then
  echo "Errore: RUN_TESTS deve essere yes o no." >&2
  exit 1
fi

if [[ "$RUN_MIGRATION_CHECK" != "yes" && "$RUN_MIGRATION_CHECK" != "no" ]]; then
  echo "Errore: RUN_MIGRATION_CHECK deve essere yes o no." >&2
  exit 1
fi

if [[ "$RUN_GRAPHIFY" != "yes" && "$RUN_GRAPHIFY" != "no" ]]; then
  echo "Errore: RUN_GRAPHIFY deve essere yes o no." >&2
  exit 1
fi

if [[ "$GRAPHIFY_DOCS" != "yes" && "$GRAPHIFY_DOCS" != "no" ]]; then
  echo "Errore: GRAPHIFY_DOCS deve essere yes o no." >&2
  exit 1
fi

if [[ "$BACKUP_DONE" != "yes" && "$BACKUP_DONE" != "no" ]]; then
  echo "Errore: BACKUP_DONE deve essere yes o no." >&2
  exit 1
fi

if [[ "$SKIP_APPLY" != "yes" && "$SKIP_APPLY" != "no" ]]; then
  echo "Errore: SKIP_APPLY deve essere yes o no." >&2
  exit 1
fi

require_cmd docker

if ! docker compose version >/dev/null 2>&1; then
  echo "Errore: docker compose v2 non disponibile." >&2
  exit 1
fi

PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
SOURCE_FILE="${SOURCE_FILE:-$(basename "$XLSX_PATH")}"

run_backend() {
  (cd "$PROJECT_DIR" && docker compose exec -T "$BACKEND_SERVICE" "$@")
}

validate_summary() {
  local summary_path="$1"
  local mode="$2"
  local expect_zero_create="$3"
  run_backend python - <<'PY' "$summary_path" "$mode" "$expect_zero_create"
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
mode = sys.argv[2]
expect_zero_create = sys.argv[3] == "yes"

summary = json.loads(summary_path.read_text())
counters = summary["counters"]

if summary["mode"] != mode:
    raise SystemExit(f"summary mode inatteso: {summary['mode']} != {mode}")
if summary["cat_particelle_unchanged"] is not True:
    raise SystemExit("cat_particelle_unchanged non e True")

if expect_zero_create:
    if counters.get("occupancy_created", 0) != 0:
        raise SystemExit(f"occupancy_created atteso 0, trovato {counters.get('occupancy_created', 0)}")
    if counters.get("raw_rows_inserted", 0) != 0:
        raise SystemExit(f"raw_rows_inserted atteso 0, trovato {counters.get('raw_rows_inserted', 0)}")
    if counters.get("unit_action_unit_created", 0) != 0:
        raise SystemExit(
            f"unit_action_unit_created atteso 0, trovato {counters.get('unit_action_unit_created', 0)}"
        )

print("summary_ok", summary_path)
print("mode", summary["mode"])
print("cat_particelle_unchanged", summary["cat_particelle_unchanged"])
print("occupancy_created", counters.get("occupancy_created", 0))
print("raw_rows_inserted", counters.get("raw_rows_inserted", 0))
print("unit_action_unit_created", counters.get("unit_action_unit_created", 0))
PY
}

echo "==> Project dir: $PROJECT_DIR"
echo "==> File Excel: $XLSX_PATH"
echo "==> Snapshot year: $SNAPSHOT_YEAR"
echo "==> Output dir dry/apply: $OUTPUT_DIR"
echo "==> Output dir idempotenza: $IDEMPOTENCY_OUTPUT_DIR"

if [[ "$RUN_MIGRATION_CHECK" == "yes" ]]; then
  echo "==> Verifica migration Alembic"
  run_backend alembic current
  run_backend alembic heads
fi

if [[ "$RUN_TESTS" == "yes" ]]; then
  echo "==> Eseguo test minimi"
  run_backend python -m pytest tests/test_capacitas_consorzio_grid_import.py -q
  run_backend python -m pytest tests/test_incass_parsers.py tests/elaborazioni/capacitas/test_incass_partitario_parsing.py -q
fi

echo "==> Verifico processi import attivi"
if run_backend pgrep -af import_capacitas_consorzio_grid.py; then
  echo "Errore: esistono processi import attivi. Fermarsi prima di proseguire." >&2
  exit 1
fi

echo "==> Dry-run import"
run_backend python scripts/import_capacitas_consorzio_grid.py \
  --xlsx-path "$XLSX_PATH" \
  --snapshot-year "$SNAPSHOT_YEAR" \
  --source-file "$SOURCE_FILE" \
  --output-dir "$OUTPUT_DIR" \
  --dry-run

DRY_SUMMARY_PATH="$OUTPUT_DIR/capacitas_grid_${SNAPSHOT_YEAR}_dry-run_summary.json"
echo "==> Valido summary dry-run: $DRY_SUMMARY_PATH"
validate_summary "$DRY_SUMMARY_PATH" "dry-run" "no"

if [[ "$SKIP_APPLY" == "yes" ]]; then
  echo "==> SKIP_APPLY=yes: mi fermo dopo il dry-run."
  exit 0
fi

if [[ "$BACKUP_DONE" != "yes" ]]; then
  echo "Errore: BACKUP_DONE deve essere yes prima di qualsiasi --apply." >&2
  exit 1
fi

echo "==> Apply import"
run_backend python scripts/import_capacitas_consorzio_grid.py \
  --xlsx-path "$XLSX_PATH" \
  --snapshot-year "$SNAPSHOT_YEAR" \
  --source-file "$SOURCE_FILE" \
  --output-dir "$OUTPUT_DIR" \
  --apply

APPLY_SUMMARY_PATH="$OUTPUT_DIR/capacitas_grid_${SNAPSHOT_YEAR}_apply_summary.json"
echo "==> Valido summary apply: $APPLY_SUMMARY_PATH"
validate_summary "$APPLY_SUMMARY_PATH" "apply" "no"

echo "==> Secondo apply per idempotenza"
run_backend python scripts/import_capacitas_consorzio_grid.py \
  --xlsx-path "$XLSX_PATH" \
  --snapshot-year "$SNAPSHOT_YEAR" \
  --source-file "$SOURCE_FILE" \
  --output-dir "$IDEMPOTENCY_OUTPUT_DIR" \
  --apply

IDEMPOTENCY_SUMMARY_PATH="$IDEMPOTENCY_OUTPUT_DIR/capacitas_grid_${SNAPSHOT_YEAR}_apply_summary.json"
echo "==> Valido summary idempotenza: $IDEMPOTENCY_SUMMARY_PATH"
validate_summary "$IDEMPOTENCY_SUMMARY_PATH" "apply" "yes"

if [[ "$RUN_GRAPHIFY" == "yes" ]]; then
  echo "==> Aggiorno Graphify codice catasto"
  (cd "$PROJECT_DIR" && make graphify-catasto-code)
  if [[ "$GRAPHIFY_DOCS" == "yes" ]]; then
    echo "==> Tento Graphify docs catasto"
    (cd "$PROJECT_DIR" && make graphify-patch-openai-base-url && make graphify-catasto-docs) || {
      echo "Attenzione: graphify-catasto-docs fallito o bloccato; deploy non bloccato." >&2
    }
  fi
fi

echo "==> Validazione completata"
echo "cat_particelle_unchanged=True"
echo "occupancy_created=0 al secondo apply"
echo "raw_rows_inserted=0 al secondo apply"
