# GAIA
## Gestione Apparati Informativi e Accessi
### Piattaforma IT governance — Consorzio di Bonifica dell'Oristanese

## Cos'è GAIA

GAIA centralizza la governance IT del Consorzio in quattro moduli integrati,
accessibili da un'unica interfaccia dopo il login.

## I quattro moduli

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

### GAIA Catasto — Servizi AdE
Automazione delle visure catastali dal portale SISTER: upload batch CSV/XLSX,
worker Playwright separato, gestione CAPTCHA, archivio PDF e download ZIP.
Stato: MVP in integrazione.

## Stack tecnologico

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- Frontend: Next.js, React, TypeScript, TailwindCSS, TanStack Table
- Infrastructure: Docker, Docker Compose, Nginx
- CI: GitHub Actions

Il frontend condiviso della piattaforma vive in `frontend/`.

## Struttura repository
```text
GAIA/
├── frontend/
├── modules/
│   ├── accessi/
│   │   ├── backend/
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
   Il comando inizializza il seed del dominio audit e il dizionario `catasto_comuni`.
6. Genera e configura la chiave vault Catasto in `.env`:
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   La stessa chiave deve essere condivisa tra `backend` e `catasto-worker`.
7. Accedi all'applicazione:
   `http://localhost:8080`

## Documentazione

- GAIA Accessi: `modules/accessi/docs/`
- GAIA Rete PRD: `modules/network/docs/PRD_network.md`
- GAIA Rete Prompt: `modules/network/docs/PROMPT_CODEX_network.md`
- GAIA Inventario PRD: `modules/inventory/docs/PRD_inventory.md`
- GAIA Inventario Prompt: `modules/inventory/docs/PROMPT_CODEX_inventory.md`
- GAIA Catasto PRD: `modules/catasto/docs/PRD_catasto.md`
- GAIA Catasto Prompt: `modules/catasto/docs/PROMPT_CODEX_catasto.md`

## Catasto MVP

- Router backend integrato sotto `/catasto`
- Worker dedicato `catasto-worker` con Playwright e OCR CAPTCHA
- Volume Docker `catasto-data` per PDF e immagini CAPTCHA
- Archivio documenti con download singolo e ZIP per batch
- Test connessione SISTER asincrono eseguito dal worker con feedback realtime
- Variabili operative in `.env.example` per storage documenti/CAPTCHA e chiave Fernet condivisa
- Selettori SISTER esterni in `modules/catasto/worker/sister_selectors.json`, sovrascrivibili via `CATASTO_SISTER_SELECTORS_PATH`
- Diagnostica probe SISTER del worker con log stdout e snapshot HTML/PNG in `CATASTO_DEBUG_ARTIFACTS_PATH`

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
