# GAIA
## Gestione Apparati Informativi e Accessi
### Piattaforma IT governance — Consorzio di Bonifica dell'Oristanese

> Regola repository
> Backend unico, frontend unico, database unico. Nuovo codice backend di dominio va nel monolite modulare sotto `backend/app/modules/<modulo>/`.

## Cos'è GAIA

GAIA centralizza la governance IT del Consorzio in domini applicativi
integrati, accessibili da un'unica interfaccia dopo il login.

Evoluzione pianificata:

- `GAIA NAS Control` e `GAIA Rete` convergeranno in un unico entrypoint frontend `GAIA CED`
- nella prima fase la convergenza riguarda soprattutto home, sidebar, route frontend e navigazione
- i backend `accessi` e `network` restano separati finche non verra approvata un'eventuale fase successiva

## Quick Start

1. Copia `.env.example` nel file ambiente locale richiesto dal tuo setup.
2. Avvia lo stack con `docker compose up -d`.
3. Verifica il backend con `GET /health` e il frontend dalla root applicativa esposta da Nginx.
4. Usa `make` per shell, log, rebuild e target di manutenzione repository.

## Documentazione

- `docs/` contiene la documentazione di piattaforma.
- `domain-docs/` contiene la documentazione funzionale per dominio.
- `modules/accessi/docs/` ospita documenti scaffold legacy mantenuti per compatibilità test/tooling.

## I quattro moduli

Nota storica: alcuni test di scaffold usano ancora il naming originario "quattro moduli".
Il repository oggi copre un perimetro più ampio, descritto nella sezione aggiornata sotto.

## I cinque moduli

### GAIA Accessi — NAS Audit
Audit completo degli accessi al NAS Synology: utenti, gruppi, cartelle condivise,
permessi effettivi e workflow di review per i responsabili di settore.
Stato: completato e funzionante.

### GAIA Rete — Network Monitor
Monitoraggio della rete LAN: scansione dispositivi, mappa interattiva per piano,
snapshot storici, diff tra scansioni, dettaglio dispositivi e alert per
dispositivi non registrati o per dispositivi conosciuti assenti dalla rete oltre soglia.
Stato: operativo avanzato.

### GAIA CED — Convergenza pianificata
Modulo aggregatore pianificato per unificare `NAS Control` e `Rete` in un solo
entrypoint infrastrutturale. Nella prima fase riusa frontend, backend e permessi
esistenti dei moduli `accessi` e `network`.
Stato: pianificato.

### GAIA Inventario — IT Inventory
Registro centralizzato dei dispositivi IT: anagrafica, garanzie, assegnazioni,
import CSV e collegamento con i dati di rete.
Stato: in sviluppo.

### GAIA Catasto — Servizi AdE
Automazione delle visure catastali dal portale SISTER: upload batch CSV/XLSX,
worker Playwright separato, gestione CAPTCHA, archivio PDF e download ZIP.
Il runtime supporta sia visure per immobile sia visure per soggetto PF/PNF,
con esiti diagnostici distinti `completed`, `failed`, `skipped`, `not_found`.
Il worker SISTER usa ora un pool concorrente per credenziale attiva, con
retry differiti su errori transitori, cooldown per lock/timeout/HTTP 500 e
metrica runtime aggregata esposta alla dashboard `/elaborazioni`.
Il dominio include anche una Fase 1 territoriale con import Capacitas,
distretti, particelle, anomalie, storico import, ricerca anagrafica singola/massiva
e dettaglio batch su base PostGIS.
I processi lunghi monitorabili da frontend sono standardizzati su job persistenti
presi in carico dal container `elaborazioni-worker`, invece di dipendere da
sessioni web o task effimeri nel processo API.
Nel perimetro Capacitas il worker esegue sync progressiva particelle, batch
Terreni e import `Storico anagrafica`, con monitor frontend, cleanup stale e
auto-resume quando previsto dal payload del job.
Stato: operativo avanzato sul perimetro corrente, con hardening backend/frontend e copertura E2E dei flussi principali Catasto.

### GAIA Utenze — Anagrafica soggetti
Registro centralizzato dei soggetti del Consorzio, con import da archivio NAS,
classificazione documentale e ricerca anagrafica.
Stato: in consolidamento.

## Stack tecnologico

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- Frontend: Next.js, React, TypeScript, TailwindCSS, TanStack Table
- Infrastructure: Docker, Docker Compose, Nginx
- CI: GitHub Actions

Il frontend condiviso della piattaforma vive in `frontend/`.

## Struttura repository
```text
GAIA/
├── docs/                    ← documentazione generale di piattaforma
│   ├── ARCHITECTURE.md
│   ├── PRD.md
│   └── ...
├── domain-docs/             ← documentazione funzionale per dominio
│   ├── accessi/docs/
│   ├── ced/docs/
│   ├── catasto/docs/
│   ├── inventory/docs/
│   ├── network/docs/
│   ├── wiki/docs/           ← Wiki Agent (Milestone 9)
│   └── utenze/docs/
├── frontend/
│   └── src/app/
│       ├── nas-control/
│       ├── anagrafica/
│       ├── utenze/
│       ├── network/
│       ├── inventory/
│       └── catasto/
├── modules/
│   └── elaborazioni/
│       └── worker/
├── backend/
│   ├── app/
│   │   ├── modules/
│   │   │   ├── core/
│   │   │   ├── accessi/
│   │   │   ├── anagrafica/
│   │   │   ├── utenze/
│   │   │   ├── network/
│   │   │   ├── inventory/
│   │   │   └── catasto/
│   │   └── ...
│   ├── alembic/
│   └── tests/
├── docker-compose.yml
├── docker-compose.override.yml
├── nginx/
├── scripts/
├── Makefile
└── .env.example
```

## Convenzioni repository

