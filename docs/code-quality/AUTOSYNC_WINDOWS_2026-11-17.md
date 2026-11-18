# Finestre autosync — candidato rifiutato, 2026-11-17

Esito runtime `NO_SAFE_CHANGE`; consegna `TEST_ONLY`. Il controllo anticipato
degli intervalli diurni riduceva l'annidamento dei due casi notturni, ma
aggiungeva una riga a `window_context`. Il ratchet contro la baseline del
merge-base rifiuta anche aumenti LOC sotto soglia sul codice legacy.
Il candidato e stato scartato e il runtime ripristinato byte per byte.

Il diff finale contiene 28 test nuovi e documentazione; nessuna modifica
runtime, baseline, eccezioni o matcher. Nessun commit, push, merge o deploy.
HEAD `743b21c1`, branch `chore/split-changes-20261109`, merge-base `686e529e`.

## Metriche

| Metrica target/file | Originale e finale | Candidato rifiutato |
| --- | ---: | ---: |
| Cognitiva | 15 | 13 |
| Ciclomatica | 8 | 8 |
| Nesting | 3 | 2 |
| LOC target / file | 14 / 15 | 15 / 16 |
| Callable / parametri | 1 / 2 | 1 / 2 |
| Error / Warning | 0 / 1 | 0 / 0 |
| Ratchet scoped exit | 0 | 1 |

Finding del candidato: `legacy_metric_regression`, `loc`, baseline 14,
value 15, delta +1. Nessuna compressione di righe o modifica al gate per
aggirarlo. Non si conteggia il Warning eliminato soltanto dal candidato.

## Caratterizzazione e verifiche

- 28 nuovi test e 38 esistenti: 66 PASS sull'originale, sul candidato e sul
  runtime ripristinato, zero failure/error/skip. Coverage originale e finale
  full-file statement/branch 100%: 15/15 e 10/10; candidato 16/16 e 10/10.
  Nessuna esclusione, missing line o partial branch.
- Test di confine: start incluso, end escluso, start=end sempre attivo,
  mezzanotte, anno bisestile e cambio anno, primo match fra intervalli
  sovrapposti, prosecuzione dopo un non-match, parsing lazily interrotto da
  un match, errori di formato e overflow prima della data minima.
- 10.032 differenziali equivalenti originale/candidato, inclusi microsecondi,
  intervalli multipli, date estreme e input malformati. AST del prefisso,
  primo match, azioni notturne e ritorno finale invariato. Lo script legge
  lo snapshot `windows-rejected.py`, non il runtime finale ripristinato.
- Tre mutanti solo in memoria respinti: guardia invertita 3.949 divergenze,
  end incluso 467, data notturna errata 1.656. Nessun mutante nel checkout.
- Finale: ratchet scoped PASS; Ruff e format-check del nuovo test,
  lint-backend (270 file) e diff-check PASS. Risultato del ratchet globale
  finale e aggiornamento semantico docs nel checkpoint degli artefatti.
- Graphify backend rieseguito dopo il ripristino: AST 1.073/1.073, nessun
  cambiamento di topologia. WIP precedenti e file protetti verificati via hash.

Totali finali invariati: 1.963 file, 22.649 callable, 1.888 Error, 2.939 Warning.
Il report completo precedente e riusato solo dopo verifica di HEAD e hash dei
WIP; il report del candidato e conservato separatamente come `global-rejected.json`.
I report condivisi del repository restano intatti.

Artefatti: `/tmp/gaia-autosync-windows-refactor-20261117/`, compresi i log del
ratchet rifiutato, tutti i test/coverage e gli snapshot originale/candidato.
Prossima azione alla continuazione: scegliere un altro singolo hotspot.

```bash
COVERAGE_FILE=/tmp/gaia-autosync-windows-refactor-20261117/.coverage-final DATABASE_URL=sqlite:////tmp/gaia-autosync-windows-refactor-20261117/test-final.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_domande_irrigue_windows.py backend/tests/test_domande_irrigue_autosync_scheduler.py backend/tests/test_autosync_window_boundaries.py --junitxml=/tmp/gaia-autosync-windows-refactor-20261117/tests-final.xml
COVERAGE_FILE=/tmp/gaia-autosync-windows-refactor-20261117/.coverage-final backend/.venv/bin/python -m coverage json --include='*/elaborazioni/autosync_windows.py' -o /tmp/gaia-autosync-windows-refactor-20261117/coverage-final.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-autosync-windows-refactor-20261117/differential.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/elaborazioni/autosync_windows.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-backend
make graphify-platform-docs
```
