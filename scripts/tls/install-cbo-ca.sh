#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
ca="$here/CBO-GAIA-Root-CA.crt"
expected='@CA_SHA256@'
name='@CA_COMMON_NAME@'
action=${1:---verify}
case "$action" in
  --verify) [[ $# -le 1 ]] || exit 2 ;;
  --install) [[ $# == 3 && $2 == --sha256 ]] || { echo 'Uso: --install --sha256 IMPRONTA_COMUNICATA_DAL_CED' >&2; exit 2; }
    supplied=$(printf '%s' "$3" | tr -d ':' | tr '[:lower:]' '[:upper:]')
    [[ $supplied == "$expected" ]] || { echo 'Impronta attesa diversa.' >&2; exit 3; } ;;
  *) echo 'Uso: --verify oppure --install --sha256 IMPRONTA' >&2; exit 2 ;;
esac
bash "$here/validate-ca.sh" "$ca" "$expected" "$name"
[[ $action == --install ]] || exit 0
[[ $(id -u) == 0 ]] || { echo 'Eseguire con sudo dopo aver verificato impronta e provenienza del pacchetto.' >&2; exit 4; }
case "$(uname -s)" in
  Darwin)
    security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$ca"
    security verify-cert -c "$ca" -p basic ;;
  Linux)
    if command -v update-ca-certificates >/dev/null; then
      anchor=/usr/local/share/ca-certificates/CBO-GAIA-Root-CA.crt
      refresh=update-ca-certificates
    elif command -v update-ca-trust >/dev/null; then
      anchor=/etc/pki/ca-trust/source/anchors/CBO-GAIA-Root-CA.crt
      refresh=update-ca-trust
    else
      echo 'Distribuzione non supportata: nessuna installazione.' >&2; exit 1
    fi
    if [[ -e $anchor || -L $anchor ]]; then
      [[ -f $anchor && ! -L $anchor ]] || exit 1
      bash "$here/validate-ca.sh" "$anchor" "$expected" "$name"
    else
      install -m 0644 "$ca" "$anchor"
    fi
    "$refresh" ;;
  *) echo 'Sistema non supportato.' >&2; exit 1 ;;
esac
echo 'CA installata. Riavviare il browser. Non configura DNS, server MCP o connettori remoti.'
