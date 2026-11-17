# OID SNMP personalizzati — 2026-11-17

Esito **IMPROVED**: due Warning eliminati in
`backend/app/modules/network/sophos_snmp.py`.

## Modifica e invarianti

`_load_custom_oids` conserva lettura della configurazione e JSON, poi delega la
normalizzazione della singola voce a `_normalize_custom_oid`. JSON non valido
o forma diversa da lista restituiscono ancora una lista vuota; gli elementi
non dict o con key/oid non stringa o vuoti vengono ignorati. Ordine e duplicati
restano intatti, compresi OID con la stessa key.

Le due strip per key/oid e le letture ripetute di mode/unit mantengono ordine,
numero e secondo risultato, anche se falsy o di tipo inatteso. Default mode
`text` e unit None, valori stringa vuoti accettati per mode/unit, eccezioni di
lettura dopo il JSON e input non mutati restano invariati. Gli otto altri
callable hanno AST identico; nove firme preesistenti preservate. Polling,
trasporto SNMP, persistenza, API, DB, auth e transazioni non cambiano.

Per rendere conforme il file toccato al ratchet Ruff sono stati ordinati gli
import, rimosso l'import inutilizzato NetworkFirewall e usato datetime.UTC
invece dell'assegnazione timezone.utc. L'identita dell'oggetto UTC e verificata
nel confronto originale/corrente. Nessuna riformattazione dei callable legacy.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Loader: cognitiva | 21 | 7 |
| Loader: ciclomatica | 13 | 6 |
| Loader: LOC | 23 | 13 |
| Loader: nesting | 2 | 2 |
| Cognitiva aggregata file | 75 | 70 |
| Ciclomatica aggregata file | 61 | 63 |
| Somma cyclomatic meno 1 | 52 | 53 |
| LOC file | 178 | 188 |
| Callable | 9 | 10 |
| Error | 1 | 1 |
| Warning | 4 | 2 |

L'helper ha cyclomatic/cognitive/LOC/nesting 9/9/13/1, sotto tutte le soglie.
Due punti ciclomatici aggiunti: baseline del nuovo callable e controllo sul
risultato opzionale; le decisioni aggregate aumentano di uno. Crescita
esplicitata, nessuna nuova violation: cognitiva aggregata ridotta di cinque,
due finding rimossi. Restano un Error sui nove parametri di record metric e
due Warning ciclomatici nei metodi async SNMP e polling, fuori slice e invariati.

## Verifiche

Artefatti `/tmp/gaia-network-custom-oids-refactor-20261117/`.
Nuovo test `backend/tests/test_network_sophos_snmp.py`.

- 133 test PASS prima/dopo, zero skip/failure/error: servizi Network, tutti
  i 50 test API Network e nuove caratterizzazioni SNMP/OID.
- Coverage full-file statement/branch100%, senza esclusioni, missing o branch
  parziali; numeri e XML nei file della slice.
- Differenziale deterministico su 20000 configurazioni: zero differenze di
  output ordinato, eccezioni, JSON, get/strip; input non mutati. Quattordici
  contratti aggiuntivi sui secondi risultati e get ripetute prima/dopo PASS.
- Tre mutanti in memoria respinti: deduplica per key, singola strip sulla key,
  lettura unica della mode. ModuleType con globals condivisi; nessun mutante
  applicato al runtime su disco.
- Test full-file: trasporto async sostituito, timeout/retry/OID mapping ed errori;
  wrapper sync; severity/coercion; add/flush, fallback host e commit del polling;
  filtri/ordine listing e chiusura sessione prima dello sleep. Nessuna rete o
  persistenza di produzione usata, nessun test preesistente indebolito.
- Ratchet mirato origin/main PASS prima/dopo contro baseline autorevole
  merge-base `686e529ee011487e0764b9f91d023be063dbdf55`.
- Ruff runtime/test e format nuovo test PASS; lint-backend230 file PASS.
- Graphify Network Make aggiornato: 458 nodi, 1158 archi, 20 comunita.
  Esito platform docs nei log/checkpoint della slice.

Comandi principali dalla root, con file coverage distinti prima/dopo:

```bash
COVERAGE_FILE=/tmp/gaia-network-custom-oids-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-custom-oids-refactor-20261117/test.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_services.py backend/tests/test_network_api.py backend/tests/test_network_sophos_snmp.py
COVERAGE_FILE=/tmp/gaia-network-custom-oids-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/sophos_snmp.py' -o /tmp/gaia-network-custom-oids-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-custom-oids-refactor-20261117/differential.py
python3 tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/sophos_snmp.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-platform-docs
```

## Stato del checkout

HEAD iniziale `ce9968b65a1b8a6fe94d061f265df2623e9a4555`. Baseline, soglie,
scope ed eccezioni intatti; baseline non sincronizzata nel checkout concorrente
e baseline-verify non eseguito. Report condivisi preesistenti preservati.
Nessun commit, push, merge o deploy eseguito. Nessun secondo hotspot avviato.

Report completi1960file, callable22609→22610, Error1907 invariati,
Warning2962→2960. Unico path con metriche variate sophos_snmp.py. Ratchet
globale exit2 per identica ambiguita `useEffect[0]<callback>` in
`frontend/src/app/ruolo/tributi/page.tsx`, dieci candidati; gate globale non
certificato verde. Dalla ripresa dieci slice: undici Error e tredici Warning
eliminati, cognitiva aggregata ridotta di 57.
