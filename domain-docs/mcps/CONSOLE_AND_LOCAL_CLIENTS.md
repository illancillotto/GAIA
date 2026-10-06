# Console MCP e client locali

Stato operativo 2026-10-05: Claude Desktop locale configurato e avviato con
`gaia-synthetic`; handshake e discovery `tools/list` verificati nei log del
client reale. La chiamata tool da una chat Desktop resta da confermare.
Host LAN e gate HTTPS: `LAN_DESKTOP_READINESS_2026-10-05.md`.

La pagina `/wiki/mcp/console`, raggiungibile dalla preview `/wiki/mcp` e dal
menu Wiki, permette di consultare le dieci entita del dataset sintetico,
incluse le tabelle di relazione. Non invoca il modello per visualizzare dati
o storico. Caricamento esplicito e paginazione: 25 record per pagina,
massimo server 100. Importi serializzati con lo stesso contratto dei tool Data.

## Autorizzazione e storico

`GET /wiki/mcp/console/{kind}` usa autenticazione GAIA e permessi correnti;
`kind` ammette solo `catalog`, `calls` e le dieci entita note. Il gateway
inoltra un bearer interno breve a `/inspect/{kind}` sul server Data, senza
configurare Docs, senza redirect e senza esporre firma o chiavi al browser.
Entita negate: 403. Principal inattivo: 401. Risorse sconosciute: 404.
Le relazioni soggetto/utenza richiedono entrambi i permessi Utenze e Catasto.

Lo storico e locale in `gaia-mcp-audit.sqlite`, separato dal dataset read-only
e dai log minimizzati su stderr. Conserva le ultime 1000 chiamate Data
complessive: timestamp, tool, durata, esito, budget stimato, correlazione,
principal pseudonimizzato, filtri ammessi, risposta sintetica e provenance.
Non conserva domande, messaggi LLM, credenziali o contenuti Docs. `query` e
`cursor` sono sempre omessi; altri filtri stringa sono conservati solo se
UUID canonici o codici `SYN-*`, altrimenti sono omessi. Gli errori non
conservano argomenti. I log applicativi restano senza record o argomenti.

Un utente vede le proprie chiamate nei domini ancora autorizzati, sul dataset
attuale. Gli amministratori ricevono `mcp.audit.read` soltanto dal gateway
della console e vedono anche altri principal nei propri domini autorizzati.
Questo scope non e emesso dal normale `/wiki/mcp/token` e non abilita tool.
La revoca di un dominio nasconde subito entita e relativo storico nelle
nuove richieste GAIA. La visualizzazione non aggiunge chiamate allo storico.
Senza `--audit-database`, il catalogo dichiara `audit_enabled=false`; lo
storico restituisce 503. Se la persistenza audit fallisce, la chiamata non
prosegue come se fosse stata registrata.

## Avvio Data-only

```bash
make mcp-data-seed QUALITY_PYTHON=backend/.venv/bin/python
make mcp-data-http QUALITY_PYTHON=backend/.venv/bin/python
```

Il secondo comando richiede `GAIA_MCP_SIGNING_SECRET` gia configurato.
`--data-only` non carica alcun corpus e non monta `/docs/`. Il CLI respinge
la combinazione `--data-only --corpus`. `make mcp-http` e i launcher Docs
esistenti restano disponibili separatamente, come la chat Wiki legacy.
L'override `docker-compose.mcp.yml` usa Data-only, solo directory Data
read-only (nessun mount del corpus Docs) e un
volume audit scrivibile distinto. Nel gateway di produzione i permessi
provengono sempre dal database GAIA; nessun account di prova viene creato.

Dataset e audit devono essere leggibili/scrivibili dall'UID scelto per il
launcher: container e stdio condividono lo stesso file audit senza cambiare
principal. I client stdio usano il principal locale `local-stdio`, non
impersonano un utente GAIA. Gli scope stdio sono assegnati dal launcher,
non da argomenti tool. La SQLite audit viene impostata a permessi 0600 e
deve restare accessibile solo agli operatori locali autorizzati; non montare
directory operative nel launcher.

## Claude Code e Desktop

Claude Code e configurato localmente nel progetto come `gaia-synthetic`.
Verifica: `claude mcp get gaia-synthetic`. La configurazione risiede nel
profilo privato di Claude e non modifica i server preesistenti.

Il comando equivalente, sostituendo `/absolute/path/GAIA`, e:

```bash
claude mcp add --scope local --transport stdio gaia-synthetic \
  -e PYTHONPATH=/absolute/path/GAIA/backend -- \
  /absolute/path/GAIA/backend/.venv/bin/python \
  -m app.modules.wiki.mcps.data serve \
  --database /absolute/path/GAIA/runtime-data/mcps/data/gaia-mcp-synthetic-v1.sqlite \
  --audit-database /absolute/path/GAIA/runtime-data/mcps/audit/gaia-mcp-audit.sqlite \
  --scopes utenze.read,catasto.read,ruolo.read
```

