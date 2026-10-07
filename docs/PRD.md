# GAIA Product Requirements Document

> Nota repository
> Questo documento descrive il prodotto GAIA a livello di piattaforma.
> I PRD di dominio restano in `domain-docs/<dominio>/docs/`.

## 1. Visione

GAIA e la piattaforma interna del Consorzio di Bonifica dell'Oristanese per la
governance di accessi, rete, inventario, catasto e anagrafica soggetti tramite
un backend monolitico modulare, un frontend condiviso e un database unico.

## 2. Obiettivo di prodotto

La gestione account in `/gaia/users` supporta il ruolo applicativo `ced`,
subordinato ad Admin e Super Admin e limitato a utenti standard e moduli
delegabili. NAS/Rete, account privilegiati e override amministrativi restano
esclusi. Requisiti ed evidenze nel dominio Accessi:
`domain-docs/accessi/docs/CED_USER_MANAGEMENT_VALIDATION.md`.

Fornire un unico punto di accesso operativo per:

- audit e review degli accessi al NAS
- monitoraggio continuo della rete LAN
- gestione dell'inventario IT
- automazione delle visure catastali e della relativa documentazione
- governance centralizzata dei layer GIS operativi, con PostGIS come sorgente
  ufficiale, QGIS come client tecnico e shapefile NAS come export/backup
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

### 3.3.1 Dotazioni operative

- beni del Consorzio, assegnazione OrgUnit e custodia temporanea operatore
- presa/restituzione/passaggio, storico, link Network/Vehicle e rotta QR
- dominio distinto da Inventory, che resta invariato
- MVP implementato, gate della change isolata superato: requisiti/residui in
  `domain-docs/dotazioni/docs/IMPLEMENTATION_PLAN.md`, evidenze in
  `domain-docs/dotazioni/docs/GATE_CLOSURE_2026-10-03.md`; baseline globale
  Wiki/MCP da riconciliare separatamente, nessun deploy

### MCP LAN e distribuzione trust HTTPS

- Perimetro corrente: `gaia.lan` / `192.168.1.110`, solo LAN, Claude Desktop
  locale; ChatGPT e connettori cloud da valutare senza pubblicazione Internet.
- Richiesti anche Claude Code e Codex, configurati localmente in stdio con
  dati sintetici; tool calling dal modello da collaudare. ChatGPT puo
  richiedere endpoint pubblico o Secure MCP Tunnel approvato, non attivato.
- Installer della CA dedicata per Windows amd64/ARM64 e guida Linux/macOS,
  link download sulla login solo con manifest corrispondente al pin atteso.
- Verifica impronta con il CED tramite canale indipendente; nessun bypass
  TLS/SmartScreen, nessuna chiave privata nei pacchetti, firma Authenticode
  e collaudo nativo richiesti prima della distribuzione gestita.
- Certificato server firmato e verificato; HTTPS/gateway non ancora rilasciati.
  Accettazione richiede trust/SAN, HTTP 308, discovery, Data 401 senza token,
  consenso/tool calling/revoca dal client approvato e hotfix preservati.
- NAS usa permessi reali con mapping/freshness ACL approvati; Trasparenza
  richiede fonte/catalogo approvato. Nessuna esposizione reale gia attiva.
- Stato, evidenze e gate: `domain-docs/mcps/CURRENT_STATUS_2026-10-06.md`.
- Letture MCP live sviluppate al 2026-10-07: `domain-docs/mcps/LIVE_READS_2026-10-07.md`; catalogo stdio opt-in separato, nessun rilascio CED o accesso NAS/Trasparenza incluso.
- Verifica/consolidamento completati, gate globale FAIL: `domain-docs/mcps/FINAL_VALIDATION_2026-10-07.md` e `domain-docs/mcps/PROGRESS.md`; nessuna nuova feature introdotta nella chiusura.

### 3.4 Catasto

- gestione credenziali SISTER
- batch e richieste singole di visura
- worker browser-based con gestione CAPTCHA
- archivio PDF e tracciamento realtime avanzamento

### 3.4.1 Elaborazioni (integrazioni operative)

- integrazione Capacitas (inVOLTURE) per workflow di elaborazione e ricerca
- monitor operativo centralizzato dei job trasversali, inclusa la sync massiva AUTODOC del parco mezzi con stato, contatori ed azioni di rilancio

### 3.4.2 GIS Platform

- catalogo layer GIS trasversale
- permessi per layer per visualizzazione, annotazione, editing e approvazione
- annotazioni e note in tabelle GAIA/PostGIS dedicate, non negli shapefile
- change request e audit per modifiche ufficiali
- export shapefile ZIP versionato verso NAS come copia di sicurezza, con
  manifest JSON e checksum SHA-256
- catalogo operativo read-only in `/gis/catalogo`, distinto dal workspace `/catasto/gis`
- gestione permessi layer per ruolo/utente con audit e override utente
- lifecycle annotazioni `open`, `in_review`, `closed`, `rejected` con filtri per
  layer, feature e status
- workflow change request `submitted`, `needs_changes`, `approved`, `rejected`,
  `applied`, con validazione payload, no-op Catasto e apply reale solo su layer
  non Catasto con opt-in controlled edit
- governance QGIS Desktop con policy ruoli DB, view read-only e runbook operativo
- decisione OGC: nessun server OGC in produzione di default; POC QGIS Server
  read-only prima di eventuale GeoServer
- onboarding multi-dominio: Riordino e registrato nel catalogo `/gis` come
  registry read-only non geometrico, senza pubblicazione QGIS o export shapefile
- dashboard stato catalogo: metriche layer/workspace/source, health issue su
  permessi, PostGIS, policy QGIS e registry applicativi
- scheduling export NAS: job opt-in, retention per layer sui soli export
  schedulati e ultimi export visibili nel dashboard catalogo

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
- worker tecnici separati per famiglia di carico, ad esempio `elaborazioni-worker-visure`, `elaborazioni-worker-runtime`, `elaborazioni-worker-autodoc` e scanner LAN
- regola di piattaforma: ogni nuovo worker introdotto nel repository deve avere una coda o famiglia di job dedicata e non deve condividere il polling con worker eterogenei gia esistenti

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


## Requisito Presenze completato — 2026-10-01

- [x] Contratto booleano `meal_voucher_manual` in LAN e poll outbound.
- [x] Persistenza con lock, audit idempotente, autore canonico e permessi esistenti.
- [x] Compatibilità KM/reperibilità e conteggio manuale OR automatico.
- [x] Test di comportamento e coverage statement/branch 100% nel perimetro modificato.

Stato operativo, verifiche e residui: `domain-docs/presenze/docs/GATE_MEAL_VOUCHER_ENTRY.md`. Nessuna modifica al frontend GAIA;
il comando mensile è nella console GATE.


## Turnisti GAIA/GATE — ciclo locale 2026-10-03

- [x] Assegnazioni persistenti per giorno/intervallo/mese: acquaiolo, telecontrollo, revoca.
- [x] Teorico locale 420 minuti; buono da almeno 420 minuti ordinari effettivi dal 26/08/2026, senza duplicazione manuale.
- [x] Precedenza GATE, import futuri, API LAN/outbound e controlli di accesso.
- [x] UI giornaliere GAIA, badge e protezione delle assegnazioni GATE.
- [ ] Rilascio autorizzato e collaudo produzione; nessun deploy nel ciclo corrente.

Specifica: `domain-docs/presenze/docs/TURNISTI_GAIA_GATE.md`.
Verifiche, matrice test e residui: `domain-docs/presenze/docs/TURNISTI_COORDINATED_VERIFICATION_2026-10-05.md`.
