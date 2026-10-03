# Nuova CA GAIA e installer client

2026-10-02. Decisione utente: **nuova CA, procedura da concordare con il CED**.
Non e stata creata una CA nuova e nessuno store client e stato modificato.
I pacchetti precedentemente generati in `runtime-data/mcps/client-ca*`
usano la vecchia CA Kiosk: **SOSPESI, NON DISTRIBUIRE**, archivi inclusi.
Non rimuovere la CA Kiosk dai PC: resta necessaria a quel servizio.

## Procedura CED

1. Individuare custode, macchina CA protetta, backup cifrato e approvatore.
2. Il CED crea una CA dedicata; nome proposto `CBO GAIA Root CA`, da approvare.
   Chiave CA cifrata/offline, mai su server GAIA, repository o pacchetti.
   Concordare scadenza, rinnovo, revoca e distribuzione tramite GPO/MDM.
3. Consegnare alla build **solo certificato pubblico**, Common Name e
   impronta SHA-256 approvata tramite canale indipendente. Mai chiave/passphrase.
4. Generare chiave e CSR per SAN `gaia.lan` sul server finale. Consegnare
   solo CSR al custode; ottenere certificato server e catena della nuova CA.
5. Verificare catena, SAN, serverAuth, validita e corrispondenza chiave;
   installare con backup e reload controllato dopo verifica configurazione.
6. Costruire gli installer, collaudarli su PC di test Windows/macOS/Linux,
   poi approvare distribuzione gestita. Nessun deploy automatico.

CSR locale: `runtime-data/mcps/tls/pending-gaia/gaia.lan.csr`; chiave 0600,
directory 0700. Rigenerarla sul server finale, non trasferire la chiave locale.

```bash
bash scripts/tls/server-csr.sh /percorso/privato/nuovo-pending-gaia
```

## Build dopo approvazione CED

```bash
export MCP_CA_SHA256='<impronta approvata dal CED>'
export MCP_CA_COMMON_NAME='<Common Name approvato dal CED>'
GO_BIN=/percorso/go make mcp-ca-bundle MCP_CA_CERT=/percorso/nuova-CA-pubblica.crt MCP_CA_BUNDLE=runtime-data/mcps/nuova-ca-client
make test-mcp-tls lint-mcp-tls GO_BIN=/percorso/go
```

Go >=1.22, Bash, OpenSSL, tar, sha256sum; zip opzionale. Build offline senza
dipendenze Go esterne. Richiede nome e pin; rifiuta CA Kiosk precedente e
output esistente. Output ignorato da Git. Solo CA pubblica incorporata:
nessuna chiave, token o documento nel pacchetto.

## Windows

EXE amd64 su Intel/AMD 64 bit, arm64 su Windows ARM64. Avviare, accettare
UAC e confrontare l'impronta col CED. Installazione idempotente in ROOT
LocalMachine. Riavviare Edge/Chrome. Per GPO, terminale gia amministratore:

```powershell
.\CBO-CA-GAIA-Windows-amd64.exe /S /SHA256=<impronta-approvata>
```

Codici: 0 ok, 1 errore, 2 argomenti, 3 pin diverso, 4 admin richiesto, 5 annullato.
Interattivo: il processo iniziale puo terminare dopo il lancio UAC; per esito
automatizzato usare /S gia elevato. EXE non firmati Authenticode: richiedere
firma code-signing aziendale per release, non usare la CA TLS per firmare EXE.
Non disabilitare SmartScreen o policy. /U rimuove il certificato incorporato
previa conferma; /S /U richiede pin e approvazione CED.

## macOS e Linux

Estrarre tutta la cartella. Su macOS:

```bash
bash Installa-CA-macOS.command --verify
sudo bash Installa-CA-macOS.command --install --sha256 '<impronta approvata>'
```

Su Linux:

```bash
bash installa-ca-linux.sh --verify
sudo bash installa-ca-linux.sh --install --sha256 '<impronta approvata>'
```

Doppio clic macOS: sola verifica. Servono Bash e OpenSSL/LibreSSL nel PATH.
macOS usa portachiavi Sistema; Linux Debian/Ubuntu update-ca-certificates,
RHEL/Fedora update-ca-trust. Anchor GAIA distinto da Kiosk, nessuna
sovrascrittura di certificato diverso. Riavviare i browser.
Nessun PKG notarizzato: per MDM preferire profilo certificato del CED.
Firefox/JVM/container possono avere store separati: usare policy enterprise,
mai disabilitare TLS. Nessuna disinstallazione Unix automatica.
Verificare provenienza e checksum: SHA256SUMS non autentica il mittente.

## Stato delle verifiche

Core Go Windows: 100% statement con gate. Adapter Win32 escluso da questa
percentuale: collaudo nativo ancora richiesto. CA/CSR OpenSSL reali;
trust Windows/macOS/Linux simulati, nessuno store reale modificato.
Lint mirato: gofmt, Go vet core, sintassi Bash. Il target `lint-mcp-tls`
risolve gofmt dal PATH quando `GO_BIN=go`, oppure dalla directory del binario
Go esplicito; `GOFMT_BIN` permette un override. L'assenza di gofmt o il suo
fallimento fa fallire il target. Graphify Wiki: AST locale, nessun invio
documenti. Lint globale con backend/.venv fallisce su I001
preesistente in test_presenze_operations_postgres.py; ratchet globale
fallisce su regressioni preesistenti non correlate. Log in
`/tmp/gaia-ca-lint-venv.log`, `/tmp/gaia-ca-ratchet.log`.

## Claude remoto

Gli installer non installano MCP e non rendono gaia.lan pubblico.
La nuova CA interna non diventa attendibile sui server Anthropic:
per il form connettore remoto servono ingresso HTTPS pubblico, certificato
pubblicamente attendibile e autenticazione MCP/OAuth. Piano in
`PRODUCTION_CONNECTOR_PLAN.md`; nessun endpoint pubblico o deploy effettuato.
