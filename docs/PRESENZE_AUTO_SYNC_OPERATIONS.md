# Presenze Auto Sync Operations

Data: 2026-08-03

## Frequenza

La sincronizzazione automatica Presenze non e continua. Il backend registra uno scheduler APScheduler con cron:

```text
PRESENZE_AUTO_SYNC_CRON=0 6,12,18 * * *
PRESENZE_AUTO_SYNC_TIMEZONE=Europe/Rome
```

Gli slot ordinari sono quindi 06:00, 12:00 e 18:00 Europe/Rome. Se un job e ancora `pending` o `running`, lo slot successivo viene saltato per non sovrapporre scrape Inaz lunghi.

## Garanzie operative

- Il trigger automatico usa un advisory lock PostgreSQL transazionale prima di creare o riaccodare job. Questo evita job duplicati quando il backend gira con piu processi `uvicorn`.
- Il worker di coda reclama il prossimo job `pending` con `FOR UPDATE SKIP LOCKED`, cosi piu worker non possono prendere lo stesso job se il servizio viene scalato.
- La riconciliazione stale marca `failed` i sync `pending` senza worker dopo 5 minuti e i sync `running` oltre `PRESENZE_SYNC_RUNNING_STALE_AFTER_HOURS`.
- Quando un sync diventa `failed` o `cancelled`, l'import job collegato viene chiuso nello stesso stato se era ancora `pending` o `running`.
- Un fallimento auto-sync non viene ritentato se un altro auto-sync `completed` con stessa credenziale e stesso periodo ha gia coperto quel tentativo. Questo evita il retry di duplicati storici creati da race tra scheduler.
- Un job auto-sync `failed` viene riaccodato solo dopo `PRESENZE_AUTO_SYNC_RETRY_DELAY_HOURS`, fino a `PRESENZE_SYNC_MAX_ATTEMPTS`.

## Diagnosi produzione

Verificare prima i record `presenze_sync_jobs`:

```sql
select id, status, created_at, started_at, finished_at, records_imported, error_detail
from presenze_sync_jobs
where created_at >= now() - interval '3 days'
order by created_at desc;
```

Poi verificare eventuali import appesi:

```sql
select id, status, created_at, started_at, finished_at, records_imported, error_detail
from presenze_import_jobs
where status in ('pending', 'running')
order by created_at desc;
```

Se le giornaliere non cambiano tra due controlli ravvicinati, non e automaticamente un errore: il full scrape puo durare ore e l'aggiornamento avviene mentre i collaboratori vengono importati, non in polling continuo.
