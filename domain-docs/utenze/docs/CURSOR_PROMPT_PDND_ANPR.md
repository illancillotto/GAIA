# CURSOR IMPLEMENTATION PROMPT
# GAIA — Integrazione PDND/ANPR: Verifica Decessi
# Versione: 1.0 — Sequenziale GSD

> Riferimenti obbligatori prima di iniziare:
> - `domain-docs/utenze/docs/PRD_PDND_ANPR_DECESSI.md`
> - `domain-docs/utenze/docs/ARCH_PDND_ANPR_DECESSI.md`
> - API spec C004: `domain-docs/utenze/docs/specs/C004-servizioVerificaDichDecesso.yaml`
> - API spec C030: `domain-docs/utenze/docs/specs/SpecificaAPI_C030.yaml`
> - Moduli esistenti di riferimento: `backend/app/modules/utenze/`, `backend/app/modules/catasto/`
> - Pattern PDND auth: consultare documentazione AgID ModI `INTEGRITY_REST_02` e `AUDIT_REST_02`

---

## REGOLE GENERALI

- Seguire la struttura modulare canonica GAIA: tutto il nuovo codice va in `backend/app/modules/utenze/anpr/`
- Non modificare modelli, schemi o route di altri moduli senza esplicita indicazione
- Ogni step deve completarsi e compilarsi correttamente prima di passare al successivo
- Usare `AsyncSession` per tutte le operazioni DB
- Usare `httpx.AsyncClient` per le chiamate HTTP verso ANPR (non `requests`)
- Loggare gli step operativi significativi con `logging.getLogger(__name__)`
- Le variabili d'ambiente vanno sempre lette da `app/core/config.py` — non hardcodare mai valori sensibili

---

## STEP 1 — Migration Alembic

Crea una nuova migration Alembic che:

1. Aggiunge a `ana_persons` le colonne:
   - `anpr_id VARCHAR(50) NULL`
   - `stato_anpr VARCHAR(30) NULL` — valori attesi: `alive`, `deceased`, `not_found_anpr`, `cancelled_anpr`, `error`, `unknown`
   - `data_decesso DATE NULL`
   - `luogo_decesso_comune VARCHAR(100) NULL`
   - `last_anpr_check_at TIMESTAMP WITH TIME ZONE NULL`
   - `last_c030_check_at TIMESTAMP WITH TIME ZONE NULL`
   - Aggiungere indice su `anpr_id` e su `stato_anpr`

2. Crea la tabella `anpr_check_log` con colonne:
   - `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
   - `subject_id UUID NOT NULL REFERENCES ana_subjects(id)`
   - `call_type VARCHAR(10) NOT NULL` — `C030` o `C004`
   - `id_operazione_client VARCHAR(100) NOT NULL`
   - `id_operazione_anpr VARCHAR(100) NULL`
   - `esito VARCHAR(30) NOT NULL`
   - `error_detail TEXT NULL`
   - `data_decesso_anpr DATE NULL`
   - `triggered_by VARCHAR(50) NOT NULL`
   - `created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()`
   - Indice su `(subject_id, created_at DESC)`

3. Crea la tabella `anpr_sync_config` con colonne:
   - `id INTEGER PRIMARY KEY DEFAULT 1`
   - `max_calls_per_day INTEGER NOT NULL DEFAULT 100`
   - `job_enabled BOOLEAN NOT NULL DEFAULT TRUE`
   - `job_cron VARCHAR(50) NOT NULL DEFAULT '0 2 * * *'`
   - `lookback_years INTEGER NOT NULL DEFAULT 1`
   - `retry_not_found_days INTEGER NOT NULL DEFAULT 90`
   - `updated_at TIMESTAMP WITH TIME ZONE NULL`
   - `updated_by_user_id INTEGER NULL REFERENCES application_users(id)`

4. Inserisce la riga di config default: `INSERT INTO anpr_sync_config(id) VALUES(1) ON CONFLICT DO NOTHING`

Verifica che la migration applichi senza errori su PostgreSQL (`alembic upgrade head`).

---

## STEP 2 — Models SQLAlchemy (`backend/app/modules/utenze/anpr/models.py`)

Implementa i modelli SQLAlchemy per:

### AnprCheckLog
Mappa la tabella `anpr_check_log`. Relazione `subject` → `AnaSubject` (lazy="noload").

### AnprSyncConfig
Mappa la tabella `anpr_sync_config`. Singleton (id sempre = 1).
Aggiungere un metodo di classe `get_or_create_default(session)` che ritorna il record singleton,
creandolo con i valori default se non esiste.

### Estensione AnaPersona
Nel file `backend/app/modules/utenze/models.py` (non nel modulo anpr/), aggiungere le
6 nuove colonne al modello `AnaPersona` (o nome equivalente esistente per `ana_persons`).
Verificare il nome esatto del modello guardando il file esistente.

---

## STEP 3 — Schemas Pydantic (`backend/app/modules/utenze/anpr/schemas.py`)

Implementa i seguenti schemi:

```python
class AnprSyncConfigRead(BaseModel):
    max_calls_per_day: int
    job_enabled: bool
    job_cron: str
    lookback_years: int
    retry_not_found_days: int
    updated_at: datetime | None