- `domain-docs/` contiene PRD, prompt, execution plan e progress dei domini funzionali.
- `backend/app/modules/<modulo>/` contiene il codice backend runtime dei moduli.
- `frontend/src/app/<modulo>/` contiene il codice frontend runtime dei moduli.
- `modules/` non e piu il contenitore dei moduli applicativi; resta disponibile solo per asset tecnici specifici, come `modules/elaborazioni/worker/`.
- l'account NAS `svc_naap` resta un identificatore tecnico legacy ancora valido e non va rinominato durante i refactor del naming progetto.
- `AGENTS.md` nella root contiene regole operative repository-level per gli agenti, incluse le policy Graphify.
- `.codex/skills/gaia-graphify-maintenance/` contiene la skill locale per mantenere aggiornati i grafi Graphify nei corpus supportati.

## Graphify

Graphify e utile in GAIA per orientarsi su domini grandi come `catasto`, dove documentazione e codice sono entrambi ricchi ma non sempre perfettamente allineati.

Se usi Graphify contro `codex-lb` invece che contro OpenAI diretto, applica prima la patch locale:

- `make graphify-patch-openai-base-url`

Questa patch rende il backend `openai` di Graphify compatibile con `OPENAI_BASE_URL`, cosi `.env.graphify` puo puntare a un proxy OpenAI-compatible come `codex-lb`.

Uso consigliato:

- `make graphify-catasto-code`
  genera o aggiorna il grafo del codice backend `catasto`
- `make graphify-catasto-docs`
  genera o aggiorna il grafo della documentazione `catasto`
- `make graphify-catasto-query Q="domanda"`
  interroga il grafo backend `catasto`
- `make graphify-presenze-code`
  genera o aggiorna il grafo del codice backend `presenze`
- `make graphify-presenze-docs`
  genera o aggiorna il grafo della documentazione del dominio `presenze` nel corpus docs storico del modulo
- `make graphify-presenze-query Q="domanda"`
  interroga il grafo backend `presenze`
- `make graphify-inaz-code`
  alias legacy di `make graphify-presenze-code`
- `make graphify-inaz-docs`
  alias legacy di `make graphify-presenze-docs`
- `make graphify-inaz-query Q="domanda"`
  alias legacy di `make graphify-presenze-query Q="domanda"`
- `make graphify-network-code`
  genera o aggiorna il grafo del codice backend `network`
- `make graphify-network-docs`
  genera o aggiorna il grafo della documentazione `network`
- `make graphify-network-query Q="domanda"`
  interroga il grafo backend `network`
- `make graphify-operazioni-code`
  genera o aggiorna il grafo del codice backend `operazioni`
- `make graphify-operazioni-docs`
  genera o aggiorna il grafo della documentazione `operazioni`
- `make graphify-operazioni-query Q="domanda"`
  interroga il grafo backend `operazioni`
- `make graphify-organigramma-code`
  genera o aggiorna il grafo del codice backend `organigramma`
- `make graphify-organigramma-docs`
  genera o aggiorna il grafo della documentazione `organigramma`
- `make graphify-organigramma-query Q="domanda"`
  interroga il grafo backend `organigramma`
- `make graphify-riordino-code`
  genera o aggiorna il grafo del codice backend `riordino`
- `make graphify-riordino-docs`
  genera o aggiorna il grafo della documentazione `riordino`
- `make graphify-riordino-query Q="domanda"`
  interroga il grafo backend `riordino`
- `make graphify-ruolo-code`
  genera o aggiorna il grafo del codice backend `ruolo`
- `make graphify-ruolo-docs`
  genera o aggiorna il grafo della documentazione `ruolo`
- `make graphify-ruolo-query Q="domanda"`
  interroga il grafo backend `ruolo`
- `make graphify-utenze-code`
  genera o aggiorna il grafo del codice backend `utenze`
- `make graphify-utenze-docs`
  genera o aggiorna il grafo della documentazione `utenze`
- `make graphify-utenze-query Q="domanda"`
  interroga il grafo backend `utenze`
- `make graphify-wiki-code`
  genera o aggiorna il grafo del codice backend `wiki`
- `make graphify-wiki-docs`
  genera o aggiorna il grafo della documentazione `wiki`
- `make graphify-wiki-query Q="domanda"`
  interroga il grafo backend `wiki`
- `make graphify-backend`
  genera o aggiorna il grafo del backend modulare
- `make graphify-backend-query Q="domanda"`
  interroga il grafo backend aggregato
- `make graphify-frontend-query Q="domanda"`
  interroga il grafo frontend aggregato
- `make graphify-docs-query Q="domanda"`
  interroga il grafo documentale aggregato
- `make graphify-query Q="come funziona il flusso anomalie catasto"`
  interroga il grafo gia presente nella directory corrente

Scorciatoie utili:

- `make graphify-refresh-core-code`
  aggiorna tutti i grafi codice dei moduli core coperti
- `make graphify-refresh-core-docs`
  aggiorna tutti i grafi docs dei domini core coperti
- `make graphify-refresh-core`
  aggiorna in sequenza code + docs per tutti i corpus core

Copertura core attuale:

| Dominio | Code target | Docs target | Query target |
|---|---|---|---|
| Catasto | `graphify-catasto-code` | `graphify-catasto-docs` | `graphify-catasto-query` |
| Presenze | `graphify-presenze-code` | `graphify-presenze-docs` | `graphify-presenze-query` |
| Network | `graphify-network-code` | `graphify-network-docs` | `graphify-network-query` |
| Operazioni | `graphify-operazioni-code` | `graphify-operazioni-docs` | `graphify-operazioni-query` |
| Organigramma | `graphify-organigramma-code` | `graphify-organigramma-docs` | `graphify-organigramma-query` |
| Riordino | `graphify-riordino-code` | `graphify-riordino-docs` | `graphify-riordino-query` |
| Ruolo | `graphify-ruolo-code` | `graphify-ruolo-docs` | `graphify-ruolo-query` |
| Utenze | `graphify-utenze-code` | `graphify-utenze-docs` | `graphify-utenze-query` |
| Wiki | `graphify-wiki-code` | `graphify-wiki-docs` | `graphify-wiki-query` |

