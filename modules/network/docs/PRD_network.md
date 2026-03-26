# GAIA Rete — Network Monitor
## Product Requirements Document v1.0

> Regola repository
> Il modulo Rete appartiene al backend monolite modulare GAIA. Nuovo codice backend Rete va in `app/modules/network/`.

> Consorzio di Bonifica dell'Oristanese — Marzo 2026  
> Documento interno — uso riservato

---

## 1. Overview del modulo

GAIA Rete è il modulo di monitoraggio della rete locale all'interno della piattaforma GAIA. Fornisce visibilità in tempo reale sui dispositivi presenti sulla LAN del Consorzio, con una mappa interattiva distribuita per piano e un sistema di alert per anomalie di rete.

> **Posizione nel sistema**  
> GAIA Rete è il secondo modulo della piattaforma. Condivide autenticazione JWT, database PostgreSQL e infrastruttura Docker con GAIA Accessi, GAIA Catasto e GAIA Inventario.
> Il backend GAIA e organizzato come **monolite modulare**: un solo servizio FastAPI con moduli logici distinti.

### 1.1 Obiettivi

- Centralizzare la visibilità sui dispositivi attivi sulla rete LAN del Consorzio
- Fornire una mappa interattiva dei dispositivi distribuita per piano/sede
- Rilevare automaticamente dispositivi nuovi o non autorizzati
- Allertare su dispositivi attesi non raggiungibili
- Conservare lo storico delle scansioni per analisi di tendenza
- Integrarsi con GAIA Inventario tramite MAC address matching

### 1.2 Non obiettivi MVP

- Modifica automatica di configurazioni di rete
- Gestione VLAN o firewall rules
- Deep packet inspection o analisi del traffico
- Integrazione con sistemi SNMP complessi (rinviata a fase successiva)
- App mobile o notifiche push

---

## 2. Requisiti funzionali

### 2.1 Scansione LAN

Il backend esegue scansioni periodiche della rete locale e salva i risultati come snapshot nel database.

| Requisito | Priorità | Descrizione |
|-----------|----------|-------------|
| RF-NET-01 | MUST | Scansione LAN tramite nmap con rilevamento IP, MAC, hostname, vendor |
| RF-NET-02 | MUST | Scansione schedulata configurabile (default: ogni 15 minuti) |
| RF-NET-03 | MUST | Salvataggio snapshot con timestamp e delta rispetto alla scan precedente |
| RF-NET-04 | SHOULD | Lettura alternativa via tabella ARP del gateway (fallback senza privilegi root) |
| RF-NET-05 | SHOULD | Rilevamento sistema operativo tramite OS fingerprinting nmap |
| RF-NET-06 | COULD | Integrazione SNMP per router e switch gestiti |

### 2.2 Mappa dispositivi

L'interfaccia presenta i dispositivi rilevati su una mappa interattiva organizzata per piano/sede. Le planimetrie sono caricate dall'amministratore in formato SVG o immagine.

| Requisito | Priorità | Descrizione |
|-----------|----------|-------------|
| RF-MAP-01 | MUST | Lista tabulare dispositivi con IP, MAC, hostname, vendor, stato, ultimo visto |
| RF-MAP-02 | MUST | Filtri per stato (online/offline), piano, tipo dispositivo |
| RF-MAP-03 | SHOULD | Planimetria per piano con posizionamento manuale drag-and-drop dei dispositivi |
| RF-MAP-04 | SHOULD | Caricamento planimetria in formato SVG o PNG da parte dell'admin |
| RF-MAP-05 | SHOULD | Badge stato real-time (verde/rosso) sovrapposto alla planimetria |
| RF-MAP-06 | COULD | Raggruppamento automatico dispositivi per subnet |

### 2.3 Alert e notifiche

| Requisito | Priorità | Descrizione |
|-----------|----------|-------------|
| RF-ALT-01 | MUST | Alert per dispositivo nuovo non presente in Inventario |
| RF-ALT-02 | MUST | Alert per dispositivo atteso (in Inventario) non rilevato da N scansioni |
| RF-ALT-03 | SHOULD | Dashboard alert con filtro per severità e stato (aperto/risolto) |
| RF-ALT-04 | COULD | Notifica email per alert critici |

### 2.4 Storico scansioni

| Requisito | Priorità | Descrizione |
|-----------|----------|-------------|
| RF-HIST-01 | MUST | Elenco snapshot con data, numero dispositivi rilevati, delta |
| RF-HIST-02 | MUST | Dettaglio snapshot: lista completa dispositivi in quel momento |
| RF-HIST-03 | SHOULD | Confronto tra due snapshot con evidenza di apparizioni/sparizioni |
| RF-HIST-04 | COULD | Grafico storico dispositivi attivi nel tempo |

### 2.5 Integrazione con GAIA Inventario

- Il sistema tenta il matching automatico tra IP/MAC rilevati e dispositivi in Inventario
- I dispositivi non matchati vengono presentati come "non riconosciuti" per revisione manuale
- Un dispositivo in Inventario mostra il suo stato di rete corrente nella scheda dettaglio

---

## 3. Modello dati

### 3.1 Tabelle principali

