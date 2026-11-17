# Normalizzazione soggetti tracciati Network — 2026-11-17

Esito **IMPROVED**: due Warning eliminati in
`backend/app/modules/network/router/helpers/tracking.py`.

## Modifica e invarianti

`_normalize_tracked_value` conserva strip iniziale e dispatch dei tipi IP,
dominio, URL e altri. `_normalize_tracked_domain` isola estrazione hostname,
fallback al testo normalizzato e sequenza strip/rstrip/lower.

Il parsing URL avviene soltanto in presenza di `://`; un hostname falsy usa
il valore originale. Non si aggiungono nuove regole di validazione: stringhe
dominio senza schema, URL senza hostname e URL malformati del tipo `url`
seguono le regole esistenti. L'IP mantiene canonicalizzazione, HTTP422 con
messaggio basato sull'input originale e causa ValueError. Domain/URL vuoti
mantengono messaggi e status; errori del parser URL, hostname, strip o IP
non-ValueError continuano a propagarsi. Ordine e numero delle operazioni
sono invariati. API, DB, auth e transazioni non cambiano.

Quattordici altri callable hanno AST identico; tutte le quindici firme
preesistenti restano invariate. Nessun'altra responsabilita rifattorizzata.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Normalizzatore: cognitiva | 17 | 10 |
| Normalizzatore: ciclomatica | 11 | 7 |
| Normalizzatore: LOC | 18 | 14 |
| Normalizzatore: nesting | 3 | 3 |
| Cognitiva aggregata file | 253 | 250 |
| Ciclomatica aggregata file | 156 | 157 |
| Somma cyclomatic meno 1 | 141 | 141 |
| LOC file | 470 | 472 |
| Callable | 15 | 16 |
| Error | 8 | 8 |
| Warning | 6 | 4 |

Helper cyclomatic/cognitive/LOC/nesting5/4/6/1, sotto tutte le soglie. Il punto
ciclomatico aggiunto corrisponde al nuovo callable; le decisioni aggregate
restano invariate. Cognitiva aggregata ridotta di tre, nessun debito trasferito.
Restano otto Error e quattro Warning in timeline ARP, riconciliazione legacy,
matching e riepilogo attivita, tutti fuori slice e invariati.

## Verifiche

Artefatti `/tmp/gaia-network-tracked-normalization-refactor-20261117/`.
Nuovo test `backend/tests/test_network_tracked_normalization.py`.

- 117test PASS prima/dopo, zero skip/failure/error:18helper router Network,
  tutti50API Network e49nuove caratterizzazioni della normalizzazione.
- Full-file statement/branch100%:249/249→251/251 statement e108/108branch
  invariati; zero esclusioni, missing o branch parziali.
- Differenziale deterministico su 30000 casi: risultati, tipo/testo/cause
  eccezioni, HTTP status/detail/headers e trace strip/parser equivalenti.
  Include IP v4/v6/scope, URL malformati, valori non stringa e tipi sconosciuti.
- Quattordici prove aggiuntive prima/dopo su sequenza operazioni, fallback
  hostname falsy, errori e mancato parsing senza separatore, tutte equivalenti.
- Tre mutanti in memoria respinti dai nuovi test: lower dominio rimosso,
  parsing di tutti i domini e fallback hostname rimosso. ModuleType mantiene
  globals delle funzioni patchabili; nessun mutante applicato al runtime.
- Ratchet mirato origin/main PASS prima/dopo contro baseline autorevole
  merge-base `686e529ee011487e0764b9f91d023be063dbdf55`.
- Ruff runtime/test, format nuovo test, lint-backend232file e diff-check PASS.
  Nessun test esistente modificato, rimosso o indebolito.
- Graphify Network e platform docs aggiornati tramite Make; dettagli dei grafi
  e completamento semantico nei log/checkpoint della slice.

Comandi principali dalla root, con file coverage distinti prima/dopo:

```bash
COVERAGE_FILE=/tmp/gaia-network-tracked-normalization-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-tracked-normalization-refactor-20261117/test.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_tracked_normalization.py
COVERAGE_FILE=/tmp/gaia-network-tracked-normalization-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/tracking.py' -o /tmp/gaia-network-tracked-normalization-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-tracked-normalization-refactor-20261117/differential.py
python3 tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/tracking.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-platform-docs
```

## Stato del checkout

HEAD iniziale `ce9968b65a1b8a6fe94d061f265df2623e9a4555`. Baseline, soglie,
scope ed eccezioni intatti; baseline non sincronizzata nel checkout concorrente
e baseline-verify non eseguito. Report condivisi preesistenti preservati.
Nessun commit, push, merge o deploy eseguito. Nessun secondo hotspot avviato.

Report completi1960file, callable22610→22611, Error1907 invariati,
Warning2960→2958. Unico path con metriche variate tracking.py. Ratchet globale
exit2 per stessa ambiguita `useEffect[0]<callback>` in
`frontend/src/app/ruolo/tributi/page.tsx`, dieci candidati; gate globale non
certificato verde. Dalla ripresa undici slice: undici Error e quindici Warning
eliminati, cognitiva aggregata ridotta di60.
