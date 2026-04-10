# GAIA — Implementazione modulo PDND Decesso

## Contesto progetto

Stai lavorando su GAIA, monolite modulare FastAPI + Next.js del Consorzio di Bonifica
dell'Oristanese.

- Backend: `backend/app/` — moduli sotto `app/modules/<modulo>/`, servizi in `app/services/`
- Frontend: `frontend/src/app/` e `frontend/src/components/`
- Migration Alembic: `backend/alembic/versions/`
- Pattern di riferimento per questo intervento: modulo `elaborazioni/capacitas` (credenziali,
  fascia oraria, batch) e modulo `utenze/anagrafica` (soggetti, `ana_subjects`, `ana_persons`)

Prima di scrivere qualsiasi codice leggi i seguenti file per capire i pattern reali:
- `backend/app/modules/elaborazioni/router.py`
- `backend/app/modules/elaborazioni/capacitas_routes.py`
- `backend/app/services/elaborazioni_capacitas.py`
- `backend/app/modules/utenze/models.py`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `frontend/src/components/elaborazioni/settings-workspace.tsx`
- Il componente di dettaglio soggetto nella modal utenze (cerca nei file sotto
  `frontend/src/components/utenze/` o `frontend/src/app/utenze/`)

---

## Obiettivo

Implementare la verifica decesso via PDND/ANPR (servizi C030 + C004) integrata in GAIA.

Il flusso è:
1. C030 — dato un codice fiscale, ottiene l'`idANPR`
2. C004 — dato l'`idANPR` (o il CF come fallback), verifica se il soggetto risulta deceduto
3. Gestione EN122: soggetto non in ANPR — se EN122 su entrambi C030 e C004, il soggetto è
   deceduto con posizione anagrafica rimossa

Le credenziali PDND (`CLIENT_ID`, `KID`, `PRIVATE_KEY_PATH`, `PURPOSE_ID_C030`,
`PURPOSE_ID_C004`, `ENV`) rimangono in `.env` e vengono lette tramite `app/core/config.py`.
La configurazione dello scheduler (fascia oraria, limite giornaliero, active flag) viene
salvata in DB in una tabella dedicata.

---

## Parte 1 — Backend

### 1.1 — Variabili di configurazione

In `backend/app/core/config.py`, aggiungere alla classe `Settings`:

```python
pdnd_env: str = "prod"
pdnd_client_id: str = ""
pdnd_kid: str = ""
pdnd_private_key_path: str = ""
pdnd_purpose_id_c030: str = ""
pdnd_purpose_id_c004: str = ""
```

Nomi env corrispondenti (automatici con pydantic-settings):
`PDND_ENV`, `PDND_CLIENT_ID`, `PDND_KID`, `PDND_PRIVATE_KEY_PATH`,
`PDND_PURPOSE_ID_C030`, `PDND_PURPOSE_ID_C004`.

Aggiungere anche a `backend/.env.example`:

```env
# PDND ANPR — Verifica Decesso
PDND_ENV=prod
PDND_CLIENT_ID=
PDND_KID=
PDND_PRIVATE_KEY_PATH=/opt/gaia/secrets/pdnd_private_key.pem
PDND_PURPOSE_ID_C030=
PDND_PURPOSE_ID_C004=
```

### 1.2 — Nuove colonne su `ana_subjects`

In `backend/app/modules/utenze/models.py`, aggiungere alla classe `AnagraficaSubject`
DOPO il campo `updated_at`:

```python
deceduto: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
ultima_verifica_decesso_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
```

### 1.3 — Migration Alembic

Creare `backend/alembic/versions/<timestamp>_add_pdnd_decesso.py`.

Recupera la revision corrente con `alembic heads` e impostala come `down_revision`.

