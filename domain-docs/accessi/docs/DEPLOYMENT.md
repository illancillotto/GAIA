# Deployment

> Regola deployment
> Il deployment del backend GAIA e unico. I moduli Accessi, Rete, Inventario e Catasto condividono FastAPI, PostgreSQL e Alembic.

## 1. Scopo

Questa guida descrive il deployment iniziale della piattaforma in ambiente locale o interno usando Docker Compose, e il deploy operativo sul server CED per l'hostname `gaia.lan`.

## 2. Prerequisiti

- Docker Engine e Docker Compose plugin
- file root `.env` derivato da `.env.example`
- per deploy CED: file locale `.env.production` derivato da `.env.production.example`
- porte locali disponibili per frontend, backend e nginx

## 3. Servizi

- `postgres`: database applicativo
- `backend`: API FastAPI
- `frontend`: applicazione Next.js
- `nginx`: reverse proxy di ingresso

## 4. Avvio Locale

1. `cp .env.example .env`
   Il file root `/.env` e la source of truth del setup locale; evitare di duplicare la configurazione in file env separati di sottocartella.
2. `make up`
3. `make migrate`
4. `make bootstrap-admin`
5. `make bootstrap-domain`
6. verificare `http://localhost:8080`

## 4.1 Deploy CED `gaia.lan`

Script dedicato:

- `./scripts/deploy-ced-gaia.sh`

Modalita supportate:

- `DEPLOY_ACTION=deploy`: build locale immagini, trasferimento progetto + `.env` + immagini, avvio stack remoto, configurazione nginx host se disponibile, smoke test
- `DEPLOY_ACTION=nginx`: configura solo il virtual host host-level per `gaia.lan`
- `DEPLOY_ACTION=smoke`: verifica solo stack e endpoint remoti

Variabili principali:

- `CED_SSH_HOST=serverCed`
- `CED_PROJECT_DIR=/opt/gaia`
- `GAIA_DOMAIN=gaia.lan`
- `GAIA_MOBILE_DOMAIN=gaia-mobile.lan`
- `GAIA_PROD_NGINX_PORT=8080`
- `ENV_FILE=.env.production`
- `RELEASE_ID=<auto>`
- `ALLOW_NON_PRODUCTION_ENV=no`
- `CONFIGURE_HOST_NGINX=auto`

Esempi:

1. deploy completo:
   `./scripts/deploy-ced-gaia.sh`
2. smoke test remoto:
   `DEPLOY_ACTION=smoke ./scripts/deploy-ced-gaia.sh`
3. sola configurazione virtual host:
   `DEPLOY_ACTION=nginx CONFIGURE_HOST_NGINX=yes ./scripts/deploy-ced-gaia.sh`

Comportamento env lato server:

- copia il file locale production sia in `/opt/gaia/.env` sia in `/opt/gaia/.env.production`
- imposta o riallinea `NGINX_PORT=$GAIA_PROD_NGINX_PORT`
- forza `NEXT_PUBLIC_API_BASE_URL=/api`
- aggiunge a `BACKEND_CORS_ORIGINS` gli origin `http(s)://gaia.lan` e, se configurato, `http(s)://gaia-mobile.lan`
- richiede `APP_ENV=production` salvo override esplicito `ALLOW_NON_PRODUCTION_ENV=yes`
- dopo le normalizzazioni, riallinea `.env.production` a `.env`
- prova ad applicare permessi restrittivi `chmod 600 .env .env.production`

Guardrail produzione:

- verifica locale di env obbligatorie: `POSTGRES_PASSWORD`, `DATABASE_URL`, `JWT_SECRET_KEY`, `BOOTSTRAP_ADMIN_*`, `CREDENTIAL_MASTER_KEY`
- rifiuta domini `*.local` come target CED
- produce un `RELEASE_ID` e archivia manifest release sotto `releases/`
- il server remoto esegue solo runtime deploy con `docker compose up -d --no-build`

Prerequisiti operativi:

- alias SSH funzionante verso il server CED
- Docker disponibile sul server remoto
- file `.env.production` locale gia valorizzato per produzione
- DNS o risoluzione interna di `gaia.lan` gia puntata al server corretto

## 5. Accessi di Default

Credenziali bootstrap locali:

- username: `admin`
- email: `admin@example.local`
- password: `change_me_admin`

Le credenziali vanno cambiate tramite variabili ambiente in ambienti non locali.

## 6. Migrazioni

- esecuzione manuale: `make migrate`
- shell backend: `make backend-shell`

## 6.1 Bootstrap Admin

- esecuzione manuale: `make bootstrap-admin`
- variabili usate:
  - `BOOTSTRAP_ADMIN_USERNAME`
  - `BOOTSTRAP_ADMIN_EMAIL`
  - `BOOTSTRAP_ADMIN_PASSWORD`

