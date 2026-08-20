# Test Coverage 100% Plan

Data di adozione: `2026-06-19`

## Obiettivo

Da `2026-06-19` GAIA adotta come obiettivo di piattaforma la copertura `100%` del codice runtime versionato.

Il requisito si applica a:

- `backend/app/**`
- `frontend/src/**`
- `modules/elaborazioni/worker/**`
- script runtime versionati che partecipano a flussi operativi o di manutenzione applicativa

Il gate sui file cambiati a `100%` resta attivo come protezione immediata, ma non e piu sufficiente come definizione di "done" finale per il repository.

## Stato di partenza

Il repository ha gia alcuni mattoni utili:

- CI backend con `pytest --cov=app` e gate `100%` sui file backend runtime cambiati
- CI frontend con Vitest coverage e gate `100%` sui file frontend runtime cambiati
- suite backend ampia e gia distribuita per dominio
- suite frontend unit + e2e gia presenti su moduli critici

Il repository non misura ancora in modo coerente il `100%` globale:

- il gate CI oggi blocca solo i file cambiati, non il totale del perimetro runtime
- `frontend/vitest.config.ts` restringe la coverage ai file cambiati o, in fallback, a un sottoinsieme esplicito
- `backend/.coveragerc` e attualmente focalizzato su un perimetro wiki e non puo essere considerato la configurazione finale del gate repository-wide
- esistono script e servizi operativi con copertura parziale o assente

## Principi operativi

- Nessun nuovo debito di coverage: ogni file runtime nuovo o modificato deve restare a `100%`.
- Niente compensazioni: un file scoperto non puo essere compensato da altri file sovra-testati.
- Prima unit test puri, poi integration/e2e dove servono side effect, IO, DB, rete o browser.
- Dove il codice e troppo accoppiato per essere testato bene, il refactor per testabilita fa parte del lavoro.
- La convergenza al `100%` totale avanza per perimetri chiari e con gate progressivi.

## Piano di azione

### Fase 1 - Definire perimetro e strumentazione

1. Congelare il perimetro "runtime versionato" da coprire in CI:
   - backend applicativo
   - frontend applicativo
   - worker
   - script operativi supportati
2. Separare gli esclusi legittimi:
   - test
   - cache
   - artefatti generati
   - `node_modules`
   - `__pycache__`
   - `*.d.ts` generati o puramente tipizzanti
3. Allineare la configurazione coverage:
   - backend: sostituire la configurazione wiki-only con una config repository-wide
   - frontend: rimuovere il fallback a include parziale e misurare tutto `frontend/src/**`
   - worker/script: aggiungere report dedicati dove oggi non esistono
4. Pubblicare in CI una lista ordinata dei file sotto soglia per ogni job.

### Fase 2 - Costruire il baseline dei gap

1. Generare report completi backend, frontend e worker sul branch principale.
2. Produrre una matrice per file con:
   - percentuale coverage
   - tipo di test mancante
   - dipendenze esterne da simulare
   - priorita
3. Classificare i gap in quattro classi:
   - puro unit test mancante
   - test DB/API mancanti
   - test browser/UI mancanti
   - codice da refactorare prima di poter essere coperto bene

### Fase 3 - Chiudere prima il codice a basso costo e alto impatto

Ordine consigliato:

1. servizi puri, parser, normalizzatori, scheduler, helper, mapper
2. script operativi Python e shell con side effect simulabili
3. router/backend API con fixture locali e mocking delle dipendenze esterne
4. componenti frontend puri, helper UI e adapter client
5. flussi browser o integrazione che richiedono Playwright o database reale

Questa fase deve ridurre rapidamente il numero di file scoperti e stabilizzare il baseline.

### Fase 4 - Ridurre l'accoppiamento che impedisce il 100%

Per i file che restano sotto soglia:

- estrarre wrapper per rete, filesystem, clock, env e subprocess
- separare orchestration da business logic
- ridurre funzioni monolitiche in unit testabili
- portare il client frontend monolitico verso adapter o helper piu piccoli quando blocca la copertura
- introdurre fixture e factory condivise per evitare duplicazione massiva nei test

Il refactor e parte del piano coverage, non attivita separata.

### Fase 5 - Attivare gate progressivi fino al totale

1. Mantenere il gate `100%` sui file cambiati.
2. Aggiungere gate warn-only sul totale per backend, frontend e worker.
3. Portare i gate a fail-on-threshold per perimetri chiusi:
   - singolo modulo backend
   - cluster frontend
   - worker/script
4. Quando tutti i perimetri sono verdi, sostituire i gate parziali con il gate repository-wide `100%`.

## Backlog iniziale per stream

### Backend

- uniformare `.coveragerc` e `pytest` al perimetro totale applicativo
- coprire i servizi operativi non wiki rimasti fuori dal baseline
- consolidare fixture condivise per DB, auth, scheduler e storage
- aggiungere test dedicati per script amministrativi e job notturni

### Frontend

- estendere `vitest` a tutto `frontend/src/**`
- eliminare i fallback coverage limitati ai file cambiati o a sample statici
- aggiungere test unitari per helper e adapter ancora inglobati nelle page
- usare Playwright solo per i flussi che non possono essere chiusi con Vitest

### Worker e script

- misurare `modules/elaborazioni/worker/**` con report coverage esplicito
- coprire script Python operativi con test su subprocess, env e filesystem finti
- per gli script shell, preferire smoke test automatizzati e wrapper testabili dove utile

## Criteri di done

Il requisito puo dirsi chiuso solo quando tutte queste condizioni sono vere:

- tutti i file runtime nel perimetro definito risultano al `100%`
- backend, frontend e worker pubblicano report completi in CI
- i gate CI falliscono sul totale, non solo sui file cambiati
- il piano e aggiornato con eventuali esclusioni residue esplicite e motivate
- i moduli nuovi ereditano automaticamente la stessa policy senza eccezioni manuali

## Sequenza operativa raccomandata

1. Allargare la misurazione coverage a tutto il runtime.
2. Fotografare il gap reale con report versionati negli artifact CI.
3. Chiudere parser/helper/script e codice puro.
4. Chiudere API, DB e scheduler.
5. Chiudere frontend e2e residuo.
6. Attivare il gate repository-wide `100%`.

## Nota di governance

Fino alla chiusura completa del piano:

- nessuna feature puo introdurre nuovo codice runtime scoperto
- ogni modulo toccato deve migliorare o mantenere il proprio delta coverage
- eventuali eccezioni temporanee devono essere documentate in questo file con motivo, perimetro e data di rientro

## Note operative

