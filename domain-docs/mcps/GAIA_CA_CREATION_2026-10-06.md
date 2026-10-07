# Creazione della CA dedicata GAIA su questo PC

Stato completo MCP e rilascio: `CURRENT_STATUS_2026-10-06.md`.

## Stato e custodia

Il PC corrente e stato scelto dall'utente come custode. La configurazione
`config/mcps/pki/gaia-ca.cnf` e pronta e collaudata con OpenSSL reale.
**La CA e stata generata dall'utente il 2026-10-06** nel terminale locale,
fuori dal repository, seguendo il blocco sottostante. Certificato pubblico,
autofirma, vincoli CA e permessi verificati; nessuna chiave privata letta.
La preparazione iniziale aveva scrittura limitata a repository e `/tmp`;
il deposito permanente nella home e stato creato dall'utente.

Certificato: `~/gaia-pki/gaia-root.crt`, CN `CBO GAIA Root CA`, valido dal
2026-10-06 14:29:54 UTC al 2036-10-03 14:29:54 UTC. Impronta SHA-256 verificata:

```text
DA38A8715DAB864B526193BE42B60279C4C9E1F8DBF03F1E0598C30BF69B2E69
```

Directory custode/private 0700, file chiave 0600; `CA:TRUE,pathlen:0`,
keyUsage critical `keyCertSign,cRLSign`, verifica autofirma e validator
installer PASS. La passphrase e rimasta nel terminale dell'utente; il file
privato non e stato ispezionato. Questo non equivale ad approvazione CED
della distribuzione, backup offline completato o trust installato.
Il CSR e stato successivamente generato sul server finale e firmato
dall'utente sul custode; il deploy HTTPS resta da completare.

## Certificato server verificato (2026-10-06)

Server approvato: `192.168.1.110`, hostname TLS `gaia.lan`, SSH `serverCed`.
Chiave e CSR generati in `/home/ced/gaia-tls/gaia-lan-20261006/`,
directory 0700, `privkey.pem` 0600 e CSR 0644. Solo il CSR pubblico e stato
trasferito al custode; firma eseguita dall'utente con passphrase locale.
Certificato valido dal 2026-10-06 15:26:58 UTC al 2027-01-04 15:26:58 UTC,
SAN esclusivo `DNS:gaia.lan`. Non copre l'accesso HTTPS tramite IP.

`openssl verify` con CA dedicata, `sslserver` e hostname: PASS. Chiave
pubblica del certificato identica a quella CSR e, sul server, a quella
derivata dalla chiave privata: PASS. La chiave privata non e stata
trasferita o stampata. Copiati sul server `gaia.lan.crt` e `gaia-root.crt`
nella stessa directory privata, senza sovrascrivere file preesistenti.

Nessuna attivazione HTTPS: listener correnti 80/8080, nessun 443/8443.
Nginx host attivo e container `gaia-nginx` presente. Checkout `/opt/gaia`
fermo a `6b61fd27` con hotfix locali; file Compose/gateway MCP, client
approvati e dataset sintetico non presenti nei percorsi previsti.
Non eseguire un aggiornamento indiscriminato o un `compose up --build`
che possa sostituire immagini/hotfix attivi. Serve pianificare un rilascio
mirato e preservare il routing Nginx host; nessun reload/deploy effettuato.
Il modulo connector e importabile nell'immagine backend attiva, ma non
certifica un gateway aggiornato o configurato. Nginx host gestisce anche
`teti.lan` e `gaia-mobile.lan`; sudo richiede password, quindi il controllo
privilegiato `nginx -t` non e stato eseguito dalla sessione SSH.

Nome dedicato: `CBO GAIA Root CA`, distinto dalla vecchia CA Kiosk. Nessuno
store di trust e stato modificato e nessun certificato Kiosk verra sostituito.
Prima della distribuzione registrare custode, approvatore CED, impronta,
backup cifrato offline e procedura di rinnovo/revoca. Il PC puo essere usato
per la cerimonia; custodire offline la chiave quando non serve alla firma.

Default proposti: root 10 anni, certificati server 90 giorni, CRL 7 giorni.
La root puo firmare certificati finali, non CA intermedie (`pathlen:0`). Il
profilo server consente solo `DNS:gaia.lan`, uso `serverAuth`, chiave EC P-256;
non copia estensioni arbitrarie dal CSR. Nessun hostname pubblico/IP inventato.