L'`upgrade()` deve:
1. `op.add_column("ana_subjects", Column("deceduto", Boolean, nullable=True))`
2. `op.add_column("ana_subjects", Column("ultima_verifica_decesso_at", DateTime(timezone=True), nullable=True))`
3. Creare la tabella `pdnd_decesso_config`:
   - `id` Integer PK (valore fisso 1 — riga singleton)
   - `active` Boolean NOT NULL DEFAULT false
   - `allowed_hours_start` Integer NOT NULL DEFAULT 8
   - `allowed_hours_end` Integer NOT NULL DEFAULT 18
   - `daily_limit` Integer NOT NULL DEFAULT 90
   - `updated_at` DateTime(timezone=True) server_default now()
4. Creare la tabella `pdnd_decesso_jobs`:
   - `id` UUID PK
   - `run_date` Date NOT NULL INDEX
   - `status` VARCHAR(32) NOT NULL DEFAULT 'pending'
     (valori: pending | running | completed | failed | cancelled)
   - `total_subjects` Integer NOT NULL DEFAULT 0
   - `processed` Integer NOT NULL DEFAULT 0
   - `deceased` Integer NOT NULL DEFAULT 0
   - `not_found` Integer NOT NULL DEFAULT 0
   - `errors` Integer NOT NULL DEFAULT 0
   - `triggered_by` VARCHAR(64) NOT NULL DEFAULT 'scheduler'
   - `error_message` Text nullable
   - `started_at` DateTime(timezone=True) nullable
   - `completed_at` DateTime(timezone=True) nullable
   - `created_at` DateTime(timezone=True) server_default now()
5. Creare la tabella `pdnd_decesso_results`:
   - `id` UUID PK
   - `job_id` UUID FK → `pdnd_decesso_jobs.id` ON DELETE CASCADE INDEX
   - `subject_id` UUID FK → `ana_subjects.id` ON DELETE SET NULL INDEX nullable
   - `codice_fiscale` VARCHAR(32) NOT NULL INDEX
   - `id_anpr` VARCHAR(64) nullable
   - `deceduto` Boolean nullable
   - `stato_http` Integer nullable
   - `messaggio` Text NOT NULL DEFAULT ''
   - `errori_json` JSONB nullable
   - `checked_at` DateTime(timezone=True) server_default now()

Il `downgrade()` deve invertire tutto nell'ordine corretto.

### 1.4 — Package `backend/app/modules/elaborazioni/pdnd/`

Creare i seguenti file dentro questa directory.

---

#### `__init__.py`
```python
"""Modulo PDND ANPR — verifica decesso soggetti anagrafica."""
```

---

#### `models.py`

SQLAlchemy models per le tre tabelle create in migrazione:
`PdndDecssoConfig`, `PdndDecssoJob`, `PdndDecssoResult`.

- `PdndDecssoResult` ha una relazione `back_populates` con `PdndDecssoJob`
- Importa `Base` da `app.core.database`
- Usa `Mapped` / `mapped_column` (stile SQLAlchemy 2.x, coerente con il resto del progetto)

---

#### `schemas.py`

Schemi Pydantic (`from_attributes=True` dove necessario):

- `PdndConfigRead` — tutti i campi di `PdndDecssoConfig`
- `PdndConfigUpdate` — tutti i campi opzionali (per PATCH)
- `PdndJobRead` — tutti i campi di `PdndDecssoJob`
- `PdndResultRead` — tutti i campi di `PdndDecssoResult`
- `PdndJobDetail(PdndJobRead)` — include `results: list[PdndResultRead]`
- `PdndDailyStatus` — `today_count`, `daily_limit`, `remaining`, `is_in_window`,
  `scheduler_active`

---

#### `client.py`

Client ANPR che implementa il flusso C030 + C004.

URL base per ambiente:

