# Stato sincronizzazione INAZ negli snapshot GaTe Mobile

## Classificazione minuti XLSM — aggiornamento 2026-09-09

Nel ramo con dettaglio INAZ autorevole, `schedule_engine.classify_daily_record`
usa `services/inaz_minute_buckets.py` per riconciliare le categorie con i totali
contabilizzati. La durata lorda delle timbrature non crea ulteriori minuti
retribuiti. Una ripartizione temporale e mantenuta solo quando ordinario ed extra
coincidono con i totali INAZ; altrimenti sono conservati i totali senza inventare
quote notturne. Le timbrature originali non sono modificate.

Il sabato programmato di un operaio, con ordinario INAZ positivo e senza una
festivita ordinaria, non diventa automaticamente festivo. Esempio di regressione:
05:15–11:31 con ORD 360 e MPE 1 produce 360 minuti ordinari e 1 extra feriale,
non 331 minuti festivi e 45 festivi notturni aggiuntivi.

Il calendario preesistente resta invariato: 14 agosto `Vigilia Ferragosto`,
15 `Ferragosto`, 16 `Recupero Ferragosto`, di tipo `ordinary` (festivita).
Il tipo `ordinary` non significa feriale e non attiva `grants_recovery_day`,
riservato al tipo `suppressed`. Il 16/08/2026 domenicale non lavorato e esportato
da GATE come `RS`, salvo causale esplicita. Non vengono assegnati automaticamente
minuti o un recupero aggiuntivo dal solo nome del giorno. Questi test fissano il
comportamento corrente, non attestano una nuova regola contrattuale.

GAIA resta autorevole per `export_ordinary_minutes` e `export_extra_minutes`:
un null esplicito non autorizza il consumer a usare i minuti grezzi di una
giornata non pubblicabile. GATE condivide la stessa ripartizione fra Archivio2
e Archivio e rifiuta categorie incompatibili. Periodo esclusivo: primo–ultimo
giorno del mese, conteggio in minuti interi.

Verifiche ripetibili dalla directory `backend`:

```bash
.venv/bin/pytest tests/test_presenze_schedule_engine.py tests/test_presenze_inaz_minute_buckets.py --cov=app.modules.presenze.services.schedule_engine --cov=app.modules.presenze.services.inaz_minute_buckets --cov-branch --cov-fail-under=100
.venv/bin/pytest tests/test_gate_mobile_sync.py tests/test_operazioni_mobile_sync_api.py
```

Coverage richiesta al 100% dei due file runtime modificati, non dell'intero
backend. Il ratchet rispetto alla baseline di `9debc990` non rileva regressioni:
classificatore principale ciclomatica 64→61, cognitiva 77→71, LOC 136→133.
Nessuna modifica a baseline, schema DB, mapping identitari, auth o transazioni.

Rilascio coordinato: aggiornare GAIA backend e outbound, verificare snapshot
agosto e run riuscito, poi GATE sul VPS. Sul CED il backend usa un bind mount,
il job outbound puo usare codice nell'immagine: verificarli entrambi. Il deploy
deve conservare copie e immagini di rollback ed escludere modifiche estranee.
La verifica read-only in produzione del 9 settembre ha riscontrato coincidenza
GAIA/GATE per 1.085 giornate di 35 dipendenti, 252.893 minuti ordinari e 29.628
extra pubblicabili, senza differenze fra le otto categorie daily/monthly.
Nessuna validazione automatica o rettifica dei dati INAZ/KM/reperibilita.

## Decisione

Il contratto precedente non era sufficiente: `synced_from_gaia_at` indicava solo
la produzione dello snapshot GAIA e nessun campo esposto dimostrava l'esito di
una sincronizzazione con INAZ.

Gli endpoint seguenti mantengono `schema_version: 1` e aggiungono l'oggetto
globale retrocompatibile `inaz_sync`:

- `GET /api/mobile-sync/presenze/months`;
- `GET /api/mobile-sync/presenze/giornaliere?month=YYYY-MM`;
- `GET /api/mobile-sync/presenze/anomalie?month=YYYY-MM`.

Gli alias con suffisso `/snapshot` espongono lo stesso payload.

## Flusso GAIA verso INAZ

Il processo applicativo `backend` registra il job APScheduler
`presenze_auto_sync`. Il cron predefinito e `0 6,12,18 * * *` nel fuso
`Europe/Rome`, configurabile con `PRESENZE_AUTO_SYNC_CRON` e
`PRESENZE_AUTO_SYNC_TIMEZONE`. La configurazione applicativa deve inoltre avere
`presenze_auto_sync_config.job_enabled = true` e una credenziale attiva.