## 1. Creare la CA nel terminale del custode

Passaggio gia eseguito per la CA sopra: non rieseguirlo e non cancellare
`~/gaia-pki`. Il blocco resta la procedura per una nuova cerimonia approvata.

Aprire un terminale su questo PC, entrare nella root del repository GAIA e
incollare il blocco seguente. Richiede OpenSSL e una passphrase robusta,
inserita ai prompt OpenSSL senza renderla visibile. Non passarla in argomenti,
variabili ambiente, file in chiaro o messaggi all'assistente.

La directory deve essere nuova: il comando si ferma se esiste, senza
sovrascrivere una CA o chiavi. In caso di errore conservare lo stato per
diagnosi; non eliminare automaticamente un deposito esistente.

```bash
(
  set -euo pipefail
  umask 077
  export GAIA_CA_DIR="$HOME/gaia-pki"
  mkdir -m 0700 "$GAIA_CA_DIR"
  mkdir -m 0700 "$GAIA_CA_DIR/private" "$GAIA_CA_DIR/issued"
  touch "$GAIA_CA_DIR/index.txt"
  printf '1000\n' > "$GAIA_CA_DIR/serial"
  printf '1000\n' > "$GAIA_CA_DIR/crlnumber"
  cp config/mcps/pki/gaia-ca.cnf "$GAIA_CA_DIR/openssl.cnf"
  openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 \
    -aes-256-cbc -out "$GAIA_CA_DIR/private/gaia-root.key.pem"
  openssl req -new -x509 -config "$GAIA_CA_DIR/openssl.cnf" \
    -key "$GAIA_CA_DIR/private/gaia-root.key.pem" -days 3650 \
    -out "$GAIA_CA_DIR/gaia-root.crt"
  chmod 0600 "$GAIA_CA_DIR/private/gaia-root.key.pem"
  chmod 0644 "$GAIA_CA_DIR/gaia-root.crt"
  openssl verify -CAfile "$GAIA_CA_DIR/gaia-root.crt" "$GAIA_CA_DIR/gaia-root.crt"
  openssl x509 -in "$GAIA_CA_DIR/gaia-root.crt" -noout \
    -subject -issuer -dates -fingerprint -sha256
)
```

Chiave privata: `~/gaia-pki/private/gaia-root.key.pem`, cifrata AES-256 e 0600.
Certificato pubblico: `~/gaia-pki/gaia-root.crt`. Non inviare la chiave al
server GAIA, a Sophos, negli installer, nel repository o all'assistente.
La directory privata resta 0700. Salvare un backup cifrato dell'intero stato
CA (chiave, certificato, database, seriali, CRL/config), separato dal PC.
Custodire la passphrase tramite la procedura CED, separata dal backup.

## 2. Generare chiave server e CSR sul server finale

Sul server GAIA, non sul custode:

```bash
bash scripts/tls/server-csr.sh /percorso/privato/nuovo-pending-gaia
```

Percorso nuovo, non una directory gia esistente. La chiave `privkey.pem`
resta sul server, 0600; trasferire al custode **solo** `gaia.lan.csr` tramite
il canale approvato. Il CSR locale storico in `runtime-data/mcps/tls/` non
dimostra la custodia della chiave sul server finale e non va usato per
il rilascio senza questa verifica.

## 3. Firmare il CSR approvato sul custode

Verificare provenienza del CSR, firma e subject/SAN `gaia.lan` prima di
approvarlo. Usare il file realmente ricevuto dal server al posto del percorso
seguente. Il profilo non eredita altri SAN o autorizzazioni dal CSR.

```bash
export GAIA_CA_DIR="$HOME/gaia-pki"
openssl req -in /percorso/CSR-approvato/gaia.lan.csr -noout -verify -text
openssl ca -config "$GAIA_CA_DIR/openssl.cnf" -extensions gaia_server \
  -notext -in /percorso/CSR-approvato/gaia.lan.csr \
  -out "$GAIA_CA_DIR/issued/gaia.lan.crt"
openssl verify -CAfile "$GAIA_CA_DIR/gaia-root.crt" -purpose sslserver \
  -verify_hostname gaia.lan "$GAIA_CA_DIR/issued/gaia.lan.crt"
```

