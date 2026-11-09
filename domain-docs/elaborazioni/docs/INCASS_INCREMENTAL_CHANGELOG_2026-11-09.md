# Changelog e verifica: inCASS incrementale

Data: 2026-11-09. Nessun push, rilascio CED, accesso al portale o attivazione.
Modalità predefinita off; autosync e worker settimanali invariati.

## Implementato

- Worker giornaliero autonomo Europe/Rome, slot e revisione, retry limitati,
  stato partial/failed/invalid/validated e lease PostgreSQL tra istanze.
- Originali immutabili per hash sul volume e su Drive, catalogo atteso,
  schema/righe/firme/provenienza; recupero senza riesportare file acquisiti.
- Parsing rigoroso e confronto globale per Avviso; lista distinta dall'identità;
  classificazione new/changed/unchanged/missing/ambiguous, snapshot invalidi
  isolati senza promozione. Nessuna cancellazione automatica.
- Baseline senza scraping massivo, bootstrap su allowlist, outbox per avviso
  con ricevuta e scrittura tributaria nella stessa transazione.
- Shadow senza dispatch; active esplicito e subordinato a schema/copertura
  attestati, giorni shadow, campionamento e audit periodico configurati.
- Applicazione sintetica tramite parser e upsert esistenti; recovery mirato
  dettaglio/partitario, fusione payload pesanti, link/documenti preservati;
  riconciliazione canonica Ruolo. Nessun download PDF dal nuovo dispatch.
- Confronto read-only con raw row e firme dei payload pesanti registrati dal
  sync ordinario; metriche/report nel journal, log privi di payload personali.

## File e motivazione

Tutti i file elencati sono nuovi, salvo l'import in `db/base.py` e le voci
aggiunte all'indice `docs/DOCS_STRUCTURE.md`.
Non sono incluse le modifiche concorrenti del checkout.

| File (dalla root) | Responsabilità |
| --- | --- |
| `backend/app/modules/elaborazioni/capacitas/incremental/__init__.py` | package indipendente |
| `backend/app/modules/elaborazioni/capacitas/incremental/config.py` | flag e ammissione configurazione, slot giornaliero |
| `backend/app/modules/elaborazioni/capacitas/incremental/models.py` | journal e outbox PostgreSQL |
| `backend/app/modules/elaborazioni/capacitas/incremental/normalize.py` | normalizzazione XLSX e hash semantici |
| `backend/app/modules/elaborazioni/capacitas/incremental/diff.py` | validazione collezione, diff, campioni e bootstrap |
| `backend/app/modules/elaborazioni/capacitas/incremental/journal.py` | creazione ciclo e promozione atomica |
| `backend/app/modules/elaborazioni/capacitas/incremental/storage.py` | originali durevoli e lease |
| `backend/app/modules/elaborazioni/capacitas/incremental/cycle.py` | raccolta, archivio, checkpoint e recovery |
| `backend/app/modules/elaborazioni/capacitas/incremental/dispatch.py` | ownership, drift, applicazione e dead-letter |
| `backend/app/modules/elaborazioni/capacitas/incremental/observability.py` | confronto shadow e conteggi outbox |
| `backend/app/modules/elaborazioni/capacitas/incremental/runner.py` | entry point e heartbeat, polling e finestra |
| `backend/app/db/base.py` | registrazione dei tre modelli per Alembic |
| `backend/alembic/versions/20261109_1000_incass_incremental.py` | migration additiva e reversibile, ramo indipendente |
| `backend/tests/incass_incremental/__init__.py` | package test |
| `backend/tests/incass_incremental/conftest.py` | fixture sintetiche, DB isolati e workbook |
| `backend/tests/incass_incremental/test_normalize_diff.py` | semantica, anomalie, chiavi, bootstrap, DST |
| `backend/tests/incass_incremental/test_cycle_journal.py` | ciclo shadow, crash, Drive, falso server HTTP e benchmark |
| `backend/tests/incass_incremental/test_dispatch.py` | upsert canonico, conservazione payload, identità, recovery |
| `backend/tests/incass_incremental/test_runner_storage.py` | flag, scheduler, lease reale, CLI, migration e rollback |
| `compose.incass-incremental.yml` | servizio opzionale, profilo separato e off |
| `docs/DOCS_STRUCTURE.md` | indice dei nuovi percorsi del dominio |
| `domain-docs/elaborazioni/docs/INCASS_INCREMENTAL_AUDIT_2026-11-09.md` | audit scritto prima del codice |
| `domain-docs/elaborazioni/docs/INCASS_INCREMENTAL_RUNBOOK.md` | configurazione, rollout, recovery e rollback |
| questo file | changelog, verifiche, limiti e perimetro |