class AnprSyncConfigUpdate(BaseModel):
    max_calls_per_day: int | None = None
    job_enabled: bool | None = None
    job_cron: str | None = None  # validare formato cron (5 campi)
    lookback_years: int | None = None
    retry_not_found_days: int | None = None

class AnprCheckLogItem(BaseModel):
    id: str
    subject_id: str
    call_type: str
    id_operazione_client: str
    id_operazione_anpr: str | None
    esito: str
    error_detail: str | None
    data_decesso_anpr: date | None
    triggered_by: str
    created_at: datetime

class AnprSyncResult(BaseModel):
    subject_id: str
    success: bool
    esito: str  # alive | deceased | not_found | cancelled | error
    data_decesso: date | None = None
    anpr_id: str | None = None
    calls_made: int  # quante chiamate API usate (1 o 2)
    message: str  # testo leggibile per l'operatore

class AnprSubjectStatus(BaseModel):
    subject_id: str
    anpr_id: str | None
    stato_anpr: str | None
    data_decesso: date | None
    luogo_decesso_comune: str | None
    last_anpr_check_at: datetime | None
    last_c030_check_at: datetime | None

class AnprJobTriggerResult(BaseModel):
    started_at: datetime
    subjects_processed: int
    deceased_found: int
    errors: int
    calls_used: int
    message: str
```

---

## STEP 4 — PDND Auth Manager (`backend/app/modules/utenze/anpr/auth.py`)

Implementa la classe `PdndAuthManager` con:

### Variabili config da `app/core/config.py`
Aggiungere a `Settings`:
```python
PDND_CLIENT_ID: str = ""
PDND_KID: str = ""
PDND_PRIVATE_KEY_PATH: str = ""
PDND_PRIVATE_KEY_PEM: str = ""          # fallback dev
PDND_AUTH_URL: str = "https://auth.interop.pagopa.it/as/token.oauth2"
PDND_AUDIENCE: str = "https://interop.pagopa.it/"
ANPR_BASE_URL: str = "https://modipa-val.anpr.interno.it/govway/rest/in/MinInternoPortaANPR-PDND"
PDND_FRUITORE_USER_ID: str = "GAIA-CBO"
PDND_FRUITORE_USER_LOCATION: str = "GAIA-SRV"
PDND_LOA: str = "LOW"
```

### Metodi `PdndAuthManager`

```python
class PdndAuthManager:
    _voucher_cache: dict = {}  # {"token": str, "expires_at": float}
    
    def _load_private_key(self) -> rsa.RSAPrivateKey:
        """Carica chiave privata da file (PDND_PRIVATE_KEY_PATH) o da env PEM."""
    
    def _build_client_assertion(self) -> str:
        """
        Crea JWT firmato RS256 per client_credentials PDND.
        Claims: iss=client_id, sub=client_id, aud=PDND_AUTH_URL,
                jti=str(uuid4()), iat=now, exp=now+60
        Header: kid=PDND_KID
        """
    
    async def get_voucher(self) -> str:
        """
        Restituisce access token PDND valido (da cache o nuovo).
        Se cache vuota o expiry < now+300s: richiede nuovo token.
        POST PDND_AUTH_URL con:
            grant_type=client_credentials
            client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer
            client_assertion=<JWT>
        """
    
    def build_agid_jwt_signature(self, payload_bytes: bytes) -> str:
        """
        JWS per INTEGRITY_REST_02.
        Header: { alg: RS256, kid: KID, typ: JWT }
        Claims: {
            iat: now,
            exp: now+300,
            jti: str(uuid4()),
            digest: { alg: "SHA-256", value: base64url(sha256(payload_bytes)) },
            signed_headers: [{"digest": "..."}, {"content-type": "application/json"}]
        }
        Firma con chiave privata RSA.
        """
    
    def build_agid_jwt_tracking_evidence(self, motivo_richiesta: str) -> str:
        """
        JWS per AUDIT_REST_02.
        Claims: {
            iat: now, exp: now+300, jti: str(uuid4()),
            userID: PDND_FRUITORE_USER_ID,
            userLocation: PDND_FRUITORE_USER_LOCATION,
            LoA: PDND_LOA,
        }
        """
