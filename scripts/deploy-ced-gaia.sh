#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/deploy-ced-gaia.sh

Variabili opzionali:
  DEPLOY_ACTION=deploy             deploy|nginx|smoke
  CED_SSH_HOST=serverCed           Host SSH o alias SSH del server CED
  CED_SERVER_IP=192.168.1.110      IP server CED, solo per log/verifica operativa
  CED_PROJECT_DIR=/opt/gaia        Directory progetto sul server
  ENV_FILE=.env.production         File env locale di produzione da copiare sul server
  GAIA_DOMAIN=gaia.lan             Dominio virtual host da configurare
  GAIA_MOBILE_DOMAIN=gaia-mobile.lan Dominio frontend mobile opzionale da includere nei CORS
  GAIA_PROD_NGINX_PORT=8080        Porta host interna usata dal container nginx di GAIA
  COMPOSE_PROJECT_NAME=gaia        Nome progetto compose
  RELEASE_ID=<auto>                Identificativo release, default timestamp + git sha
  RELEASE_RETENTION_COUNT=3        Quante release mantenere in $CED_PROJECT_DIR/releases per progetto/immagini/manifest
  ALLOW_NON_PRODUCTION_ENV=no      yes|no. Se no, APP_ENV deve essere production
  CONFIGURE_HOST_NGINX=auto        auto|yes|no. In auto configura nginx solo se sudo non richiede password
  SSH_OPTS="-p 22"                 Opzioni extra per ssh/scp

Lo script:
  - DEPLOY_ACTION=deploy: builda, copia immagini/progetto/.env.production, avvia lo stack e configura nginx host se possibile
  - DEPLOY_ACTION=nginx: configura solo il virtual host host nginx per gaia.lan
  - DEPLOY_ACTION=smoke: verifica soltanto container e health endpoint remoti

Note CED:
  - gaia.lan deve risolvere all'IP del server CED dai client che lo useranno.
  - La risoluzione DNS/router non viene modificata da questo script.
  - Il virtual host creato e dedicato a gaia.lan e punta allo stack GAIA su 127.0.0.1:$GAIA_PROD_NGINX_PORT.
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

require_nonempty_env() {
  local env_file="$1"
  local key="$2"
  local value
  value="$(read_env_value "$env_file" "$key" || true)"
  value="$(printf '%s' "$value" | sed 's/[[:space:]]*$//')"
  if [[ -z "$value" ]]; then
    echo "Errore: variabile obbligatoria assente o vuota in $env_file: $key" >&2
    exit 1
  fi
}

