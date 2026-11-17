# Anomalie temporali timeline ARP Network — 2026-11-17

Esito **IMPROVED**: cognitiva aggregata230→221 e un Warning eliminato in
`backend/app/modules/network/router/helpers/tracking.py`, senza nuovi finding.
Il builder resta sopra soglia: tre Error residui, dichiarati separatamente.

## Modifica e invarianti

Due helper separano il conteggio delle riapparizioni online dai motivi di
anomalia. La timeline conserva query, raggruppamento, ordinamenti, lookup del
dispositivo, label, conteggi e costruzione della risposta. Non si spostano
blocchi ancora sopra soglia in helper: entrambi i nuovi callable sono sotto
tutte le soglie. Venti altri callable hanno AST identico; tutte le ventuno
firme preesistenti sono preservate.

Il conteggio usa osservazioni in ordine temporale crescente, aggiorna il
timestamp precedente solo per status esattamente online e considera inclusivo
il limite di due ore. La conversione dei timestamp naive a UTC avviene soltanto
per il confronto; la risposta conserva i timestamp originali. Anche timestamp
offline invalidi mantengono gli errori originali, perche la lettura temporale
non viene posticipata dentro la condizione online.

I motivi restano nell'ordine MAC multipli, IP multipli con MAC recente presente,
riapparizioni maggiori di uno. L'accesso al MAC recente resta lazy, dopo il
conteggio degli IP distinti. Ordine e numero letture ORM non cambiano. Restano
sorting per timestamp/ID discendenti, ordine stabile degli indirizzi distinti,
pareggi dei Counter, sei dettagli al massimo e slicing del limite soltanto
dopo il ranking. API, auth, schema, transazioni e query restano invariati.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Timeline: cognitiva | 63 | 35 |
| Timeline: ciclomatica | 33 | 22 |
| Timeline: LOC | 96 | 83 |
| Timeline: nesting | 4 | 1 |
| Cognitiva aggregata file | 230 | 221 |
| Ciclomatica aggregata file | 162 | 164 |
| Somma cyclomatic meno 1 | 141 | 141 |
| LOC file | 490 | 498 |
| Callable | 21 | 23 |
| Error | 6 | 6 |
| Warning | 2 | 1 |

Helper riapparizioni cognitive/cyclomatic/LOC/nesting13/7/10/3; motivi6/6/11/1.
Entrambi sotto soglia. I due punti ciclomatici aggiunti sono quelli dei nuovi
callable, senza crescita delle decisioni aggregate. File sotto500LOC, nessuna
violation trasferita. Residuo: tre Error del builder e tre Error/un Warning
del riepilogo attivita, invariato.

## Verifiche

Artefatti `/tmp/gaia-network-arp-timeline-refactor-20261117/`.
Nuovo test `backend/tests/test_network_arp_timeline.py`.

- 217test PASS prima/dopo:18helper,50API Network,49normalizzazione,43matching,
  38riconciliazione e19nuovi ARP; zero skip/failure/error nei due XML.
- Full-file statement/branch100%:262/262→268/268statement,108/108branch;
  zero esclusioni, missing o branch parziali. Hash sorgente finale verificato.
- Differenziale6000timeline equivalente per risposta completa ordinata, errori,
  SQL, clock e trace letture osservazioni/label. Include IDzero, dati vuoti,
  timestamp naive/aware/invalidi e fallimenti alle singole operazioni.
- Cinque mutanti in memoria respinti: intervallo due ore esclusivo, status
  non offline considerato online, una sola riapparizione flaggata, guardia
  MAC recente rimossa e limite sei dettagli rimosso. Nessun mutante sul runtime
  su disco; nessun test preesistente modificato, rimosso o indebolito.
- Ratchet mirato origin/main PASS prima/dopo, baseline autorevole merge-base
  `686e529ee011487e0764b9f91d023be063dbdf55`. Globale exit2 per la stessa ambiguita
  preesistente Tributi: `useEffect[0]<callback>`, dieci candidati. Nessun PASS globale.
- Report completi1960file: Error1903 invariati, Warning2954→2953,
  callable22620→22622; solo tracking.py varia metriche, nessun errore di parsing.
- Ruff runtime/test, format test nuovo, lint-backend239file e diff-check PASS.
- Graphify Network Make470nodi/1183archi; aggiornamento platform docs e verifica
  semantica registrati nel checkpoint della slice.

Comandi principali dalla root, con coverage distinta prima/dopo:

```bash
COVERAGE_FILE=/tmp/gaia-network-arp-timeline-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-arp-timeline-refactor-20261117/test.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_tracked_normalization.py backend/tests/test_network_tracked_matching.py backend/tests/test_network_legacy_reconciliation.py backend/tests/test_network_arp_timeline.py
COVERAGE_FILE=/tmp/gaia-network-arp-timeline-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/tracking.py' -o /tmp/gaia-network-arp-timeline-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-arp-timeline-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-arp-timeline-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/tracking.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-platform-docs
```

## Stato del checkout

HEAD `ce9968b65a1b8a6fe94d061f265df2623e9a4555`; baseline/soglie/scope/eccezioni
intatti, nessuna sincronizzazione o baseline-verify nel checkout concorrente.
Hash delle slice precedenti e report condivisi preservati. Dalla ripresa diciassette
slice: -15Error/-20Warning/-107cognitiva aggregata; nessuna percentuale storica
di completamento dedotta. Nessun commit, push, merge o deploy. Obiettivo generale
ancora attivo; il builder ARP resta candidato a una successiva slice delimitata.