Per Claude Desktop, integra soltanto la voce `gaia-synthetic` di
`config/mcps/claude-desktop.example.json` nel file di configurazione del
client, sostituendo i path assoluti. Non sovrascrivere altre voci. Su questa
macchina la configurazione con path gia risolti e disponibile in
`runtime-data/mcps/claude-desktop-config.json`, ignorata da Git. La stessa voce
e ora integrata nel profilo Desktop privato, con backup 0600 e verifica che
l'inserimento preservi preferenze e altre impostazioni prima dell'avvio.
Desktop e stato avviato;
ha inizializzato il server e richiesto `tools/list` con successo.
Non occorrono credenziali codex-lb o GAIA per lo stdio.
Il collegamento espone solo tool Data, senza Docs o API operative.
La connessione di Claude Code e stata verificata; la chiamata tool precedente
e stata eseguita con SDK stdio, senza avviare un modello Claude nel repository.
La nuova connessione Desktop non dimostra ancora una chiamata tool dal modello:
eseguire in una nuova chat «Usa gaia-synthetic per cercare i soggetti sintetici
omonimi e mostrami la provenance». Non utilizzare documenti NAS reali.

## ChatGPT successivamente

Su scelta dell'utente, il collegamento ChatGPT e rimandato. La documentazione
ufficiale corrente ammette un endpoint Streamable HTTP HTTPS oppure Secure
MCP Tunnel per lo sviluppo. Per le risorse che richiedono un account serve
discovery di autenticazione compatibile: il bearer interno GAIA di 60 secondi
non costituisce un'integrazione OAuth pronta per ChatGPT.

Non pubblicare il server misto `/docs/`+`/data/`. Usare il server Data-only e
preparare autenticazione/consenso e scope prima del collegamento. Il tunnel
non e stato installato o avviato; nessun endpoint pubblico e stato creato.
L'account ChatGPT e la disponibilita delle funzioni devono essere verificati
al momento del collegamento. Riferimenti ufficiali consultati:

- https://developers.openai.com/plugins/deploy/connect-chatgpt
- https://developers.openai.com/api/docs/mcp
- https://platform.claude.com/docs/en/agents-and-tools/mcp-connector

## Validazione locale del 2026-10-01

Ambiente isolato `gaia-mcp-validation`: server Data Docker, gateway con router
Auth/MCP/console reali e database di login temporaneo interamente sintetico.
L'immagine lab aggiunge SDK MCP e Starlette 0.48.0 compatibile con FastAPI
0.118.0; non sostituisce l'immagine/servizio GAIA operativo. Il backend GAIA
esistente era gia unhealthy e non e stato riavviato.

Gateway `127.0.0.1:18769`, Data `127.0.0.1:18768`; accesso browser tramite
`http://127.0.0.1:18770/wiki/mcp/console`. Il proxy inoltra solo alle fixture
e a un frontend dev isolato su 13000, compilato in `/tmp`, senza alterare
il frontend operativo. Login di prova: `synthetic-mcp` /
`synthetic-login-password`, account amministratore solo nel DB temporaneo.

Config effimere: `/tmp/gaia-mcp-local-compose.yml`,
`/tmp/gaia-mcp-local-gateway.py`, `/tmp/gaia-mcp-local-nginx.conf`.
Credenziali provider esistenti lette senza stamparle; ambiente locale
`.env.mcp.local` ignorato da Git, permessi 0600. Solo il gateway riceve
credenziali provider; il server Data riceve esclusivamente la firma interna.
La rete host della prova conserva l'URL codex-lb loopback esistente; tutti
i listener della prova sono legati a loopback. Nessun documento reale.

```bash
docker compose --env-file .env.mcp.local -p gaia-mcp-validation \
  -f /tmp/gaia-mcp-local-compose.yml ps
docker compose --env-file .env.mcp.local -p gaia-mcp-validation \
  -f /tmp/gaia-mcp-local-compose.yml down
```

La prova live verifica login, discovery di 12 tool Data, gpt-reserve con
risultati/provenance sintetici, catalogo di 10 entita, storico condiviso con
stdio, revoca immediata del dominio Utenze e blocco dell'utente inattivo.
Lo stato dell'account sintetico viene ripristinato nel teardown. Report
minimizzato: `/tmp/gaia-mcp-console-live-final.log`. Le prove unitarie del
modello restano simulate; la prova Docker usa il provider reale.

Gate finali: 205 test MCP, 1494/1494 statement e 294/294 branch (100%);
122 regressioni Wiki. Frontend console/preview: 7 test, 72 statement,
43 branch e 19 funzioni (100%); navigazione: 12 test, 57 statement,
57 branch e 27 funzioni (100%). Browser Chromium con login e provider reali:
1 test passato, screenshot `/tmp/gaia-mcp-console-browser.png`.
Typecheck frontend, ESLint mirato, Ruff check/format MCP e Compose quiet
passano. Il ratchet mirato include MCP, router Wiki, pagine/componenti e
navigazione, contro merge-base `6b61fd27`: `findings: []`.

Metriche console e MCP: prima 31 file/114 callable/33 warning/0 error;
dopo 36 file/137 callable/41 warning/0 error, con nuove superfici sotto le
soglie error-level. Nessun refactoring hotspot o aggiornamento baseline.
I gate globali lint/ratchet falliscono su modifiche concorrenti estranee
(test Presenze, read model Ruolo, utenti, Elaborazioni e altri runtime
Presenze), preservate. Log `/tmp/gaia-mcp-console-lint-global.log` e
`/tmp/gaia-mcp-console-ratchet-global.log`; non sono gate globali superati.

Graphify via `make graphify-wiki-code GRAPHIFY_CODE_FLAGS=--force` e
`make graphify-frontend GRAPHIFY_CODE_FLAGS=--force`: aggiornamento AST-only
riuscito. Wiki: 937 nodi/2263 edge; frontend: 7235 nodi/17416 edge,
visualizzazione HTML omessa dal limite di dimensione. Nessuna estrazione
semantica di documenti al provider. Nessun commit, push o deploy operativo.