Regole pratiche:

- ogni target esegue Graphify dentro il corpus di riferimento, cosi ogni modulo mantiene il proprio `graphify-out/`
- i target `*-code` usano estrazione strutturale senza LLM e funzionano anche senza API key
- i target `*-docs` usano estrazione semantica e richiedono una API key supportata da Graphify
- se `.env.graphify` usa `OPENAI_BASE_URL`, su una installazione Graphify standard devi prima applicare `make graphify-patch-openai-base-url`
- per interrogare un grafo specifico puoi entrare nella directory del corpus e usare `graphify query "..."`, oppure usare i target `graphify-*-query`
- non lanciare Graphify sulla root grezza del repository senza filtri: dipendenze, cache, runtime-data e artefatti inquinano il corpus
- il file `.graphifyignore` definisce le esclusioni standard del progetto
- usare Graphify soprattutto per onboarding, analisi impatto e verifica drift tra docs e codice

## Architettura backend attuale

Il backend di GAIA e un **monolite modulare**: un solo servizio FastAPI,
un solo database PostgreSQL e un solo set di migration Alembic.

La directory fisica del backend e:
- `backend/`

La struttura logica canonica del codice backend e invece:
- `backend/app/modules/core`
- `backend/app/modules/accessi`
- `backend/app/modules/anagrafica`
- `backend/app/modules/utenze`
- `backend/app/modules/inventory`
- `backend/app/modules/network`
- `backend/app/modules/catasto`

I package storici fuori da `app/modules/` restano disponibili come layer di compatibilita.
Per il dominio anagrafico convivono ancora namespace runtime `anagrafica` e `utenze`;
la documentazione di dominio fa riferimento a `domain-docs/utenze/`.

## Quick Start

1. Copia il file ambiente:
   `cp .env.example .env`
   Il file ambiente canonico del repository e `/.env`; i servizi Docker e il backend leggono da questa source of truth.
2. Avvia lo stack:
   `make up`
3. Rebuild quando cambi dipendenze o entrypoint:
   `make rebuild`
4. Esegui le migrazioni:
   `make migrate`
5. Crea l'admin iniziale:
   `make bootstrap-admin`
   Il backend ora esegue anche un bootstrap admin idempotente all'avvio usando
   `BOOTSTRAP_ADMIN_*`; il comando resta utile per forzare riallineamento delle
   credenziali bootstrap su stack gia avviati.
   All'avvio viene anche riallineato il catalogo `sections` dei moduli applicativi,
   cosi `auth/my-permissions` e i controlli `require_section(...)` restano coerenti
   anche su database locali inizializzati prima dell'introduzione di nuovi moduli.
6. Carica i dati seed:
   `make bootstrap-domain`
   Il comando inizializza il seed del dominio audit e il dizionario `catasto_comuni`.
7. Genera e configura la chiave vault Catasto in `.env`:
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   La stessa chiave deve essere condivisa tra `backend` e `elaborazioni-worker`.
8. Accedi all'applicazione:
   `http://localhost:8080`

## Inviti utente e Google Login

Il modulo `Utenti GAIA` supporta ora:

- creazione utente con invio mail di attivazione
- attivazione password tramite link monouso
- login classico username/password
- login Google OAuth in modalita test

Variabili env rilevanti:

