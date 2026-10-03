#!/usr/bin/env bash
set -euo pipefail
[[ $# == 3 ]] || { echo 'Uso: validate-ca.sh CA.crt SHA256 COMMON_NAME' >&2; exit 2; }
ca=$1
expected=$(printf '%s' "$2" | tr -d ':' | tr '[:lower:]' '[:upper:]')
name=$3
[[ $name =~ ^[A-Za-z0-9\ _-]{1,80}$ ]] || exit 2
[[ $expected =~ ^[0-9A-F]{64}$ ]] || exit 2
awk '
  /^-----BEGIN CERTIFICATE-----$/ { if (inside || count) exit 1; inside=1; count++; next }
  /^-----END CERTIFICATE-----$/ { if (!inside) exit 1; inside=0; next }
  { if (inside) { if ($0 !~ /^[A-Za-z0-9+\/=]+$/) exit 1 } else if ($0 !~ /^[[:space:]]*$/) exit 1 }
  END { if (inside || count != 1) exit 1 }
' "$ca"
actual=$(openssl x509 -in "$ca" -noout -fingerprint -sha256)
actual=${actual#*=}
[[ ${actual//:/} == "$expected" ]] || { echo 'Impronta CA diversa: nessuna installazione.' >&2; exit 3; }
details=$(openssl x509 -in "$ca" -noout -text)
grep -q 'CA:TRUE' <<< "$details"
grep -q 'Certificate Sign' <<< "$details"
subject=$(openssl x509 -in "$ca" -noout -subject -nameopt RFC2253)
[[ ,${subject#subject=}, == *",CN=$name,"* ]]
openssl verify -CAfile "$ca" "$ca" >/dev/null
printf 'CA verificata, SHA256=%s\n' "$expected"
