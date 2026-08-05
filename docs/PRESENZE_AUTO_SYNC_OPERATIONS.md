# Presenze Auto Sync Operations

Data: 2026-08-05

## Frequenza

La sincronizzazione automatica Presenze e schedulata dal backend con APScheduler:

```text
PRESENZE_AUTO_SYNC_CRON=0 6,12,18 * * *
PRESENZE_AUTO_SYNC_TIMEZONE=Europe/Rome
```

Gli slot ordinari sono quindi 06:00, 12:00 e 18:00 Europe/Rome. Se un job e ancora `pending` o `running`, lo slot successivo viene saltato per non sovrapporre scrape Inaz lunghi.

Dal 2026-08-05 l'autosync lavora in modalita parallela a shard quando sono disponibili collaboratori gia noti in `presenze_collaborators`. Il trigger non crea piu un singolo full scrape monolitico: calcola l'elenco delle matricole attive, esclude quelle gia coperte da job `pending/running` sullo stesso periodo e accoda piu job con `params_json.employee_codes`.

Configurazione operativa:

```text
PRESENZE_WORKER_CONCURRENCY=3
PRESENZE_AUTO_SYNC_PARALLEL_ENABLED=true
PRESENZE_AUTO_SYNC_PARALLEL_CHUNK_SIZE=50
PRESENZE_AUTO_SYNC_PARALLEL_MAX_JOBS=4
PRESENZE_AUTO_SYNC_FAILED_EMPLOYEE_RETRY_ENABLED=true
PRESENZE_AUTO_SYNC_FAILED_EMPLOYEE_RETRY_MAX_ATTEMPTS=2
PRESENZE_AUTO_SYNC_FAILED_EMPLOYEE_RETRY_BATCH_SIZE=15
```

Con i default attuali il worker Presenze mantiene fino a 3 processi `sync_worker` contemporanei. L'autosync crea al massimo 4 shard per finestra, bilanciati rispetto alla dimensione target del blocco. Lo shard successivo resta `pending` e parte appena si libera uno slot.

## Garanzie operative

- Il trigger automatico usa un advisory lock PostgreSQL transazionale prima di creare o riaccodare job. Questo evita job duplicati quando il backend gira con piu processi `uvicorn`.
- Il worker di coda reclama il prossimo job `pending` con `FOR UPDATE SKIP LOCKED`, cosi piu worker non possono prendere lo stesso job se il servizio viene scalato.
- La riconciliazione stale marca `failed` i sync `pending` senza worker dopo 5 minuti e i sync `running` oltre `PRESENZE_SYNC_RUNNING_STALE_AFTER_HOURS`.
- Il supervisor `presenze-worker` marca `failed` i job `running` orfani rimasti appesi dopo restart/crash del container. Il controllo non si affida piu solo al PID, perche i PID sono locali al namespace del container e possono essere riusati.
- Quando un sync diventa `failed` o `cancelled`, l'import job collegato viene chiuso nello stesso stato se era ancora `pending` o `running`.
- Un fallimento auto-sync non viene ritentato se un altro auto-sync `completed` con stessa credenziale e stesso periodo ha gia coperto quel tentativo. Questo evita il retry di duplicati storici creati da race tra scheduler.
- Un job auto-sync `failed` viene riaccodato solo dopo `PRESENZE_AUTO_SYNC_RETRY_DELAY_HOURS`, fino a `PRESENZE_SYNC_MAX_ATTEMPTS`.
- In modalita parallela, un fallimento di uno shard non blocca la creazione degli shard successivi per matricole non gia aperte. La deduplica usa `period_start`, `period_end`, `credential_id` e `params_json.employee_codes`.
- A fine shard completato, gli errori per singolo dipendente vengono raccolti da `scrape_result.errors` e accodati automaticamente in micro-job `trigger = auto_failed_employee_retry`, fino a `PRESENZE_AUTO_SYNC_FAILED_EMPLOYEE_RETRY_MAX_ATTEMPTS`. Questo evita di ripetere tutto lo shard quando falliscono poche matricole.

## Metadati shard

I job shard espongono nel `params_json`:

- `trigger = "auto"`
- `sync_group_id`: id comune della run parallela
- `shard_index` e `shard_count`
- `target_scope` con suffisso `_shard`
- `employee_codes`: matricole assegnate allo shard
- `worker_mode = "queue_worker"` e `worker_instance_id` quando il worker reclama il job

I micro-job di recupero dipendenti falliti espongono inoltre:

- `trigger = "auto_failed_employee_retry"`
- `retry_source = "failed_employee_codes"`
- `parent_sync_job_id`
- `failed_employee_retry_attempt`
- `source_sync_group_id` e `source_shard_index`

## Diagnosi produzione

Verificare prima i record `presenze_sync_jobs`:

```sql
select id, status, created_at, started_at, finished_at, records_imported, error_detail
from presenze_sync_jobs
where created_at >= now() - interval '3 days'
order by created_at desc;
```

Verificare una run parallela per gruppo:

```sql
select
  id,
  status,
  records_imported,
  records_errors,
  params_json->>'shard_index' as shard_index,
  jsonb_array_length((params_json->'employee_codes')::jsonb) as employees,
  params_json->'progress'->>'completed_collaborators' as completed,
  params_json->'progress'->>'total_collaborators' as total,
  params_json->'progress'->>'last_event_at' as last_event_at
from presenze_sync_jobs
where params_json->>'sync_group_id' = '<sync_group_id>'
order by (params_json->>'shard_index')::int;
```

Poi verificare eventuali import appesi:

```sql
select id, status, created_at, started_at, finished_at, records_imported, error_detail
from presenze_import_jobs
where status in ('pending', 'running')
order by created_at desc;
```

Se le giornaliere non cambiano tra due controlli ravvicinati, non e automaticamente un errore: il full scrape puo durare ore e l'aggiornamento avviene mentre i collaboratori vengono importati, non in polling continuo.

In modalita parallela, un segnale sano e vedere almeno uno tra `records_imported`, `records_errors`, `completed_collaborators` o `last_event_at` cambiare su uno degli shard `running`. Se tutti gli shard `running` restano fermi oltre il timeout per collaboratore o se il worker non ha processi figli, verificare i log artifact:

```bash
docker compose exec -T presenze-worker sh -c \
  'tail -120 /runtime-data/presenze/sync/<job_id>/worker.log'
```

Per verificare la concorrenza reale:

```bash
docker compose exec -T presenze-worker ps -eo pid,ppid,stat,etime,cmd
```

Per vedere i micro-retry dei dipendenti falliti:

```sql
select id, status, records_imported, records_errors,
       params_json->>'parent_sync_job_id' as parent_job,
       params_json->>'failed_employee_retry_attempt' as retry_attempt,
       params_json->'employee_codes' as employee_codes
from presenze_sync_jobs
where params_json->>'trigger' = 'auto_failed_employee_retry'
order by created_at desc;
```
