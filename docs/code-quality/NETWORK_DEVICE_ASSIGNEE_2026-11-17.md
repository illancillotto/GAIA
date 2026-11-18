# Validazione assegnatario patch dispositivi Network — 2026-11-17

Esito **IMPROVED** sulla ciclomatica: un Warning eliminato in
`backend/app/modules/network/router/routes/devices.py`. Cognitiva e decisioni
aggregate restano invariate; nessuna violation trasferita al validatore.

## Modifica e invarianti

`_validate_device_assignee(db, updates)` isola il controllo dell'assegnatario
dall'orchestrazione della patch. Il corpo e identico al blocco originale e la
chiamata occupa la stessa posizione, subito dopo model_dump(exclude_unset=True).
La validazione resta dopo auth e lookup del dispositivo, prima del lifecycle.

Assegnatario assente non modifica il dato; None lo cancella senza query;
zero viene cercato come ogni altro ID esplicito. Un utente inesistente produce
lo stesso 404 prima di modificare il dispositivo, anche se si richiede retired.
Le letture ripetute della mappa non vengono accorpate. Retirement, reactivation,
timestamp, ordine dei setter, sync alert, add, unico commit, refresh e letture
per la risposta mantengono ordine e comportamento, anche in caso di errore.
Non vengono aggiunti rollback, retry o nuove transazioni.

Espandendo la chiamata con il corpo dell'helper, l'AST di patch_device coincide
con l'originale. Sette altri callable hanno AST identico; otto firme, return e
decorator originali e tutti i sette contratti delle route restano invariati.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Patch: cognitiva | 14 | 8 |
| Patch: ciclomatica | 11 | 7 |
| Patch: LOC | 33 | 30 |
| Patch: nesting | 2 | 2 |
| Cognitiva file | 32 | 32 |
| Ciclomatica file | 34 | 35 |
| Somma cyclomatic meno 1 | 26 | 26 |
| Callable | 8 | 9 |
| LOC file | 195 | 197 |
| Densita | 0,338462 | 0,340102 |
| Error | 1 | 1 |
| Warning | 1 | 0 |

Helper cognitive/cyclomatic/LOC/nesting `6/5/5/2`, due parametri, sotto soglia.
L'aumento della somma ciclomatica corrisponde al callable aggiunto; nessuna
riduzione cognitiva aggregata o delle decisioni viene rivendicata.
Resta l'Error dei dodici parametri di get_devices.

## Verifiche

Artefatti `/tmp/gaia-network-device-assignee-refactor-20261117/`.
Nuovo `backend/tests/test_network_device_assignee.py`: 26 casi.

- 118 test PASS prima/dopo: 50 API, 18 helper, 24 bulk, 26 assignee. Entrambi
  gli XML con zero skip/failure/error; nessun test esistente modificato.
- Full-file statement/branch 100% prima 94/94 statement e 30/30 branch,
  dopo 96/96 e 30/30. Zero esclusioni, righe mancanti o branch parziali.
- 4.000 scenari differenziali equivalenti per risposta, eccezioni, stato
  parziale device/updates e trace ordinato query, letture mappa/ORM, setter,
  clock, auth, sync, add, commit, refresh e serializzazione. Include ordine
  variabile dei campi, getter variabili, None/zero/False, retirement esistente
  o nuovo, errori iniettati e refresh che cambia lo stato.
- Cinque mutanti in memoria respinti anche per stato o risultato: zero ignorato,
  retirement che salta la validazione, controllo dopo lifecycle, assegnatario
  inesistente accettato, lookup su None. Nessun mutante applicato su disco.
- Ratchet mirato origin/main PASS prima/dopo, zero finding; merge-base
  `686e529ee011487e0764b9f91d023be063dbdf55`. Globale exit 2 per la stessa
  ambiguita preesistente Tributi useEffect[0]<callback>, dieci candidati.
  Nessun PASS globale, baseline sync o baseline-verify dichiarato.
- Report completi 1.963 file, callable 22.636→22.637, Error 1.897 invariati,
  Warning 2.950→2.949. Varia solo routes/devices.py; zero parse/exception error.
- Ruff runtime/test, format nuovo test, lint-backend 250 file e diff-check PASS.
  Nessuna nuova failure applicativa; 98 warning JWT API preesistenti.
- Graphify Network aggiornato via Make: 485 nodi/1.212 archi. Esito platform
  docs e verifica semantica registrati nel checkpoint finale.

Comandi principali dalla root:

```bash
COVERAGE_FILE=/tmp/gaia-network-device-assignee-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-device-assignee-refactor-20261117/test-after.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_api.py backend/tests/test_network_router_helpers.py backend/tests/test_network_device_bulk.py backend/tests/test_network_device_assignee.py --junitxml=/tmp/gaia-network-device-assignee-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-network-device-assignee-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/routes/devices.py' -o /tmp/gaia-network-device-assignee-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-device-assignee-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-device-assignee-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/routes/devices.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-patch-openai-base-url
make graphify-platform-docs
```

## Stato e prossima azione

HEAD iniziale `8f65d353c7ecbf9d055dcecd564b617c6278cf6e`. Il runtime applicato
coincide con il candidato verificato. Hash delle altre slice, baseline, eccezioni
e report condivisi preservati; nessuna modifica a soglie, scope o matcher.
Modifiche concorrenti Communications, Ruolo e frontend preservate. Nessun
commit/push/merge/deploy o secondo hotspot avviato.

Dalla ripresa 23 slice: −21 Error, −24 Warning, −140 cognitiva aggregata.
Snapshot corrente 1.897 Error/2.949 Warning; programma generale ancora aperto.
Prossima azione: review del delta, poi selezione di un altro hotspot dal report.
