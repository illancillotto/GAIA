# Risposta WHOIS Network — 2026-11-17

Esito **IMPROVED**: due Error e un Warning eliminati da
`backend/app/modules/network/router/helpers/devices.py`, sulla versione
gia verificata dalla precedente slice dei nomi RDAP.

## Modifica e comportamento

Il flusso WHOIS mantiene classificazione dell'IP e recupero remoto, poi passa
il payload a `_rdap_response`. La risposta condivide `_rdap_text` per nome,
handle e paese e usa `_rdap_address_range` per l'intervallo CIDR. Questi sono
confini del formato RDAP: nessun wrapper aggiunto per rinominare debito.

La classificazione conserva la precedenza private, loopback, link-local.
URL, timeout di quattro secondi, gestione del context manager e lettura JSON
restano identici. Gli errori di rete/JSON conservano il loro confine: un errore
sollevato leggendo un campo dopo il caricamento non viene intercettato come
indisponibilita remota. Anche JSON valido di forma inattesa propaga gli errori
originali. Nessuna nuova validazione o fallback viene introdotta.

Intervalli validi IPv4/IPv6 producono gli stessi CIDR nello stesso ordine;
intervalli invertiti/invalidi mantengono la risposta originale. Un intervallo
misto IPv4/IPv6 continua a propagare TypeError. I campi testuali non vengono
trimmati: restano due get quando il primo restituisce una stringa, uno negli
altri casi. Cosi restano identiche anche le letture di un dict personalizzato.
Sei callable esterni alla slice hanno AST invariato; sette firme preesistenti
identiche. Nessuna modifica a API, auth, query, transazioni o schema.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| WHOIS: ciclomatica | 20 | 8 |
| WHOIS: cognitiva | 27 | 9 |
| WHOIS: LOC / nesting | 68 / 3 | 41 / 2 |
| File: cognitiva | 57 | 55 |
| File: ciclomatica | 53 | 54 |
| Somma di cyclomatic meno 1 | 46 | 44 |
| LOC file | 192 | 203 |
| Callable | 7 | 10 |
| Error | 2 | 0 |
| Warning | 2 | 1 |

Nuovi helper cyclomatic/cognitive/LOC/nesting:

- Intervallo CIDR: 7/12/8/3, due parametri.
- Campo testuale: 2/1/2/0, due parametri.
- Risposta RDAP: 4/3/28/0, tre parametri.

Tutti sono sotto soglia. La lettura testuale condivisa elimina decisioni
duplicate; le decisioni aggregate diminuiscono anche contando tutti i nuovi
callable. Nessuna violation trasferita. Residuo: `_serialize_device`, LOC 55,
un Warning preesistente non modificato.

## Verifiche

Nuovo test `backend/tests/test_network_whois_response.py`.
Artefatti privati `/tmp/gaia-network-whois-refactor-20261117/`.

- 141 test PASS prima/dopo, zero skip, errori o failure: 18 helper router,
  50 API Network, 37 caratterizzazioni nomi RDAP e 36 nuove prove WHOIS.
- Runtime full-file 100% statement/branch: 77/77 statement prima e 84/84
  dopo; 28/28 branch invariati. Zero esclusioni, missing o branch parziali.
- Prima esecuzione: 140 PASS/1 FAIL per il nuovo test che attendeva la regex
  `same IP version`; il messaggio reale e `same version`. Corretto solo il
  testo atteso, poi ripetuta tutta la suite sul runtime originale (141 PASS)
  prima di applicare il refactor. Log e JUnit iniziali preservati.
- Differenziale prima/applicato: 10000 casi, zero differenze nei risultati,
  eccezioni, chiamate remote, gestione JSON e trace delle letture. Copre
  campi malformati, intervalli, IP pubblici/privati/invalidi e IPv6 espanso.
  Nessuna mutazione degli input; tutte le chiamate remote sono sostituite.
- Quattro esecuzioni di contratti sul vecchio e nuovo flusso provano letture
  ripetute e confine dell'errore di accesso al payload. Due mutanti in memoria
  respinti: get testuale unico e inversione CIDR; runtime non alterato.
- Ratchet del file contro `origin/main` PASS prima/dopo; merge-base `686e529e`.
- Ruff, format del nuovo test, lint-backend su 222 file e diff-check PASS.
- Graphify Network aggiornato tramite Make: 444 nodi, 1124 archi, 17 comunita.

Comandi principali dalla root, con file coverage/JUnit distinti prima/dopo:

```bash
COVERAGE_FILE=/tmp/gaia-network-whois-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_rdap_names.py backend/tests/test_network_whois_response.py --junitxml=/tmp/gaia-network-whois-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-network-whois-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/devices.py' -o /tmp/gaia-network-whois-refactor-20261117/coverage-after.json --fail-under=100
python3 tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/devices.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
```

## Checkout e limiti

SHA iniziale `82bda86882d9fd8c29955a8f750c54abca8fdb20`; hash SHA256 della
versione prima di questa slice, comprensiva del precedente lavoro RDAP:
`58e99f689b8d3947232963e8df04ad96277f9b90d8728e9c0803296b84b4fb3b`.

Baseline, soglie, scope ed eccezioni invariati; baseline non sincronizzata
nel checkout concorrente e baseline-verify non eseguito. I report completi
prima/dopo hanno lo stesso perimetro di 1960 file: Error 1916→1914, Warning
2967→2966, callable 22593→22596. Il solo path con metriche cambiate e il
servizio interessato. Il perimetro comprende i test worker: nessuna percentuale
storica dedotta da confronti fra corpus differenti.

Il ratchet globale resta exit 2 per `ambiguous_identity` preesistente di
`useEffect[0]<callback>` in `frontend/src/app/ruolo/tributi/page.tsx`, dieci
candidati. Nessuna modifica al matcher o alle soglie per aggirare il problema.
Report condivisi e modifiche concorrenti preservati. Nessun commit, push,
merge o deploy; una sola responsabilita modificata in questa iterazione.
