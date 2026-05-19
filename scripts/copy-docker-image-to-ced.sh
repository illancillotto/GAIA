#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/copy-docker-image-to-ced.sh --ssh serverCed --service backend [--service frontend ...]
  ./scripts/copy-docker-image-to-ced.sh --ssh serverCed --image gaia-backend:latest [--image gaia-frontend:latest ...]
  ./scripts/copy-docker-image-to-ced.sh --ssh serverCed --service backend --copy-env --remote-env-path /opt/gaia/.env

Options:
  --ssh TARGET              Target SSH, also as alias from ~/.ssh/config. Required.
  --service NAME            Docker Compose service name to resolve as <project>-<service>:latest.
  --image REF               Explicit local Docker image reference.
  --copy-env                Copy local .env to the remote host.
  --local-env PATH          Local env file path. Default: .env
  --remote-env-path PATH    Remote env file path. Default: <remote-dir>/.env
  --project-name NAME       Compose project name. Default: gaia
  --remote-dir PATH         Remote temp directory. Default: /tmp/gaia-images
  --remote-docker-cmd CMD   Remote Docker command. Default: docker
  --help                    Show this help.

Notes:
  - At least one between --service and --image is required.
  - The script verifies the local image exists before exporting it.
  - The remote host must already have SSH access and Docker available.
EOF
}

SSH_TARGET=""
PROJECT_NAME="gaia"
REMOTE_DIR="/tmp/gaia-images"
REMOTE_DOCKER_CMD="docker"
COPY_ENV="false"
LOCAL_ENV_PATH=".env"
REMOTE_ENV_PATH=""
declare -a SERVICES=()
declare -a IMAGES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ssh)
      SSH_TARGET="${2:-}"
      shift 2
      ;;
    --service)
      SERVICES+=("${2:-}")
      shift 2
      ;;
    --image)
      IMAGES+=("${2:-}")
      shift 2
      ;;
    --copy-env)
      COPY_ENV="true"
      shift
      ;;
    --local-env)
      LOCAL_ENV_PATH="${2:-}"
      shift 2
      ;;
    --remote-env-path)
      REMOTE_ENV_PATH="${2:-}"
      shift 2
      ;;
    --project-name)
      PROJECT_NAME="${2:-}"
      shift 2
      ;;
    --remote-dir)
      REMOTE_DIR="${2:-}"
      shift 2
      ;;
    --remote-docker-cmd)
      REMOTE_DOCKER_CMD="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$SSH_TARGET" ]]; then
  echo "--ssh e obbligatorio." >&2
  usage >&2
  exit 1
fi

if [[ ${#SERVICES[@]} -eq 0 && ${#IMAGES[@]} -eq 0 && "$COPY_ENV" != "true" ]]; then
  echo "Specifica almeno un --service oppure un --image." >&2
  usage >&2
  exit 1
fi

if [[ -z "$REMOTE_ENV_PATH" ]]; then
  REMOTE_ENV_PATH="${REMOTE_DIR%/}/.env"
fi

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Comando richiesto non trovato: $1" >&2
    exit 1
  fi
}

require_command docker
require_command gzip
require_command ssh
require_command scp

declare -a ALL_IMAGES=()
for service in "${SERVICES[@]}"; do
  if [[ -z "$service" ]]; then
    echo "Valore vuoto ricevuto per --service." >&2
    exit 1
  fi
  ALL_IMAGES+=("${PROJECT_NAME}-${service}:latest")
done

for image in "${IMAGES[@]}"; do
  if [[ -z "$image" ]]; then
    echo "Valore vuoto ricevuto per --image." >&2
    exit 1
  fi
  ALL_IMAGES+=("$image")
done

tmp_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

ssh "$SSH_TARGET" "mkdir -p '$REMOTE_DIR'"

if [[ "$COPY_ENV" == "true" ]]; then
  if [[ ! -f "$LOCAL_ENV_PATH" ]]; then
    echo "File env locale non trovato: $LOCAL_ENV_PATH" >&2
    exit 1
  fi

  remote_env_dir="$(dirname "$REMOTE_ENV_PATH")"
  ssh "$SSH_TARGET" "mkdir -p '$remote_env_dir'"
  echo "[gaia] trasferimento env verso $SSH_TARGET:$REMOTE_ENV_PATH..."
  scp "$LOCAL_ENV_PATH" "${SSH_TARGET}:${REMOTE_ENV_PATH}"
fi

for image_ref in "${ALL_IMAGES[@]}"; do
  if ! docker image inspect "$image_ref" >/dev/null 2>&1; then
    echo "Immagine locale non trovata: $image_ref" >&2
    exit 1
  fi

  safe_name="${image_ref//\//_}"
  safe_name="${safe_name//:/_}"
  archive_name="${safe_name}.tar.gz"
  local_archive="${tmp_dir}/${archive_name}"
  remote_archive="${REMOTE_DIR%/}/${archive_name}"

  echo "[gaia] esportazione $image_ref..."
  docker image save "$image_ref" | gzip >"$local_archive"

  echo "[gaia] trasferimento $archive_name verso $SSH_TARGET..."
  scp "$local_archive" "${SSH_TARGET}:${remote_archive}"

  echo "[gaia] caricamento remoto di $image_ref..."
  ssh "$SSH_TARGET" "$REMOTE_DOCKER_CMD load -i '$remote_archive' && rm -f '$remote_archive'"
done

echo "[gaia] trasferimento completato."