```python
TOKEN_URLS = {
    "prod": "https://auth.interop.pagopa.it/token.oauth2",
    "val":  "https://auth.uat.interop.pagopa.it/token.oauth2",
}
CLIENT_ASSERTION_AUDIENCES = {
    "prod": "auth.interop.pagopa.it/client-assertion",
    "val":  "auth.uat.interop.pagopa.it/client-assertion",
}
BASE_URLS = {
    "C030": {
        "prod": "https://modipa.anpr.interno.it/govway/rest/in/MinInternoPortaANPR-PDND/C030-servizioAccertamentoIdUnicoNazionale/v1",
        "val":  "https://modipa-val.anpr.interno.it/govway/rest/in/MinInternoPortaANPR-PDND/C030-servizioAccertamentoIdUnicoNazionale/v1",
    },
    "C004": {
        "prod": "https://modipa.anpr.interno.it/govway/rest/in/MinInternoPortaANPR-PDND/C004-servizioVerificaDichDecesso/v1",
        "val":  "https://modipa-val.anpr.interno.it/govway/rest/in/MinInternoPortaANPR-PDND/C004-servizioVerificaDichDecesso/v1",
    },
}
RESOURCE_PATH = "/anpr-service-e002"
```

Dettagli implementativi:

**JWT builders** — leggono la chiave privata dal path in `settings.pdnd_private_key_path`.
Tutti firmati RS256 con `kid` da `settings.pdnd_kid`.

- `_build_client_assertion(tracking_digest, purpose_id)`:
  claims: `iss/sub=client_id`, `aud=CLIENT_ASSERTION_AUDIENCES[env]`, `jti=uuid4()`,
  `iat/exp=now±300`, `purposeId`, `digest={"alg":"SHA256","value":tracking_digest}`

- `_build_tracking_evidence(endpoint_base, purpose_id)`:
  claims: `iss/sub=client_id`, `aud=normalize_anpr_url(endpoint_base)`, `iat/exp=now±300`,
  `purposeId`, `userID="CBO_SYSTEM"`, `userLocation="SERVER_CBO"`, `LoA="2"`

- `_build_agid_jwt_signature(endpoint_base, http_digest)`:
  claims: `aud=normalize_anpr_url(endpoint_base)`, `iat/nbf/exp`, 
  `signed_headers=[{"digest": http_digest}, {"content-type": "application/json"}]`

- `normalize_anpr_url(url)`: sostituisce `/MinInternoPortaANPR-PDND/` con
  `/MinInternoPortaANPR/` e fa rstrip("/")

**Token PDND**:
- `_request_access_token(tracking_digest, purpose_id)` — POST form-urlencoded a
  `TOKEN_URLS[env]` con `client_id`, `client_assertion`, `client_assertion_type`,
  `grant_type`. Valida il `purposeId` nel JWT ricevuto. Lancia `RuntimeError` se fallisce.

**Chiamata ANPR** — `_call_anpr(service_code, payload)`:
- Compone endpoint = `BASE_URLS[service_code][env] + RESOURCE_PATH`
- Costruisce tracking_evidence → sha256 hex → richiede access token
- Costruisce body JSON (keys sorted, no spaces) → Digest SHA-256 base64 →
  AgID-JWT-Signature
- Headers: `Authorization: Bearer`, `Content-Type: application/json`,
  `Accept: application/json`, `Digest`, `Agid-JWT-TrackingEvidence`,
  `Agid-JWT-Signature`
- Retry su 503: max 2 tentativi, aspetta `Retry-After` (default 5s)
- Restituisce `{"status_code": int, "json": dict}`

**Payload factories** — usano `date.today()` per `dataRiferimentoRichiesta` e
`date.today() - timedelta(days=1)` per `dataEvento` (datiDecesso).
`motivoRichiesta` fisso: `"Verifica decesso intestatario utenza bonifica"`.

- `_payload_c030(codice_fiscale)` — `criteriRicerca: {codiceFiscale: cf}`, `casoUso: "C030"`
- `_payload_c004_by_id(id_anpr)` — `criteriRicerca: {idANPR: id}`, `casoUso: "C004"`
- `_payload_c004_by_cf(codice_fiscale)` — `criteriRicerca: {codiceFiscale: cf}`, `casoUso: "C004"`

**Parsing C004** — `_parse_c004(status_code, json) -> tuple[bool|None, str, list[dict]]`:
- Se status != 200: EN122 → `(None, "Soggetto non registrato in ANPR (EN122)", errori)`
  altrimenti `(None, f"Esito non determinabile (HTTP {status_code})", errori)`