Testo documentale precedente: **assente** per i tre nuovi documenti. Il nuovo
testo completo è nei file versionati sopra, non sostituisce documenti esistenti.
Nell'indice `docs/DOCS_STRUCTURE.md` le nuove voci erano assenti. Aggiunta
integrale, nella sezione Elaborazioni:

```text
- `domain-docs/elaborazioni/docs/INCASS_INCREMENTAL_AUDIT_2026-11-09.md`: audit della pipeline giornaliera inCASS.
- `domain-docs/elaborazioni/docs/INCASS_INCREMENTAL_RUNBOOK.md`: configurazione, shadow/active, recovery e rollback.
- `domain-docs/elaborazioni/docs/INCASS_INCREMENTAL_CHANGELOG_2026-11-09.md`: perimetro, test e limiti live.
- `backend/app/modules/elaborazioni/capacitas/incremental/`: pipeline autonoma, avviabile come modulo Python `incremental.runner`.
- `backend/tests/incass_incremental/`: fixture sintetiche e integrazioni locali della pipeline.
- `compose.incass-incremental.yml`: servizio opzionale con profilo separato, modalità predefinita off.
```

L'unica aggiunta testuale a codice condiviso, prima assente, è integralmente:

```python
from app.modules.elaborazioni.capacitas.incremental.models import (
    IncrementalChange,
    IncrementalCycle,
    IncrementalHead,
)
```

## Verifiche effettive

Suite nuova: **108 passed**, coverage statement/branch **100%** su tutti gli
11 file runtime nuovi e sull'intero `app/db/base.py`: conteggi nell'evidenza coverage,
zero missing/partial branch. Include PostgreSQL temporaneo locale isolato,
senza connessione al DB applicativo o al CED.

```bash
GAIA_TEST_POSTGRES_URL='<PostgreSQL temporaneo autorizzato>' \
COVERAGE_FILE=/tmp/gaia-incass.coverage backend/.venv/bin/python -m pytest \
  backend/tests/incass_incremental \
  --cov=app.modules.elaborazioni.capacitas.incremental --cov=app.db.base \
  --cov-branch --cov-report=term-missing --cov-fail-under=100
```

Verificati: invarianti semantiche, cambio ordine/header, date/decimali/zeri
espliciti, file errati/formule/errori/schema drift, vuoti, conteggi incoerenti,
duplicati anche cross-year, codici speciali, CF/PIVA condiviso, cambi lista e
pagamento, bootstrap, crash prima/dopo upload e prima del commit diff,
idempotenza della ricevuta, errore partitario e dead-letter, rollback DB,
flag off/shadow/active, finestra operativa, lease concorrenti e migration
upgrade/downgrade su SQLite e PostgreSQL. I payload/documenti pesanti vengono
verificati attraverso il vero upsert e la vera riconciliazione canonica.
Una verifica aggiunta in review prova anche il rinvio senza retry debt quando
un job legacy parte dopo l'ammissione iniziale e prima dell'upsert attivo.

Regressioni: **234 test passed**, con il comando seguente (warning preesistenti
runpy e JWT nelle fixture; nessuna failure):

```bash
PYTHONPATH=backend:modules/elaborazioni/worker backend/.venv/bin/python -m pytest \
  backend/tests/test_capacitas_ruoli_export_service.py \
  backend/tests/test_capacitas_ruoli_export_retry_state.py \
  backend/tests/test_incass_exports.py backend/tests/test_incass_autosync_scheduler.py \
  backend/tests/test_incass_parsers.py backend/tests/test_materialize_ruolo_from_incass.py \
  backend/tests/test_capacitas_full_recovery.py backend/tests/ruolo/test_incass_read_model.py \
  backend/tests/ruolo/test_incass_notice_numbering.py \
  backend/tests/ruolo/test_tributi_incass_notice_match.py \
  modules/elaborazioni/worker/tests/test_ruoli_export_runner.py
```

