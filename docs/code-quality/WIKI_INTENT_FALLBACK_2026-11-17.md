# Fallback intenti Wiki — 2026-11-17

`classify_intent` elimina due controlli ridondanti senza cambiare pattern,
punteggi o priorita. Esito `IMPROVED`: cognitiva 15→11, due Warning diventano
uno, nessuna estrazione o aumento delle metriche PRIMARY.

## Prova e invarianti

I punteggi sono somme di unita, con bonus identificatore positivo: sono
interi non negativi. Pertanto live_score>docs_score implica live_score>0.
L'ultimo if docs_score>0 restituiva lo stesso `docs_only` del fallback.
Rimossi il secondo confronto live e l'ultimo ramo docs.

Overview resta prioritaria, poi logic, poi live strettamente maggiore di docs,
infine docs. Parita, duplicati fra pattern, bonus identificatori, normalizzazione,
ordine delle regex e propagazione errori restano identici. Il prefisso della
funzione, costanti, pattern e import hanno AST invariato; i return residui sono
identici. Nessuna modifica a routing, strumenti, autorizzazioni, payload o DB.

Il commento RUF001 sul solo apostrofo tipografico documenta il suo uso
intenzionale nel pattern italiano, conservandone esattamente il valore.
Non e una modifica al matching, alla coverage o alle esclusioni di complessita.

## Metriche

| Metrica target/file | Prima | Dopo |
| --- | ---: | ---: |
| Cognitiva | 15 | 11 |
| Ciclomatica | 13 | 10 |
| Decisioni cyclomatic-1 | 12 | 9 |
| LOC target / file | 16 / 130 | 14 / 128 |
| Nesting / parametri / callable | 1 / 1 / 1 | 1 / 1 / 1 |
| Error / Warning | 0 / 2 | 0 / 1 |

Resta il Warning cyclomatic 10, soglia inclusiva. Nessun nuovo callable o
debito trasferito. HEAD `743b21c1`, branch `chore/split-changes-20261109`,
merge-base origin/main `686e529e`; WIP precedenti preservati.

## Verifiche

- 101 test PASS prima/dopo, 23 nuovi; router, orchestrator e quattro casi
  API chat selezionati inclusi. Test esistenti intatti, zero failure/error/skip.
- Coverage full-file statement/branch 100%: prima 25/25 e 10/10, dopo
  23/23 e 8/8. Nessuna esclusione, missing line o partial branch.
- 10.000 differenziali equivalenti per risultati, trace regex/normalizzazioni
  ed errori iniettati. Prova AST del prefisso e dei return/pattern/import PASS.
- Tre mutanti solo in memoria respinti: live vincitore della parita 1.423
  divergenze, priorita logic rimossa 2.157, fallback live 1.897.
- Ruff/lint iniziali FAIL per RUF001 preesistente sul carattere intenzionale;
  log conservati. Dopo motivazione puntuale: Ruff runtime/test, format-check
  del nuovo test, lint-backend (272 file) e diff-check PASS.
- Ratchet scoped origin/main prima/dopo PASS. Globale exit 2 soltanto
  ambiguous_identity preesistente in Tributi useEffect[0]<callback>, dieci
  candidati. Baseline, eccezioni e matcher intatti; nessun sync/verify baseline
  o PASS globale dichiarato.
- Report completi isolati: 1.963 file e 22.649 callable invariati, Error
  1.888 invariati, Warning 2.939→2.938. Solo il file target cambia nelle metriche;
  zero parse/exception error. Report condivisi e altri WIP protetti via hash.
- Graphify Wiki AST 125/125, 1.051 nodi e 2.447 archi; passaggio finale per
  il commento senza cambi topologia. Graphify platform docs e hash finali nel
  checkpoint degli artefatti `/tmp/gaia-wiki-intent-refactor-20261117/`.

Peer Communications riallineato: audit main in preparazione, usare checkout
dedicato per preservare i WIP. Nessun cambio HEAD/branch, commit, push, merge
o deploy da questo thread. Singola slice conclusa; programma ancora aperto.
Prima della prossima slice, riallineare ownership con il peer.

```bash
COVERAGE_FILE=/tmp/gaia-wiki-intent-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/wiki/services/intent_classifier.py' -o /tmp/gaia-wiki-intent-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-wiki-intent-refactor-20261117/differential.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/wiki/services/intent_classifier.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-wiki-code
make graphify-platform-docs
```

Argv esatto dei 101 test conservato nei log e nel checkpoint degli artefatti;
non estendere il PASS API all'intera suite chat non eseguita in questa slice.
