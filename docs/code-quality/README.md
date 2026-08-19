# GAIA Code Complexity Program

Questo pacchetto prepara GAIA a ridurre la complessita in modo incrementale,
misurabile e verificabile con Hermes Agent. La skill e parte del repository e
non viene installata nel profilo globale di Hermes.

Non contiene un refactoring applicativo gia eseguito. Contiene il contratto di
lavoro, la baseline policy, i checkpoint, i prompt e una skill Hermes pronta da
leggere dal checkout. La prima esecuzione costruisce e valida l'infrastruttura;
le esecuzioni successive intervengono su un solo hotspot per volta.

## Ordine di utilizzo

1. Verificare che siano presenti `docs/code-quality/` e
   `skills/gaia-complexity-reduction/`.
2. Non reintegrare manualmente `AGENTS_ADDENDUM.md`: nel pacchetto definitivo le
   sue regole sono gia presenti nel `AGENTS.md` root. Non creare `.hermes.md`.
3. Leggere `INSTRUCTIONS.md` e verificare branch, working tree e dipendenze.
4. Avviare il goal di bootstrap descritto in `HERMES_GOAL_PHASE_1.md`; il prompt
   ordina a Hermes di leggere la skill direttamente dal repository.
5. Approvare il Checkpoint 1 prima di rendere bloccanti i gate in CI.
6. Avviare un goal per singolo hotspot con
   `HERMES_GOAL_REFACTOR_ONE_HOTSPOT.md`.
7. Usare `PROGRESS.md` come fonte di verita tra sessioni.

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

## Tool locale di complessita

La Fase 1 introduce una CLI deterministica in:

```text
tools/code_quality/complexity.py
```

Il motore usa:

- Python: `ast` della standard library;
- JS/TS/JSX/TSX: parser AST reale tramite `@babel/parser`, invocato dal helper
  locale `tools/code_quality/js_ast_metrics.mjs` usando le dipendenze gia
  presenti in `frontend/node_modules`, senza modificare `package.json` o lockfile.

Output versionati:

```text
config/code-quality/complexity-baseline.json
config/code-quality/complexity-exceptions.json
reports/code-quality/complexity-report.json
reports/code-quality/complexity-report.md
```

## Comandi locali

| Comando | Effetto | Read-only |
| --- | --- | --- |
| `make quality-test` | Test sintetici del tool | si |
| `make complexity-report` | Rigenera report JSON/Markdown; accetta `REPORT_JSON=/tmp/... REPORT_MD=/tmp/...` per verifiche temporanee | no di default, read-only rispetto al repo se usa output temporanei |
| `make complexity-check` | Confronta checkout contro baseline | si |
| `make complexity-changed BASE_REF=origin/main` | Controllo differenziale via merge-base | si |
| `make complexity-baseline` | Aggiorna baseline solo se non assorbe regressioni | no |
| `make complexity-baseline-verify` | Verifica riproducibilita baseline ignorando timestamp/commit | si |
| `make complexity-ci-gate` | Esegue il gate CI differenziale tramite `scripts/complexity_ci_gate.sh` | si |
| `make lint-backend` | Compileall backend/test/worker | si |
| `make lint-frontend` | `npm run lint` da frontend | si |
| `cd frontend && npm run typecheck:from-root` | Typecheck runtime frontend con `frontend/tsconfig.typecheck.json` e cache fuori repo | si |

Codici di uscita della CLI:

- `0`: controllo superato;
- `1`: nuove violazioni o peggioramenti;
- `2`: errore di configurazione/uso, baseline ambigua, eccezioni non valide o
  merge-base non disponibile.

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

La Fase 1 e stata local-first: ha creato report, baseline e test dello strumento
senza rendere bloccante GitHub Actions. Dopo l'approvazione formale del
Checkpoint 1, la Fase 2 ha attivato il gate differenziale nei workflow backend e
frontend.

Gate CI attivo in Fase 2:

1. i workflow includono `tools/code_quality/**`, `config/code-quality/**`,
   `reports/code-quality/**`, `docs/code-quality/**`, `tests/code_quality/**`,
   `scripts/complexity_ci_gate.sh` e `Makefile` nei path trigger;
2. `fetch-depth: 0` e mantenuto per rendere disponibile il merge-base;
3. le PR usano `BASE_REF=origin/${{ github.base_ref }}`; lo script fallisce con
   exit `2` e messaggio esplicito se il merge-base non e disponibile;
4. `scripts/complexity_ci_gate.sh` riusa la CLI locale: report temporaneo,
   `complexity-check`, `complexity-changed`, `complexity-baseline-verify` e
   `validate-exceptions`;
5. il gate e bloccante solo per nuove violazioni error-level, peggioramenti del
   legacy, baseline tampering, eccezioni/esclusioni non valide o errori di
   configurazione; il debito legacy invariato resta consentito.