- `FRONTEND_PUBLIC_URL`: base URL usata nei link di attivazione quando la request non fornisce un origin pubblico affidabile
- `USER_INVITE_EXPIRE_HOURS`: scadenza link invito/attivazione
- `SMTP_ENABLED`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS`, `SMTP_USE_SSL`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`
- `GOOGLE_OAUTH_ENABLED`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`

Note operative:

- in locale, se il frontend e raggiunto via IP/LAN e non via `localhost`, i link mail usano in priorita `Origin` o `Referer` della request di invio
- con Gmail e consigliato usare una app password dedicata sull'account mittente
- con dominio locale/non verificabile, Google OAuth va mantenuto in test mode e limitato agli utenti di prova autorizzati nella Google Cloud Console
- il modulo `Elaborazioni` e visibile ed accessibile solo ai profili `super_admin`; utenti `admin` e `operator` ricevono filtro gia nella navigazione frontend oltre al blocco backend

### Build frontend pulito

Quando il frontend mostra comportamenti incoerenti o il build Next fallisce su cache stale di `.next`, usare uno di questi due percorsi:

- locale dentro `frontend/`:
  `npm run build:clean`
- stack Docker del repository:
  `./scripts/frontend_clean_build.sh`

Il comando Docker ferma temporaneamente il servizio `frontend`, esegue un build pulito in un container effimero e poi rialza il servizio.

### Trasferimento immagini Docker verso server CED

Per copiare una o piu immagini Docker locali dal PC di sviluppo al server CED senza passare da un registry, usare:

- `./scripts/copy-docker-image-to-ced.sh --ssh serverCed --service backend --service frontend`
- `./scripts/copy-docker-image-to-ced.sh --ssh serverCed --image gaia-backend:latest`
- `./scripts/copy-docker-image-to-ced.sh --ssh serverCed --service backend --copy-env --remote-env-path /opt/gaia/.env`

Lo script:

- risolve i servizi Compose come immagini `<project>-<service>:latest` con project name default `gaia`
- esporta l'immagine con `docker image save`
- comprime l'archivio in `tar.gz`
- lo trasferisce via `scp`
- sul server esegue `docker load` e rimuove il file temporaneo
- opzionalmente copia anche il file `.env` del repository sul path remoto desiderato

Prerequisiti:

- accesso SSH gia configurato verso il server CED, ad esempio tramite alias `serverCed`
- Docker disponibile sia sulla macchina locale sia sul server remoto
- immagine gia presente localmente, ad esempio dopo `docker compose build`
- se usi `--copy-env`, verifica che il file `.env` locale sia quello corretto per il server CED

### Deploy CED verso `gaia.lan`

Per deployare lo stack GAIA su server CED con virtual host dedicato `gaia.lan`, usare:

- `./scripts/deploy-ced-gaia.sh`

### Sync persistente GAIA -> Gate Mobile Gateway

Per il job automatico outbound verso il gateway pubblico usare il runbook:

- [domain-docs/operazioni/docs/GAIA_GATE_MOBILE_SYNC_RUNBOOK.md](/home/cbo/CursorProjects/GAIA/domain-docs/operazioni/docs/GAIA_GATE_MOBILE_SYNC_RUNBOOK.md)

File env di riferimento per il deploy:

- example tracciato: `.env.production.example`
- file reale locale da usare per il deploy: `.env.production`

Azioni supportate:

- `DEPLOY_ACTION=deploy`: build locale immagini GAIA, copia progetto + immagini + `.env`, `docker compose up -d`, configurazione nginx host se disponibile, smoke test finale
- `DEPLOY_ACTION=nginx`: configura solo il virtual host host-level `gaia.lan -> 127.0.0.1:$GAIA_PROD_NGINX_PORT`
- `DEPLOY_ACTION=smoke`: verifica container e endpoint remoti senza rilanciare il deploy
- smoke operativo console bypass locale: `make smoke-network-vpn-bypass`
  - include anche un ingest syslog Sophos sintetico e la verifica che `network_firewall_events.max(observed_at)` avanzi davvero
  verifica `summary`, `arp-timeline`, `detection-watchlist` e `tracking` tramite login admin sul proxy `:8080`

Esempi:

- `./scripts/deploy-ced-gaia.sh`
- `DEPLOY_ACTION=smoke CED_SSH_HOST=serverCed GAIA_DOMAIN=gaia.lan ./scripts/deploy-ced-gaia.sh`
- `DEPLOY_ACTION=nginx CONFIGURE_HOST_NGINX=yes ./scripts/deploy-ced-gaia.sh`

Variabili operative principali:

- `CED_SSH_HOST`: alias SSH del server, default `serverCed`
- `CED_PROJECT_DIR`: directory remota progetto, default `/opt/gaia`
- `ENV_FILE`: file env locale da trasferire, default `.env.production`
- `GAIA_DOMAIN`: hostname pubblico, default `gaia.lan`
- `GAIA_MOBILE_DOMAIN`: hostname mobile opzionale, default `gaia-mobile.lan`
- `GAIA_PROD_NGINX_PORT`: porta host usata dallo stack Docker GAIA, default `8080`
- `RELEASE_ID`: release identifier, default `YYYYmmdd-HHMMSS-<gitsha>`
- `RELEASE_RETENTION_COUNT`: quante release mantenere sul server in `releases/`, default `3`
- `ALLOW_NON_PRODUCTION_ENV`: default `no`; se `no`, il deploy rifiuta `.env` con `APP_ENV` diverso da `production`
- `CONFIGURE_HOST_NGINX`: `auto|yes|no`
- `POSTGRES_VOLUME_NAME`: volume Docker da usare per i dati Postgres sul server CED; se assente usa `gaia_postgres_data`

Maintenance mode:

- `./scripts/maintenance-on.sh`: abilita la pagina statica "Deploy in corso" servita da `nginx`
- `./scripts/maintenance-off.sh`: disabilita la pagina di maintenance e ripristina il routing normale
- `DEPLOY_ACTION=deploy` abilita automaticamente la maintenance prima del restart dello stack e la disabilita prima degli smoke test finali

Modello operativo:

- il server CED viene trattato come ambiente runtime di produzione
- la build delle immagini avviene localmente sulla macchina da cui lanci lo script
- il deploy CED usa esplicitamente solo `docker-compose.yml` e non carica `docker-compose.override.yml`
- il server remoto riceve artefatti gia buildati e li avvia con `docker compose up -d --no-build`
- il file locale `.env.production` viene copiato sul server sia come `.env` sia come `.env.production`
- il deploy sovrascrive quindi ad ogni esecuzione il file env runtime remoto partendo da quello locale selezionato in `ENV_FILE`
- sul server `.env` e il file runtime usato da Docker Compose; `.env.production` e la copia esplicita del file production
- prima dell'avvio remoto il deploy verifica che `docker-compose.yml` risolva davvero `postgres_data` verso `POSTGRES_VOLUME_NAME`; se trova un mismatch si ferma invece di rischiare di agganciare il volume sbagliato
- ogni deploy salva un manifest minimale di release in `releases/gaia-release-<release_id>.txt` e aggiorna `current-release.txt`
- il progetto compresso esclude cache, virtualenv, backup e dump locali per evitare archivi enormi e saturazione disco sul server
- a fine deploy viene applicata una retention automatica sugli artefatti `gaia-project-*`, `gaia-images-*` e `gaia-release-*`

Il deploy normalizza automaticamente alcune variabili nel `.env` remoto:

- `NGINX_PORT=$GAIA_PROD_NGINX_PORT`
- `NEXT_PUBLIC_API_BASE_URL=/api`
- `BACKEND_CORS_ORIGINS` include `http://gaia.lan` se assente
- `BACKEND_CORS_ORIGINS` include anche `https://gaia.lan` e, se configurato, `http(s)://gaia-mobile.lan`

Checklist minima del `.env` di produzione prima del deploy:

- `APP_ENV=production`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `BOOTSTRAP_ADMIN_USERNAME`
- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_PASSWORD`
- `CREDENTIAL_MASTER_KEY`
- `POSTGRES_VOLUME_NAME` coerente con il volume dati reale del server; su `serverCed` il volume operativo corrente e `gaia_postgres_recovered_data`
- eventuali credenziali NAS/PDND/ANPR realmente richieste dall'ambiente
- se vuoi fallback Wiki locale quando `codex-lb` non risponde:
  `WIKI_AGENT_FALLBACK_ENABLED=true`, `WIKI_AGENT_HOST_HOME=/home/ced`, `WIKI_AGENT_CLI_PATH=/home/ced/.local/bin/agent`

Note operative:

- `gaia.local` resta un dominio di sviluppo locale; per il server CED il target operativo e `gaia.lan`
- lo script non modifica DNS o router: `gaia.lan` deve gia risolvere verso il server corretto
- nell'assetto corrente `gaia.lan`, `teti.lan` e `gaia-mobile.lan` sono gestiti a livello infrastrutturale come voci host DNS su Sophos
- in particolare `gaia.lan` e pubblicato nel DNS interno Sophos verso `192.168.1.110`; se vuoi usare `gaia.lan` in locale devi fare un override esplicito su quella macchina, ad esempio via `/etc/hosts`
- se nginx host non e installato o `sudo` richiede password, lo script stampa i passaggi manuali da eseguire sul server
- il deploy fallisce se mancano env critiche o se `GAIA_DOMAIN` punta a un hostname `.local`
- il deploy fallisce anche se il compose remoto non allinea `postgres_data` al `POSTGRES_VOLUME_NAME` richiesto dall'env
- dopo le normalizzazioni remote, lo script riallinea `.env.production` a `.env` e prova ad applicare `chmod 600` a entrambi
- il container `backend` puo usare la CLI locale `agent` del server host come fallback Wiki montando `${WIKI_AGENT_HOST_HOME}` sugli stessi path assoluti dentro al container

### Pull database dal CED verso locale

Per importare l'intero database del server CED nel database locale usare:

- `CONFIRM_PULL=yes ./scripts/pull-ced-db-to-local.sh`

Lo script:

- esegue un backup preventivo completo del DB locale
- produce un dump del DB remoto sul server CED
- scarica il dump in `./backups/db`
- ferma i servizi locali che usano PostgreSQL
- ricrea il DB locale e applica il restore completo
- riavvia lo stack ed esegue smoke test opzionali

Variabili operative principali:

- `LOCAL_ENV_FILE`: env locale usato per il restore, default `.env`
- `REMOTE_ENV_FILE`: env remoto letto sul server CED, default `.env`
- `LOCAL_RECREATE_DB`: `yes|no`, default `yes`
- `RUN_SMOKE_TEST`: `yes|no`, default `yes`
- `BACKUP_RETENTION_COUNT`: numero backup/dump da mantenere per pattern, default `2`

Nota importante:

- se `CREDENTIAL_MASTER_KEY` locale e remota differiscono, le credenziali cifrate importate dal CED potrebbero non essere riutilizzabili in locale senza reinserimento

### Sync database slim dal CED verso locale

Per sincronizzare solo le tabelle operative che risultano cambiate tra CED e locale usare:

- `CONFIRM_PULL=yes ./scripts/pull-ced-db-to-local-slim.sh`

Lo script slim:

- esegue comunque un backup completo preventivo del DB locale
- confronta firme remoto/locale tabella per tabella
- esporta dal CED solo le tabelle cambiate
- applica in locale un restore `--data-only` con `TRUNCATE ... RESTART IDENTITY CASCADE`

Perimetro default della sync slim:

- utenti applicativi, sezioni, permessi, inviti
- credenziali e configurazioni operative leggere
- job, run, selection e metadati di orchestrazione
- esclusi di default i dataset bulk e i log firewall voluminosi

Variabili operative principali:

- `SYNC_TABLES_CSV`: override dell'elenco tabelle `schema.nome` separate da virgole
- `SIGNATURE_ROW_HASH_LIMIT`: soglia righe per usare un hash completo sulle tabelle senza timestamp, default `20000`

Nota operativa:

- la sync slim non e un merge record-by-record: per ogni tabella cambiata sostituisce in locale il contenuto completo della tabella remota selezionata

### Export database su NAS

Per pubblicare un dump PostgreSQL locale sul NAS usare:

- `./scripts/export-gaia-db-to-nas.sh`
- `make backup-db-to-nas`

Lo script:

- genera prima un dump locale con la stessa logica di `backup-gaia-db.sh`
- usa le credenziali `NAS_*` gia presenti nell'env per aprire una sessione SSH/SFTP
- carica dump e manifest JSON in una directory di staging sul NAS
- verifica il checksum SHA-256 lato NAS prima della pubblicazione finale
- sposta il dump in modo atomico sotto `NAS_DB_BACKUP_ROOT/archives/YYYY/MM`
- aggiorna `latest.json` e applica retention remota sui backup piu vecchi

Variabili operative principali:

- `NAS_DB_BACKUP_ROOT`: root remota dedicata ai dump DB, default `/volume1/Backups/GAIA/db`
- `NAS_DB_BACKUP_RETENTION_COUNT`: numero backup da mantenere sul NAS, default `14`
- `NAS_PRIVATE_KEY_PATH` oppure `NAS_PASSWORD`: autenticazione NAS

Note operative:

- il transfer usa Paramiko via `python3` locale, quindi l'ambiente che esegue lo script deve avere le dipendenze backend installate
- il dump viene verificato con checksum sia in locale sia sul NAS; se il NAS non espone `sha256sum`, `shasum` o `openssl`, l'export fallisce

### Import database dal NAS verso locale

Per ripristinare in locale l'ultimo dump presente sul NAS usare:

- `CONFIRM_NAS_IMPORT=yes ./scripts/import-gaia-db-from-nas.sh`
- `CONFIRM_NAS_IMPORT=yes make restore-db-from-nas`

Lo script:

- esegue un backup preventivo completo del DB locale
- scarica `latest.json` dal NAS, poi dump e manifest associati
- verifica checksum e dimensione del dump scaricato
- ferma i servizi locali che usano PostgreSQL
- ricrea il DB locale e applica il restore completo
- riavvia lo stack ed esegue smoke test opzionali

Opzioni principali:

- `--manifest-path`: forza un manifest remoto specifico invece di usare `latest.json`
- `--recreate-db yes|no`: controlla se droppare e ricreare il DB prima del restore
- `--run-smoke-test yes|no`: abilita o disabilita i controlli finali HTTP

### Backup notturno automatico Elaborazioni

Il backend registra anche un job automatico nel pannello Elaborazioni che crea snapshot DB notturni sul NAS:

- chiave auto-job: `elaborazioni_db_backup`
- schedule default: `5 2 * * *`
- timezone default: `Europe/Rome`
- retention default: ultimi `5` snapshot

Variabili principali:

- `ELABORAZIONI_DB_BACKUP_ENABLED=true|false`
- `ELABORAZIONI_DB_BACKUP_CRON`, default `5 2 * * *`
- `ELABORAZIONI_DB_BACKUP_TIMEZONE`, default `Europe/Rome`
- `ELABORAZIONI_DB_BACKUP_RETENTION_COUNT`, default `5`
- `ELABORAZIONI_DB_BACKUP_REMOTE_ROOT`, default `/volume1/Backups/GAIA/db`

Nota operativa:

- il container backend deve essere rebuildato dopo l'update per includere `pg_dump` (`postgresql-client`)

### Dominio locale `gaia.local`

Per allineare l'accesso locale a un hostname stabile invece di usare solo `localhost`, usare:

- `./scripts/setup-local-domain.sh`

Lo script:

- registra `gaia.local` in `/etc/hosts` verso `127.0.0.1`
- crea `.env` da `.env.example` se manca
- aggiorna `BACKEND_CORS_ORIGINS` nel file ambiente locale includendo `http://gaia.local` e `http://gaia.local:8080`