- `2026-07-22` - frontend Capacitas inCASS job monitor
  (`frontend/src/lib/capacitas-incass-job-visibility.ts`)
  Per la change sulla vista collassabile dei job `Avvisi pagamenti`, la logica nuova di priorita
  e limite lista e stata isolata in helper puro e validata con:
  `cd frontend && npm run test:unit -- tests/unit/capacitas-incass-job-visibility.test.ts`
  e
  `cd frontend && VITEST_COVERAGE_INCLUDE='src/lib/capacitas-incass-job-visibility.ts' npm run test:coverage -- tests/unit/capacitas-incass-job-visibility.test.ts`
  Esito validato il `2026-07-22`: `100%` statements/branches/functions/lines sul runtime nuovo.

- `2026-07-23` - backend Capacitas inCASS recovery credenziali
  (`backend/app/services/elaborazioni_capacitas.py`,
  `backend/app/services/elaborazioni_capacitas_runtime.py`,
  `backend/app/services/elaborazioni_capacitas_incass.py`,
  `modules/elaborazioni/worker/worker.py`)
  Per la change sulla ripartenza dei job `Avvisi pagamenti`, il runtime inCASS rimette in
  `queued_resume` gli errori credenziali temporanei e il worker non reclama job Capacitas senza
  credenziali disponibili. Validazioni:
  `pytest --cov=app.services.elaborazioni_capacitas --cov-report=term-missing --cov-fail-under=100 ...`
  sui 4 test credenziali Capacitas: `100%`.
  `pytest --cov=app.services.elaborazioni_capacitas_runtime --cov=app.services.elaborazioni_capacitas_incass ...`
  sui test mirati recovery: runtime `100%`; suite Capacitas estesa con 4 test non correlati esclusi:
  `130 passed, 6 deselected`, `elaborazioni_capacitas_incass.py` al `100%`.
  `pytest --cov=worker --cov-report=term-missing modules/elaborazioni/worker/tests/test_worker.py`:
  `19 passed`; il file worker monolitico resta sotto il target globale, ma le nuove righe
  `_next_capacitas_job`/credential gate sono coperte e non risultano tra le righe mancanti.

- `2026-07-22` - backend + frontend Ruolo import pagamenti CapaciTas
  (`app/modules/ruolo/routes/tributi_routes.py`, `app/modules/ruolo/schemas.py`,
  `app/modules/ruolo/tributi_repositories.py`,
  `frontend/src/app/ruolo/tributi/import-pagamenti/page.tsx`, `frontend/src/lib/ruolo-api.ts`)
  Per la change sull'import pagamenti CSV/XLSX/XLSM con mapping opzionale/autodetect, report
  anomalie e deduplica, le misurazioni affidabili nel workspace locale GAIA sono state:
  `docker compose exec -T backend coverage run --source=app/modules/ruolo -m pytest tests/ruolo/test_tributi_api.py tests/test_ruolo_small_runtime.py -q`
  seguita da
  `docker compose exec -T backend coverage report --include='app/modules/ruolo/tributi_repositories.py,app/modules/ruolo/routes/tributi_routes.py,app/modules/ruolo/schemas.py'`
  e
  `cd frontend && VITEST_COVERAGE_INCLUDE='src/app/ruolo/tributi/import-pagamenti/page.tsx,src/lib/ruolo-api.ts' npm run test:coverage -- tests/unit/ruolo-tributi-placeholder-pages.test.tsx tests/unit/ruolo-api-client.test.ts`
  Esito validato il `2026-07-22`: `100%` sui file runtime backend e frontend toccati dalla
  change.

- `2026-07-22` - backend + frontend Ruolo tributi (`app/modules/ruolo/routes/tributi_routes.py`,
  `app/modules/ruolo/schemas.py`, `app/modules/ruolo/tributi_repositories.py`,
  `frontend/src/app/ruolo/tributi/page.tsx`, `frontend/src/lib/ruolo-api.ts`)
  Per la change sui KPI header della sezione `/ruolo/tributi` e sul rename del template
  solleciti, le misurazioni affidabili nel workspace locale GAIA sono state:
  `cd backend && ../.venv/bin/pytest tests/ruolo/test_tributi_api.py --cov=app.modules.ruolo.tributi_repositories --cov=app.modules.ruolo.routes.tributi_routes --cov=app.modules.ruolo.schemas --cov=app.modules.ruolo.services.tributi_reminder_service --cov-report=term-missing`
  e
  `cd frontend && VITEST_COVERAGE_INCLUDE='src/app/ruolo/tributi/page.tsx,src/lib/ruolo-api.ts' npm run test:coverage -- tests/unit/ruolo-tributi-page.test.tsx tests/unit/ruolo-api-client.test.ts`
  Esito validato il `2026-07-22`: `100%` sui file runtime backend e frontend toccati dalla
  change.

- `2026-07-28` - frontend Ruolo tributi (`frontend/src/app/ruolo/tributi/page.tsx`)
  Per la change UI/UX della modale `Dettaglio tributo` e del link cliccabile `Apri link
  CapaciTas`, la misurazione affidabile nel workspace locale GAIA e stata:
  `cd frontend && VITEST_COVERAGE_INCLUDE='src/app/ruolo/tributi/page.tsx' npm run test:coverage -- tests/unit/ruolo-tributi-page.test.tsx tests/unit/ruolo-tributi-detail-page.test.tsx`
  Esito validato il `2026-07-28`: `100%` statements/branches/functions/lines sul runtime
  frontend modificato.

- `2026-07-22` - backend Ruolo tributi (`app/modules/ruolo/services/tributi_reminder_service.py`)
  Per la change sul template batch multi-annualita dei solleciti, la misurazione affidabile nel
  workspace locale GAIA e stata:
  `.venv/bin/coverage run --source=backend/app/modules/ruolo/services -m pytest backend/tests/ruolo/test_tributi_api.py -q`
  seguita da
  `.venv/bin/coverage report --include='backend/app/modules/ruolo/services/tributi_reminder_service.py'`
  Esito validato il `2026-07-22`: `100%` sul file runtime
  `backend/app/modules/ruolo/services/tributi_reminder_service.py`.

- `2026-07-22` - backend Ruolo tributi (`app/modules/ruolo/tributi_repositories.py`)
  Per la change sul wizard solleciti con annualita selezionabili e numero avviso progressivo,
  la misurazione affidabile nel workspace locale GAIA e stata:
  `.venv/bin/coverage run --source=backend/app/modules/ruolo -m pytest backend/tests/ruolo/test_tributi_api.py -q`
  seguita da
  `.venv/bin/coverage report --include='backend/app/modules/ruolo/tributi_repositories.py,backend/app/modules/ruolo/services/tributi_reminder_service.py'`
  Esito validato il `2026-07-22`: `100%` su
  `backend/app/modules/ruolo/tributi_repositories.py` e conferma del `100%` su
  `backend/app/modules/ruolo/services/tributi_reminder_service.py`.

