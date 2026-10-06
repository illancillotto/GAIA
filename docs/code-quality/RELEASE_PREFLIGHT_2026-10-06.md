# Preflight rilascio dopo le slice di complessita

## Stato verificato

Commit applicativo: `9a11320d344a230dc7c86c45065836e63dff3b83`, push
confermato su `origin/main` anche tramite `git ls-remote`. Il push pubblica
la storia committata da `6b61fd27` fino a questo commit, non soltanto banca ore.
Le modifiche documentali concorrenti nel working tree locale sono preservate
e non incluse. MPC/MCP resta escluso dalle slice di refactoring.

La slice banca ore ha 227 test router/API verdi e coverage full-file 100%
(221 statement, 72 branch), lint/format e ratchet mirato verdi. Review:
`domain-docs/presenze/docs/BANK_HOURS_COMPLEXITY_VALIDATION_2026-10-06.md`.
Graphify Presenze codice/docs e platform docs aggiornati; estrazioni docs
con `chunk 1/1 done`, senza warning di chunk semantici falliti.

## Gate globale

Il confronto dell'intero repository contro il merge-base del push
`6b61fd27` NON e verde: 24 finding, 17 `legacy_metric_regression` e
7 `new_callable_violation`. Non sono attribuiti alla sola slice banca ore.
Nessuna baseline, esclusione o soglia e stata aggiornata per assorbirli.

```bash
python tools/code_quality/complexity.py ratchet --base-ref 6b61fd27
```

Evidenza: `/tmp/gaia-release-audit-20261006/full-ratchet.json`.
Il controllo GitHub per lo SHA applicativo mostra soltanto check Dependabot
e dependency graph riusciti; non prova backend-ci, frontend-ci o code-quality-ci
verdi. Non equiparare l'assenza di quei check a un esito positivo.

Il push segnala inoltre 32 advisory Dependabot (1 critical, 15 high,
13 moderate, 3 low): non e stato svolto un audit vulnerabilita in questa slice.

## Riconciliazione CED

L'utente richiede esplicitamente di riconciliare gli hotfix con main prima
del deploy. Finora tutte le verifiche remote sono read-only.

- Checkout `/opt/gaia` sul CED: `6b61fd27`, sette file tracciati modificati,
  file runtime e overlay non tracciati. Nessun reset, stash o restore eseguito.
- I tre sorgenti SISTER `sister_exceptions.py`, `sister_request_rows.py` e
  `sister_requests_navigation.py` hanno AST identico a main.
- La cancellazione squadre e il controllo console-admin sono gia in main;
  il dispatcher differisce per il refactoring a tabella.
- La materializzazione inCass e la preservazione dei dettagli pesanti sono
  presenti in main. Il controllo proprietario dell'avviso e aggiunto in main;
  il read model accetta anche identificativi ordinari con prefisso `1`.
- L'ack di cancellazione squadra usa `team_id` anche in main. Altre funzioni
  Gate, recupero inCass e risoluzione soggetti differiscono e richiedono la
  verifica dei contratti/test, non una semplice equivalenza testuale.

Il checkout non descrive da solo i container in esecuzione:

| Servizio | Immagine rilevata |
| --- | --- |
| backend | `gaia-backend:turnisti-open-ended-44b0c4ac` |
| frontend | `gaia-frontend` |
| elaborazioni-worker-runtime | `gaia-elaborazioni-worker-runtime:irrigue-four-20261005` |

Gli overlay attivi comprendono inCass, recupero Capacitas/irrigue, quattro
worker paralleli e il compose override frontend. Gate sync e presenze worker
montano il backend della release `turnisti-open-ended-44b0c4ac` su `/app`.
Non e ancora dimostrata la riconciliazione completa delle immagini/overlay
attivi con il nuovo checkout. Tutti i servizi dotati di healthcheck risultano
healthy; il manifest release storico non prova lo SHA delle immagini attive.

## Decisione operativa

Deploy NON eseguito: nessun restart, migration, modifica dati o env remoto.
Il deploy standard `scripts/deploy-ced-gaia.sh` richiede checkout pulito,
builda lo stack base e copia l'env locale sul server; non usarlo per eliminare
implicitamente hotfix e configurazioni di produzione non riconciliati.

Prima del rilascio occorrono:

1. Chiudere o decidere esplicitamente i 24 finding globali in slice revisionabili.
2. Verificare le regressioni degli hotfix e le immagini realmente attive,
   conservando backup e possibilita di rollback prima di qualsiasi mutazione.
3. Confrontare overlay ed env senza pubblicare segreti, preservando volumi,
   segreti e configurazione canonica di produzione.
4. Dimostrare i gate della release, poi deploy canonico e smoke test finali.

Artefatti audit locali: `/tmp/gaia-release-audit-20261006/`;
checkpoint `/tmp/gaia-release-context-checkpoint-20261006.md`.
Il programma di complessita resta incompleto e non viene dichiarato concluso.
