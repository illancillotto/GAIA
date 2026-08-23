# GAIA/SISTER — Demanio_R9 completamento finale

Data: 2026-08-23 13:31 CEST circa
Target: `serverCed` / batch `Demanio_R9` (`e3862317-8fa4-46fd-8c2b-23da253c40ef`)
Scope: recupero finale dei 21 failed residui, monitor e verifica DB.

## Stato iniziale del recupero finale

Dopo il primo recupero massivo il batch era:

```text
completed: 3338 / 3359
failed: 21
skipped: 0
```

Breakdown dei 21:

```text
16 flow_failed / CAPTCHA manuale non arrivato entro timeout
5 retry_exhausted / massimo tentativi SISTER raggiunto
```

## Azioni eseguite

1. Aggiornato monitor Hermes del batch per controllare anche `awaiting_captcha` e allegare l'immagine CAPTCHA quando presente.
2. Portato il monitor da `every 15m` a `every 2m` durante il recupero.
3. Allungata finestra CAPTCHA manuale del worker:

```text
CAPTCHA_MANUAL_TIMEOUT_SEC=900
CAPTCHA_MANUAL_ATTEMPTS=5
```

4. Aumentato budget retry transitorio SISTER nel compose:

```text
ELABORAZIONI_MAX_REQUEST_ATTEMPTS=50
```

5. Reset mirato delle 21 richieste residue a `pending`.
6. I primi 16 sono stati recuperati/completati rapidamente.
7. Per le ultime 5, il worker multi-credenziale produceva `sister_correlation_error` perché vedeva più righe nuove SISTER ambigue; quindi ho fatto retry pulito single-credential:

```text
credential pinned: 62a686a7-cdb4-4ab6-a6b8-74fca19a88d8
remote state/correlation fields cleared on remaining non-completed rows
```

Questo ha evitato l'ambiguità e ha permesso al worker di completare le ultime 5.

## Stato finale verificato live

Query finale su PostgreSQL server CED:

```text
status: completed
total_items: 3359
completed_items: 3359
failed_items: 0
skipped_items: 0
current_operation: Batch terminato
completed_at: 2026-08-23 11:30:00 UTC
```

Distribuzione richieste:

```text
completed: 3359
```

## Monitor

Il cron di monitor specifico `GAIA SISTER Demanio_R9 monitor` è stato messo in pausa dopo il completamento per evitare alert ripetuti su batch finito.

```text
job_id: e89baebd6156
state: paused
```

## Risultato

Il batch `Demanio_R9` è completato al 100%:

```text
3359 / 3359 completate
0 failed
0 skipped
```

## Note sicurezza

- Nessuna password/token riportato.
- Nessun commit/push eseguito.
- Backup DB per reset precedenti già creati:
  - `catasto_batches_recovery_20260823_final21`
  - `catasto_visure_requests_recovery_20260823_final21`
- Le visure già completate sono state preservate durante tutti i reset mirati.
