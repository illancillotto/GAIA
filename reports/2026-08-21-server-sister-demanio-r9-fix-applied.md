# GAIA server CED — Fix applicato per Demanio_R9 / SISTER 501

Data: 2026-08-21 23:59 CEST circa  
Target: `serverCed` / `/opt/gaia` / `gaia-elaborazioni-worker-visure` / `gaia-postgres` DB `naap`  
Scope: intervento operativo e codice sul server CED. Nessuna credenziale o password riportata.

## Obiettivo

Evitare che gli errori HTTP 501 del portale SISTER consumino i tentativi delle singole visure e mandino righe sane in `failed/retry_exhausted`.

## Stato iniziale verificato

Batch server:

- `id`: `e3862317-8fa4-46fd-8c2b-23da253c40ef`
- `name`: `Demanio_R9`
- `status`: `processing`
- `total_items`: 3359
- `completed_items`: 0
- `failed_items`: 120
- errore dominante: HTTP `501` su `portale-rest/rs/initPortale`

Credenziali server:

- `catasto_credentials`: 8 righe totali
- attive totali: 6
- username SISTER distinti: 7
- per `user_id=1`: 7 credenziali totali, 5 attive

## Azioni eseguite

### 1. Stop worker visure

Eseguito su server:

```bash
cd /opt/gaia
docker compose stop elaborazioni-worker-visure
```

### 2. Backup configurazione

Creato backup:

```text
/opt/gaia/docker-compose.yml.bak-sister-retry-20260821_235449
```

### 3. Patch configurazione worker visure

Aggiunte al servizio `elaborazioni-worker-visure` in `docker-compose.yml`:

```yaml
ELABORAZIONI_MAX_REQUEST_ATTEMPTS: ${ELABORAZIONI_MAX_REQUEST_ATTEMPTS:-50}
ELABORAZIONI_SISTER_500_COOLDOWN_SEC: ${ELABORAZIONI_SISTER_500_COOLDOWN_SEC:-300}
ELABORAZIONI_SISTER_500_MAX_COOLDOWN_SEC: ${ELABORAZIONI_SISTER_500_MAX_COOLDOWN_SEC:-3600}
ELABORAZIONI_SISTER_500_GLOBAL_PAUSE_SEC: ${ELABORAZIONI_SISTER_500_GLOBAL_PAUSE_SEC:-900}
ELABORAZIONI_REQUEST_RETRY_DEFER_SEC: ${ELABORAZIONI_REQUEST_RETRY_DEFER_SEC:-300}
```

Verifica env effettivo nel container dopo restart:

```text
ELABORAZIONI_MAX_REQUEST_ATTEMPTS=50
ELABORAZIONI_REQUEST_RETRY_DEFER_SEC=300
ELABORAZIONI_SISTER_500_COOLDOWN_SEC=300
ELABORAZIONI_SISTER_500_GLOBAL_PAUSE_SEC=900
ELABORAZIONI_SISTER_500_MAX_COOLDOWN_SEC=3600
```

### 4. Reset righe bruciate dal blackout SISTER

Reset DB mirato, solo per il batch `Demanio_R9` e solo per righe:

```text
status = failed
last_error_code = retry_exhausted
```

Risultato:

```text
reset_rows = 120
```

Poi corretto il contatore batch da conteggio reale richieste.

### 5. Patch codice worker

Creato backup:

```text
/opt/gaia/modules/elaborazioni/worker/sister_worker_reliability.py.bak-sister-server-attempt-20260821_235738
```

Patch applicata in `SisterRequestRepository.reset_for_retry(...)`:

```python
if error_code == "sister_server_error":
    # HTTP 5xx/portale SISTER instabile is not a request-specific
    # visura failure. Keep the row resumable without consuming the
    # per-request retry budget while global/credential cooldowns
    # throttle the portal.
    request.attempts = max((request.attempts or 0) - 1, 0)
```

Effetto: quando il portale SISTER dà HTTP 5xx, la richiesta torna `pending` senza consumare il budget retry della visura.

### 6. Test eseguiti

Test mirati sul server:

```bash
PYTHONPATH=/opt/gaia/backend:/opt/gaia/modules/elaborazioni/worker \
./.venv/bin/python -m pytest \
  modules/elaborazioni/worker/tests/test_worker_reliability_claims.py \
  modules/elaborazioni/worker/tests/test_worker.py::test_sister_server_error_cooldown_uses_progressive_backoff \
  modules/elaborazioni/worker/tests/test_worker.py::test_sister_server_error_cooldown_is_capped -q
```

Risultato:

```text
26 passed in 19.05s
```

### 7. Build e restart worker

Eseguito:

```bash
docker compose build elaborazioni-worker-visure
docker compose create --force-recreate elaborazioni-worker-visure
docker compose start elaborazioni-worker-visure
```

Verificato che la patch è presente nell’immagine running:

```text
/app/worker/sister_worker_reliability.py contiene:
if error_code == "sister_server_error":
    request.attempts = max((request.attempts or 0) - 1, 0)
```

### 8. Normalizzazione tentativi pre-patch

Le righe `pending/sister_server_error` già create prima della patch avevano attempts 1/3. Sono state normalizzate a 0 perché il loro errore è portale SISTER, non errore visura.

Risultato:

```text
UPDATE 10
pending / sister_server_error / attempts=0: 15
```

## Stato finale verificato

Batch:

```text
status: processing
total_items: 3359
completed_items: 0
failed_items: 0
skipped_items: 0
not_found_items: 0
current_operation: Portale SISTER instabile, pausa globale 888s prima della ripresa
```

Richieste:

```text
pending / attempts=0 / no error code: 3344
pending / attempts=0 / sister_server_error: 15
failed: 0
```

## Stato SISTER

Il portale continua a rispondere HTTP `501` su `initPortale`; il worker ora va in pausa globale lunga e non brucia più le righe come `retry_exhausted`.

## Note operative

- Durante `docker compose create --force-recreate elaborazioni-worker-visure`, Docker Compose ha ricreato/riavviato anche `gaia-postgres` per dipendenza. DB verificato healthy subito dopo.
- Container verificati: `gaia-postgres` healthy, `gaia-backend` healthy, `gaia-frontend` healthy, worker visure up.
- Il batch non completa finché SISTER continua a dare HTTP 501; però ora resta riprendibile e non perde richieste.

## Prossimi step raccomandati

1. Monitorare dopo la pausa globale di 900s.
2. Se SISTER torna OK, il batch dovrebbe procedere con le credenziali attive.
3. Se SISTER continua a dare 501, lasciare il worker in cooldown/pausa oppure fermarlo manualmente per non martellare il portale.
4. Portare questa patch in branch/PR pulita e allinearla anche con la patch locale `sister_credential_pool.py` già testata.
