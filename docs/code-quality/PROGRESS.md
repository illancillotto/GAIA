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