require_exact_env_value() {
  local env_file="$1"
  local key="$2"
  local expected="$3"
  local value
  value="$(read_env_value "$env_file" "$key" || true)"
  value="$(printf '%s' "$value" | sed 's/[[:space:]]*$//')"
  if [[ "$value" != "$expected" ]]; then
    echo "Errore: in $env_file la variabile $key deve essere '$expected' per il deploy CED." >&2
    exit 1
  fi
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

DEPLOY_ACTION="${DEPLOY_ACTION:-deploy}"
CED_SSH_HOST="${CED_SSH_HOST:-serverCed}"
CED_SERVER_IP="${CED_SERVER_IP:-192.168.1.110}"
CED_PROJECT_DIR="${CED_PROJECT_DIR:-/opt/gaia}"
ENV_FILE="${ENV_FILE:-.env.production}"
GAIA_DOMAIN="${GAIA_DOMAIN:-gaia.lan}"
GAIA_MOBILE_DOMAIN="${GAIA_MOBILE_DOMAIN:-gaia-mobile.lan}"
GAIA_PROD_NGINX_PORT="${GAIA_PROD_NGINX_PORT:-8080}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-gaia}"
RELEASE_ID="${RELEASE_ID:-}"
RELEASE_RETENTION_COUNT="${RELEASE_RETENTION_COUNT:-3}"
ALLOW_NON_PRODUCTION_ENV="${ALLOW_NON_PRODUCTION_ENV:-no}"
CONFIGURE_HOST_NGINX="${CONFIGURE_HOST_NGINX:-auto}"
SSH_OPTS="${SSH_OPTS:-}"

if [[ "$DEPLOY_ACTION" != "deploy" && "$DEPLOY_ACTION" != "nginx" && "$DEPLOY_ACTION" != "smoke" ]]; then
  echo "Errore: DEPLOY_ACTION deve essere deploy, nginx o smoke." >&2
  exit 1
fi

if [[ "$CONFIGURE_HOST_NGINX" != "auto" && "$CONFIGURE_HOST_NGINX" != "yes" && "$CONFIGURE_HOST_NGINX" != "no" ]]; then
  echo "Errore: CONFIGURE_HOST_NGINX deve essere auto, yes o no." >&2
  exit 1
fi

if [[ "$ALLOW_NON_PRODUCTION_ENV" != "yes" && "$ALLOW_NON_PRODUCTION_ENV" != "no" ]]; then
  echo "Errore: ALLOW_NON_PRODUCTION_ENV deve essere yes o no." >&2
  exit 1
fi

if ! [[ "$RELEASE_RETENTION_COUNT" =~ ^[1-9][0-9]*$ ]]; then
  echo "Errore: RELEASE_RETENTION_COUNT deve essere un intero positivo." >&2
  exit 1
fi

if [[ "$DEPLOY_ACTION" == "deploy" && ! -f "$ENV_FILE" ]]; then
  echo "Errore: file env non trovato: $ENV_FILE" >&2
  exit 1
fi

require_cmd ssh

if [[ "$DEPLOY_ACTION" == "deploy" ]]; then
  require_cmd docker
  require_cmd scp
  require_cmd tar
  require_cmd gzip

  if ! docker compose version >/dev/null 2>&1; then
    echo "Errore: docker compose v2 non disponibile." >&2
    exit 1
  fi
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
LOCAL_GIT_SHA="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")"
RELEASE_ID="${RELEASE_ID:-$(date +%Y%m%d-%H%M%S)-$LOCAL_GIT_SHA}"
IMAGES_ARCHIVE="$TMP_DIR/gaia-images-${RELEASE_ID}.tar.gz"
PROJECT_ARCHIVE="$TMP_DIR/gaia-project-${RELEASE_ID}.tar.gz"
RELEASE_MANIFEST="$TMP_DIR/gaia-release-${RELEASE_ID}.txt"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

cd "$ROOT_DIR"

echo "==> Target CED: $CED_SSH_HOST ($CED_SERVER_IP), dominio $GAIA_DOMAIN"
echo "==> Azione: $DEPLOY_ACTION"
echo "==> Release ID: $RELEASE_ID"
echo "==> Porta interna GAIA nginx: $GAIA_PROD_NGINX_PORT"

if [[ "$DEPLOY_ACTION" == "deploy" ]]; then
  require_nonempty_env "$ENV_FILE" "POSTGRES_PASSWORD"
  require_nonempty_env "$ENV_FILE" "DATABASE_URL"
  require_nonempty_env "$ENV_FILE" "JWT_SECRET_KEY"
  require_nonempty_env "$ENV_FILE" "BOOTSTRAP_ADMIN_USERNAME"
  require_nonempty_env "$ENV_FILE" "BOOTSTRAP_ADMIN_EMAIL"
  require_nonempty_env "$ENV_FILE" "BOOTSTRAP_ADMIN_PASSWORD"
  require_nonempty_env "$ENV_FILE" "CREDENTIAL_MASTER_KEY"
  require_exact_env_value "$ENV_FILE" "NETWORK_SOPHOS_SNMP_COMMUNITY" "GAIA-prod"

  app_env_value="$(read_env_value "$ENV_FILE" "APP_ENV" || true)"
  if [[ "$ALLOW_NON_PRODUCTION_ENV" != "yes" && "$app_env_value" != "production" ]]; then
    echo "Errore: per deploy CED APP_ENV deve essere production in $ENV_FILE. Usa ALLOW_NON_PRODUCTION_ENV=yes solo se davvero necessario." >&2
    exit 1
  fi

  if [[ "$GAIA_DOMAIN" == *.local ]]; then
    echo "Errore: GAIA_DOMAIN non puo puntare a un dominio locale in deploy CED: $GAIA_DOMAIN" >&2
    exit 1
  fi
  if [[ -n "$GAIA_MOBILE_DOMAIN" && "$GAIA_MOBILE_DOMAIN" == *.local ]]; then
    echo "Errore: GAIA_MOBILE_DOMAIN non puo puntare a un dominio locale in deploy CED: $GAIA_MOBILE_DOMAIN" >&2
    exit 1
  fi

  cat > "$RELEASE_MANIFEST" <<EOF
