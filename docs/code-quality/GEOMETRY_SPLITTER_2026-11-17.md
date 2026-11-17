# Separatori WKT Catasto — 2026-11-17

Esito **IMPROVED**: eliminati entrambi i Warning del servizio
`backend/app/modules/catasto/services/geometry_serialization.py`.

## Modifica e invarianti

Una sola riga in `_split_top_level`: il controllo della virgola e indipendente
dal ramo che aggiorna la profondita delle parentesi. Una parentesi non puo
essere una virgola, quindi il controllo indipendente conserva i separatori
riconosciuti e riduce l'annidamento senza introdurre helper o duplicazioni.

Restano invariati ordine e contenuto delle parti, trimming, parti vuote prima
delle virgole e coda vuota scartata. Anche parentesi sbilanciate e profondita
negativa mantengono il comportamento originale: nessuna nuova validazione.
Nessun cambiamento a parser Polygon/MultiPolygon, SRID, WKB, eccezioni,
centroidi, API, schema, transazioni o firme. Gli altri nove callable hanno AST
identico prima/dopo. Query Graphify sul corpus Catasto eseguita prima della slice.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Cognitiva `_split_top_level` | 17 | 13 |
| Nesting `_split_top_level` | 4 | 3 |
| Ciclomatica `_split_top_level` | 8 | 8 |
| LOC `_split_top_level` | 16 | 16 |
| Cognitiva aggregata file | 67 | 63 |
| Ciclomatica aggregata file | 57 | 57 |
| LOC file | 101 | 101 |
| Callable | 10 | 10 |
| Warning | 2 | 0 |
| Error | 0 | 0 |

## Evidenze

Nuovo test: `backend/tests/test_catasto_geometry_serialization.py`.
Artefatti privati: `/tmp/gaia-geometry-refactor-20261117/`.

- 28 test PASS prima/dopo, con riferimento indipendente basato sul conteggio
  delle parentesi del prefisso per 19531 stringhe corte esaustive.
- Coverage full-file prima/dopo: 98/98 statement e 48/48 branch (100%),
  zero righe escluse, missing o branch parziali; fail-under 100.
- Esecuzione insieme ai due test API esistenti
  `test_distretto_geojson_endpoint_returns_feature` e
  `test_distretto_geojson_endpoint_returns_404_without_geometry`: 30 PASS.
  Le fixture API usano SQLite in memoria; nessun dato reale modificato.
- Confronto originale/corrente su 97656 stringhe, incluse profondita negative,
  e 360 chiamate agli adapter: zero differenze di risultato o eccezione.
- Due mutanti in memoria respinti dal test esaustivo: separazione a profondita
  negativa e separazione dentro le parentesi. Runtime su disco non alterato.
- Ratchet mirato `origin/main` PASS prima/dopo; merge-base `686e529e`.
- Ruff runtime/test, format del nuovo test e `make lint-backend` PASS,
  215 file nel ratchet di stile. Prima verifica Ruff segnalava RUF001 nel
  nuovo esempio greco: sostituito con Unicode accentato senza ignore.
- Il primo differenziale aveva gia verificato stringhe e adapter, ma non
  caricava il test per `ModuleNotFoundError: app`. Esecuzione finale completa
  con `PYTHONPATH=backend` PASS; log distinti preservati.
- `make graphify-catasto-code` PASS: nessuna variazione topologica nel grafo.

Comandi principali, dalla root:

```bash
COVERAGE_FILE=/tmp/gaia-geometry-refactor-20261117/.coverage-after backend/.venv/bin/python -m pytest -q backend/tests/test_catasto_geometry_serialization.py --cov=app.modules.catasto.services.geometry_serialization --cov-branch --cov-report=term-missing --cov-report=json:/tmp/gaia-geometry-refactor-20261117/coverage-after.json --cov-fail-under=100
DATABASE_URL=sqlite:////tmp/gaia-geometry-refactor-20261117/test.db backend/.venv/bin/python -m pytest -q backend/tests/test_catasto_geometry_serialization.py backend/tests/test_catasto_phase1.py -k 'geometry_serialization or distretto_geojson_endpoint'
python3 tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/catasto/services/geometry_serialization.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-catasto-code
```

Baseline, soglie, scope ed eccezioni invariati; baseline non sincronizzata
nel checkout concorrente e baseline-verify non eseguito. SHA iniziale
`82bda86882d9fd8c29955a8f750c54abca8fdb20`. Hash SHA256 sorgente originale:
`85f8f832c15074429a343c74a7a77c4e97f7b1806746be67329379baf4af0a70`.
Modifiche concorrenti e precedente slice pagatori preservate.

Il report globale completo dopo la slice conta 1960 file, 1918 Error e
2969 Warning: due Warning in meno rispetto alla chiusura pagatori (2971).
Il solo path con metriche cambiate e il servizio geometrico. Il ratchet globale
resta exit 2 per `ambiguous_identity` su `useEffect[0]<callback>` in
`frontend/src/app/ruolo/tributi/page.tsx`, dieci candidati: stesso finding
preesistente, nessuna correzione opportunistica al matcher. I report completi
includono i test worker e non dimostrano percentuali rispetto a corpus storici
diversi. Report condivisi gia modificati nel checkout preservati.

Nessun commit, push, merge o deploy. Questa slice termina senza Warning
residui nel servizio; l'obiettivo di riduzione per ondate resta attivo.
