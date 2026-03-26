# GAIA Inventario — IT Inventory
## Product Requirements Document v1.0

> Regola repository
> GAIA Inventario non introduce un backend separato. Usa il backend monolite modulare condiviso.

> Consorzio di Bonifica dell'Oristanese — Marzo 2026  
> Documento interno — uso riservato

---

## 1. Overview del modulo

GAIA Inventario è il modulo di gestione dell'inventario IT all'interno della piattaforma GAIA. Fornisce un registro centralizzato e strutturato di tutti i dispositivi hardware e software del Consorzio, con tracciamento delle assegnazioni, garanzie e scadenze.

> **Posizione nel sistema**  
> GAIA Inventario è il terzo modulo della piattaforma. Condivide autenticazione JWT, database PostgreSQL e infrastruttura Docker con GAIA Accessi e GAIA Rete. Si integra con GAIA Rete tramite MAC address matching per arricchire automaticamente i dati dei dispositivi.

### 1.1 Obiettivi

- Centralizzare l'anagrafica di tutti i dispositivi IT del Consorzio in un unico registro
- Tracciare assegnazioni dei dispositivi a utenti e uffici/sedi
- Gestire le scadenze di garanzia con alert preventivi
- Supportare import da CSV per migrazione dati esistenti
- Collegarsi a GAIA Rete per l'arricchimento automatico con dati di rete (IP, MAC, stato)
- Collegarsi a GAIA Accessi per associare dispositivi a utenti NAS
- Produrre report e export per audit e acquisti

### 1.2 Non obiettivi MVP

- Integrazione automatica con portali fornitori o sistemi di acquisto
- Gestione software licensing automatizzata
- MDM (Mobile Device Management)
- Barcode/QR scanning da app mobile
- Workflow di approvazione acquisti

---

## 2. Requisiti funzionali

### 2.1 Anagrafica dispositivi

Il nucleo del modulo è il registro dei dispositivi. Ogni dispositivo ha una scheda completa con dati tecnici, amministrativi e di assegnazione.

| Requisito | Priorità | Descrizione |
|-----------|----------|-------------|
| RF-INV-01 | MUST | CRUD completo: creazione, lettura, modifica, eliminazione logica |
| RF-INV-02 | MUST | Campi obbligatori: tipo, marca, modello, numero seriale, stato |
| RF-INV-03 | MUST | Campi opzionali: MAC address, IP manuale, sistema operativo, note |
| RF-INV-04 | MUST | Assegnazione a utente (con data inizio/fine) e sede/ufficio |
| RF-INV-05 | MUST | Import da CSV con mapping colonne configurabile |
| RF-INV-06 | SHOULD | Storico assegnazioni: chi ha avuto il dispositivo e quando |
| RF-INV-07 | SHOULD | Upload allegati (fattura, scheda tecnica) per dispositivo |
| RF-INV-08 | COULD | QR code generato per ogni dispositivo (per etichettatura fisica) |

### 2.2 Dati amministrativi e garanzie

| Requisito | Priorità | Descrizione |
|-----------|----------|-------------|
| RF-GAR-01 | MUST | Data acquisto, fornitore, numero ordine/fattura, costo |
| RF-GAR-02 | MUST | Data inizio e fine garanzia |
| RF-GAR-03 | MUST | Alert dashboard per garanzie in scadenza entro 30/60/90 giorni |
| RF-GAR-04 | SHOULD | Tipo garanzia (standard, estesa, on-site) |
| RF-GAR-05 | COULD | Link diretto alla pagina supporto fornitore |

### 2.3 Tipologie di dispositivi

| Categoria | Campi specifici aggiuntivi |
|-----------|---------------------------|
| Computer (desktop/laptop) | CPU, RAM, storage, OS, versione OS |
| Server | CPU, RAM, storage, rack unit, IP management |
| Stampante/Scanner | Tipo connessione, contatore pagine |
| Switch/Router/AP | Numero porte, VLAN supportate, firmware |
| Monitor | Pollici, risoluzione, tipo pannello |
| Telefono fisso/VoIP | Interno, protocollo SIP |
| Altro | Descrizione libera |

### 2.4 Ricerca e filtraggio

| Requisito | Priorità | Descrizione |
|-----------|----------|-------------|
| RF-SRC-01 | MUST | Ricerca full-text su seriale, hostname, modello, note |
| RF-SRC-02 | MUST | Filtri per: categoria, stato, utente assegnato, sede, fornitore |
| RF-SRC-03 | MUST | Filtro garanzie in scadenza (30/60/90 gg o scadute) |
| RF-SRC-04 | SHOULD | Filtro per stato rete (online/offline — da GAIA Rete) |
| RF-SRC-05 | SHOULD | Ordinamento per qualsiasi colonna della tabella |

### 2.5 Export e report

| Requisito | Priorità | Descrizione |
|-----------|----------|-------------|
| RF-EXP-01 | MUST | Export CSV della lista dispositivi con tutti i campi |
| RF-EXP-02 | SHOULD | Export XLSX con formattazione (colori per stato garanzia) |
| RF-EXP-03 | SHOULD | Report garanzie in scadenza (PDF stampabile) |
| RF-EXP-04 | COULD | Report assegnazioni per utente o per ufficio |

### 2.6 Integrazione con GAIA Rete

- Matching automatico tra MAC address in Inventario e MAC rilevati da GAIA Rete
- La scheda dispositivo mostra stato rete corrente (online/offline, IP rilevato, ultima vista)
- I dispositivi rilevati in rete non presenti in Inventario vengono segnalati per revisione
- Il link può essere creato manualmente in caso di mancato match automatico

