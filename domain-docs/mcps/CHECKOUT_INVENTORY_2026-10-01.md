# MCP — inventario dei checkout e lavoro residuo

Verifica locale read-only del 2026-10-01, prima del commit del runtime MCP
Data-only in `GAIA/`. Nessun merge, cherry-pick, modifica o commit nei checkout
esterni. Le tre directory sono worktree dello stesso repository Git, non copie
indipendenti. Nessuna chiamata al provider su documentazione reale.

## Risultato

Si, ci sono componenti sviluppati che non sono presenti nel runtime corrente
di `GAIA/`. Non sono file temporanei da cancellare: rappresentano una linea
sperimentale distinta, gia in parte consolidata nel branch
`feature/wiki-mcp-mainline`. Copiarne i package MCP nel runtime attuale
sovrascriverebbe contratti diversi. Non e autorizzata una migrazione implicita.

| Checkout | HEAD osservato | Working tree | Contenuto rilevante |
| --- | --- | --- | --- |
| `gaia-thesis-experiment-v1` | `e8962ff7` detached | Pulito | Freeze Git v1: agentic, policy LLM strutturata, budget/context/citation guard, static renderer, scoring, runner, freeze/leakage gate, manifest e corpus tesi |
| `gaia-thesis-experiment-v2-refreeze` | `2575a6f1` detached | Pulito | v1 piu final runner candidato, test runner, report e schedule v2 |
| `GAIA-wiki-mcp-mainline` | `e54cb51c`, branch `feature/wiki-mcp-mainline` | Cinque file modificati | Consolidamento tesi/mainline, server MCP PostgreSQL, auth per principal, preview UI, benchmark Docs, preflight runner, audit espansione domini |

Nessuno dei tre HEAD e antenato dell'HEAD `6b61fd27` di `GAIA/` alla verifica.
Questo prova che i loro commit finali non sono integrati per ancestry, non che
ogni modifica manchi: alcune parti possono essere gia condivise o convergenti.

## Freeze v1/v2

v1 contiene `backend/app/modules/wiki/agentic/`, `experiments/`,
`mcps/common/`, il modello SQLAlchemy/servizi Data e il renderer statico;
documentazione e artifact sotto `domain-docs/wiki/mcps/`.
Il manifest storico `EXPERIMENT_FREEZE_MANIFEST.md` mantiene stati
`PENDING_MANUAL` e `BLOCKED`: il commit denominato freeze non dimostra
l'approvazione umana finale di modello, corpus e ground truth.

Il diff v1→v2 contiene esattamente:

- `backend/app/modules/wiki/experiments/final_runner.py`;
- `backend/tests/test_wiki_final_runner.py`;
- `domain-docs/wiki/mcps/FINAL_RUNNER_IMPLEMENTATION_REPORT.md`;
- `domain-docs/wiki/mcps/generated/final-schedule-v2-candidate.json`.

Il candidato v2 descrive schedule da 360 condizioni, confronto static/agentic,
budget B1/B2/B3, raw result e scoring. Questi componenti non sono il benchmark
gateway da 30 query eseguito nel runtime Data-only corrente.
I worktree congelati sono puliti: nessun pezzo uncommitted rilevato in v1/v2.

## Mainline Wiki MCP: pezzi non ancora in GAIA

La documentazione `reports/2026-09-22-mcp-thesis-unification.md` registra il merge
di `thesis-experiment-v4-candidate` e l'autenticazione MCP nel branch unificato.
Non serve recuperare ciecamente v1/v2 sopra questa revisione piu recente.

Componenti distinti assenti dal ciclo Data-only corrente:

1. Orchestratore agentico con policy euristica/LLM strutturata, trace dettagliato,
   citation validator, context builder, budget e registry fonti.
2. Runner sperimentale/static RAG, renderer sintetico statico, scoring,
   freeze/leakage/corpus-cleanup gate e final runner/preflight/schedule.
3. Route `/wiki/agentic/query` con versioni dataset/corpus pinned e flag off di
   default; client in-process. Preview frontend `/wiki/agentic` e relativi test.
4. MCP common/authentication e modelli/services Data/Docs PostgreSQL con FTS,
   script di manifest/benchmark e test specifici.
5. Skill/hook di review espansione MCP, audit e decisioni di dominio;
   documentazione tesi e artifact congelati sotto `domain-docs/wiki/mcps/`.

In questo branch `final_runner.py` descrive anche un adapter locale llama-cpp
con alias Granite. Non e il provider `gpt-reserve` del ciclo attuale e non viene
avviato. Nessun cambio di provider o download modello effettuato.