Il comando chiede passphrase e conferma di firma; il database mantiene seriali
e cronologia. Per un rinnovo usare un nuovo nome output, non sovrascrivere
il certificato precedente. Ritrasferire al server solo il certificato
firmato e la CA pubblica. Verificare li che le chiavi pubbliche coincidano:

```bash
openssl x509 -in gaia.lan.crt -pubkey -noout
openssl pkey -in privkey.pem -pubout
```

I due output devono essere identici. Senza intermedi `gaia.lan.crt` e
sufficiente come certificate chain del server; i client devono fidarsi della
root distribuita separatamente. Non disabilitare la verifica TLS.

## 4. Installer e HTTPS dopo approvazione

Comunicare Common Name e impronta SHA-256 tramite canale indipendente.
Passare alla build soltanto `gaia-root.crt`, con `MCP_CA_COMMON_NAME` e
`MCP_CA_SHA256` approvati: `CLIENT_CA_INSTALLERS.md`. I vecchi pacchetti Kiosk
restano sospesi; non distribuirli per GAIA.

Installazione sul server, porte e controlli: `HTTP_HTTPS_GATEWAY.md`.
Nessun NAT/WAF Sophos richiesto per il perimetro locale concordato; verificare
eventuali policy endpoint/rete e firewall del server senza disabilitarle.
Accettazione: SAN/trust validi, HTTP MCP308 verso HTTPS, Data401 senza token,
discovery e chiamata del client approvato. Nessun deploy automatico qui.

## Revoca e rinnovo

Revocare usando la copia del certificato conservata dal custode:

```bash
export GAIA_CA_DIR="$HOME/gaia-pki"
openssl ca -config "$GAIA_CA_DIR/openssl.cnf" \
  -revoke "$GAIA_CA_DIR/issued/gaia.lan.crt" -crl_reason keyCompromise
openssl ca -config "$GAIA_CA_DIR/openssl.cnf" -gencrl \
  -out "$GAIA_CA_DIR/gaia-root.crl.pem"
```

Distribuzione e rinnovo CRL sono responsabilita CED da definire: nessun
endpoint CDP/OCSP viene inventato. La generazione della CRL **non** rende
automaticamente tutti i browser capaci di rilevare la revoca. In incidente
considerare anche revoca autorizzazioni OAuth, sostituzione chiave/certificato
e blocco temporaneo del servizio secondo la procedura approvata.

## Verifiche della preparazione

Successiva distribuzione client: generati gli EXE Windows amd64/ARM64
incorporando esclusivamente il certificato pubblico verificato. Pacchetto
Linux/macOS, guida con pin reale e link condizionali in `/login`
implementati; procedura build/pubblicazione in `CLIENT_CA_INSTALLERS.md`.
Asset ignorati da Git, nessun trust installato, nessun deploy effettuato.
Firma Authenticode e collaudo su sistemi operativi reali ancora necessari.

`make test-mcp-pki QUALITY_PYTHON=backend/.venv/bin/python`: quattro test con
OpenSSL reale, chiavi/certificati esclusivamente di test. Coprono chiave root
cifrata/password errata, vincoli CA, compatibilita validator installer,
catena/hostname/serverAuth e key match, SAN CSR non approvati esclusi,
seriali distinti e revoca verificata con CRL. Non installano trust e non
creano la CA operativa. Nessun runtime Python introdotto e nessuna soglia
coverage abbassata; la configurazione OpenSSL non ha coverage Python.

Esiti 2026-10-06: quattro test PKI PASS; `test-mcp-tls` e `lint-mcp-tls`
PASS, core Go installer 100% statement. Usato `GO_BIN=/snap/go/current/bin/go`
e `GOCACHE=/tmp/gaia-pki-gocache`: il launcher Snap `go` non funziona nel
sandbox, il binario toolchain esplicito esegue i controlli senza escalation.
Ruff/check-format del nuovo test e diff-check PASS. Nessun trust reale installato.

Graphify docs dominio/piattaforma tentato con i target Make e `gpt-reserve`:
API irraggiungibile, `Connection error` e risultati semantici parziali, pur
con exit 0. Non e un aggiornamento semantico completato; rieseguire i target
quando la connessione API e disponibile. Nessuna chiave CA inviata a Graphify.
