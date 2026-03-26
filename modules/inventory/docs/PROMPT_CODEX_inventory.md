# Prompt Codex — GAIA Inventario

> Regola strutturale vincolante
> GAIA usa un backend monolitico modulare. Il codice backend del dominio Inventario va creato in `backend/app/modules/inventory/`. Il frontend del modulo vive in `frontend/src/app/inventory/`. Non va creato alcun servizio backend separato.

> Da usare come system prompt o primo messaggio in una sessione di sviluppo dedicata al modulo Inventario.

---

## Contesto del progetto

Stai sviluppando **GAIA Inventario**, il modulo di inventario IT della piattaforma **GAIA**.

GAIA e una piattaforma multi-modulo con backend e frontend condivisi. I moduli applicativi convivono nello stesso monolite:

- **Accessi**
- **Network**
- **Inventory**
- **Catasto**

Il repository adotta una struttura canonica in cui il backend applicativo vive sotto `backend/` e i moduli di dominio sotto `backend/app/modules/`.

---

## Stack obbligatorio

**Backend**
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic
- pandas per import CSV con validazione
- openpyxl per export XLSX

**Frontend**
- Next.js
- React
- TypeScript
- TailwindCSS
- TanStack Table
- react-hook-form

**Infrastructure**
- Docker Compose gia esistente
- database e autenticazione condivisi con gli altri moduli
- worker/container separati solo se gia previsti dall'architettura GAIA; il modulo Inventario non introduce un nuovo backend autonomo

---

## Principi architetturali

- Il backend resta un **monolite modulare**: nessuna nuova feature di Inventario deve nascere nei path legacy fuori da `backend/app/modules/`, salvo eventuali wrapper di compatibilita strettamente necessari
- Il modulo backend va implementato in `backend/app/modules/inventory/`
- Il modulo frontend va implementato in `frontend/src/app/inventory/`
- Il punto di integrazione backend e il router di modulo: creare `backend/app/modules/inventory/router.py` e includerlo in `backend/app/api/router.py`
- Se il modulo cresce, le route di dettaglio possono essere organizzate sotto `backend/app/modules/inventory/routes/`, mantenendo `router.py` come entrypoint
- I file canonici del modulo backend sono:

```text
backend/app/modules/inventory/
  __init__.py
  router.py
  models.py
  schemas.py
  services.py
  repositories.py      # se utile
  routes/              # opzionale, se necessario
```

- I path legacy sotto `backend/app/api/routes/`, `backend/app/models/`, `backend/app/schemas/`, `backend/app/services/` non sono la destinazione primaria per nuove feature
- Auth, dipendenze FastAPI, sessione DB, logging e configurazione vanno riutilizzati dall'app esistente
- Alembic resta unico e condiviso: nuove migration in `backend/alembic/versions/` senza modificare revisioni esistenti
- Eliminazione sempre logica dove previsto dal dominio; evitare cancellazioni fisiche se non esplicitamente richieste dalla specifica
- L'integrazione con il modulo Network deve avvenire tramite database condiviso e modelli/tabelle del monolite, non tramite chiamate HTTP interne tra moduli

---

## Modello dati da implementare

Entita principali del modulo:

```text
inventory_devices
inventory_device_details
inventory_assignments
inventory_warranties
inventory_purchases
inventory_locations
inventory_attachments
inventory_network_links
```

Riferimento funzionale e campi iniziali: `modules/inventory/docs/PRD_inventory.md`, sezione modello dati.

Linee guida:

- `serial_number` univoco a livello DB e API
- `mac_address` opzionale ma univoco se presente
- una sola assegnazione attiva per dispositivo (`returned_at IS NULL`)
- path allegati salvati in forma relativa, non assoluta
- collegamento con Network preferibilmente tramite chiave di correlazione su `mac_address` o tabella di link esplicita, secondo il caso d'uso implementato

---

## API da implementare

Tutti gli endpoint del modulo devono essere esposti dal backend condiviso e pubblicati sotto prefisso `/inventory`.

Pattern architetturale:

- route dichiarate nel modulo Inventario
- business logic in `services.py`
- eventuale accesso dati dedicato in `repositories.py`
- schemi request/response in `schemas.py`
- modelli SQLAlchemy in `models.py`

Riferimento endpoint: `modules/inventory/docs/PRD_inventory.md`, sezione API.

---

## Pagine frontend da implementare

```text
/inventory
/inventory/devices
/inventory/devices/new
/inventory/devices/[id]
/inventory/devices/[id]/edit
/inventory/import
/inventory/warranties
/inventory/locations
```

Linee guida frontend:

- usare App Router nella struttura esistente di `frontend/src/app/`
- evitare applicazioni frontend separate o microfrontend
- mantenere coerenza con layout, auth flow, componenti condivisi e convenzioni gia presenti nel progetto
- tabelle con sorting, filtri e paginazione lato server quando il dataset lo richiede

---

## Requisiti UI/UX

- UI amministrativa sobria, leggibile, coerente con gli altri moduli GAIA
- form dispositivo organizzato in sezioni chiare: generale, tecnica, acquisto, assegnazione
- badge garanzia con semantica visiva chiara
- stato rete mostrato come informazione derivata dal modulo Network, non modificabile dall'utente Inventario
- import CSV guidato con preview, mapping colonne e validazione prima del commit
- responsive desktop-first; mobile secondario

---

## Priorita di sviluppo

1. Modello dati e migration Alembic
2. Router di modulo `backend/app/modules/inventory/router.py`
3. API CRUD dispositivi, assegnazioni, garanzie, sedi
4. Integrazione del router in `backend/app/api/router.py`
5. Frontend lista dispositivi e form creazione/modifica
6. Scheda dettaglio dispositivo
7. Import CSV con validazione
8. Export CSV/XLSX
9. Integrazione con Network nel database condiviso

---

## Vincoli tecnici

- non creare un backend separato per Inventario
- non introdurre nuovi path primari fuori da `backend/app/modules/inventory/` per il codice backend di dominio
- non duplicare meccanismi di auth, sessione DB o configurazione gia esistenti
- non usare chiamate API interne tra moduli dello stesso backend se il dato e gia disponibile nel database condiviso
- non hardcodare path assoluti per file allegati
- prima di introdurre wrapper legacy, privilegiare sempre la struttura canonica del modulo

---

## Istruzioni operative per Codex

Quando implementi il modulo Inventario:

- verifica prima la struttura reale del repository e segui i pattern gia usati in `backend/app/modules/accessi/`, `backend/app/modules/network/` e `backend/app/modules/catasto/`
- considera `backend/app/modules/inventory/` come superficie primaria del backend
- aggiungi il router di modulo in `backend/app/api/router.py`
- mantieni separati modelli, schemi, servizi e route
- evita refactor non richiesti ai moduli esistenti
- preserva compatibilita con il monolite condiviso e con il database unico
- usa `modules/inventory/docs/PRD_inventory.md` come riferimento funzionale di base, ma fai prevalere l'architettura canonica del repository quando trovi indicazioni obsolete nei documenti piu vecchi
