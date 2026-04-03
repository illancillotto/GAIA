#!/usr/bin/env bash
set -euo pipefail

export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"

echo "==> Verifica file staged..."
STAGED_FILES="$(git diff --cached --name-only --diff-filter=ACMR)"

if [ -z "$STAGED_FILES" ]; then
  echo "Nessun file staged. Esco."
  exit 0
fi

echo "==> File staged:"
echo "$STAGED_FILES"

# Evita loop se il commit tocca solo documentazione
ONLY_DOCS="true"
while IFS= read -r file; do
  case "$file" in
    *.md|domain-docs/*/docs/*|DOCS_STRUCTURE.md)
      ;;
    *)
      ONLY_DOCS="false"
      break
      ;;
  esac
done <<< "$STAGED_FILES"

if [ "$ONLY_DOCS" = "true" ]; then
  echo "Commit solo documentazione. Nessun aggiornamento automatico."
  exit 0
fi

# Root docs
ROOT_DOC_FILES=(
  "README.md"
  "ARCHITECTURE.md"
  "PRD.md"
  "IMPLEMENTATION_PLAN.md"
  "DOCS_STRUCTURE.md"
)

# Whitelist docs per dominio
ACCESSI_DOC_FILES=(
  "domain-docs/accessi/docs/PRD.md"
  "domain-docs/accessi/docs/ARCHITECTURE.md"
  "domain-docs/accessi/docs/IMPLEMENTATION_PLAN.md"
  "domain-docs/accessi/docs/EXECUTION_PLAN.md"
  "domain-docs/accessi/docs/DEPLOYMENT.md"
  "domain-docs/accessi/docs/PROGRESS.md"
)

CATASTO_DOC_FILES=(
  "domain-docs/catasto/docs/PRD_catasto.md"
  "domain-docs/catasto/docs/SISTER_debug_runbook.md"
  "domain-docs/elaborazioni/capacitas/docs/CAPACITAS_integration.md"
)

INVENTORY_DOC_FILES=(
  "domain-docs/inventory/docs/PRD_inventory.md"
)

NETWORK_DOC_FILES=(
  "domain-docs/network/docs/PRD_network.md"
)

UTENZE_DOC_FILES=(
  "domain-docs/utenze/docs/PRD_anagrafica.md"
  "domain-docs/utenze/docs/EXECUTION_PLAN.md"
  "domain-docs/utenze/docs/PROGRESS.md"
)

# Crea solo i file root mancanti
for f in "${ROOT_DOC_FILES[@]}"; do
  [ -f "$f" ] || touch "$f"
done

# Flag di routing
NEEDS_ROOT_DOCS="false"
NEEDS_STRUCTURE_DOCS="false"

NEEDS_ACCESSI="false"
NEEDS_CATASTO="false"
NEEDS_INVENTORY="false"
NEEDS_NETWORK="false"
NEEDS_UTENZE="false"

# Routing per file modificato
while IFS= read -r file; do
  [ -z "$file" ] && continue

  case "$file" in
    # infra / config / struttura
    .github/*|scripts/*|nginx/*|docker*|docker-compose*|Makefile|package.json|pnpm-lock.yaml|yarn.lock|backend/requirements*|frontend/package.json)
      NEEDS_ROOT_DOCS="true"
      NEEDS_STRUCTURE_DOCS="true"
      ;;

    # backend/frontend condivisi
    backend/app/core/*|backend/app/db/*|backend/app/api/*|backend/app/models/*|backend/app/repositories/*|backend/app/schemas/*|backend/app/services/*|backend/app/utils/*|backend/app/jobs/*|frontend/src/app/*|frontend/src/components/*|frontend/src/lib/*|frontend/src/hooks/*|frontend/src/services/*|frontend/src/types/*|frontend/src/utils/*)
      NEEDS_ROOT_DOCS="true"
      ;;

    # accessi
    *accessi*|backend/app/modules/accessi/*|frontend/src/features/accessi/*|domain-docs/accessi/*)
      NEEDS_ACCESSI="true"
      ;;

    # catasto
    *catasto*|modules/catasto/*|backend/app/modules/catasto/*|frontend/src/features/catasto/*|domain-docs/catasto/*)
      NEEDS_CATASTO="true"
      ;;

    # inventory
    *inventory*|backend/app/modules/inventory/*|frontend/src/features/inventory/*|domain-docs/inventory/*)
      NEEDS_INVENTORY="true"
      ;;

    # network
    *network*|backend/app/modules/network/*|frontend/src/features/network/*|domain-docs/network/*)
      NEEDS_NETWORK="true"
      ;;

    # utenze / anagrafica
    *utenze*|*anagrafica*|backend/app/modules/utenze/*|backend/app/modules/anagrafica/*|frontend/src/features/utenze/*|frontend/src/features/anagrafica/*|domain-docs/utenze/*)
      NEEDS_UTENZE="true"
      ;;

    # moduli/funzionalità generiche
    modules/*|backend/app/modules/*|frontend/src/features/*)
      NEEDS_ROOT_DOCS="true"
      ;;

    # fallback generale
    backend/*|frontend/*)
      NEEDS_ROOT_DOCS="true"
      ;;
  esac
done <<< "$STAGED_FILES"

# Se cambiano struttura o percorsi, aggiorna anche DOCS_STRUCTURE
while IFS= read -r file; do
  [ -z "$file" ] && continue
  case "$file" in
    .github/*|scripts/*|nginx/*|modules/*|backend/*|frontend/*)
      NEEDS_STRUCTURE_DOCS="true"
      break
      ;;
  esac
done <<< "$STAGED_FILES"

# Diff utile: esclude docs già modificate
DIFF_CONTENT="$(git diff --cached -- . ':(exclude)*.md' ':(exclude)domain-docs/**/docs/*' || true)"

if [ -z "$DIFF_CONTENT" ]; then
  echo "Diff utile vuoto. Esco."
  exit 0
fi

# Costruzione lista file consentiti
ALLOWED_FILES=()

if [ "$NEEDS_ROOT_DOCS" = "true" ]; then
  ALLOWED_FILES+=("README.md" "ARCHITECTURE.md" "PRD.md" "IMPLEMENTATION_PLAN.md")
fi

if [ "$NEEDS_STRUCTURE_DOCS" = "true" ]; then
  ALLOWED_FILES+=("DOCS_STRUCTURE.md")
fi

if [ "$NEEDS_ACCESSI" = "true" ]; then
  ALLOWED_FILES+=("${ACCESSI_DOC_FILES[@]}")
fi

if [ "$NEEDS_CATASTO" = "true" ]; then
  ALLOWED_FILES+=("${CATASTO_DOC_FILES[@]}")
fi

if [ "$NEEDS_INVENTORY" = "true" ]; then
  ALLOWED_FILES+=("${INVENTORY_DOC_FILES[@]}")
fi

if [ "$NEEDS_NETWORK" = "true" ]; then
  ALLOWED_FILES+=("${NETWORK_DOC_FILES[@]}")
fi

if [ "$NEEDS_UTENZE" = "true" ]; then
  ALLOWED_FILES+=("${UTENZE_DOC_FILES[@]}")
fi

# Rimuovi duplicati
mapfile -t ALLOWED_FILES < <(printf "%s\n" "${ALLOWED_FILES[@]}" | awk '!seen[$0]++')

if [ "${#ALLOWED_FILES[@]}" -eq 0 ]; then
  echo "Nessun file documentale consentito individuato. Esco."
  exit 0
fi

PROMPT_FILE="$(mktemp)"

{
  echo "Analizza il diff git staged fornito sotto e aggiorna SOLO i file markdown consentiti elencati più avanti."
  echo
  echo "Regole:"
  echo "- Non riscrivere da zero i documenti se non necessario."
  echo "- Aggiorna solo le sezioni davvero impattate dal diff."
  echo "- Non modificare file fuori dalla whitelist."
  echo "- Non creare nuovi file non presenti nella whitelist."
  echo "- Mantieni stile tecnico, sintetico e coerente con il repository."
  echo "- Se non serve aggiornare un file della whitelist, lascialo invariato."
  echo
  echo "Whitelist dei file aggiornabili in questo commit:"
  for f in "${ALLOWED_FILES[@]}"; do
    echo "- $f"
  done
  echo
  echo "Routing deciso:"
  echo "- ROOT_DOCS=$NEEDS_ROOT_DOCS"
  echo "- STRUCTURE_DOCS=$NEEDS_STRUCTURE_DOCS"
  echo "- ACCESSI=$NEEDS_ACCESSI"
  echo "- CATASTO=$NEEDS_CATASTO"
  echo "- INVENTORY=$NEEDS_INVENTORY"
  echo "- NETWORK=$NEEDS_NETWORK"
  echo "- UTENZE=$NEEDS_UTENZE"
  echo
  echo "Se una modifica è locale a un dominio, concentra l'aggiornamento sui file docs del dominio."
  echo "Se una modifica è trasversale, aggiorna i documenti root consentiti."
  echo "Aggiorna DOCS_STRUCTURE.md solo se percorsi, struttura o organizzazione del repository risultano impattati."
  echo
  echo "Ecco il diff staged:"
  echo
  printf "%s\n" "$DIFF_CONTENT"
} > "$PROMPT_FILE"

echo "==> Routing documentazione:"
echo "ROOT=$NEEDS_ROOT_DOCS STRUCTURE=$NEEDS_STRUCTURE_DOCS ACCESSI=$NEEDS_ACCESSI CATASTO=$NEEDS_CATASTO INVENTORY=$NEEDS_INVENTORY NETWORK=$NEEDS_NETWORK UTENZE=$NEEDS_UTENZE"

echo "==> File consentiti:"
printf ' - %s\n' "${ALLOWED_FILES[@]}"

echo "==> Avvio Codex per aggiornare la documentazione..."
codex exec \
  --skip-git-repo-check \
  --cd "$PROJECT_ROOT" \
  - < "$PROMPT_FILE"

echo "==> Aggiungo allo staging i file documentali consentiti..."
git add -- "${ALLOWED_FILES[@]}" 2>/dev/null || true

rm -f "$PROMPT_FILE"
echo "==> Documentazione aggiornata."