Se per esigenze operative devi usare proprio `gaia.lan` anche in locale, il repository supporta anche questa modalita:

- `./scripts/setup-local-domain.sh --domain gaia.lan --ip 127.0.0.1 --env-file .env --port 8080`

Questo override vale solo sulla macchina locale e forza `gaia.lan` a puntare allo stack Docker locale invece che al server CED esposto dal DNS Sophos.

Con la configurazione default del repository l'app resta raggiungibile su:

- `http://gaia.local:8080`

Se sullo stesso host convivono anche altri stack locali, ad esempio `teti.local` e `gaia-mobile.local`, la logica corretta e mantenere porte host distinte per ogni progetto:

- `GAIA`: `http://gaia.local:8080`
- `TETI`: `http://teti.local:8085`
- `GAIA-mobile`: `http://gaia-mobile.local:5173`

Con stack Docker separati non e possibile pubblicare tutti direttamente sulla stessa porta host `80`. Il dominio dedicato aiuta a rendere stabile l'accesso, ma la distinzione resta fatta dalla porta.

Usare `http://gaia.local` senza porta ha senso solo in uno di questi casi:

- GAIA e l'unico servizio esposto su quel server
- esiste un reverse proxy condiviso davanti a tutti gli stack, con routing per `Host` verso porte/container interni diversi

### Gateway locale condiviso per `gaia.local`, `teti.local`, `gaia-mobile.local`

Nel contesto locale in cui i tre stack convivono sullo stesso host, il repository include uno stack dedicato di reverse proxy:

- [docker-compose.local-gateway.yml](/home/cbo/CursorProjects/GAIA/docker-compose.local-gateway.yml:1)
- [nginx/local-dev-gateway.conf](/home/cbo/CursorProjects/GAIA/nginx/local-dev-gateway.conf:1)

Routing previsto:

- `gaia.local` -> `127.0.0.1:8080`
- `teti.local` -> `127.0.0.1:8085`
- `gaia-mobile.local` -> `127.0.0.1:5173`

Bootstrap rapido:

- `./scripts/setup-local-dev-gateway.sh`
- `./scripts/setup-local-dev-gateway.sh --use-lan-domains`
- `./scripts/setup-local-dev-gateway.sh --skip-hosts`

Il comando:

- aggiunge i tre hostname a `/etc/hosts`
- avvia il reverse proxy condiviso su porta host `80`
- lascia invariati gli stack applicativi esistenti e le loro porte interne/esterne

Con `--use-lan-domains` aggiunge anche:

- `gaia.lan`
- `teti.lan`
- `gaia-mobile.lan`

verso `127.0.0.1` sulla sola macchina locale, cosi puoi usare in sviluppo gli stessi hostname operativi del CED senza uscire verso il server remoto.

La variante `--skip-hosts` avvia solo il gateway Docker e va usata quando i mapping dei domini sono gia presenti oppure quando vuoi gestire `/etc/hosts` manualmente.

In alternativa:

- `make local-gateway-up`
- `make local-gateway-down`

Prerequisiti operativi:

- `GAIA` attivo su `:8080`
- `TETI` attivo su `:8085`
- `GAIA-mobile` attivo su `:5173`

Con il gateway attivo, gli URL diventano:

- `http://gaia.local`
- `http://teti.local`
- `http://gaia-mobile.local`

Nota operativa Docker:
- lo stack Compose forza temporaneamente `build.network: host` per il solo servizio `frontend`, per aggirare timeout DNS intermittenti del builder Docker verso `registry.npmjs.org`
- il workaround e intenzionale ma non definitivo; l'obiettivo a regime e spostare la correzione sul daemon Docker host con DNS espliciti e rimuovere la dipendenza da `build.network: host`

### Test frontend

- smoke statici:
  `cd frontend && npm test`
- typecheck (Next/TS) dal frontend:
  `cd frontend && npm run typecheck`
- typecheck dal root del repo (utile se apri il workspace su `GAIA/` in Cursor/VS Code):
  `cd frontend && npm run typecheck:from-root`
