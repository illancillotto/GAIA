# Raggruppamento avvisi per pagatore — 2026-11-17

Esito locale **IMPROVED**: cognitiva aggregata 52→50 e due Warning rimossi.
Il ratchet dell'intero checkout resta distinto dalla certificazione della slice.

## Perimetro e invarianti

Runtime: `backend/app/modules/ruolo/services/payer_assignments.py`.
Test nuovo: `backend/tests/ruolo/test_payer_candidate_grouping.py`.
Estratto soltanto il raggruppamento per `subject_id` del pagatore in
`_avvisi_by_payer`; selezione dei candidati propri e trasformazione finale
mantengono sequenza e comportamento originali. Nessun cambiamento a query,
schema, transazioni, API, firme pubbliche o assegnazioni.

I test verificano ordine dei candidati e dei gruppi, ordine e molteplicita
degli avvisi, prima assegnazione come motivo del gruppo, indirizzi e importi,
separazione tra intestatari con lo stesso pagatore, riuso del candidato
invariato, copie degli avvisi spostati e assenza di mutazioni degli input.
Le liste vuote conservano il comportamento preesistente.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Cognitiva totale file | 52 | 50 |
| Cognitiva massima file | 18 | 13 |
| Ciclomatica totale file | 53 | 54 |
| Decisioni, somma di cyclomatic meno 1 | 41 | 41 |
| LOC effettive file | 195 | 201 |
| Callable | 12 | 13 |
| Warning | 4 | 2 |
| Error | 0 | 0 |
| `reassign_candidates` cognitiva | 18 | 13 |
| `reassign_candidates` ciclomatica | 11 | 9 |
| `reassign_candidates` LOC / nesting | 18 / 3 | 15 / 2 |

Il nuovo helper vale cognitive/cyclomatic/LOC/nesting 3/3/9/2, sotto soglia.
L'incremento della somma ciclomatica e il contributo base del nuovo callable;
le decisioni fisiche non diminuiscono. L'obiettivo migliorato e la cognitiva,
con riduzione delle violation e senza trasferimento di debito. Restano i due
Warning preesistenti di `assign`: cyclomatic 11 e parametri 6.

## Verifiche

Artefatti in `/tmp/gaia-payer-refactor-20261117/`.

- 9 test originali PASS con coverage full-file 100% prima della slice.
- 12 test PASS prima e dopo: test originali piu tre caratterizzazioni;
  il caso esaustivo percorre 341 sequenze, anche con duplicati.
- Coverage statement/branch prima 105/105 e 36/36; dopo 108/108 e 36/36.
  Zero missing, branch parziali o nuove esclusioni. Dopo: fail-under 100.
- Confronto tra sorgente originale congelato e corrente: 5461 casi,
  zero differenze di valori, identita degli oggetti o chiamate a `active_payers`.
- Due controtest in memoria: ordinamento arbitrario dei gruppi e rimozione
  duplicati respinti dal test esaustivo; sorgente runtime non alterato.
- Ruff runtime/test e format-check del test nuovo PASS.
- `make lint-backend QUALITY_PYTHON=backend/.venv/bin/python`: PASS,
  213 file nel ratchet di stile. `git diff --check`: PASS.
- `make graphify-ruolo-code`: PASS, 151 file AST, 1745 nodi e 4288 archi.

Comandi principali (dalla root, output e coverage salvati nella directory sopra):

```bash
python3 tools/code_quality/complexity.py report backend/app/modules/ruolo/services/payer_assignments.py --json /tmp/gaia-payer-refactor-20261117/after.json --markdown /tmp/gaia-payer-refactor-20261117/after.md
COVERAGE_FILE=/tmp/gaia-payer-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-payer-refactor-20261117/test.db RUOLO_REMINDER_STORAGE_PATH=/tmp/gaia-payer-refactor-20261117/reminders backend/.venv/bin/python -m pytest -q backend/tests/ruolo/test_payer_assignments.py backend/tests/ruolo/test_payer_candidate_grouping.py --cov=app.modules.ruolo.services.payer_assignments --cov-branch --cov-report=term-missing --cov-report=json:/tmp/gaia-payer-refactor-20261117/coverage-after.json --cov-fail-under=100
python3 tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/ruolo/services/payer_assignments.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-ruolo-code
```

## Baseline e limiti

Branch `chore/split-changes-20261109`; SHA iniziale `f6386073`, poi
`ac288c6b` per commit Communications concorrente. Sorgente del servizio
originale congelato con hash SHA256
`8cd575e8d2a4925bb98830fd15d213926aac8d39b5cfcf9c684d78f1a98b0aae`.
Merge-base con `origin/main`: `686e529ee011487e0764b9f91d023be063dbdf55`.

Ratchet del servizio PASS prima/dopo, zero finding. Il ratchet globale prima
e dopo la slice esce 2 con lo stesso finding: `ambiguous_identity` su `useEffect[0]<callback>` nel file
frontend concorrente `frontend/src/app/ruolo/tributi/page.tsx` (10 candidati).
Nessuna modifica al matcher per aggirare il problema. Baseline, soglie, scope
ed eccezioni invariate; baseline non sincronizzata, baseline-verify non eseguito.

Le scansioni complete sullo stesso perimetro contano 1960 file, callable
22586→22587, Error 1918→1918 e Warning 2973→2971. Il solo path con metriche
variate e il servizio della slice. Il perimetro include i test worker: non confrontare questi totali
con un audit storico diverso per attribuire percentuali di miglioramento.
I report condivisi gia modificati nel checkout erano parziali e sono preservati.
Le suite applicative complete non sono state rieseguite per questa slice.

Singolo hotspot concluso; nessun commit, push, merge o deploy della slice.
