# MCP — verifica successiva al commit, 2026-10-01

## Scope e implementazione

Verifiche successive a `345cd7ab`; snapshot finale HEAD `2048a8e1` con working
tree condiviso e modifiche concorrenti. Nessun nuovo commit, push o deploy.
I report precedenti sono evidenze storiche e non sono stati riscritti.

Runtime modificato soltanto in `backend/app/modules/wiki/mcps/`:

- `experiment_scoring.py`: l'assenza non richiede piu che tutte le ricerche
  intermedie siano vuote. Un avviso esistente senza pagamenti e un caso valido;
  servono evidenze senza errori e un terminale vuoto pertinente, completo e senza
  cursor. Il parent diretto e derivato dal catalogo `QUERIES` esistente.
- `experiment_cases.py`: il contratto chiarisce che status e citazioni riguardano
  i record richiesti, non quelli intermedi. Citazioni extra restano invalide.
- Test di dominio con DataService reale e modello simulato: tre pagamenti con
  cursori reali, avviso senza pagamenti, input/entita non pertinenti, errori,
  truncation, cursor residuo, diniego e budget esaurito.
- E2E opt-in aggiunto al test esistente: login GAIA reale, gateway e MCP HTTP
  reali, `gpt-reserve` via configurazione codex-lb esistente. Il forwarding
  Playwright inoltra le richieste al backend isolato: non simula le risposte.

Nessuna nuova dipendenza, API, tabella, migrazione, servizio o architettura
parallela. Nessun cambiamento al generatore sintetico, alla chat Wiki legacy,
al server Docs separato o ai permessi. Fixture auth/DB isolate; nessun DB operativo.
Nessuna credenziale stampata o versionata. Nessun documento reale inoltrato.

## Matrice funzionalita → comportamento → test

La matrice completa del recupero resta in `SYNTHETIC_RECOVERY_PLAN.md`.

| Funzionalita | Comportamento | Test aggiunto/modificato |
| --- | --- | --- |
| Multi-hop paginato | Avviso → tre pagine, quattro chiamate, UUID/provenance distinti | `test_agent_multiple_payments_follows_real_cursors` |
| Assenza multi-hop | Avviso positivo + pagamenti vuoti valido; entita errata, errori, troncamento/cursor, status/citazioni sbagliati respinti | `test_no_payments_scoring_requires_terminal_entity` |
| Autorizzazioni/budget | Denial, max_calls=1, evidence_tokens=100 non diventano falsa assenza valida | `test_agent_denial_and_exhaustion_do_not_become_valid_absence` (tre parametri) |
| Browser live | Login, JWT, risposta subject UUID esatto, assenza con tool calling e provenance vuota | `live synthetic login to gateway to MCP to model` |
| Regressioni browser | Preset-only, API MCP simulata, 503 e reset | `synthetic preview uses MCP only and handles source failure` |
| Privacy invariata | Discovery/invocazioni/messaggi Data-only, dataset remoto verificato | `test_verified_sources_reject_docs_before_invocation_and_wrong_dataset`, `test_comparison_uses_real_sdk_catalog_and_http_tools_without_docs` |

## Risultati dei controlli

| Controllo eseguito | Esito |
| --- | --- |
| `make test-mcp QUALITY_PYTHON=backend/.venv/bin/python` | 191 PASS |
| Coverage MCP/router, branch inclusi | 1351/1351 statement, 252/252 branch, 100%, zero esclusioni |
| Coverage runtime modificato | cases 20/20 statement, 2/2 branch; scorer 46/46 statement, 4/4 branch |
| Regressioni backend `test_wiki*.py` | 751 PASS; warning preesistenti su chiavi JWT di test |
| Frontend `npm test` | 251 suite, 3084 test PASS |
| Frontend smoke | 18 PASS |
| Frontend type-check/lint | PASS; warning lint legacy |
| `make quality-test` | 83 PASS |
| Ruff check/format runtime e test MCP modificati | PASS |
| Ratchet mirato cases/scorer vs merge-base `origin/main` | PASS, findings vuoti, baseline invariata |
| `make lint-backend` globale | FAIL su modifiche concorrenti: import/router, bootstrap e test Presenze/Dotazioni; due file da formattare |
| `make complexity-ratchet` globale | FAIL, 18 finding su Presenze, user/bootstrap e frontend users, nessuno nei file MCP modificati |
| `npm run build:clean` nel checkout | FAIL prima della compilazione: cache `.next` root-owned, permission denied |
| Build clean in copia frontend isolata con dipendenze esistenti | PASS, non sostituisce il gate del checkout |
| Playwright Chromium preview | 2 PASS: uno live opt-in e uno simulato; live eseguito anche una seconda volta |
| Compose base + overlay MCP e pip check | PASS |
| `make graphify-wiki-code` | PASS, 922 nodi, 2232 edge, 73 community |
| `git diff --check` | PASS |

