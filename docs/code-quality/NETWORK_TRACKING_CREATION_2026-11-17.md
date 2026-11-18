# Creazione soggetti tracciati Network — 2026-11-17

Esito **IMPROVED**: due Error eliminati senza aumentare i Warning.
`create_tracked_subject` separa risoluzione del target e riattivazione;
la cognitiva aggregata di routes/tracking.py scende da 82 a 62.

## Confini e invarianti

- `_resolve_tracking_target` mantiene strip/truthiness del valore, scelta
  device o valore esplicito, lookup device, errori 404/422, lettura id/IP e
  normalizzazione nello stesso ordine. Restituisce device, valore e identita.
- `_reactivate_tracked_subject` aggiorna label/notes soltanto se diversi da
  None, converte stringhe vuote in None e riattiva il soggetto. Solo per il
  ramo existing-device rilegge device.id/IP e li assegna dopo i metadati.
  Condivide add, commit, refresh e serializzazione senza activity summary.
- La route mantiene autorizzazione prima delle letture, query legacy IP e
  lookup existing con gli stessi SQL/parametri. Il ramo legacy conserva
  reconcile, primo commit e refresh prima di modificare metadati, quindi il
  secondo commit/refresh nella riattivazione. Non assegna nuovamente device/IP
  al soggetto riconciliato. Nessun commit viene accorpato.
- Il ramo nuovo mantiene campi, fallback, ordine di valutazione e autore;
  existing/legacy conservano l'autore originale. Errori continuano a fermare
  le stesse operazioni con lo stesso stato parziale; nessun rollback/retry nuovo.

Undici altre funzioni hanno AST identico; dodici firme/decorator/return e i
nodi top-level restano invariati. API, schema, autorizzazione e UI preservati.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Route cognitiva | 48 | 13 |
| Route ciclomatica | 29 | 13 |
| Route LOC | 72 | 42 |
| Route nesting | 3 | 2 |
| Cognitiva file | 82 | 62 |
| Ciclomatica file | 70 | 67 |
| Decisioni (somma cyclomatic meno 1) | 58 | 53 |
| Callable | 12 | 14 |
| LOC file | 376 | 382 |
| Densita | 0,404255 | 0,337696 |
| Error | 3 | 1 |
| Warning | 3 | 3 |

Resolver cognitive/cyclomatic/LOC/nesting `6/5/18/2`, due parametri;
riattivazione `9/8/18/1`, quattro parametri. Entrambi sotto tutte le soglie.
La route perde il Warning LOC e la ciclomatica scende da Error a Warning;
i Warning complessivi non aumentano. Nessun debito trasferito agli helper.

## Evidenze

Artefatti separati dall'audit peer precedente:
`/tmp/gaia-network-create-tracking-refactor-20261117/`.

- 120 test PASS prima e dopo: 50 API, 18 helper, 20 VPN summary e 32 nuovi
  `backend/tests/test_network_tracking_creation.py`; zero failure/error/skip.
  Nessun test preesistente cambiato. 98 warning JWT preesistenti nella suite.
- Coverage runtime full-file statement/branch 100% prima e dopo: 177/177
  statement e 52/52 branch prima, 175/175 e 50/50 dopo. Zero esclusioni,
  missing e branch parziali; nessuna configurazione coverage modificata.
- 4.000 confronti originale/candidato equivalenti: risultati, eccezioni,
  SQL/parametri, letture/getter/scritture, commit/refresh e stato parziale;
  include IP variabili fra letture ed errori iniettati nelle operazioni.
- Sei mutanti solo in memoria respinti senza collection error/skip: rimozione
  primo commit legacy (7 failure), label vuoto ignorato (3), riassociazione
  device del legacy dopo refresh (1), autore sovrascritto (9), activity summary
  attivato (9), normalizzazione saltata (7).
- Ruff runtime/test, format-check nuovo test, lint-backend 256 file e
  diff-check PASS. Ratchet scoped origin/main PASS prima/dopo; merge-base
  `686e529ee011487e0764b9f91d023be063dbdf55`.
- Ratchet globale exit 2 per `useEffect[0]<callback>` Tributi, dieci candidati.
  Il peer ha provato sorgente Tributi HEAD PASS e delta WIP exit 2. Il blocco
  precede questa slice Network; nessun PASS globale o baseline sync/verify.
- Report completi 1.963 file: callable 22.641→22.643, Error 1.894→1.892,
  Warning 2.947 invariati. Cambia soltanto routes/tracking.py, zero errori
  parser/eccezioni. Report prima identico al completo finale della slice VPN.
- Baseline, soglie, scope, eccezioni, matcher e report condivisi preservati;
  WIP Tributi/config e altre slice Network intatti. Runtime uguale al candidato.
- Graphify Network Make: 491 nodi/1.228 archi. Aggiornamento platform docs,
  chunk e warning nel checkpoint finale; nessun graphify-out versionato.

Comandi principali dalla root (report e database soltanto in `/tmp`):

```bash
COVERAGE_FILE=/tmp/gaia-network-create-tracking-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-create-tracking-refactor-20261117/test-after.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_api.py backend/tests/test_network_router_helpers.py backend/tests/test_network_vpn_summary.py backend/tests/test_network_tracking_creation.py --junitxml=/tmp/gaia-network-create-tracking-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-network-create-tracking-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/routes/tracking.py' -o /tmp/gaia-network-create-tracking-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-create-tracking-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-create-tracking-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/routes/tracking.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-patch-openai-base-url
make graphify-platform-docs
```

## Stato

HEAD iniziale `743b21c132b19c82d1201f93b59a541a3b28269a`. Coordinamento peer
concluso prima della slice; il suo audit dei 36 file resta storico. Questa
slice ha prove e hash distinti. Nessun commit/push/PR/merge/deploy.

Dalla ripresa: 26 slice migliorative, −26 Error, −26 Warning, −177 cognitiva
aggregata. Debito globale residuo: 1.892 Error e 2.947 Warning. Nel file
restano parametri/LOC lista, cyclomatic creazione e parametri attivita.
Prossima azione review del delta; nessun secondo hotspot in questo turno.