```

**Dipendenze**: `PyJWT`, `cryptography`. Installare se non presenti in `requirements.txt`.

**Test di smoke**: aggiungere un test `tests/test_pdnd_auth.py` che verifica la corretta
costruzione del JWT senza chiamate di rete (mock del key loading, verifica claims).

---

## STEP 5 — ANPR API Client (`backend/app/modules/utenze/anpr/client.py`)

Implementa `AnprClient` con due metodi pubblici.

### c030_get_anpr_id(codice_fiscale, subject_id_short) → C030Result

```python
@dataclass
class C030Result:
    success: bool
    anpr_id: str | None
    id_operazione_anpr: str | None
    esito: str          # "anpr_id_found" | "not_found" | "cancelled" | "error"
    error_detail: str | None
    id_operazione_client: str
```

Costruisce la request body C030 come da spec YAML.
`idOperazioneClient` = `str(uuid4())` (alfanumerico, come da spec C030).
`motivoRichiesta` = `f"GAIA-CHECK-{subject_id_short}"`.
`dataRiferimentoRichiesta` = data odierna in formato `YYYY-MM-DD`.
`casoUso` = `"C030"`.

Headers: `Authorization: Bearer <voucher>`, `Agid-JWT-Signature: <JWS>`,
`Content-Type: application/json`.

Parsing risposta:
- `200` + `listaSoggetti.datiSoggetto[0].identificativi.idANPR` presente → `esito = "anpr_id_found"`
- `404` o `listaAnomalie` con codice "non trovato" → `esito = "not_found"`
- `200` con `listaAnomalie` indicante cancellazione non-decesso → `esito = "cancelled"`
- Qualsiasi eccezione HTTP → `esito = "error"`, loggare il dettaglio

### c004_check_death(anpr_id, subject_id_short) → C004Result

```python
@dataclass
class C004Result:
    success: bool
    esito: str          # "alive" | "deceased" | "not_found" | "error"
    data_decesso: date | None
    id_operazione_anpr: str | None
    error_detail: str | None
    id_operazione_client: str
    raw_response: dict | None   # per debug durante integration testing
