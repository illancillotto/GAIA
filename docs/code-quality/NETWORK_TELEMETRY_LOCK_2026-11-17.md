# Lock del job telemetry Network — 2026-11-17

Esito **IMPROVED**: eliminati i due Warning di `_run_job_wrapper`.
La cognitiva del file `backend/app/modules/network/telemetry_scheduler.py`
scende da 22 a 18; nessun debito trasferito agli helper.

## Responsabilita e invarianti

Il wrapper conserva il ciclo del job: acquisisce la sessione, conserva la
connessione PostgreSQL, tenta il lock, salta il lavoro se occupato, esegue
refresh rollup e prune, quindi chiude le risorse nello stesso ordine.

- `_try_acquire_telemetry_lock` possiede cursore, SELECT pg_try_advisory_lock,
  fetchone e conversione bool. Chiude il cursore nel finally. Il wrapper salva
  raw_connection prima di chiamarlo: gli errori di acquisizione lasciano la
  connessione disponibile per il cleanup originale.
- `_release_telemetry_lock` esegue unlock e close della connessione con due
  suppress(Exception) indipendenti. Un errore ordinario del cursore non salta
  la chiusura della connessione; BaseException continua a propagarsi.
- Il close della sessione, anche awaitable, precede unlock e close connessione;
  next(generator) resta per ultimo con suppress(StopIteration). Gli errori del
  close DB possono ancora interrompere il cleanup successivo; non si cambia
  questa semantica durante il refactor.

SQL, chiave 2200615, parametri, condizioni PostgreSQL, contesa del lock,
lookback/retention, registrazione scheduler, log e ordine degli errori invariati.
Nessuna modifica a transazioni, concorrenza, API o schema.

Il wrapper ha AST identico all'originale espandendo i due helper e riportando
il return acquisizione all'assegnazione originale. `_consume_db_factory` e
`register_network_telemetry_scheduler` hanno AST identico. Gli altri nodi
modulo sono invariati salvo gli import richiesti da Ruff: Callable da
collections.abc e import rollup multilinea, UP035/I001 gia riprodotti prima.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Wrapper cognitiva | 20 | 14 |
| Wrapper ciclomatica | 10 | 8 |
| Wrapper LOC | 42 | 30 |
| Wrapper nesting | 3 | 3 |
| Cognitiva file | 22 | 18 |
| Ciclomatica file | 14 | 16 |
| Decisioni (somma cyclomatic meno 1) | 11 | 11 |
| Callable | 3 | 5 |
| LOC file | 85 | 92 |
| Densita | 0,423529 | 0,369565 |
| Error | 0 | 0 |
| Warning | 2 | 0 |

Helper acquire cognitive/cyclomatic/LOC/nesting `1/2/7/1`, release `1/2/9/1`,
un parametro ciascuno. L'aumento della ciclomatica aggregata corrisponde ai
due ingressi funzione; decisioni invariate e cognitiva ridotta dimostrano che
il branching non aumenta. Tutti i callable del file sono sotto soglia.

## Verifiche

Artefatti `/tmp/gaia-network-telemetry-lock-refactor-20261117/`.

- 59 test PASS prima/dopo: 56 nuovi in `test_network_telemetry_scheduler.py`,
  3 runner piattaforma. Zero failure/error/skip; test esistenti intatti.
- Coverage full-file statement/branch 100%: prima 58/58 statement e 16/16
  branch, dopo 62/62 e 16/16. Zero esclusioni, missing o branch parziali.
- Primo avvio dei nuovi test con marker asyncio non disponibile nell'ambiente:
  corretto su anyio gia usato dal progetto, backend asyncio. Nessun pacchetto
  installato e nessuna configurazione coverage o gate modificata.
- 4.000 scenari differenziali equivalenti per risultato, errori e precedenza,
  SQL/parametri, trace completo e stato generator. Include DB sync/async/senza
  close, PostgreSQL e altro dialetto, contesa, truthiness e fino a tre errori
  contemporanei fra lavoro e cleanup, compresi BaseException.
- Sei mutanti solo in memoria respinti: cursore acquire non chiuso (19 failure),
  cancellazione soppressa (3), unlock anticipato rispetto al close DB (10),
  connessione non chiusa (28), lavoro senza lock (8), chiave lock errata (16).
  Zero collection error o skip; nessun mutante applicato al runtime.
- Ruff runtime/test, format-check nuovo test, lint-backend 258 file e
  diff-check PASS. Nessuna nuova failure applicativa.
- Ratchet scoped origin/main PASS prima/dopo, merge-base `686e529e`. Globale
  exit 2 sulla stessa ambiguita Tributi useEffect[0]<callback>, dieci candidati.
  Il blocco precede questa slice; l'audit peer prova HEAD Tributi PASS e WIP
  exit 2. Nessun PASS globale, baseline sync o baseline-verify dichiarato.
- Report completi 1.963 file: callable 22.643→22.645, Error 1.892 invariati,
  Warning 2.947→2.945. Solo scheduler cambia, zero parse/exception error;
  scansione prima identica al completo finale della slice creation precedente.
- Baseline/scope/soglie/eccezioni/matcher/report condivisi e WIP estranei
  preservati; audit peer dei 36 file storico e distinto da questa verifica.
- Graphify Network Make: 493 nodi/1.232 archi. Platform docs, chunk e warning
  registrati nel checkpoint finale; nessun graphify-out versionato.

Comandi principali dalla root:

```bash
COVERAGE_FILE=/tmp/gaia-network-telemetry-lock-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-telemetry-lock-refactor-20261117/test-after.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_telemetry_scheduler.py backend/tests/test_platform_scheduler_runner.py --junitxml=/tmp/gaia-network-telemetry-lock-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-network-telemetry-lock-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/telemetry_scheduler.py' -o /tmp/gaia-network-telemetry-lock-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-telemetry-lock-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-telemetry-lock-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/telemetry_scheduler.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-patch-openai-base-url
make graphify-platform-docs
```

## Stato

HEAD iniziale `743b21c132b19c82d1201f93b59a541a3b28269a`. Singola slice
conclusa; nessun secondo hotspot, commit/push/PR/merge/deploy.

Dalla ripresa: 27 slice migliorative, −26 Error, −28 Warning, −181 cognitiva
aggregata. Restano globalmente 1.892 Error e 2.945 Warning. Nessun hotspot
residuo nello scheduler. Prossima azione review e nuova selezione alla
continuazione; goal generale attivo.