release_id=$RELEASE_ID
git_sha=$LOCAL_GIT_SHA
deployed_from_host=$(hostname)
deployed_at_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
gaia_domain=$GAIA_DOMAIN
gaia_mobile_domain=$GAIA_MOBILE_DOMAIN
gaia_prod_nginx_port=$GAIA_PROD_NGINX_PORT
env_file=$ENV_FILE
remote_env_file=.env
remote_production_env_file=.env.production
EOF

  echo "==> Build immagini Docker produzione GAIA"
  COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file "$ENV_FILE" build \
    backend frontend elaborazioni-worker-visure elaborazioni-worker-runtime elaborazioni-worker-autodoc scanner arp-helper

  echo "==> Salvataggio immagini in $IMAGES_ARCHIVE"
  docker save \
    "${COMPOSE_PROJECT_NAME}-backend:latest" \
    "${COMPOSE_PROJECT_NAME}-frontend:latest" \
    "${COMPOSE_PROJECT_NAME}-elaborazioni-worker-visure:latest" \
    "${COMPOSE_PROJECT_NAME}-elaborazioni-worker-runtime:latest" \
    "${COMPOSE_PROJECT_NAME}-elaborazioni-worker-autodoc:latest" \
    "${COMPOSE_PROJECT_NAME}-scanner:latest" \
    "${COMPOSE_PROJECT_NAME}-arp-helper:latest" \
    | gzip -c > "$IMAGES_ARCHIVE"

  echo "==> Preparazione archivio progetto"
  tar \
    --exclude='.git' \
    --exclude='.env' \
    --exclude='.env.*' \
    --exclude='.venv' \
    --exclude='.venv-*' \
    --exclude='.pydeps' \
    --exclude='.pytest_cache' \
    --exclude='.mypy_cache' \
    --exclude='node_modules' \
    --exclude='frontend/node_modules' \
    --exclude='frontend/.next' \
    --exclude='frontend/.next-*' \
    --exclude='frontend/playwright-report' \
    --exclude='frontend/test-results' \
    --exclude='backend/.pytest_cache' \
    --exclude='modules/elaborazioni/worker/.pytest_cache' \
    --exclude='__pycache__' \
    --exclude='scripts/tmp' \
    --exclude='tmp' \
    --exclude='backend/.mypy_cache' \
    --exclude='frontend/.turbo' \
    --exclude='backups' \
    --exclude='releases' \
    --exclude='deployments' \
    --exclude='*.tar' \
    --exclude='*.tar.gz' \
    --exclude='*.dump' \
    -czf "$PROJECT_ARCHIVE" .

  echo "==> Creazione directory remota $CED_PROJECT_DIR"
  ssh $SSH_OPTS "$CED_SSH_HOST" "CED_PROJECT_DIR='$CED_PROJECT_DIR' bash -s" <<'REMOTE_MKDIR'
set -Eeuo pipefail
if ! mkdir -p "$CED_PROJECT_DIR/releases" 2>/dev/null; then
  sudo mkdir -p "$CED_PROJECT_DIR/releases"
  sudo chown -R "$(id -u):$(id -g)" "$CED_PROJECT_DIR"