- `2026-07-08` - backend ANPR (`app/modules/utenze/anpr/routes.py`, `app/modules/utenze/anpr/service.py`)
  Nel workspace locale GAIA la misurazione coverage mirata tramite `pytest-cov` puo fallire in collection con SQLAlchemy 2.x (`AssertionError: Type <class 'object'> is already registered`) pur avendo test verdi. Per questo perimetro il comando affidabile e:
  `.venv/bin/coverage run --source=app/modules/utenze/anpr -m pytest tests/test_anpr_service.py tests/test_anpr_routes.py -q`
  seguito da
  `.venv/bin/coverage report --include='app/modules/utenze/anpr/service.py,app/modules/utenze/anpr/routes.py'`
  Esito validato il `2026-07-08`: `100%` su entrambi i file runtime ANPR.

- `2026-07-23` - backend Capacitas inCASS autosync status refresh
  (`app/core/config.py`, `app/modules/elaborazioni/capacitas/models.py`,
  `app/modules/elaborazioni/incass_autosync_scheduler.py`,
  `app/services/elaborazioni_capacitas_incass.py`,
  `app/modules/ruolo/tributi_repositories.py`)
  Per la change sul refresh leggero dell'autosync `Avvisi pagamenti`, gli avvisi gia
  sincronizzati aggiornano solo stato/griglia operativa preservando dettaglio, partitario,
  PDF e importi; i nuovi avvisi possono essere arricchiti con dettaglio/partitario tramite
  flag dedicati. Misurazione affidabile nel container backend:
  `coverage run --rcfile=/dev/null -m pytest tests/test_config.py tests/test_incass_autosync_scheduler.py tests/test_elaborazioni_capacitas.py tests/ruolo/test_tributi_api.py -q -k 'not rpt_certificato_link_requires_explicit_context_params and not rpt_certificato_link_requires_context_even_with_unique_local_snapshot'`
  seguita da
  `coverage report --rcfile=/dev/null --include='app/core/config.py,app/modules/elaborazioni/capacitas/models.py,app/modules/elaborazioni/incass_autosync_scheduler.py,app/services/elaborazioni_capacitas_incass.py,app/modules/ruolo/tributi_repositories.py' --fail-under=100`.
  Esito validato il `2026-07-23`: `100%` sui file runtime backend toccati.

- `2026-07-23` - backend/worker Capacitas inCASS autosync window
  (`app/core/config.py`, `app/modules/elaborazioni/incass_autosync_scheduler.py`,
  `app/services/elaborazioni_capacitas_incass.py`, `modules/elaborazioni/worker/worker.py`)
  Per la change che limita i job automatici Ruolo/inCASS alla finestra `20:00-06:00 Europe/Rome`,
  il gate backend affidabile e:
  `coverage run --rcfile=/dev/null -m pytest tests/test_config.py tests/test_incass_autosync_scheduler.py tests/test_elaborazioni_capacitas.py tests/ruolo/test_tributi_api.py -q -k 'not rpt_certificato_link_requires_explicit_context_params and not rpt_certificato_link_requires_context_even_with_unique_local_snapshot'`
  seguito dal report mirato sui file backend inCASS con `--fail-under=100`.
  Esito validato il `2026-07-23`: `100%` sui file runtime backend toccati.
  Per il worker monolitico e stata eseguita la suite completa
  `pytest modules/elaborazioni/worker/tests/test_worker.py -q`: `32 passed`; la coverage full-file
  resta sotto target per debito preesistente del worker, ma le nuove righe del gate inCASS non risultano
  nei missing del report mirato.

- `2026-07-23` - Poste Online in Elaborazioni
  (`backend/app/modules/elaborazioni/posta_online/schemas.py`,
  `backend/app/modules/elaborazioni/posta_online_routes.py`,
  `backend/app/services/elaborazioni_posta_online.py`,
  `modules/elaborazioni/worker/posta_online_client.py`,
  `modules/elaborazioni/worker/posta_online_sync.py`,
  `frontend/src/components/elaborazioni/posta-online-workspace.tsx`)
  Per la change su credenziali Poste, test login worker-only, scraper polite e workspace
  `/elaborazioni/posta-online`, le misurazioni affidabili sono state:
  `cd backend && coverage run --rcfile=/dev/null --source=app.modules.elaborazioni.posta_online.schemas,app.modules.elaborazioni.posta_online_routes,app.services.elaborazioni_posta_online -m pytest tests/test_elaborazioni_posta_online.py -q`
  seguita da
  `coverage report --rcfile=/dev/null --fail-under=100 --show-missing`.
  Esito: `100%` su schemi, route e service backend Poste.
  `coverage run --rcfile=/dev/null --source=posta_online_sync,posta_online_client -m pytest modules/elaborazioni/worker/tests/test_worker.py modules/elaborazioni/worker/tests/test_posta_online_client.py -q`
  seguita da
  `coverage report --rcfile=/dev/null --fail-under=100 --show-missing`.
  Esito: `100%` su client e runner worker Poste.
  Rivalidato il `2026-07-23` dopo la logica di sync completa con pacing anti-rate-limit:
  `49 passed`, `posta_online_client.py` e `posta_online_sync.py` al `100%`.
  `cd frontend && VITEST_COVERAGE_INCLUDE='src/components/elaborazioni/posta-online-workspace.tsx' npm run test:coverage -- posta-online-workspace.test.tsx`.
  Esito: `100%` statements/branches/functions/lines sul componente runtime nuovo.
  Nota: `frontend/src/lib/api.ts` resta aggregatore API sotto eccezione temporanea gia aperta; le
  funzioni Poste sono esercitate dai test componente, mentre il gate per-file resta sul runtime
  UI nuovo.

- `2026-07-23` - Ruolo tributi preview solleciti
  (`app/modules/ruolo/services/tributi_reminder_service.py`,
  `frontend/src/app/ruolo/tributi/page.tsx`)
  Per la change sulla modale immediata di `Avviso sollecito` e sulla risoluzione di Chromium
  da cache Playwright nel container backend, le misurazioni affidabili sono state:
  `cd backend && COVERAGE_FILE=/tmp/gaia-backend-tributi-reminder.coverage python -m pytest tests/ruolo/test_tributi_api.py --cov=app.modules.ruolo.services.tributi_reminder_service --cov-report=term-missing -q`.
  Esito: `100%` su `tributi_reminder_service.py`.
  `cd frontend && VITEST_COVERAGE_INCLUDE='src/app/ruolo/tributi/page.tsx' npm run test:coverage -- ruolo-tributi-page.test.tsx`.
  Esito: `100%` statements/branches/functions/lines su `page.tsx`.

- `2026-07-23` - Riesecuzione finale gate Ruolo/Elaborazioni/Poste
  Rieseguiti i gate mirati sul perimetro modificato:
  backend InCASS/Ruolo nel container backend con `100%` su config, modelli Capacitas,
  scheduler autosync, service inCASS e repository tributi; backend Poste con `100%` su schemi,
  route e service; worker Poste con `100%` su client e sync; frontend Poste con `100%` sul

