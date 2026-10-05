# Assegnazioni turnisti senza scadenza — 5 ottobre 2026

## Scope e stato

Branch `main`, base/HEAD iniziale `1279e3ceaaf6658ad2ce071bef3102898c75b003`.
Working tree iniziale non pulito: modifiche Wiki, Ruolo, SISTER, documentazione
quality e snapshot del rilascio precedente sono preservate e fuori da questa change.

**DONE:** contratto, persistenza nullable, risoluzione delle assegnazioni,
test di decorrenza/revoca/retry/permessi e migrazione PostgreSQL.
**PARTIAL:** richiesta operativa dei nove acquaioli dal 01/09/2026 senza scadenza;
richieste preparate localmente, nessuna assegnazione reale eseguita in questa verifica.
**RESIDUAL:** rilascio mirato, migrazione di produzione e applicazione tramite API
amministrativa autorizzata, seguiti dalla verifica dello snapshot settembre su GATE.
**OUT OF SCOPE:** nuovi controlli UI, rotazione dei turni, modifica squadre e mapping
identitari, codice degli altri team.

`date_to: null` è richiesto esplicitamente per la durata senza scadenza.
Gli intervalli con data finale conservano il vincolo di ordinamento e stesso mese.
L'assegnazione si applica anche ai record importati in futuro; una revoca successiva
`none` segue la precedenza già esistente. Nessuna nuova implementazione delle regole
CCNL o dei buoni pasto. I dialoghi attuali continuano a inviare date mensili.

La migrazione `20261005_1500` dipende da `20261003_1200`. Non cancella righe,
non aggiunge indici o nuove tabelle. Il downgrade rifiuta assegnazioni aperte:
prima serve chiuderle esplicitamente. Il test usa PostgreSQL reale, verifica
nullable, conservazione dei dati, downgrade rifiutato e round trip dopo chiusura.

## Matrice comportamento → test

| Comportamento | File principali | Test | Esito |
|---|---|---|---|
| Null esplicito; omissione/data invalida respinte | shift_worker_schemas.py | test_presenze_shift_open_ended.py | PASS |
| Nessun effetto prima del 01/09; durata negli anni futuri | services/shift_assignments.py | test_admin_assigns_ongoing_shift_and_future_imports_inherit_it | PASS |
| Sovrapposizioni inclusive aperte/chiuse | services/shift_assignments.py | test_bounded_and_ongoing_overlap_is_inclusive | PASS, 4 casi |
| Revoca, precedenza GATE e retry idempotente | services/shift_assignments.py | test_admin_assigns_ongoing_shift_and_future_imports_inherit_it | PASS |
| LAN/outbound conservano null e applicano anni futuri | gate patch / gate_mobile_sync | test_gate_ongoing_assignment_survives_transport_retry_and_future_month | PASS, 2 trasporti |
| Proprietario viewer/operator non autorizzato | route turnista esistente | test_ongoing_assignment_does_not_grant_owner_global_edit_permission | PASS, 2 ruoli |
| Persistenza e downgrade senza perdita dati | migration / shift_worker_models.py | test_ongoing_migration_preserves_rows_and_rejects_lossy_downgrade | PASS PostgreSQL |
| Regressione intervalli mensili, buoni e concorrenza | servizi Presenze | test_presenze_shift_workers.py, test_presenze_shift_workers_postgres.py, test_presenze_coordinated_regression.py | PASS |

## Verifica riproducibile

Dalla root GAIA, con `GAIA_TEST_POSTGRES_URL` configurato sul database isolato:

```bash
backend/.venv/bin/pytest backend/tests/test_presenze_shift_open_ended.py backend/tests/test_presenze_shift_workers.py backend/tests/test_presenze_shift_workers_postgres.py backend/tests/test_presenze_coordinated_regression.py --cov=backend/app/modules/presenze --cov=backend/alembic/versions --cov-config=/tmp/turnisti-open-ended-20261005-_rf_2yh2/backend.coveragerc --cov-report=term-missing --cov-fail-under=100
PATH="$PWD/backend/.venv/bin:$PATH" BASE_REF=1279e3ce make lint-backend
PATH="$PWD/backend/.venv/bin:$PATH" BASE_REF=1279e3ce make complexity-ratchet
```

Pytest: **47 passed**, 30 warning (deprecazioni e chiave JWT corta delle fixture).
Coverage rigenerata: **109/109 statement, 18/18 branch**, nessuna riga esclusa
aggiunta. `shift_worker_schemas.py`, `shift_worker_models.py`,
`services/shift_assignments.py` e migrazione nuova: **100%** righe/statement/branch;
nessuna funzione runtime non eseguita. Il frontend cambia solo il tipo TypeScript
della data finale, senza nuovo comportamento JavaScript. Typecheck frontend PASS.
Lint PASS. Il ratchet globale finale GAIA è FAIL con 8 finding nei file Wiki
`mcps/auth.py`, `mcps/cli.py`, `mcps/data/cli.py`, `mcps/http.py`, modificati
contemporaneamente dall'altro team: nessuna finding nei file di questa estensione.
Il controllo separato sul perimetro turno è PASS, senza finding, registrato in
`gaia-ratchet-scoped.log`. Baseline e soglie non modificate. Non si dichiara PASS
globale sulla base del precedente run privo di queste regressioni concorrenti.

## Operatività e sicurezza

Il probe GET corrente conferma route turnista disponibile e 5670 giornaliere di
settembre con `shift_worker_type`. Non prova che la durata senza scadenza sia
rilasciata. Sono attestati gli ID canonici già presenti per i nove collaboratori:
nessun mapping da creare o modificare. Le nove richieste API sono un artefatto
locale non versionato, con stato `PREPARED_NOT_APPLIED`.

L'applicazione prevista usa `POST /api/admin/presenze/pending-actions` GATE,
con anchor settembre autorizzato, tipologia `acquaiolo`, decorrenza `2026-09-01`
e `date_to: null`; autore e comando vengono attestati dal server. Non si cambia
la squadra. Verificare ACK/errori e snapshot aggiornati per tutte le nove persone;
prima della decorrenza lo stato precedente deve restare invariato.

Il rilascio deve essere isolato dalle modifiche concorrenti, con backup verificato,
GAIA migration e runtime compatibili prima dell'invio dei comandi GATE. Non usare
SQL non auditato o identità amministrative inventate per applicare il roster.

Evidenze locali: `/tmp/turnisti-open-ended-20261005-_rf_2yh2/`.
Graphify codice Presenze e frontend aggiornati tramite target dedicati; artefatti
ignorati e non versionati. Graphify docs Presenze completato senza chunk falliti:
1063 nodi / 2014 edge, estrazione semantica finale 1982 token input / 3597 output,
stima tool $0.0065. Esiti GATE nel report coordinato
`GaTe-mobile/docs/TURNISTI_OPEN_ENDED_2026-10-05.md`.

Il gate globale resta **FINAL QUALITY GATE — FAIL** per le 8 regressioni Wiki
contemporanee, fuori dalla change turnisti. Il perimetro tecnico di questa
estensione è verificato; l'applicazione operativa resta pendente.