fi
REMOTE_MKDIR

  echo "==> Copia archivio progetto, immagini e env sul server"
  scp $SSH_OPTS "$PROJECT_ARCHIVE" "$CED_SSH_HOST:$CED_PROJECT_DIR/releases/gaia-project-${RELEASE_ID}.tar.gz"
  scp $SSH_OPTS "$IMAGES_ARCHIVE" "$CED_SSH_HOST:$CED_PROJECT_DIR/releases/gaia-images-${RELEASE_ID}.tar.gz"
  scp $SSH_OPTS "$RELEASE_MANIFEST" "$CED_SSH_HOST:$CED_PROJECT_DIR/releases/gaia-release-${RELEASE_ID}.txt"
  scp $SSH_OPTS "$ENV_FILE" "$CED_SSH_HOST:$CED_PROJECT_DIR/.env"
  scp $SSH_OPTS "$ENV_FILE" "$CED_SSH_HOST:$CED_PROJECT_DIR/.env.production"
fi

echo "==> Deploy remoto"
ssh $SSH_OPTS "$CED_SSH_HOST" \
  "DEPLOY_ACTION='$DEPLOY_ACTION' CED_PROJECT_DIR='$CED_PROJECT_DIR' GAIA_DOMAIN='$GAIA_DOMAIN' GAIA_MOBILE_DOMAIN='$GAIA_MOBILE_DOMAIN' GAIA_PROD_NGINX_PORT='$GAIA_PROD_NGINX_PORT' COMPOSE_PROJECT_NAME='$COMPOSE_PROJECT_NAME' CONFIGURE_HOST_NGINX='$CONFIGURE_HOST_NGINX' RELEASE_ID='$RELEASE_ID' RELEASE_RETENTION_COUNT='$RELEASE_RETENTION_COUNT' bash -s" <<'REMOTE'
set -Eeuo pipefail

NGINX_BASENAME="${GAIA_DOMAIN}.conf"
NGINX_SITE="/etc/nginx/conf.d/$NGINX_BASENAME"
if [[ -d /etc/nginx/sites-available && -d /etc/nginx/sites-enabled ]]; then
  NGINX_SITE="/etc/nginx/sites-available/$GAIA_DOMAIN"
fi

read_remote_env_value() {
  local env_file="$1"
  local key="$2"
  local line
  line="$(grep -E "^${key}=" "$env_file" | tail -n1 || true)"
  if [[ -z "$line" ]]; then
    return 1
  fi
  printf '%s' "${line#*=}"
}

postgres_volume_name_from_env() {
  local value
  value="$(read_remote_env_value .env "POSTGRES_VOLUME_NAME" || true)"
  value="$(printf '%s' "$value" | sed 's/[[:space:]]*$//')"
  if [[ -z "$value" ]]; then
    printf '%s' "gaia_postgres_data"
    return 0
  fi
  printf '%s' "$value"
}

compose_cmd() {
  local postgres_volume_name
  postgres_volume_name="$(postgres_volume_name_from_env)"
  POSTGRES_VOLUME_NAME="$postgres_volume_name" COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose --env-file .env "$@"
}

