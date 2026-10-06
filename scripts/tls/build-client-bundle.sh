#!/usr/bin/env bash
set -euo pipefail
[[ $# == 2 ]] || { echo 'Uso: build-client-bundle.sh CA_PUBBLICA.crt NUOVA_DIRECTORY_OUTPUT' >&2; exit 2; }
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
ca=$(realpath "$1")
out=$(realpath -m "$2")
expected=${MCP_CA_SHA256:?Serve impronta della NUOVA CA approvata dal CED}
expected=$(printf '%s' "$expected" | tr -d ':' | tr '[:lower:]' '[:upper:]')
name=${MCP_CA_COMMON_NAME:?Serve Common Name della NUOVA CA approvata dal CED}
[[ $expected != 84420F2555B205A98C3279E234126DAED183FDC1554FED09DB7475E20F66E7FF ]] || { echo 'CA Kiosk esclusa: richiesta nuova CA.' >&2; exit 3; }
bash "$here/validate-ca.sh" "$ca" "$expected" "$name"
[[ ! -e $out && ! -e $out.tar.gz && ! -e $out.zip ]] || { echo 'Output esistente: non sovrascrivo.' >&2; exit 1; }
go_bin=${GO_BIN:-go}
"$go_bin" version
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir "$work/source" "$work/bundle"
cp "$root"/installer/windows/*.go "$root/installer/windows/go.mod" "$work/source/"
sed "s/expectedName = \"CBO GAIA Root CA\"/expectedName = \"$name\"/" "$root/installer/windows/core.go" > "$work/source/core.go"
cp "$ca" "$work/source/ca.crt"
for arch in amd64 arm64; do
  (cd "$work/source"; CGO_ENABLED=0 GOOS=windows GOARCH=$arch GOTOOLCHAIN=local GOPROXY=off GOSUMDB=off \
    "$go_bin" build -buildvcs=false -trimpath -ldflags '-s -w -H windowsgui' -o "$work/bundle/CBO-CA-GAIA-Windows-$arch.exe" .)
done
cp "$ca" "$work/bundle/CBO-GAIA-Root-CA.crt"
cp "$here/validate-ca.sh" "$work/bundle/validate-ca.sh"
sed -e "s/@CA_SHA256@/$expected/" -e "s/@CA_COMMON_NAME@/$name/" \
  "$here/install-cbo-ca.sh" > "$work/bundle/Installa-CA-macOS.command"
cp "$work/bundle/Installa-CA-macOS.command" "$work/bundle/installa-ca-linux.sh"
cp "$root/domain-docs/mcps/CLIENT_CA_INSTALLERS.md" "$work/bundle/ISTRUZIONI.md"
sed -e "s/@CA_SHA256@/$expected/g" -e "s/@CA_COMMON_NAME@/$name/g" \
  "$root/config/mcps/CA_CLIENT_GUIDE.txt" > "$work/bundle/GUIDA-CLIENT.txt"
chmod 0755 "$work/bundle/"*.sh "$work/bundle/"*.command
printf '%s\n' "$expected" > "$work/bundle/CA-SHA256.txt"
(cd "$work/bundle"; sha256sum ./* > "$work/SHA256SUMS")
mv "$work/SHA256SUMS" "$work/bundle/"
mkdir -p "$(dirname "$out")"
mv "$work/bundle" "$out"
tar -czf "$out.tar.gz" -C "$(dirname "$out")" "$(basename "$out")"
if command -v zip >/dev/null; then
  (cd "$out"; zip -q "${out}.zip" ./*)
fi
printf 'Pacchetto pronto: %s\nArchivio: %s.tar.gz\n' "$out" "$out"
