# Proiezione elementi timeline ARP Network — 2026-11-17

Esito **IMPROVED**: tre Error eliminati e cognitiva aggregata221→208 sui due
runtime coinvolti. Il builder e tutti i callable del nuovo modulo sono sotto
soglia. Resta distinto il debito del riepilogo attivita, invariato.

## Modifica e invarianti

`network/router/helpers/tracking.py` conserva query, finestra temporale,
raggruppamento per scope, caricamento dispositivi, ranking stabile e limite.
`helpers/arp_timeline.py` costruisce il singolo elemento della timeline:
ordinamento osservazioni, indirizzi distinti, anomalie, label, contatori e
dettagli. Gli helper temporali della slice precedente mantengono AST e firme
e sono re-esportati da tracking per conservare l'accesso ai simboli.

Il resolver della label viene passato dal builder: resta patchabile dalla
stessa ownership. Le letture delle osservazioni mantengono ordine e numero,
inclusi gli accessi ripetuti a status, ID, indirizzi e timestamp. I contatori
presenza vengono valutati nella posizione originale dei campi risposta,
dopo osservazioni_count. Non vengono anticipati prima della risoluzione label.

Restano sorting per timestamp/ID discendenti, ordine degli indirizzi distinti,
pareggi dei Counter, timestamp UTC solo nel confronto, sei dettagli al massimo,
label corrente o fallback display_name/hostname/IP e IDzero. API, auth,
query, errori, schema, transazioni e risposta non cambiano.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Builder: cognitiva | 35 | 7 |
| Builder: ciclomatica | 22 | 7 |
| Builder: LOC | 83 | 42 |
| Builder: nesting | 1 | 1 |
| Cognitiva aggregata | 221 | 208 |
| Ciclomatica aggregata | 164 | 167 |
| Somma cyclomatic meno 1 | 141 | 141 |
| LOC aggregate | 498 | 542 |
| Callable | 23 | 26 |
| Error | 6 | 3 |
| Warning | 1 | 1 |

File finali: tracking444LOC/cognitiva174, arp_timeline98LOC/cognitiva34.
Proiezione cognitive/cyclomatic/LOC/nesting8/9/46/0; label5/6/13/0;
conteggi2/3/5/0; riapparizioni13/7/14/3; motivi6/6/14/1.
Tutti sotto soglia, nessun debito trasferito. Crescita LOC dichiarata,
comprende wrapping dei nuovi file e re-export; le decisioni aggregate non
diminuiscono. Residuo: riepilogo attivita68/32/133/4, tre Error e un Warning.

## Verifiche

Artefatti `/tmp/gaia-network-arp-projection-refactor-20261117/`.
Nuovo test `backend/tests/test_network_arp_projection.py`, otto casi.

- 225test PASS sul codice originale, sul candidato e sul runtime finale:
  18helper,50API,49normalizzazione,43matching,38riconciliazione,19anomalie ARP
  e8proiezione. Tre XML con zero skip/failure/error.
- Full-file statement/branch100%: prima tracking268/268statement e108/108branch;
  finale tracking242/242 e96/96, arp_timeline41/41 e12/12. Zero esclusioni,
  missing e branch parziali. Non semplice coverage delle righe cambiate.
- Differenziale6000timeline equivalente per intera risposta ordinata, errori,
  SQL/clock e trace ordinato degli accessi alle osservazioni e alle label.
  Ventidue altri AST e ventitre firme preservati, inclusi helper ricollocati.
- Cinque mutanti solo in memoria respinti: presenza letta prima della label,
  tie-break ID rimosso, hostname dello snapshot al posto della label dettagli,
  display_name saltato nel fallback e contatore offline omesso.
- Ratchet mirato origin/main PASS prima/dopo/finale, zero finding; baseline
  autorevole merge-base `686e529ee011487e0764b9f91d023be063dbdf55`.
  Globale exit2 per la stessa ambiguita preesistente in Tributi:
  `useEffect[0]<callback>`, dieci candidati. Nessun PASS globale rivendicato.
- Report completi1960→1961file,22622→22625callable, Error1903→1900,
  Warning2953 invariati. Cambiano solo i due runtime della slice; nessun errore
  di parsing o di eccezioni. Nessuna modifica dei report condivisi.
- Primo lint FAIL I001 sui re-export; Ruff ha separato gli import senza
  cambiare gli AST non-import. Suite/coverage/metriche/ratchet e lint finali
  ripetuti sul runtime finale. Lint-backend241file e formato file nuovi PASS.
  La suite API conserva98warning JWT sulla chiave sintetica corta.
- Graphify Network e platform docs aggiornati mediante target Make dedicati;
  conteggi finali e verifica chunk semantici registrati nel checkpoint.

Comandi principali dalla root:

```bash
COVERAGE_FILE=/tmp/gaia-network-arp-projection-refactor-20261117/.coverage-final DATABASE_URL=sqlite:////tmp/gaia-network-arp-projection-refactor-20261117/test-final.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_tracked_normalization.py backend/tests/test_network_tracked_matching.py backend/tests/test_network_legacy_reconciliation.py backend/tests/test_network_arp_timeline.py backend/tests/test_network_arp_projection.py --junitxml=/tmp/gaia-network-arp-projection-refactor-20261117/tests-final.xml
COVERAGE_FILE=/tmp/gaia-network-arp-projection-refactor-20261117/.coverage-final backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/tracking.py,*/network/router/helpers/arp_timeline.py' -o /tmp/gaia-network-arp-projection-refactor-20261117/coverage-final.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-arp-projection-refactor-20261117/differential-final.py
backend/.venv/bin/python /tmp/gaia-network-arp-projection-refactor-20261117/mutations-final.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/tracking.py backend/app/modules/network/router/helpers/arp_timeline.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code GRAPHIFY_CODE_FLAGS=--force
make graphify-platform-docs
```

## Stato e prossima azione

HEAD `ce9968b65a1b8a6fe94d061f265df2623e9a4555`; baseline/soglie/scope/eccezioni
intatti. Nessuna sincronizzazione della baseline o baseline-verify dichiarata.
Hash delle slice precedenti e report condivisi preservati; nessun test esistente
modificato, rimosso o indebolito. Nessun commit, push, merge o deploy.

Dalla ripresa diciotto slice: -18Error/-20Warning/-120cognitiva aggregata.
Lo snapshot corrente conserva1900Error/2953Warning; il programma resta aperto.
Singolo hotspot concluso: prossima azione e la review del delta e del blocco
globale Tributi, prima di selezionare un altro hotspot. Nessuna seconda slice
avviata in questo turno.
