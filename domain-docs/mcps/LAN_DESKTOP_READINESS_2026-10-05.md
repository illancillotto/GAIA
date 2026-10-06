# Readiness LAN e Claude Desktop

Aggiornamento 2026-10-06: nuova CA creata dall'utente sul PC custode,
certificato pubblico/autofirma/vincoli e permessi verificati. Impronta e
procedura: `GAIA_CA_CREATION_2026-10-06.md`. CSR/chiave ora creati sul server
`192.168.1.110`, certificato firmato dall'utente, catena/hostname/serverAuth
e key match verificati. Certificati pubblici copiati sul server; restano
trust e deploy HTTPS. Checkout server arretrato con hotfix locali e senza
file gateway MCP: nessun aggiornamento indiscriminato effettuato. Le rilevazioni
di rete e Desktop sotto sono lo snapshot 2026-10-05, non una prova TLS nuova.

## Perimetro approvato

Host `gaia.lan`, solo LAN. Claude Desktop locale, stdio/bridge;
ChatGPT da valutare. Nessuna apertura Internet, nuova CA o lettura documenti
NAS autorizzata implicitamente. Hardening: `OAUTH_HARDENING_2026-10-05.md`.

## Evidenza operativa reale

- `getent hosts gaia.lan`: hostname risolto su indirizzo LAN.
- HTTP porta 8080, `/api/wiki/mcp/connector/data`: 404, non redirect 308.
- HTTPS porte 443 e 8443: connessione rifiutata; il gateway TLS non e attivo
  su questi ingressi. Non e un errore di trust verificato, manca il listener.
- Nessun container locale attivo rilevato da `docker ps` durante l'audit.
  Questo non descrive lo stato Docker del server LAN remoto.
- Claude Desktop installato, avviato nella sessione grafica locale.
- Voce `gaia-synthetic` integrata in `~/.config/Claude/claude_desktop_config.json`,
  corrispondente all'esempio risolto ignorato da Git. Solo database sintetico,
  tre scope Data; nessun mount/corpus Docs e nessun segreto provider aggiunto.
- Backup privato 0600 creato prima della modifica. Hash della configurazione
  escluso `mcpServers` invariato subito dopo l'inserimento, prima dell'avvio;
  configurazione ancora 0600. Dopo l'avvio e stata osservata una variazione
  in `preferences/epitaxyPrefs/dframe-code-sections`: non e stata sovrascritta
  o ripristinata implicitamente. La voce MCP resta identica a quella verificata.
- Log Desktop `mcp-server-gaia-synthetic.log`: server connected successfully,
  `initialize`/result, `notifications/initialized`, `tools/list`/result,
  verificati alle 16:25:47–48 UTC del 2026-10-05. Non e una simulazione SDK.

## Accettazione ancora incompleta

Handshake e discovery sono provati; **nessuna `tools/call` dal modello Desktop
e ancora osservata**. Non equivalgono a una prova end-to-end completata.
L'utente e invitato a eseguire in una nuova chat:

> Usa gaia-synthetic per cercare i soggetti sintetici omonimi e mostrami la provenance.

Confermare la chiamata reale nel log del server e la risposta/provenance
nell'app, senza leggere o copiare chat personali non pertinenti. Lo stdio usa
il principal `local-stdio`, non una delega OAuth di un utente GAIA.

Per HTTPS operativo usare i percorsi verificati nel report CA del 2026-10-06
e pianificare il rilascio mirato sul server LAN preservando gli hotfix.
Non riutilizzare la CA precedentemente sospesa. Con lo stack attivato
verificare trust, discovery, HTTP308 e protezione Data401, quindi consenso
e chiamata OAuth con un client/callback approvato se richiesto dal bridge.

NAS: mapping GAIA/account NAS verificato e freshness/allowlist ACL da definire.
Trasparenza: fonte/catalogo approvato da definire. Entrambe le estensioni
restano non esposte. ChatGPT non pubblicato o attivato.

## Ripristino locale

Chiudere Desktop prima di ripristinare il backup privato della configurazione
e riavviarlo. Percorso backup annotato localmente in
`/tmp/gaia-claude-desktop-backup-path`; nessun file del profilo viene versionato.
Rimuovere soltanto la voce aggiunta e preservare altre voci/configurazioni
se il profilo e stato modificato successivamente dall'utente.
