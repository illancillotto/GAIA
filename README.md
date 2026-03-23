# GAIA
## Gestione Accessi Inventario e Apparati
### Piattaforma IT governance — Consorzio di Bonifica dell'Oristanese

## Cos'è GAIA

GAIA centralizza la governance IT del Consorzio in tre moduli integrati,
accessibili da un'unica interfaccia dopo il login.

## I tre moduli

### GAIA Accessi — NAS Audit
Audit completo degli accessi al NAS Synology: utenti, gruppi, cartelle condivise,
permessi effettivi e workflow di review per i responsabili di settore.
Stato: completato e funzionante.

### GAIA Rete — Network Monitor
Monitoraggio della rete LAN: scansione dispositivi, mappa interattiva per piano,
alert per dispositivi nuovi o non raggiungibili.
Stato: in sviluppo.

### GAIA Inventario — IT Inventory
Registro centralizzato dei dispositivi IT: anagrafica, garanzie, assegnazioni,
import CSV e collegamento con i dati di rete.
Stato: in sviluppo.

## Stack tecnologico

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- Frontend: Next.js, React, TypeScript, TailwindCSS, TanStack Table
- Infrastructure: Docker, Docker Compose, Nginx
- CI: GitHub Actions

## Struttura repository
```text
GAIA/
├── modules/
│   ├── accessi/
│   │   ├── backend/
│   │   ├── frontend/
│   │   └── docs/
│   ├── network/
│   │   └── docs/
│   │       ├── PRD_network.md
│   │       └── PROMPT_CODEX_network.md
│   └── inventory/
│       └── docs/
│           ├── PRD_inventory.md
│           └── PROMPT_CODEX_inventory.md
├── docker-compose.yml
├── docker-compose.override.yml
├── nginx/
├── scripts/
├── Makefile
└── .env.example
```

## Quick Start

1. Copia il file ambiente:
   `cp .env.example .env`
2. Avvia lo stack:
   `make up`
3. Esegui le migrazioni:
   `make migrate`
4. Crea l'admin iniziale:
   `make bootstrap-admin`
5. Carica i dati seed:
   `make bootstrap-domain`
6. Accedi all'applicazione:
   `http://localhost:8080`

## Documentazione

- GAIA Accessi: `modules/accessi/docs/`
- GAIA Rete PRD: `modules/network/docs/PRD_network.md`
- GAIA Rete Prompt: `modules/network/docs/PROMPT_CODEX_network.md`
- GAIA Inventario PRD: `modules/inventory/docs/PRD_inventory.md`
- GAIA Inventario Prompt: `modules/inventory/docs/PROMPT_CODEX_inventory.md`

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