- E2E browser sullo stack locale:
  `cd frontend && PLAYWRIGHT_BASE_URL=http://127.0.0.1:8080 npm run test:e2e`

I test E2E correnti coprono:

- login admin e wizard import Catasto Fase 1 fino al report finale
- ricerca anagrafica Catasto singola e massiva, inclusa la massiva persistita su job worker con polling UI

Credenziali bootstrap locali:

- username: valore di `BOOTSTRAP_ADMIN_USERNAME` in `.env`
- password: valore di `BOOTSTRAP_ADMIN_PASSWORD` in `.env`

### Policy coverage

- Da oggi, per codice nuovo o modificato, la coverage richiesta e `100%` sul file/classe toccato.
- Non e ammesso usare una media globale di repository per compensare file runtime cambiati sotto soglia.
- Parser, validatori, normalizzatori, scheduler, servizi puri, router e componenti frontend runtime toccati devono tutti rispettare lo stesso gate `100%`.
- La CI backend pubblica `coverage.json` e `coverage.xml` come artifact del job, cosi il report resta consultabile anche quando il gate coverage fallisce.
- La CI frontend esegue unit test Vitest con report `coverage-final.json`, `cobertura-coverage.xml` e report HTML, li pubblica come artifact e applica lo stesso gate `100%` sui file runtime cambiati sotto `frontend/src/` (esclusi `src/types/` e `*.d.ts`).
- Data di entrata in vigore della policy rafforzata: `2026-06-19`.
- Il gate sui file cambiati resta il minimo obbligatorio immediato, ma l'obiettivo di piattaforma e la copertura `100%` dell'intero codice runtime versionato.
- Il piano operativo per portare backend, frontend, worker e script runtime a copertura totale e documentato in `docs/TEST_COVERAGE_100_PLAN.md`.

### Cancellazione documenti Anagrafica (protetta da password)

Per riabilitare la rimozione dei documenti dal frontend (modulo Anagrafica) con controllo lato server, imposta in `.env` (backend):

- `ANAGRAFICA_DELETE_PASSWORD`: se valorizzata, ogni `DELETE /api/anagrafica/documents/{id}` richiede l'header `X-GAIA-Delete-Password`.

Se la variabile e vuota/non impostata, la password non viene richiesta.

## Documentazione

- Architettura piattaforma: `docs/ARCHITECTURE.md`
- PRD piattaforma: `docs/PRD.md`
- Piano implementazione: `docs/IMPLEMENTATION_PLAN.md`
- Wiki Agent (Milestone 9): `domain-docs/wiki/docs/`
  - il fallback della chat Wiki e del widget è contestuale a `module_key` e `page_path`, con priorità `pagina > modulo > generico`; label ed esempi sono centralizzati in `backend/app/modules/wiki/services/context_hints.py`
- GAIA Accessi: `domain-docs/accessi/docs/`
- GAIA CED PRD: `domain-docs/ced/docs/PRD.md`
- GAIA CED Plan: `domain-docs/ced/docs/IMPLEMENTATION_PLAN.md`
- GAIA CED Prompt: `domain-docs/ced/docs/CODEX_PROMPT.md`
- GAIA CED Progress: `domain-docs/ced/docs/PROGRESS.md`
- GAIA Utenze PRD: `domain-docs/utenze/docs/PRD_anagrafica.md`
- GAIA Utenze Prompt: `domain-docs/utenze/docs/PROMPT_CODEX_anagrafica.md`
- GAIA Utenze Plan: `domain-docs/utenze/docs/EXECUTION_PLAN.md`
- GAIA Rete PRD: `domain-docs/network/docs/PRD_network.md`
- GAIA Rete Prompt: `domain-docs/network/docs/PROMPT_CODEX_network.md`
- GAIA Capacitas Data Recovery: `domain-docs/elaborazioni/capacitas/docs/CAPACITAS_DATA_RECOVERY.md`
- Backend monolite modulare: `backend/app/MONOLITH_MODULAR.md`
- GAIA Inventario PRD: `domain-docs/inventory/docs/PRD_inventory.md`
- GAIA Inventario Prompt: `domain-docs/inventory/docs/PROMPT_CODEX_inventory.md`
- GAIA Catasto PRD: `domain-docs/catasto/docs/PRD_catasto.md`
- Avanzamento tranche Catasto 2026-04-22: `progress/2026-04-22_catasto_phase_progress.md`

## Catasto MVP

- Runtime operativo backend esposto sotto `/elaborazioni`; `/catasto` resta area dominio/documenti/comuni
- Worker dedicato `elaborazioni-worker` con Playwright, OCR CAPTCHA e presa in carico dei job Capacitas persistenti
- Volume Docker `catasto-data` per PDF e immagini CAPTCHA
- Database locale Docker su `postgis/postgis:16-3.4-alpine` per supportare la Fase 1 geospaziale
- Archivio documenti con download singolo e ZIP per batch
- Nuove API Fase 1 sotto `/catasto/import`, `/catasto/distretti`, `/catasto/particelle`, `/catasto/anomalie`
- Wrapper frontend condiviso `CatastoPage` per le pagine Fase 1 con navigazione di dominio uniforme
- Test connessione SISTER asincrono eseguito dal worker con feedback realtime
- Variabili operative in `.env.example` per storage documenti/CAPTCHA e chiave Fernet condivisa
- Selettori SISTER esterni in `modules/elaborazioni/worker/sister_selectors.json`, sovrascrivibili via `ELABORAZIONI_SISTER_SELECTORS_PATH` con fallback compatibile su `CATASTO_SISTER_SELECTORS_PATH`
- Diagnostica probe SISTER del worker con log stdout e snapshot HTML/PNG in `ELABORAZIONI_DEBUG_ARTIFACTS_PATH`
- Supporto ai due flussi SISTER:
  - ricerca per immobile con comune, foglio, particella e subalterno
  - ricerca per soggetto con `subject_id`, inferenza PF/PNF e richiesta `ATTUALITA`/`STORICA`
