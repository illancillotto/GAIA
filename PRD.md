# GAIA Product Requirements Document

> Nota repository
> Questo documento descrive il prodotto GAIA a livello di piattaforma.
> I PRD di dominio restano in `domain-docs/<dominio>/docs/`.

## 1. Visione

GAIA e la piattaforma interna del Consorzio di Bonifica dell'Oristanese per la
governance di accessi, rete, inventario, catasto e anagrafica soggetti tramite
un backend monolitico modulare, un frontend condiviso e un database unico.

## 2. Obiettivo di prodotto

Fornire un unico punto di accesso operativo per:

- audit e review degli accessi al NAS
- monitoraggio continuo della rete LAN
- gestione dell'inventario IT
- automazione delle visure catastali e della relativa documentazione
- gestione anagrafica dei soggetti e dei documenti correlati

## 3. Domini funzionali

### 3.1 Accessi

- ingestione utenti, gruppi, share e ACL dal NAS
- calcolo permessi effettivi
- workflow di review e reporting audit

### 3.2 Network

- scansioni LAN schedulate e manuali
- inventory osservato della rete
- alert su dispositivi sconosciuti o assenti
- planimetrie e storico snapshot

### 3.2.1 CED (convergenza pianificata)

- unificazione frontend delle superfici `NAS Control` e `Rete`
- nuovo entrypoint `GAIA CED` per l'ambito infrastrutturale
- mantenimento iniziale dei backend e dei permessi esistenti

### 3.3 Inventory

- anagrafica centralizzata degli asset IT
- import dati e correlazione con apparati rilevati in rete
- stato operativo, assegnazioni e garanzie

### 3.4 Catasto

- gestione credenziali SISTER
- batch e richieste singole di visura
- worker browser-based con gestione CAPTCHA
- archivio PDF e tracciamento realtime avanzamento

### 3.4.1 Elaborazioni (integrazioni operative)

- integrazione Capacitas (inVOLTURE) per workflow di elaborazione e ricerca

### 3.5 Utenze

- registro soggetti persone fisiche e giuridiche
- import da archivio NAS
- classificazione e ricerca documentale
- integrazione progressiva con Catasto e Accessi

## 4. Architettura di riferimento

- backend unico FastAPI sotto `backend/`
- namespace canonici di dominio in `backend/app/modules/<modulo>/`
- frontend unico Next.js sotto `frontend/`
- database PostgreSQL condiviso
- worker tecnici separati solo dove necessario, ad esempio `modules/catasto/worker/` e scanner LAN

## 5. Requisiti trasversali

### 5.1 Sicurezza e accesso

- autenticazione applicativa centralizzata
- autorizzazioni per modulo e sezione
- audit trail delle operazioni critiche

### 5.2 Osservabilita e operativita

- log applicativi coerenti tra moduli
- job e workflow asincroni monitorabili
- documentazione allineata alla struttura reale del repository

### 5.3 Coerenza architetturale

- nessun backend separato per dominio
- nessuna duplicazione di stack applicativo per modulo
- migrazioni centralizzate in `backend/alembic/versions/`

## 6. Non obiettivi di piattaforma

- microservizi per ogni dominio
- provisioning infrastrutturale automatico fuori dallo stack Compose
- portali esterni pubblici nella baseline corrente

## 7. KPI iniziali

- bootstrap locale ripetibile del repository
- navigazione unificata tra domini da una sola web app
- workflow core di ogni dominio eseguibile nel backend condiviso
- documentazione root e dominio coerente con la struttura effettiva

## 8. Roadmap sintetica

1. consolidamento del monolite modulare e dei namespace canonici
2. completamento del dominio Catasto e integrazione Capacitas
3. consolidamento del dominio Utenze e dei collegamenti documentali
4. avanzamento del dominio Inventory con correlazione ai dati Network
5. hardening operativo, permessi applicativi e documentazione trasversale
6. convergenza frontend `GAIA CED` per i domini infrastrutturali NAS e Rete
