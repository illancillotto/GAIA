# MCP — verifica finale del ciclo di sviluppo

Data: 2026-10-01. Base: `6b61fd27` (`origin/main` merge-base).
Esito: **FINAL QUALITY GATE — FAIL**. Il runtime MCP supera i propri gate;
lo smoke frontend fallisce e la build pulita non e completabile con i permessi
attuali. Non si dichiara PASS del ciclo complessivo.

## 1. Scope e implementazione

Verificati tutti i 26 file runtime inclusi dalla coverage MCP: package
`backend/app/modules/wiki/mcps/` e `backend/app/modules/wiki/router.py`.
Inclusi cinque file test `backend/tests/test_wiki*mc*.py`, target Make MCP,
`backend/requirements.txt`, `config/mcps/`, `docker-compose.mcp.yml` e dominio
documentale `domain-docs/mcps/`. Nessuna feature aggiunta durante questo audit.

Funzionalita: builder Docs con manifest/freeze/hash/chunk UUIDv5 e FTS5;
replica Data SQLite deterministica e read-only con dodici tool; trasporti stdio
e HTTP autenticato; bearer MCP TTL 60 s, scope effettivi e contesto isolato;
client SDK con fonti distinte; gateway autenticato Data-only; orchestrazione
dinamica con budget/provenance; provider `gpt-reserve` codex-lb; valutazione
offline Docs 32 query e Data 30 query; config/launcher/telemetria.

API nuove: `POST /wiki/mcp/token`, `GET /wiki/mcp/tools`,
`POST /wiki/mcp/chat`. Schemi `Correlation`/`AgentQuestion` con extra vietati;
scope derivati dai moduli e dalle sezioni GAIA nel DB, non dal modello.
Errori input API 422, autenticazione 401, provider/fonti indisponibili 503
minimizzati; errori tool tipizzati, assenza risultato esplicita.

Il ciclo non modifica modelli/tabelle GAIA operativi, servizi legacy o frontend.
`ApplicationUser`, permessi di sezione e autenticazione sono dipendenze esistenti.
Gli utenti, permessi e dispositivi VPN nei test di login persistono soltanto
nel database temporaneo. Nessun account operativo e modificato.

Dipendenza diretta nuova: `mcp==2.0.0`; `httpx2` e dipendenza del suo SDK.
OpenAI, Pydantic, JWT, FastAPI, SQLAlchemy e Uvicorn erano gia utilizzati.
`pip check` e resolver `pip install --dry-run -r backend/requirements.txt`
passano, senza installazioni. Il resolver propone aggiornamenti di dipendenze
gia presenti; il dry-run non li applica.

## 2. Matrice funzionalita → comportamento → test

Tutti i nomi sotto sono test eseguiti. Legenda: D = `test_wiki_docs_mcp.py`,
S = `test_wiki_data_mcp.py`, H = `test_wiki_mcp_http.py`,
I = `test_wiki_mcp_integration.py`, E = `test_wiki_mcp_evaluation.py`,
tutti sotto `backend/tests/`. Le parametrizzazioni coprono ciascun tool Data.