Il scheduler accoda uno o piu `PresenzeSyncJob`; il processo
`presenze-worker` li acquisisce dalla coda e usa lo scraper Playwright con una
credenziale INAZ. Ogni job persiste in `presenze_sync_jobs`:

- `created_at`, `started_at`, `finished_at`;
- `status`: `pending`, `running`, `completed`, `failed` o `cancelled`;
- `attempt_count`, contatori record e `error_detail` interno;
- periodo richiesto, eventuale gruppo/shard e progresso JSON;
- lease, heartbeat e retry del worker.

Il worker crea anche un `presenze_import_jobs` con `source = live-sync`. Per
ogni collaboratore esegue upsert su `presenze_collaborators`,
`presenze_daily_records`, sostituisce i `presenze_daily_punches` e rigenera i
`presenze_event_summaries`. Le anomalie Mobile non hanno una seconda pipeline:
sono calcolate dagli stessi record giornalieri e punch durante la costruzione
dello snapshot.

Ogni giornaliera pubblica anche `request_type`, `request_description`,
`request_status` e `request_authorized_by`, insieme a `justified_minutes` e
`absence_minutes`. GATE usa questi campi per rendere visibile il permesso che
accompagna un'anomalia di ore mancanti, senza modificare il calcolo operativo
di `missing_minutes` eseguito da GAIA.

Il primo slot giornaliero include anche il mese precedente fino al giorno 10;
gli altri slot aggiornano il mese corrente. Se il parallelismo e attivo, un
tentativo puo essere composto da piu shard. Il resolver considera riuscito il
tentativo solo quando l'intera coorte e `completed`, senza record o
collaboratori falliti.

## Contratto precedente

Esempio anonimizzato di `giornaliere`:

```json
{
  "schema_version": 1,
  "source": "gaia",
  "month": "2026-08",
  "rules_version": "presenze-2026-09-extra-5h-warning",
  "export_rules_version": "presenze-xlsm-2026-08",
  "synced_from_gaia_at": "2026-08-31T07:30:00Z",
  "records": [
    {
      "record_id": "018f...001",
      "collaborator_id": "018f...002",
      "collaborator_name": "COLLABORATORE 001",
      "employee_code": "P001",
      "work_date": "2026-08-31",
      "status": "ok",
      "review_status": "pending",
      "ordinary_minutes": 420,
      "extra_minutes": 0,
      "validated_at": null
    }
  ],
  "giornaliere": ["stessi oggetti di records"]
}
```

Esempio anonimizzato di `anomalie`:

```json
{
  "schema_version": 1,
  "source": "gaia",
  "month": "2026-08",
  "rules_version": "presenze-2026-09-extra-5h-warning",
  "synced_from_gaia_at": "2026-08-31T07:30:00Z",
  "anomalies": [
    {
      "record_id": "018f...001",
      "collaborator_id": "018f...002",
      "work_date": "2026-08-31",
      "severity": "warning",
      "reasons": ["extra_over_5h"],
      "operator_message": "Straordinario superiore alla soglia."
    }
  ],
  "anomalie": ["stessi oggetti di anomalies"]
}
```

Esempio anonimizzato di `months`:

```json
{
  "schema_version": 1,
  "source": "gaia",
  "rules_version": "presenze-2026-09-extra-5h-warning",
  "synced_from_gaia_at": "2026-08-31T07:30:00Z",
  "months": [
    {"month": "2026-07", "records_total": 2325},
    {"month": "2026-08", "records_total": 2410}
  ]
}
```

Non esistevano campi affidabili equivalenti a `inaz_updated_at`,
`inaz_last_success_at`, `inaz_last_attempt_at` o `inaz_sync_status`.
`PresenzeDailyRecord.updated_at` e un timestamp tecnico GAIA aggiornabile anche
da operazioni non INAZ; `validated_at` riguarda la validazione; `source_job_id`
non e esposto e non identifica in modo affidabile l'ultimo refresh INAZ di una
riga esistente. Nessuno di questi campi ha semantica di timestamp sorgente.

## Contratto esteso

Esempio di ultimo tentativo fallito con successo precedente:

```json
{
  "schema_version": 1,
  "source": "gaia",
  "month": "2026-08",
  "rules_version": "presenze-2026-09-extra-5h-warning",
  "synced_from_gaia_at": "2026-08-31T07:30:00Z",
  "inaz_sync": {
    "status": "degraded",
    "last_attempt_at": "2026-08-31T07:25:00Z",
    "last_success_at": "2026-08-30T07:25:12Z",
    "data_updated_at": "2026-08-30T07:25:12Z",
    "error_code": "inaz_sync_failed",
    "error_message": "The latest INAZ synchronization attempt did not complete successfully."
  },
  "records": [],
  "giornaliere": []
}
```

Semantica:

- `synced_from_gaia_at`: istante UTC in cui GAIA costruisce lo snapshot;
- `last_attempt_at`: inizio dell'ultimo tentativo worker effettivamente avviato;
  una riga solo accodata non conta come tentativo;
- `last_success_at`: fine dell'ultima coorte live INAZ completamente riuscita;
- `data_updated_at`: ultimo limite globale affidabile dei dati INAZ nello
  snapshot; coincide conservativamente con `last_success_at` e non avanza dopo
  run parziali o fallite;
- `status`: `success`, `running`, `degraded`, `error` o `never`;
- `error_code` e `error_message`: diagnostica pubblica a vocabolario fisso. Il
  testo grezzo `error_detail`, stack trace, SQL, credenziali e dati personali
  non sono esposti.

Per `giornaliere` e `anomalie` vengono considerati solo i job il cui periodo
interseca `month`. Per `months` lo stato e globale su tutti i periodi visibili.
`never` significa che non esiste alcun tentativo live osservabile nel perimetro,
anche se GAIA contiene record caricati da file.

Non viene aggiunto `inaz_updated_at` alla singola riga: INAZ non fornisce e GAIA
non persiste oggi un timestamp sorgente canonico per giornata. Aggiungerlo da
`updated_at` o dall'ora di risposta produrrebbe un'informazione falsa.

## Consumo GaTe Mobile

GaTe Mobile deve usare quattro fonti distinte:

- aggiornamento INAZ: `inaz_sync.status`, `data_updated_at`,
  `last_attempt_at`, `last_success_at`, `error_code`, `error_message`;
- generazione snapshot GAIA: `synced_from_gaia_at`;
- ricezione snapshot GaTe: timestamp locale persistito da GaTe al termine
  dell'acquisizione;
- connector GAIA: heartbeat/stato connector gia gestito da GaTe.

GAIA mantiene separatamente i cicli outbound in `gate_mobile_sync_run`, espone
la diagnostica amministrativa su
`GET /api/operazioni/mobile-gateway-sync/status` e pubblica l'heartbeat del
processo `gate-mobile-sync`. Questi valori non rappresentano lo stato INAZ e
non vengono copiati dentro `inaz_sync`.

## Migrazioni e operativita

Non sono richieste migrazioni. Il resolver usa `presenze_sync_jobs` gia
versionata. Il retry automatico conserva nel proprio storico
`previous_started_at` e `previous_finished_at`, cosi il tentativo precedente
resta osservabile quando lo stesso job viene riaccodato.

La configurazione operativa resta invariata: cron e timezone sono configurabili;
i servizi `backend` e `presenze-worker` devono essere attivi, e l'autosync deve
essere abilitata con una credenziale valida.

## Verifiche e deploy 2026-08-31

La suite mirata ha eseguito 90 test, inclusi successo, stato mai osservato,
fallimento dopo un successo, run in corso, timestamp assente o non valido,
snapshot vuoto con stato globale e compatibilita dei consumer esistenti. I tre
file runtime modificati hanno coverage aggregata `1028/1028`, pari al `100%`.
Il complexity ratchet rispetto al merge-base
`840c010001e0aa45434539c4cf96065de61bdc41` e passato senza findings.

Il deploy CED ha ricostruito l'immagine condivisa da `backend` e
`presenze-worker`, senza migrazioni. Dopo il riavvio entrambi i container erano
attivi, il backend era healthy e i tre endpoint autenticati restituivano HTTP
`200`, `schema_version: 1`, `source: gaia` e tutte le sei proprieta di
`inaz_sync`. Lo stato reale osservato al momento della verifica era `degraded`.
Il connector outbound resta un cron host separato ogni cinque minuti e non
viene usato per derivare lo stato INAZ. Un ciclo end-to-end post-deploy ha
pubblicato con HTTP `200` gli snapshot `months`, `giornaliere` e `anomalie` e
si e concluso senza failure.
