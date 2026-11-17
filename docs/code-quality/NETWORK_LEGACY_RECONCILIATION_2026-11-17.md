# Riconciliazione soggetti IP legacy Network — 2026-11-17

Esito **IMPROVED**: due Warning eliminati in
`backend/app/modules/network/router/helpers/tracking.py`.

## Modifica e invarianti

`_reconcile_legacy_ip_tracked_subject` conserva ricerca del dispositivo, query
del soggetto canonico, aggiornamento riferimenti e persistenza. La fusione di
label, note e stato attivo e isolata in `_merge_legacy_tracked_subject_metadata`.
L'helper contiene la stessa sequenza di letture e assegnazioni del blocco originale.

I metadati canonici non vuoti prevalgono; quelli legacy vengono letti nuovamente
al momento dell'assegnazione. `is_active` conserva OR con short-circuit e valore
originale anche non booleano. L'assenza di dispositivo restituisce lo stesso
soggetto senza query o scritture. L'assenza di canonico converte lo stesso
soggetto senza eliminarlo. Un canonico trovato viene aggiunto prima di eliminare
il legacy. Query, parametri, identita, errori, transazioni e API non cambiano;
la funzione non introduce commit o flush. Diciannove altri callable hanno AST
identico e tutte le venti firme preesistenti sono preservate.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Riconciliazione: cognitiva | 17 | 2 |
| Riconciliazione: ciclomatica | 11 | 3 |
| Riconciliazione: LOC | 28 | 24 |
| Riconciliazione: nesting | 2 | 1 |
| Cognitiva aggregata file | 235 | 230 |
| Ciclomatica aggregata file | 161 | 162 |
| Somma cyclomatic meno 1 | 141 | 141 |
| LOC file | 486 | 490 |
| Callable | 20 | 21 |
| Error | 6 | 6 |
| Warning | 4 | 2 |

Helper cognitive/cyclomatic/LOC/nesting10/9/8/1, sotto tutte le soglie.
Il punto ciclomatico aggiunto corrisponde al nuovo callable; le decisioni
aggregate non crescono. Il file resta sotto 500LOC. Nessuna violation trasferita.
Residuo tracking: sei Error e due Warning nella timeline ARP e nel riepilogo
attivita, entrambi invariati.

## Verifiche

Artefatti `/tmp/gaia-network-legacy-reconciliation-refactor-20261117/`.
Nuovo test `backend/tests/test_network_legacy_reconciliation.py`.

- 198test PASS prima/dopo:18helper router,50API Network,49normalizzazione,
  43matching e38nuove caratterizzazioni; XML zero skip/failure/error.
- Coverage full-file statement/branch100%:260/260→262/262statement,
  108/108branch invariati; zero esclusioni, missing o branch parziali.
- Differenziale deterministico su12000scenari: identita e changed, SQL,
  risultati/eccezioni, trace ordinato letture/scritture/persistenza e stato
  parziale degli oggetti equivalenti. Include valori non booleani, letture
  successive diverse e failure iniettate alle singole operazioni.
- Quattro mutanti in memoria respinti dai nuovi test: sovrascrittura label
  canonica, OR→AND, delete prima di add e caching della prima lettura label.
  Nessun mutante applicato al runtime su disco; nessun test esistente modificato.
- Ratchet mirato origin/main PASS prima/dopo contro baseline autorevole del
  merge-base `686e529ee011487e0764b9f91d023be063dbdf55`.
- Ratchet globale exit2 per la stessa ambiguita preesistente Tributi:
  `useEffect[0]<callback>`, dieci candidati. Nessun PASS globale dichiarato.
- Report completi1960file: Error1905 invariati, Warning2958→2956,
  callable22615→22616. Solo tracking.py varia metriche; nessun errore di parsing.
- Ruff runtime/test, format nuovo test, lint-backend234file e diff-check PASS.
- Graphify Network aggiornato con Make:464nodi/1170archi. Aggiornamento platform
  docs e completamento semantico registrati nel checkpoint della slice.

Comandi principali dalla root, con file coverage distinti prima/dopo:

```bash
COVERAGE_FILE=/tmp/gaia-network-legacy-reconciliation-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-legacy-reconciliation-refactor-20261117/test.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_tracked_normalization.py backend/tests/test_network_tracked_matching.py backend/tests/test_network_legacy_reconciliation.py
COVERAGE_FILE=/tmp/gaia-network-legacy-reconciliation-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/tracking.py' -o /tmp/gaia-network-legacy-reconciliation-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-legacy-reconciliation-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-legacy-reconciliation-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/tracking.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-platform-docs
```

## Stato del checkout

HEAD `ce9968b65a1b8a6fe94d061f265df2623e9a4555`. Baseline, soglie, scope ed
eccezioni intatti; nessuna sincronizzazione o baseline-verify nel checkout
concorrente. Report condivisi preservati. Dalla ripresa tredici slice:
-13Error/-17Warning/-80cognitiva aggregata; nessuna percentuale storica di
completamento dedotta. Nessun commit, push, merge o deploy. Obiettivo generale
ancora attivo; prossima azione: selezionare un hotspot revisionabile dal report
corrente, con ownership e coverage verificati prima del runtime.
