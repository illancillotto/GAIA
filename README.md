# GAIA
## Gestione Apparati Informativi e Accessi
### Piattaforma IT governance — Consorzio di Bonifica dell'Oristanese

> Regola repository
> Backend unico, frontend unico, database unico. Nuovo codice backend di dominio va nel monolite modulare sotto `backend/app/modules/<modulo>/`.

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
snapshot storici, diff tra scansioni, dettaglio dispositivi e alert per
dispositivi non registrati o per dispositivi conosciuti assenti dalla rete oltre soglia.
Stato: operativo avanzato.

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
├── domain-docs/
│   ├── accessi/docs/
│   ├── anagrafica/docs/
│   ├── catasto/docs/
│   ├── inventory/docs/
│   └── network/docs/
├── frontend/
│   └── src/app/
│       ├── nas-control/
│       ├── anagrafica/
│       ├── network/
│       ├── inventory/
│       └── catasto/
├── modules/
│   └── catasto/
│       └── worker/
├── backend/
│   ├── app/
│   │   ├── modules/
│   │   │   ├── core/
│   │   │   ├── accessi/
│   │   │   ├── anagrafica/
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
- `modules/` non e piu il contenitore dei moduli applicativi; resta disponibile solo per asset tecnici specifici, come `modules/catasto/worker/`.

## Architettura backend attuale

Il backend di GAIA e un **monolite modulare**: un solo servizio FastAPI,
un solo database PostgreSQL e un solo set di migration Alembic.

La directory fisica del backend e:
- `backend/`

La struttura logica canonica del codice backend e invece:
- `backend/app/modules/core`
- `backend/app/modules/accessi`
- `backend/app/modules/network`
- `backend/app/modules/catasto`

I package storici fuori da `app/modules/` restano disponibili come layer di compatibilita.

## Quick Start

1. Copia il file ambiente:
   `cp .env.example .env`
2. Avvia lo stack:
   `make up`
3. Rebuild quando cambi dipendenze o entrypoint:
   `make rebuild`
4. Esegui le migrazioni:
   `make migrate`
5. Crea l'admin iniziale:
   `make bootstrap-admin`
6. Carica i dati seed:
   `make bootstrap-domain`
   Il comando inizializza il seed del dominio audit e il dizionario `catasto_comuni`.
7. Genera e configura la chiave vault Catasto in `.env`:
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   La stessa chiave deve essere condivisa tra `backend` e `catasto-worker`.
8. Accedi all'applicazione:
   `http://localhost:8080`

## Documentazione

- GAIA Accessi: `domain-docs/accessi/docs/`
- GAIA Anagrafica PRD: `domain-docs/anagrafica/docs/PRD_anagrafica.md`
- GAIA Anagrafica Prompt: `domain-docs/anagrafica/docs/PROMPT_CODEX_anagrafica.md`
- GAIA Anagrafica Plan: `domain-docs/anagrafica/docs/EXECUTION_PLAN.md`
- GAIA Rete PRD: `domain-docs/network/docs/PRD_network.md`
- GAIA Rete Prompt: `domain-docs/network/docs/PROMPT_CODEX_network.md`
- Backend monolite modulare: `backend/app/MONOLITH_MODULAR.md`
- GAIA Inventario PRD: `domain-docs/inventory/docs/PRD_inventory.md`
- GAIA Inventario Prompt: `domain-docs/inventory/docs/PROMPT_CODEX_inventory.md`
- GAIA Catasto PRD: `domain-docs/catasto/docs/PRD_catasto.md`
- GAIA Catasto Prompt: `domain-docs/catasto/docs/PROMPT_CODEX_catasto.md`

## Catasto MVP

- Router backend integrato sotto `/catasto`
- Worker dedicato `catasto-worker` con Playwright e OCR CAPTCHA
- Volume Docker `catasto-data` per PDF e immagini CAPTCHA
- Archivio documenti con download singolo e ZIP per batch
- Test connessione SISTER asincrono eseguito dal worker con feedback realtime
- Variabili operative in `.env.example` per storage documenti/CAPTCHA e chiave Fernet condivisa
- Selettori SISTER esterni in `modules/catasto/worker/sister_selectors.json`, sovrascrivibili via `CATASTO_SISTER_SELECTORS_PATH`
- Diagnostica probe SISTER del worker con log stdout e snapshot HTML/PNG in `CATASTO_DEBUG_ARTIFACTS_PATH`

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