```

`idOperazioneClient` = `str(int(time.time() * 1000))` (numerico crescente come da spec C004).
Criterio di ricerca: `criteriRicerca.idANPR = anpr_id`.
Campo `verifica` OMESSO (verifica pura senza dati di confronto).

Parsing risposta:
- `200` senza anomalie di decesso → `esito = "alive"`
- `200` con `listaAnomalie` contenente codice decesso → `esito = "deceased"`, estrarre data
- `200` con `infoSoggettoEnte` e chiave indicante decesso → `esito = "deceased"`
- `404` → `esito = "not_found"`
- Errore rete/HTTP → `esito = "error"`

> **NOTA**: Il parsing esatto della risposta C004 per il caso "deceased" va validato
> sull'ambiente ANPR test. Implementare con un flag `_RESPONSE_MAP_VALIDATED = False`
> e loggare sempre `raw_response` finché il flag non viene impostato a `True` da un
> developer dopo validazione su test ANPR.

Timeout httpx: 30 secondi per chiamata.
Retry automatico: NO (idempotenza non garantita per C004 con ID crescente).

---

## STEP 6 — Service Layer (`backend/app/modules/utenze/anpr/service.py`)

Implementa le seguenti funzioni asincrone:

### `get_config(db) → AnprSyncConfig`
Wrapper per `AnprSyncConfig.get_or_create_default(db)`.

### `update_config(db, update: AnprSyncConfigUpdate, user_id: int) → AnprSyncConfig`
Aggiorna i campi non-None dell'update. Valida `job_cron` (deve avere 5 campi separati da spazio).
Aggiorna `updated_at` e `updated_by_user_id`.

### `build_check_queue(db, config) → list[str]`

Query SQL con:
1. JOIN `ana_subjects` + `ana_persons`
2. Solo `subject_type = 'person'`, `codice_fiscale IS NOT NULL`
3. Escludi `stato_anpr = 'deceased'`
4. Escludi `stato_anpr = 'not_found_anpr'` se `last_anpr_check_at > NOW() - INTERVAL config.retry_not_found_days days`
5. LEFT JOIN `cat_utenze_irrigue` per flag priorità (anno precedente sì, anno corrente no)
6. ORDER BY: flag priorità DESC, `data_nascita ASC NULLS LAST`
7. LIMIT: `config.max_calls_per_day` (budget conservativo — il service gestirà il decremento effettivo)

### `sync_single_subject(subject_id, db, triggered_by, auth, client) → AnprSyncResult`

```
1. Carica ana_persons via subject_id (JOIN ana_subjects)
2. Controlla codice_fiscale presente → se no, ritorna errore
3. calls_made = 0
4. Se anpr_id mancante:
   a. c030_result = await client.c030_get_anpr_id(cf, subject_id_short)
   b. calls_made += 1
   c. Crea AnprCheckLog(call_type="C030", ...)
   d. Se esito != "anpr_id_found":
      - Aggiorna stato_anpr, last_c030_check_at
      - Ritorna AnprSyncResult con esito appropriato
   e. Persiste anpr_id in ana_persons
5. c004_result = await client.c004_check_death(anpr_id, subject_id_short)
6. calls_made += 1
7. Crea AnprCheckLog(call_type="C004", ...)
8. Aggiorna ana_persons:
   - stato_anpr = c004_result.esito
   - data_decesso = c004_result.data_decesso (se deceased)
   - last_anpr_check_at = now()
9. db.commit()
10. Ritorna AnprSyncResult
```

### `run_daily_job(db_factory) → AnprJobSummary`

```
1. db = await db_factory()
2. config = await get_config(db)
3. Se not config.job_enabled → return con messaggio "job disabled"
4. queue = await build_check_queue(db, config)
5. calls_budget = config.max_calls_per_day
6. results = {processed: 0, deceased: 0, errors: 0, calls_used: 0}
7. auth = PdndAuthManager()
8. client = AnprClient(auth)
9. For subject_id in queue:
   a. Se calls_budget <= 0 → break
   b. result = await sync_single_subject(subject_id, db, "job", auth, client)
   c. calls_budget -= result.calls_made
   d. results.calls_used += result.calls_made
   e. results.processed += 1
   f. Se result.esito == "deceased" → results.deceased += 1
   g. Se not result.success → results.errors += 1
   h. await asyncio.sleep(0.5)  # rate limiting ANPR