- Se status == 200: itera `listaSoggetti.datiSoggetto[0].infoSoggettoEnte` cercando
  `chiave == "verifica dichiarazione morte"`:
  - `valore == "S"` → `(True, "Soggetto risulta deceduto (dati corrispondenti)", errori)`
  - `valore == "N"` + `"non corrispondente" in dettaglio` →
    `(True, "Soggetto risulta deceduto (dati decesso non corrispondenti)", errori)`
  - `valore == "N"` senza "non corrispondente" → `(False, "Soggetto non risulta deceduto", errori)`
- Se chiave non trovata → `(None, "Chiave 'verifica dichiarazione morte' non trovata", errori)`

**Entry point pubblico**:

```python
class AnprDecssoEsito:
    deceduto: bool | None
    stato_http: int
    messaggio: str
    errori: list[dict]
    id_anpr: str | None

def verifica_decesso(codice_fiscale: str) -> AnprDecssoEsito:
    """
    Esegue C030 + C004. Lancia RuntimeError in caso di errore bloccante.
    
    Logica fallback EN122:
    - C030 restituisce EN122 → c030_not_found = True, tenta C004 per CF
    - Se anche C004 restituisce EN122 → deceduto = True (posizione rimossa)
    - Qualunque altro errore C030 non EN122 → RuntimeError
    """
```

---

#### `service.py`

Dipende da `client.py`, `models.py` e dai modelli utenze.
Import da usare:
```python
from app.modules.utenze.models import AnagraficaSubject, AnagraficaPerson
from app.modules.elaborazioni.pdnd.client import verifica_decesso
from app.modules.elaborazioni.pdnd.models import PdndDecssoConfig, PdndDecssoJob, PdndDecssoResult
```

Funzioni da implementare:

**Config (singleton row id=1)**:
- `get_config(db) -> PdndDecssoConfig` — se non esiste, crea con default e committa
- `update_config(db, **kwargs) -> PdndDecssoConfig` — applica kwargs non None
- `is_in_allowed_hours(cfg) -> bool` — gestisce fascia che attraversa mezzanotte

**Contatore giornaliero**:
- `count_today_calls(db) -> int` — conta `pdnd_decesso_results` dove
  `date(checked_at) == date.today()`
- `daily_status(db) -> dict` — restituisce i campi dello schema `PdndDailyStatus`

**Job management**:
- `list_jobs(db, limit=20) -> list[PdndDecssoJob]` — ordinati per `created_at` DESC
- `get_job(db, job_id) -> PdndDecssoJob | None`

**Batch run** — `run_batch(db, triggered_by="scheduler") -> PdndDecssoJob`:
- Verifica `remaining > 0`, altrimenti `RuntimeError("Limite giornaliero...")`
- Se `triggered_by == "scheduler"` verifica anche `is_in_allowed_hours`, altrimenti
  il trigger manuale ignora la fascia oraria
- Query soggetti: `AnagraficaPerson JOIN AnagraficaSubject` dove
  `status == "active"` AND `codice_fiscale IS NOT NULL`,
  ordinati per `ultima_verifica_decesso_at ASC NULLS FIRST`, `LIMIT remaining`
- Crea job con `status="running"`, `started_at=now(UTC)`
- Per ogni persona:
  - Chiama `verifica_decesso(cf)` dentro try/except
  - Crea `PdndDecssoResult` con tutti i campi
  - In caso di successo: aggiorna `AnagraficaSubject.deceduto` e
    `AnagraficaSubject.ultima_verifica_decesso_at`
  - Incrementa contatori job (`processed`, `deceased`, `not_found`, `errors`)
  - `db.commit()` dopo ogni riga (tracciabilità real-time se il job si interrompe)
- Finalizza job: `status="completed"` o `"failed"`, `completed_at=now(UTC)`
- Log con livello `logging.INFO` per inizio/fine batch, `logging.ERROR` per errori CF