verify_postgres_volume_binding() {
  local expected_volume
  local resolved_volume
  local running_volume
  local expected_mountpoint=""
  local running_mountpoint=""

  expected_volume="$(postgres_volume_name_from_env)"
  resolved_volume="$(compose_cmd config | awk '
    $1 == "postgres_data:" { in_postgres = 1; next }
    in_postgres && $1 == "name:" { print $2; exit }
    /^[^[:space:]]/ && $1 != "postgres_data:" { in_postgres = 0 }
  ')"

  if [[ -z "$resolved_volume" ]]; then
    echo "Errore: impossibile risolvere il volume Docker di postgres dal compose remoto." >&2
    return 1
  fi

  if [[ "$resolved_volume" != "$expected_volume" ]]; then
    echo "Errore: il compose remoto risolve postgres_data su '$resolved_volume' ma .env richiede '$expected_volume'." >&2
    echo "Correggi docker-compose.yml o POSTGRES_VOLUME_NAME prima di procedere, altrimenti il deploy puo puntare al volume dati sbagliato." >&2
    return 1
  fi

  if docker volume inspect "$expected_volume" >/dev/null 2>&1; then
    expected_mountpoint="$(docker volume inspect "$expected_volume" --format '{{.Mountpoint}}' 2>/dev/null || true)"
  fi

  if docker ps -a --format '{{.Names}}' | grep -qx 'gaia-postgres'; then
    running_volume="$(docker inspect gaia-postgres --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' 2>/dev/null || true)"
    if [[ -n "$running_volume" && "$running_volume" != "$expected_volume" ]]; then
      echo "Errore: il container gaia-postgres attuale usa il volume '$running_volume' ma .env richiede '$expected_volume'." >&2
      echo "Il deploy si ferma per evitare di riallineare il runtime verso un volume dati inatteso." >&2
      return 1
    fi
  fi

  if [[ -n "$expected_mountpoint" ]]; then
    echo "==> Volume postgres atteso: $expected_volume ($expected_mountpoint)"
  else
    echo "==> Volume postgres atteso: $expected_volume"
  fi
}

print_nginx_manual_steps() {
  cat <<EOF

==> Azione manuale richiesta: configurazione nginx host
Lo stack GAIA e avviato su http://127.0.0.1:$GAIA_PROD_NGINX_PORT.
Per esporre http://$GAIA_DOMAIN eseguire sul server:

  sudo bash /opt/gaia/scripts/setup-ced-nginx-http-on-host.sh

EOF
}