10. Log summary
11. return AnprJobSummary(**results)
```

---

## STEP 7 — Router API (`backend/app/modules/utenze/anpr/routes.py`)

Prefisso: `/utenze/anpr`

```python
router = APIRouter(prefix="/utenze/anpr", tags=["anpr"])
```

Implementa tutti gli endpoint definiti in ARCH_PDND_ANPR_DECESSI.md, sezione 7.

**Endpoint critici**:

`POST /sync/{subject_id}` — Sync singola
- Richiede auth: admin o reviewer
- Esegue `sync_single_subject(..., triggered_by=f"user:{current_user.id}")`
- Risposta: `AnprSyncResult`
- Timeout client: 60s (due chiamate ANPR in serie)

`GET /sync/{subject_id}/status` — Stato soggetto
- Tutti i ruoli autenticati
- Risposta: `AnprSubjectStatus`

`GET /log` — Lista log (paginata)
- Solo admin
- Query params: `subject_id` (opzionale), `esito` (opzionale), `page`, `page_size`

`GET /config` + `PUT /config` — Gestione configurazione
- Solo admin
- PUT valida formato cron prima di salvare

`POST /job/trigger` — Trigger manuale
- Solo admin
- Lancia `run_daily_job` in background (`BackgroundTasks`)
- Risposta immediata 202 Accepted con messaggio

**Integrare il router in** `backend/app/api/router.py` con:
```python
from backend.app.modules.utenze.anpr.routes import router as anpr_router
api_router.include_router(anpr_router)
```

Aggiungere le section key `utenze.anpr.*` al bootstrap sezioni se necessario (verificare
il pattern usato dagli altri moduli in `backend/app/core/bootstrap.py` o equivalente).

---

## STEP 8 — Scheduler (`backend/app/modules/utenze/anpr/scheduler.py`)

```python
from apscheduler.triggers.cron import CronTrigger

async def register_anpr_scheduler(scheduler, get_db):
    """
    Legge config da DB e registra il job.
    Chiamare durante l'avvio del backend (lifespan o startup event).
    """
    async with get_db() as db:
        config = await get_config(db)
    
    if not config.job_enabled:
        logger.info("ANPR daily job disabled — skip scheduler registration")
        return
    
    scheduler.add_job(
        _run_job_wrapper,
        trigger=CronTrigger.from_crontab(config.job_cron),
        id="anpr_daily_check",
        replace_existing=True,
        misfire_grace_time=3600,
        kwargs={"get_db": get_db},
    )
    logger.info(f"ANPR daily job registered — cron: {config.job_cron}")
```

Trovare il punto di registrazione scheduler nel backend (cercare APScheduler nel codice
esistente, tipicamente in `main.py` o `app/core/scheduler.py`) e aggiungere la chiamata
a `register_anpr_scheduler`.

---

## STEP 9 — Frontend: AnprStatusCard

**File**: `frontend/src/components/anagrafica/AnprStatusCard.tsx`

Componente React che:

1. Props: `subjectId: string`, `initialStatus?: AnprSubjectStatus`

2. Mostra una card con:
   - **Badge stato**: `alive` → verde, `deceased` → rosso con icona ⚠️, `null/unknown` → grigio, `not_found_anpr` → arancione, `error` → rosso outline
   - Data decesso (se `deceased`)
   - Comune decesso (se presente)
   - "Ultimo controllo: {last_anpr_check_at formattata}" o "Mai verificato"
   - Pulsante **"Verifica ANPR"** (solo per ruolo admin/reviewer):
     - Spinner durante chiamata
     - Chiama `POST /utenze/anpr/sync/{subjectId}`
     - Toast di successo/errore al completamento
     - Aggiorna lo stato visualizzato

3. Aggiungere alla pagina dettaglio soggetto in posizione visibile nella sezione dati anagrafici.
   Trovare il file corretto per la pagina di dettaglio soggetto guardando la struttura
   `frontend/src/app/anagrafica/` o `frontend/src/app/utenze/` (il path esatto dipende
   dall'implementazione esistente).

**Tipi TypeScript** da aggiungere in `frontend/src/lib/types.ts` o file tipi equivalente:
```typescript
export interface AnprSubjectStatus {
  subject_id: string;
  anpr_id: string | null;
  stato_anpr: "alive" | "deceased" | "not_found_anpr" | "cancelled_anpr" | "error" | "unknown" | null;
  data_decesso: string | null;  // ISO date
  luogo_decesso_comune: string | null;
  last_anpr_check_at: string | null;
  last_c030_check_at: string | null;
}

