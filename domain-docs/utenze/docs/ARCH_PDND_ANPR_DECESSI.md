# GAIA — Integrazione PDND/ANPR: Verifica Decessi
## Documento di Architettura v1

> Dipende da: PRD_PDND_ANPR_DECESSI.md
> Modulo backend: `backend/app/modules/utenze/anpr/`
> Modulo frontend: `frontend/src/app/anagrafica/subjects/[id]/` (estensione)

---

## 1. Struttura modulo backend

```
backend/app/modules/utenze/anpr/
├── __init__.py
├── models.py          # AnprCheckLog, AnprSyncConfig (SQLAlchemy)
├── schemas.py         # Pydantic request/response schemas
├── client.py          # ANPR API client: C030 + C004
├── auth.py            # PDND JWT client assertion + voucher management
├── service.py         # Business logic: coda prioritizzata, sync singola
├── scheduler.py       # APScheduler job registration
└── routes.py          # FastAPI router /utenze/anpr/*
```

Estensioni a moduli esistenti:
- `backend/app/modules/utenze/models.py` — aggiunta colonne ANPR su `AnaPersona` (migration Alembic)
- `backend/app/modules/utenze/routes.py` — inclusione router ANPR

---

## 2. Modelli SQLAlchemy

### 2.1 Estensione AnaPersona (ana_persons)

```python
# Aggiungere a AnaPersona in backend/app/modules/utenze/models.py

anpr_id = Column(String(50), nullable=True, index=True)
stato_anpr = Column(
    String(30),
    nullable=True,
    # valori: alive | deceased | not_found_anpr | cancelled_anpr | error | unknown
)
data_decesso = Column(Date, nullable=True)
luogo_decesso_comune = Column(String(100), nullable=True)
last_anpr_check_at = Column(DateTime(timezone=True), nullable=True)
last_c030_check_at = Column(DateTime(timezone=True), nullable=True)
```

### 2.2 AnprCheckLog