- `2026-07-27` - Ruolo tributi permessi preview e solleciti
  (`app/modules/ruolo/routes/tributi_routes.py`,
  `frontend/src/app/ruolo/tributi/page.tsx`,
  `frontend/src/app/ruolo/tributi/solleciti/page.tsx`)
  Per la change che riallinea preview e wizard solleciti al permesso di consultazione
  `ruolo.tributi.view`, le misurazioni affidabili sono state:
  `cd backend && COVERAGE_RCFILE=/dev/null coverage run --branch --source=app.modules.ruolo.routes.tributi_routes -m pytest tests/ruolo/test_tributi_api.py && COVERAGE_RCFILE=/dev/null coverage report -m`.
  Esito: `100%` statements/branches su `tributi_routes.py`.
  `cd frontend && VITEST_COVERAGE_INCLUDE='src/app/ruolo/tributi/page.tsx,src/app/ruolo/tributi/solleciti/page.tsx' npm run test:coverage -- tests/unit/ruolo-tributi-page.test.tsx tests/unit/ruolo-tributi-placeholder-pages.test.tsx`.
  Esito: `100%` statements/branches/functions/lines su `page.tsx` e `solleciti/page.tsx`.
  workspace; frontend Ruolo tributi con `100%` su `page.tsx`; typecheck frontend pulito.
  Nota operativa: i coverage Vitest vanno eseguiti in sequenza, non in parallelo, per evitare
  conflitti sulla directory condivisa `frontend/coverage/.tmp`.

- `2026-07-27` - Ruolo tributi template GAIA default per wizard batch
  (`app/modules/ruolo/tributi_repositories.py`,
  `frontend/src/app/ruolo/tributi/page.tsx`)
  Per la change che rende il template GAIA con bollettino postale il default del wizard
  `Genera PDF nel NAS` e del fallback backend batch, le misurazioni affidabili sono state:
  `cd backend && PYTHONPATH=. .venv/bin/pytest tests/ruolo/test_tributi_api.py --cov=app.modules.ruolo.tributi_repositories --cov-report=term-missing --cov-fail-under=100 -q`.
  Esito: `100%` su `tributi_repositories.py`.

- `2026-08-05` - Ruolo tributi Regole ruolo e solleciti multi-annualita
  (`app/modules/ruolo/tributi_repositories.py`,
  `app/modules/ruolo/services/tributi_reminder_service.py`,
  `frontend/src/app/ruolo/tributi/page.tsx`)
  Per la change che raggruppa in preview gli avvisi coperti dallo stesso gruppo `Regole ruolo`,
  conserva il collegamento policy anche su importi effettivi inCASS e riusa il numero avviso
  preview a parita di CF/P.IVA, annualita e avvisi inclusi, le misurazioni affidabili sono state:
  `pytest backend/tests/ruolo/test_tributi_api.py --cov=app.modules.ruolo.tributi_repositories --cov=app.modules.ruolo.services.tributi_reminder_service --cov-report=term-missing --cov-fail-under=100 -q`.
  Esito: `100%` su `tributi_repositories.py` e `tributi_reminder_service.py`.
  `cd frontend && VITEST_COVERAGE_INCLUDE=src/app/ruolo/tributi/page.tsx npm run test:coverage -- tests/unit/ruolo-tributi-page.test.tsx`.
  Esito: `100%` statements/branches/functions/lines su `page.tsx`.
  `cd frontend && VITEST_COVERAGE_INCLUDE=src/app/ruolo/tributi/page.tsx npm run test:coverage -- tests/unit/ruolo-tributi-page.test.tsx`.
  Esito: `100%` statements/branches/functions/lines su `page.tsx`.

- `2026-08-06` - Ruolo tributi interessi Euribor 6M + delibera e recupero BCE
  (`app/modules/ruolo/services/euribor.py`,
  `app/modules/ruolo/tributi_repositories.py`,
  `app/modules/ruolo/routes/tributi_routes.py`,
  `app/modules/ruolo/schemas.py`,
  `frontend/src/app/ruolo/tributi/page.tsx`,
  `frontend/src/lib/ruolo-api.ts`)
  Per la change che calcola gli interessi come `Euribor medio 6 mesi + tasso da delibera`
  e consente il recupero automatico dal Data Portal BCE, le misurazioni affidabili sono:
  `cd backend && coverage run --rcfile=/dev/null --source=app.modules.ruolo.services.euribor,app.modules.ruolo.tributi_repositories,app.modules.ruolo.routes.tributi_routes,app.modules.ruolo.schemas -m pytest tests/ruolo/test_tributi_api.py -q`.
  Seguito da `coverage report --rcfile=/dev/null --include='app/modules/ruolo/services/euribor.py,app/modules/ruolo/tributi_repositories.py,app/modules/ruolo/routes/tributi_routes.py,app/modules/ruolo/schemas.py' --fail-under=100 --show-missing`.
  Esito: `100%` su `euribor.py`, `tributi_repositories.py`, `tributi_routes.py` e `schemas.py`.
  Frontend: `cd frontend && VITEST_COVERAGE_INCLUDE='src/app/ruolo/tributi/page.tsx,src/lib/ruolo-api.ts' npm run test:coverage -- tests/unit/ruolo-tributi-page.test.tsx tests/unit/ruolo-api-client.test.ts`.
  Esito: `100%` statements/branches/functions/lines su `page.tsx` e `ruolo-api.ts`.

- `2026-08-07` - Ruolo tributi riferimento visibile bollettino TD 896
  (`app/modules/ruolo/services/tributi_reminder_service.py`)
  Per la regressione in cui il riferimento visibile del bollettino mostrava il codice cliente
  derivato con padding/controcode invece del numero avviso GAIA, la misurazione affidabile e:
  `cd backend && coverage run --rcfile=/dev/null --source=app.modules.ruolo.services.tributi_reminder_service -m pytest tests/ruolo/test_tributi_api.py -q`.
  Seguito da `coverage report --rcfile=/dev/null --include='app/modules/ruolo/services/tributi_reminder_service.py' --fail-under=100 --show-missing`.
  Esito: `100%` su `tributi_reminder_service.py`.

- `2026-08-10` - Ruolo tributi layout bollettino TD 896 e preview sempre rigenerata
  (`app/modules/ruolo/services/tributi_reminder_service.py`,
  `app/modules/ruolo/tributi_repositories.py`)
  Per la change che riposiziona il bollettino GAIA entro i margini di stampa, stampa
  l'indirizzo di residenza sotto `eseguito da` e forza la rigenerazione del PDF in
  `preview_only` senza riusare documenti gia generati, la misurazione affidabile e:
  `cd backend && PYTHONPATH=. .venv/bin/pytest tests/ruolo/test_tributi_api.py --cov=app.modules.ruolo.services.tributi_reminder_service --cov=app.modules.ruolo.tributi_repositories --cov-report=term-missing --cov-fail-under=100 -q`.
  Esito: `100%` su `tributi_reminder_service.py` e `tributi_repositories.py`.
  Verifica mirata aggiuntiva:
  `cd backend && PYTHONPATH=. .venv/bin/pytest tests/ruolo/test_tributi_api.py -q -k 'gaia_reminder_template_contract or generate_batch_reminder_pdf or preview_regenerates_document_when_notice_identity_is_reused'`.
  Esito: template GAIA e rigenerazione preview validati.

