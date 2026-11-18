# Policy ingestione listener Syslog Network — 2026-11-17

Esito **IMPROVED**: due Warning eliminati e cognitiva aggregata 51→48 in
`backend/app/modules/network/sophos_syslog_listener.py`. Nessuna violation
trasferita; rimane il Warning sui sei parametri del costruttore.

## Modifica e invarianti

`SophosSyslogListener._ingest_message(db, message, client_ip)` contiene il
blocco originale di lettura policy, log dello skip e ingestione. Il metodo
pubblico handle_message mantiene la gestione della sessione e degli errori:
session factory prima del try, log dell'errore prima del rollback, close nel
finally. Gli errori della session factory continuano a propagarsi senza
cleanup; BaseException non viene catturata, ma chiude la sessione creata.
Errori del logger, rollback e close mantengono ordine e propagazione.

Policy disabilitata continua a leggere la finestra soltanto per il log e non
esegue ingestione o rollback. Policy attiva non legge is_within_window.
Letture di self, bool dei fallback, argomenti logger, messaggio grezzo e
preferenza management_ip prima del client IP sono preservati. Nessun cambio
ad API, DB, auth, transazioni, code, worker, threading o UDP.

Espandendo la chiamata con il corpo dell'helper, l'AST di handle_message
coincide con l'originale. Cinque altri metodi della classe restano identici;
sei firme e return preesistenti sono preservati. Gli altri nodi top-level
sono invariati salvo il fix di stile richiesto da Ruff: Callable importato
da collections.abc anziche typing. Non esistono altri metodi omonimi o
override del nuovo metodo nel runtime del repository alla verifica.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Handler: cognitiva | 16 | 7 |
| Handler: ciclomatica | 10 | 5 |
| Handler: LOC | 22 | 9 |
| Handler: nesting | 2 | 2 |
| Cognitiva file | 51 | 48 |
| Ciclomatica file | 45 | 46 |
| Somma cyclomatic meno 1 | 36 | 36 |
| Callable | 9 | 10 |
| LOC file | 131 | 133 |
| Densita | 0,732824 | 0,706767 |
| Error | 0 | 0 |
| Warning | 3 | 1 |

Metodo estratto cognitive/cyclomatic/LOC/nesting `6/6/15/1`, quattro parametri,
sotto soglia. L'aumento della somma ciclomatica corrisponde al nuovo callable;
le decisioni aggregate restano invariate.

## Verifiche

Artefatti `/tmp/gaia-network-syslog-policy-refactor-20261117/`.
Nuovo `backend/tests/test_network_syslog_listener.py`: 35 casi.

- 61 test PASS prima e sui byte finali: 26 servizi Network/script e 35 nuovi.
  Zero skip/failure/error in entrambi gli XML; nessun test esistente modificato.
- Full-file statement/branch 100%: prima 95/95 statement e 20/20 branch,
  dopo 97/97 e 20/20; zero esclusioni, righe mancanti o branch parziali.
- 5.000 confronti differenziali equivalenti per risultati, eccezioni incluse
  BaseException, stato parziale d'ingestione e trace ordinato letture self,
  policy/getter/bool/logger/ingest/rollback/close. Include combinazioni di
  errori durante il cleanup e policy che modifica la configurazione del
  listener. Differenziale ripetuto dopo il fix import sui byte finali.
- Sei mutanti in memoria respinti dai nuovi test: policy disabilitata ignorata
  (16 failure), rollback rimosso (6), close rimosso (22), factory dentro il try
  (1), client IP preferito (3), cattura di BaseException (1). Zero collection
  error o skip; nessun mutante applicato al runtime su disco.
- La nuova suite caratterizza anche start/stop idempotenti, coda piena,
  task_done in caso di errore e sentinella, decodifica UDP e chiusura server.
- Primo lint dopo estrazione fallito per UP035 nell'import Callable legacy,
  riprodotto anche sul sorgente originale. Corretto l'import e ripetuti test,
  differenziale, lint e ratchet sui byte finali. I log iniziali falliti restano
  conservati separatamente; nessun gate indebolito.
- Ruff runtime/test, format nuovo test, lint-backend 253 file e diff-check PASS.
  Nessuna nuova failure applicativa.
- Ratchet mirato origin/main PASS prima/dopo e finale. Merge-base
  `686e529ee011487e0764b9f91d023be063dbdf55`. Globale finale exit 2 per la
  stessa ambiguita preesistente Tributi useEffect[0]<callback>, dieci
  candidati. Nessun PASS globale dichiarato.
- Report completi 1.963 file, callable 22.637→22.638, Error 1.897 invariati,
  Warning 2.949→2.947; cambia solo sophos_syslog_listener.py, zero parse/exception
  error. La scansione finale dopo il fix import riproduce esattamente metriche,
  callable e violation del report completo dopo. Report condivisi intatti.
- Graphify Network Make: 486 nodi/1.216 archi; verifica dopo fix import senza
  cambi topologici. Platform docs e verifica chunk/warning nel checkpoint finale.
- Hash delle altre slice, baseline, eccezioni e report condivisi preservati.
  Nessuna baseline sync/verify, modifica a scope/soglie/matcher o nuova esclusione.

Comandi principali dalla root:

```bash
COVERAGE_FILE=/tmp/gaia-network-syslog-policy-refactor-20261117/.coverage-final DATABASE_URL=sqlite:////tmp/gaia-network-syslog-policy-refactor-20261117/test-final.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_services.py backend/tests/test_network_sophos_syslog_script.py backend/tests/test_network_syslog_listener.py --junitxml=/tmp/gaia-network-syslog-policy-refactor-20261117/tests-final.xml
COVERAGE_FILE=/tmp/gaia-network-syslog-policy-refactor-20261117/.coverage-final backend/.venv/bin/python -m coverage json --include='*/network/sophos_syslog_listener.py' -o /tmp/gaia-network-syslog-policy-refactor-20261117/coverage-final.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-syslog-policy-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-syslog-policy-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/sophos_syslog_listener.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-patch-openai-base-url
make graphify-platform-docs
```

## Stato e prossima azione

HEAD iniziale `8f65d353c7ecbf9d055dcecd564b617c6278cf6e`. Il runtime finale
coincide con il candidato verificato. Modifiche concorrenti Communications,
Ruolo e frontend preservate. Nessun commit/push/merge/deploy o secondo hotspot.
HEAD avanzato esternamente a `b83c4de1f14eedf6e9a216be94eec253789fa015`
durante la chiusura per un commit Communications di un altro autore; hash
protetti e runtime della slice invariati. Nessun commit creato da questa slice.

Dalla ripresa 24 slice migliorative: −21 Error, −26 Warning, −143 cognitiva
aggregata. Snapshot corrente 1.897 Error/2.947 Warning; obiettivo generale
ancora attivo. Prossima azione: review del delta, poi selezione di un altro
hotspot con ownership libera; costruttore del listener non affrontato.
