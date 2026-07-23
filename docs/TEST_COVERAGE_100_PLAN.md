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

## Eccezioni temporanee aperte

- `2026-07-06` - frontend `src/app/presenze/collaboratori/[id]/page.tsx`
  Motivo: la pagina resta monolitica; la suite `presenze-collaboratore-detail` copre helper, tab `Cartellino`, tab `Riepilogo eventi`, rettifiche e flussi admin principali, ma il gate mirato Vitest misura ancora `98.21%` statement / `81.19%` branch / `100%` functions / `98.26%` lines.
  Rientro atteso: spezzare la page in componenti/helper testabili e chiudere i rami residui su redirect embedded, azioni admin edge e fallback di dettaglio.

- `2026-07-06` - frontend `src/lib/api.ts`
  Motivo: file aggregatore API molto ampio; i test Presenze coprono le chiamate aggiunte/toccate, ma la misurazione per file resta `3.40%` statement / `1.82%` branch / `0.51%` functions / `3.60%` lines.
  Rientro atteso: separare client API per dominio o introdurre suite mirate sui gruppi di funzioni prima di rendere vincolante il gate per questo file.

- `2026-07-06` - backend `app/modules/me/router.py`
  Motivo: router aggregatore gia esistente; i test mirati coprono gli helper modificati, ma la misurazione per file resta `31%` perche include molte route non interessate da questa change.
  Rientro atteso: estrarre helper puri e aggiungere test route-level prima di applicare il gate `100%` al router completo.
