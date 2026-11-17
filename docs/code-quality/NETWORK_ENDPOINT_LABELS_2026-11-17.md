# Fallback nomi endpoint firewall — 2026-11-17

Esito **IMPROVED**: un Error e un Warning eliminati in
`backend/app/modules/network/router/helpers/endpoints.py`.

## Modifica

Il fallback del nome del dispositivo collegato era duplicato per IP sorgente
e destinazione. `_linked_endpoint_label` applica la stessa regola a entrambi:
preserva un nome gia risolto, altrimenti usa il nome collegato soltanto se
l'IP e non vuoto e coincide con quello del dispositivo. Il dispositivo viene
passato all'helper senza anticipare la lettura del suo attributo ORM.

Le query per IP restano entrambe eseguite in ordine sorgente/destinazione.
Il lookup per ID e la risoluzione del nome collegato mantengono ordine e
condizioni, incluso ID zero valido. None e stringhe vuote restano distinti;
numero e sequenza delle letture IP non cambiano, anche se la seconda lettura
solleva un errore. Nessuna modifica a API, schema, auth o transazioni.
Il resolver IP e l'estrattore traffico mantengono AST identico.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Resolver endpoint: ciclomatica | 15 | 7 |
| Resolver endpoint: cognitiva | 18 | 8 |
| Resolver endpoint: LOC | 20 | 19 |
| Cognitiva aggregata file | 36 | 31 |
| Ciclomatica aggregata file | 34 | 31 |
| Somma di cyclomatic meno 1 | 30 | 26 |
| LOC file | 56 | 64 |
| Callable | 4 | 5 |
| Error | 1 | 0 |
| Warning | 2 | 1 |

L'helper vale cyclomatic/cognitive/LOC/nesting/parametri 5/5/9/1/4, sotto
tutte le soglie. La regola condivisa elimina decisioni duplicate e non
trasferisce violation. Residuo fuori slice: `_extract_event_traffic`,
cyclomatic 12, un Warning. Nessuna seconda responsabilita modificata.

## Verifiche

Nuovo test: `backend/tests/test_network_endpoint_labels.py`.
Artefatti privati: `/tmp/gaia-network-endpoints-refactor-20261117/`.

- 36 test PASS prima/dopo: 18 originali del router e 18 nuove caratterizzazioni.
- Coverage full-file 100%: 45/45 statement prima/dopo, branch 18/18 prima
  e 16/16 dopo, nessuna esclusione, missing o branch parziale.
- Quattro casi con un vero `NetworkDevice` SQLAlchemy e IP scaduto: refresh
  SELECT solo quando necessario, una volta al massimo, nessuna scrittura.
  Proxy con attributo variabile provano ordine e numero delle letture.
- 11 test API Network su firewall, tracking e traffico PASS, con fixture
  SQLite in memoria. Nessun dato o servizio reale modificato.
- Differenziale con sorgente originale congelato su 12960 combinazioni:
  risultati, eccezioni e trace dei lookup/attributi identici. Include nomi
  None/vuoti/presenti, IP vuoti/diversi/uguali, ID None/zero/valido,
  dispositivo assente/presente, IP variabile ed errori sulle letture.
- Due mutanti in memoria respinti: guardia sul nome esistente rimossa e
  accesso anticipato all'IP. Runtime su disco non alterato dai controtest.
- Ratchet del file `origin/main` PASS prima/dopo; merge-base `686e529e`.
- Ruff, format del nuovo test, lint-backend su 217 file e diff-check PASS.
- Graphify Network aggiornato con Make: 439 nodi, 1112 archi, 16 comunita.

I primi due tentativi pytest-cov con source indicato come modulo causavano
una doppia importazione SQLAlchemy e fallivano in collection con
`Type object is already registered`, prima di modificare runtime. La prova
completa usa `coverage run --branch` senza import anticipato, poi filtra
il solo report del file: nessuna esclusione o policy modificata. Log iniziali
`tests-original.log` e `tests-before.log` conservati, non contati come PASS.

Comandi principali dalla root (prima/dopo con COVERAGE_FILE distinti):

```bash
COVERAGE_FILE=/tmp/gaia-network-endpoints-refactor-20261117/.coverage-after-run backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_endpoint_labels.py
COVERAGE_FILE=/tmp/gaia-network-endpoints-refactor-20261117/.coverage-after-run backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/endpoints.py' -o /tmp/gaia-network-endpoints-refactor-20261117/coverage-after-run.json --fail-under=100
DATABASE_URL=sqlite:////tmp/gaia-network-endpoints-refactor-20261117/test.db backend/.venv/bin/python -m pytest -q backend/tests/test_network_api.py -k 'firewall or tracked or traffic'
python3 tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/endpoints.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
```

## Stato del checkout

SHA iniziale `82bda86882d9fd8c29955a8f750c54abca8fdb20`; sorgente originale
SHA256 `52f0651cd3f1978d3cf7e93e094d813d4ee65042c4e8301cd0b57cd35f38a15a`.
Baseline, soglie, scope ed eccezioni invariati; baseline non sincronizzata
nel checkout concorrente, baseline-verify non eseguito.

Il report completo conta 1960 file, 22590 callable, 1917 Error e 2968 Warning.
Rispetto alla slice precedente varia anche `admin-templates.tsx`, modificato
da lavoro Communications concorrente: callable 11→13, cognitive 21→22,
cyclomatic 28→31, senza delta nei suoi finding. Nessuna di quelle variazioni
e attribuita al refactor Network. I report condivisi preesistenti restano intatti.

Il ratchet globale resta exit 2 per l'ambiguita preesistente di
`useEffect[0]<callback>` in `frontend/src/app/ruolo/tributi/page.tsx`, dieci
candidati. Nessuna certificazione globale o campagna dichiarata conclusa.
Modifiche concorrenti e slice precedenti preservate; nessun commit, push,
merge o deploy eseguito.
