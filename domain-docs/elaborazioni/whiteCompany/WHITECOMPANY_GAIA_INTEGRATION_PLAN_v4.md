# WhiteCompany → GAIA — Piano di integrazione organico v4

> Stato: v4 — 10 aprile 2026
> Corretto su: path Python reali, org_chart in accessi, wc_id su category, sync_state table,
>              sequenza implementazione, rimozione import Excel posticipata,
>              path doc reale, refuso Fase 4, semantica review_status, shape /sync/status,
>              warehouse_request DDL, regola applicativa rejected, step ridondante Fase 3,
>              path completi uniformati su tutte le fasi
>
> Documento di riferimento scraping:
> `domain-docs/elaborazioni/whiteCompany/WHITECOMPANY_integration.md`

---

## 1. Path e naming canonici

Il provider vive già nel repository con questo naming:

| Elemento | Path / valore |
|---|---|
| Package Python | `backend/app/modules/elaborazioni/bonifica_oristanese/` |
| Route canonica | `/elaborazioni/bonifica` |
| Route compatibile | `/elaborazioni/bonifica-oristanese` |
| Helper datatable | `backend/app/modules/shared/datatable_helpers.py` |
| App registry | `backend/app/modules/elaborazioni/bonifica_oristanese/apps/registry.py` |
| Client base | `backend/app/modules/elaborazioni/bonifica_oristanese/apps/client.py` |
| UI workspace | `frontend/src/components/elaborazioni/settings-workspace.tsx` |

Tutti i riferimenti nel codice usano `bonifica_oristanese`, non `bonifica`.

---

## 2. Distribuzione dati nei moduli GAIA

| Sorgente White | Modulo GAIA | Tabelle target |
|---|---|---|
| Segnalazioni | `operazioni` | `field_report`, `internal_case`, `internal_case_event` |
| Tipologie segnalazione | `operazioni` | `field_report_category` (+`wc_id`) |
| Automezzi/attrezzature | `operazioni` | `vehicle` (+campi `wc_*`) |
| Rifornimenti | `operazioni` | `vehicle_fuel_log` (+`wc_id`) |
| Presa in carico automezzi | `operazioni` | `vehicle_usage_session` (+`wc_id`) |
| Aree territoriali | `operazioni` | `wc_area` (nuova lookup) |
| Utenti operatori | `operazioni` | `wc_operator` (nuova staging) |
| Consorziati | `utenze` | `bonifica_user_staging` → review → `ana_subjects` |
| Organigrammi | **`accessi`** | `wc_org_chart`, `wc_org_chart_entry` (nuove, in accessi) |
| Richieste magazzino | `inventory` | `warehouse_request` (nuova) |

### Nota organigrammi → `accessi`

Gli organigrammi White rappresentano la struttura gerarchica interna del Consorzio:
chi appartiene a quale area, quale ruolo ricopre, chi è referente di cosa.
Questa è informazione di **governance degli accessi e delle competenze**,
non anagrafica soggetti. Va in `accessi` perché:
- determina chi può fare cosa nel sistema (base per future regole di autorizzazione)
- è ortogonale all'anagrafica consorziati (`utenze`)
- il modulo accessi già gestisce strutture organizzative (NAS, permessi, review)

`utenze` espone solo dati anagrafici di persone fisiche/giuridiche.
Se in futuro serve un join org_chart ↔ ana_subjects, si fa tramite FK in `wc_org_chart_entry`.

---

## 3. Modello dati — nuove tabelle e campi

### 3.1 Nuova tabella `wc_sync_job` (trasversale)

Ogni run di sync scrive un record qui. Sostituisce la risposta calcolata al volo
per `/sync/status`.

```sql
CREATE TABLE wc_sync_job (
    id              UUID PRIMARY KEY,
    entity          VARCHAR(50) NOT NULL,   -- "reports" | "vehicles" | "users" | ...
    status          VARCHAR(20) NOT NULL,   -- "running" | "completed" | "failed"
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    records_synced  INTEGER,
    records_skipped INTEGER,
    records_errors  INTEGER,
    error_detail    TEXT,
    triggered_by    INTEGER REFERENCES application_users(id),
    params_json     JSONB                   -- date_from, date_to, filtri usati
);
CREATE INDEX ON wc_sync_job (entity, started_at DESC);
```

### 3.2 Modulo `operazioni`

#### Nuova tabella `wc_area`