- Report batch `JSON` e `Markdown` persistiti dal worker
- Artifact per richiesta con path persistito, download ZIP dal runtime `elaborazioni` e preview immagine autenticata nel dettaglio batch; per i `not_found` su ricerca soggetto il worker salva anche una preview focalizzata sul blocco diagnostico SISTER
- I batch `pending` mai avviati scadono automaticamente dopo `ELABORAZIONI_PENDING_START_TIMEOUT_MINUTES` e vengono marcati `failed`, evitando code orfane nello storico operativo
- Metriche runtime visure disponibili via `GET /elaborazioni/metrics` e riusate nella dashboard `/elaborazioni` per throughput, success rate, tempi medi e ultimo processato
- Finestra operativa opzionale del worker tramite `ELABORAZIONI_OPERATION_WINDOW_ENABLED`, `ELABORAZIONI_OPERATION_START_HOUR`, `ELABORAZIONI_OPERATION_END_HOUR`, `ELABORAZIONI_OPERATION_TIMEZONE`: i batch possono partire anche fuori fascia, ma i runner si mettono in pausa automatica e riprendono al primo orario utile

## Network MVP

- Scanner LAN dedicato con `nmap`, fallback `scapy`, enrichment DNS, mDNS, NetBIOS e SNMP best-effort
- Enrichment HTTP per dispositivi con interfaccia web, inclusi title, meta refresh e nome dispositivo
- Recupero MAC via ARP cache locale, helper host-side e fallback opzionale via gateway
- Snapshot storici completi per scansione con dettaglio snapshot e diff tra snapshot
- Gestione anagrafica apparati con campi manuali `display_name`, `asset_label`, `location_hint`, `notes`
- Flag `is_known_device` per distinguere i dispositivi registrati dai dispositivi solo osservati in rete
- Dettaglio dispositivo con `hostname_source` e `metadata_sources` per capire da dove arriva il nome rilevato
- Alert `UNKNOWN_DEVICE` per dispositivi presenti in rete ma non registrati
- Alert `MISSING_DEVICE` solo per dispositivi conosciuti assenti dalla rete oltre soglia temporale
- Planimetrie con posizionamento persistito dei device e vista dashboard/modali operative
- Scheduler e scanner condividono il backend monolitico e il database unico della piattaforma

### Variabili operative Network

- `NETWORK_RANGE`: subnet da scandire
- `NETWORK_SCAN_PORTS`: porte da verificare sugli host attivi
- `NETWORK_ENRICHMENT_TIMEOUT_SECONDS`: timeout per reverse DNS, mDNS, NetBIOS e SNMP
- `NETWORK_MISSING_DEVICE_ALERT_DAYS`: giorni di assenza oltre i quali un dispositivo conosciuto genera alert
- `NETWORK_SNMP_COMMUNITIES`: elenco CSV di community SNMP generiche
- `NETWORK_SNMP_COMMUNITY_PROFILES`: JSON array opzionale con community per subnet specifiche
- `NETWORK_ARP_HELPER_BASE_URL`: endpoint HTTP usato dai container per interrogare la neighbor table dell'host
- `NETWORK_GATEWAY_ARP_HOST`: host SSH opzionale del gateway o di una macchina di rete da cui interrogare ARP
- `NETWORK_GATEWAY_ARP_PORT`: porta SSH del gateway
- `NETWORK_GATEWAY_ARP_USERNAME`: utente SSH del gateway
- `NETWORK_GATEWAY_ARP_PASSWORD`: password SSH del gateway
- `NETWORK_GATEWAY_ARP_PRIVATE_KEY_PATH`: chiave privata opzionale per il gateway
- `NETWORK_GATEWAY_ARP_COMMAND`: comando remoto da eseguire per il lookup ARP, con placeholder `{ip}`

Esempio `NETWORK_SNMP_COMMUNITY_PROFILES`:

```json
[
  { "cidr": "192.168.1.0/24", "communities": ["public", "rete-lan"] },
  { "cidr": "192.168.10.0/24", "communities": ["switch-mgmt"] }
]
```

Ordine di risoluzione hostname del modulo Rete:

1. hostname rilevato da `nmap`
2. `sysName` SNMP
3. nome NetBIOS
4. nome mDNS
5. reverse DNS

Semantica alert attuale del modulo Rete:

1. `UNKNOWN_DEVICE`: host rilevato in rete ma non marcato come `is_known_device`
2. `MISSING_DEVICE`: host marcato come `is_known_device` e assente dalla rete per piu di `NETWORK_MISSING_DEVICE_ALERT_DAYS`

Componenti runtime del modulo Rete:

- backend API FastAPI nel monolite modulare
- servizio `scanner` dedicato per scansioni schedulate
- servizio `arp-helper` host-side per recupero MAC da neighbor table host quando i container non vedono direttamente la LAN

## Comandi utili

| Comando | Descrizione |
|---------|-------------|
| `make up` | Avvia lo stack |
| `make down` | Ferma i container |
| `make logs` | Tail dei log |
| `make rebuild` | Rebuild e restart |
| `make migrate` | Esegue migrazioni Alembic |
| `make bootstrap-admin` | Crea utente admin |
| `make bootstrap-domain` | Carica dati seed |
| `make live-sync` | Sync live dal NAS via SSH |

## Piano di migrazione backend

1. Consolidare tutto il nuovo codice di dominio in `app/modules/<modulo>/`.
2. Lasciare i path legacy come wrapper compatibili fino a stabilizzazione.
3. `network` e `catasto` sono gia su namespace canonico di modulo.
4. `accessi` usa gia route e entrypoint canonici di modulo, con wrapper legacy mantenuti.
5. La directory fisica del backend e stata rinominata in `backend/`; i riferimenti storici vanno considerati obsoleti.