- `2026-07-27` - Ruolo tributi ordine pagina e navigazione hash sidebar
  (`frontend/src/app/ruolo/tributi/page.tsx`,
  `frontend/src/components/layout/nav-item.tsx`)
  Per la regressione in cui `/ruolo/tributi` mostrava/percepiva sempre Raccomandate, le
  misurazioni affidabili sono state:
  `cd frontend && VITEST_COVERAGE_INCLUDE=src/app/ruolo/tributi/page.tsx npm run test:coverage -- tests/unit/ruolo-tributi-page.test.tsx`.
  Esito: `100%` statements/branches/functions/lines su `page.tsx`.
  `cd frontend && VITEST_COVERAGE_INCLUDE=src/components/layout/nav-item.tsx npm run test:coverage -- tests/unit/app-shell.test.tsx`.
  Esito: `100%` statements/branches/functions/lines su `nav-item.tsx`.

- `2026-07-27` - Ruolo tributi renderer PDF GAIA con partitario lungo
  (`app/modules/ruolo/services/tributi_reminder_service.py`)
  Per la regressione in cui un partitario reale lungo riduceva/spostava la pagina bollettino TD
  896, la misurazione affidabile e stata:
  `cd backend && PYTHONPATH=. .venv/bin/pytest tests/ruolo/test_tributi_api.py --cov=app.modules.ruolo.services.tributi_reminder_service --cov-report=term-missing --cov-fail-under=100 -q`.
  Esito: `100%` su `tributi_reminder_service.py`.

- `2026-07-28` - Ruolo tributi numero avviso per annualita nel template GAIA
  (`app/modules/ruolo/services/tributi_reminder_service.py`)
  Per la change che aggiunge la colonna `Numero avviso` alla tabella riepilogo della prima
  pagina del template GAIA, la misurazione affidabile e stata:
  `cd backend && PYTHONPATH=. .venv/bin/pytest tests/ruolo/test_tributi_api.py --cov=app.modules.ruolo.services.tributi_reminder_service --cov-report=term-missing --cov-fail-under=100 -q`.
  Esito: `46 passed`, `100%` su `tributi_reminder_service.py`.

- `2026-07-28` - Access token utente a 12 ore
  (`app/core/config.py`)
  Per la change che porta il default `JWT_EXPIRE_MINUTES` a `720`, la misurazione affidabile
  e stata:
  `coverage run --rcfile=/dev/null --source=backend/app/core -m pytest backend/tests/test_config.py backend/tests/test_auth_service.py -q`.
  Esito report:
  `coverage report --rcfile=/dev/null --include='backend/app/core/config.py' --fail-under=100 --show-missing`;
  `100%` su `backend/app/core/config.py`.

- `2026-07-28` - Ricerca operativa home Utenze/Ruolo/Catasto
  (`app/api/router.py`, `app/modules/search/*`, `frontend/src/app/page.tsx`,
  `frontend/src/lib/operational-search-api.ts`)
  Per la change che introduce `GET /search`, l'alias `GET /api/search`, matching multi-token su
  Utenze/Catasto/Ruolo e la barra centrale in home, le misurazioni
  affidabili sono state:
  `cd backend && .venv/bin/coverage run --rcfile=/dev/null --source=app.modules.search,app.api.router -m pytest tests/test_operational_search_api.py -q`.
  Esito report:
  `.venv/bin/coverage report --rcfile=/dev/null --include='app/modules/search/*.py,app/api/router.py' --fail-under=100 --show-missing`;
  `100%` su router API e modulo `app.modules.search`.
  `cd frontend && VITEST_COVERAGE_INCLUDE='src/app/page.tsx,src/lib/operational-search-api.ts' npm run test:coverage -- tests/unit/api-request.test.ts tests/unit/home-page-presence-widget.test.tsx`.
  Esito: `100%` statements/branches/functions/lines sui runtime frontend toccati.

- `2026-07-28` - Home search-first, stato operativo Utenze/Ruolo/Catasto/NAS e admin module
  (`frontend/src/app/page.tsx`)
  Per la change che riduce il cruscotto home a riga secondaria, rimuove KPI rete dalla home,
  sposta `Attivita utenti GAIA` sotto la griglia, rende `Amministrazione GAIA` un modulo e
  usa summary Utenze/NAS per anagrafiche e dati NAS,
  la misurazione affidabile e stata:
  `cd frontend && VITEST_COVERAGE_INCLUDE='src/app/page.tsx' npm run test:coverage -- tests/unit/home-page-presence-widget.test.tsx`.
  Esito: `100%` statements/branches/functions/lines su `frontend/src/app/page.tsx`.

- `2026-07-29` - Correzione KPI Stato operativo home per distretti ruolo e particelle FD
  (`frontend/src/app/page.tsx`)
  Per la change che separa le particelle a ruolo `FD`/fuori distretto dal conteggio dei
  distretti operativi, la misurazione affidabile e:
  `cd frontend && VITEST_COVERAGE_INCLUDE='src/app/page.tsx' npm run test:coverage -- tests/unit/home-page-presence-widget.test.tsx`.
  Esito: `100%` statements/branches/functions/lines su `frontend/src/app/page.tsx`.

- `2026-07-29` - Ricerca operativa riusabile in home e topbar globale
  (`frontend/src/app/page.tsx`, `frontend/src/components/search/operational-search-box.tsx`,
  `frontend/src/components/layout/topbar.tsx`, `frontend/src/components/layout/app-shell.tsx`,
  `frontend/src/components/layout/app-shell-context.tsx`)
  Per la change che estrae la barra in `OperationalSearchBox`, mantiene la variante hero in home
  e aggiunge la variante compatta con `Ctrl/Cmd+K` nella topbar delle pagine `AppShell`,
  la misurazione affidabile e:
  `cd frontend && VITEST_COVERAGE_INCLUDE='src/app/page.tsx,src/components/search/operational-search-box.tsx,src/components/layout/topbar.tsx,src/components/layout/app-shell.tsx,src/components/layout/app-shell-context.tsx' npm run test:coverage -- tests/unit/home-page-presence-widget.test.tsx tests/unit/app-shell.test.tsx`.
  Esito: `100%` statements/branches/functions/lines sui runtime frontend toccati.

