# Domande irrigue — chiusura del blocco e ammissione

## Perimetro autorizzato

Correzione del solo blocco di coverage e consolidamento dei nove file Elaborazioni
rimasti nelle Changes. Attività di manutenzione separata: la campagna GAIA resta
**PAUSED / INCOMPLETE**. Nessuna nuova wave, baseline inflation, push, deploy,
backfill o chiamata al portale reale.

Checkout `/home/cbo/CursorProjects/GAIA`, branch `main`; HEAD e merge-base con
`main` prima delle verifiche e dei commit:
`b047abdf89e0c174493dd41b8c56ee44d4794389`.
I nove originali sono stati confrontati con l'archivio del consolidamento.
La precedente esclusione documentata in
`CONCURRENT_CONSOLIDATION_2026-10-12.md` resta una ricevuta storica: questa è la
nuova ammissione, non una riscrittura delle prove precedenti.

## Correzione

`run_incass_job_by_id` manteneva un'uscita per esaurimento del `for` che non poteva
essere raggiunta con il `range` reale. Il precedente 100% era ottenuto sostituendo
quella primitiva Python con una lista vuota. La verifica indipendente aveva
misurato 99,676% nel runtime condiviso, con il solo ramo `52 -> exit` mancante.

Il contatore dei tentativi è ora esplicito nel ciclo: gli stessi percorsi
`return` terminano il worker e la stessa guardia consente il retry solo prima
dell'ultimo tentativo. Rimangono tre tentativi massimi e pause 2/5 secondi.
Nessun helper artificiale, soglia o esclusione viene introdotto.

Il test del `range` vuoto è sostituito dal test legittimo dello stato resume
non-dict. Un nuovo controtest di tre timeout consecutivi verifica esattamente
rollback, pause, chiusura sessione/DB, assenza del mark-success e commit finale
della failure. Ordine dei side effect, transazioni e cleanup restano invariati.

## File ammessi e commit

| Responsabilità | File |
| --- | --- |
| Cursore full/recent e riconciliazione | `backend/app/modules/elaborazioni/domande_irrigue_autosync_scheduler.py` |
| Persistenza limiti nel worker parallelo | `backend/app/modules/elaborazioni/domande_irrigue_parallel.py` |
| Filtro anni e validazione fail-closed | `backend/app/modules/elaborazioni/domande_irrigue_refresh.py` |
| Worker seriale e retry inCASS condiviso | `backend/app/services/elaborazioni_capacitas_runtime.py` |
| Regressioni scheduler | `backend/tests/test_domande_irrigue_autosync_scheduler.py` |
| Limiti, rollover, errori e dettagli | `backend/tests/test_domande_irrigue_refresh.py` |
| Contratto worker e lifecycle dei retry | `backend/tests/test_capacitas_runtime_refresh_contract.py` |
| Profilo conservativo preparato | `config/capacitas/compose.conservative.yml` |
| Documentazione dominio, con addendum corrente | `domain-docs/elaborazioni/docs/CAPACITAS_POLITE_SYNC_2026-10-07.md` |

Tutti classificati **AMMESSO**. Due commit coerenti: runtime/test con questa
ricevuta, poi profilo conservativo/documentazione. Gli hash effettivi sono nella
ricevuta esterna `FINAL_RECEIPT.json` e nel log Git. Staging per elenco esplicito,
confronto dei blob con gli snapshot verificati, nessun `git add -A` o `git add .`.

## Test e coverage

**147 test PASS, zero skip, failure o error; nessuna deselezione**.
Le suite mirate coprono scheduler, refresh, runtime, finestre, prefetch parallelo,
platform scheduler e persist/recovery/anomalie Catasto. Si aggiungono sei
controtest esterni, conservati nell'archivio: parser e metodi reali dello scraper
con il solo trasporto HTTP sintetico, e stato resume non-dict.

| Runtime completo | Statement | Branch | Coverage |
| --- | ---: | ---: | ---: |
| `domande_irrigue_autosync_scheduler.py` | 148/148 | 42/42 | 100% |
| `domande_irrigue_parallel.py` | 96/96 | 18/18 | 100% |
| `domande_irrigue_refresh.py` | 44/44 | 16/16 | 100% |
| `elaborazioni_capacitas_runtime.py` | 253/253 | 56/56 | 100% |
| Totale | 541/541 | 132/132 | 100% |

