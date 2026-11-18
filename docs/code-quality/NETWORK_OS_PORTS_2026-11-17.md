# Classificazione OS da porte Network — 2026-11-17

La classificazione SMB usa un solo controllo della porta 445. Il ramo sceglie
Linux/Unix server quando e presente anche SSH, altrimenti Windows/SMB appliance.
RDP continua ad avere precedenza; seguono SSH, HTTP/HTTPS e il fallback None.
Esito `IMPROVED`: un Warning ciclomatico eliminato, nessun helper.

`set(open_ports)` resta all'inizio della funzione e viene consumato integralmente
prima delle decisioni. Il set locale non viene modificato durante la
classificazione: il secondo controllo 445 era ridondante. Ordine o duplicati
delle porte non cambiano il risultato; errori dell'iteratore e valori non
hashable continuano a fallire durante la materializzazione. Nessuna modifica
ai chiamanti, alle sonde, alle richieste di rete, ai dati o alle transazioni.

## Metriche del motore

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Target cognitiva | 11 | 9 |
| Target ciclomatica | 10 | 8 |
| Target LOC / nesting / parametri | 13 / 1 / 1 | 11 / 1 / 1 |
| Cognitiva file | 620 | 618 |
| Ciclomatica file | 474 | 472 |
| Somma cyclomatic meno 1 | 406 | 404 |
| Callable | 68 | 68 |
| LOC file | 1.448 | 1.446 |
| Error file/callable | 17 | 17 |
| Warning file/callable | 11 | 10 |

Nessuna estrazione o trasferimento di debito. Il target e sotto tutte le soglie;
gli altri finding legacy del servizio restano. Le altre 67 funzioni,
gli import e lo stato modulo hanno AST identico.

## Evidenze

Artefatti `/tmp/gaia-network-os-ports-refactor-20261117/`.

- Prima runtime: 1.248 test Network PASS, inclusi 80 nuovi, zero failure/error/
  skip. Servizio full-file 804/804 statement e 284/284 branch 100%, zero
  missing/partial; dieci righe import opzionali legacy escluse invariate.
- Tutte le 64 combinazioni di 3389/445/22/80/443 e una porta neutra, ciascuna
  con liste, tuple, set, iteratori, ordine inverso e duplicati. Verificati
  consumo completo anche quando la prima porta decide il risultato,
  generatori che falliscono, valori non hashable e uguaglianza numerica.
- 10.000 differenziali equivalenti per risultato, errori e trace iteratore.
- Quattro mutanti solo in memoria respinti senza error/skip: precedenza RDP
  alterata (16 failure), SMB+SSH invertito (19), HTTPS ignorato (2),
  materializzazione rimossa (37). Nessun mutante nel checkout.
- Nessun runtime modificato nelle esplorazioni precedenti SNMP/inference;
  quei candidati non fanno parte della slice e non contano come riduzioni.
- Dopo: 1.248 test PASS, zero failure/error/skip; full-file 802/802 statement
  e 282/282 branch 100%, nessuna nuova esclusione/missing/partial.
- Ruff runtime/test, format nuovo test, lint-backend e diff-check PASS;
  ratchet scoped origin/main prima/dopo PASS, merge-base `686e529e`.
  Globale exit 2 soltanto per ambiguous_identity Tributi useEffect[0]<callback>,
  dieci candidati, preesistente. Nessun PASS globale o sync/verify baseline.
- Report completi isolati: 1.963 file e 22.648 callable invariati, Error
  1.890 invariati, Warning 2.941 -> 2.940; solo services.py cambia,
  zero parse/exception error. WIP estranei, baseline, matcher e report
  condivisi preservati. Runtime finale identico al candidato.
- Graphify Network Make aggiornato: 496 nodi/1.240 archi.

Graphify platform docs e hash finali registrati nel checkpoint finale.
Nessun commit, push, merge o deploy; WIP estranei preservati.

```bash
COVERAGE_FILE=/tmp/gaia-network-os-ports-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-os-ports-refactor-20261117/test-after.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network*.py --junitxml=/tmp/gaia-network-os-ports-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-network-os-ports-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/services.py' -o /tmp/gaia-network-os-ports-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-os-ports-refactor-20261117/differential.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/services.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-platform-docs
```