- `2026-07-29` - SERP ricerca operativa
  (`frontend/src/app/search/page.tsx`, `frontend/src/components/search/operational-search-box.tsx`)
  Per la change che aggiunge `/search?q=...`, il pulsante `Vedi tutti i risultati`
  e la navigazione Enter verso SERP quando i risultati non sono univoci, la misurazione
  affidabile e:
  `cd frontend && VITEST_COVERAGE_INCLUDE='src/app/page.tsx,src/app/search/page.tsx,src/components/search/operational-search-box.tsx,src/components/layout/topbar.tsx,src/components/layout/app-shell.tsx,src/components/layout/app-shell-context.tsx' npm run test:coverage -- tests/unit/home-page-presence-widget.test.tsx tests/unit/app-shell.test.tsx tests/unit/operational-search-page.test.tsx`.
  Esito: `100%` statements/branches/functions/lines sui runtime frontend toccati.

- `2026-08-06` - Strumentazione coverage repository-wide e batch iniziale verso il 100% globale
  (`backend/.coveragerc`, `frontend/vitest.config.ts`, test backend/frontend lib e moduli `me`/`core`/`shared`/`riordino`/`ruolo`)
  Per la change che allinea la misurazione al perimetro runtime completo e chiude i primi gap a basso costo:
  - backend: `.coveragerc` esteso a `app/**` (omit `__init__.py`, test, cache); nuovo `tests/test_coverage_small_runtime.py`;
    estensioni a `tests/test_me_router_helpers.py`, `tests/riordino/test_riordino_api.py`, `tests/test_presenze_api.py`,
    `tests/ruolo/test_tributi_api.py` (Euribor BCE, permissions, gis flags, datatable, core/security/database, riordino routes/services).
  - frontend: `vitest.config.ts` misura di default tutto `src/**` (esclusi `src/types/**`, `*.d.ts`); nuovi test lib
    (`lib-runtime-helpers`, `presentation`, `presenze-display`, `presence-actions`, `network-device-utils`, `catasto-anomalie`, `auth`, `riordino-api-client`).
  Baseline pre-change misurata il `2026-08-06`: backend `app/` ~`87.5%`, frontend `src/` ~`34.7%`, worker ~`49%`.
  Esito batch locale (file toccati): `100%` su runtime backend mirati (`euribor.py`, permissions, gis_flags, datatable_helpers, re-export catasto,
  cluster `me`/`core`/`shared`/riordino routes+services del batch); `100%` su 8 file `src/lib/**` del batch frontend.
  Residuo globale: centinaia di file sotto soglia (pagine/workspace frontend a 0%, servizi operazioni/elaborazioni/catasto/wiki, worker).
  Graphify aggiornato: `make graphify-ruolo-code`, `make graphify-riordino-code`, `make graphify-frontend`.

- `2026-08-07` - Batch servizi backend e lib frontend presenza/presenze
  (`app/services/email.py`, `app/services/google_oauth.py`, `src/lib/presence.ts`, `src/lib/catasto-gis-cache.ts`,
  `src/lib/use-presence-heartbeat.ts`, `src/lib/presenze-collaboratore-detail-helpers.ts`)
  Test aggiunti: `tests/test_email_service.py`, `tests/test_google_oauth_service.py`,
  `tests/unit/catasto-gis-cache.test.ts`, `tests/unit/presenze-collaboratore-detail-helpers.test.ts`;
  estensioni a `presence-route-meta.test.ts` e `presence-heartbeat.test.tsx`.
  Esito validato: `100%` sui file runtime elencati (backend via `coverage report --fail-under=100`,
  frontend via Vitest coverage mirata sui singoli file del batch).

- `2026-08-07` - Batch `src/lib/api.ts` (core + auth/me + presenze) e lib presenza
  (`src/lib/api.ts`, `src/lib/presence.ts`, `src/lib/presenze-collaborator-mapping.ts`; conferma `ruolo-api.ts` gia al `100%`)
  Test aggiunti:
  - `tests/unit/api-core.test.ts` (request/blob/xhr/upload, ApiError, base URL, websocket URL)
  - `tests/unit/api-auth-me.test.ts` (login, providers, presence heartbeat, `/me/*` summary)
  - `tests/unit/api-presenze.test.ts` (93 export Presenze in `api.ts`, happy-path)
  Esito validato:
  - `ruolo-api.ts`: `100%`
  - `presence.ts`: `100%`
  - `presenze-collaborator-mapping.ts`: `100%`
  - `api.ts`: da ~`5.6%` a ~`36%` linee (`416/1156`); blocchi Presenze (~L624–2351) e core HTTP al `100%` linee
  Residuo `api.ts`: export organigramma, utenze, wiki, network, elaborazioni, catasto (~300 funzioni).

- `2026-08-07` - Batch completo client `src/lib/api.ts` via generatore e suite dominio
  (`scripts/generate_api_coverage_tests.py`, `tests/unit/api-{catasto,elaborazioni,misc,network,organigramma,platform,sync,utenze,wiki}.test.ts`,
  `tests/unit/api-branches.test.ts`; estensioni `api-auth-me.test.ts`)
  Generatore Vitest happy-path per ~287 export non-Presenze (firme multilinea, XHR upload, fetch multipli, params ricchi).
  Esito validato: `403` test `api-*` passano; `api.ts` da ~`36%` a ~`86%` linee (`~1050/1222`); `98.5%` functions.
  Residuo `api.ts`: rami query condizionali, cache presenze/credential, alias re-export, blob download edge (~170 linee).

- `2026-08-07` - Batch frontend componenti/hook piccoli (<150 righe)
  (12 file test: `ui-primitives`, `source-tag`, `use-gis-selection`, `use-domain-data`, `catasto-ui-badges`,
  `network-ui-primitives`, `riordino-format`, `utenze-number-format`, `table-primitives`, `app-shell-context`,
  `recent-batches-open-context`, `organigramma-reference-data`)
  Esito: `100%` linee su 30 runtime piccoli (UI catasto/network, hook, table, context, format helper).
  Baseline frontend post-batch: ~`37%` linee globali; ~95 file piccoli ancora a `0%` (route wrappers app).
  Fix test flaky: `presenze-collaboratore-detail.test.tsx` — label mese e bounds calendario derivati da `currentMonthBounds()`/`shiftMonthBounds()`.

- `2026-08-07` - Batch backend `core/` + `shared/` + `me/` + servizi piccoli
  (`app/core/{config,database,datetime_compat,logging,security}.py`, `app/modules/shared/{datatable_helpers,http_shared}.py`,
  `app/modules/me/{router,schemas}.py`, `app/modules/catasto/services/dashboard_queries.py`,
  `app/services/{email,google_oauth}.py`)
  Test estesi: `tests/test_coverage_small_runtime.py`, `tests/test_me_router_helpers.py`;
  route `/me/*` coperte anche da `tests/test_presenze_api.py -k me`.
  Esito validato: `930/930` statement al `100%` sul perimetro batch (`core`, `shared`, `me`, `dashboard_queries`, `email`, `google_oauth`).