**Verifica singola** — `verify_single(db, subject_id, triggered_by="manual") -> PdndDecssoResult`:
- Valida che il soggetto esista e abbia CF (ValueError se no)
- Verifica limite giornaliero (RuntimeError se raggiunto)
- Crea job one-shot `total_subjects=1` per tracciabilità
- Esegue verifica, aggiorna `ana_subjects`, finalizza job
- In caso di eccezione: finalizza job con `status="failed"`, rilancia l'eccezione

---

#### `scheduler.py`

Usa `BackgroundScheduler` da APScheduler (già in `requirements.txt` come
`APScheduler==3.10.4`).

```python
from apscheduler.schedulers.background import BackgroundScheduler
```

- Scheduler singleton module-level `_scheduler: BackgroundScheduler | None = None`
- `start_pdnd_scheduler()` — crea il scheduler con `timezone="Europe/Rome"`,
  aggiunge job `_run_scheduled_batch` con trigger `cron` `minute=0`
  (ogni ora intera), id `"pdnd-decesso"`, poi chiama `scheduler.start()`
- `stop_pdnd_scheduler()` — shutdown graceful
- `_run_scheduled_batch()` — apre una `SessionLocal`, controlla
  `cfg.active` e `is_in_allowed_hours`, chiama `run_batch`, loga esito.
  Sempre `finally: db.close()`. Cattura tutte le eccezioni con `logger.error`.

---

#### `routes.py`

Router con `prefix="/pdnd"`, `tags=["elaborazioni-pdnd"]`.

Tutti gli endpoint richiedono autenticazione via `Depends(get_current_user)` —
usa lo stesso pattern degli altri router del progetto (leggi come viene fatto in
`elaborazioni/capacitas_routes.py` o `runtime_routes.py` per replicarlo esatto).

Endpoint:

| Metodo | Path | Descrizione |
|--------|------|-------------|
| GET | `/pdnd/config` | Legge config scheduler |
| PATCH | `/pdnd/config` | Aggiorna config scheduler |
| GET | `/pdnd/status` | Stato giornaliero (quota, fascia) |
| GET | `/pdnd/jobs` | Lista job (query param `limit=20`) |
| GET | `/pdnd/jobs/{job_id}` | Dettaglio job con risultati |
| POST | `/pdnd/batch/run` | Trigger manuale batch — `202 ACCEPTED` |
| POST | `/pdnd/subjects/{subject_id}/verify` | Verifica singola on-demand |
| GET | `/pdnd/subjects/{subject_id}/latest` | Ultimo risultato per soggetto |

`POST /pdnd/batch/run` e `POST /pdnd/subjects/{subject_id}/verify`:
- `RuntimeError` → HTTP 409
- `ValueError` → HTTP 404

### 1.5 — Mount nel router elaborazioni

In `backend/app/modules/elaborazioni/router.py` aggiungere:

```python
from app.modules.elaborazioni.pdnd.routes import router as pdnd_router
router.include_router(pdnd_router)
```

### 1.6 — Scheduler nel lifespan FastAPI

In `backend/app/main.py` aggiornare il lifespan:

```python
from app.modules.elaborazioni.pdnd.scheduler import start_pdnd_scheduler, stop_pdnd_scheduler

@asynccontextmanager
async def lifespan(_: FastAPI):
    _ensure_bootstrap_admin_on_startup()
    start_pdnd_scheduler()
    yield
    stop_pdnd_scheduler()
```

### 1.7 — Registrazione modelli

Verifica che i nuovi modelli vengano importati nel punto in cui Alembic fa l'autogenerate
(tipicamente `backend/app/core/database.py` o `backend/alembic/env.py`). Se esiste già
un pattern di import esplicito (es. `from app.modules.elaborazioni.pdnd.models import ...`),
seguilo. Se esiste un `Base.metadata` condiviso e i modelli vengono rilevati
automaticamente all'import, assicurati che `pdnd/models.py` venga importato prima
dell'autogenerate.

---

## Parte 2 — Frontend Elaborazioni

### 2.1 — `frontend/src/components/elaborazioni/pdnd-workspace.tsx`

