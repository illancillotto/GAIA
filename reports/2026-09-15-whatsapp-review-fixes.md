# Correzioni review promemoria WhatsApp

## Perimetro e stato

Corretti i sei rilievi della review su GAIA. Nessuna modifica a GATE,
nessun commit, deploy, attivazione provider o invio WhatsApp reale.
Le modifiche Presenze preesistenti del team e quelle GIS/code-quality
di altre sessioni restano nel working tree.

## Comportamento

- Lock PostgreSQL transaction-level su connessione dedicata, mantenuto
  attraverso i commit delle notifiche e rilasciato anche su eccezione.
- Tentativo SENDING persistito prima della chiamata sendText. Timeout,
  errore server o risposta senza ID producono UNKNOWN, senza retry automatico.
  Crash dopo l'invio lascia SENDING in quarantena. Recupero amministrativo
  tramite `reconcile_uncertain_attempt`, con evidenza e ID WAHA se inviato.
- NOT_ON_WHATSAPP resta ritentabile; FAILED riapre le giornate.
  Le ricevute durabili proteggono callback anticipate e duplicati;
  READ/DELIVERED prevalgono su FAILED tardivi.
- STOP, mapping, profilo, telefono, assenze e timbrature riletti dopo la pausa
  e dopo check-exists; se cambiano il tentativo e cancellato.
- Giorni pendenti persistiti oltre il lookback; i dati restano ricalcolati,
  quindi giornate corrette o validate vengono eliminate dal backlog.
- Payload WAHA validati: booleano per check-exists, ID per sendText.

Limite inevitabile: modifiche arrivate dopo l'ultimo controllo non annullano
una chiamata esterna gia partita. Non si dichiara exactly-once WAHA; i casi
incerti richiedono verifica umana invece di reinvio automatico.

## Verifiche mirate

- 56 test passati, incluse regressioni di tutti i rilievi.
- Coverage full-file 100%: 513 statement, 104 branch, zero mancanti.
  File: punch_reminder_job, punch_reminder_dispatch, punch_reminder_pending,
  whatsapp_receipts, whatsapp_waha e whatsapp_models.
- PostgreSQL 16 temporaneo: lock con pool/commit/competitor/eccezione;
  upgrade/downgrade/re-upgrade di 20260915_1200 e 20260915_1300;
  unicita giornate, upsert ricevute e persistenza tentativi verificati.
- Ruff e ratchet contro 2507f223 passano. Metriche prima su 3 servizi:
  40 callable, 0 errori, 1 warning. Dopo su 6 runtime: 53 callable,
  0 errori, 8 warning. Aumento funzionale per durabilita e riconciliazione,
  nessuna nuova violation error-level. Non e un hotspot di riduzione.
- Baseline globale invariata: resta il disallineamento gia noto, non
  assorbito da questa change.
- Graphify Presenze codice aggiornato tramite target dedicato.
- Graphify Presenze docs completato: `chunk 1/1 done`, nessun chunk fallito.
- Suite estesa Presenze/GATE/platform-scheduler conclusa con exit code 0;
  gli integration test senza database configurato vengono saltati nel repeat
  generale. I due nuovi test PostgreSQL sono stati eseguiti separatamente
  e nella suite strumentata, entrambi passati. Warning di fixture JWT corta
  e runpy gia esterni ai file corretti.

## Artefatti di verifica

- `/tmp/whatsapp-fix-coverage.log` e `/tmp/whatsapp-fix-coverage.json`
- `/tmp/whatsapp-fix-ratchet.log`
- `/tmp/whatsapp-fix-regression.log`: repeat suite Presenze/GATE/scheduler
- `/tmp/whatsapp-fix-graph-code.log` e `/tmp/whatsapp-fix-graph-docs.log`

Runbook aggiornato:
`domain-docs/presenze/docs/PRESENZE_PROMEMORIA_WHATSAPP_TIMBRATURE.md`.
