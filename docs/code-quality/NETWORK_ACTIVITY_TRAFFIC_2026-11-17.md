# Contatori traffico attivita soggetti Network — 2026-11-17

Esito **IMPROVED**: un Warning eliminato e cognitiva aggregata174→168 in
`backend/app/modules/network/router/helpers/tracking.py`. Nessuna violation
trasferita. Il riepilogo conserva tre Error, dichiarati come debito residuo.

## Modifica e invarianti

`_tracked_activity_traffic` separa il blocco di conversione dei contatori dal
riepilogo attivita. Il builder lo chiama nella posizione originale: dopo il
matching e la detection, prima degli aggregati. Il blocco mantiene le stesse
istruzioni; l'helper restituisce i due contatori. Le altre venti funzioni
preesistenti hanno AST identico e tutte le ventuno firme sono preservate.

La guardia device richiede ancora entity_type esattamente device e value
truthy. La seconda lettura di subject.value resta nel keyword device_ip,
senza accorparla alla prima. Il risultato dell'estrattore non viene riclampato.
Il percorso raw legge bytes_sent prima di bytes_received; conserva get con
default0, str, strip, int e max0, con catch separati TypeError/ValueError.
Gli altri errori continuano a propagarsi. Nessuna lettura anticipata su eventi
non corrispondenti; il limite dei dettagli non interrompe i totali.

Query, SQL, auth, schema, transazioni, rilevamenti, ordinamento, label,
contatori e risposta rimangono invariati. Nessun test esistente modificato.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Summary: cognitiva | 68 | 48 |
| Summary: ciclomatica | 32 | 25 |
| Summary: LOC | 133 | 121 |
| Summary: nesting | 4 | 3 |
| Cognitiva file | 174 | 168 |
| Ciclomatica file | 136 | 137 |
| Somma cyclomatic meno 1 | 115 | 115 |
| LOC file | 444 | 449 |
| Callable | 21 | 22 |
| Error | 3 | 3 |
| Warning | 1 | 0 |

Helper cognitive/cyclomatic/LOC/nesting14/8/17/3, tre parametri, sotto tutte
le soglie. La crescita ciclomatica corrisponde al callable aggiunto;
non si rivendica una riduzione delle decisioni aggregate.

## Verifiche

Artefatti `/tmp/gaia-network-activity-traffic-refactor-20261117/`.
Nuovo `backend/tests/test_network_activity_traffic.py`:23casi.

- 248test PASS prima/dopo:18helper,50API,49normalizzazione,43matching,
  38riconciliazione,19anomalie ARP,8proiezione ARP e23contatori attivita.
  Entrambi gli XML hanno zero failure/error/skip; nessun retry necessario.
- Tracking full-file statement/branch100% prima242/242statement e96/96branch,
  dopo245/245 e96/96. Zero esclusioni, missing e branch parziali.
- Differenziale8000scenari equivalente per payload completo, SQL, clock,
  eccezioni e trace ordinato di attributi subject/event, get/str e chiamate
  matching/detection/traffic/label. Include value variabile tra letture,
  IDzero, limit negativo/zero/positivo, byte malformati o negativi, device
  traffic negativo e fallimenti alle singole operazioni.
- Cinque mutanti in memoria respinti: clamp eliminato, str saltato prima di
  int, guardia falsey device rimossa, catch ampliato a Exception, contatori
  sent/received scambiati. Nessun mutante scritto nel runtime.
- Ratchet mirato origin/main PASS prima/dopo, zero finding; baseline del
  merge-base `686e529ee011487e0764b9f91d023be063dbdf55`. Globale exit2 per
  l'ambiguita preesistente Tributi `useEffect[0]<callback>`, dieci candidati.
  Nessun PASS globale dichiarato e nessuna modifica al matcher.
- Report completi1961file:22625→22626callable, Error1900 invariati,
  Warning2953→2952. Solo tracking.py varia metriche; zero errori di parsing
  o eccezioni. Baseline, soglie, scope e report condivisi preservati per hash.
- Ruff runtime/test, format del nuovo test, lint-backend243file e diff-check
  PASS. Nessuna nuova failure;98warning JWT della suite API preesistenti.
- Graphify Network via Make475nodi/1194archi; aggiornamento platform docs
  e verifica semantica registrati nel checkpoint finale.

Comandi principali, dalla root:

```bash
COVERAGE_FILE=/tmp/gaia-network-activity-traffic-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-activity-traffic-refactor-20261117/test-after.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_tracked_normalization.py backend/tests/test_network_tracked_matching.py backend/tests/test_network_legacy_reconciliation.py backend/tests/test_network_arp_timeline.py backend/tests/test_network_arp_projection.py backend/tests/test_network_activity_traffic.py --junitxml=/tmp/gaia-network-activity-traffic-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-network-activity-traffic-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/tracking.py' -o /tmp/gaia-network-activity-traffic-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-activity-traffic-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-activity-traffic-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/tracking.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-platform-docs
```

## Stato e prossima azione

HEAD `ce9968b65a1b8a6fe94d061f265df2623e9a4555`; runtime finale identico al
candidato verificato. Nessuna sincronizzazione baseline o baseline-verify
dichiarata; nessun commit, push, merge o deploy. Modifiche concorrenti preservate.

Dalla ripresa diciannove slice: -18Error/-21Warning/-126cognitiva aggregata.
Snapshot globale1900Error/2952Warning: obiettivo generale ancora attivo.
Singola slice conclusa. Prossima azione: review del delta prima di scegliere
un ulteriore confine nel summary48/25/121/3; nessun secondo hotspot avviato.
