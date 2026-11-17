# Risoluzione nome peer Network — 2026-11-17

Esito **IMPROVED**: due Error e un Warning eliminati in
`backend/app/modules/network/router/helpers/traffic.py`.

## Modifica e invarianti

`_resolve_peer_label` conserva validazione IP, DNS e cache LRU da 512 elementi.
Quattro helper separano il recupero RDAP, la precedenza dei nomi nel payload,
la lettura della singola entita e la validazione di una riga `fn`. L'estrazione
riduce l'annidamento delle vCard; ogni helper resta sotto tutte le soglie.
Gli altri sei callable conservano AST identico e tutte le sette firme e i
decorator preesistenti restano invariati.

Il DNS precede il filtro degli indirizzi privati, loopback, link-local e
multicast. Un risultato DNS vuoto lascia proseguire RDAP solo sugli indirizzi
ammessi. URL, timeout 4, context manager e catch rete/JSON restano identici;
gli errori di lettura del payload dopo il JSON continuano a propagarsi.

La prima riga `fn` valida vince; `org` continua a essere ignorato. I fallback
restano `name` e poi `handle`. Numero e ordine delle letture e delle due
`strip` restano identici. L'helper di entita restituisce zero o un elemento:
cosi il chiamante distingue l'assenza di una riga valida da un secondo risultato
`strip` falsy, che prima era restituito immediatamente. Nessun fallback viene
anticipato. Cache di risultati e None, mancata cache delle eccezioni ed eviction
a 512 elementi restano invariati. API, DB, auth e transazioni non cambiano.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Resolver: cognitiva | 56 | 9 |
| Resolver: ciclomatica | 32 | 7 |
| Resolver: LOC | 43 | 15 |
| Resolver: nesting | 4 | 2 |
| Cognitiva aggregata file | 297 | 286 |
| Ciclomatica aggregata file | 176 | 181 |
| Somma cyclomatic meno 1 | 169 | 170 |
| LOC file | 449 | 462 |
| Callable | 7 | 11 |
| Error | 8 | 6 |
| Warning | 4 | 3 |

Helper cyclomatic/cognitive/LOC/nesting: recupero RDAP 8/9/11/2, payload
8/13/12/3, entita 8/9/10/2, predicato 6/5/8/0. Nessuna nuova violation.
La ciclomatica cresce di cinque punti: quattro baseline dei nuovi callable e
una decisione per distinguere un'entita senza nome da una con nome falsy.
Questa crescita e dichiarata; la cognitiva aggregata scende di 11 e i finding
diminuiscono senza trasferimento del debito. Restano sei Error e tre Warning
nei riepiloghi traffico/statistiche e nel peer hint, tutti fuori slice e invariati.

## Verifiche

Artefatti: `/tmp/gaia-network-peer-refactor-20261117/`.
Test nuovo: `backend/tests/test_network_peer_resolution.py`.

- 118 test PASS di caratterizzazione/API prima/dopo, zero skip/failure/error: 18 helper originali, tutti
  i 50 test API Network e 50 nuove caratterizzazioni.
- Full-file statement/branch 100%: 276/276→287/287 statement e
  92/92→94/94 branch, zero esclusioni, missing o branch parziali. Anche i soli
  68 test preesistenti passano sul runtime originale con coverage 100%.
- Differenziale deterministico su 15000 casi: zero differenze di risultato,
  tipo/testo eccezioni, cache hit/miss/size, chiamate DNS/HTTP/JSON, accessi
  lazy ai campi/liste e strip. Input non mutati; rete sostituita nei test.
- Otto prove aggiuntive su letture lazy e secondo risultato strip falsy,
  eseguite separatamente sul sorgente originale e corrente, tutte equivalenti.
- Tre mutanti in memoria respinti dai nuovi test: accettazione di `org`, una
  sola strip sul nome e cache ridotta a due elementi. Runtime su disco intatto.
- Ratchet mirato origin/main PASS prima/dopo; baseline autorevole al merge-base
  `686e529ee011487e0764b9f91d023be063dbdf55`.
- Ruff runtime/test e format del nuovo test PASS; lint-backend PASS su
  226 file cambiati. Nessun test esistente modificato, rimosso o indebolito.
- Graphify Network aggiornato tramite Make: 451 nodi, 1140 archi, 17 comunita.
  L'esito dell'aggiornamento piattaforma docs e nei log/checkpoint della slice.

Comandi principali dalla root, con file coverage distinti per prima/dopo:

```bash
COVERAGE_FILE=/tmp/gaia-network-peer-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-peer-refactor-20261117/test.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_peer_resolution.py
COVERAGE_FILE=/tmp/gaia-network-peer-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/traffic.py' -o /tmp/gaia-network-peer-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-peer-refactor-20261117/differential.py
python3 tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/traffic.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-platform-docs
```

## Stato del checkout

HEAD iniziale `a6421cff23dbf2d4674fe7b34047742f06f89965`: avanzamento
Communications estraneo alla slice preservato. Baseline, soglie, scope ed
eccezioni intatti; baseline non sincronizzata nel checkout concorrente e
baseline-verify non eseguito. Report condivisi preesistenti preservati.
Nessun commit, push, merge o deploy eseguito.

Report completi prima/dopo: 1960 file, callable 22599→22603; Error1912→1910,
Warning2965→2964. Unico path con metriche variate `traffic.py`. Ratchet globale
exit2 per identica ambiguita preesistente `useEffect[0]<callback>` in
`frontend/src/app/ruolo/tributi/page.tsx`, dieci candidati. Non certificato
verde il gate globale. Dalla ripresa sette slice hanno eliminato otto Error
e nove Warning, riducendo di 36 la cognitiva aggregata dei file.
