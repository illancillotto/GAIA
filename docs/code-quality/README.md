# GAIA Code Complexity Program

Questo pacchetto applica a GAIA una riduzione della complessita incrementale,
misurabile e verificabile. La skill e parte del repository e non viene
installata nel profilo globale dell'agente.

La modalita predefinita e il quality ratchet sugli sviluppi ordinari. I
refactoring dedicati restano disponibili per un solo hotspot alla volta, ma non
costituiscono una campagna separata dal lavoro di prodotto. La decisione e le
evidenze dell'esperimento iniziale sono in `QUALITY_RATCHET.md`.

## Ordine di utilizzo

1. Verificare che siano presenti `docs/code-quality/` e
   `skills/gaia-complexity-reduction/`.
2. Non reintegrare manualmente `AGENTS_ADDENDUM.md`: nel pacchetto definitivo le
   sue regole sono gia presenti nel `AGENTS.md` root. Non creare `.hermes.md`.
3. Leggere `QUALITY_RATCHET.md`, `INSTRUCTIONS.md` e verificare branch, working
   tree e dipendenze.
4. Avviare il goal di fondazione descritto in `HERMES_GOAL_PHASE_1.md`; il prompt
   ordina a Hermes di leggere la skill direttamente dal repository.
5. Approvare baseline e Checkpoint 1 prima di rendere bloccanti i gate in CI.
6. Applicare la modalita ratchet della skill durante gli sviluppi ordinari.
7. Solo se necessario, avviare un goal per singolo hotspot con
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
| `QUALITY_RATCHET.md` | Decisione, modalita operative e rollout |
| `AGENTS_ADDENDUM.md` | Copia di riferimento delle regole gia integrate nel `AGENTS.md` root |

La skill di progetto si trova in
`skills/gaia-complexity-reduction/SKILL.md`.

## Comandi

| Comando | Scopo |
| --- | --- |
| `make quality-test` | esegue tutta la suite `tests/code_quality` |
| `make complexity-report` | rigenera report JSON e Markdown |
| `make complexity-check` | verifica lo stato contro la baseline corrente |
| `make complexity-ratchet BASE_REF=origin/main` | confronta i file cambiati con la baseline del merge-base |
| `make complexity-baseline` | sincronizza esplicitamente la baseline dopo il ratchet |
| `make complexity-baseline-verify` | verifica la riproducibilita della baseline corrente |
| `make complexity-ci-gate` | esegue la sequenza autorevole per CI |

`complexity-ratchet` e il controllo anti-regressione autorevole.
`complexity-check` da solo non basta, perche consulta la baseline presente nel
working tree.

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

La fondazione e local-first: crea report, baseline e test dello strumento senza
rendere bloccante GitHub Actions. Il gate non puo essere attivato nella stessa
change che introduce la prima baseline, perche il confronto autorevole richiede
che una baseline revisionata esista gia al merge-base. L'integrazione workflow
e quindi una change successiva e separata. L'enforcement vive nel workflow
dedicato `.github/workflows/code-quality.yml`, evitando implementazioni duplicate
nei workflow applicativi backend e frontend.