---

## 3. Modello dati

### 3.1 Tabelle principali

| Tabella | Descrizione |
|---------|-------------|
| `inventory_devices` | Dispositivo: `id, category, brand, model, serial_number, mac_address, status, location_id, notes, created_at` |
| `inventory_device_details` | Dettagli tecnici categoria-specifici: `device_id, field_name, field_value` (EAV pattern) |
| `inventory_assignments` | Assegnazione: `id, device_id, user_id, assigned_at, returned_at, notes` |
| `inventory_warranties` | Garanzia: `id, device_id, start_date, end_date, warranty_type, vendor_contact` |
| `inventory_purchases` | Acquisto: `id, device_id, purchase_date, vendor, order_number, invoice_number, cost` |
| `inventory_locations` | Sede/ufficio: `id, name, building, floor, description` |
| `inventory_attachments` | Allegati: `id, device_id, filename, file_path, uploaded_at` |
| `inventory_network_links` | Collegamento inventario-rete: `inventory_device_id, network_device_id, match_type` |

### 3.2 Stati dispositivo

| Stato | Descrizione |
|-------|-------------|
| `active` | In uso, assegnato o disponibile |
| `in_repair` | In manutenzione o riparazione |
| `stored` | In magazzino, non assegnato |
| `decommissioned` | Dismesso, non più in uso |
| `lost` | Smarrito o rubato |

---

## 4. API Endpoints

| Endpoint | Descrizione |
|----------|-------------|
| `GET /inventory/devices` | Lista dispositivi con filtri e paginazione |
| `POST /inventory/devices` | Crea nuovo dispositivo |
| `GET /inventory/devices/{id}` | Dettaglio con garanzia, assegnazioni, link rete |
| `PUT /inventory/devices/{id}` | Aggiorna dispositivo |
| `DELETE /inventory/devices/{id}` | Eliminazione logica (status = decommissioned) |
| `POST /inventory/devices/import` | Import massivo da CSV |
| `GET /inventory/devices/{id}/assignments` | Storico assegnazioni dispositivo |
| `POST /inventory/assignments` | Crea nuova assegnazione |
| `PATCH /inventory/assignments/{id}/return` | Registra restituzione |
| `GET /inventory/warranties/expiring` | Garanzie in scadenza (parametro: giorni) |
| `GET /inventory/locations` | Lista sedi/uffici |
| `POST /inventory/locations` | Crea sede/ufficio |
| `GET /inventory/export` | Export CSV/XLSX con filtri |
| `GET /inventory/stats` | Statistiche aggregate per categoria, stato, sede |

---

## 5. Architettura tecnica

### 5.1 Stack tecnologico

| Componente | Tecnologia |
|------------|------------|
| API modulo | FastAPI router `/inventory` — aggiunto al backend esistente |
| Frontend | Next.js — nuova sezione `/inventory` nel frontend esistente |
| Import CSV | Python `csv` + `pandas` per validazione e mapping colonne |
| Export | `openpyxl` per XLSX, `csv` stdlib per CSV |
| Database | PostgreSQL — nuove tabelle migrate con Alembic |
| File storage | Volume Docker locale per allegati (path configurabile) |

### 5.2 Struttura cartelle

```
modules/inventory/
  backend/
    routers/inventory.py    # FastAPI router
    models/inventory.py     # SQLAlchemy models
    schemas/inventory.py    # Pydantic schemas
    services/inventory.py   # business logic
    services/import_csv.py  # CSV import con validazione
    services/export.py      # CSV/XLSX export
    services/warranty.py    # alert garanzie
  frontend/
    pages/inventory/
      index.tsx             # dashboard
      new.tsx               # form nuovo dispositivo
      import.tsx            # import CSV wizard
      [id]/index.tsx        # dettaglio dispositivo
      [id]/edit.tsx         # modifica dispositivo
      warranties.tsx        # alert garanzie
      locations.tsx         # gestione sedi
    components/
      DeviceForm.tsx        # form riutilizzabile
      DeviceCard.tsx        # scheda dispositivo
      WarrantyBadge.tsx     # badge stato garanzia
      NetworkStatusBadge.tsx # badge stato rete (da GAIA Rete)
  docs/
    PRD.md
    PROMPT_CODEX.md
```

---

## 6. Pagine frontend

| Route | Contenuto |
|-------|-----------|
| `/inventory` | Dashboard: totali per categoria, alert garanzie, ultimi dispositivi aggiunti |
| `/inventory/devices` | Tabella dispositivi con ricerca, filtri multipli, export |
| `/inventory/devices/new` | Form creazione: sezioni Generale, Tecnica, Acquisto, Assegnazione |
| `/inventory/devices/[id]` | Scheda completa: dati, garanzia, storico assegnazioni, stato rete, link NAS |
| `/inventory/devices/[id]/edit` | Form modifica dispositivo |
| `/inventory/import` | Upload CSV con preview mapping colonne e validazione prima dell'import |
| `/inventory/warranties` | Lista garanzie con filtro scadenza, ordinamento, export |
| `/inventory/locations` | Gestione sedi e uffici (CRUD) |

---

## 7. Non obiettivi MVP

- Integrazione automatica con portali fornitori
- Gestione software licensing
- MDM
- Barcode/QR scanning da app mobile
- Workflow approvazione acquisti
- Notifiche push
