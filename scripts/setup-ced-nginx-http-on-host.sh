#!/usr/bin/env bash
set -Eeuo pipefail

# Run on the CED host with sudo to restore HTTP-only nginx vhosts.
#   sudo ./scripts/setup-ced-nginx-http-on-host.sh

GAIA_PORT="${GAIA_PORT:-8080}"
TETI_PORT="${TETI_PORT:-8085}"
MOBILE_PORT="${MOBILE_PORT:-5183}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Esegui come root: sudo $0" >&2
  exit 1
fi

write_vhost() {
  local site_name="$1"
  local server_name="$2"
  local upstream_port="$3"
  local body_size="${4:-128m}"
  local site_path="/etc/nginx/sites-available/${site_name}"

  tee "$site_path" >/dev/null <<EOF
server {
    listen 80;
    server_name ${server_name};

    client_max_body_size ${body_size};

    location / {
        proxy_pass http://127.0.0.1:${upstream_port};
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

  ln -sfn "$site_path" "/etc/nginx/sites-enabled/${site_name}"
}

write_vhost "gaia.lan" "gaia.lan" "$GAIA_PORT"
write_vhost "gaia-mobile.conf" "gaia-mobile.lan" "$MOBILE_PORT" "50m"
write_vhost "teti.lan" "teti.lan" "$TETI_PORT" "50m"

nginx -t
systemctl reload nginx

echo "[gaia] nginx HTTP attivo su http://gaia.lan, http://teti.lan, http://gaia-mobile.lan"
