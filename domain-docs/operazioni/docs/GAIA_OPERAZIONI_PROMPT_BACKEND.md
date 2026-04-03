# GAIA Operazioni — Prompt Backend (Production Grade)

## Contesto

Stai lavorando nel repository **GAIA**, piattaforma interna del Consorzio di Bonifica dell'Oristanese.
L'architettura del progetto prevede:

- **backend unico** FastAPI
- **frontend unico** Next.js
- **database unico** PostgreSQL
- **monolite modulare**
- nuovo codice backend di dominio in `backend/app/modules/<modulo>/`

Per questo task devi implementare il nuovo modulo:

`backend/app/modules/operazioni/`

Il modulo **Operazioni** copre:
- gestione mezzi
- attività operatori
- segnalazioni che generano pratiche interne
- allegati multimediali
- integrazione GPS con valore di consuntivazione
- workflow approvativi
- monitoraggio quota storage allegati

Non creare microservizi separati. Non creare backend duplicati. Non introdurre stack alternativi.

---

## Documenti di riferimento

Usa come sorgente di verità questi file già predisposti:

- `GAIA_OPERAZIONI_DB_SCHEMA.md`
- `GAIA_OPERAZIONI_API_COMPLETE.md`
- `domain-docs/operazioni/docs/PRD_operazioni.md` oppure equivalente PRD del dominio
- `ARCHITECTURE.md`
- `PRD.md`

Se trovi incongruenze, privilegia:
1. schema DB del dominio Operazioni
2. API complete del dominio Operazioni
3. convenzioni architetturali del repository GAIA

---

## Obiettivo

Implementare il backend completo del modulo `operazioni` pronto per integrazione frontend, con:

- modelli SQLAlchemy
- schemi Pydantic
- repository/service layer
- router FastAPI
- gestione autorizzazioni per ruolo
- audit trail
- validazioni di business
- storage metadata per allegati
- quota monitoring
- supporto iniziale a GPS adapter astratto
- test backend essenziali
- migration Alembic

---

## Vincoli architetturali obbligatori

1. Usa il backend monolite esistente.
2. Crea tutto il nuovo dominio sotto `backend/app/modules/operazioni/`.
3. Non inserire nuovo codice di dominio nei path legacy fuori da `app/modules/`.
4. Le migration devono stare in `backend/alembic/versions/`.
5. Gli endpoint devono essere montati nel router API condiviso del backend.
6. Riusa pattern, naming e dipendenze già usate dagli altri moduli GAIA.
7. Mantieni separazione chiara tra:
   - models
   - schemas
   - services
   - repositories se il progetto li usa
   - routes
   - enums/constants
8. Tutti i model devono avere audit fields coerenti con il progetto:
   - `created_at`
   - `updated_at`
   - `created_by` se previsto
   - `updated_by` se previsto
9. Tutte le operazioni critiche devono essere loggate.
10. Il dato operatore dichiarato e il dato GPS rilevato devono restare distinti.

---

## Struttura desiderata

Crea una struttura simile a questa, adattandola alle convenzioni già presenti nel repository:

```text
backend/app/modules/operazioni/
  __init__.py
  module.py
  constants.py
  enums.py
  dependencies.py
  models/
    __init__.py
    vehicle.py
    activity.py
    report.py
    attachment.py
    workflow.py
    gps.py
    quota.py
  schemas/
    __init__.py
    vehicle.py
    activity.py
    report.py
    case.py
    attachment.py
    quota.py
    common.py
  repositories/
    __init__.py
    vehicle_repository.py
    activity_repository.py
    report_repository.py
    case_repository.py
    attachment_repository.py
  services/
    __init__.py
    vehicle_service.py
    activity_service.py
    report_service.py
    case_service.py
    attachment_service.py
    quota_service.py
    gps_service.py
    audit_service.py
  routes/
    __init__.py
    vehicles.py
    activities.py
    reports.py
    cases.py
    attachments.py
    dashboards.py
    admin.py
  utils/
    media.py
    gps.py
    pagination.py
    validators.py
```

Se il repository usa una struttura differente, adeguati al pattern esistente senza perdere chiarezza.

---

## Scope funzionale minimo da implementare

### 1. Mezzi
Implementa:
- anagrafica mezzo
- assegnazioni storiche a operatore o squadra
- sessioni utilizzo mezzo
- letture km iniziali/finali
- rifornimenti carburante
- manutenzioni
- documenti/scadenze solo lato metadata se il file storage fisico è già centralizzato altrove

Business rules:
- un mezzo non può avere due sessioni attive contemporanee salvo esplicita policy futura
- km finali devono essere >= km iniziali
- il sistema deve gestire assegnazione sia a `operator_id` sia a `team_id`
- le assegnazioni devono essere storicizzate

### 2. Attività
Implementa:
- catalogo attività fisso
- start attività
- stop attività
- associazione opzionale a mezzo e/o squadra
- note testuali
- note audio come allegato/attachment collegato
- workflow approvazione capo

Business rules:
- una attività nasce in stato `draft` o `submitted` a seconda del flusso deciso nel servizio
- chiusura attività imposta `ended_at`
- durata attività derivata dai timestamp, non salvata come dato manuale principale se non come cache/summary
- attività approvata non può essere modificata direttamente: eventuali cambi generano rettifica/evento