```sql
CREATE TABLE wc_area (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wc_id        INTEGER UNIQUE NOT NULL,
    name         VARCHAR(200) NOT NULL,
    color        VARCHAR(7),
    is_district  BOOLEAN NOT NULL DEFAULT FALSE,
    description  TEXT,
    lat          NUMERIC(10,7),
    lng          NUMERIC(10,7),
    polygon      TEXT,
    wc_synced_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`field_report.area_code` rimane testo libero per retrocompatibilità.
Aggiungere FK opzionale `wc_area_id UUID REFERENCES wc_area(id)` su `field_report`.

#### Nuova tabella `wc_operator`

```sql
CREATE TABLE wc_operator (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wc_id        INTEGER UNIQUE NOT NULL,
    username     VARCHAR(100),
    email        VARCHAR(200),
    first_name   VARCHAR(100),
    last_name    VARCHAR(100),
    tax          VARCHAR(20),
    role         VARCHAR(50),
    enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    gaia_user_id INTEGER REFERENCES application_users(id),
    wc_synced_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### Nuovi campi su `field_report_category`

```python
wc_id   = Column(Integer, nullable=True, unique=True, index=True)
# Stabilizza l'upsert: se White rinomina la categoria,
# il match avviene su wc_id (stabile) non su slugify(name) (fragile).
# Lo slug/code viene aggiornato solo se wc_id corrisponde.
```

#### Nuovi campi su `vehicle`

```python
wc_id            = Column(Integer, nullable=True, index=True)
# NON unique=True: il tenant è unico (CBO), ma lasciare margine
# per importazioni manuali o ambienti di test senza collisioni.
# Unicità garantita a livello applicativo in sync_vehicles.py.
wc_vehicle_id    = Column(String(50), nullable=True)   # targa / n. telaio White
vehicle_type_wc  = Column(String(20), nullable=True)   # "automezzo" | "attrezzatura"
source_system    = Column(String(20), nullable=True, default="gaia")
wc_synced_at     = Column(DateTime(timezone=True), nullable=True)
```

#### Nuovi campi su `vehicle_fuel_log`

```python
wc_id        = Column(Integer, nullable=True, index=True)
operator_name = Column(String(200), nullable=True)   # nome testuale operatore White
wc_synced_at = Column(DateTime(timezone=True), nullable=True)
```

#### Nuovi campi su `vehicle_usage_session`

```python
wc_id        = Column(Integer, nullable=True, index=True)
km_start     = Column(Integer, nullable=True)
km_end       = Column(Integer, nullable=True)
operator_name = Column(String(200), nullable=True)
wc_synced_at = Column(DateTime(timezone=True), nullable=True)
```

### 3.3 Modulo `utenze`

#### Nuova tabella `bonifica_user_staging`

```sql
CREATE TABLE bonifica_user_staging (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wc_id            INTEGER UNIQUE NOT NULL,
    username         VARCHAR(100),
    email            VARCHAR(200),
    user_type        VARCHAR(20),        -- "company" | "private"
    business_name    VARCHAR(300),
    first_name       VARCHAR(100),
    last_name        VARCHAR(100),
    tax              VARCHAR(20),
    phone            VARCHAR(30),
    mobile           VARCHAR(30),
    role             VARCHAR(50),        -- "Consorziato"
    enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    wc_synced_at     TIMESTAMPTZ,
    -- stato revisione
    -- "new"      = tax non trovato in ana_subjects → attende approvazione per creare
    -- "matched"  = tax trovato, tutti i campi allineati → nessuna azione richiesta
    -- "mismatch" = tax trovato, divergenze rilevate → attende revisione manuale
    -- "rejected" = escluso esplicitamente dall'operatore
    review_status    VARCHAR(20) NOT NULL DEFAULT 'new',
    matched_subject_id UUID REFERENCES ana_subjects(id),
    mismatch_fields  JSONB,             -- {"email": {"wc": "x", "gaia": "y"}}
    reviewed_by      INTEGER REFERENCES application_users(id),
    reviewed_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON bonifica_user_staging (review_status);
CREATE INDEX ON bonifica_user_staging (tax);
```

**Semantica**: il matching avviene al momento della sync in `sync_consorziati.py`,
che scrive direttamente `new` / `matched` / `mismatch` in base al confronto con `ana_subjects`.
Non esiste uno stato `pending` intermedio: il record è già classificato quando entra in staging.

**Regola applicativa per re-sync** — in `sync_consorziati.py`:
```python
# Su record esistenti con review_status='rejected': aggiorna i campi WC
# (wc_synced_at, dati anagrafici) ma NON resettare review_status.
# La decisione di esclusione è dell'operatore, non di White.
if existing and existing.review_status == 'rejected':
    _update_wc_fields_only(existing, row)   # no review_status touch
    continue
```

**Approvazione**: bulk per `review_status = 'new'` (crea nuovo `ana_subjects`),
singola/manuale per `review_status = 'mismatch'` (aggiorna `ana_subjects` esistente dopo verifica).
La scrittura effettiva in `ana_subjects` avviene solo via endpoint esplicito con approvazione.

### 3.4 Modulo `accessi`

#### Nuove tabelle organigrammi

```sql
CREATE TABLE wc_org_chart (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wc_id        INTEGER UNIQUE NOT NULL,
    chart_type   VARCHAR(20) NOT NULL,   -- "area" | "user"
    name         VARCHAR(200) NOT NULL,
    wc_synced_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE wc_org_chart_entry (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_chart_id    UUID NOT NULL REFERENCES wc_org_chart(id) ON DELETE CASCADE,
    wc_id           INTEGER NOT NULL,
    label           VARCHAR(200),
    role            VARCHAR(100),
    wc_operator_id  UUID REFERENCES wc_operator(id),   -- FK cross-modulo via DB condiviso
    wc_area_id      UUID REFERENCES wc_area(id),       -- FK cross-modulo via DB condiviso
    sort_order      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.5 Modulo `inventory`

#### Nuova tabella `warehouse_request`

```sql
CREATE TABLE warehouse_request (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    wc_id            INTEGER     UNIQUE NOT NULL,
    wc_report_id     INTEGER,
    field_report_id  UUID        REFERENCES field_report(id),
    report_type      VARCHAR(200),
    reported_by      VARCHAR(200),
    requested_by     VARCHAR(200),
    report_date      TIMESTAMPTZ,
    request_date     TIMESTAMPTZ,
    archived         BOOLEAN     NOT NULL DEFAULT FALSE,
    status_active    BOOLEAN     NOT NULL DEFAULT TRUE,
    wc_synced_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 4. Migration Alembic — naming e raggruppamento

Una migration per dominio tematico, non una per tabella.
Ordine rispetta le FK tra moduli (DB condiviso).

```
20260411_NNNN_add_wc_sync_job.py
  → wc_sync_job

20260411_NNNN_add_wc_area_and_operator.py
  → wc_area, wc_operator
  → campi wc_* su field_report_category, vehicle, vehicle_fuel_log, vehicle_usage_session
  → wc_area_id su field_report (nullable FK)

20260411_NNNN_add_bonifica_user_staging.py
  → bonifica_user_staging

20260411_NNNN_add_wc_org_charts.py
  → wc_org_chart, wc_org_chart_entry
  (dopo wc_area e wc_operator per le FK)

20260411_NNNN_add_warehouse_request.py
  → warehouse_request
  (dopo field_report per la FK)
```

---

## 5. Endpoint API GAIA

### Sync orchestrator

```
POST /elaborazioni/bonifica/sync/run
     body: { entities: list[str] | "all", date_from?: date, date_to?: date }
     auth: admin
     response: { job_id: uuid, entity: { status, started_at } }

GET  /elaborazioni/bonifica/sync/status
     → legge l'ultimo wc_sync_job per entità, non calcola al volo
     response:
     {
       "entities": {
         "reports": {
           "entity":          "reports",
           "status":          "completed",        // running | completed | failed | never
           "last_started_at": "2026-04-10T11:00:00Z",
           "last_finished_at":"2026-04-10T11:02:14Z",
           "records_synced":  826,
           "records_skipped": 12,
           "records_errors":  0,
           "error_detail":    null
         },
         "vehicles": { ... },
         "report_types": { ... },
         ...
       }
     }
     // Se un'entità non ha ancora mai girato: status="never", tutti i campi null
```

### Operazioni

```
GET  /api/operazioni/areas              ← lista wc_area
GET  /api/operazioni/areas/{id}
GET  /api/operazioni/operators          ← lista wc_operator
GET  /api/operazioni/operators/{id}
```

### Utenze — staging consorziati

```
GET  /api/utenze/bonifica-staging
     params: review_status, search, page, page_size
GET  /api/utenze/bonifica-staging/{id}
POST /api/utenze/bonifica-staging/{id}/approve
POST /api/utenze/bonifica-staging/{id}/reject
POST /api/utenze/bonifica-staging/bulk-approve
     body: { ids: list[uuid] }   ← solo per review_status="new"
```

### Inventory

```
GET  /api/inventory/warehouse-requests
GET  /api/inventory/warehouse-requests/{id}
```

---

## 6. Sequenza di implementazione

### Fase 1 — Infrastruttura (prerequisito tutto il resto)
1. Migration `wc_sync_job`
2. Migration `wc_area_and_operator` + campi `wc_*` su tabelle esistenti
3. `apps/report_types/client.py` — scraping tipologie (semplice, 38 record, pagina singola)
4. `apps/reports/client.py` — scraping segnalazioni con paginazione
5. `operazioni/services/sync_report_types.py` — upsert su `wc_id` (non su slug)
6. `operazioni/services/sync_white.py` — adattato da `import_white.py`, input `List[dict]`
7. Orchestratore `POST /elaborazioni/bonifica/sync/run` con scrittura su `wc_sync_job`
8. `GET /elaborazioni/bonifica/sync/status` da `wc_sync_job`
9. Test: sync idempotente segnalazioni, verifica wc_sync_job

> Import Excel (`import_reports.py`, `import_white.py`, modal frontend) rimane attivo
> finché `sync_white.py` non raggiunge parità funzionale e idempotenza verificata.
> Rimozione in Fase 2 post-validazione.

### Fase 2 — Segnalazioni stabili + pulizia Excel
10. Validazione idempotenza sync segnalazioni su dataset reale
11. Rimozione `routes/import_reports.py`
12. Rimozione `services/import_white.py`
13. Rimozione `frontend/src/components/operazioni/import-white-modal.tsx`
14. Rimozione `importWhiteReports()` da `client.ts`
15. Rimozione bottone import Excel dalla UI
> `services/parsing.py` e migration `add_white_import_fields_to_field_report` restano.

### Fase 3 — Automezzi e log operativi
16. `backend/app/modules/elaborazioni/bonifica_oristanese/apps/vehicles/client.py`
17. `backend/app/modules/elaborazioni/bonifica_oristanese/apps/refuels/client.py`
18. `backend/app/modules/elaborazioni/bonifica_oristanese/apps/taken_charge/client.py`
19. `backend/app/modules/operazioni/services/sync_vehicles.py`
20. `backend/app/modules/operazioni/services/sync_areas.py`
21. Test sync veicoli + fuel_log + usage_session

### Fase 4 — Operatori
22. `backend/app/modules/elaborazioni/bonifica_oristanese/apps/users/client.py` — fetch ruoli operativi (escluso Consorziato)
23. `backend/app/modules/operazioni/services/sync_operators.py` — upsert `wc_operator`
24. API `GET /api/operazioni/operators`

### Fase 5 — Consorziati (rischio dati alto, last)
25. Migration `bonifica_user_staging`
26. `backend/app/modules/elaborazioni/bonifica_oristanese/apps/users/client.py` — paginazione completa (~12.000+ record, `filter_role=Consorziato`)
27. `backend/app/modules/utenze/services/sync_consorziati.py` — staging + mismatch check su `tax`
28. Endpoint `/utenze/bonifica-staging` + UI revisione
29. Bulk approve per `review_status=new`
30. Singola approve/reject per `review_status=mismatch`

### Fase 6 — Magazzino e organigrammi
31. Migration `warehouse_request` + `wc_org_charts`
32. `backend/app/modules/elaborazioni/bonifica_oristanese/apps/warehouse_requests/client.py`
33. `backend/app/modules/inventory/services/sync_warehouse.py`
34. `backend/app/modules/elaborazioni/bonifica_oristanese/apps/org_charts/client.py`
35. `backend/app/modules/accessi/services/sync_org_charts.py`
36. API inventory warehouse requests
37. Background job: link `warehouse_request.field_report_id` via `wc_report_id`

### Fase 7 — Frontend sync dashboard
38. Blocco stato sync in `/elaborazioni/settings` (workspace Bonifica già presente)
39. Pagina `/elaborazioni/bonifica/sync` con tabella `wc_sync_job` per entità
40. UI revisione consorziati `/utenze/bonifica-staging`

---

## 7. Logica di sync per entità — dettaglio

### Segnalazioni
- Upsert su `external_code` (già nel model)
- Prima sync `report_types`, poi `reports`
- `field_report_category`: upsert su `wc_id` (stabile); aggiorna `name`/`code` se cambiati
- `area_code` testo libero + `wc_area_id` FK opzionale se `wc_area` già sincronizzata
- `parsing.py` riusato invariato per date e tempo completamento

### Automezzi
- Upsert applicativo su `wc_id` (non constraint DB unique per sicurezza)
- Non sovrascrivere campi modificati manualmente in GAIA
- Aggiorna solo `wc_vehicle_id`, `vehicle_name`, `vehicle_type_wc`, `wc_synced_at`

### Tipologie segnalazione
- Upsert su `wc_id` — se White rinomina, aggiorna `name` e ricalcola `code` (slug)
- Non disabilitare categorie native GAIA (senza `wc_id`)

### Consorziati
- Fetch completo con `filter_role=Consorziato` e `filter_enabled=` (tutti, abilitati + disabilitati)
- Paginazione step 250 su `recordsTotal` (~12.000+)
- Match su `tax` (CF/PIVA) con `ana_subjects`
- `review_status` scritto direttamente al momento della sync:
  - `new`      = tax non trovato in `ana_subjects`
  - `matched`  = tax trovato, tutti i campi allineati
  - `mismatch` = tax trovato, divergenze in `mismatch_fields`
  - `rejected` = escluso esplicitamente dall'operatore (solo via UI, non sovrascrivere in re-sync)

### Richieste magazzino
- Link automatico `field_report_id` in background post-sync:
  `WHERE wc_report_id = field_report.external_code::int`