| Funzionalita | Comportamento atteso | Test |
| --- | --- | --- |
| Policy corpus | Esclusione archive/prompt/codice, path e symlink sicuri | D `test_policy_enforced_even_if_manifest_includes_document`, `test_rejects_unsafe_paths`, `test_symlink_cannot_escape_root` |
| Freeze | Hash/versione/ID stabili, rifiuto modifiche e chunk estranei | D `test_manifest_exclusion_duplicate_and_freeze`, `test_frozen_corpus_integrity`, `test_frozen_corpus_rejects_invalid_manifest_and_chunks` |
| Chunking | Heading/fence preservati, limiti documento/corpus/chunk | D `test_chunking_fences_headings_and_hard_cap`, `test_corpus_budget_and_encoding` |
| Docs retrieval | Filtri, ordine, provenance, metadata, cap e no-answer | D `test_search_filters_order_provenance_and_no_answer`, `test_section_metadata_domains_and_telemetry`, `test_metadata_cap_and_empty_document` |
| Seed/schema | Stesso seed stessi byte, FK/relazioni/importi coerenti | S `test_seed_determinism_counts_relations_and_money` |
| DB isolamento | Rifiuto DB operativo/symlink/corruzione, reset atomico, niente scritture | S `test_cannot_open_or_reset_operational_database`, `test_symlink_database_rejected`, `test_corrupt_database_fails_closed`, `test_readonly_database_and_guarded_reset`, `test_seed_failure_cleans_temporary_file` |
| Tool Data | Validazione strict, input extra/tipi errati, UUID inesistente | S `test_every_tool_valid_input_provenance_telemetry_and_permissions`, `test_all_tools_reject_extra_fields_and_wrong_types`, `test_unknown_record_is_not_found` |
| Query/paginazione | SQL parametrizzato, cap e cursori legati a tool/filtri/principal/dataset | S `test_every_filter_and_injection_is_parameterized`, `test_caps_and_pagination_for_every_collection`, `test_cursor_bound_to_tool_filters_dataset_and_principal`, `test_invalid_cursor_payloads` |
| Dominio | Soggetto/utenze/particelle/avvisi/righe/pagamenti, multi-hop | S `test_single_hop_and_multi_hop_ground_truth`; E `test_30_structured_ground_truth_queries` |
| Errori/log | Errori minimizzati, logging senza argomenti o record | S `test_database_and_internal_errors_are_minimized`; D `test_invalid_calls_are_audited_without_payloads` |
| Token/scope | Firma, TTL, audience/issuer/type, moduli e tutte le sezioni | H `test_tokens_validate_signature_audience_issuer_expiry_and_scope`, `test_permission_mapping_checks_module_and_each_section` |
| HTTP/concorrenza | Bearer obbligatorio, limiti/host, separazione principal e cleanup | H `test_authenticated_discovery_source_separation_and_error_handling`, `test_http_concurrent_principals_do_not_leak_context`, `test_bearer_context_isolated_during_overlapping_requests` |
| Client SDK | Namespace, scope e risposta remota coerenti, vero HTTP | I `test_client_calls_and_remote_contract_validation`, `test_source_urls_cannot_escape_internal_hosts`, `test_real_http_sdk_client_discovers_and_calls_both_sources` |
| Data-only | Nessuna discovery/session/chiamata Docs anche con docs.read | I `test_data_only_client_blocks_docs_sessions_and_all_tools`, `test_real_http_sdk_client_discovers_and_calls_both_sources` |
| Messaggi LLM | Evidenze Docs rifiutate, catalogo solo Data, assenza contenuti Docs | I `test_data_only_agent_rejects_docs_evidence_from_data_transport`, `test_real_http_sdk_client_discovers_and_calls_both_sources` |
| Provider | Modello fisso, config esplicita/riuso codex-lb, URL invalidi e config assente 503 | I `test_model_provider_uses_configured_codex_lb_and_routes_mounted`, `test_model_provider_fails_closed_without_configuration`, `test_model_provider_reuses_existing_codex_lb_credentials` |
| Agente/budget | Tool dinamici, provenance, JSON invalido, permission denied, cap/troncamento/no-tools | I `test_agent_selects_sources_and_returns_provenance`, `test_agent_invalid_model_arguments_are_source_errors`, `test_agent_permission_denial_no_tools_and_budgets`, `test_agent_batch_call_cap_and_model_ignoring_budget`, `test_evidence_hard_budget_truncates_without_mutating_source` |
| API/payload | Empty/missing/oversize/non-string/UUID invalidi/extra 422 prima di provider/fonti | I `test_gateway_rejects_invalid_payload_before_model_or_sources` (8 casi) |
| Gateway/errori | Token/correlation, tools/chat, provider/fonti/signing failures 503 | I `test_gateway_tokens_tools_chat_and_configuration_errors` |
| Login/persistenza/revoca | Login reale, contatore/dispositivo persistiti, revoca moduli/sezioni e inactive | I `test_gateway_real_login_permissions_revocation_and_inactive_user` |
| CLI/SDK | Entrypoint, config, cleanup anche errori, handshake stdio reale | D `test_cli_artifacts_and_cleanup`, `test_stdio_protocol_handshake_and_tools`; S `test_cli_seed_serve_cleanup_and_entrypoint`, `test_real_stdio_handshake_discovery_multi_hop_and_denied_scope`; I `test_http_cli_config_cleanup_and_entrypoint` |
| Evaluation | Ground truth freeze Docs32/Data30 e CLI riproducibile | E `test_frozen_repository_corpus_and_32_reviewed_queries`, `test_30_structured_ground_truth_queries`, `test_evaluation_cli_and_entrypoint` |

## 3. Test consolidati e coverage

Durante l'audit aggiunti otto casi pertinenti API invalidi, con controllo che
provider/fonti non vengano aperti; esteso il test di login reale per verificare
persistenza di contatore login, timestamp e dispositivo VPN.
Nessuna esclusione, test rimosso, test indebolito o test mirato solo ai numeri.