L'audit del branch documenta coverage importato non completamente dimostrato,
ratchet verso origin/main non conforme (38 finding nell'ultimo report), ACL
Docs/E2E browser ancora aperti e freeze 4B.1 `PENDING_HUMAN_APPROVAL` su 60 query
e 138 documenti. Questi sono esiti documentati del branch, non gate rieseguiti
in questa ricognizione. Nessun benchmark finale o attivazione autorizzato qui.

### Cinque file non committati nel worktree mainline

| File | Modifica locale osservata |
| --- | --- |
| `backend/app/modules/wiki/agentic/policy.py` | Introduce `RetrievalOnlyAgentPolicy`: testo fisso e citazioni, senza sintesi dei contenuti |
| `backend/app/modules/wiki/routes/agentic.py` | Usa la policy retrieval-only nella route al posto di quella euristica |
| `backend/tests/test_wiki_agentic.py` | Aggiunge verifica che la policy non sintetizzi contenuti privati |
| `backend/tests/test_wiki_mcp_authentication.py` | Verifica policy selezionata e risposta fissa del confine HTTP |
| `domain-docs/mcps/MCP_EXPANSION_AUDIT_2026-09-28.md` | Corregge stato di attivazione, scope del worktree, gate aperti e contratto retrieval-only |

Sono preservati e non inclusi nel commit `GAIA/`: hanno un contratto diverso
e appartengono al worktree mainline. Non viene dichiarata la loro validazione
attuale dai test del nuovo runtime.

## Confronto con il ciclo appena completato

| Aspetto | GAIA corrente Data-only | Linea tesi/mainline |
| --- | --- | --- |
| Storage Data | SQLite dedicato sintetico, DB operativo irraggiungibile | Modelli/servizi SQLAlchemy e schema sperimentale PostgreSQL |
| Docs | Snapshot manifest e FTS5, server interno separato | Modelli/indexer/manifest/chunker e FTS PostgreSQL |
| Consumatore | `/wiki/mcp/token`, `/tools`, `/chat`, SDK HTTP con bearer TTL | `/wiki/agentic/query` in-process, runner stdio |
| Provider/risposta | gpt-reserve codex-lb, solo Data sintetico | Policy euristica/strutturata; retrieval-only locale in pending changes, runner con adapter separato |
| Valutazione | 32 retrieval Docs offline; 30 Data offline e 30 gateway live | Ground truth tesi, budget B1/B2/B3, static/agentic, schedule/raw/scoring |
| UI | Nessuna UI MCP nuova | Preview `/wiki/agentic` |
| Confine privacy | Docs escluso dal catalogo/session/call/token del gateway esterno | Docs consultabile internamente; contratti experiment e approvazioni distinti |

Anche file con lo stesso path, come `mcps/data/server.py` e `generator.py`,
non sono byte-identici. Un merge indiscriminato rischierebbe perdita del
guardrail Data-only, dei test di coverage oppure dei freeze scientifici.

## Documentazione di sviluppo verificata

Il corpus autorevole del runtime attuale e `domain-docs/mcps/`: README,
architettura, privacy, cataloghi/schema, piani di implementazione e test,
`RUNTIME_AND_VALIDATION.md`, `FINAL_DEVELOPMENT_REVIEW.md`.
La documentazione tesi `domain-docs/wiki/mcps/` non e presente qui e non deve
essere considerata implicitamente implementata dal nuovo runtime.
README aggiornato con questo inventario; piani distinguono core completato e
residui opzionali. L'audit finale e storico: registra FAIL dello smoke/build
frontend nel suo snapshot, non impedisce il commit esplicitamente richiesto.
Non viene reinterpretato come successo globale in base a modifiche concorrenti.

## Recupero residuo e decisioni

Aggiornamento dopo il recupero autorizzato: runner/scoring/renderer e preview
sono adattati selettivamente al contratto corrente, senza merge dei checkout.
Stato: `SYNTHETIC_RECOVERY_PLAN.md` e `SYNTHETIC_RECOVERY_REPORT.md`.
Le decisioni sui freeze e sui cinque pending change restano valide;
nessun artifact storico e stato modificato.

- Conservare i due freeze storici: nessuna pulizia/rimozione richiesta.
- Conservare i cinque pending change mainline; commit/review nel loro branch
  richiedono un'attivita esplicita separata dal commit corrente.
- Per proseguire la tesi: riconciliare il runner/renderer/scoring piu recenti
  con il nuovo contratto Data-only mediante una change dedicata e testata;
  mantenere byte/hash degli artifact congelati e approvazioni manuali.
- Per unificare la UI/route: decidere quale contratto e autorevole; non
  affiancare automaticamente due orchestratori o abilitare Docs nel gateway.
- I gate e la freeze approval della linea mainline restano residui reali della
  tesi, anche se il runtime MCP corrente e implementato e verificato.

La ricognizione non ha eseguito servizi, test o provider nei worktree esterni;
ha verificato Git history/stato, differenze e documentazione/codice selezionato.