export interface AnprSyncResult {
  subject_id: string;
  success: boolean;
  esito: string;
  data_decesso: string | null;
  anpr_id: string | null;
  calls_made: number;
  message: string;
}
```

---

## STEP 10 — Frontend: Pagina configurazione ANPR (admin)

**File**: `frontend/src/app/anagrafica/anpr-config/page.tsx`

Pagina accessibile solo ad admin che mostra:

1. **Form configurazione job**:
   - `max_calls_per_day`: input numerico (min 1, max 10000)
   - `job_enabled`: toggle switch
   - `job_cron`: input testo con placeholder `"0 2 * * *"` e link a crontab.guru
   - `lookback_years`: input numerico (min 1, max 10)
   - `retry_not_found_days`: input numerico (min 1, max 365)
   - Pulsante "Salva configurazione" → `PUT /utenze/anpr/config`

2. **Sezione stato job** (polling ogni 30s):
   - Data ultima esecuzione
   - Soggetti verificati, deceduti trovati, errori
   - Pulsante "Esegui ora" → `POST /utenze/anpr/job/trigger` (solo se job_enabled)

3. Aggiungere voce di navigazione nel sidebar del modulo utenze/anagrafica per gli admin.

---

## STEP 11 — Test

Crea `backend/tests/test_anpr_service.py` con test unitari per:

1. `test_build_check_queue_priority_order` — verifica che soggetti con utenza solo anno precedente vengano prima
2. `test_sync_single_no_anpr_id` — mock C030 + C004, verifica flusso completo
3. `test_sync_single_already_has_anpr_id` — solo C004, verifica che C030 non venga chiamato
4. `test_sync_single_deceased` — verifica aggiornamento `stato_anpr = deceased`
5. `test_config_singleton` — verifica upsert config

Mock da usare: `unittest.mock.AsyncMock` per `AnprClient`, `pytest-asyncio` per test async.

---

## STEP 12 — Documentazione yaml spec

Copiare i file spec ANPR in:
```
domain-docs/utenze/docs/specs/
├── C004-servizioVerificaDichDecesso.yaml
└── SpecificaAPI_C030.yaml
```

Aggiornare `domain-docs/utenze/docs/PROGRESS_ANPR.md` con lo stato di implementazione
seguendo il formato degli altri PROGRESS.md del progetto.

---

## CHECKLIST FINALE

Prima di considerare l'implementazione completa, verificare:

- [ ] `alembic upgrade head` eseguito senza errori su DB locale
- [ ] Backend si avvia senza eccezioni (`docker compose up backend`)
- [ ] Endpoint `/utenze/anpr/config` GET risponde 200 con valori default
- [ ] Endpoint `/utenze/anpr/sync/{id}` risponde (anche con errore PDND — credenziali non configurate in dev)
- [ ] Frontend: badge stato ANPR visibile nella scheda soggetto
- [ ] Frontend: pulsante "Verifica ANPR" presente e chiama l'endpoint corretto
- [ ] Test unitari passano (`pytest backend/tests/test_anpr_service.py`)
- [ ] Nessun CF o chiave privata in chiaro nei log applicativi
- [ ] Variabili d'ambiente PDND documentate in `.env.example` (con valori placeholder)

---

## NOTE PER L'INTEGRAZIONE TEST ANPR

Prima del go-live, eseguire manualmente queste chiamate curl sull'ambiente
`modipa-val.anpr.interno.it` con soggetti di test forniti da ANPR/SOGEI:

```bash
# Test C030 con CF noto
curl -X POST https://modipa-val.anpr.interno.it/govway/rest/in/MinInternoPortaANPR-PDND/C030-servizioAccertamentoIdUnicoNazionale/v1/anpr-service-e002 \
  -H "Authorization: Bearer <voucher>" \
  -H "Agid-JWT-Signature: <JWS>" \
  -H "Content-Type: application/json" \
  -d '{"idOperazioneClient": "test-001", "criteriRicerca": {"codiceFiscale": "<CF_TEST>"}, "datiRichiesta": {"dataRiferimentoRichiesta": "2025-01-01", "motivoRichiesta": "TEST", "casoUso": "C030"}}'

# Annotare idANPR dalla risposta, poi testare C004:
curl -X POST https://modipa-val.anpr.interno.it/.../C004.../anpr-service-e002 \
  -d '{"idOperazioneClient": "1234567890", "criteriRicerca": {"idANPR": "<ID_ANPR>"}, "datiRichiesta": {"dataRiferimentoRichiesta": "2025-01-01", "motivoRichiesta": "TEST", "casoUso": "C004"}}'
```

Documentare la struttura esatta della risposta C004 per soggetti vivi e deceduti e
aggiornare `client.py` di conseguenza prima del deploy in produzione.