Un primo tentativo congiunto senza PYTHONPATH worker è fallito in collection
(`ModuleNotFoundError: ruoli_export_runner`); risolto configurando il percorso,
senza cambiare test o codice legacy. Nei test nuovi iniziali il fixture schema
Catasto era incompleto; corretto aggiungendo il Comune sintetico, mantenendo
il vero materializzatore. Questi tentativi non sono stati contati come PASS.

Ruff check e format-check del perimetro nuovo: PASS. Ruff check di db/base.py:
PASS. Compose `config --quiet`: PASS. `git diff --check` del perimetro: PASS.

`make lint-backend QUALITY_PYTHON=backend/.venv/bin/python`: FAIL globale su
file Presenze/SISTER fuori da questa change, nel checkout concorrente.
Non sono stati modificati o esclusi per far passare il gate. Non è dichiarata
una riproduzione di queste failure su HEAD pulito.

Metriche prima: i runtime esistenti esportazione/stato/runner, poi lasciati
invariati, erano 3 file / 36 callable / zero violation. I runtime nuovi erano
assenti. Metriche finali del perimetro incrementale più db/base.py: 12 file,
55 callable, **zero error-level**, 31 warning. Non è un refactoring hotspot:
nessuna dichiarazione di riduzione o spostamento del debito legacy.

Ratchet autorevole eseguito contro `origin/main` e la baseline del merge-base
`686e529e`: il report globale contiene 44 finding nel checkout concorrente,
**zero** sui file runtime di questa change. Il gate globale resta rosso; non
sono state cambiate baseline, soglie o esclusioni. Baseline synchronization e
baseline-verify non dichiarati. Un primo report parziale aveva un falso
matching cross-file sul nome `cell_value`, perché escludeva dal report la
sorgente legacy ancora presente: il controllo globale completo risolve tale
ambiguità e resta il riferimento autorevole.

Evidenze temporanee: `/tmp/gaia-incass-complete-tests.log`,
`/tmp/gaia-incass-coverage-complete.json`,
`/tmp/gaia-incass-regressions-fixed.log`,
`/tmp/gaia-incass-ratchet-final.log`, `/tmp/gaia-incass-metrics-complete.json`,
`/tmp/gaia-incass-lint-backend.log`. Questi percorsi non sostituiscono i test
versionati e non sono artefatti da committare.

Graphify aggiornato tramite `make graphify-backend` e
`make graphify-elaborazioni-docs`. AST codice aggiornato senza chiamate LLM;
grafo docs: `chunk 1/1 done`, nessun warning di chunk semantico fallito,
8.142 token input / 812 output, costo stimato dal tool $0,0046 nella prima
estrazione dei tre documenti nuovi. Gli artefatti `graphify-out/` restano
ignorati e non sono inclusi nei commit.

## Risultati quantitativi e limiti

Fixture HTTP controllata: 1.000 avvisi, due snapshot, 6 richieste export
effettivamente intercettate (catalogo+POST+GET per giorno). Secondo snapshot:
2 changed, 998 unchanged, 2 azioni summary e zero recuperi pesanti pianificati.
Il confronto con un recupero completo ipotetico evita 1.996 GET/POST pesanti;
non è una misura di risparmio sul portale o sull'autosync light corrente.
Il test separato del dispatch prova zero chiamate pesanti su variazione del
solo pagamento con partitario presente.

Non implementato/volutamente fuori rollout iniziale:

- sostituzione o disattivazione dell'autosync; nessun passaggio produzione active;
- download PDF automatici e nuova elaborazione quotidiana Minuta/Bollettini;
- prenotazione globale delle sessioni dei worker legacy non cooperanti;
- allarmi via email/chat e dashboard dedicata: report, log e heartbeat sono
  disponibili, l'instradamento al monitoraggio operativo va configurato;
- nuova baseline automatica per cambi legittimi di schema/catalogo e retention
  distruttiva del journal/originali;
- attestazione automatica di falsi negativi/positivi critici: serve campione
  live adjudicato, comprese variazioni interne al partitario non esposte.

Bloccato da evidenze live assenti: intestazioni reali dei due export inCASS,
tipi/precisione Excel, completezza indipendente dal file, costo corrente,
omissioni critiche, guadagno HTTP reale e dimensionamento campioni/audit.
Nessuno XLSX inCASS idoneo trovato nei percorsi locali ispezionati; fixture e
server fittizio non provano il comportamento del portale. Seguire il runbook
per shadow osservato, ammissione canary e rollback, mantenendo il processo
operativo attuale.