configure_host_nginx() {
  if ! command -v nginx >/dev/null 2>&1; then
    echo "==> nginx host non installato."
    print_nginx_manual_steps
    return
  fi

  if [[ "$CONFIGURE_HOST_NGINX" == "no" ]]; then
    echo "==> Configurazione nginx host disabilitata."
    print_nginx_manual_steps
    return
  fi

  if [[ "$CONFIGURE_HOST_NGINX" == "auto" ]] && ! sudo -n true >/dev/null 2>&1; then
    echo "==> sudo senza password non disponibile, salto configurazione automatica nginx."
    print_nginx_manual_steps
    return
  fi

  if [[ "$CONFIGURE_HOST_NGINX" == "yes" ]] && ! sudo -n true >/dev/null 2>&1; then
    echo "Errore: CONFIGURE_HOST_NGINX=yes ma sudo richiede password." >&2
    exit 1
  fi

  echo "==> Configurazione nginx host per $GAIA_DOMAIN"
  sudo mkdir -p "$(dirname "$NGINX_SITE")"
  sudo tee "$NGINX_SITE" >/dev/null <<EOF
server {
    listen 80;
    server_name $GAIA_DOMAIN;

    client_max_body_size 128m;

    location / {
        proxy_pass http://127.0.0.1:$GAIA_PROD_NGINX_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

  if [[ "$NGINX_SITE" == /etc/nginx/sites-available/* ]]; then
    sudo ln -sfn "$NGINX_SITE" "/etc/nginx/sites-enabled/$GAIA_DOMAIN"
  fi

  sudo nginx -t
  sudo systemctl reload nginx
}

run_smoke_tests() {
  wait_for_http() {
    local url="$1"
    local label="$2"
    local attempts="${3:-30}"
    local delay_sec="${4:-2}"
    local host_header="${5:-}"
    local attempt=1

    while (( attempt <= attempts )); do
      if [[ -n "$host_header" ]]; then
        if curl -fsS -H "Host: $host_header" "$url" >/dev/null 2>&1; then
          return 0
        fi
      elif curl -fsS "$url" >/dev/null 2>&1; then
        return 0
      fi
      sleep "$delay_sec"
      attempt=$((attempt + 1))
    done

    echo "Errore: endpoint non pronto dopo $((attempts * delay_sec))s: $label ($url)" >&2
    return 1
  }

  echo "==> Smoke test container GAIA"
  docker ps --filter "name=gaia-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

  echo "==> Attesa readiness backend diretto"
  wait_for_http "http://127.0.0.1:8000/health" "backend health diretto"

  echo "==> Attesa readiness frontend diretto"
  wait_for_http "http://127.0.0.1:3000/login" "frontend login diretto"

  echo "==> Smoke test health stack su porta $GAIA_PROD_NGINX_PORT"
  wait_for_http "http://127.0.0.1:$GAIA_PROD_NGINX_PORT/api/health" "nginx -> backend /api/health"

  echo "==> Smoke test home stack su porta $GAIA_PROD_NGINX_PORT"
  wait_for_http "http://127.0.0.1:$GAIA_PROD_NGINX_PORT/" "nginx -> frontend home"

  echo "==> Smoke test pagina login"
  wait_for_http "http://127.0.0.1:$GAIA_PROD_NGINX_PORT/login" "nginx -> frontend login"

  if command -v nginx >/dev/null 2>&1 && [[ -f "$NGINX_SITE" || -L "$NGINX_SITE" ]]; then
    echo "==> Smoke test virtual host $GAIA_DOMAIN"
    wait_for_http "http://127.0.0.1/api/health" "host nginx virtual host health" 30 2 "$GAIA_DOMAIN"
  else
    echo "==> Smoke test virtual host saltato: nginx host non configurato."
  fi
}

verify_nginx_upstreams() {
  if ! docker ps --format '{{.Names}}' | grep -qx 'gaia-nginx'; then
    echo "Errore: container gaia-nginx non trovato." >&2
    return 1
  fi

  echo "==> Verifica risoluzione upstream da gaia-nginx"
  if docker exec gaia-nginx sh -lc 'getent hosts frontend backend >/dev/null'; then
    echo "==> Upstream Docker risolti correttamente da gaia-nginx"
    return 0
  fi

  echo "==> Upstream non risolti da gaia-nginx, forzo ricreazione mirata di frontend/backend/nginx"
  compose_cmd up -d --no-build --force-recreate frontend backend nginx

  echo "==> Attesa riallineamento rete Docker interna"
  local attempt=1
  while (( attempt <= 15 )); do
    if docker exec gaia-nginx sh -lc 'getent hosts frontend backend >/dev/null'; then
      echo "==> Upstream Docker ripristinati"
      return 0
    fi
    sleep 2
    attempt=$((attempt + 1))
  done

  echo "Errore: gaia-nginx non riesce ancora a risolvere frontend/backend dopo la ricreazione." >&2
  docker ps --filter "name=gaia-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" >&2 || true
  docker logs --tail=80 gaia-nginx >&2 || true
  return 1
}

prune_release_artifacts() {
  local release_dir="$CED_PROJECT_DIR/releases"
  local keep_count="${RELEASE_RETENTION_COUNT:-3}"

  prune_pattern() {
    local pattern="$1"
    local label="$2"
    local -a files=()

    mapfile -t files < <(find "$release_dir" -maxdepth 1 -type f -name "$pattern" -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk '{print $2}')
    if (( ${#files[@]} <= keep_count )); then
      return 0
    fi

    for file in "${files[@]:keep_count}"; do
      echo "==> Retention releases: rimuovo $label $(basename "$file")"
      rm -f -- "$file"
    done
  }

  echo "==> Retention releases: mantengo le ultime $keep_count release per artefatto"
  prune_pattern 'gaia-project-*.tar.gz' 'project'
  prune_pattern 'gaia-images-*.tar.gz' 'images'
  prune_pattern 'gaia-release-*.txt' 'manifest'
}

if [[ "$DEPLOY_ACTION" == "deploy" ]]; then
  cd "$CED_PROJECT_DIR"

  if [[ ! -f .env.production && -f .env ]]; then
    cp .env .env.production
  fi

  echo "==> Estrazione progetto"
  tar -xzf "releases/gaia-project-${RELEASE_ID}.tar.gz" -C "$CED_PROJECT_DIR"

  echo "==> Normalizzazione .env produzione"
  if grep -q '^NGINX_PORT=' .env; then
    sed -i "s|^NGINX_PORT=.*|NGINX_PORT=$GAIA_PROD_NGINX_PORT|" .env
  else
    printf '\nNGINX_PORT=%s\n' "$GAIA_PROD_NGINX_PORT" >> .env
  fi

  if grep -q '^NEXT_PUBLIC_API_BASE_URL=' .env; then
    sed -i 's|^NEXT_PUBLIC_API_BASE_URL=.*|NEXT_PUBLIC_API_BASE_URL=/api|' .env
  else
    printf 'NEXT_PUBLIC_API_BASE_URL=/api\n' >> .env
  fi

  if grep -q '^BACKEND_CORS_ORIGINS=' .env; then
    current_cors="$(grep '^BACKEND_CORS_ORIGINS=' .env | cut -d= -f2-)"
    new_cors="$current_cors"
    for origin in "http://$GAIA_DOMAIN"; do
      if [[ "$new_cors" != *"$origin"* ]]; then
        new_cors="${new_cors},${origin}"
      fi
    done
    if [[ -n "$GAIA_MOBILE_DOMAIN" ]]; then
      for origin in "http://$GAIA_MOBILE_DOMAIN"; do
        if [[ "$new_cors" != *"$origin"* ]]; then
          new_cors="${new_cors},${origin}"
        fi
      done
    fi
    sed -i "s|^BACKEND_CORS_ORIGINS=.*|BACKEND_CORS_ORIGINS=${new_cors}|" .env
  else
    if [[ -n "$GAIA_MOBILE_DOMAIN" ]]; then
      printf 'BACKEND_CORS_ORIGINS=http://%s,http://%s\n' "$GAIA_DOMAIN" "$GAIA_MOBILE_DOMAIN" >> .env
    else
      printf 'BACKEND_CORS_ORIGINS=http://%s\n' "$GAIA_DOMAIN" >> .env
    fi
  fi

  cp .env .env.production
  chmod 600 .env .env.production || true

  echo "==> Verifica APP_ENV remoto"
  remote_app_env="$(grep -E '^APP_ENV=' .env | tail -n1 | cut -d= -f2- || true)"
  if [[ "$remote_app_env" != "production" ]]; then
    echo "Errore: APP_ENV remoto deve essere production, trovato: ${remote_app_env:-<vuoto>}" >&2
    exit 1
  fi

  echo "==> Caricamento immagini Docker"
  gzip -dc "releases/gaia-images-${RELEASE_ID}.tar.gz" | docker load

  echo "==> Pull immagini registry dipendenti"
  verify_postgres_volume_binding

  compose_cmd pull postgres martin nginx || true

  echo "==> Avvio stack GAIA produzione"
  compose_cmd up -d --no-build --remove-orphans

  verify_nginx_upstreams

  if [[ -f "releases/gaia-release-${RELEASE_ID}.txt" ]]; then
    cp "releases/gaia-release-${RELEASE_ID}.txt" "$CED_PROJECT_DIR/current-release.txt"
  fi
fi

if [[ "$DEPLOY_ACTION" == "nginx" || "$DEPLOY_ACTION" == "deploy" ]]; then
  configure_host_nginx
fi

if [[ "$DEPLOY_ACTION" == "smoke" || "$DEPLOY_ACTION" == "deploy" ]]; then
  run_smoke_tests
  echo "Smoke test completati: http://$GAIA_DOMAIN"
fi

if [[ "$DEPLOY_ACTION" == "deploy" ]]; then
  prune_release_artifacts
fi
REMOTE
