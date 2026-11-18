# Applicazione campi bulk dispositivi Network — 2026-11-17

Esito **IMPROVED**: due Warning eliminati e cognitiva aggregata37→32 in
`backend/app/modules/network/router/routes/devices.py`. Nessuna violation
trasferita; restano l'Error parametri di get_devices e il Warning di patch_device.

## Modifica e invarianti

`_apply_device_bulk_fields` contiene gli stessi tre if prima nel ciclo di
bulk_update_devices: known, location e note. La route conserva autorizzazione,
query ordinata per IP, 404 senza dispositivi, preparazione note, ciclo e risposta.

None mantiene i valori; False aggiorna known; location vuota diventa None,
mentre whitespace resta tale. Le note vengono strip una volta prima del ciclo;
contenuto interno e letture ripetute di payload e device.notes restano invariati.
L'helper non contiene query, alert, commit o serializzazione.

Per ogni dispositivo: setter nello stesso ordine, sync alert, add. Seguono
un unico commit, tutti i refresh nello stesso ordine della query, poi tutte
le serializzazioni. Errori e stato parziale mantengono lo stesso comportamento;
la route non introduce rollback o retry. Auth, API, schema e transazioni restano
invariati. Sei altri callable hanno AST identico; sette firme, return annotation,
decorator e contratti delle route sono preservati.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Bulk: cognitiva | 18 | 5 |
| Bulk: ciclomatica | 12 | 6 |
| Bulk: LOC | 28 | 23 |
| Bulk: nesting | 2 | 1 |
| Cognitiva file | 37 | 32 |
| Ciclomatica file | 33 | 34 |
| Somma cyclomatic meno 1 | 26 | 26 |
| Callable | 7 | 8 |
| LOC file | 191 | 195 |
| Error | 1 | 1 |
| Warning | 3 | 1 |

Helper cognitive/cyclomatic/LOC/nesting8/7/9/1, tre parametri, sotto soglia.
Crescita ciclomatica pari al callable aggiunto, decisioni aggregate invariate.
Nessuna riformattazione delle route o modifica opportunistica di patch_device.

## Verifiche

Artefatti `/tmp/gaia-network-device-bulk-refactor-20261117/`.
Nuovo `backend/tests/test_network_device_bulk.py`:24casi.

- 92test PASS prima/dopo:50API Network,18helper e24nuovi casi. Entrambi gli
  XML con zero skip/failure/error; nessun test esistente modificato o indebolito.
- Full-file statement/branch100% prima92/92statement e30/30branch,
  dopo94/94 e30/30; zero esclusioni, missing e branch parziali.
- Differenziale8000scenari equivalente per risposta completa ordinata, SQL,
  eccezioni, stato parziale dei dispositivi e trace auth/setattr/sync/add/
  commit/refresh/serialize/letture ORM e payload. Include getter variabili,
  None/False/vuoti, note whitespace, refresh che cambia il dato ed errori
  iniettati alle singole operazioni. Body helper AST identico al blocco originale.
- Cinque mutanti in memoria respinti: False ignorato, location vuota ignorata,
  lettura payload accorpata, commit per dispositivo e strip note omessa.
  Nessun mutante applicato al runtime su disco.
- Ratchet mirato origin/main PASS prima/dopo, zero finding; merge-base
  `686e529ee011487e0764b9f91d023be063dbdf55`. Globale exit2 per la stessa
  ambiguita preesistente Tributi `useEffect[0]<callback>`, dieci candidati.
  Nessuna modifica baseline/soglie/scope/eccezioni/matcher e nessun PASS globale.
- Report completi1963file:22635→22636callable, Error1897 invariati,
  Warning2952→2950; cambia solo routes/devices.py, zero parse/exception error.
  Il nuovo file Communications rispetto al report della slice precedente
  era gia presente nel report prima e non fa parte di questa modifica.
- Ruff runtime/test, format nuovo test, lint-backend249file e diff-check PASS.
  Nessuna nuova failure applicativa;98warning JWT API preesistenti.
- Graphify Network Make484nodi/1210archi; platform docs e verifica semantica
  registrati nel checkpoint finale.

Comandi principali dalla root:

```bash
COVERAGE_FILE=/tmp/gaia-network-device-bulk-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-device-bulk-refactor-20261117/test-after.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_api.py backend/tests/test_network_router_helpers.py backend/tests/test_network_device_bulk.py --junitxml=/tmp/gaia-network-device-bulk-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-network-device-bulk-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/routes/devices.py' -o /tmp/gaia-network-device-bulk-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-device-bulk-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-device-bulk-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/routes/devices.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-platform-docs
```

## Stato e prossima azione

HEAD iniziale `8f65d353c7ecbf9d055dcecd564b617c6278cf6e`. Runtime finale uguale
al candidato verificato; hash delle slice precedenti, baseline e report condivisi
preservati. Modifiche concorrenti Communications/Ruolo/frontend non toccate.
Nessuna sync baseline o baseline-verify dichiarata, nessun commit/push/merge/deploy
eseguito da questo turno. Nessuna seconda slice avviata.

Dalla ripresa ventidue slice: -21Error/-23Warning/-140cognitiva aggregata.
Snapshot corrente1897Error/2950Warning; obiettivo generale ancora attivo.
Prossima azione: review del delta, poi selezione di un altro hotspot dal report.