`make test-mcp QUALITY_PYTHON=backend/.venv/bin/python`: **164 passed**.
Coverage: **1080/1080 statement e 208/208 branch, 100%**, su 26 file runtime.
Zero linee escluse, mancanti o branch parziali. Nessuna porzione scoperta da
giustificare. JSON ignorato: `backend/coverage-mcp.json`.
Log: `/tmp/gaia-mcp-final-tests.log`.

## 4. Regression gate, build e type-check

| Controllo realmente eseguito | Risultato |
| --- | --- |
| Tutti `backend/tests/test_wiki*.py` legacy, esclusi i cinque MCP gia coperti | 716 passed, 262 warning legacy JWT (chiave test corta), nessuna failure |
| Frontend 14 suite unit Wiki (`npm run test:unit -- ...wiki...`) | 114 passed; warning jsdom di navigazione non implementata |
| `cd frontend && npm test` | FAIL: 12 passed, 6 failed; riferimenti legacy/file e aspettative smoke fuori scope MCP |
| `cd frontend && npm run build:clean` | FAIL prima di Next build: permessi negati su due cache `.next/cache/webpack/*-development/*.pack.gz_` |
| `cd frontend && npm run typecheck` | PASS, exit 0 |
| `cd frontend && npm run lint` | PASS con warning preesistenti hooks/unused e deprecazione next lint |
| `make lint-backend` con PYTHONPYCACHEPREFIX temporaneo | PASS; compileall e style ratchet di tutti i Python cambiati |
| Ruff check MCP/router/test e format check dei nuovi file | PASS, 30 file format conformi |
| `make complexity-ratchet` contro origin/main | PASS, findings vuoti, baseline/eccezioni invariate |
| `pip check`, resolver requirements dry-run | PASS |
| Compose override profilo MCP `config --quiet` | PASS, valori credenziali non stampati |
| `git diff --check` | PASS |

Le sei failure smoke comprendono API client `src/lib/api.ts` assente, layout
Catasto/Elaborazioni, dashboard/detail Utenze e export Catasto. Lo smoke stesso
e invariato rispetto a HEAD; `src/lib/api.ts` e assente anche a HEAD. Non si
attribuiscono queste failure al codice MCP, che non modifica frontend; non si
dichiara riprodotto l'intero smoke sul commit base. Nessuna correzione fuori scope.

La build richiesta ha tentato la pulizia di `.next`: parte degli artifact
generati viene rimossa prima del permission error. Non sono cambiati sorgenti
frontend o permessi; nessuna pulizia forzata/cache root eliminata.
Non e verificata la build di produzione ne l'immagine backend Python 3.11;
la validazione runtime locale usa Python 3.12.3. Questi limiti non sono PASS.

E2E MCP pertinente: HTTP SDK/stdio reali e gateway autenticato live su soli
dati sintetici, descritti nel runbook. Nessuna UI MCP introdotta: browser E2E
Wiki legacy non eseguito (richiede ambiente operativo e login, estraneo al
percorso sintetico). Test unit frontend e test API legacy verificano la
compatibilita delle superfici Wiki interessate dal mount router.

## 5. Integrazione live e limiti della misura

Run precedente nel medesimo ciclo: 30/30 query gateway live `gpt-reserve` con
login/permessi GAIA reali su utenti e DB sintetici, zero richieste Docs;
revoca/inactive PASS. Massimo 7 tool call e 2911 token stimati evidenze.
p50/p95/p99 16.152/30.736/34.886 s. Report ignorato
`runtime-data/mcps/evaluation/live-gateway.json`; log
`/tmp/gaia-mcp-live-gateway.log`. Non viene ripetuto: l'audit modifica solo
test/documentazione e artifact Graphify, nessun runtime.
Si verificano UUID/provenance/citazioni, non la correttezza semantica completa
del testo libero. Una singola misura non costituisce SLA o benchmark ripetuto.

## 6. Code quality, sicurezza e architettura

Metriche finali: 26 file, 84 callable, 26 warning, zero errori. Prima del
passaggio Data-only: 26/84/24 warning/zero errori. L'audit finale non modifica
runtime: metriche prima/dopo invariate, nessun refactoring classificato IMPROVED.
Complessita principali (cognitiva/ciclomatica): `markdown_sections` 24/12,
`load_corpus` 22/13, `evaluate_docs` 20/13, `financial_entities` 18/9,
`DataService._execute` 16/10, `WikiMCPAgent.answer` 15/11.
Warning residui trasparenti, non assorbiti nella baseline.
Report: `/tmp/gaia-mcp-final-metrics.{json,md}`.

