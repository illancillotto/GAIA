# Matching soggetti tracciati Network — 2026-11-17

Esito **IMPROVED**: due Error eliminati in
`backend/app/modules/network/router/helpers/tracking.py`, nessun Warning aggiunto.

## Modifica e invarianti

`_match_tracked_subject_against_event` mantiene il dispatch e la verifica del
dominio; quattro helper isolano matching dispositivo, matching IP, matching URL
e candidato dominio. Tutti restano sotto soglia. Quindici altri callable hanno
AST identico, inclusa la precedente normalizzazione; sedici firme preesistenti
invariate. API, DB, auth e transazioni non cambiano.

Il matching dispositivo richiede ancora subject.device_id truthy e confronta
nell'ordine ID, IP sorgente, IP destinazione. La lettura ripetuta dell'ID e del
valore non viene anticipata o accorpata. Nel matching IP la sorgente precede la
destinazione, la comparazione resta letterale e normalized_value viene riletto
per il ritorno. Anche i valori vuoti/None conservano il comportamento originale.

Il dominio esplicito non vuoto precede l'hostname URL; un dominio esplicito che
non coincide non fa provare l'URL. I punti finali del dominio non vengono tolti:
questa regola resta distinta dalla normalizzazione del valore tracciato. Get,
doppie strip e lower mantengono ordine, numero e risultati. Il matching URL
confronta soltanto il testo stripped, senza parsing o case-folding; il secondo
risultato strip, anche se falsy, viene restituito. Errori parser/hostname/get e
attributi ORM mantengono propagazione e confini di short-circuit.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Dispatcher: cognitiva | 50 | 10 |
| Dispatcher: ciclomatica | 27 | 8 |
| Dispatcher: LOC | 33 | 18 |
| Dispatcher: nesting | 3 | 2 |
| Cognitiva aggregata file | 250 | 235 |
| Ciclomatica aggregata file | 157 | 161 |
| Somma cyclomatic meno 1 | 141 | 141 |
| LOC file | 472 | 486 |
| Callable | 16 | 20 |
| Error | 8 | 6 |
| Warning | 4 | 4 |

Helper cyclomatic/cognitive/LOC/nesting: device7/8/6/1, IP3/2/8/1,
URL4/4/7/1, candidato dominio9/11/8/1. Tutti sotto soglia. Il file resta sotto
500LOC; i quattro punti ciclomatici aggiunti corrispondono ai quattro nuovi
callable, senza crescita delle decisioni aggregate. Cognitiva ridotta di15,
nessuna violation trasferita. Residuo: sei Error e quattro Warning in timeline
ARP, riconciliazione e riepilogo attivita, fuori slice e invariati.

## Verifiche

Artefatti `/tmp/gaia-network-tracked-matching-refactor-20261117/`.
Nuovo test `backend/tests/test_network_tracked_matching.py`.

- 160test PASS prima/dopo:18helper router,50API Network,49normalizzazione e43
  nuovi matching; zero skip/failure/error, XML/log della slice.
- Coverage full-file statement/branch100%:251/251→260/260 statement,
  108/108branch invariati; zero esclusioni/missing/partial branch.
- Differenziale25000scenari equivalente per risultati, eccezioni, trace degli
  attributi subject/event, get/strip dei payload e parser URL. Include errori
  iniettati alle singole letture, valori malformati e IP vuoti/None.
- Dieci contratti aggiuntivi prima/dopo su short-circuit, letture ripetute,
  valore strip falsy e propagazione errori hostname, tutti equivalenti.
- Quattro mutanti in memoria respinti: IDzero ammesso, destinazione prima,
  punto finale dominio tolto, seconda strip URL rimossa. ModuleType e globals
  condivisi; nessun mutante applicato al runtime su disco.
- Ratchet mirato origin/main PASS prima/dopo contro baseline autorevole
  merge-base `686e529ee011487e0764b9f91d023be063dbdf55`.
- Ratchet globale exit2 per la stessa ambiguita Tributi gia registrata prima
  della slice: `useEffect[0]<callback>` in `frontend/src/app/ruolo/tributi/page.tsx`,
  dieci candidati. Il gate globale resta aperto; nessuna modifica al matcher.
- Report completi1960file: Error1907→1905, Warning2958 invariati,
  callable22611→22615. Solo tracking.py varia metriche; nessun errore di parsing
  o eccezione configurata. Dalla ripresa dodici slice: -13Error/-15Warning e
  -75cognitiva aggregata. Nessuna percentuale storica di completamento dedotta.
- Ruff runtime/test, format nuovo test, lint-backend233file e diff-check PASS.
  Nessun test preesistente modificato, rimosso o indebolito.
- Graphify Network e platform docs aggiornati tramite Make; numeri e log
  semantici nel checkpoint della slice.
- Ripresa: candidato e runtime finale identici byte per byte; rieseguiti
  differenziale, contratti aggiuntivi e quattro mutanti, tutti con esito atteso.

Comandi principali dalla root, con file coverage distinti prima/dopo:

```bash
COVERAGE_FILE=/tmp/gaia-network-tracked-matching-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-tracked-matching-refactor-20261117/test.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_tracked_normalization.py backend/tests/test_network_tracked_matching.py
COVERAGE_FILE=/tmp/gaia-network-tracked-matching-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/tracking.py' -o /tmp/gaia-network-tracked-matching-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-tracked-matching-refactor-20261117/differential.py
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