```python
class AnprCheckLog(Base):
    __tablename__ = "anpr_check_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("ana_subjects.id"), nullable=False, index=True)
    call_type = Column(String(10), nullable=False)          # C030 | C004
    id_operazione_client = Column(String(100), nullable=False)
    id_operazione_anpr = Column(String(100), nullable=True)
    esito = Column(String(30), nullable=False)
    # esito: alive | deceased | not_found | cancelled | error | anpr_id_found
    error_detail = Column(Text, nullable=True)
    data_decesso_anpr = Column(Date, nullable=True)
    triggered_by = Column(String(50), nullable=False)       # job | user:{id}
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

### 2.3 AnprSyncConfig

```python
class AnprSyncConfig(Base):
    __tablename__ = "anpr_sync_config"

    id = Column(Integer, primary_key=True, default=1)       # singleton row
    max_calls_per_day = Column(Integer, default=100, nullable=False)
    job_enabled = Column(Boolean, default=True, nullable=False)
    job_cron = Column(String(50), default="0 2 * * *", nullable=False)
    lookback_years = Column(Integer, default=1, nullable=False)
    retry_not_found_days = Column(Integer, default=90, nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    updated_by_user_id = Column(Integer, ForeignKey("application_users.id"), nullable=True)
```

---

## 3. PDND Authentication Layer (`auth.py`)

### 3.1 Variabili d'ambiente richieste

```env
# PDND Credentials
PDND_CLIENT_ID=<UUID client PDND dell'ente>
PDND_KID=<Key ID della chiave pubblica registrata su PDND>
PDND_PRIVATE_KEY_PATH=/run/secrets/pdnd_private_key.pem
# oppure inline (per dev)
PDND_PRIVATE_KEY_PEM=<contenuto PEM — solo per sviluppo>

# PDND Auth Server
PDND_AUTH_URL=https://auth.interop.pagopa.it/token.oauth2
PDND_CLIENT_ASSERTION_AUDIENCE=auth.interop.pagopa.it/client-assertion
PDND_AUDIENCE=https://interop.pagopa.it/

# ANPR API endpoints
ANPR_BASE_URL_TEST=https://modipa-val.anpr.interno.it/govway/rest/in/MinInternoPortaANPR-PDND
ANPR_BASE_URL_PROD=https://modipa.anpr.interno.it/govway/rest/in/MinInternoPortaANPR-PDND
ANPR_CA_BUNDLE_PATH=/run/secrets/sogei-ca-test.pem
ANPR_SSL_VERIFY=true
ANPR_ENV=test  # test | prod

# Ente fruitore (per claims audit)
PDND_FRUITORE_USER_ID=GAIA-CBO  # userID da includere nel tracking
PDND_FRUITORE_USER_LOCATION=GAIA-SRV-CBO  # postazione
PDND_LOA=LOW  # livello di autenticazione
```

Validazioni runtime minime:
- `PDND_CLIENT_ID` obbligatorio
- `PDND_KID` obbligatorio
- almeno uno tra `PDND_PRIVATE_KEY_PATH` e `PDND_PRIVATE_KEY_PEM` obbligatorio
- se `PDND_PRIVATE_KEY_PATH` è valorizzato, il file deve esistere ed essere un PEM RSA valido

Comportamento applicativo:
- la sync manuale `POST /utenze/anpr/sync/{subject_id}` restituisce `503 Service Unavailable` con dettaglio esplicito se la configurazione PDND è assente o non valida
- in assenza di queste variabili il backend non può ottenere il voucher PDND né firmare gli header `Agid-JWT-*`
- sull'ambiente ANPR di collaudo con CA privata Sogei, il container backend deve fidarsi del certificato via `ANPR_CA_BUNDLE_PATH`; `ANPR_SSL_VERIFY=false` va considerato solo workaround temporaneo di sviluppo

### 3.2 Flusso autenticazione

```
┌─────────────────────────────────────────────────────────────────┐
│ auth.py — PdndAuthManager                                        │
│                                                                   │
│  1. build_client_assertion()                                      │
│     └─ JWT firmato con chiave privata RSA:                        │
│        { iss: client_id, sub: client_id,                          │
│          aud: pdnd_client_assertion_audience                      │
│               oppure <host_di_pdnd_auth_url>/client-assertion,    │
│          purposeId: opzionale per servizio,                       │
│          digest: opzionale con hash del TrackingEvidence,         │
│          jti: uuid4(), iat: now, exp: now+60s }                   │
│                                                                   │
│  2. get_voucher(purpose_id)  [cached per purpose,                 │
│                               rinnovato 5min prima di scadenza]   │
│     └─ POST PDND_AUTH_URL                                         │
│        client_id=<PDND_CLIENT_ID>                                 │
│        client_assertion_type=urn:ietf:params:oauth:...jwt-bearer  │
│        client_assertion=<JWT firmato>                             │
│        grant_type=client_credentials                              │
│        tracking digest derivato da `Agid-JWT-TrackingEvidence`    │
│        └─ ritorna: { access_token, expires_in }                   │
│                                                                   │
│  3. build_agid_jwt_signature(payload_bytes)                       │
│     └─ JWS del payload request (INTEGRITY_REST_02)               │
│        header: { alg: RS256, kid: KID, typ: JWT }                 │
│        payload: { iss, sub, aud=<endpoint ANPR normalizzato>,     │
│                   nbf, iat, exp, jti,                             │
│                   digest: { alg: SHA256, value: b64url(sha256) }, │
│                   signed_headers: [Digest, Content-Type] }        │
│                                                                   │
│  4. build_agid_jwt_tracking_evidence(endpoint, purpose_id)        │
│     └─ JWS per AUDIT_REST_02                                      │
│        claims: { iss, sub, aud=<endpoint ANPR normalizzato>,      │
│                  nbf, iat, exp, jti,                              │
│                  userID, userLocation, LoA,                       │
│                  purposeId (se richiesto) }                       │
└─────────────────────────────────────────────────────────────────┘
```

**Librerie Python richieste:**
- `cryptography` (già probabilmente presente)
- `PyJWT>=2.0` con supporto RS256
- `httpx` (async HTTP client — preferibile a `requests` per il backend async FastAPI)

---

## 4. ANPR API Client (`client.py`)

### 4.1 Chiamata C030 — Accertamento idANPR

**Endpoint**: `POST {base_url}/C030-servizioAccertamentoIdUnicoNazionale/v1/anpr-service-e002`

**Request body**:
```json
{
  "idOperazioneClient": "<uuid_progressivo_numerico_ente>",
  "criteriRicerca": {
    "codiceFiscale": "<CF_soggetto>"
  },
  "datiRichiesta": {
    "dataRiferimentoRichiesta": "<YYYY-MM-DD oggi>",
    "motivoRichiesta": "<numero pratica interno — es. GAIA-CHECK-{subject_id_short}>",
    "casoUso": "C030"
  }
}
```

**Headers**:
```
Authorization: Bearer <voucher>
Accept: application/json
Digest: SHA-256=<base64 sha256 body>
Agid-JWT-Signature: <JWS payload>
Agid-JWT-TrackingEvidence: <JWS tracking>
Content-Type: application/json
```

**Risposta attesa (200)**:
```json
{
  "idOperazioneANPR": "...",
  "listaSoggetti": {
    "datiSoggetto": [
      {
        "identificativi": {
          "idANPR": "<identificativo_unico_nazionale>"
        }
      }
    ]
  }
}
```

**Casi di errore**:
- `404` → CF non trovato in ANPR → `esito = not_found`
- `400` → request malformata → `esito = error`
- `listaAnomalie` valorizzata → parsare il codice anomalia per capire se è cancellazione non-decesso

### 4.2 Chiamata C004 — Verifica dichiarazione decesso

**Endpoint**: `POST {base_url}/C004-servizioVerificaDichDecesso/v1/anpr-service-e002`

**Request body** (verifica pura senza dati decesso — scopre se il soggetto risulta deceduto):
```json
{
  "idOperazioneClient": "<uuid_progressivo_numerico_ente>",
  "criteriRicerca": {
    "idANPR": "<anpr_id_soggetto>"
  },
  "datiRichiesta": {
    "dataRiferimentoRichiesta": "<YYYY-MM-DD oggi>",
    "motivoRichiesta": "<GAIA-CHECK-{subject_id_short}>",
    "casoUso": "C004"
  }
}
```

**NOTA**: Il campo `verifica.datiDecesso` è omesso intenzionalmente. In questa modalità il
servizio risponde con lo stato ANPR del soggetto alla data di riferimento senza confrontare
dati di decesso forniti dall'ente. I valori restituiti nel campo `infoSoggettoEnte` vanno
interpretati secondo il mapping AgID/ANPR (da validare sull'ambiente di test):

**Aggiornamento runtime**: l'ambiente ANPR/GovWay in uso risponde con `EN148` se la sezione
`verifica.datiDecesso` non viene inviata per `C004`. Il payload operativo GAIA include quindi
`verifica.datiDecesso.dataEvento = ieri` come minimo set richiesto dal caso d'uso.

| Chiave ANPR attesa | Valore | Significato |
|---|---|---|
| (TBD — validare da test) | `A` o `S` | Affermativo / Sì → deceduto |
| (TBD) | `N` | No → vivo |

**Risposta 200 — soggetto vivo**: `listaSoggetti` presente con `listaAnomalie` vuota o assente
**Risposta 200 — soggetto deceduto**: `listaAnomalie` con codice specifico decesso, oppure campo
`chiave/valore` con indicatore di decesso (da mappare su ambiente test ANPR)
**Risposta 404**: soggetto non trovato in ANPR alla data

> ⚠️ **TODO di integrazione**: Prima del go-live su produzione, eseguire almeno 3 chiamate
> sull'ambiente di test ANPR con soggetti noti (vivi e deceduti) per validare esattamente
> la struttura della risposta e il mapping chiave→stato. Aggiornare `client.py` di conseguenza.

### 4.3 Gestione `idOperazioneClient` (C004 — numerico crescente)

Per C004, `idOperazioneClient` deve essere numerico e crescente. Strategia:

```python
# Usa UNIX timestamp in millisecondi come ID operazione (crescente e univoco per l'ente)
id_operazione_client = str(int(time.time() * 1000))
```

Il valore va persistito in `anpr_check_log.id_operazione_client` per idempotenza:
se ANPR riceve lo stesso ID già processato, restituisce la risposta precedente.

Per C030, `idOperazioneClient` è alfanumerico — usare `str(uuid4())`.

---

## 5. Service Layer (`service.py`)

### 5.1 Costruzione coda prioritizzata

```python
async def build_check_queue(db: AsyncSession, config: AnprSyncConfig) -> list[str]:
    """
    Ritorna lista ordinata di subject_id (UUID str) da verificare.
    
    Priorità:
    1. Soggetti con utenza irrigua solo nell'anno precedente (non nell'anno corrente)
       JOIN cat_utenze_irrigue WHERE anno = YEAR-1 AND NOT EXISTS (anno = YEAR)
    2. Esclusione soggetti già deceased
    3. Ordinamento per data_nascita ASC (più anziani prima)
    4. Limitato a max_calls_per_day (considerando che per soggetti senza anpr_id
       servono 2 chiamate: C030 + C004)
    """
```

**Query SQL logica** (da tradurre in SQLAlchemy):

```sql
WITH candidati AS (
    SELECT DISTINCT
        s.id AS subject_id,
        p.data_nascita,
        p.anpr_id,
        p.stato_anpr,
        p.last_anpr_check_at,
        -- Flag priorità 1: presente nel ruolo anno scorso ma non quest'anno
        EXISTS (
            SELECT 1 FROM cat_utenze_irrigue u
            WHERE u.codice_fiscale = p.codice_fiscale
            AND u.anno_campagna = EXTRACT(YEAR FROM NOW()) - 1
        ) AS in_ruolo_anno_prec,
        NOT EXISTS (
            SELECT 1 FROM cat_utenze_irrigue u
            WHERE u.codice_fiscale = p.codice_fiscale
            AND u.anno_campagna = EXTRACT(YEAR FROM NOW())
        ) AS non_in_ruolo_corrente
    FROM ana_subjects s
    JOIN ana_persons p ON p.subject_id = s.id
    WHERE s.subject_type = 'person'
      AND p.codice_fiscale IS NOT NULL
      AND (p.stato_anpr IS NULL OR p.stato_anpr NOT IN ('deceased'))
      -- Non ritentare not_found troppo spesso
      AND (
          p.stato_anpr != 'not_found_anpr'
          OR p.last_anpr_check_at < NOW() - INTERVAL ':retry_days days'
      )
)
SELECT subject_id
FROM candidati
ORDER BY
    (in_ruolo_anno_prec AND non_in_ruolo_corrente) DESC,   -- priorità 1 prima
    data_nascita ASC NULLS LAST                            -- più anziani prima
LIMIT :max_calls_budget
```

**Budget chiamate**: poiché soggetti senza `anpr_id` richiedono C030 + C004 (2 chiamate),
il budget reale di soggetti verificabili è `max_calls_per_day / 1.5` in media. La logica
deve calcolare a runtime quante chiamate residue restano e fermarsi quando esaurite.

### 5.2 sync_single_subject()

```python
async def sync_single_subject(
    subject_id: str,
    db: AsyncSession,
    triggered_by: str,  # "job" | "user:{user_id}"
) -> AnprSyncResult:
    """
    1. Carica ana_persons del soggetto
    2. Se manca anpr_id → chiama _call_c030() → persiste anpr_id
    3. Se ora ha anpr_id → chiama _call_c004() → aggiorna stato_anpr
    4. Ritorna AnprSyncResult con esito e dettaglio
    """
```

### 5.3 run_daily_job()

```python
async def run_daily_job() -> AnprJobSummary:
    """
    1. Legge AnprSyncConfig
    2. Se job_enabled == False → ritorna subito
    3. Costruisce coda via build_check_queue()
    4. Per ogni subject_id nella coda:
        a. Chiama sync_single_subject(triggered_by="job")
        b. Incrementa contatore chiamate usate
        c. Se calls_used >= max_calls_per_day → interrompe
        d. Sleep configurabile tra chiamate (ANPR rate limiting)
    5. Ritorna summary: totale verificati, deceduti trovati, errori
    """
```

---

## 6. Scheduler (`scheduler.py`)

Integrazione con APScheduler già presente nel backend GAIA:

```python
from apscheduler.triggers.cron import CronTrigger

def register_anpr_jobs(scheduler: AsyncIOScheduler, app_state):
    """
    Registra il job ANPR sul scheduler esistente.
    Il cron viene letto da DB (AnprSyncConfig) ad ogni avvio.
    Se la config non esiste in DB, usa i default.
    """
    scheduler.add_job(
        run_daily_job_wrapper,
        trigger=CronTrigger.from_crontab(config.job_cron),
        id="anpr_daily_check",
        replace_existing=True,
        misfire_grace_time=3600,  # 1h di tolleranza su avvio ritardato
    )
```

---

## 7. API Endpoints (`routes.py`)

Prefisso router: `/utenze/anpr`

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| `POST` | `/sync/{subject_id}` | admin, reviewer | Sync singola soggetto |
| `GET` | `/sync/{subject_id}/status` | admin, reviewer, viewer | Stato ANPR soggetto |
| `GET` | `/log` | admin | Lista log chiamate ANPR (paginata) |
| `GET` | `/log/{subject_id}` | admin, reviewer | Log chiamate per soggetto specifico |
| `GET` | `/config` | admin | Lettura config job |
| `PUT` | `/config` | admin | Aggiornamento config job |
| `POST` | `/job/trigger` | admin | Trigger manuale job (usa budget giornaliero) |
| `GET` | `/job/status` | admin | Stato ultima esecuzione job |

---

## 8. Frontend — estensione scheda soggetto

### 8.1 Componente AnprStatusCard

Aggiungere alla pagina `frontend/src/app/anagrafica/subjects/[id]/page.tsx` (o path equivalente):

```tsx
// Nuovo componente: AnprStatusCard
// Mostra:
// - stato_anpr corrente con badge colorato:
//   alive → verde, deceased → rosso, unknown/null → grigio, not_found_anpr → arancione
// - data_decesso se deceased
// - last_anpr_check_at (ultimo controllo)
// - Pulsante "Verifica ANPR" (solo admin/reviewer)
//   → chiama POST /utenze/anpr/sync/{subject_id}
//   → mostra spinner durante chiamata
//   → aggiorna stato alla risposta
// - Link al log verifiche (solo admin)
```

### 8.2 Pagina configurazione job

Nuova pagina admin: `frontend/src/app/anagrafica/anpr-config/page.tsx`

```tsx
// Form per AnprSyncConfig:
// - max_calls_per_day (input numerico)
// - job_enabled (toggle)
// - job_cron (input testo con validazione cron)
// - lookback_years (input numerico)
// - retry_not_found_days (input numerico)
// - Pulsante "Salva configurazione"
// - Sezione "Stato job": ultima esecuzione, soggetti verificati, deceduti trovati
// - Pulsante "Esegui ora" (trigger manuale)
```

---

## 9. Migration Alembic

Una singola migration che:

1. Aggiunge colonne ANPR a `ana_persons`:
   - `anpr_id`, `stato_anpr`, `data_decesso`, `luogo_decesso_comune`, `last_anpr_check_at`, `last_c030_check_at`
2. Crea tabella `anpr_check_log`
3. Crea tabella `anpr_sync_config`
4. Inserisce la riga default di config (id=1 con valori default)

```
alembic revision --autogenerate -m "add_anpr_integration"
```

---

## 10. Dipendenze Python da aggiungere

```
# requirements.txt / pyproject.toml
PyJWT>=2.8.0          # JWT RS256 per client assertion PDND
httpx>=0.27.0         # HTTP async client per chiamate ANPR (se non già presente)
cryptography>=42.0.0  # RSA key loading (probabilmente già presente per Fernet)
```

---

## 11. Sicurezza

- La chiave privata PDND va montata come Docker secret o volume read-only, **mai** nelle env vars in chiaro nel `docker-compose.yml` di produzione
- Il CF nei payload ANPR non va loggato nel DB — `anpr_check_log` non ha colonna CF
- I log APScheduler per il job ANPR devono essere a livello INFO, non DEBUG (evitare esposizione payload)
- Il voucher PDND va cachato in memoria (variabile di classe `PdndAuthManager`) — non persistito su DB né log
- Rate limiting: rispettare almeno 500ms tra chiamate consecutive ANPR per evitare throttling

---

## 12. Sequenza di implementazione raccomandata

```
Step 1  → Migration Alembic (modelli DB)
Step 2  → models.py + schemas.py
Step 3  → auth.py (PDND JWT + voucher — testabile su ambiente PDND test)
Step 4  → client.py (C030 + C004 — validare su ANPR test con CF di test)
Step 5  → service.py (sync_single + build_queue)
Step 6  → routes.py + integrazione router backend
Step 7  → scheduler.py + registrazione job
Step 8  → Frontend: AnprStatusCard + sync button
Step 9  → Frontend: pagina config admin
Step 10 → Test integrazione end-to-end su ANPR test
```
