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
| RF-NET-01 | MUST | Scansione LAN tramite nmap con rilevamento IP, MAC, hostname, porte aperte e classificazione iniziale |
| RF-NET-02 | MUST | Scansione schedulata configurabile (default: ogni 15 minuti) |
| RF-NET-03 | MUST | Salvataggio snapshot con timestamp e delta rispetto alla scan precedente |
| RF-NET-04 | SHOULD | Lettura alternativa via tabella ARP del gateway (fallback senza privilegi root) |
| RF-NET-05 | SHOULD | Rilevamento sistema operativo tramite OS fingerprinting nmap |
| RF-NET-06 | SHOULD | Enrichment best-effort via SNMP, mDNS e NetBIOS per hostname, modello, vendor e sistema operativo quando disponibili |
| RF-NET-07 | SHOULD | Ingestione syslog da firewall Sophos per eventi di sicurezza e correlazione con i dispositivi LAN |

### 2.2 Mappa dispositivi

L'interfaccia presenta i dispositivi rilevati su una mappa interattiva organizzata per piano/sede. Le planimetrie sono caricate dall'amministratore in formato SVG o immagine.

| Requisito | Priorità | Descrizione |
|-----------|----------|-------------|
| RF-MAP-01 | MUST | Lista tabulare dispositivi con IP, MAC, hostname, vendor, stato, ultimo visto |
| RF-MAP-02 | MUST | Filtri per stato (online/offline), piano, tipo dispositivo |
| RF-MAP-02B | MUST | Possibilità di assegnare manualmente `display_name` e `asset_label` a ogni dispositivo |
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

### 2.6 Enrichment e naming device

- Ogni dispositivo puo avere un nome operativo assegnato manualmente (`display_name`) e una etichetta inventariale (`asset_label`)
- Quando presente un collegamento a `application_users`, il label operativo mostrato in UI viene risolto dal profilo utente (`full_name`, fallback `username`)
- Il detentore del dispositivo puo essere modificato manualmente dalla scheda device, sganciando o riassegnando l'apparato a un diverso `application_users`
- I device non piu in uso possono essere marcati come `rotamati`: restano a storico ma escono dal monitoraggio operativo attivo
- Il backend conserva anche il nome osservato automaticamente (`hostname`) e la sua sorgente (`hostname_source`)
- Il sistema salva le sorgenti di arricchimento effettivamente usate (`metadata_sources`) per rendere ispezionabile il dato
- L'ordine di preferenza del nome osservato e: `nmap`, `snmp`, `netbios`, `mdns`, `dns`
- SNMP usa community globali e opzionalmente profili per subnet
- `network_devices.assigned_user_id` collega esplicitamente il device all'utente applicativo quando il mapping e noto

---

## 3. Modello dati

### 3.1 Tabelle principali

| Tabella | Descrizione |
|---------|-------------|
| `network_scans` | Snapshot di scansione: `id, started_at, completed_at, status, devices_count` |
| `network_devices` | Dispositivo rilevato: `id, scan_id, ip, mac, hostname, hostname_source, display_name, asset_label, vendor, model_name, metadata_sources, os_guess, is_online, first_seen, last_seen` |
| `network_alerts` | Alert generato: `id, device_id, alert_type, severity, created_at, resolved_at` |
| `network_firewalls` | Anagrafica firewall gestiti: `id, vendor, name, model_name, management_ip, status, last_seen_at` |
| `network_firewall_events` | Eventi ricevuti da firewall: `id, firewall_id, device_id, source, event_type, severity, src_ip, dst_ip, observed_at` |
| `network_firewall_metrics` | Metriche puntuali firewall: `id, firewall_id, metric_key, metric_value, severity, observed_at` |
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
| `FIREWALL_EVENT` | Evento critico ricevuto dal firewall Sophos |

---

## 4. API Endpoints

| Endpoint | Descrizione |
|----------|-------------|
| `GET /network/scans` | Lista snapshot scansioni con paginazione |
| `POST /network/scans` | Avvia nuova scansione manuale |
| `GET /network/scans/{id}` | Dettaglio snapshot con lista dispositivi |
| `GET /network/scans/{id}/diff/{id2}` | Confronto tra due snapshot |
| `GET /network/statistics` | Vista aggregata su rete, dispositivi e navigazione firewall |
| `GET /network/devices` | Lista dispositivi con filtri (stato, piano, vendor) |
| `GET /network/devices/{id}` | Dettaglio dispositivo con storico, posizione e riepilogo traffico Sophos ultime 24h |
| `PATCH /network/devices/{id}` | Aggiorna naming operativo, detentore, ciclo di vita e metadati manuali del dispositivo |
| `GET /network/alerts` | Lista alert attivi e risolti |
| `PATCH /network/alerts/{id}` | Aggiorna stato alert (risolto/ignorato) |
| `GET /network/firewalls` | Lista firewall registrati nel modulo rete |
| `GET /network/firewalls/{id}/events` | Storico eventi del firewall |
| `POST /network/firewalls/sophos/syslog` | Ingestione applicativa di un evento syslog Sophos |
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
    - NETWORK_SCAN_PORTS=22,80,161,443,445,3389
    - NETWORK_ENRICHMENT_TIMEOUT_SECONDS=1.0
    - NETWORK_SNMP_COMMUNITIES=public
    - NETWORK_SNMP_COMMUNITY_PROFILES=[]
    - DATABASE_URL=${DATABASE_URL}
