# Riepilogo VPN bypass Network — 2026-11-17

Esito **IMPROVED**: tre Error eliminati, cognitiva aggregata 96→82 e decisioni
66→58 in `backend/app/modules/network/router/routes/tracking.py`. Nessuna
violation trasferita; route e tre helper sotto tutte le soglie.

## Modifica e invarianti

`get_vpn_bypass_summary` coordina la richiesta: autorizzazione, seed watchlist,
lista soggetti con le stesse opzioni, accumulo per soggetto, conteggi DB e
risposta. Tre responsabilita ora hanno confini espliciti:

- `_accumulate_bypass_subject` aggiorna i contatori. Un soggetto incrementa
  ogni categoria positiva indipendentemente dal numero di eventi e dalle
  altre categorie; solo suspicious positivo contribuisce al totale sospetti.
- `_get_bypass_alert_counts` esegue le sei letture nell'ordine originale e
  restituisce i campi della risposta relativi ad alert e watchlist.
- `_count_open_bypass_alerts` condivide il SELECT e il filtro status=open
  ripetuti cinque volte, conservando i predicati specifici IN ed uguaglianza.

La query watchlist resta senza filtro di stato. SQL compilati PostgreSQL e
parametri, ordine delle query e fallback scalar or 0 sono identici. Nessuna
query viene accorpata, anticipata rispetto alle attivita o trasformata in una
nuova transazione. Auth, seed e lista soggetti mantengono ordine e argomenti.

Il fallback activity conserva window_hours e truthiness. Le letture ripetute
di suspicious_events per guardia e totale non vengono accorpate; gli errori
nei getter continuano a precedere tutte le query. Errori su auth/seed/lista,
una delle sei query e costruzione risposta interrompono lo stesso flusso.
Nessun nuovo commit, rollback o retry. API, schema, auth e altre route invariati.

Otto altri callable hanno AST identico; nove firme, return e decorator e nove
contratti route sono preservati. Il loop resta equivalente dopo il mapping
dei contatori a chiavi del dizionario. Espandendo il SELECT comune, gli AST
delle sei query coincidono con gli originali. I campi della risposta sono
gli stessi, con lo stesso mapping ai contatori e ai risultati SQL.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Route: cognitiva | 26 | 1 |
| Route: ciclomatica | 21 | 2 |
| Route: LOC | 86 | 36 |
| Route: nesting | 2 | 1 |
| Cognitiva file | 96 | 82 |
| Ciclomatica file | 75 | 70 |
| Somma cyclomatic meno 1 | 66 | 58 |
| Callable | 9 | 12 |
| LOC file | 367 | 376 |
| Densita | 0,465940 | 0,404255 |
| Error | 6 | 3 |
| Warning | 3 | 3 |

Helper cognitive/cyclomatic/LOC/nesting: accumulo `7/8/15/1`, tre parametri;
collector `2/3/36/0`, un parametro; query comune `2/3/7/0`, due parametri.
Il calo delle decisioni aggregate deriva dalla deduplica del SELECT e del
fallback ripetuto, senza cambiare numero o comportamento delle query.

## Verifiche

Artefatti `/tmp/gaia-network-vpn-summary-refactor-20261117/`.
Nuovo `backend/tests/test_network_vpn_summary.py`: 20 casi.

- 88 test PASS prima/dopo: 50 API Network, 18 helper e 20 nuovi. Zero
  skip/failure/error nei due XML; nessun test esistente modificato.
- Runtime full-file statement/branch 100%: prima 174/174 statement e 52/52
  branch, dopo 177/177 e 52/52; zero esclusioni, missing o branch parziali.
- 4.000 scenari differenziali equivalenti per risposta completa, eccezioni,
  SQL e parametri ordinati, stato dei getter, trace auth/seed/lista/iterazione/
  default/letture/bool/query/response. Include valori negativi e nulli, oggetti
  falsey, letture variabili e errori iniettati lungo il flusso.
- Sei mutanti in memoria respinti dai nuovi test: suspicious letto una sola
  volta (1 failure), categorie indipendenti saltate (2), eventi al posto dei
  soggetti (1), alert chiusi inclusi (1), un tipo alert mancante (1), None
  senza fallback scalar a zero (1). Nessun collection error o skip; nessun
  mutante applicato al checkout.
- Ratchet mirato origin/main PASS prima/dopo; merge-base
  `686e529ee011487e0764b9f91d023be063dbdf55`. Globale exit 2 per la stessa
  ambiguita preesistente Tributi useEffect[0]<callback>, dieci candidati.
  Nessun PASS globale, baseline sync o baseline-verify dichiarato.
- Report completi 1.963 file, callable 22.638→22.641, Error 1.897→1.894,
  Warning 2.947 invariati; cambia solo routes/tracking.py. Zero parse/exception
  error; report condivisi, baseline, scope, soglie, eccezioni e matcher intatti.
- Ruff runtime/test, format nuovo test, lint-backend 255 file e diff-check PASS.
  Nessuna nuova failure applicativa; 98 warning JWT API preesistenti.
- Graphify Network aggiornato tramite Make: 489 nodi/1.223 archi. Platform
  docs e verifica chunk/warning semantici nel checkpoint finale.
- Runtime finale uguale al candidato caratterizzato; hash delle altre slice,
  baseline e report condivisi preservati. Modifiche concorrenti intatte.

Comandi principali dalla root:

```bash
COVERAGE_FILE=/tmp/gaia-network-vpn-summary-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-vpn-summary-refactor-20261117/test-after.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_api.py backend/tests/test_network_router_helpers.py backend/tests/test_network_vpn_summary.py --junitxml=/tmp/gaia-network-vpn-summary-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-network-vpn-summary-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/routes/tracking.py' -o /tmp/gaia-network-vpn-summary-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-vpn-summary-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-vpn-summary-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/routes/tracking.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-patch-openai-base-url
make graphify-platform-docs
```

## Stato e prossima azione

HEAD iniziale `743b21c132b19c82d1201f93b59a541a3b28269a`. Singolo hotspot
completato; nessun commit/push/merge/deploy o secondo hotspot avviato.
Restano nel file tre Error e tre Warning nelle altre route, in particolare
creazione tracking, parametri e LOC della lista. Nessuna loro modifica.

Dalla ripresa 25 slice migliorative: −24 Error, −26 Warning, −157 cognitiva
aggregata. Snapshot corrente 1.894 Error/2.947 Warning; goal generale ancora
attivo. Prossima azione: review del delta, poi selezione di un altro hotspot
con ownership libera e riduzione effettiva.
