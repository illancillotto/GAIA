# GAIA/SISTER — Demanio_R9 failed/skipped analysis

Data: 2026-08-23 09:40 CEST circa
Target: `serverCed` / batch `Demanio_R9` (`e3862317-8fa4-46fd-8c2b-23da253c40ef`)
Scope: sola lettura su cron output, runtime Docker e DB PostgreSQL. Nessuna credenziale o dato personale riportato.

## Stato verificato

Cron monitor `e89baebd6156` ha riportato:

```text
status=failed completed=3076/3359 failed=171 skipped=112
operation=Batch terminato
```

DB batch live:

```text
status: failed
total_items: 3359
completed_items: 3076
failed_items: 171
skipped_items: 112
current_operation: Batch terminato
started_at: 2026-08-21 11:38:16 UTC
completed_at: 2026-08-23 03:38:03 UTC
```

Distribuzione richieste live:

```text
completed: 3076
failed: 171
skipped: 112
```

## Perché 171 failed

I `failed` sono quasi tutti dovuti al flusso CAPTCHA automatico non completato:

```text
failed / attempts=1 / last_error_code=flow_failed / current_operation=Fallita / count=170
failed / attempts=2 / last_error_code=flow_failed / current_operation=Fallita / count=1
error_message=Automatic CAPTCHA exhausted; manual CAPTCHA response missing
```

Interpretazione: il worker ha scaricato molte visure, ma su 171 richieste il CAPTCHA non è stato risolto/fornito entro la policy automatica; quelle righe sono state marcate `failed` con `flow_failed`.

## Perché 112 skipped

Gli `skipped` hanno il marker di release sessioni:

```text
skipped / attempts=1 / current_operation=Release requested by user / count=112
error_message=Credenziale SISTER liberata su richiesta utente
```

Interpretazione: sono righe finite nello stato di rilascio credenziale/sessione, non errori di particella. Il marker deriva dalla procedura precedente di logout/rilascio sessioni SISTER; su queste righe il batch conserva `Release requested by user`.

## Telemetria portale rilevante

Sul batch risultano anche errori portale storici, ma non sono la spiegazione primaria dei 171 failed correnti:

```text
http_error 501: 1498
http_error 500: 6
execution_complete success: 3076
download success: 3076
```

Il vecchio problema `initPortale`/HTTP 501 è ancora presente come telemetria, ma il worker è riuscito comunque a completare 3076 PDF; il blocco operativo finale che ha prodotto i failed è CAPTCHA.

## Conclusione

- Il batch non è fallito perché "tutto" non funziona: ha completato `3076/3359` PDF.
- I `171 failed` sono richieste bloccate da CAPTCHA automatico esaurito/mancata risposta manuale.
- I `112 skipped` sono righe con marker di rilascio sessione/credenziale (`Release requested by user`).
- Totale torna: `3076 + 171 + 112 = 3359`.

## Prossima azione consigliata

Prima di rilanciare in massa:

1. verificare/riparare policy CAPTCHA server-side: i CAPTCHA non risolti dovrebbero andare in attesa/notifica manuale invece di diventare subito `failed`;
2. decidere se recuperare le `112 skipped` da release marker a pending;
3. dopo il fix, fare reset mirato solo delle `171 failed` da `flow_failed`/CAPTCHA e delle `112 skipped` da release marker, preservando i `3076 completed`;
4. riprendere il batch con monitor attivo.

Nessuna modifica DB o restart è stata eseguita in questa analisi.
