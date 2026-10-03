#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes \
  -subj '/CN=CBO Internal Root CA' -days 1 \
  -addext 'basicConstraints=critical,CA:TRUE' -addext 'keyUsage=critical,keyCertSign,cRLSign' \
  -keyout "$work/test.key" -out "$work/CBO-Internal-Root-CA.crt" 2>/dev/null
expected=$(openssl x509 -in "$work/CBO-Internal-Root-CA.crt" -noout -fingerprint -sha256)
expected=${expected#*=}
expected=${expected//:/}
cp "$here/validate-ca.sh" "$work/"
cp "$work/CBO-Internal-Root-CA.crt" "$work/CBO-GAIA-Root-CA.crt"
sed -e "s/@CA_SHA256@/$expected/" -e 's/@CA_COMMON_NAME@/CBO Internal Root CA/' \
  "$here/install-cbo-ca.sh" > "$work/installer.sh"
expect_failure() {
  if "$@" > "$work/failure.log" 2>&1; then
    echo "Accettato comando che doveva fallire: $*" >&2; exit 1
  fi
}
bash "$work/installer.sh" --verify
expect_failure bash "$work/installer.sh" --install
expect_failure bash "$work/installer.sh" --unknown
expect_failure bash "$work/installer.sh" --install --sha256 "$(printf '0%.0s' {1..64})"
expect_failure bash "$here/validate-ca.sh" "$work/CBO-Internal-Root-CA.crt" bad 'CBO Internal Root CA'
cat "$work/CBO-Internal-Root-CA.crt" "$work/test.key" > "$work/private.crt"
expect_failure bash "$here/validate-ca.sh" "$work/private.crt" "$expected" 'CBO Internal Root CA'
cat "$work/CBO-Internal-Root-CA.crt" "$work/CBO-Internal-Root-CA.crt" > "$work/two.crt"
expect_failure bash "$here/validate-ca.sh" "$work/two.crt" "$expected" 'CBO Internal Root CA'
{ echo garbage; cat "$work/CBO-Internal-Root-CA.crt"; } > "$work/garbage.crt"
expect_failure bash "$here/validate-ca.sh" "$work/garbage.crt" "$expected" 'CBO Internal Root CA'
expect_failure bash "$here/validate-ca.sh" "$work/CBO-Internal-Root-CA.crt" "$expected" 'Wrong CA'
expect_failure env MCP_CA_SHA256=84420F2555B205A98C3279E234126DAED183FDC1554FED09DB7475E20F66E7FF MCP_CA_COMMON_NAME='CBO Internal Root CA' \
  bash "$here/build-client-bundle.sh" "$work/CBO-Internal-Root-CA.crt" "$work/forbidden-bundle"
[[ ! -e $work/forbidden-bundle ]]
mkdir "$work/bin"
cat > "$work/bin/id" <<'STUB'
#!/usr/bin/env bash
echo "${TEST_UID:-0}"
STUB
cat > "$work/bin/uname" <<'STUB'
#!/usr/bin/env bash
echo "${TEST_OS:-Unsupported}"
STUB
for command in install update-ca-certificates security; do
  cat > "$work/bin/$command" <<'STUB'
#!/usr/bin/env bash
printf '%s %s\n' "$(basename "$0")" "$*" >> "$TEST_LOG"
STUB
done
chmod 0755 "$work/bin/"*
export PATH="$work/bin:$PATH" TEST_LOG="$work/commands.log"
expect_failure env TEST_UID=1000 bash "$work/installer.sh" --install --sha256 "$expected"
expect_failure bash "$work/installer.sh" --install --sha256 "$expected"
[[ ! -e $TEST_LOG ]]
TEST_OS=Darwin bash "$work/installer.sh" --install --sha256 "$expected"
grep -q 'security add-trusted-cert -d -r trustRoot' "$TEST_LOG"
grep -q 'security verify-cert' "$TEST_LOG"
if [[ ! -e /usr/local/share/ca-certificates/CBO-GAIA-Root-CA.crt ]]; then
  TEST_OS=Linux bash "$work/installer.sh" --install --sha256 "$expected"
  grep -q 'install -m 0644' "$TEST_LOG"
  grep -q 'update-ca-certificates' "$TEST_LOG"
fi
bash "$here/server-csr.sh" "$work/server"
[[ $(stat -c '%a' "$work/server/privkey.pem") == 600 ]]
openssl req -in "$work/server/gaia.lan.csr" -noout -text | grep -q 'DNS:gaia.lan'
expect_failure bash "$here/server-csr.sh" "$work/server"
echo 'PASS: CA/CSR OpenSSL reali; trust Windows/Unix simulato, nessuno store modificato.'
