# Suggerimento nome peer Network — 2026-11-17

Esito **IMPROVED**: due Warning eliminati in
`backend/app/modules/network/router/helpers/traffic.py`.

## Modifica e invarianti

`_extract_peer_hint` riusa `_extract_firewall_event_parsed`, gia importato e
usato nel modulo: eliminate tre righe di parsing duplicate, senza modificare
il parser condiviso. `_peer_url_hostname` separa la lettura dell'hostname URL
dalla scelta tra dominio, URL e indirizzo peer.

La precedenza resta dominio non vuoto, hostname URL non vuoto, resolver IP.
I campi vengono letti pigramente; numero e ordine delle due strip restano
identici. Il secondo risultato strip del dominio, anche se falsy, viene
restituito subito. Errori di parsing URL o lettura hostname propagano senza
fallback IP; il resolver non viene chiamato per peer_ip falsy. Raw payload e
parser vengono letti/chiamati una volta. Nessuna modifica a API, cache, DB,
auth o transazioni. Dieci altri callable, inclusa la precedente slice RDAP,
conservano AST identico; undici firme e decorator preesistenti invariati.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Peer hint: cognitiva | 15 | 6 |
| Peer hint: ciclomatica | 13 | 6 |
| Peer hint: LOC | 15 | 11 |
| Peer hint: nesting | 2 | 1 |
| Cognitiva aggregata file | 286 | 281 |
| Ciclomatica aggregata file | 181 | 178 |
| Somma cyclomatic meno 1 | 170 | 166 |
| LOC file | 462 | 462 |
| Callable | 11 | 12 |
| Error | 6 | 6 |
| Warning | 3 | 1 |

L'helper URL ha cyclomatic/cognitive/LOC/nesting 4/4/4/1, sotto soglia.
La deduplica elimina decisioni esistenti e non trasferisce violation. Restano
sei Error e un Warning nei riepiloghi traffico/statistiche, fuori slice e
invariati. Nessuna seconda responsabilita modificata.

## Verifiche

Artefatti `/tmp/gaia-network-peer-hint-refactor-20261117/`.
Nuovo test `backend/tests/test_network_peer_hints.py`.

- 154 test PASS prima/dopo, zero skip/failure/error: 18 helper, 50 API,
  50 caratterizzazioni peer resolution e 36 nuovi casi peer hint.
- Coverage full-file statement/branch 100%: 287/287 statement e 94/94 branch
  prima/dopo, zero esclusioni, missing o branch parziali.
- Differenziale deterministico su 16000 input: zero differenze di risultati,
  tipo/testo eccezioni, raw payload/parser, campi/strip, URL e resolver.
  Input non mutati. Dodici prove aggiuntive lazy/falsy/hostname prima/dopo
  tutte equivalenti.
- Tre mutanti in memoria respinti dai test: dominio ignorato, seconda strip
  URL rimossa e resolver chiamato anche con IP falsy. Runtime su disco intatto.
- I primi due tentativi dei controtest non sono PASS: il primo selezionava
  una stringa presente due volte, il secondo usava una copia namespace le cui
  patch non raggiungevano i globals delle funzioni mutate. Corretto solo lo
  script temporaneo: selezione limitata all'hotspot e vero ModuleType con
  globals condivisi. Log/script dei tentativi conservati; nessun test o gate
  indebolito. Confronto funzionale e dodici contratti erano gia equivalenti.
- Ratchet mirato origin/main PASS prima/dopo contro baseline autorevole
  merge-base `686e529ee011487e0764b9f91d023be063dbdf55`.
- Ruff runtime/test, format nuovo test e lint-backend su 227 file PASS.
  Nessun test esistente modificato, rimosso o indebolito.
- Graphify Network aggiornato tramite Make: 452 nodi, 1143 archi,
  18 comunita. Esito Graphify platform docs nei log/checkpoint della slice.

Comandi principali dalla root, con file coverage distinti prima/dopo:

```bash
COVERAGE_FILE=/tmp/gaia-network-peer-hint-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-peer-hint-refactor-20261117/test.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_peer_resolution.py backend/tests/test_network_peer_hints.py
COVERAGE_FILE=/tmp/gaia-network-peer-hint-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/traffic.py' -o /tmp/gaia-network-peer-hint-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-peer-hint-refactor-20261117/differential.py
python3 tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/traffic.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-platform-docs
```

## Stato del checkout

HEAD iniziale `ce9968b65a1b8a6fe94d061f265df2623e9a4555`. Baseline, soglie,
scope ed eccezioni intatti; baseline non sincronizzata nel checkout concorrente
e baseline-verify non eseguito. Report condivisi preesistenti preservati.
Nessun commit, push, merge o deploy eseguito.

Report completo: 1960 file; callable22603→22604, Error1910 invariati,
Warning2964→2962. Unico path con metriche variate `traffic.py`. Ratchet globale
exit2 per l'identica ambiguita preesistente `useEffect[0]<callback>` in
`frontend/src/app/ruolo/tributi/page.tsx`, dieci candidati. Non certificato
verde il gate globale. Dalla ripresa otto slice hanno eliminato otto Error
e undici Warning, riducendo di 41 la cognitiva aggregata dei file.
