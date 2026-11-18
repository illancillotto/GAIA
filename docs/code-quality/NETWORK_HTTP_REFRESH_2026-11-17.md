# Meta refresh HTTP Network — 2026-11-17

Esito **IMPROVED**: `_resolve_http_metadata` perde un Error nesting e un
Warning LOC; cognitiva aggregata services.py 644→633. Il file gia sopra la
soglia LOC diminuisce da 1.451 a 1.448 righe, senza spostare debito nell'helper.

## Modifica e invarianti

`_follow_http_meta_refresh` possiede soltanto il tentativo del secondo GET,
la verifica status<500 e gli aggiornamenti response/body con fallback Exception.
La selezione dichiarativa degli endpoint mantiene i test membership nell'ordine
80/443; il caso senza candidati raggiunge lo stesso costruttore finale vuoto.

Client, with ed except esterni restano nel resolver. Base URL, destinazione
relativa/assoluta, User-Agent, verify=False, follow_redirects e timeout sono
identici. Il primo successo ritorna anche se la pagina e vuota; non si tenta
HTTPS solo per assenza di metadati. La classificazione resta dopo il close.

Se la lettura del body del refresh fallisce con Exception, la nuova response
resta selezionata mentre il body precedente viene mantenuto, come prima.
BaseException continua a propagarsi attraverso il cleanup del client. Il
contratto del Client.__exit__ installato e stato letto e salvato negli artefatti:
non sopprime gli errori; le simulazioni rispettano questo contratto runtime.

Sessantacinque altre funzioni top-level, gli import e lo stato modulo hanno
AST identico. Espandendo l'helper e normalizzando i candidati letterali ordinati
e la guardia vuota ridondante si ricostruisce l'AST originale del target.
Nessuna modifica a chiamanti, API, schema, auth o transazioni.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Target cognitiva | 44 | 28 |
| Target ciclomatica | 20 | 15 |
| Target LOC | 57 | 45 |
| Target nesting | 5 | 3 |
| Cognitiva file | 644 | 633 |
| Ciclomatica file | 482 | 481 |
| Callable | 67 | 68 |
| Decisioni (somma cyclomatic meno 1) | 415 | 413 |
| LOC file | 1.451 | 1.448 |
| Densita | 0,776017 | 0,769337 |
| Error file/callable | 18 | 17 |
| Warning | 14 | 13 |

Helper cognitive/cyclomatic/LOC/nesting `5/4/9/2`, quattro parametri, zero
violation. Restano Error cognitive/cyclomatic del resolver e LOC del file,
oltre al debito negli altri servizi: nessuno viene assorbito nella baseline.

## Verifiche

Artefatti `/tmp/gaia-network-http-refresh-refactor-20261117/`.

- Intera suite Network: 1.131 test PASS prima/dopo, compresi 27 nuovi in
  `test_network_http_refresh.py`; zero failure/error/skip. Test esistenti intatti.
- Coverage full-file statement/branch 100% secondo la configurazione esistente:
  prima 807/807 statement e 290/290 branch, dopo 804/804 e 284/284. Zero
  missing/partial. Le dieci righe import opzionali legacy gia escluse restano
  identiche; nessuna nuova esclusione o modifica alla configurazione coverage.
- 4.000 confronti equivalenti: risultato, richieste e argomenti, ordine,
  chiusura client, stato parziale response/body, parsing, consumo porte e
  Exception/BaseException. Include 499/500, target relativi/assoluti, errori
  GET/text/status/exit/parse, dipendenza assente e iteratori che falliscono.
- Sei mutanti in memoria respinti senza collection error/skip: status500
  accettato (2 failure), cancellazione soppressa (2), response non sostituita
  (5), precedenza HTTPS (12), consumo porte senza httpx (1), secondo tentativo
  dopo successo vuoto (1). Nessun mutante applicato ai file condivisi.
- Ruff runtime/test, format-check nuovo test, lint-backend 262 file e diff-check
  PASS. Ratchet scoped origin/main PASS prima/dopo, merge-base `686e529e`.
- Globale exit 2 sulla stessa ambiguita Tributi useEffect[0]<callback>, dieci
  candidati. Blocco precedente alla slice, audit peer HEAD Tributi PASS/WIP2;
  nessun PASS globale, baseline sync o baseline-verify dichiarato.
- Report completi 1.963 file, callable 22.646→22.647, Error 1.891→1.890,
  Warning 2.945→2.944. Solo services.py cambia, zero parse/exception error;
  before identico al completo finale scan history precedente.
- Baseline/scope/soglie/eccezioni/matcher/report condivisi e WIP estranei
  preservati. Candidato uguale ai byte finali; nessuna nuova failure applicativa.
- Graphify Network Make 495 nodi/1.238 archi; platform docs e verifica chunk/
  warning nel checkpoint finale, nessun graphify-out versionato.

Comandi principali dalla root:

```bash
COVERAGE_FILE=/tmp/gaia-network-http-refresh-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-http-refresh-refactor-20261117/test-after.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network*.py --junitxml=/tmp/gaia-network-http-refresh-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-network-http-refresh-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/services.py' -o /tmp/gaia-network-http-refresh-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-http-refresh-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-http-refresh-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/services.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-patch-openai-base-url
make graphify-platform-docs
```

## Stato

HEAD iniziale `743b21c132b19c82d1201f93b59a541a3b28269a`. Una sola unita
conclusa; nessun secondo hotspot, commit/push/PR/merge/deploy. Audit peer
storico e coordinamento chiuso; nessun messaggio ordinario al thread inattivo.

Dalla ripresa 29 slice migliorative, −28 Error, −29 Warning e −201 cognitiva
aggregata tool. Snapshot attuale 1.890 Error/2.944 Warning; goal generale
attivo. Prossima azione review e nuova selezione alla continuazione.