### 3. Segnalazioni e pratiche
Implementa:
- creazione field report
- generazione automatica pratica interna collegata
- assegnazione pratica
- presa in carico
- avanzamento stato
- chiusura pratica
- cronologia eventi pratica

Business rules:
- ogni segnalazione crea sempre una pratica
- categoria e severity sono obbligatorie
- la pratica deve avere storico eventi sempre persistito
- chiusura pratica richiede utente autorizzato e timestamp server-side

### 4. Allegati
Implementa metadata e API per:
- immagini
- audio
- video
- documenti

Vincoli:
- nessun blob nel database
- salva path, dimensione, mime type, checksum se disponibile
- collega allegati a report, activity o case
- prepara campo per file compresso/derivato se esiste preview

### 5. GPS
Implementa base astratta per:
- posizione raccolta da mini-app
- futuro adapter provider GPS mezzi
- summary GPS per attività e sessioni mezzo

Vincoli:
- non accoppiare il dominio a un vendor GPS specifico
- prevedi interfaccia/servizio adapter-based

### 6. Quota storage
Implementa:
- endpoint e servizio di quota usage
- calcolo spazio occupato allegati del modulo
- soglie warning: 70%, 85%, 95%
- stato critico oltre soglia configurata

---

## API da implementare

Implementa gli endpoint descritti nel file `GAIA_OPERAZIONI_API_COMPLETE.md`.

Almeno questi gruppi:
- `/api/operazioni/vehicles`
- `/api/operazioni/vehicle-assignments`
- `/api/operazioni/vehicle-usage-sessions`
- `/api/operazioni/vehicle-fuel-logs`
- `/api/operazioni/vehicle-maintenances`
- `/api/operazioni/activity-catalog`
- `/api/operazioni/activities`
- `/api/operazioni/activity-approvals`
- `/api/operazioni/reports`
- `/api/operazioni/cases`
- `/api/operazioni/case-events`
- `/api/operazioni/attachments`
- `/api/operazioni/storage`
- `/api/operazioni/dashboard`

Per ogni endpoint:
- request/response Pydantic tipizzate
- codici HTTP coerenti
- error handling coerente
- paginazione standard dove serve
- filtri query params

---

## Autorizzazioni

Integra controllo ruoli coerente con il sistema GAIA.

Ruoli minimi attesi:
- `admin`
- `capo_servizio` oppure equivalente reviewer/manager da riallineare con il sistema esistente
- `operatore`
- `viewer` opzionale per consultazione

Regole minime:
- operatore può creare e chiudere le proprie attività
- operatore può creare le proprie segnalazioni
- capo servizio può approvare/rifiutare attività nel proprio scope
- capo servizio può assegnare e chiudere pratiche
- admin ha visibilità globale

Non hardcodare scope se il progetto usa tabelle/claims diversi: prepara dipendenze estendibili.

---

## Audit trail

Aggiungi logging e storico su eventi critici:
- creazione attività
- chiusura attività
- approvazione/rifiuto attività
- creazione segnalazione
- generazione pratica
- cambio stato pratica
- assegnazione pratica
- upload metadata allegato
- superamento soglia storage

Se il progetto ha già un pattern di audit centralizzato, riusalo.

---

## Migration Alembic

Genera migration iniziale del modulo Operazioni basata sullo schema DB fornito.

Requisiti:
- naming coerente
- foreign key esplicite
- index su colonne di filtro
- enum PostgreSQL dove utile oppure check constraint coerenti con il progetto
- supporto soft delete solo se già usato nel repository

Aggiungi indici almeno su:
- status
- created_at
- operator_id
- team_id
- vehicle_id
- case_id
- severity
- activity_catalog_id

---

## Test

Aggiungi test backend essenziali:

### Unit / service tests
- creazione activity
- stop activity
- approvazione activity
- creazione report con pratica automatica
- cambio stato pratica
- calcolo quota storage

### API tests
- create/list vehicles
- start/stop activity
- create report
- list cases
- storage usage endpoint

Se il repository usa pytest, segui i pattern già presenti.

---

## Output richiesto

Devi produrre:
1. codice backend completo del modulo
2. migration Alembic
3. router integrato nell'app
4. test minimi
5. eventuale seed catalogo attività base
6. breve README del modulo in `domain-docs/operazioni/` o posizione equivalente

---

## Criteri di qualità

Il risultato deve essere:
- coerente con architettura GAIA
- leggibile
- tipizzato
- estendibile
- pronto a essere consumato dal frontend
- senza TODO vaghi lasciati nei punti critici

Evita semplificazioni che rompano il dominio, ad esempio:
- niente singolo campo generico JSON al posto dei modelli core
- niente endpoint monolitici “do everything”
- niente storage file nel DB
- niente logica GPS hardcoded su un provider specifico

---

## Extra richiesto

Alla fine del lavoro restituisci anche:
- elenco file creati/modificati
- note sulle decisioni architetturali adottate
- eventuali assunzioni da validare
- eventuali gap rispetto al repository se hai dovuto adattarti a naming o auth esistenti