| Tabella | Descrizione |
|---------|-------------|
| `network_scans` | Snapshot di scansione: `id, started_at, completed_at, status, devices_count` |
| `network_devices` | Dispositivo rilevato: `id, scan_id, ip, mac, hostname, vendor, os_guess, is_online, first_seen, last_seen` |
| `network_alerts` | Alert generato: `id, device_id, alert_type, severity, created_at, resolved_at` |
| `floor_plans` | Planimetria: `id, name, floor_number, building, image_path, created_at` |
| `device_positions` | Posizione su planimetria: `device_id, floor_plan_id, x, y, updated_at` |
| `device_inventory_links` | Collegamento rete-inventario: `network_device_id, inventory_device_id, match_type (auto/manual)` |

### 3.2 Tipi di alert

| Tipo | Descrizione |
|------|-------------|
| `NEW_DEVICE` | Dispositivo rilevato non presente in Inventario |
| `MISSING_DEVICE` | Dispositivo in Inventario non visto da più di N scan |
| `IP_CONFLICT` | Due MAC diversi associati allo stesso IP in scan ravvicinate |
| `VENDOR_MISMATCH` | Vendor rilevato diverso da quello registrato in Inventario |

---

## 4. API Endpoints

| Endpoint | Descrizione |
|----------|-------------|
| `GET /network/scans` | Lista snapshot scansioni con paginazione |
| `POST /network/scans` | Avvia nuova scansione manuale |
| `GET /network/scans/{id}` | Dettaglio snapshot con lista dispositivi |
| `GET /network/scans/{id}/diff/{id2}` | Confronto tra due snapshot |
| `GET /network/devices` | Lista dispositivi con filtri (stato, piano, vendor) |
| `GET /network/devices/{id}` | Dettaglio dispositivo con storico e posizione |
| `GET /network/alerts` | Lista alert attivi e risolti |
| `PATCH /network/alerts/{id}` | Aggiorna stato alert (risolto/ignorato) |
| `GET /network/floor-plans` | Lista planimetrie disponibili |
| `POST /network/floor-plans` | Carica nuova planimetria |
| `GET /network/floor-plans/{id}/devices` | Dispositivi posizionati su una planimetria |
| `PUT /network/devices/{id}/position` | Aggiorna posizione dispositivo su planimetria |

---

## 5. Architettura tecnica

### 5.1 Scanner LAN

> **Configurazione Docker consigliata**  
> Il container dello scanner richiede `NET_RAW` capability per nmap in modalità SYN scan.  
> In alternativa, usare nmap in modalità ping scan (`-sn`) che non richiede root, oppure leggere la tabella ARP tramite SSH sul gateway.

```yaml
# docker-compose.yml — servizio scanner
scanner:
  build:
    context: ./backend
  command: python -m app.scripts.network_scanner
  cap_add:
    - NET_RAW
    - NET_ADMIN
  depends_on:
    - postgres
  environment:
    - NETWORK_SCAN_INTERVAL_SECONDS=900
    - NETWORK_RANGE=192.168.1.0/24
    - DATABASE_URL=${DATABASE_URL}
```

### 5.2 Stack tecnologico

| Componente | Tecnologia |
|------------|------------|
| Scanner backend | Python · python-nmap · scapy (fallback ARP) |
| Scheduler | APScheduler integrato in FastAPI |
| API modulo | FastAPI router `/network` — aggiunto al backend monolite esistente |
| Frontend | Next.js — nuova sezione `/network` nel frontend esistente |
| Planimetria UI | React + SVG overlay con drag-and-drop (`react-draggable`) |
| Database | PostgreSQL — nuove tabelle migrate con Alembic |

### 5.3 Struttura cartelle

```
backend/app/
  modules/
    network/
      router.py
      models.py
      schemas.py
      services.py
      scheduler.py
      scanner_script.py
frontend/src/app/
  network/
    page.tsx
    devices/
    floor-plan/
    alerts/
    scans/
modules/network/docs/
  PRD_network.md
  PROMPT_CODEX_network.md
```

I path legacy `app/api/routes/network.py`, `app/models/network.py`, `app/schemas/network.py`,
`app/services/network_*.py` restano come wrapper di compatibilita.

### 5.4 Piano di migrazione backend

1. Introdurre `app/modules/` come struttura canonica.
2. Migrare i nuovi moduli direttamente in `app/modules/<modulo>/`.
3. Tenere i path storici come wrapper fino al completamento del refactor.
4. Considerare obsoleti i riferimenti storici al vecchio path backend.

---

## 6. Pagine frontend

| Route | Contenuto |
|-------|-----------|
| `/network` | Dashboard: dispositivi online/offline, alert attivi, ultima scan, pulsante scan manuale |
| `/network/devices` | Tabella dispositivi con filtri stato, piano, vendor, ricerca hostname/IP/MAC |
| `/network/devices/[id]` | Dettaglio: info, storico visto, posizione planimetria, link Inventario |
| `/network/floor-plan` | Selezione piano + planimetria interattiva con badge dispositivi |
| `/network/alerts` | Lista alert con filtro tipo/severità, azione risolvi/ignora |
| `/network/scans` | Storico scansioni con delta e confronto snapshot |
| `/network/scans/[id]` | Dettaglio snapshot: lista completa dispositivi |

---

## 7. Non obiettivi MVP

- Modifica automatica di configurazioni di rete
- Gestione VLAN o firewall rules
- Deep packet inspection
- Integrazione SNMP complessa
- Notifiche push
- App mobile