```

Formato `NETWORK_SNMP_COMMUNITY_PROFILES`:

```json
[
  { "cidr": "192.168.1.0/24", "communities": ["public", "rete-lan"] },
  { "cidr": "192.168.10.0/24", "communities": ["switch-mgmt"] }
]
```

### 5.2 Stack tecnologico

| Componente | Tecnologia |
|------------|------------|
| Scanner backend | Python · python-nmap · scapy (fallback ARP) |
| Ingestione firewall | Parser syslog Sophos + correlazione IP verso `network_devices` |
| Scheduler | APScheduler integrato in FastAPI |
| API modulo | FastAPI router `/network` — aggiunto al backend monolite esistente |
| Frontend | Next.js — nuova sezione `/network` nel frontend esistente |
| Planimetria UI | React + SVG overlay con drag-and-drop (`react-draggable`) |
| Database | PostgreSQL — nuove tabelle migrate con Alembic |

### 5.2B Collector Sophos syslog

- servizio dedicato `sophos-syslog` separato dal backend HTTP
- listener UDP configurabile via `NETWORK_SOPHOS_SYSLOG_BIND_HOST` e `NETWORK_SOPHOS_SYSLOG_PORT`
- il listener accetta payload syslog con header RFC3164/RFC5424, rimuove il prefisso e passa il body all’ingestor Sophos
- il client IP UDP viene usato come fallback per il `management_ip` del firewall se non configurato esplicitamente

### 5.2C Poller Sophos SNMP

- servizio dedicato `sophos-snmp` separato dal backend HTTP
- polling periodico configurabile via `NETWORK_SOPHOS_SNMP_INTERVAL_SECONDS`
- metriche standard lette da MIB supportate ufficialmente da Sophos Firewall: `sysName`, `sysDescr`, `sysUpTime`, `ifNumber`
- supporto a OID custom via `NETWORK_SOPHOS_SNMP_CUSTOM_OIDS` per aggiungere metriche del MIB Sophos reale dopo il download dal firewall

### 5.2D Correlazione traffico per dispositivo

- il dettaglio dispositivo aggrega gli eventi `network_firewall_events` delle ultime 24 ore correlati per `device_id`, `src_ip` o `dst_ip`
- il riepilogo espone traffico in ingresso/uscita, eventi consentiti/bloccati, peer principali e ultimi eventi traffico
- i peer pubblici vengono arricchiti con label leggibili usando, in ordine: `domain` / hostname da `url` del log Sophos, reverse DNS, fallback RDAP/organizzazione

### 5.2D-bis Statistiche rete

- la sezione `/network/statistics` aggrega, su finestra temporale configurabile, lo stato dei dispositivi e la navigazione osservata dal firewall
- espone KPI su dispositivi attivi, rotamati, assegnati, non assegnati, monitorati, traffico in ingresso/uscita, eventi allowed e blocked
- include breakdown per tipi dispositivo, vendor, uffici, assegnatari, severita, protocolli, eventi Sophos e regole firewall
- include top list per domini navigati, destinazioni esterne e device sorgente piu attivi
- include timeline per fascia oraria degli eventi e del volume di traffico

### 5.2E Import censimento dispositivi

- script operativo: `backend/scripts/import_network_census_xlsx.py`
- sorgente supportata: Excel con colonne `TELEFONO INTERNO`, `NOME`, `SERVIZIO`, `IP`, `LICENZA OFFICE`
- matching primario per `ip_address` sui device gia presenti in GAIA
- campi aggiornati senza toccare i metadati tecnici di discovery: `display_name`, `location_hint`, `notes`, `is_known_device`
- il contesto di censimento viene tracciato in `notes` con marcatore `[Censimento CBO]`

### 5.2F Mapping device -> application_users

- script operativo: `backend/scripts/sync_network_devices_to_application_users.py`
- matching primario per normalizzazione del nome persona tra `network_devices.display_name` e profilo/username/email local-part di `application_users`
- lo script puo:
  - valorizzare `network_devices.assigned_user_id`
  - copiare `display_name` verso `application_users.full_name` quando assente
  - copiare `location_hint` verso `application_users.office_location` quando assente
  - estrarre l'interno telefonico da `notes` e salvarlo in `application_users.phone_extension`
- il label operativo esposto in UI usa questo ordine:
  1. `application_users.full_name`
  2. `application_users.username`
  3. `network_devices.display_name`
  4. `network_devices.hostname`
  5. `network_devices.ip_address`
- i device possono assumere `lifecycle_state=active|retired`
- quando un device viene marcato `retired`, GAIA:
  - azzera `assigned_user_id`
  - disattiva `is_monitored`
  - salva `retired_at`
  - lo esclude dai conteggi operativi di dashboard

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
domain-docs/network/docs/
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
