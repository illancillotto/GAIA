# Decodifica valori Syslog Sophos — 2026-11-17

Esito `IMPROVED`: separazione della decodifica di un valore dal
ciclo del parser. `_unquote_syslog_value` conserva le slice che riconoscono
le virgolette, `shlex.split(value)[0]` e il fallback soltanto su ValueError.
La guardia precoce usa il complemento logico dello stesso predicato su str,
con identico short circuit; non modifica il riconoscimento tramite regex.

Il parser mantiene ordine dei campi e chiavi duplicate: l'ultimo valore
sostituisce il precedente senza spostare la posizione della chiave. Errori
diversi da ValueError continuano a propagarsi interrompendo i campi successivi.
Nessun cambio a ingestion, transazioni, query, autenticazione o schema.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Parser cognitiva | 14 | 1 |
| Parser ciclomatica | 7 | 2 |
| Parser LOC / nesting | 11 / 4 | 5 / 1 |
| Helper cognitiva / ciclomatica / LOC / nesting | assente | 7 / 6 / 7 / 2 |
| File cognitiva | 121 | 115 |
| File ciclomatica | 100 | 101 |
| Decisioni: somma cyclomatic meno 1 | 85 | 85 |
| Callable | 15 | 16 |
| LOC file | 303 | 309 |
| Error | 5 | 5 |
| Warning | 4 | 3 |

Nessuna nuova violation nel helper, un parametro. Le decisioni aggregate non
aumentano: il +1 ciclomatico deriva dal nuovo callable. Il Warning nesting
del parser scompare. Le LOC includono il wrapping degli import richiesto da
Ruff; il file rimane sotto soglia. Error legacy degli altri callable restano.

Ruff originario segnalava I001 e UP017: import ordinati e datetime.UTC al posto
di timezone.utc, verificati come lo stesso oggetto. Nessuna riformattazione
del resto del file. Le altre 14 funzioni hanno AST identico; reinserendo il
blocco decodifica originale nel caller si ricostruisce esattamente il suo AST.

## Evidenze

Artefatti `/tmp/gaia-network-syslog-unquote-refactor-20261117/`.

- Prima runtime: suite Network 1.168 PASS, zero failure/error/skip, inclusi
  22 nuovi test; riesecuzione dei 22 dopo aggiunta del ramo severita Warning.
  Coverage full-file 165/165 statement e 54/54 branch, 100%, zero esclusioni.
- 10.000 differenziali su messaggi reali sintetici equivalenti per valori,
  ordine ed eccezioni: quote singole/doppie, whitespace, escape, token
  incompleti, duplicati e chiavi non riconosciute. Nessuna richiesta di rete.
- Quattro mutanti solo in memoria respinti dai nuovi test, zero error/skip:
  decodifica rimossa (10 failure), catch Exception (2), valori senza quote
  troncati (7), fallback rimosso (2). Nessun mutante nel checkout.
- Tentativi prima del runtime conservati: fixture senza log_type corretta
  perche il parser del prefisso consuma il primo token come hostname;
  import Base aggiunto per registrare i modelli anche nel test isolato.
  Misura coverage intermedia 99% corretta aggiungendo l'asserzione Warning.
  Nessuna failure applicativa nuova non spiegata o gate indebolito.
- Ratchet scoped origin/main prima/dopo PASS; lint-backend, Ruff runtime/test,
  format nuovo test e diff-check PASS. Baseline/soglie/eccezioni intatte.
- Graphify Network aggiornato tramite Make: 496 nodi, 1.240 archi.
- Dopo runtime: 1.168 test Network PASS, zero failure/error/skip; full-file
  165/165 statement e 54/54 branch 100%, nessuna esclusione/missing/partial.
- Report completi isolati: 1.963 file, callable 22.647 -> 22.648, Error
  1.890 invariati, Warning 2.942 -> 2.941. Solo sophos.py cambia,
  zero parse/exception error. Ratchet globale exit 2 unicamente per
  ambiguous_identity Tributi useEffect[0]<callback>, dieci candidati,
  preesistente. Nessun PASS globale o sync/verify baseline dichiarato.
- Hash runtime precedenti, WIP estranei, baseline, eccezioni, matcher e report
  condivisi invariati. Runtime finale identico al candidato verificato.

Graphify platform docs e hash finali registrati nel checkpoint di chiusura.
Nessun secondo hotspot, commit, push, merge o deploy.

```bash
COVERAGE_FILE=/tmp/gaia-network-syslog-unquote-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-syslog-unquote-refactor-20261117/test-after.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network*.py --junitxml=/tmp/gaia-network-syslog-unquote-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-network-syslog-unquote-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/sophos.py' -o /tmp/gaia-network-syslog-unquote-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/sophos.py
backend/.venv/bin/python /tmp/gaia-network-syslog-unquote-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-syslog-unquote-refactor-20261117/mutations.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-platform-docs
```
