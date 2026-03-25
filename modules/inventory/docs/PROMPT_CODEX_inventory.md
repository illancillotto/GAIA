# Prompt Codex — GAIA Inventario (IT Inventory)

> Da usare come system prompt o primo messaggio in una sessione di sviluppo dedicata.

---

## Contesto del progetto

Stai sviluppando **GAIA Inventario**, il modulo di inventario IT della piattaforma **GAIA** per il Consorzio di Bonifica dell'Oristanese.

GAIA è una piattaforma IT governance con tre moduli:
- **GAIA Accessi** — NAS Audit (già completato, repo esistente)
- **GAIA Rete** — Network Monitor (modulo parallelo)
- **GAIA Inventario** — IT Inventory (questo modulo)

Il repository si trova su `github.com/illancillotto/GAIA`.

---

## Stack obbligatorio

**Backend**
- FastAPI, SQLAlchemy, Alembic, PostgreSQL
- pandas (import CSV con validazione)
- openpyxl (export XLSX)

**Frontend**
- Next.js, React, TypeScript, TailwindCSS
- TanStack Table
- react-hook-form (form gestione dispositivi)

**Infrastructure**
- Docker Compose esistente — nessun container aggiuntivo necessario

---

## Principi architetturali

- Il modulo si aggiunge al backend e frontend **esistenti** come router/sezione aggiuntiva
- **NON** creare un backend separato: aggiungere `app/routers/inventory.py` al FastAPI esistente
- **NON** creare un frontend separato: aggiungere `frontend/src/app/inventory/` al Next.js esistente
- Auth JWT condivisa: riutilizzare il middleware esistente senza modifiche
- Alembic: creare nuove migration in `alembic/versions/` senza toccare quelle esistenti
- Eliminazione sempre **logica** (`status = decommissioned`), mai DELETE fisico sul DB
- Integrazione GAIA Rete: leggere da `network_devices` tramite JOIN su `mac_address`, **non** API call

---

## Modello dati da implementare

```
inventory_devices         — anagrafica dispositivi
inventory_device_details  — campi tecnici categoria-specifici (EAV)
inventory_assignments     — assegnazioni a utenti
inventory_warranties      — garanzie e scadenze
inventory_purchases       — dati acquisto
inventory_locations       — sedi e uffici
inventory_attachments     — allegati (fatture, schede tecniche)
inventory_network_links   — collegamento inventario ↔ rete
```

Schema completo in `modules/inventory/docs/PRD.md` sezione 3.

---

## API da implementare

Tutti gli endpoint sotto il prefisso `/inventory`.  
Lista completa in `modules/inventory/docs/PRD.md` sezione 4.

---

## Pagine frontend da implementare

```
/inventory                    — dashboard
/inventory/devices            — lista dispositivi
/inventory/devices/new        — form creazione
/inventory/devices/[id]       — scheda dettaglio
/inventory/devices/[id]/edit  — form modifica
/inventory/import             — import CSV wizard
/inventory/warranties         — alert garanzie
/inventory/locations          — gestione sedi
```

---

## Requisiti UI/UX

- Stile coerente con GAIA Accessi: professionale, orientato alla lettura amministrativa, no effetti decorativi
- Form dispositivo: suddiviso in sezioni/tab (Generale, Tecnica, Acquisto, Assegnazione)
- Badge garanzia: verde (valida), arancione (scadenza < 60 gg), rosso (scaduta)
- Badge stato rete (da GAIA Rete): verde online, grigio offline, bianco non collegato
- Tabelle: TanStack Table con sorting, filtering e paginazione lato server
- Import CSV: wizard a step con preview mapping colonne e validazione prima del salvataggio
- Responsive desktop-first; mobile non prioritario

---

## Priorità di sviluppo

1. Modello dati + migration Alembic
2. API FastAPI router `/inventory` (CRUD + assegnazioni + garanzie)
3. Frontend: lista dispositivi + form creazione
4. Frontend: scheda dettaglio dispositivo
5. Import CSV con wizard di mapping
6. Dashboard garanzie con alert
7. Export CSV/XLSX
8. Integrazione con GAIA Rete (MAC matching + badge stato rete)

---

## Vincoli e note tecniche

- Il **numero seriale** deve essere univoco nel sistema (constraint DB + validazione API)
- L'import CSV deve gestire duplicati per seriale: **aggiorna** se esiste, **crea** se nuovo
- Un dispositivo può avere **una sola assegnazione attiva** alla volta (`returned_at IS NULL`)
- Il **MAC address** è opzionale ma se presente deve essere univoco
- Alert garanzie: calcolare daily tramite APScheduler (condiviso con modulo Rete se già attivo)
- File allegati: salvare in volume Docker, path relativo in DB, mai path assoluti hardcoded
- Integrazione GAIA Rete: JOIN diretto su `network_devices.mac_address`, non chiamate API inter-modulo
- Lo stato rete nel dettaglio dispositivo è read-only: viene da GAIA Rete, non modificabile qui
