# Progress - GAIA Code Complexity Program

Questo file e la fonte di verita persistente. Hermes deve aggiornarlo dopo ogni
blocco verificato e prima di chiudere un goal.

## Stato generale

- Program status: `NOT_STARTED`
- Current phase: `0 - audit`
- Last verified commit: `79794c89e42e381a01d5dbbab36fa3a7abbde98d`
- Reference branch: `main`
- Last update: `2026-08-17`
- Current owner: `unassigned`
- Active goal: `none`
- Blocking CI enabled: `no`

> Il commit sopra e lo snapshot usato per preparare il kit. Alla prima
> esecuzione Hermes deve sostituirlo con il commit realmente analizzato.

## Checkpoint

| Checkpoint | Stato | Evidenza | Approvazione |
| --- | --- | --- | --- |
| 0 - audit reale | pending | - | - |
| 1 - tooling e baseline | pending | - | required |
| 2 - gate differenziale CI | pending | - | required |
| 3 - primo hotspot ridotto | pending | - | review PR |

## Decision log

| Data | Decisione | Motivo | Impatto |
| --- | --- | --- | --- |
| 2026-08-17 | Local-first in Fase 1 | Evitare dipendenza operativa dalla CI | Nessun gate bloccante prima del Checkpoint 1 |
| 2026-08-17 | Un hotspot per goal | Ridurre rischio e facilitare review/revert | Niente batch refactor |
| 2026-08-17 | `/goal` per modifiche, `/loop` per monitoraggio | Goal e verificabile; loop e temporizzato | Refactoring non eseguiti a timer |

## Audit corrente

Da compilare da Hermes:

- Branch/commit:
- Working tree preesistente:
- Tool Python esistenti:
- Tool frontend esistenti:
- Test backend:
- Test frontend:
- Test worker:
- Workflow CI:
- Perimetro runtime:
- Esclusioni:
- Failure preesistenti:
- Rischi o blocker:

## Fase 1

- [ ] Audit completato
- [ ] Architettura del motore approvata nel diff
- [ ] Adapter Python implementato
- [ ] Adapter JS/TS implementato
- [ ] Schema comune implementato
- [ ] Baseline generata
- [ ] Eccezioni validate
- [ ] Diff checker implementato
- [ ] Test dello strumento verdi
- [ ] Target Make verificati
- [ ] Documentazione completata
- [ ] Report Checkpoint 1 prodotto
- [ ] Nessun refactoring applicativo incluso

## Iterazione attiva

- ID: `none`
- Hotspot:
- Modulo:
- Motivazione:
- Invarianti:
- Test di caratterizzazione:
- Metriche prima:
- Slice pianificata:
- File previsti:
- Stato: `not_started`
- Metriche dopo:
- Verifiche:
- Coverage:
- Baseline diff:
- Esito:
- Debito residuo:

## Iterazioni concluse

| ID | Data | Hotspot | Prima | Dopo | Test/coverage | Commit/PR |
| --- | --- | --- | --- | --- | --- | --- |
| - | - | - | - | - | - | - |

## Modifiche funzionali verificate fuori dal programma hotspot

### 2026-08-19 - Export completo riepiloghi eventi INAZ

- Branch/worktree: `main` nel worktree dedicato `/home/cbo/CursorProjects/gaia-inaz-ferie-main`, base `2ded321cd99aeb59c02865e5e7f2bc158804e4b9`.
- Scope runtime: `backend/app/modules/presenze/services/parser.py` e nuovo `event_summary_export.py`.
- Invarianti: nessuna modifica a route, schema DB, autenticazione, autorizzazione, transazioni o sync; i campi legacy `*_minutes` persistiti restano compatibili.
- Correzione: segno delle durate negative `-HH:MM`; nuovo export unit-aware che conserva i valori grezzi e non filtra le descrizioni.
- Coverage: `pytest tests/test_presenze_event_summary_export.py tests/test_presenze_parser.py --cov=... --cov-fail-under=100` -> `17 passed`, `100%` sui due file runtime e sull'entrypoint CLI.
- Verifiche aggiuntive: compileall completato; suite mirate import/summary `16 passed`; suite backend completa senza failure; export read-only su produzione `6563` righe; Graphify code/docs aggiornato.
- Metriche complessita: tooling/target `complexity-*` non presente sul commit `main` di base; nessuna baseline modificata o rigenerata. Il nuovo servizio usa funzioni piccole e isolate, senza nuove esclusioni o eccezioni.
- Baseline diff: nessuno.
- Commit previsto: `fix(presenze): export complete INAZ event summaries`; PR: nessuna.

### 2026-08-20 - Versionamento hotfix live GATE Presenze

- Branch/worktree: `main` nel worktree dedicato `/home/cbo/CursorProjects/gaia-inaz-ferie-main`; nessuna integrazione dal branch `gaia/code-complexity-refactor`.
- Scope runtime: `backend/app/services/gate_mobile_sync.py`; diff live acquisito dal CED pari a `23` righe aggiunte e `2` rimosse.
- Invarianti: route, schema DB, autenticazione, autorizzazione e transazioni invariati; `_get_gate_record_or_404` continua a essere il gate autorizzativo finale.
- Comportamento: propagazione KM/reperibilita negli snapshot GATE e fallback del record giornaliero rigenerato tramite `collaborator_id/work_date`.
- Provenienza: il file modificato coincide byte per byte con il runtime CED, SHA256 `bb1aad87b1c05884d08afd5a33495a0887e1d081bde7ee2da9747127753ed30e`.
- Coverage: `pytest tests/test_gate_mobile_sync.py --cov=app.services.gate_mobile_sync --cov-fail-under=100` -> `28 passed`, `100%` (`655/655` statement).
- Metriche complessita: i target `complexity-*` non sono presenti sulla base `main`; nessuna baseline, eccezione o esclusione e stata importata dal branch di refactoring.
- Baseline diff: nessuno.

## Failure preesistenti

| Data | Comando | Failure | Riproducibile | Relazione con il lavoro |
| --- | --- | --- | --- | --- |
| - | - | - | - | - |

## Blocker e domande aperte

- Confermare le soglie dopo la prima distribuzione reale.
- Confermare le categorie di file dichiarativi ammesse come eccezione.
- Confermare il momento di attivazione dei gate CI.
- Verificare che i test del worker siano inclusi in un percorso autorevole.

## Prossima azione

Eseguire `HERMES_GOAL_PHASE_1.md` e fermarsi al Checkpoint 1.
