# Deployment

> Regola deployment
> Il deployment del backend GAIA e unico. I moduli Accessi, Rete, Inventario e Catasto condividono FastAPI, PostgreSQL e Alembic.

## 1. Scopo

Questa guida descrive il deployment iniziale della piattaforma in ambiente locale o interno usando Docker Compose.

## 2. Prerequisiti

- Docker Engine e Docker Compose plugin
- file root `.env` derivato da `.env.example`
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
  - `POST /sync/live-apply`
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
- scheduling configurabile:
  - `SYNC_SCHEDULE_ENABLED`
  - `SYNC_SCHEDULE_INTERVAL_SECONDS`
  - `SYNC_SCHEDULE_MAX_CYCLES`
- se il NAS non e raggiungibile o i comandi falliscono, il backend restituisce `503`
- ogni esecuzione sync applicata viene registrata in `sync_runs`

## 7. Log e Troubleshooting

- log stack completo: `make logs`
- stop servizi: `make down`
- rebuild immagini: `make rebuild`

## 8. Note Produzione

- esporre i servizi preferibilmente dietro VPN o LAN interna
- usare secret manager o variabili ambiente protette
- configurare backup regolari del volume PostgreSQL
- introdurre TLS terminato su proxy o load balancer interno

## 9. Backup Dati

Strategia minima consigliata:

- backup periodico del volume `postgres_data`
- dump applicativo schedulato del database
- conservazione documentata delle versioni Alembic
