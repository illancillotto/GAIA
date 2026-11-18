# Catena fallback discovery Network — 2026-11-17

`discover_hosts` sceglie la prima sonda ARP oppure ordinaria, poi condivide
la catena Scapy/fallback locale prima duplicata nei due rami. Nessun helper.
Esito `IMPROVED` per la riduzione reale di cognitiva e duplicazione.
Il Warning ciclomatico resta: la soglia inclusiva e 10, valore finale 10.
Questo intervento non si conta come riduzione del numero di finding.

## Invarianti

Default per range e porte, validazione della rete e messaggio di errore restano
prima delle sonde. Solo scan_type esattamente "arp" usa la prima sonda ARP;
gli altri valori continuano a usare Nmap ordinario con range e porte.
Il primo risultato truthy ritorna per identita, senza copie o conversioni.
Ogni risultato intermedio viene testato una volta; il fallback finale viene
restituito senza un ulteriore test di truthiness. Errori di sonde e truthiness
si propagano senza avviare tentativi successivi.

Prova AST: i due suffissi originali erano identici. Prefisso/default/validazione,
prima chiamata di ogni ramo e suffisso condiviso hanno AST invariato. Le altre
67 funzioni, gli import e lo stato modulo sono identici. API, schema,
autenticazione, transazioni, timeout e strumenti di rete non cambiano.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Target cognitiva | 14 | 10 |
| Target ciclomatica | 12 | 10 |
| Target LOC | 27 | 22 |
| Target nesting / parametri | 2 / 3 | 2 / 3 |
| Cognitiva file | 618 | 614 |
| Ciclomatica file | 472 | 470 |
| Somma cyclomatic meno 1 | 404 | 402 |
| Callable | 68 | 68 |
| LOC file | 1.446 | 1.441 |
| Error file/callable | 17 | 17 |
| Warning file/callable | 10 | 10 |

Nessun debito trasferito: non ci sono estrazioni, nuove callable o nuove
violation. Restano il Warning del target e gli altri finding legacy.

## Evidenze

Artefatti `/tmp/gaia-network-discovery-chain-refactor-20261117/`.

- Prima runtime: 1.290 test Network PASS, inclusi 42 nuovi, zero failure/error/
  skip. Servizio full-file 802/802 statement e 282/282 branch 100%, zero
  missing/partial; dieci righe import opzionali legacy escluse invariate.
- 4.000 differenziali equivalenti per oggetto selezionato, default, causa
  dell'errore di rete, ordine/argomenti delle sonde, truthiness ed errori.
- Tre mutanti solo in memoria respinti senza error/skip: selettore ARP invertito
  (35 failure), presenza al posto della truthiness (38), Scapy saltato (24).
  Nessun mutante nel checkout.
- Dopo: 1.290 test PASS, zero failure/error/skip; full-file services.py
  796/796 statement e 278/278 branch 100%, nessuna nuova esclusione/missing/
  partial. Ruff runtime/test, format nuovo test, lint-backend e diff-check PASS.
- Ratchet scoped origin/main prima/dopo PASS, merge-base `686e529e`;
  globale exit 2 soltanto per ambiguous_identity Tributi useEffect[0]<callback>,
  dieci candidati preesistenti. Nessun PASS globale o sync/verify baseline.
- Report completi isolati: 1.963 file, 22.648 callable, Error 1.890 e Warning
  2.940 invariati; solo services.py cambia, zero parse/exception error.
  Hash altri WIP, baseline, eccezioni, matcher e report condivisi invariati.
  Runtime finale identico al candidato. Graphify Network Make 496 nodi/1.240 archi.

Graphify platform docs e hash finali registrati nel checkpoint finale.
Nessun secondo hotspot, commit, push, merge o deploy; WIP estranei preservati.

```bash
COVERAGE_FILE=/tmp/gaia-network-discovery-chain-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-discovery-chain-refactor-20261117/test-after.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network*.py --junitxml=/tmp/gaia-network-discovery-chain-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-network-discovery-chain-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/services.py' -o /tmp/gaia-network-discovery-chain-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-discovery-chain-refactor-20261117/differential.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/services.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-platform-docs
```
