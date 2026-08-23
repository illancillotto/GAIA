# GAIA/SISTER — Demanio_R9 CAPTCHA recovery resume

Data: 2026-08-23 09:55 CEST circa
Target: `serverCed` / batch `Demanio_R9` (`e3862317-8fa4-46fd-8c2b-23da253c40ef`)
Scope: fix worker CAPTCHA manuale, reset mirato richieste recuperabili, ripresa batch controllata.

## Fix applicato

Comportamento richiesto da Ale:

> Se un CAPTCHA viene inserito sbagliato, SISTER a volte lo cambia; quindi il CAPTCHA nuovo va riverificato.

È stato modificato il worker per non chiudere subito la richiesta dopo un CAPTCHA manuale rifiutato:

- dopo un CAPTCHA manuale sbagliato, il worker fa `reload_captcha()`;
- cattura una nuova immagine;
- riapre l'attesa manuale sul nuovo CAPTCHA;
- ripete fino a `CAPTCHA_MANUAL_ATTEMPTS` tentativi;
- default server-side: `5` tentativi manuali.

File modificati/deployati su `serverCed`:

```text
modules/elaborazioni/worker/visura_flow.py
modules/elaborazioni/worker/worker.py
modules/elaborazioni/worker/tests/test_visura_flow.py
```

## Test

RED verificato localmente:

```text
test_manual_wrong_answer_reloads_and_waits_for_new_captcha
FAILED prima del fix
```

GREEN verificato localmente:

```text
2 passed
105 passed
```

GREEN verificato nel container server appena buildato:

```text
2 passed in 0.06s
```

## Deploy

Azioni eseguite su `serverCed`:

```text
docker compose stop elaborazioni-worker-visure
copy file patchati
docker compose build elaborazioni-worker-visure
docker compose up -d elaborazioni-worker-visure
```

Worker ripartito e ha preso in carico il batch.

## Reset DB mirato

Backup tabellare creato in PostgreSQL prima del reset:

```text
catasto_batches_recovery_20260823_captcha
catasto_visure_requests_recovery_20260823_captcha
```

Reset eseguito solo su richieste recuperabili del batch:

```text
171 failed: flow_failed + Automatic CAPTCHA exhausted; manual CAPTCHA response missing
112 skipped: Release requested by user + Credenziale SISTER liberata su richiesta utente
```

Totale reset:

```text
283 richieste
```

Stato subito dopo reset:

```text
batch: processing
completed: 3076
pending: 283
failed: 0
skipped: 0
```

## Monitor post-ripresa

Dopo la ripartenza il batch ha ripreso a completare PDF:

```text
completed: 3090
failed: 0
skipped: 0
```

Successiva verifica:

```text
completed: 3098
pending: 258
processing: 2
awaiting_captcha: 1
failed: 0
skipped: 0
```

Il batch è quindi tornato operativo e senza failed/skipped, ma ora richiede input CAPTCHA manuale su una riga.

## Stato attuale

```text
status: processing
completed_items: 3098 / 3359
failed_items: 0
skipped_items: 0
awaiting_captcha: 1
```

La nuova patch farà sì che, se il CAPTCHA manuale inserito è sbagliato e SISTER ne propone uno nuovo, il worker riapra l'attesa sul nuovo CAPTCHA invece di chiudere la richiesta in failed.

## Note sicurezza

- Nessuna password o token riportato.
- Nessun commit/push eseguito.
- Le richieste già completate sono state preservate.