- `2026-08-07` - Self-service Presenze calendario mensile
  (`frontend/src/app/me/presenze-calendar.tsx`, integrazione in `frontend/src/app/me/me-page-content.tsx`)
  La vista `/me/presenze?period=current` usa ora un componente dedicato per il calendario mensile lun-dom con celle cliccabili,
  stato giornata, ore, assenze, KM, timbrature sintetiche e chip richieste/anomalie.
  Test aggiunti/estesi: `tests/unit/me-presenze-calendar.test.tsx`, `tests/unit/me-page-content.test.tsx`.
  Esito validato:
  - `cd frontend && npm run test:unit` -> `132` file / `1295` test passati.
  - `cd frontend && VITEST_COVERAGE_INCLUDE='src/app/me/presenze-calendar.tsx' npm run test:coverage -- tests/unit/me-presenze-calendar.test.tsx` -> `100%` statements / branches / functions / lines sul nuovo runtime calendario.
  - `cd frontend && npm run typecheck` resta bloccato da errori TypeScript preesistenti nei test API/helper; nessun errore su `me-page-content.tsx`, `presenze-calendar.tsx` o relativi test.
  Nota: `me-page-content.tsx` resta un contenitore monolitico multi-tab; il gate isolato sul file intero misura circa `61.53%` linee per codice preesistente fuori dalla change.
  Il nuovo runtime della feature e stato estratto proprio per mantenere il perimetro incrementale al `100%`.

- `2026-08-10` - Presenze export tecnico richiesta straordinari
  (`app/modules/presenze/services/straordinari_export_job.py`, `app/modules/presenze/services/straordinari_export_worker.py`)
  I servizi Presenze generano il file `Straordinari_YYYY_MM_Mese.xlsx` dal template `Straordinari.xlsx` e restano riusabili dai workflow amministrativi o self-service. La pagina `/presenze/export` resta export giornaliere amministrativo, non il flusso operatore.
  Test aggiunti: `backend/tests/test_presenze_straordinari_export.py`.
  Esito validato:
  - `backend/.venv/bin/python -m pytest backend/tests/test_presenze_straordinari_export.py --cov=app.modules.presenze.services.straordinari_export_job --cov=app.modules.presenze.services.straordinari_export_worker --cov-report=term-missing --cov-fail-under=100 -q` -> `20` test passati, `100%` statement sui due servizi.
  - `backend/.venv/bin/python -m pytest backend/tests/test_presenze_api.py -k 'straordinari_export' -q` -> ok, endpoint preview/job/download/delete coperti dai test API esistenti.
  - `cd frontend && npm run test:unit -- tests/unit/presenze-export-page.test.tsx` -> ok, flusso UI modale motivazioni/job coperto da rendering test.

- `2026-08-10` - Self-service richiesta straordinari operatore
  (`app/modules/me/router.py`, `app/modules/me/schemas.py`, `frontend/src/app/me/straordinari/page.tsx`, `frontend/src/lib/api.ts`)
  La nuova sezione `/me/straordinari` consente all'operatore mappato a un collaboratore Presenze di selezionare le giornate extra del mese precedente, compilare le motivazioni e scaricare il modulo `Straordinari.xlsx` o PDF. Il PDF richiede `LibreOffice`/`soffice`; in assenza del binario l'API ritorna `503` e lascia disponibile l'Excel stampabile.
  Aggiornamento regola pausa/fascia post-pausa: il servizio condiviso detrae la pausa pranzo mancante dalle giornate con entrata mattutina e uscita pomeridiana/serale senza pausa singola di almeno `30` minuti; se il residuo e `0`, la riga viene esclusa dal modulo. La flessibilita di `10` minuti riguarda solo la fascia ordinaria: quando la pausa e valida e l'extra importato supera di poco la coda post-pausa, GAIA ricondice la durata alla fascia reale dopo pausa. Analisi DB locale sul periodo `2026-07-01`..`2026-08-01`: `2800` candidate originali, `279` rettificate pausa, `21` allineate alla fascia post-pausa, `4` scartate, `2796` candidate finali.
  Esito validato:
  - `COVERAGE_FILE=/tmp/gaia-me-straordinari.coverage backend/.venv/bin/python -m pytest backend/tests/test_me_router_helpers.py backend/tests/test_presenze_api.py -k 'me' --cov=app.modules.me.router --cov=app.modules.me.schemas --cov-report=term-missing --cov-fail-under=100 -q` -> `100%` su `app.modules.me.router` e `app.modules.me.schemas`.
  - `cd frontend && npm run test:unit -- tests/unit/me-straordinari-page.test.tsx tests/unit/layout-navigation.test.ts tests/unit/api-presenze.test.ts` -> `115` test passati.
  - `cd frontend && VITEST_COVERAGE_INCLUDE='src/app/me/straordinari/page.tsx' npm run test:coverage -- tests/unit/me-straordinari-page.test.tsx` -> `100%` statements / branches / functions / lines sulla nuova pagina.

- `2026-08-10` - Ruolo tributi mobile actions e preview PDF solleciti
  (`frontend/src/app/ruolo/tributi/page.tsx`)
  La lista `/ruolo/tributi` mantiene i tre pulsanti rapidi della card sulla stessa riga in viewport mobile e riduce lo zoom della preview PDF sollecito sotto `640px`, lasciando invariato lo zoom desktop.
  Test esteso: `frontend/tests/unit/ruolo-tributi-page.test.tsx`, con regressione dedicata su viewport `406px`.
  Esito validato:
  - `cd frontend && VITEST_COVERAGE_INCLUDE=src/app/ruolo/tributi/page.tsx npm run test:coverage -- tests/unit/ruolo-tributi-page.test.tsx` -> `41` test passati, `100%` statements / branches / functions / lines su `page.tsx`.

- `2026-08-10` - Ruolo tributi ruoli speciali Capacitas audit-only
  (`app/modules/ruolo/services/capacitas_role_codes.py`, `app/modules/ruolo/tributi_repositories.py`,
  `app/modules/ruolo/routes/tributi_routes.py`, `app/modules/ruolo/schemas.py`)
  I codici speciali `2525`, `2626`, `7700`, `7890` e `99xx` sono trattati come movimenti
  amministrativi fuori ordinario: non impattano saldo/morosita/annualita, espongono stato
  operativo normalizzato e supportano filtri su annullamento.
  Esito validato:
  - `python -m pytest backend/tests/test_ruolo_capacitas_role_codes.py backend/tests/ruolo/test_tributi_api.py --cov=app.modules.ruolo.services.capacitas_role_codes --cov=app.modules.ruolo.tributi_repositories --cov=app.modules.ruolo.schemas --cov=app.modules.ruolo.routes.tributi_routes --cov-report=term-missing --cov-fail-under=100` -> `100` test passati, `100%` su tutti i file runtime in scope.

