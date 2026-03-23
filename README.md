# NAS Access Audit Platform

Piattaforma interna per audit, consultazione e validazione degli accessi al NAS Synology del Consorzio di Bonifica dell'Oristanese.

## Obiettivo

L'applicazione centralizza la visibilita sugli accessi a utenti, gruppi e cartelle condivise, calcola i permessi effettivi e supporta il workflow di review dei responsabili di settore. Il MVP e orientato ad audit e reporting, senza modifiche automatiche ai permessi del NAS.

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- Frontend: Next.js, React, TypeScript
- DevOps: Docker, Docker Compose, Nginx
- CI: GitHub Actions

## Struttura Repository

```text
.
|-- backend/
|   |-- alembic/
|   |-- app/
|   |-- tests/
|   |-- Dockerfile
|   |-- alembic.ini
|   `-- requirements.txt
|-- docs/
|   |-- ARCHITECTURE.md
|   |-- CODEX_PROMPT.md
|   |-- DEPLOYMENT.md
|   |-- IMPLEMENTATION_PLAN.md
|   `-- PRD.md
|-- frontend/
|   |-- src/
|   |-- Dockerfile
|   `-- package.json
|-- nginx/
|   `-- nginx.conf
|-- scripts/
|   |-- bootstrap-admin.sh
|   |-- bootstrap-domain.sh
|   |-- backend-shell.sh
|   |-- frontend-shell.sh
|   |-- migrate.sh
|   |-- start-backend.sh
|   |-- start-frontend.sh
|   |-- start-nginx.sh
|   |-- start-postgres.sh
|   `-- wait-for-db.sh
|-- .github/workflows/
|-- .editorconfig
|-- .env.example
|-- .gitignore
|-- Makefile
|-- docker-compose.override.yml
`-- docker-compose.yml
```

## Quick Start

1. Copiare il file ambiente:
   `cp .env.example .env`
2. Avviare lo stack:
   `make up`
3. Eseguire la migrazione iniziale:
   `make migrate`
4. Bootstrap utente admin e dominio seed:
   `make bootstrap-admin`
   `make bootstrap-domain`
5. Verificare i servizi:
   - frontend: `http://localhost:3000`
   - backend health: `http://localhost:8000/health`
   - nginx entrypoint: `http://localhost:8080`

## Documentazione Disponibile

- [PRD](docs/PRD.md)
- [Piano implementazione](docs/IMPLEMENTATION_PLAN.md)
- [Execution Plan](docs/EXECUTION_PLAN.md)
- [Architettura](docs/ARCHITECTURE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Prompt Codex](docs/CODEX_PROMPT.md)
- [Progress](docs/PROGRESS.md)

## Stato Progetto

Bootstrap iniziale completato per sviluppo incrementale:

- backend FastAPI avviabile con endpoint `/health`
- autenticazione applicativa base con `POST /auth/login` e `GET /auth/me`
- sync NAS con preview/apply da payload testuale e live apply via SSH con endpoint `GET /sync/capabilities`, `POST /sync/preview`, `POST /sync/apply`, `POST /sync/live-apply`
- audit trail persistente delle sync disponibile via `GET /sync-runs`
- permission engine MVP con preview `POST /permissions/calculate-preview` e lista `GET /effective-permissions`
- seed iniziale del dominio audit con utenti, gruppi, share, review e permessi effettivi
- frontend Next.js con login reale e pagina `Sync` collegata al backend
- stack Docker Compose per backend, frontend, postgres e nginx
- documentazione iniziale coerente per prodotto, architettura e deployment

## Comandi Utili

- `make up`: avvio stack locale
- `make down`: stop e cleanup container
- `make logs`: tail dei log
- `make rebuild`: rebuild immagini e restart
- `make backend-shell`: shell nel container backend
- `make frontend-shell`: shell nel container frontend
- `make migrate`: esecuzione migrazioni Alembic
- `make bootstrap-admin`: crea o verifica l'admin iniziale applicativo
- `make bootstrap-domain`: popola dati seed iniziali per il dominio audit
- `make live-sync`: esegue una live sync via SSH con retry controllato
- `make scheduled-live-sync`: avvia il runner schedulato della live sync
