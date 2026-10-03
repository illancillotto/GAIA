#!/usr/bin/env bash
set -euo pipefail
[[ $# == 1 ]] || { echo 'Uso: server-csr.sh DIRECTORY_PRIVATA_OUTPUT' >&2; exit 2; }
directory=$1
[[ ! -e $directory ]] || { echo 'Directory esistente: non sovrascrivo chiavi.' >&2; exit 1; }
umask 077
mkdir -p "$directory"
chmod 0700 "$directory"
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$directory/privkey.pem"
openssl req -new -key "$directory/privkey.pem" -sha256 -subj '/CN=gaia.lan' \
  -addext 'subjectAltName=DNS:gaia.lan' \
  -addext 'basicConstraints=critical,CA:FALSE' \
  -addext 'keyUsage=critical,digitalSignature' \
  -addext 'extendedKeyUsage=serverAuth' -out "$directory/gaia.lan.csr"
chmod 0600 "$directory/privkey.pem"
chmod 0644 "$directory/gaia.lan.csr"
openssl req -in "$directory/gaia.lan.csr" -noout -verify
echo 'Copiare al custode CA SOLO gaia.lan.csr. La chiave resta sul server.'
