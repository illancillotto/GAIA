# Release MCP isolata sul CED

## Stato verificato

Preparata release in `/home/ced/gaia-mcp/releases/20261006-644928ce/`.
Snapshot dei soli sorgenti versionati `backend/app` dal commit `644928ce`,
non copia del working tree o di chiavi/env locali. Dataset generato offline
con seed `gaia-v1`; database e manifest trasferiti con checksum verificati.
Client approvati vuoti: non autorizzano alcun client e non sono inventati.

L'immagine backend gia attiva e importabile ma manca `oauth_maintenance.py`:
non riutilizzarla direttamente come gateway aggiornato. Creata immagine
dedicata `gaia-mcp-lan:644928ce-20261006`, senza pip/apt o rebuild dello
stack, ereditando le dipendenze della base locale verificata
`sha256:9311573717e4eb05d986da7ee30ec2911e4a1df2ef609f41e481c2b7876cc60b`
e copiando lo snapshot applicativo. L'ID risultante e fissato nel `.env`
della release:
`sha256:49a2b53f861c0b686d593ef664244e4aa12ec3aaad96257bc906050fa57b0516`.
Il tag di build non deve essere considerato immutabile: Compose usa l'ID.

Il progetto `gaia-mcp-lan-20261006` avvia unicamente `connector`, con porta
host `127.0.0.1:8769`, network esterna gia esistente `gaia_default`,
filesystem readonly, cap drop ALL e no-new-privileges. Dataset e config
sono readonly; audit/OAuth hanno directory scrivibili separate. Il processo
non esegue migration o entrypoint del backend.

L'ambiente backend `/opt/gaia/.env` e letto solo sul server, mai trasferito
o stampato; `connector.env` applicato dopo impone OAuth `false`. Il preflight
ha verificato factory disattivata, import hardening e DataService sintetico
in container senza rete. Data e discovery su loopback rispondono 404.
Questo non e un gateway OAuth attivo, un HTTPS servito o un test autorizzato
tools/call. Non sono stati riavviati backend, frontend, Nginx o altri job;
gli hotfix in `/opt/gaia` non sono stati modificati.

## Template e riproducibilita

`config/mcps/lan-release/` contiene Dockerfile, Compose dedicato e default
connector disattivato. La base deve essere scelta esplicitamente e verificata
prima della build; con BuildKit usare un tag locale della base e confrontare
l'ID, non `FROM sha256:...`, che viene interpretato come repository remoto.
Lo snapshot `backend-app/` e un input di build generato, non versionato qui.
Dockerfile cambia soltanto i sorgenti applicativi della nuova immagine.
Non usare questa tecnica per aggiornare implicitamente il backend operativo.

Variabili Compose obbligatorie: `GAIA_MCP_RELEASE_IMAGE` (ID immagine),
`GAIA_MCP_BACKEND_ENV_FILE` (env backend server), `GAIA_MCP_NETWORK`
(rete Docker esistente). Renderizzare con `config --quiet`, mai stampare
`config` completo in presenza di env segreti. Le route Nginx/Compose
originali sono copiate nella directory config solo come materiale di
preparazione; non sono installate nel proxy e non vanno incluse ciecamente
nel Nginx host, perche usano network/resolver e variabili del proxy Docker.

Test: `make test-mcp-lan-release QUALITY_PYTHON=backend/.venv/bin/python`.
Quattro contratti verificano config Docker Compose reale: unico servizio,
bind loopback, override fail-closed rispetto all'env backend, isolamento
volumi/network, assenza di entrypoint migration e rifiuto input mancanti.
Ruff e check-format passati. Nessun file runtime Python modificato.
Riverifica OAuth 31 test e connector 43 test, inclusa chiamata TCP/revoca:
entrambi PASS, coverage full-file 100% statement/branch nei rispettivi gate.
Gateway HTTP/HTTPS: 67 test PASS senza skip, inclusi proxy TLS, redirect,
body/rate limit e isolamento route; test reali con Docker locale, non
certificazione di un HTTPS gia attivo sul CED.

## Client richiesti e limiti

Richiesti Claude Code/Desktop e Codex/ChatGPT Desktop. I client locali
possono usare lo stdio; per il gateway HTTP servono client_id/callback
effettivi e supporto preregistrazione del client. Nessuna registration
dinamica implementata o autorizzata nel gateway GAIA.

Codex locale ora configurato con `gaia-synthetic` tramite CLI ufficiale,
Python del repository, database sintetico e tre scope Data. Backup privato
prima della modifica; configurazione restante verificata semanticamente
invariata (ripristinata una conversione automatica estranea del timeout).
Claude Code aveva gia la voce project-local; Claude Desktop aveva gia la
voce equivalente. Nessun token OAuth o documento reale aggiunto ai profili.
Smoke SDK con la configurazione reale Codex: initialize, tools/list e
tools/call search_subjects PASS con due risultati sintetici e provenance.
Non e una chiamata dal modello Codex/Claude Desktop: l'accettazione nelle
app resta da eseguire. Riavviare/aprire nuova sessione per caricare il profilo.

La documentazione OpenAI descrive stdio/HTTP e OAuth per Codex. Per
ChatGPT descrive un endpoint HTTPS pubblico oppure Secure MCP Tunnel per
server privati: non assumere che l'app Desktop apra direttamente `gaia.lan`.
Tunnel, associazione workspace, consenso e invio dei soli dati consentiti
richiedono decisione esplicita; nessun tunnel o ingresso Internet attivato.
Fonti ufficiali consultate il 2026-10-06:
- https://developers.openai.com/codex/mcp
- https://developers.openai.com/apps-sdk/deploy/connect-chatgpt

## Attivazione e rollback

Restano definizione client/callback, trust del client effettivo, frontend
consenso aggiornato, HTTPS e integrazione Nginx host con sudo/backup/test.
Non impostare OAuth true prima di questi prerequisiti. Non usare il token
di login GAIA come bearer permanente del client MCP.

Rollback della sola preparazione avviata, senza toccare lo stack GAIA:

```bash
cd /home/ced/gaia-mcp/releases/20261006-644928ce
docker compose -p gaia-mcp-lan-20261006 -f compose.yml stop connector
```

Conservare release, database e certificati per audit; nessuna cancellazione
automatica. Riepilogo corrente: `CURRENT_STATUS_2026-10-06.md`.
