# Punteggio ricerca operativa — 2026-11-17

`_score_value` calcola il punteggio di un singolo valore con guardie precoci;
`_score` mantiene normalizzazione iniziale della query, consumo completo dei
valori e aggregazione del massimo. Esito `IMPROVED`: separazione di due
responsabilita concrete e riduzione cognitiva aggregata senza trasferire debito.

## Invarianti

- Punteggi e precedenza: exact 100, prefix 86, substring 68, tutti i token 64,
  fallback complessivo 40. Valori vuoti/None non contribuiscono al massimo.
- Query lower prima di acquisire l'iteratore; valori strip/lower durante il
  consumo. Query vuote, whitespace, Unicode e token ripetuti conservati.
- Tutti i valori vengono consumati anche dopo score 100. Errori di iterazione,
  normalizzazione e confronto si propagano nello stesso punto e ordine.
- Il massimo e sempre un intero non negativo: aggiungere il candidato zero
  per valori senza match non cambia il valore accumulato. Nessun early return.
- Le altre 11 funzioni, import e stato modulo hanno AST invariato. Query SQL,
  autenticazione, autorizzazioni, ranking, payload, link e DB non cambiano.

Ownership libera confermata dal peer Communications. HEAD `743b21c1`, branch
`chore/split-changes-20261109`, merge-base locale origin/main `686e529e`.
WIP precedenti Network, Tributi e altri file preservati; nessun commit o merge.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| `_score` cognitive / cyclomatic | 28 / 12 | 3 / 4 |
| `_score` LOC / nesting / parametri | 16 / 5 / 2 | 6 / 1 / 2 |
| `_score_value` cognitive / cyclomatic | — | 9 / 9 |
| `_score_value` LOC / nesting / parametri | — | 13 / 1 / 2 |
| Cognitiva file, somma / massimo | 59 / 28 | 43 / 11 |
| Ciclomatica file, somma / massimo | 49 / 12 | 50 / 9 |
| Decisioni aggregate sum(cyclomatic-1) | 37 | 37 |
| Callable | 12 | 13 |
| LOC file | 376 | 383 |
| Error / Warning file e callable | 4 / 1 | 2 / 0 |

LOC include quattro righe aggiuntive per il wrapping import richiesto da Ruff.
Il file resta sotto soglia; nessuna nuova violation. I due Error residui sono
LOC di `_search_utenze` (101) e `_search_catasto` (168), funzioni invariate.
Il lieve aumento della somma ciclomatica e il costo base del nuovo callable;
le decisioni restano identiche, la cognitiva aggregata diminuisce di 16.

## Verifiche

Artefatti `/tmp/gaia-search-score-refactor-20261117/`.

- 62 test prima/dopo, 55 nuovi e sette API originali, zero failure/error/skip.
  Coverage full-file statement/branch 100%: prima 104/104 e 38/38; dopo
  107/107 e 38/38. Nessuna esclusione, missing line o partial branch.
- 10.000 confronti differenziali del codice originale e corrente, inclusi
  trace delle operazioni stringa, iteratori ed errori; nessuna divergenza.
- Tre mutanti eseguiti soltanto in memoria: exact abbassato respinto da 389
  casi, any-token da 1.127, early return dopo exact da 659. Nessun mutante
  applicato al checkout. Prova AST di import/stato/altre 11 funzioni PASS.
- Ruff runtime e nuovo test, format-check del test, lint-backend (269 file)
  e diff-check PASS. Corretto soltanto I001 preesistente degli import runtime.
- Ratchet scoped origin/main prima/dopo PASS. Globale exit 2 esclusivamente
  per ambiguous_identity preesistente in Tributi useEffect[0]<callback>, dieci
  candidati. Nessun sync/verify baseline o PASS globale dichiarato.
- Report completi isolati: 1.963 file, callable 22.648→22.649, Error
  1.890→1.888, Warning 2.940→2.939; zero parse/exception error. Solo il servizio
  Search cambia nelle metriche. Hash baseline, eccezioni, matcher, report
  condivisi e altri WIP verificati invariati.
- Graphify backend Make: AST 1.073/1.073, 11.640 nodi e 28.908 archi.
  HTML omesso automaticamente dal limite di 5.000 nodi, grafo JSON aggiornato.
  Esito Graphify platform docs nel checkpoint finale degli artefatti.

```bash
COVERAGE_FILE=/tmp/gaia-search-score-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-search-score-refactor-20261117/test-after.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_operational_search_api.py backend/tests/test_operational_search_scoring.py --junitxml=/tmp/gaia-search-score-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-search-score-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/modules/search/service.py' -o /tmp/gaia-search-score-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-search-score-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-search-score-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/search/service.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-backend
make graphify-platform-docs
```

Singola slice conclusa; il programma generale resta aperto. Prossima azione:
review del delta e selezione di un altro hotspot alla continuazione.