Scansione AST dei corpi funzione con almeno tre statement: nessuna duplicazione
esatta. Non e una misura di duplicazioni semantiche. Review di import/callable,
entrance CLI e copertura non rileva dead code evidente; non viene dichiarata
una prova formale di assenza di dead code. Type safety: schemi Pydantic strict
e contratti SDK testati; nessun nuovo type-checker Python installato/configurato.

Responsabilita separate: corpus/retrieval, generator/DB/query/service, auth,
transport, client, agent, gateway, evaluation. Il coupling Data→Docs corpus
riguarda utility deterministiche JSON/hash/token, non retrieval documentale.
Nessuna duplicazione dei resolver permessi GAIA. Nessuna architettura parallela:
dominio backend sotto `backend/app/modules/wiki/`; HTTP/stdio sono adattatori
del package nel monolite. Frontend/API legacy e migration operative preservati.

Failure path verificati: bearer/expiry/scope, invalid input/cursor/path,
corpus/DB corrotti, tool sconosciuti, errori DB/provider/fonti, budget esaurito,
LLM che inventa Docs o ignora il budget, cleanup connessioni/contesto concorrente.
Query fisse parametrizzate, DB runtime read-only, scope lato server, segreti
separati, log minimizzati e provenance. Nessun documento reale inviato esternamente.
Il testo libero della domanda non e protetto da classificazione DLP: gli
esperimenti devono usare domande sintetiche. Manifest/hash rilevano modifiche
rispetto agli artifact, non sostituiscono la fiducia nell'operatore che li genera.
Budget riguarda tool/evidenze; non e un cap della spesa totale di inferenza.

## 7. Documentazione e Graphify

README, runtime/runbook, piani Data/Docs, architettura e privacy allineati a
Data-only/gpt-reserve; questa matrice e il registro finale di avanzamento del
ciclo MCP. Nessun nuovo PRD separato esiste nel dominio MCP: specifiche sono
analisi/schema/catalogo/piani, gia implementati. I PRD congelati di altri domini
non sono modificati. `docs/code-quality/PROGRESS.md` appartiene a lavoro
concorrente e non viene toccato; il ratchet ordinario e registrato qui.

`make graphify-wiki-code GRAPHIFY_CODE_FLAGS=--force` eseguito. La versione
locale conserva nodi preesistenti senza change list anche con --force: rilevato
e rimosso `local_model_client()` obsoleto mediante `_rebuild_code` con change
list routes/client, passato via override `GRAPHIFY_ENV` dello stesso target Make.
Nessuna patch/installazione di Graphify, nessuna chiamata LLM.
Finale: 878 nodi, 2103 edge, 57 comunita; `model_client()` presente, simbolo
vecchio assente, tutti gli endpoint degli edge esistenti. Log
`/tmp/gaia-mcp-final-graphify-prune.log`. Artifact ignorati, non versionati.
Graphify docs semantico non eseguito: violerebbe il divieto approvato di inviare
documenti reali al provider. Limite esplicito del grafo documentale finale.

## 8. Working tree e residui

MCP runtime/config/test sono ancora untracked; Makefile, router, requirements
e documentazione MCP sono modificati. Nessun commit/push/deploy effettuato.
Preservate modifiche concorrenti GATE/Presenze (servizi, script, test e runbook),
docs/code-quality, documentazione Poste/Elaborazioni/Ruolo e test frontend
Presenze. Non appartengono al ciclo MCP e non sono corretti o inclusi nel suo
perimetro coverage. Nessuna baseline/eccezione alterata.
Credenziali `.env`/`.env.graphify` ignorate, nessuna chiave copiata in file nuovi.
Coverage/report runtime/Graphify e log/script `/tmp` sono artifact locali,
non parte del codice versionabile. Lo snapshot cambia per lavoro concorrente:
non si assume un working tree pulito.
Snapshot finale: 44 voci (`27` modificate, `17` untracked), elenco in
`/tmp/gaia-mcp-final-working-tree.txt`. Scansione locale dei valori credenziali
esistenti sui file MCP/config/documentazione: zero corrispondenze; nessun valore
stampato. Compose quiet e diff whitespace ricontrollati dopo la documentazione.

Residui obbligatori per un futuro PASS complessivo: correggere/coordinare le
sei failure smoke frontend, rendere completabile la build pulita e rieseguirla;
la build di produzione resta non verificata. Non sono feature MCP residue.
Deploy intenzionalmente non eseguito; esperimenti optional embedding/hybrid/
reranking/cache, estensione corpus incerti, Operazioni e nuove fonti rimangono
fuori v1. Debito: 26 warning complessita, warning legacy test/lint, limite DLP
domande e misura live unica. Nessuna esclusione aggiunta per nasconderli.

**FINAL QUALITY GATE — FAIL**
