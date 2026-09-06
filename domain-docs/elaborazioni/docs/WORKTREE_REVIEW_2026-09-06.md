# Verifica modifiche residue del worktree

Ambito: Portal Health, logging scheduler, editor Festivita. Verifica iniziale
senza deploy; rilascio selettivo successivo autorizzato dall'utente e descritto
sotto. Nessun push. Il worker del rilascio SISTER precedente resta invariato.

## Correzioni

- Festivita: il riferimento all'elemento `article` usa `HTMLElement`, non
  l'inesistente `HTMLArticleElement`. Conservati editor evidenziato, focus,
  scroll e gestione delle tre categorie; test nuovo incluso nel commit.
- Portal Health: KPI credenziali operative e media delle esecuzioni uniche
  attribuite. Eventi senza credenziale o run ID non partecipano al calcolo.
  Calcolo estratto in `_credential_execution_totals`; presentazione dei due
  KPI separata in `CredentialExecutionKpis`, coerente con `DownloadKpi`.
- Scheduler: inizializzazione del logging in `main`. Non modifica frequenze,
  concorrenza o gestione dei job e non risolve i ritardi del loop condiviso.

## Evidenze

- Sei test backend passati; 100% statement e branch su telemetry_service,
  telemetry_schemas e platform_scheduler_runner.
- Sedici test frontend; coverage esplicita dei due componenti modificati.
- Typecheck globale, Ruff ed ESLint mirato verificati separatamente dai test.
- Metriche Portal Health backend: get_portal_health ciclomatica 15 -> 10,
  cognitiva 14 -> 9, LOC 64 -> 54; helper 6/5/9, sotto soglia. Estrazione
  caratterizzata, non rivendicata come riduzione della complessita aggregata.
- Ratchet contro baseline del merge-base `6d6278cb`: backend KPI e Festivita
  passano. Per il frontend Portal Health serve il corpus completo: la scansione
  ristretta genera un falso matching di spostamenti da file esclusi dal report.
  Il polling useEffect non e stato modificato rispetto al merge-base; il suo
  rilievo LOC 5 -> 6 deriva dalla baseline precedente, non dai nuovi KPI.
  Anche run_scheduler e invariato rispetto al merge-base: non attribuire alla
  singola aggiunta configure_logging i finding legacy della scansione ristretta.
- Baseline e report generati nel repository non modificati da questa verifica.
  Evidenze temporanee: `/tmp/external-fix-{before,after}.json`,
  `/tmp/external-fix-full-corpus-ratchet.json`,
  `/tmp/external-fix-{backend,frontend,typecheck,eslint}.log`.

## Separazione del lavoro

Commit indipendenti per Festivita, logging scheduler e KPI Portal Health.
Documentazione pregressa delle modularizzazioni e report generati restano
fuori dai commit funzionali: il report JSON residuo cambia perimetro e contiene
oltre 244 mila righe di diff, quindi richiede una decisione separata.
Il rimando della skill Graphify ad AGENTS.md e coerente con le regole correnti,
ma non e necessario per le tre correzioni funzionali.

## Deploy selettivo del 6 settembre

- Commit funzionali: `99610401`, `3113e347`, `f5ef8428`.
- Bundle CED: `/opt/gaia-releases/ui-f5ef8428`; checkout `/opt/gaia` non
  aggiornato e modifiche locali del server preservate.
- Backend derivato da `gaia-backend:sister-621cb157` con soli tre file
  runtime: runner scheduler, telemetry service e schemas. Diff verificato
  rispetto ai file del container attivo: solo le modifiche dei due commit.
- Frontend ricostruito dal commit del checkout CED `9e4bbed1`, con overlay
  della pagina Festivita, workspace Portal Health e relativi tipi. La vecchia
  immagine e stata costruita tre minuti dopo quel commit; package.json e
  next.config.mjs coincidono via SHA256. Non sono disponibili i sorgenti
  nell'immagine standalone: questa provenienza non e una prova riproducibile
  byte-per-byte dell'intera build precedente. Refactoring API e modifiche GIS
  successive del worktree locale non inclusi.
- Ripetuti i 16 test frontend sulla base selettiva: 100% statement, branch,
  funzioni e linee dei due componenti. Build Next completata, incluso
  typecheck. Warning legacy e npm audit con tre vulnerabilita (una high)
  delle dipendenze preesistenti: non dichiarare il repository privo di debito.
- Smoke della nuova immagine backend sul DB in transazione read-only: import
  e KPI validi; 5 credenziali operative e media 497.8 nella finestra osservata.
- Compose pinned e rollback con permessi 0600. Environment, command,
  entrypoint e mount verificati contro i container originali prima del deploy.
  Configurazioni contengono segreti: non allegarle al repository o ai log.
- Avvio selettivo `up -d --no-deps --no-build backend platform-scheduler
  frontend`, ore 10:00:46 UTC (12:00:46 Europe/Rome). Nessuna migrazione;
  Alembic resta `20260905_1100`. Worker visure non riavviato: stesso container
  `8782f4742cb6` avviato alle 09:30:35 UTC e stessa immagine SISTER.
- Immagine backend/scheduler `gaia-backend:ui-f5ef8428`:
  `sha256:4916a432a270845ce8b00bbfaf3e8202553a3e00ccd2164640bccb77f164c8d3`.
- Immagine frontend `gaia-frontend:ui-f5ef8428`:
  `sha256:72bebbd63e993d8e0cc765a749c7210d3f944c98fe77e29223faaf85c104bb50`.
- Tre servizi healthy; `/api/health`, `/elaborazioni/visure`,
  `/elaborazioni/portal-health`, `/presenze/festivita` HTTP 200 via porta8080.
  Pagine verificate anche nel container candidato prima del rollout.
  Non eseguita interazione browser autenticata o modifica Festivita reale.
- Logging scheduler ora visibile a INFO, con registrazione AutoSync e avvio
  APScheduler. Questa correzione non risolve latenze del loop o errori SISTER.
  Primo ciclo AutoSync `_run_job_wrapper` avviato alle 10:01:49 UTC e
  concluso `executed successfully` alle 10:01:53 UTC, senza lancio manuale.
- Prima del deploy: 25 documenti negli ultimi 30 minuti, ultimo alle09:39:49
  UTC. Alle10:02:44 nessun nuovo PDF dopo il deploy: login e riprese remoti
  continuano, con errori polling/form. Non dichiarare scarichi post-deploy
  verificati sulla sola base dello stato healthy o dei download precedenti.

Rollback selettivo, se necessario:

```sh
docker compose -p gaia \
  -f /opt/gaia-releases/ui-f5ef8428/compose.rollback.pinned.json \
  up -d --no-deps --no-build backend platform-scheduler frontend
```

Log locali del rilascio: `/tmp/ui-f5ef8428-{build,tests,deploy}.log`.
I quattro file residui del worktree restano esclusi, senza essere scartati.