## 6.2 Bootstrap Dominio Audit

- esecuzione manuale: `make bootstrap-domain`
- popola uno snapshot seed con:
  - utenti NAS
  - gruppi NAS
  - share
  - permission entry
  - effective permission
  - review di esempio
- lo script e idempotente e aggiorna lo snapshot seed esistente

## 6.3 Sync Live NAS

- configurazione minima:
  - `NAS_HOST`
  - `NAS_PORT`
  - `NAS_USERNAME`
  - `NAS_PASSWORD` oppure `NAS_PRIVATE_KEY_PATH`
- comandi configurabili:
  - `NAS_PASSWD_COMMAND`
  - `NAS_GROUP_COMMAND`
  - `NAS_SHARES_COMMAND`
  - `NAS_ACL_COMMAND_TEMPLATE`
- endpoint runtime:
  - `GET /sync/capabilities`
  - `POST /sync/jobs`
  - `GET /sync/jobs`
  - `GET /sync/jobs/{id}`
  - `POST /sync/jobs/{id}/retry`
  - `POST /sync/jobs/{id}/cancel`
  - `POST /sync/live-apply` come alias compatibile verso la creazione job
  - `GET /sync-runs`
- script operativo:
  - `make live-sync`
  - `make scheduled-live-sync`
- retry configurabile:
  - `SYNC_LIVE_MAX_ATTEMPTS`
  - `SYNC_LIVE_RETRY_DELAY_SECONDS`
  - `SYNC_LIVE_BACKOFF_MODE`
  - `SYNC_LIVE_BACKOFF_MULTIPLIER`
  - `SYNC_LIVE_BACKOFF_MAX_DELAY_SECONDS`
  - `SYNC_LIVE_BACKOFF_JITTER_ENABLED`
  - `SYNC_LIVE_BACKOFF_JITTER_RATIO`
  - `SYNC_LIVE_WORKER_ARTIFACTS_PATH`
  - `SYNC_LIVE_PENDING_TIMEOUT_MINUTES`
- scheduling configurabile:
  - `SYNC_SCHEDULE_ENABLED`
  - `SYNC_SCHEDULE_INTERVAL_SECONDS`
  - `SYNC_SCHEDULE_MAX_CYCLES`
- la pagina `/nas-control/sync` non esegue piu la scansione dentro la request HTTP: accoda un job `pending|running|succeeded|failed|cancelled`
- il worker NAS esegue la connessione SSH, applica retry/backoff, persiste lo snapshot e registra l'audit finale in `sync_runs`
- ogni job scrive un log append-only in `${SYNC_LIVE_WORKER_ARTIFACTS_PATH}/<job_id>/worker.log`
- il `worker.log` espone avanzamento per fase: passwd, group, share root, subpath, ACL e persistenza finale
- alla ripartenza del backend, i job `pending` scaduti e i `running` senza processo o senza `worker_pid` oltre timeout vengono marcati `failed`
- `sync_runs` resta lo storico consolidato delle sync completate o fallite; `sync_jobs` e la coda operativa con PID, log worker e stato runtime

## 7. Log e Troubleshooting

- log stack completo: `make logs`
- stop servizi: `make down`
- rebuild immagini: `make rebuild`

## 8. Note Produzione

- esporre i servizi preferibilmente dietro VPN o LAN interna
- usare secret manager o variabili ambiente protette
- configurare backup regolari del volume PostgreSQL
- in LAN interna usare HTTP su `gaia.lan` (nginx host su porta 80)
- per deploy online con hostname pubblico: TLS con **Let's Encrypt** (certbot) su nginx; aggiornare `BACKEND_CORS_ORIGINS` con `https://`
- distinguere chiaramente gli hostname:
  - `gaia.lan` per sviluppo locale e ambiente CED/interno

### TLS con Let's Encrypt (deploy online)

Quando GAIA sara esposta su un dominio pubblico risolvibile (non `.lan`):

1. Puntare DNS A/AAAA verso il server
2. Installare certbot: `sudo apt install certbot python3-certbot-nginx`
3. Emettere certificato: `sudo certbot --nginx -d gaia.example.it`
4. Aggiornare `.env` remoto: `BACKEND_CORS_ORIGINS=https://gaia.example.it`
5. Verificare rinnovo automatico: `sudo certbot renew --dry-run`

In LAN interna **non** usare mkcert ne certificati self-signed: HTTP e sufficiente finche la rete e fidata.

## 9. Backup Dati

Strategia minima consigliata:

- backup periodico del volume `postgres_data`
- dump applicativo schedulato del database
- conservazione documentata delle versioni Alembic
