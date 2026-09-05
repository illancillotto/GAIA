#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/archive-gaia-artifacts.sh [--apply] [--project-dir DIR] [--archive-root DIR]

Migra in modo verificato gli artefatti non piu' recenti dal disco di sistema
all'archivio GAIA. Per ogni file viene eseguito rsync con checksum e poi un
confronto SHA-256: la sorgente viene rimossa soltanto dopo una verifica identica.

Opzioni:
  --apply                 Esegue le copie e le rimozioni. Default: dry-run.
  --project-dir DIR       Root GAIA. Default: /opt/gaia.
  --archive-root DIR      Root archivio montato. Default: /mnt/gaia-archive/gaia.
  --backup-keep-count N   Dump DB completi da mantenere localmente. Default: 1.
  --backup-min-bytes N    Dimensione minima di un dump completo. Default: 1 GiB.
  --release-keep-count N  Artefatti per famiglia da mantenere localmente. Default: 3.
  --gate-mobile-lock FILE Lock usato dal cron Gate Mobile.
                          Default: /tmp/gaia-gate-mobile-sync.lock.
  -h, --help              Mostra questo messaggio.

Esempi:
  ./scripts/archive-gaia-artifacts.sh
  ./scripts/archive-gaia-artifacts.sh --apply

Il mount dell'archivio deve essere disponibile prima dell'esecuzione. Lo script
non esegue prune Docker e non cancella mai file gia' presenti nell'archivio.
EOF
}

PROJECT_DIR="${PROJECT_DIR:-/opt/gaia}"
ARCHIVE_ROOT="${ARCHIVE_ROOT:-/mnt/gaia-archive/gaia}"
BACKUP_KEEP_COUNT="${BACKUP_KEEP_COUNT:-1}"
BACKUP_MIN_BYTES="${BACKUP_MIN_BYTES:-1073741824}"
RELEASE_KEEP_COUNT="${RELEASE_KEEP_COUNT:-3}"
GATE_MOBILE_LOCK_FILE="${GATE_MOBILE_LOCK_FILE:-/tmp/gaia-gate-mobile-sync.lock}"
APPLY=no

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=yes; shift ;;
    --project-dir) PROJECT_DIR="${2:?--project-dir richiede un valore}"; shift 2 ;;
    --archive-root) ARCHIVE_ROOT="${2:?--archive-root richiede un valore}"; shift 2 ;;
    --backup-keep-count) BACKUP_KEEP_COUNT="${2:?--backup-keep-count richiede un valore}"; shift 2 ;;
    --backup-min-bytes) BACKUP_MIN_BYTES="${2:?--backup-min-bytes richiede un valore}"; shift 2 ;;
    --release-keep-count) RELEASE_KEEP_COUNT="${2:?--release-keep-count richiede un valore}"; shift 2 ;;
    --gate-mobile-lock) GATE_MOBILE_LOCK_FILE="${2:?--gate-mobile-lock richiede un valore}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Errore: opzione sconosciuta: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for count in "$BACKUP_KEEP_COUNT" "$RELEASE_KEEP_COUNT" "$BACKUP_MIN_BYTES"; do
  if ! [[ "$count" =~ ^[0-9]+$ ]]; then
    echo "Errore: i valori retention devono essere interi non negativi." >&2
    exit 2
  fi
done

for command in date find findmnt flock gzip mv rsync sha256sum sort; do
  command -v "$command" >/dev/null || { echo "Errore: comando mancante: $command" >&2; exit 1; }
done

archive_probe="$ARCHIVE_ROOT"
while [[ ! -e "$archive_probe" && "$archive_probe" != / ]]; do
  archive_probe="$(dirname "$archive_probe")"
done
archive_source="$(findmnt -no SOURCE -T "$archive_probe" 2>/dev/null || true)"
project_source="$(findmnt -no SOURCE -T "$PROJECT_DIR" 2>/dev/null || true)"
if [[ -z "$archive_source" || "$archive_source" == "$project_source" ]]; then
  echo "Errore: archivio non montato separatamente dalla root progetto: $ARCHIVE_ROOT" >&2
  exit 1
fi

if [[ "$APPLY" == yes ]]; then
  mkdir -p "$ARCHIVE_ROOT/backups/db" "$ARCHIVE_ROOT/logs" "$ARCHIVE_ROOT/releases"
fi
exec 9>"$archive_probe/.archive-gaia-artifacts.lock"
flock -n 9 || { echo "Errore: una migrazione archivi GAIA e' gia' in corso." >&2; exit 1; }

move_verified() {
  local source="$1"
  local destination_dir="$2"
  local destination="$destination_dir/$(basename "$source")"
  local source_hash destination_hash

  if [[ -e "$destination" ]]; then
    if [[ "$APPLY" != yes ]]; then
      echo "DRY-RUN: sorgente gia' verificabile nell'archivio: $source"
      return 0
    fi
    source_hash="$(sha256sum "$source" | awk '{print $1}')"
    destination_hash="$(sha256sum "$destination" | awk '{print $1}')"
    if [[ "$source_hash" != "$destination_hash" ]]; then
      echo "Errore: destinazione esistente diversa, non sovrascrivo: $destination" >&2
      return 1
    fi
  elif [[ "$APPLY" == yes ]]; then
    rsync -a --checksum -- "$source" "$destination_dir/"
    source_hash="$(sha256sum "$source" | awk '{print $1}')"
    destination_hash="$(sha256sum "$destination" | awk '{print $1}')"
    if [[ "$source_hash" != "$destination_hash" ]]; then
      echo "Errore: checksum non coincidente, sorgente mantenuta: $source" >&2
      return 1
    fi
  else
    echo "DRY-RUN: archiverei $source -> $destination"
    return 0
  fi

  echo "Verificato: $source -> $destination"
  rm -f -- "$source"
  echo "Rimosso dalla root: $source"
}