Log locali minimizzati: `/tmp/gaia-close-tests-clarified.log`,
`/tmp/gaia-close-wiki-all.log`, `/tmp/gaia-close-frontend-unit.log`,
`/tmp/gaia-close-browser-test-final.log`, `/tmp/gaia-close-lint-final.log`,
`/tmp/gaia-close-ratchet-final.log`, `/tmp/gaia-close-build-isolated.log`.
Non e stata eseguita l'intera suite backend di tutti i domini o tutti gli E2E.
Le evidenze fotografano il workspace durante le esecuzioni, non certificano
eventuali modifiche concorrenti successive.

## Qualita e architettura

Nessuna esclusione coverage o baseline aggiornata per mascherare failure.
Scorer: quattro callable, zero errori di complessita, un warning per
`verified_absence` (ciclomatica 10, soglia warning 10; cognitiva 11).
`score_answer`: ciclomatica 9, cognitiva 12. Nessun refactor fuori scope.
Non emergono nuove duplicazioni, dead code o accoppiamenti con altri domini:
la dipendenza dal catalogo Data e interna al modulo Wiki del monolite.
Il check di assenza verifica struttura/entita dell'evidenza: non e una prova
indipendente della pertinenza semantica dei filtri scelti dal modello.

Graphify codice aggiornato tramite Make, artefatti non versionati. Il grafo docs
non e stato rigenerato semanticamente: i corpus documentali non sono dati
sintetici e il vincolo privacy vieta di inviarli al provider esterno.

## Pilot live ampliato: risultati non selezionati

Tre seed (`gaia-v1`, `synthetic-expanded-seed-2`, `synthetic-expanded-seed-3`),
cinque casi per seed, due condizioni: 30 esecuzioni per pilot. Casi: primo
avviso pagato, avviso pagato non iniziale, avviso senza pagamenti, tre pagamenti
su pagine limit=1, avviso inesistente. Fixture soltanto sintetica: un pagamento
e diviso in tre preservando il totale, senza cambiare il generatore congelato.

| Pilot | MCP strict | Static strict | Errori infrastruttura | Richieste Docs |
| --- | --- | --- | --- | --- |
| Contratto iniziale | 8/15 | 3/15 | 0 | 0 |
| Contratto chiarito, nuovi journal | 14/15 | 3/15 | 0 | 0 |

Il primo pilot ha evidenziato tre status/citazioni errati sugli avvisi senza
pagamenti e quattro citazioni parent extra. Dopo la chiarificazione del
contratto resta una failure reale: seed 3, `paginated-three`, UUID del primo
pagamento copiato erroneamente nella citazione. I record/fatti sono corretti
15/15 in entrambi i pilot; nel secondo paginazione 3/3 con quattro chiamate,
avvisi senza pagamenti 3/3 e avvisi inesistenti 3/3. Non si dichiara 15/15 strict.

I journal originali sono preservati; nessun retry delle risposte sbagliate o
indebolimento dello scorer. Secondo pilot: tutti i dieci hash runtime di ciascun
manifest coincidono con il codice corrente. Il primo pilot usa il contratto
precedente e non va aggregato con il secondo come un unico protocollo congelato.

Artefatti ignorati in `runtime-data/mcps/evaluation/`:
`expanded-multihop-seed-{1,2,3}.jsonl`, `expanded-multihop-summary.json`,
`expanded-contract-clarified-seed-{1,2,3}.jsonl`,
`expanded-contract-clarified-summary.json`.

Guardrail live separati: scope Ruolo escluso dalla discovery e invocazione
diretta negata prima della rete; max_calls=1 rispettato (una chiamata, 185 token
evidenze); budget=100 rispettato (una chiamata, 85 token). Le risposte incomplete
non passano l'oracle. Zero Docs. Report `guardrails-live-close.json`.
Questa prova precede la chiarificazione del contratto.

Browser live: due login reali, quattro chat, 28 richieste Data e zero Docs nel
report aggregato `browser-live-close.json`. Override della sola dipendenza DB
per autenticazione sintetica; auth/permessi/persistenza device reali.
Server/DB temporanei arrestati e frontend isolato fermato dopo le prove.
Il test live richiede `GAIA_MCP_LIVE_BROWSER=1` e
`GAIA_MCP_SYNTHETIC_BACKEND_URL=http://127.0.0.1:<porta>` con fixture isolata;
non va puntato a dati operativi. Senza opt-in risulta esplicitamente skipped.

## Checkout, protocollo tesi e residui

Ricontrollati: v1 e v2-refreeze puliti; Wiki-mainline conserva i cinque file
pending inventariati. Implementano una policy retrieval-only interna, non una
sintesi fattuale compatibile automaticamente col nuovo agente esterno. Nessuna
importazione, modifica o commit nei checkout storici.