- `2026-08-10` - Ruolo tributi summary parziale con filtri effettivi
  (`app/modules/ruolo/tributi_repositories.py`, `app/modules/ruolo/schemas.py`,
  `frontend/src/app/ruolo/tributi/page.tsx`)
  La summary `/ruolo/tributi/summary` elabora a chunk i filtri effettivi `open_only`/`payment_status`
  e, quando raggiunge il limite operativo, espone `summary_partial`, `summary_scan_limit` e
  `summary_scanned_count`; la pagina mostra il KPI `Totale avvisi` come parziale.
  Esito validato:
  - `backend/.venv/bin/python -m pytest backend/tests/test_ruolo_capacitas_role_codes.py backend/tests/ruolo/test_tributi_api.py --cov=app.modules.ruolo.services.capacitas_role_codes --cov=app.modules.ruolo.tributi_repositories --cov=app.modules.ruolo.schemas --cov=app.modules.ruolo.routes.tributi_routes --cov-report=term-missing --cov-fail-under=100 -q` -> `100%` su tutti i file runtime backend in scope.
  - `cd frontend && VITEST_COVERAGE_INCLUDE=src/app/ruolo/tributi/page.tsx npm run test:coverage -- tests/unit/ruolo-tributi-page.test.tsx` -> `42` test passati, `100%` statements / branches / functions / lines su `page.tsx`.

- `2026-08-10` - GaTe pending action operatori/permessi console
  (`app/services/gate_mobile_sync.py`, `app/modules/operazioni/models/wc_operator.py`,
  `app/modules/operazioni/schemas/operators.py`, payload operatori mobile sync e label frontend ruoli console)
  GAIA consuma `propose_operator_update` dal flusso pending action Presenze, valida
  `schema_version=1`, `source=gate_admin_console` e operazioni
  `create_operator`/`update_operator`/`update_operator_domains`, quindi applica domini,
  abilitazione console, ruolo `team_manager` e pagine console sul record operatore master.
  Test aggiunti/estesi: `backend/tests/test_gate_mobile_sync.py`.
  Esito validato:
  - `COVERAGE_FILE=/tmp/gaia-gate-mobile-sync.coverage backend/.venv/bin/python -m pytest backend/tests/test_gate_mobile_sync.py --cov=app.services.gate_mobile_sync --cov-report=term-missing --cov-fail-under=100 -q` -> `28` test passati, `100%` su `app.services.gate_mobile_sync`.
  - `COVERAGE_FILE=/tmp/gaia-operazioni-schemas.coverage backend/.venv/bin/python -m pytest backend/tests/test_gate_mobile_sync.py backend/tests/test_operazioni_mobile_sync_api.py backend/tests/test_operazioni_mobile_sync_unit.py --cov=app.modules.operazioni.schemas.operators --cov-report=term-missing --cov-fail-under=100 -q` -> `100%` su `app.modules.operazioni.schemas.operators`.
  - `COVERAGE_FILE=/tmp/gaia-operazioni-models.coverage backend/.venv/bin/python -m pytest backend/tests/test_gate_mobile_sync.py --cov=app.modules.operazioni.models --cov-report=term-missing -q` -> `wc_operator.py` al `100%`; il package modelli resta al `99%` per righe legacy non toccate in `organizational.py`.
  - `backend/.venv/bin/python -m pytest backend/tests/test_operazioni_mobile_sync_api.py backend/tests/test_operazioni_mobile_sync_unit.py backend/tests/test_user_management.py backend/tests/test_admin_users_gate_mobile_summary_unit.py -q` -> ok.
  - `cd frontend && npm run test:unit -- tests/unit/gaia-users-page.test.tsx` -> ok.
  - `cd frontend && set -o pipefail; npm run typecheck 2>&1 | tail -80` -> resta bloccato da errori TypeScript preesistenti nei test API/helper, non introdotti dalla change.

- `2026-08-20` - Export giornaliere XLSM GATE con valori canonici GAIA
  (`app/services/gate_mobile_sync.py`,
  `app/modules/presenze/services/gate_mobile_payloads.py`,
  `app/modules/presenze/gate_router.py`)
  Lo snapshot mensile espone la versione export e tutti i valori canonici necessari al compilatore XLSM GATE; lo snapshot squadre collega inoltre il responsabile al proprio collaboratore Presenze quando presente.
  Esito validato:
  - `pytest tests/test_gate_mobile_sync.py --cov=app.services.gate_mobile_sync --cov=app.modules.presenze.services.gate_mobile_payloads --cov-fail-under=100 -q` -> `28` test passati, `100%` sul sync (`640/640`) e sul payload (`36/36`);
  - `pytest tests/test_presenze_api.py -q -k 'gate_presenze' --cov=app.modules.presenze.gate_router --cov-fail-under=100` -> `13` test passati, `100%` sul router (`343/343`);
  - `make complexity-ratchet BASE_REF=main` -> pass, findings vuoti; baseline globale invariata a `4328` violation e `make complexity-baseline-verify` verde.

## Eccezioni temporanee aperte

- `2026-07-06` - frontend `src/app/presenze/collaboratori/[id]/page.tsx`
  Motivo: la pagina resta monolitica; la suite `presenze-collaboratore-detail` copre helper, tab `Cartellino`, tab `Riepilogo eventi`, rettifiche e flussi admin principali, ma il gate mirato Vitest misura ancora `98.21%` statement / `81.19%` branch / `100%` functions / `98.26%` lines.
  Rientro atteso: spezzare la page in componenti/helper testabili e chiudere i rami residui su redirect embedded, azioni admin edge e fallback di dettaglio.

- `2026-07-06` - frontend `src/lib/api.ts`
  Motivo: file aggregatore API molto ampio; la suite `api-*` (403 test) copre ~`86%` linee / ~`98.5%` functions ma restano rami condizionali (query params, cache, blob) non esercitati.
  Rientro atteso: estendere `api-branches.test.ts` e test Presenze con parametri non vuoti, oppure split del client per dominio, prima del gate globale al `100%`.

- `2026-08-07` - frontend `src/app/me/me-page-content.tsx`
  Motivo: contenitore self-service monolitico con tab overview/presenze/operativita/dotazioni/anomalie, export CSV/XLSX e modali dettaglio.
  La change calendario ha spostato il runtime nuovo in `src/app/me/presenze-calendar.tsx`, coperto al `100%`, ma il file orchestratore resta sotto soglia se misurato integralmente.
  Rientro atteso: estrarre progressivamente tab Presenze/Operativita/Dotazioni/Anomalie in componenti dedicati e lasciare `me-page-content.tsx` come shell dati/navigazione minima.