rotate_gate_mobile_log() {
  local source="$PROJECT_DIR/logs/gate-mobile-sync-cron.log"
  local destination_dir="$ARCHIVE_ROOT/logs"
  local timestamp rotated destination

  [[ -s "$source" ]] || return 0
  timestamp="$(date -u -r "$source" +%Y%m%dT%H%M%SZ)"
  rotated="$PROJECT_DIR/logs/gate-mobile-sync-cron-$timestamp.log"
  destination="$destination_dir/$(basename "$rotated")"

  if [[ "$APPLY" != yes ]]; then
    echo "DRY-RUN: ruoterei $source -> $destination.gz"
    return 0
  fi

  exec 8>"$GATE_MOBILE_LOCK_FILE"
  flock -w 300 8 || {
    echo "Errore: timeout sul lock Gate Mobile: $GATE_MOBILE_LOCK_FILE" >&2
    return 1
  }

  if [[ ! -s "$source" ]]; then
    flock -u 8
    return 0
  fi
  timestamp="$(date -u -r "$source" +%Y%m%dT%H%M%SZ)"
  rotated="$PROJECT_DIR/logs/gate-mobile-sync-cron-$timestamp.log"
  destination="$destination_dir/$(basename "$rotated")"
  if [[ -e "$rotated" || -e "$destination" || -e "$destination.gz" ]]; then
    flock -u 8
    echo "Errore: rotazione Gate Mobile gia' esistente per $timestamp" >&2
    return 1
  fi

  mv -- "$source" "$rotated"
  if ! { : > "$source" && chmod --reference="$rotated" "$source"; }; then
    rm -f -- "$source"
    mv -- "$rotated" "$source"
    flock -u 8
    echo "Errore: impossibile ricreare il log Gate Mobile" >&2
    return 1
  fi
  flock -u 8

  move_verified "$rotated" "$destination_dir"
  gzip -n -- "$destination"
  gzip -t -- "$destination.gz"
  echo "Compresso e verificato: $destination.gz"
}

migrate_older_than_retention() {
  local source_dir="$1"
  local destination_dir="$2"
  local keep_count="$3"
  shift 3
  local -a files=()
  local pattern

  [[ -d "$source_dir" ]] || return 0
  for pattern in "$@"; do
    while IFS= read -r file; do
      files+=("$file")
    done < <(find "$source_dir" -maxdepth 1 -type f -name "$pattern" -printf '%T@ %p\n' | sort -rn | sed 's/^[^ ]* //')
  done

  if (( ${#files[@]} <= keep_count )); then
    return 0
  fi
  for file in "${files[@]:keep_count}"; do
    move_verified "$file" "$destination_dir"
  done
}

migrate_database_backups() {
  local source_dir="$PROJECT_DIR/backups/db"
  local destination_dir="$ARCHIVE_ROOT/backups/db"
  local -a files=()

  [[ -d "$source_dir" ]] || return 0
  mapfile -t files < <(
    find "$source_dir" -maxdepth 1 -type f \( -name '*.dump' -o -name '*.sql' \) \
      -printf '%s %T@ %p\n' \
      | awk -v minimum="$BACKUP_MIN_BYTES" '{ priority=($1 >= minimum ? 0 : 1); print priority, $2, $3 }' \
      | sort -k1,1n -k2,2nr \
      | awk '{print $3}'
  )

  if (( ${#files[@]} > BACKUP_KEEP_COUNT )); then
    for file in "${files[@]:BACKUP_KEEP_COUNT}"; do
      move_verified "$file" "$destination_dir"
    done
  fi

  while IFS= read -r file; do
    move_verified "$file" "$destination_dir"
  done < <(
    find "$source_dir" -maxdepth 1 -type f \
      ! -name '*.dump' ! -name '*.sql' ! -name '.gitkeep' \
      -print | sort
  )
}

echo "==> Modalita': $([[ "$APPLY" == yes ]] && echo apply || echo dry-run)"
echo "==> Archivio: $ARCHIVE_ROOT"
migrate_database_backups
rotate_gate_mobile_log

for pattern in 'gaia-project-*.tar.gz' 'gaia-images-*.tar.gz' 'presenze-scraper-*.tar.gz' 'gaia-secrets-pdnd-*.tar.gz' 'gaia-release-*.txt'; do
  migrate_older_than_retention "$PROJECT_DIR/releases" "$ARCHIVE_ROOT/releases" "$RELEASE_KEEP_COUNT" "$pattern"
done

for pattern in 'gaia-images.tar.gz' 'gaia-backend-*.tar.gz' 'gaia-frontend-*.tar.gz' \
  'env-*.backup' 'orgchart-*.dump' 'pre-*.txt' 'ruolo_*.log'; do
  migrate_older_than_retention "$PROJECT_DIR/releases" "$ARCHIVE_ROOT/releases" 0 "$pattern"
done

echo "==> Spazio root"
df -h "$PROJECT_DIR"
echo "==> Spazio archivio"
df -h "$archive_probe"