Zero righe escluse nei quattro file. Gli input runtime e test non sono cambiati
dopo l'esecuzione. Ambiente sintetico con dotenv disabilitato e SQLite privati;
nessuna credenziale live. Non sono certificate concorrenza/row lock PostgreSQL
o lo stato di produzione. Le suite complete backend/frontend/worker, build ed
E2E non sono state ripetute: niente modifiche ai relativi input frontend/worker.
I 449 skip backend della campagna e i 392 skip Ruolo dell'altro consolidamento
restano non verificati, non diventano PASS per questa ricevuta.

## Gate e metriche

- `BASE_REF=main make lint-backend QUALITY_PYTHON=backend/.venv/bin/python`:
  PASS; compileall e Ruff su sette file Python toccati, format dei tre nuovi.
- `make complexity-ratchet BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python`:
  PASS, zero finding; confronto prima dei commit contro il merge-base sopra.
- `git diff --check` e check staged: PASS.
- Baseline, matcher, soglie, eccezioni, ignore e coverage policy invariati.
  Nessuna esecuzione di `complexity-baseline` o `baseline-repair`.
- Il FAIL/ambiguità integrale storico resta distinto dal gate della change;
  non è stato assorbito o dichiarato risolto.

La correzione locale non rivendica una riduzione della complessità:

| Metrica inCASS | Prima della correzione | Dopo | Su HEAD prima della change |
| --- | ---: | ---: | ---: |
| Cognitive | 57 | 57 | 57 |
| Cyclomatic | 20 | 20 | 20 |
| Nesting | 5 | 5 | 5 |
| Callable LOC | 49 | 51 | 51 |
| Params | 1 | 1 | 1 |

Le due LOC del contatore riportano il callable a 51, già presenti nel riferimento
Git autorevole; la warning LOC non è una nuova regressione della change. File LOC
effettive del runtime: 272 su HEAD, 287 nel candidato, 289 dopo la correzione.
Rimangono sotto la soglia file; debito legacy cognitive/nesting non risolto.
Per scheduler e worker irrigue restano le misure già verificate: principale
9/9 → 6/7 cognitive/cyclomatic, riconciliazione 18/13 → 16/12, worker parallelo
10/8 → 12/9 sotto soglia. Nessuna riduzione globale della campagna viene dichiarata.

## Profilo e Graphify

Il YAML del profilo è invariato rispetto alla verifica indipendente: tre servizi,
intervallo 5 secondi, cooldown 300/3600, parallelismo worker 1. Settings e mount
sono stati validati staticamente nella verifica precedente; non è stato applicato.
Un rilascio futuro deve rispettare pin, hotfix e mount condiviso esistenti.

`make graphify-backend GRAPHIFY_CODE_FLAGS=--force`: PASS, patch force-pruning
idempotente, AST di 923 file, 10206 nodi, 25835 archi, 545 comunità. HTML saltato
dal tool perché sopra il limite di 5000 nodi, senza alzare il limite.
`make graphify-elaborazioni-docs GRAPHIFY_DOC_MODEL=gpt-reserve`: PASS, 37 cache
hit e dieci file riestratti, `chunk 1/1 done`, nessun warning di chunk falliti;
729 nodi, 1155 archi, 49 comunità. Token 10396 input / 3594 output, costo stimato
dal tool $0.0099. Patch OpenAI base URL verificata. Target dedicati, nessuna
estrazione dalla root; grafi non committati e non usati come prova di coverage.

## Evidenze e handoff

Archivio privato e durevole:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-irrigue-admission-20261012`.
`ADMISSION_MANIFEST.json`, SHA256
`048cc107276955993f065aeeede21db8c999f33401fe89efb1ea9b59bf4561e8`.

Contiene input e custody dei nove percorsi, originali precedenti e snapshot
ammessi, log/argv/exit, JUnit, coverage JSON/native, metriche e checksum della
policy immutata, copie dei grafi e dei controtest HTTP esterni. La ricevuta finale
registra i due commit, il checksum del report e lo stato del working tree.
Cache, DB, dipendenze, build e graphify-out non sono versionati. Freeze storici
preservati; solo un addendum datato nel documento dominio mutabile.

Stop: nessuna altra slice, nessun push o deploy. Il consolidamento di questi file
non completa e non riattiva il goal globale della campagna.
