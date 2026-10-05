# Report recupero selettivo MCP — 2026-10-01

Questo report conserva lo snapshot del recupero iniziale. Analisi e correzione
successiva del multi-hop: `MULTIHOP_NOTICE_CODE_REVIEW.md`; non reinterpretare
i risultati live iniziali come risultati della versione corretta.

## Scope verificato e implementazione

Base `main@4a9af231`. Recuperati tutti i punti del piano selettivo: harness,
schedule/repetition/resume/retry, scoring, renderer Static sintetico, confronto
con l'agente corrente, trace/citazioni e preview UI. Vecchi server, auth e
orchestratori restano riferimenti, non vengono reintegrati. Freeze storici
immutati; nessuna modifica ai cinque pending change retrieval-only mainline.

Backend: cinque nuovi `backend/app/modules/wiki/mcps/experiment_*.py`.
Frontend: `frontend/src/app/wiki/mcp/page.tsx`. Nessuna nuova API: la preview
usa `POST /wiki/mcp/chat` e autenticazione/permessi/provenance esistenti. Nessun
modello ORM, migration, database operativo, dipendenza third-party o servizio
di dominio nuovo. Static FTS5 e journal sono artifact sperimentali locali.
Il monolite modulare e preservato, come server Docs separato e chat Wiki legacy.
Credenziali codex-lb esistenti caricate solo in memoria; no Ollama o Docs esterni.

Requisiti, comportamenti, matrice completa funzionalita → test, execution plan,
progress e residui: `SYNTHETIC_RECOVERY_PLAN.md`.

## Test aggiunti e risultati

- `backend/tests/test_wiki_mcp_experiment.py`: 21 casi eseguiti inclusi parametri;
  happy path, limiti/config invalidi, JSON/fatti/citazioni falsi, duplicati,
  assenza/accesso negato, scope, fonti/dataset errati, schedule/manifest,
  lock/fsync/resume, corruzione/interruzione, retry/esaurimento, CLI/cleanup,
  contratto Static e integrazione HTTP/SDK/bearer con namespace reali.
- `frontend/tests/unit/wiki-mcp-preview.test.tsx`: 3 test per auth, soli preset,
  endpoint/payload, loading, provenance, assenza, errori e reset della risposta.
- `frontend/tests/e2e/wiki-mcp-preview.spec.ts`: 1 test Chromium della pagina
  Next reale con auth/API sintetiche simulate. Non e un E2E contro backend operativo
  o provider reale. Next eseguito in copia temporanea, senza cambiare permessi/cache
  del repository. Prima esecuzione corretta nell'UI ma locator ambiguo per il
  route-announcer Next; test corretto, esecuzione finale PASS.
- `make test-mcp QUALITY_PYTHON=backend/.venv/bin/python`: **185 PASS**.
- Regressioni backend Wiki: **744 PASS**, warning legacy per chiave JWT di test corta.
- Regressioni frontend Wiki: **117 PASS / 15 suite** (114 esistenti + 3 nuove).
- `npm test`: **18 PASS** allo snapshot finale; smoke precedente rosso non
  viene reinterpretato retroattivamente, il suo report storico resta invariato.

## Coverage e code quality

Coverage backend MCP completa, router Wiki incluso: **1340/1340 statement,
250/250 branch, 100%**. Nuovi cinque file: **260/260 statement, 42/42 branch**,
zero esclusioni e zero linee/branch mancanti. Non modificati scope o soglie.
Preview: **23/23 statement, 10/10 branch, 5/5 funzioni, 23/23 linee, 100%**.

Ruff check e format-check dei cinque runtime e test nuovo: PASS. ESLint dei tre
file frontend nuovi: PASS senza warning. Lint frontend globale PASS con warning
legacy. Typecheck frontend finale PASS; un run precedente durante modifiche
concorrenti falliva in `presenze/inaz-sync-control.tsx`, non nel perimetro MCP.

