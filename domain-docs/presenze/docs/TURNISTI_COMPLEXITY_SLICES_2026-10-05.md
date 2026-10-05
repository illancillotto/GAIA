# Slice di correzione complessità turnisti — 2026-10-05

Verifica corrente successiva al report coordinato. Branch `main`, HEAD/base
`17242e81ee607ad9e0eeb09d3f60d7cd4964f972`; confronto autorevole con la baseline
committata al base, scanner/soglie/esclusioni invariati.
L’utente ha autorizzato la risoluzione delle slice dopo il gate fallito.

## Perimetro e invarianti

19finding iniziali del ciclo: serializzazione buoni, export CCNL, patch GATE,
classificazione giornaliera, registrazione modello e pagina giornaliere.
Ogni slice resta nella relativa responsabilità, con API, durata/decorrenza del
buono, precedenza GATE, permessi globali, audit, lock e reload mese invariati.
Lavoro Wiki concorrente preservato; nessuna modifica a produzione o baseline.
Evidenze locali: `/tmp/gaia-turnisti-slices-20261005-rbj1647t/`.
Snapshot iniziale, copie runtime prima e hash in `initial.json` e `before/`.

| Slice / responsabilità | Prima cyc/cog/LOC | Dopo cyc/cog/LOC | Motivazione e verifica |
| --- | --- | --- | --- |
| `meal_voucher_values` |12/11/28 |4/3/12 | La fonte di maturazione è separata dalla rappresentazione API. Il turno non ricade sulla regola extra ore. Test soglia419/420, decorrenza, viaggio, manuale+automatico, trasporti |
| `classification_breakdown_values` |3/2/18 |2/1/6 | Tuple immutabile di bucket; provenance CCNL posseduta dal servizio CCNL. Test calendario notturno, prefisso export, assenza metadata legacy |
| `apply_gate_daily_record_patch` |4/3/15 |3/2/13 | Lock/audit comune con GAIA, source distinta. API web4parametri preservata tramite facade di compatibilità; nessuna seconda implementazione della regola. Test grant/revoke/retry/omitted e patch ordinarie |
| `classify_daily_record` |57/63/128 |49/55/121 | Interpretazione override overtime/MPE distinta; zero mantiene precedenza e totale0 restaNone. Risultato dataclass condiviso ordinari/turni, re-export schedule compatibile. Suite schedule/operai/CCNL/export |
| metadata modello |file517LOC |file514LOC | Registrazione nella registry canonica `app.db.base`, non nel monolite Presenze. Import test dal modulo proprietario; migrazione/FK/metadata nei test |
| `PresenzeGiornalierePage` |458/551/2276 |457/550/2275 | Componente per le due azioni correlate, permessi giornalieri/globali distinti e reload range. Rimossi callback pagina e locale label ridondante. DOM/browser per viewer/owner/admin, conflitto, reload e autorità GATE |

Il massimo cognitivo buoni passa11→8 senza nuove violation nei servizi di
maturazione. Gli aggregati completi sono in `metrics-proof.json`; estrazioni di
ownership e dataclass sono `REORGANIZED_AND_CHARACTERIZED`, non dichiarate come
riduzione del debito globale. La semplificazione override riduce la complessità
di orchestrazione (49/55) e il file schedule scende sotto la dimensione al base.
L’obiettivo del ciclo è `IMPROVED`:19finding regressione rimossi, nessun debito
error-level trasferito a nuovi helper/componenti. Non è eliminato il debito
storico dei grandi classificatori/pagina.

## Matrice funzionalità → test

La matrice completa del ciclo rimane nel report coordinato; le slice usano
quei test senza skip/ignore o test artificiali. Test mirati eseguiti:

- 80test buoni/shift/CCNL/trasporti/coordinated: PASS prima del rerun finale;
  perimetro ristretto99% perché non includeva omissione nel path API web.
- 193test incluse API: PASS; misura intermedia coverage non accettata perché
  il codice era stato aggiornato durante il run. Non dichiarata100%.
- CCNL22test PASS; trasporti buoni e regressioni coordinate19test PASS.
- Coverage backend completa iniziale interrotta durante le ultime correzioni;
  sostituita da un run da zero sul runtime finale. Nessun risultato parziale PASS.

## Gate delle slice

`complexity.py ratchet --base-ref 17242e81 <file slice>`: PASS per ogni slice e
per il perimetro completo del ciclo; `findings: []` in `cycle-ratchet.log`.
Il ratchet globale su HEAD/base con working tree corrente restituisce8finding,
tutti Wiki (`auth.py`, HTTP e CLI); **zero finding Presenze/frontend**.
Nessun finding Wiki corretto o assorbito in baseline da questo intervento.
Le modifiche Wiki concorrenti non sono certificate dalle suite turnisti.

DONE:19regressioni del ciclo rimosse;frontend3829test/271suite,100% tutte4metriche
su6runtime inclusa pagina e componente nuovo;lint/typecheck/build PASS;
Chromium3PASS;quality tooling169PASS;backend lint PASS dopo formatter del nuovo
dataclass. Graphify codice Presenze1386nodi/4244archi/60comunità,
frontend6486nodi/15538archi/227comunità; HTML frontend omesso dal limite5000.
DONE: rerun backend completo con PG:1097test PASS, zero skip; coverage
rigenerata sul runtime finale19file,1293/1293statements/lines,264/264branches.
Nessuna riga esclusa. Tutte86funzioni sorgenti eseguite, verificando la prima
istruzione del corpo nel JSON coverage; coverage.py non emette una metrica
functions autonoma. Evidenza AST in `backend-function-evidence.json`.
RESIDUAL / UNRELATED: ratchet globale Wiki rosso; nessun commit prima del gate
coordinato verde. Lavoro concorrente e vecchie baseline non sovrascritti.
OUT OF SCOPE: deploy/sync/backfill, nuove feature, dipendenze, hotspot legacy
non peggiorati dal ciclo.

