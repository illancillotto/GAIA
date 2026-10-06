# Banca ore — review di complessita e validazione

Data: 2026-10-06. Perimetro runtime:
`backend/app/modules/presenze/router/helpers/bank_hours.py`.

## Responsabilita e invarianti

Le slice sono behavior-preserving: nessuna modifica a API, autorizzazioni,
query, schema dati, transazioni o regole HR. MPC/MCP e lavori concorrenti
restano esclusi dalla campagna di refactoring.

- Il dashboard aggrega solo i collaboratori inclusi dai filtri; l'ordinamento
  resta pending decrescente, saldo crescente, nome crescente.
- Il saldo efficace resta saldo importato piu rettifiche approvate; le
  rettifiche pending contribuiscono ai conteggi, non al saldo.
- Gli straordinari liquidabili rispettano l'ordine day/night/festive/
  festive-night e includono il nome del bucket abilitato anche con minuti zero.
- La candidatura giornaliera resta il massimo fra classificazione, minuti
  extra importati e timbrature complete. Le timbrature sono candidate soltanto
  quando la somma degli extra importati e positiva; oltre mezzanotte invariato.
- Una giornata lavorata richiede almeno una voce importata positiva, non una
  somma positiva: una voce negativa non annulla una voce positiva nel conteggio.
- I record non classificati non alimentano compensi o bonus. Il conteggio
  mensile e l'aliquota notturna mantengono il massimo; la soglia raggiunta resta
  true anche quando i record successivi non la raggiungono.
- Proposta di liquidazione, soglia minima, reason code, precedenza delle
  condizioni e note HR restano invariati.

## Metriche verificate

Le misure si riferiscono allo snapshot immediatamente precedente ciascuna
slice, non al report storico versionato.

| Slice | Cognitive | Cyclomatic | LOC | Nesting |
| --- | --- | --- | --- | --- |
| Selezione bucket liquidazione | 31 -> 30 | 24 -> 22 | 85 -> 82 | 4 -> 4 |
| Accumulatore compensi e bonus mensile | 50 -> 37 | 31 -> 24 | 91 -> 49 | 2 -> 2 |
| Conteggi giornate compensi | 37 -> 21 | 24 -> 16 | 49 -> 47 | 2 -> 2 |
| Aggregati dashboard | 90 -> 87 | 56 -> 55 | 123 -> 116 | 3 -> 2 |

L'unico helper introdotto e `_apply_bank_hours_night_bonus`, metriche
8/8/13/1, due parametri e zero violation. L'aumento di una unita della
cyclomatic aggregata nella slice mensile corrisponde alla base del nuovo
callable: il numero di decisioni resta invariato. Le altre slice non
introducono callable o nuovi modelli.

La riduzione non completa il programma: dashboard, guida alla liquidazione,
dettaglio collaboratore e cyclomatic del riepilogo conservano debito legacy.
Non sono modificate baseline, soglie o esclusioni per nasconderlo.

## Validazione finale

- 227 test router/API Presenze verdi, compresi 53 nuovi casi di
  caratterizzazione eseguiti anche prima dei rispettivi refactoring.
- Coverage full-file: 221/221 statement e 72/72 branch, 100%, zero esclusioni.
- Ruff check e format runtime, lint-backend e diff-check verdi.
- Ratchet mirato contro baseline del merge-base `916ed94a`: `findings: []`.
- Graphify codice aggiornato tramite `make graphify-presenze-code`.

```bash
COVERAGE_FILE=/tmp/gaia-bank-totals-after.coverage .venv/bin/python -m pytest -q \
  backend/tests/test_presenze_router_helpers.py backend/tests/test_presenze_api.py \
  --cov=backend/app/modules/presenze/router/helpers --cov-branch \
  --cov-report=json:/tmp/gaia-bank-totals-coverage.json
python tools/code_quality/complexity.py ratchet --base-ref 916ed94a \
  backend/app/modules/presenze/router/helpers/bank_hours.py
make lint-backend BASE_REF=916ed94a QUALITY_PYTHON=.venv/bin/python
```

Le verifiche sono mirate al runtime modificato: non attestano tutti i gate
globali o tutti i commit gia presenti su main. Le evidenze per ciascuna slice
sono registrate in `docs/code-quality/PROGRESS.md`.

## Preflight rilascio CED

Il controllo read-only del 2026-10-06 rileva checkout CED `6b61fd27`, runtime
modificati per GaTe Mobile, inCass e SISTER, lockfile frontend modificato,
hotfix e override non tracciati. I servizi dotati di healthcheck risultano
healthy. Il manifest release storico non coincide con il checkout corrente:
nessuno dei due prova la versione delle immagini in esecuzione.

Il deploy standard richiede commit pushati e checkout pulito. Non eseguire
reset/stash o sovrascrittura del server per aggirare questi controlli;
riconciliare gli hotfix e gli override prima del rilascio. Il push di main
pubblica l'intera storia committata, non soltanto le slice di questa review.
Le modifiche documentali concorrenti non committate non sono parte del rilascio.