Componente `PdndWorkspace({ embedded?: boolean })`.

Chiama le API PDND usando `getStoredAccessToken()` (stesso pattern di tutti gli altri
workspace elaborazioni — leggi `settings-workspace.tsx` per il pattern esatto).

**Struttura UI** (segui lo stile visivo già presente in `settings-workspace.tsx` —
stesse classi CSS, stesso arrotondamento, stessa palette `#1D4E35`):

**Card 1 — Stato giornaliero**:
- 4 metric box: "Chiamate oggi", "Rimanenti", "Fascia oraria" (dot verde/grigio),
  "Scheduler" (dot verde/grigio)
- Pulsante "Avvia batch ora" (disabilitato se `remaining === 0` o `triggering`)
- Pulsante "Aggiorna"
- In caso di errore trigger, mostra il messaggio sotto i pulsanti

**Card 2 — Configurazione scheduler**:
- Input numerico "Ore inizio fascia" (0-23)
- Input numerico "Ore fine fascia" (0-23)
- Input numerico "Limite giornaliero" (1-90)
- Checkbox "Scheduler attivo"
- Pulsante "Salva configurazione"
- Stato locale del form: modifica senza inviare finché non si salva

**Card 3 — Job recenti**:
- Tabella: Data | Stato | Elaborati | Deceduti | Errori | Trigger | Completato
- Badge colorati per lo stato job (completed=verde, running=blu, failed=rosso,
  pending=giallo, cancelled=grigio)
- Se `deceased > 0`: valore in rosso bold
- Se `errors > 0`: valore in arancio bold
- Se un job ha `error_message`: mostra i messaggi sotto la tabella

**Banner avvisi** (sopra le card):
- Se qualsiasi job recente ha `errors > 0` → banner warning arancio
- Se qualsiasi job recente ha `deceased > 0` → banner rosso "Rilevati soggetti deceduti"
- Questi banner sono informativi, non bloccanti

**Gestione loading/error**: stato `loading` iniziale, `error` generale in cima.

Endpoints consumati:
GET  /api/elaborazioni/pdnd/config
PATCH /api/elaborazioni/pdnd/config
GET  /api/elaborazioni/pdnd/status
GET  /api/elaborazioni/pdnd/jobs?limit=10
POST /api/elaborazioni/pdnd/batch/run

### 2.2 — Aggiornamento `settings-workspace.tsx`

Aggiungere la sezione PDND dopo la sezione Capacitas esistente:

```tsx
import { PdndWorkspace } from "@/components/elaborazioni/pdnd-workspace";

// Nel render, dopo </section> della sezione Capacitas:
<section>
  <div className={`border-b border-[#edf1eb] ${embedded ? "px-5 py-4" : "px-6 py-5"}`}>
    <p className="text-lg font-semibold text-gray-900">PDND — Verifica Decesso</p>
    <p className={`text-sm text-gray-500 ${embedded ? "mt-1.5 leading-5" : "mt-2 leading-6"}`}>
      Verifica automatica stato in vita dei soggetti anagrafica tramite ANPR/PDND.
    </p>
  </div>
  <div className={embedded ? "p-5" : "p-6"}>
    <PdndWorkspace embedded={embedded} />
  </div>
</section>
```

---

## Parte 3 — Frontend Utenze (modal soggetto)

### 3.1 — `frontend/src/components/utenze/pdnd-decesso-section.tsx`

Componente `PdndDecssoSection({ subjectId: string, compact?: boolean })`.

Al mount: `GET /api/elaborazioni/pdnd/subjects/{subjectId}/latest` → carica l'ultimo
risultato disponibile.

**Struttura UI**:

Header riga: label "Verifica Decesso (PDND/ANPR)" + pulsante "Verifica ora" (piccolo,
secondario, con icona refresh).

Stato loading: testo "Caricamento…"

Nessun risultato (`null`): testo "Nessuna verifica disponibile. Usa il pulsante per
verificare ora."

Con risultato — card colorata in base all'esito:
- `deceduto === true`: sfondo rosso chiaro, icona Skull, testo "Deceduto"
- `deceduto === false`: sfondo verde chiaro, icona CheckCircle, testo "Non deceduto"
- `deceduto === null`: sfondo grigio chiaro, icona HelpCircle, testo "Non determinabile"

Contenuto card:
- Riga icona + label stato
- `result.messaggio`
- Se `result.id_anpr`: "ID ANPR: …" (opacizzato)
- "Verificato il {formatDateTime(result.checked_at)}" (opacizzato)
- Se `result.errori_json` non vuoto: `<details>` collassabile "Dettaglio errori/anomalie"
  con lista `[codice] testo`

Se errore dal pulsante "Verifica ora": banner rosso con il messaggio.

Endpoint consumato per il trigger manuale:
POST /api/elaborazioni/pdnd/subjects/{subjectId}/verify

### 3.2 — Inserimento nel dettaglio soggetto

Trova il componente o la pagina che mostra il dettaglio soggetto nella modal utenze
(cerca la modal o il pannello che mostra `cognome`, `nome`, `codice_fiscale` per una
persona fisica).

Aggiungi il componente nella sezione dati anagrafici, dopo i dati principali e prima dei
documenti (o in un tab/sezione dedicata se la UI è già organizzata a tab):

```tsx
import { PdndDecssoSection } from "@/components/utenze/pdnd-decesso-section";

// Solo per soggetti di tipo "person" con codice_fiscale valorizzato:
{subject.subject_type === "person" && subject.codice_fiscale && (
  <PdndDecssoSection subjectId={subject.id} />
)}
```

---

## Parte 4 — Verifiche da eseguire

### Backend

```bash
# 1. Applica la migration
cd backend
alembic upgrade head

# 2. Compila tutto il package pdnd
python -m compileall app/modules/elaborazioni/pdnd/

# 3. Esegui i test esistenti per verificare che non si rompano
PYTHONPATH=. pytest tests/ -q --tb=short -x

# 4. Verifica che il server si avvii senza errori
uvicorn app.main:app --reload --port 8001
# Controlla che nel log compaia: "PDND scheduler avviato (cron ogni ora)"
# Controlla che GET /docs mostri gli endpoint /elaborazioni/pdnd/*
```

### Frontend

```bash
cd frontend
npx tsc --noEmit
npm run lint
```

Correggere tutti gli errori TypeScript e lint prima di considerare l'implementazione
completata.

---

## Vincoli e note importanti

1. **Non modificare** la logica esistente di altri moduli — questo intervento è
   puramente additivo salvo le 2 colonne su `ana_subjects` e il lifespan in `main.py`.

2. **Naming**: usa esattamente i nomi di tabella/colonna specificati nella migration.
   Il client `verifica_decesso(cf)` deve lanciare `RuntimeError` (non eccezioni custom)
   per errori bloccanti — il service layer li cattura e li converte in log + risultato
   di errore senza interrompere il batch.

3. **Commit granulare nel batch**: `db.commit()` dopo ogni singolo `PdndDecssoResult`
   (non un commit finale per tutto il batch). Questo è intenzionale: se il processo
   viene interrotto, i risultati già processati vengono preservati.

4. **Il trigger manuale** (`POST /pdnd/batch/run`) ignora la fascia oraria ma rispetta
   il limite giornaliero. Questo comportamento è nel service, non nel route.

5. **BackgroundScheduler** gira nello stesso processo del backend FastAPI — non serve
   un container separato. L'interval è ogni ora intera (`cron minute=0`): il service
   interno controlla fascia e limite ad ogni tick.

6. **La chiave privata PDND** viene letta da disco ad ogni chiamata
   (via `open(settings.pdnd_private_key_path)`). Non cachare in memoria — le variabili
   di `settings` sono immutabili a runtime e sono lette da env all'avvio.

7. Se durante l'ispezione del codice scopri che il pattern di autenticazione è diverso
   da quanto descritto (es. il nome del Depends o della funzione cambia),
   adattati al pattern reale — non inventare nuovi pattern.