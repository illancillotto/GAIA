# Deployment

## 1. Scopo

Questa guida descrive il deployment iniziale della piattaforma in ambiente locale o interno usando Docker Compose.

## 2. Prerequisiti

- Docker Engine e Docker Compose plugin
- file `.env` derivato da `.env.example`
- porte locali disponibili per frontend, backend e nginx

## 3. Servizi

- `postgres`: database applicativo
- `backend`: API FastAPI
- `frontend`: applicazione Next.js
- `nginx`: reverse proxy di ingresso

## 4. Avvio Locale

1. `cp .env.example .env`
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