## Risultati finali riproducibili

| Comando reale | Esito finale |
| --- | --- |
| pytest `test_presenze*.py`, `test_gate_mobile_sync.py`, `test_gate_meal_vouchers.py`, `test_operazioni_mobile_sync_api.py`, `--cov=backend/app --cov=backend/alembic --cov-branch --cov-fail-under=100` | PASS1097, PostgreSQL16 isolato configurato, nessuno skip |
| frontend `npm run test:coverage -- --maxWorkers=2` con6runtime include | PASS3829test /271suite |
| frontend `npm run lint`, `npm run typecheck`, `npm run build` | PASS, warning legacy senza nuovo errore |
| frontend `PLAYWRIGHT_BASE_URL=http://127.0.0.1:54680 npm run test:e2e -- tests/e2e/presenze-operational-controls.spec.ts` | PASS3Chromium |
| `make quality-test` | PASS169 |
| `make lint-backend QUALITY_PYTHON=backend/.venv/bin/python BASE_REF=17242e81` | PASS |
| Ruff nuovo dataclass format/check | PASS dopo rimozione whitespace finale |
| `complexity.py ratchet --base-ref 17242e81 <perimetro ciclo>` | PASS0finding |
| `complexity.py ratchet --base-ref 17242e81` sul working tree completo | FAIL8finding, tutti Wiki unrelated |
| `make complexity-ci-gate BASE_REF=17242e81` sul runtime finale | FAIL8finding Wiki al ratchet; check/baseline-verify successivi non eseguiti |
| `make graphify-presenze-code`, `make graphify-frontend`, ripetuti con pruning `--force` | PASS, nessuna nuova topology dopo refresh finale |
| `make graphify-presenze-docs` | PASS chunk1/1,1010nodi/1936archi/75comunità;14134token in/4138out,costo stimato0.0123USD; ulteriore refresh sui risultati finali |
| `make graphify-platform-docs` | PASS chunk1/1,2469nodi/5703archi/160comunità;5796token in/3604out,costo stimato0.0081USD |
| GATE `npm run graphify:code-map` | PASS5845nodi/9862archi/343comunità |

Frontend finale:1229/1229statements,1385/1385branches,320/320functions,
1012/1012lines. Tutti6file100%; nuova orchestrazione UI coperta dai test DOM
reali di salvataggio/permessi e dai3browser. Nessun test aggiunto solo per
misurare righe; unica modifica test è l’import dal modulo proprietario del
modello, ora registrato nella registry canonica.

La misura runtime finale include19Python/migration (17del ciclo originario,
più registry e risultato condiviso) e6frontend (5originari più controlli comuni).
API/schema/autorizzazioni/persistenza conservati: route e restrizione globale
restano identiche, audit conserva source/actor/grant/revoke, lock invariato,
range e precedenza GATE invariati; regressioni, retry e migration testati.
Contratto esportato CCNL e buoni invariato nelle suite snapshot/trasporti.
Nessuna nuova funzione error-level, servizio o resolver parallelo.

### Chiusura e residual

DONE: tutte le19regressioni attribuite al ciclo risolte; nessuna parte runtime
modificata non coperta. Tutti i controlli pertinenti delle slice passano.
RESIDUAL BLOCKING per il gate globale:8finding Wiki concorrenti estranei a
queste slice. Non corretti senza ampliare il perimetro; baseline non modificata.
PRE-EXISTING: warning lint/JWT sintetico e dependency audit della verifica
precedente; nessun nuovo audit/deploy produttivo dichiarato in questa fase.
OUT OF SCOPE: rilascio coordinato produttivo e certificazione snapshot live.

Documentazione: nuovo report slice, rimandi nei report coordinati e progress
Presenze/turnisti; solo append della sezione propria nel progress qualità,
preservando il contenuto Wiki concorrente. Artifact Graphify/coverage/log
locali ignorati, nessuno selezionato. Diff review e `git diff --check` PASS;
inventario classificato in `gaia-hygiene.json` e `gate-hygiene.json`.
GAIA53percorsi dirty, GATE3; task Next e PostgreSQL dedicati arrestati/rimossi,
nessun servizio preesistente fermato.

```text
Slice turnisti: PASS
Final commit: commit delle sole modifiche turnisti autorizzato esplicitamente
Identificazione: git log -1 --format=%H -- domain-docs/presenze/docs/TURNISTI_COMPLEXITY_SLICES_2026-10-05.md
GAIA HEAD finale: 17242e81ee607ad9e0eeb09d3f60d7cd4964f972
GATE HEAD finale: 6d07f9d9c7c93e8dcbbdb0b6270b029ddbc4c627
Working tree dopo commit: restano solo modifiche Wiki/quality dell’altro team
```

FINAL QUALITY GATE — FAIL (globale; slice del ciclo PASS)

## Autorizzazione del commit isolato

L’utente ha confermato che Wiki appartiene a un altro team e ha richiesto il
commit del solo nostro lavoro. Il commit contiene il ciclo turnisti, i test,
le slice e i documenti pertinenti; nel progress qualità viene selezionata
soltanto la sezione aggiunta per le slice. Restano esclusi Wiki, test Wiki,
HOTSPOTS, baseline quality e report storico GATE unrelated, oltre agli artefatti.
La precedente condizione di non committare con il gate globale rosso è superata
da questa autorizzazione esplicita. Il gate globale resta FAIL8Wiki; non viene
riclassificato PASS. Il perimetro turnisti validato rimane PASS, runtime invariato.
Gli esiti «nessun commit» nei report precedenti descrivono il loro momento storico.
