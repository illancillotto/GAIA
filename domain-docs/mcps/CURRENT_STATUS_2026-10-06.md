# MCP GAIA: stato verificato al 2026-10-06

Aggiornamento sviluppo 2026-10-07: `LIVE_READS_2026-10-07.md` descrive
17 tool live in un server stdio separato, opt-in e verificato con dati
sintetici. Nessun cambiamento di deploy/HTTPS/OAuth sul CED e nessun
profilo live attivato: lo stato operativo riportato qui resta distinto.

Questo documento e il riepilogo operativo corrente. Preparazione isolata
successiva: `LAN_ISOLATED_RELEASE_2026-10-06.md` (container su loopback,
OAuth disattivato, dataset sintetico e immagine dedicata aggiornata).
I report datati precedenti
restano evidenze storiche: un gate locale passato non certifica il rilascio LAN.

## Perimetro

- Server CED `192.168.1.110`, hostname `gaia.lan`, accesso SSH `serverCed`.
- Solo LAN. Richiesti Claude Code/Desktop e Codex/ChatGPT Desktop;
  collegamento locale stdio/bridge e gateway HTTP da completare. Per
  ChatGPT serve valutare un ingresso supportato, incluso Secure MCP Tunnel;
  nessuna pubblicazione o associazione workspace autorizzata implicitamente.
- Nessun ingresso Internet, documento reale NAS o catalogo Trasparenza esposto.
- Connector HTTP Data-only sintetico, OAuth PKCE, consenso GAIA, scope,
  audit, budget e hardening implementati nel repository.
- OAuth: sessione assoluta 8 ore, cleanup 60 secondi, cap 10.000 grant
  complessivi e 1.000 per client, configurabili; nessuna espulsione dei
  token validi per fare spazio a nuove emissioni.

## PKI e installer

CA dedicata `CBO GAIA Root CA`, creata dall'utente sul PC custode;
chiave cifrata esterna al repository. Pin pubblico:
`DA38A8715DAB864B526193BE42B60279C4C9E1F8DBF03F1E0598C30BF69B2E69`.

CSR e chiave server generati sul CED, certificato firmato sul custode.
Catena, SAN `DNS:gaia.lan`, serverAuth e key match verificati. Certificato
valido dal 2026-10-06 15:26:58 UTC al 2027-01-04 15:26:58 UTC;
non copre l'accesso tramite IP. Pianificare il rinnovo prima della scadenza.
Certificati pubblici in `/home/ced/gaia-tls/gaia-lan-20261006/`;
chiave `privkey.pem` 0600, mai trasferita dal server.

EXE Windows amd64/ARM64 e guida/pacchetto Linux/macOS generati con la
nuova CA. Download implementati sulla login, visibili soltanto con manifest
corrispondente al pin atteso. Asset ignorati da Git: rigenerarli/pubblicarli
prima della build frontend. Nessuna installazione trust automatica;
EXE senza firma Authenticode, collaudo nativo ancora da completare.
I vecchi pacchetti CA Kiosk restano sospesi per GAIA, non rimuovere il
trust Kiosk necessario al servizio distinto.

## Server reale: preparato, non rilasciato

SSH e trasferimento dei soli certificati pubblici completati. Nginx host
serve `gaia.lan:80` verso `127.0.0.1:8080`; gestisce anche `teti.lan` e
`gaia-mobile.lan`. Container `gaia-nginx` attivo su 8080; nessun listener
443/8443 rilevato. Il certificato presente su disco non e ancora servito.

Checkout `/opt/gaia` a `6b61fd27` con hotfix locali e immagini applicative
gia distribuite. Il modulo connector e importabile nel container backend,
ma questo non dimostra che sia aggiornato, configurato o attivo.
File Compose/gateway MCP, client approvati e dataset sintetico assenti nei
percorsi del checkout storico. La release separata ora contiene template,
dataset sintetico e config client vuota, con container disattivato su
loopback; nessun gateway aggiunto al Nginx pubblico.
Nginx host richiede sudo con password; il test/reload
privilegiato non e stato eseguito. Nessun `git pull`, rebuild generale,
riavvio applicativo o modifica del routing effettuato. L'immagine attiva
non ha il nuovo modulo oauth_maintenance: la release usa un'immagine
dedicata aggiornata, non sostituisce backend o altri container.

## Evidenze e limiti

- CA/bundle: 8 test infrastruttura passati; PE reali amd64/ARM64 e checksum
  verificati. Core Go al 100% statement, adapter Win32 fuori da tale misura.
- Login/download: 19 test, tre file runtime al 100% di statement, branch,
  funzioni e linee. ESLint, TypeScript e ratchet mirato passati.
- Riverifica OAuth: 31 test, coverage full-file 100%; consenso: 23 test,
  100%; discovery/stdio: 15 test, 100% sui file misurati.
- Nella riverifica iniziale con sandbox ristretto, connector 42 test passati e
  un test TCP bloccato dai socket; gateway bloccato dall'accesso Docker.
  Successiva riverifica senza restrizioni: OAuth 31 e connector 43 test
  PASS, inclusa chiamata TCP/revoca, coverage 100% nei rispettivi gate.
  Quattro nuovi test Compose release isolata PASS. Non sono prove OAuth
  abilitate sul CED o un gate integrato completamente verde.
- Claude Desktop: handshake e tools/list osservati il 2026-10-05;
  tools/call dal modello e risposta/provenance ancora da verificare.
- Successivamente: gateway 67 test PASS con Docker locale. Codex aggiunto
  al profilo stdio, Claude Code/Desktop gia configurati; smoke SDK dalla
  configurazione reale con tools/call e provenance PASS. Non e una prova
  tool calling del modello nelle app o un collegamento ChatGPT operativo.
- Gate globali stile/complessita non certificati verdi; i risultati mirati
  non risolvono debito o modifiche concorrenti esterni a questa change.

## Prossimi passi, in ordine

1. Approvare il rilascio mirato: backup, preservazione hotfix e immagini,
   scelta dell'ingresso HTTPS host/Compose, test configurazione e rollback.
2. Installare il trust sui client approvati e distribuire il frontend con
   gli asset pubblici; non aggirare TLS o SmartScreen.
3. Per il gateway OAuth definire client_id/callback reali del bridge/client
   approvato, dataset sintetico e configurazione; non inventare callback.
4. Attivare HTTPS e gateway nella finestra concordata, verificare SAN/trust,
   redirect HTTP 308, discovery e Data 401 senza token.
5. Completare consenso, tool calling e revoca dal client effettivo;
   lo stdio locale usa local-stdio, non delega automaticamente utenti GAIA.
6. Per NAS definire mapping canonico GAIA/account NAS, ACL/freshness e
   allowlist; per Trasparenza approvare fonte/catalogo. Restano fail-closed.

Procedure: `GAIA_CA_CREATION_2026-10-06.md`, `CLIENT_CA_INSTALLERS.md`,
`HTTP_HTTPS_GATEWAY.md`, `CONNECTOR_RUNTIME_2026-10-03.md`,
`OAUTH_HARDENING_2026-10-05.md`, `LAN_DESKTOP_READINESS_2026-10-05.md`.