Proposta, non approvazione: mantenere questi 3 seed × 5 casi come pilot
diagnostico; definire separatamente campione definitivo, ripetizioni, criteri
strict, baseline RAG, policy degli errori e alias/versione provider prima del
freeze umano. `gpt-reserve` non certifica pesi immutabili. I runner ampliati
sono script locali effimeri: prima del freeze serviranno fixture/runner
versionati e una prova riproducibile sotto protocollo approvato.

Residui: errore di citazione live 1/15; gate globali concorrenti; permessi cache
build del checkout; Graphify docs non verificato; approvazione/freeze e disegno
statistico della tesi; review separata della policy retrieval-only storica.
Non e stata introdotta una nuova feature per correggere automaticamente gli
UUID del modello o normalizzare risposte errate.

Working tree: quattro file codice/test MCP e tre documenti aggiornati piu
questo report. Modifiche concorrenti AGENTS/Makefile, Dotazioni, users, GATE,
Presenze, quality e Poste preservate, non staged e non incluse nel ciclo MCP.
Artefatti live/coverage/Graphify ignorati; nessuna configurazione credenziali
modificata. Stato dettagliato da ricontrollare prima di un eventuale commit.

## Follow-up: diagnosi della citazione e gate ricontrollati

Snapshot HEAD `61f992a0`, successivo commit concorrente Presenze. Gli esiti della
tabella precedente restano storici; questo follow-up non cambia il pilot live.

Il primo pagamento del caso seed 3 ha UUID
`0cce0d0a-afd2-5c03-98f7-1dde0e5efd49` sia nei risultati tool sia nel record
restituito dal modello. La citazione invece contiene
`0cce0d0a-afd2-5c7d-93fd-1dde0e5efd49`: due segmenti sono quelli di un altro
pagamento. Questo UUID non compare nella provenance. Diagnosi: errore di copia
nella risposta del modello, non corruzione del database, della paginazione o
della provenance da parte del client. Tutti gli hash runtime del manifest
coincidono ancora con il codice corrente.

Nuovo test `test_model_payment_citation_corruption_is_preserved_and_rejected`
con due varianti: segmenti copiati da un altro pagamento, oppure riferimento
duplicato a un pagamento noto. Esegue DataService e agente reali con un modello
simulato che produce il difetto: fatti/record restano corretti, citazioni e
score complessivo falliscono, il testo grezzo non viene normalizzato. Non e
una nuova prova live e non implica che il modello abbia smesso di sbagliare.

- `make test-mcp`: **193 PASS**, 1351/1351 statement e 252/252 branch, **100%**.
- Ruff check/format del test: PASS; `git diff --check`: PASS.
- Ratchet runtime MCP contro `origin/main`: PASS, nessun finding.
- Ratchet globale: FAIL, ora 16 finding estranei al MCP nei domini
  Presenze/user/bootstrap/frontend users. Baseline non modificata.
- Lint globale inizialmente bloccato anche da `__pycache__` root-owned. Ripetuto
  con `PYTHONPYCACHEPREFIX=/tmp/gaia-citation-pycache` senza toccare le cache
  concorrenti: rimane un solo I001 in
  `backend/tests/test_presenze_operations_postgres.py:3`, fuori scope.
- `make graphify-wiki-code`: PASS, nessun cambio di topologia AST.

Cache frontend precedente preservata integralmente in
`/tmp/gaia-mcp-next-cache-preserved.jUBGmw/.next`, sullo stesso filesystem;
nessun sudo, cancellazione della vecchia cache o stop/deploy di container.
La nuova `npm run build:clean` nel checkout e terminata **PASS** (exit 0),
compilazione riuscita e 161/161 pagine generate. Restano warning lint legacy,
nessun nuovo errore MCP. Questo risultato sostituisce il blocco cache del
checkout nella tranche corrente, senza riscrivere il risultato storico.

Nessun cambio runtime ulteriore per sanare un errore generativo: normalizzare
gli UUID, ritentare risposte scorrette o rilassare il criterio scientifico
maschererebbe il risultato. Resta necessario decidere separatamente se una
futura feature di validazione delle risposte sia desiderata; non e parte di
questa verifica. Runner/fixture sperimentali versionati e freeze umano restano
residui espliciti del protocollo tesi, non attivita approvate automaticamente.

Log follow-up: `/tmp/gaia-citation-regression.log`,
`/tmp/gaia-citation-coverage.log`, `/tmp/gaia-citation-lint-clean-cache.log`,
`/tmp/gaia-citation-ratchet.log`, `/tmp/gaia-citation-ratchet-target.log`,
`/tmp/gaia-citation-build.log`, `/tmp/gaia-citation-graph-refresh.log`.
Modifiche concorrenti preservate; nessun commit/push/deploy.

FINAL QUALITY GATE — FAIL
