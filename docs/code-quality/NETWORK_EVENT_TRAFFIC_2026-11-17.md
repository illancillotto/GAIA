# Contatori traffico evento Network — 2026-11-17

Esito **IMPROVED** sulla ciclomatica dell'estrattore: eliminato l'ultimo Warning
di `backend/app/modules/network/router/helpers/endpoints.py`, senza trasferirlo.
Tutti i callable del file sono sotto soglia. Cognitiva e decisioni aggregate
restano invariate; nessuna riduzione aggregata viene rivendicata.

## Modifica e invarianti

`_extract_event_traffic` mantiene il calcolo di byte in ingresso/uscita e peer.
`_event_traffic_counters` isola parsing del payload e conversione dei due contatori.
Il convertitore locale `_to_int` mantiene AST identico nella nuova ownership.
I tre resolver dei nomi endpoint mantengono AST identico; le cinque firme
preesistenti sono preservate.

Restano invariati parsing e fallback dei payload non mapping, ordine get/str
sent prima di received, conversione `str/strip/int/max`, clamp negativo e catch
limitato a TypeError/ValueError. OverflowError e altri errori continuano a
propagarsi. I contatori vengono letti anche quando il dispositivo non coincide
con nessun endpoint, prima di leggere gli IP. La sorgente prevale se entrambi
gli endpoint coincidono; il ritorno per destinazione rilegge la sorgente.
Il fallback peer conserva `dst_ip or src_ip`, inclusi valori vuoti e None.
Nessuna query, transazione, API, schema o autorizzazione modificata.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Estrattore: cognitiva | 12 | 4 |
| Estrattore: ciclomatica | 12 | 5 |
| Estrattore: LOC | 18 | 7 |
| Estrattore: nesting | 2 | 1 |
| Cognitiva aggregata file | 31 | 31 |
| Ciclomatica aggregata file | 31 | 32 |
| Somma cyclomatic meno 1 | 26 | 26 |
| LOC file | 64 | 65 |
| Callable | 5 | 6 |
| Error | 0 | 0 |
| Warning | 1 | 0 |

Helper contatori cognitive/cyclomatic/LOC/nesting8/8/12/2; convertitore4/4/7/2,
entrambi sotto soglia. Il punto ciclomatico aggiunto e quello del nuovo callable,
senza crescita delle decisioni aggregate. Nessuna violation trasferita.

## Verifiche

Artefatti `/tmp/gaia-network-event-traffic-refactor-20261117/`.
Nuovo test `backend/tests/test_network_event_traffic.py`.

- 145test PASS prima/dopo:18helper,50API Network,18nomi endpoint,
  16riepilogo dispositivo e43nuove caratterizzazioni; zero skip/failure/error.
- Full-file statement/branch100%:45/45→46/46statement,16/16branch invariati;
  zero esclusioni, missing o branch parziali. Sorgente finale congelato tramite hash.
- Differenziale18000scenari equivalente per risultati/eccezioni e trace di
  parser, get, str e attributi evento. Include JSON reali, stringhe numeriche
  Unicode, payload non mapping, IP variabili ed errori alle singole operazioni.
- Cinque mutanti in memoria respinti: byte invertiti, clamp negativo rimosso,
  IP letto prima dei contatori, OverflowError catturato e get received prima
  della conversione sent. Nessun runtime su disco mutato dai controtest.
- Ratchet mirato origin/main PASS prima/dopo, baseline autorevole merge-base
  `686e529ee011487e0764b9f91d023be063dbdf55`. Globale exit2 per la stessa
  ambiguita Tributi preesistente (`useEffect[0]<callback>`, dieci candidati).
- Report completi1960file: Error1905 invariati, Warning2956→2955,
  callable22616→22617; solo endpoints.py varia metriche, nessun errore di parsing.
- Ruff, format nuovo test, lint-backend235file e diff-check PASS. Primo lint
  segnalava cifre fullwidth intenzionali nel test; usati escape Unicode senza
  rimuovere il caso o aggiungere noqa. Nessun test esistente modificato.
- Graphify Network aggiornato con `make graphify-network-code GRAPHIFY_CODE_FLAGS=--force`
  dopo `make graphify-patch-force-pruning`:465nodi/1173archi. Aggiornamento platform
  docs e completamento semantico registrati nel checkpoint.

Comandi principali dalla root, con coverage distinta prima/dopo:

```bash
COVERAGE_FILE=/tmp/gaia-network-event-traffic-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-event-traffic-refactor-20261117/test.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_endpoint_labels.py backend/tests/test_network_device_traffic_summary.py backend/tests/test_network_event_traffic.py
COVERAGE_FILE=/tmp/gaia-network-event-traffic-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/endpoints.py' -o /tmp/gaia-network-event-traffic-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-event-traffic-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-event-traffic-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/endpoints.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code GRAPHIFY_CODE_FLAGS=--force
make graphify-platform-docs
```

## Stato del checkout

HEAD `ce9968b65a1b8a6fe94d061f265df2623e9a4555`; baseline/soglie/scope/eccezioni
intatti, nessuna sincronizzazione o baseline-verify nel checkout concorrente.
Hash tracking precedente e report condivisi preservati. Dalla ripresa quattordici
slice: -13Error/-18Warning/-80cognitiva aggregata; nessuna percentuale storica di
completamento dedotta. Nessun commit, push, merge o deploy. Obiettivo generale
ancora attivo; selezione del prossimo hotspot rimandata al turno successivo.
