# GAIA Code Complexity Program

Questo pacchetto prepara GAIA a ridurre la complessita in modo incrementale,
misurabile e verificabile con Hermes Agent. La skill e parte del repository e
non viene installata nel profilo globale di Hermes.

Non contiene un refactoring applicativo gia eseguito. Contiene il contratto di
lavoro, la baseline policy, i checkpoint, i prompt e una skill Hermes pronta da
installare. La prima esecuzione deve costruire e validare l'infrastruttura; le
esecuzioni successive intervengono su un solo hotspot per volta.

## Ordine di utilizzo

1. Estrarre il pacchetto definitivo dalla root del repository GAIA, autorizzando
   la sostituzione di `AGENTS.md` e `docs/AGENTS.md`.
2. Verificare che siano presenti `docs/code-quality/` e
   `skills/gaia-complexity-reduction/`.
3. Non reintegrare manualmente `AGENTS_ADDENDUM.md`: nel pacchetto definitivo le
   sue regole sono gia presenti nel `AGENTS.md` root. Non creare `.hermes.md`.
4. Leggere `INSTRUCTIONS.md` e verificare branch, working tree e dipendenze.
5. Avviare il goal di bootstrap descritto in `HERMES_GOAL_PHASE_1.md`; il prompt
   ordina a Hermes di leggere la skill direttamente dal repository.
6. Approvare il Checkpoint 1 prima di rendere bloccanti i gate in CI.
7. Avviare un goal per singolo hotspot con
   `HERMES_GOAL_REFACTOR_ONE_HOTSPOT.md`.
8. Usare `PROGRESS.md` come fonte di verita tra sessioni.

## File

| File | Scopo |
| --- | --- |
| `PROMPT.md` | Brief tecnico completo per la prima implementazione |
| `PLAN.md` | Fasi, checkpoint e dipendenze |
| `PROGRESS.md` | Stato persistente e diario delle iterazioni |
| `INSTRUCTIONS.md` | Regole operative e stop condition |
| `HERMES_GOAL_PHASE_1.md` | Comando `/goal` per audit, tooling e baseline |
| `HERMES_GOAL_REFACTOR_ONE_HOTSPOT.md` | Comando `/goal` per un refactoring delimitato |
| `HERMES_LOOP_MONITORING.md` | Uso opzionale di `/loop`, solo per monitoraggio |
| `METRICS_AND_BASELINE.md` | Metriche, soglie, matching ed eccezioni |
| `HOTSPOTS.md` | Seed backlog da verificare con l'analisi AST |
| `VALIDATION.md` | Matrice di verifiche e definition of done |
| `AGENTS_ADDENDUM.md` | Copia di riferimento delle regole gia integrate nel `AGENTS.md` root |

La skill di progetto si trova in
`skills/gaia-complexity-reduction/SKILL.md`.

## Principi non negoziabili

- Nessuna modifica del comportamento per ridurre un numero.
- Nessun refactoring massivo o trasversale in una singola iterazione.
- Una sola unita di lavoro revisionabile per goal.
- La baseline legacy puo restare, ma non peggiorare.
- Il check ordinario e read-only; aggiornare la baseline richiede un comando
  esplicito e un diff revisionabile.
- Test mirati e copertura al 100% dei file runtime modificati.
- Nessun commit, push, merge o attivazione di branch protection senza richiesta
  esplicita.
- Le modifiche non correlate gia presenti nel working tree vanno preservate.

## Strategia di rollout

La Fase 1 e local-first: crea report, baseline e test dello strumento senza
rendere bloccante GitHub Actions. Questo evita di legare il programma a problemi
temporanei di billing o disponibilita CI. Il gate differenziale diventa
bloccante solo dopo la revisione del Checkpoint 1.