Ratchet mirato contro baseline merge-base `origin/main`: **findings=[]**.
Metriche nuovi file (5 backend + 1 frontend): **29 callable, 0 error, 7 warning**.
Massimi rilevanti: `run_comparison` cognitiva 21 / ciclomatica 9 / nesting 4;
`score_answer` 14/11; costruttore journal 18/10. Le responsabilita di scoring
e record dei tentativi sono separate; il tool calling resta nell'agente esistente.
Prima dello sviluppo questi file non esistevano: nessun debito legacy trasferito.
Nessuna baseline/eccezione aggiornata; nessun refactor fuori scope. Controllo AST
dei corpi funzione nuovi con almeno tre statement: zero duplicati esatti.

Le metriche sopra descrivono lo sviluppo iniziale. Aggiornamento 2026-10-05:
le slice successive hanno eliminato i warning del runner/CLI; l'API Python
interna e ora `run_comparison(cases, executor, output)`. CLI e HTTP invariati,
304 test MCP verdi e coverage statement/branch 100%. Metriche prima/dopo,
compatibilita journal e limiti globali in `RUNNER_COMPLEXITY_REVIEW_2026-10-05.md`.

## Pilot live reale, distinto dai test simulati

5 casi generati dalla replica verificata `gaia-v1`: 3 lookup UUID, 1 multi-hop
avviso→pagamenti, 1 identificativo inesistente. 2 ripetizioni × 2 condizioni =
**20 esecuzioni complete, zero errori infrastrutturali nella prova finale**.
Modello `gpt-reserve` via codex-lb reale; per MCP server HTTP, SDK, bearer e
tool calling reali. Principal sintetico sperimentale, non login di utente operativo.
Solo fixture sintetiche anche per il server Docs: **zero richieste Docs**.

| Condizione | Risposte corrette | p50 ms | p95/p99 ms |
| --- | ---: | ---: | ---: |
| Static lexical RAG | 8/10 | 5361.684 | 20235.454 |
| MCP agent | 9/10 | 6748.624 | 18009.424 |

Static fallisce entrambi i multi-hop: il retriever non espande relazioni. MCP
risolve una ripetizione con i pagamenti corretti, nell'altra restituisce falsamente
`absent` dopo una sola chiamata; lo scorer la boccia. Non sono stati modificati
oracle/prompt o ritentate le risposte errate per rendere il risultato verde.
Questi sono risultati del modello, non failure dei test unitari. Nessuna garanzia
di risposta fattuale perfetta o superiorita statistica: cinque casi non bastano.
`gpt-reserve` e un alias provider, non un freeze verificato dei pesi del modello.

La prima prova del nuovo harness ha invece prodotto errori tecnici conservati:
catalogo controllato usando nomi non namespaced e payload Static con `tools=null` /
`tool_choice=none` rifiutato dal provider. Corrette le integrazioni, aggiunto test
HTTP/SDK reale; ripetuta la prova in un journal nuovo senza cancellare i fallimenti.

Artifact ignorati da Git:
- `runtime-data/mcps/evaluation/comparison-live-2026-10-01.jsonl`: tentativi tecnici falliti.
- `runtime-data/mcps/evaluation/comparison-live-2026-10-01-validated.jsonl`: prova finale,
  manifest/hash, tentativi, risposte, scoring, trace e evidenze sintetiche.
- Stesso basename `.summary.json`: aggregato della prova finale.

Hash dei file runtime della prova finale verificati uguali allo stato consegnato.
`make mcp-comparison-plan` eseguito offline con replica temporanea: PASS,
nessuna chiamata provider o scrittura del journal. CLI live esercitata dalla
prova reale con provider esistente e server isolato; nessun documento reale inviato.

## Regression gate globale e build

I gate globali includono lavoro concorrente esterno a questa tranche. Non sono
stati modificati per ottenere un PASS del recupero:

- `make lint-backend`: FAIL su import/variabili/formattazione Presenze e relativi
  test concorrenti. Primo run impedito anche da permessi su `__pycache__`; ripetuto
  con `PYTHONPYCACHEPREFIX=/tmp/gaia-recovery-pycache`, senza chmod o pulizia.
- `make complexity-ratchet`: FAIL, 27 finding esclusivamente Presenze (helper jobs,
  routes, schemas, import_jobs, operai_rules, parser, xlsm_export e UI Presenze).
  Il ratchet dei nuovi file MCP/frontend e separatamente verde.
- Suite unit frontend completa allo snapshot iniziale: 2680 PASS / 189 FAIL,
  failure solo in due suite Presenze. Riprova delle due suite senza test nuovi MCP:
  170 PASS / 22 FAIL durante successivi cambi concorrenti. Errore di mock API
  `listPresenzeCredentials` assente; non attribuito alla nuova pagina Wiki.
  Esecuzione completa finale: **2856 PASS / 22 FAIL, 245 suite PASS / 1 FAIL**,
  residui nella sola suite `presenze-giornaliere-page.test.tsx`. La variazione
  dei conteggi riflette le modifiche concorrenti, non fix opportunistici MCP.
- `npm run build:clean` nel repository: FAIL prima della compilazione per permessi
  di due cache webpack `.next`; nessun cambiamento ai permessi o sorgenti.
- Build clean della copia frontend temporanea usata dal browser: PASS, compilazione,
  type-check, generazione 160 pagine e `/wiki/mcp` inclusa. Non cancella il limite
  di permessi della build nel repository originale e non e un deploy.
- Compose: PASS con `docker compose -f docker-compose.yml -f docker-compose.mcp.yml
  config -q`. L'overlay MCP da solo non e un progetto autonomo: il primo controllo
  senza base era invalido, poi corretto senza modificare la configurazione.

Evidenze locali `/tmp/gaia-recovery-*.log`, metriche `.json/.md`. Working tree
concorrente non congelato: i conteggi non descrivono una release immutabile.

## Documentazione, Graphify e working tree

Aggiornati README MCP, runbook, architettura, privacy, valutazione e inventario;
nuovi piano/progress/matrice e questo report. Report del ciclo precedente e freeze
restano evidenze storiche, non riscritti come PASS. Nessuna strategia coverage o
perimetro gate cambiato; documenti code-quality/Poste/Presenze dell'utente preservati.

Graphify tramite `make graphify-wiki-code` e `make graphify-frontend`: PASS.
Wiki **921 nodi / 2229 edge / 67 comunita**; frontend **7159 / 17234 / 240**.
Componenti nuovi presenti e tutti gli endpoint degli edge validi. HTML frontend
non rigenerato per limite 5000 nodi, JSON/report aggiornati. Graphify docs remoto
non eseguito per il divieto di inviare documentazione reale; nessun grafo committato.

Scope della tranche: Makefile, cinque runtime, un test backend, pagina preview,
test unit/browser e documenti MCP. Tutte le altre modifiche, anche aggiunte durante
il lavoro, appartengono alle attivita concorrenti e restano intatte. Output coverage,
live, browser, graph e cache non inclusi; nessuna chiave configurata/versionata.
v1/v2 restano clean, mainline conserva esattamente i cinque pending change rilevati.
Nessun commit, push, merge o deploy eseguito in questa tranche.

## Problemi residui e debito

Gate globali e build nella directory originale non sono verdi. Resta l'errore
fattuale multi-hop del modello e il limite relazionale del baseline Static.
Prima di usare risultati in tesi servono campione/disegno statistico, approvazione
umana e freeze separato. I cinque pending change retrieval-only richiedono review
nel loro branch, non merge automatico. I warning di complessita sono sotto soglia
error; nessuna esclusione aggiunta per nasconderli.

FINAL QUALITY GATE — FAIL
