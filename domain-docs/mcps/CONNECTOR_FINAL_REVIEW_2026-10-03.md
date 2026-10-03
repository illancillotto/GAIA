# Verifica finale — consenso GAIA e connettore MCP

Data: 2026-10-03. Checkout verificato: `main@b8929feb`.
Baseline autorevole del ratchet: merge-base `origin/main`, `6b61fd27`.
Stato complessivo: **FINAL QUALITY GATE — FAIL**.

## Scope e stato del prodotto

Questa verifica chiude la tranche OAuth + consenso + gateway sintetico,
non tutte le modifiche concorrenti del checkout. Sono verificati integralmente
i sette runtime `oauth_store.py`, `oauth_provider.py`, `oauth_http.py`,
`oauth_gaia.py`, `connector.py`, `connector_config.py`, `connector_budget.py`
in `backend/app/modules/wiki/mcps/` e i tre runtime frontend
`features/wiki/mcp-consent.tsx`, `features/wiki/mcp-consent-api.ts`,
`app/mcp/consent/page.tsx`. Inclusi test OAuth/connector/consenso, target Make,
configurazione di esempio, overlay Compose, Dockerfile e template Nginx.

- [x] OAuth authorization-code PKCE S256 con client pubblici preregistrati.
- [x] Riutilizzo login/sessioni/permessi GAIA; consenso esplicito allow/deny.
- [x] Discovery OAuth e protected-resource, listener Data-only stateless.
- [x] Dataset verificato contro il generatore, readonly, senza Docs/inspection.
- [x] Budget persistenti per utente, audit/provenance dei tool autorizzati.
- [x] Flag backend/frontend disattivate per default e configurazione fail-closed.
- [ ] Quality gate complessivo: build, browser e suite MCP completa non verdi.
- [ ] Pubblicazione HTTPS, configurazione client Claude approvata e test live.

Nessuna feature nuova o modifica runtime durante la verifica. Aggiunto solo
un test pertinente di protezione Host/Origin/content-type e persistenza token
al riavvio. Nessun commit, push, deploy, nuova CA o attivazione effettuati.

## Architettura, dipendenze e dati

La logica rimane nel dominio Wiki del monolite modulare. Il listener separato
riusa immagine backend, DataService, AuditStore, CallContext e autenticazione
canonica: non introduce un servizio di dominio parallelo. La UI rimane in
`features/wiki`; `/mcp/consent` e una route di callback autorizzativo, non una
seconda implementazione Wiki. La sua posizione fuori `/wiki` e intenzionale
e vincolata da configurazione/proxy; non viene rinominata durante l'audit.

Dipendenze riusate: MCP SDK, Starlette, Pydantic, HTTPX, SQLAlchemy, SQLite,
React/Next.js e API login esistenti. Nessuna dipendenza/migration GAIA aggiunta
in questa tranche; `pip check` passa. `frontend/package-lock.json` contiene
una modifica preesistente fuori scope, non inclusa nella verifica MCP.

Database OAuth dedicato 0600: grants opachi memorizzati tramite SHA256 e
counter per principal pseudonimo. Database audit separato; database Data
readonly con manifest confrontato col generatore. Utenti, permessi, device
VPN e login nei test usano solo SQLite temporanea sintetica. Le tabelle
operative GAIA sono dipendenze di autenticazione, non sorgenti dei tool.

API e flusso completo sono documentati in `CONNECTOR_RUNTIME_2026-10-03.md`.
Nessuna modifica al login legacy, al server Docs separato o alla chat Wiki.
Il gateway non chiama modelli: Claude ricevera soltanto risposte sintetiche.
Il percorso agente gpt-reserve preesistente e verificato con modello simulato,
non con una nuova prova live; nessun Ollama o documento reale inviato.

## Matrice funzionalita → comportamento → test

Legenda: C = `backend/tests/test_wiki_mcp_connector.py`,
O = `backend/tests/test_wiki_mcp_oauth.py`,
I = `backend/tests/test_wiki_mcp_integration.py`,
D = `backend/tests/test_wiki_mcp_discovery.py`,
F = `frontend/tests/unit/mcp-consent.test.tsx`.
I/D verificano anche invarianti preesistenti da preservare.

| Funzionalita | Comportamento atteso / failure path | Test pertinente |
| --- | --- | --- |
| Config opt-in | Default 404 senza DB; env errati/client duplicati/segreti/scope non Data rifiutati | C `test_configuration_fail_closed_and_preapproved_clients`, `test_disabled_and_failed_startup_do_not_expose_routes` |
| HTTPS e callback | URL puliti, resource/issuer e route esatti, client approvati | O `test_https_required`, `test_configuration_requires_preapproved_public_clients`, `test_authorization_is_data_only_and_bound`; C configurazione |
| Store grants | Solo hash, file dedicato 0600, scadenza, consume atomico, rollback | O `test_store_security_transactions_and_expiry`, `test_consumption_races_and_atomic_pair_rollback` |
| Consenso backend | Richiesta valida/scaduta, allow/deny, cambio configurazione, scope attuali | O `test_consent_expiration_denial_and_configuration_change`, `test_http_sdk_pkce_resource_consent_and_revocation` |
| PKCE/token API | Code/redirect/verifier/resource esatti, resource duplicata errata, no password grant | O `test_http_sdk_pkce_resource_consent_and_revocation` |
| Token lifecycle | Scadenza, rotation/reuse, no scope escalation, revoca proprietario | O `test_token_lifecycle_rotation_reuse_and_permissions`, test HTTP SDK; C login/oauth/tools |
| Autenticazione GAIA | Login reale come funzione route; sessioni e permessi canonici, utente inattivo | O `test_gaia_sessions_reuse_login_and_canonical_permissions`; C `test_real_gaia_login_oauth_data_tools_audit_permissions_and_revocation` |
| Metadata e isolamento | Discovery RFC8414/RFC9728, challenge 401; Docs/inspection/register assenti | C login/oauth/tools; O `test_delegated_scopes_keep_discovery_calls_and_provenance_data_only` |
| Discovery e chiamate | Catalogo limitato per scope; chiamata tool nascosto negata, Docs mai eseguito | C login/oauth/tools; D `test_hidden_tools_remain_denied_and_docs_never_execute` |
| Audit/provenance | Origine sintetica conservata, chiamate negate registrate, token non persistiti | C login/oauth/tools; suite audit (filtri/persistenza) |
| Budget | Condiviso tra token/client dello stesso utente, isolamento utenti, 429/Retry-After, cleanup | C `test_principal_budget_shared_by_tokens_and_isolated_by_user`, `test_budget_window_persistence_and_rollback` |
| Errori trasporto | Body >64KiB, disconnect, JSON invalido/batch, failure SQLite503, contesto resettato | C `test_body_limits_invalid_inputs_backend_failures_and_context_reset` |
| Sicurezza HTTP / riavvio | Host421, Origin403, content-type400, origin approvato ammesso; token persistito valido dopo riavvio | C nuovo `test_transport_security_and_persisted_grants_survive_gateway_restart` |
| Integrita dataset | Dataset arbitrario con manifest coerente ma non generato respinto prima delle route | C `test_gateway_rejects_dataset_merely_labelled_synthetic` |
| UI disattivata/input | Nessuna lettura sessione/richiesta da pagina disattivata; query invalida senza auth | F `default page is disabled...`, parametrizzati `invalid request...` |
| UI login | API GAIA con device metadata, password reset, errori generici, password mai al consenso | F `inline login reuses...`, `failed login hides...` |
| UI sessione/decisione | Nessuna approvazione automatica, allow/deny espliciti, sessione scaduta/errori senza redirect | F `existing GAIA session...`, `explicit decision...`, `load failure...`, `failed decision...` |
| UI navigazione | Callback limitato a HTTPS/origin/path, no userinfo/hash; cambio query rimonta il flusso | F `unregistered or unsafe callback...`, `query change remounts...`, `inactive hook...` |
| Messaggi al modello | Catalogo/schema autorizzati; Docs e evidenze documentali spurie respinti prima del modello | D `test_model_receives_full_tool_descriptions_with_authorized_schema`; I `test_data_only_client_blocks_docs_sessions_and_all_tools`, `test_data_only_agent_rejects_docs_evidence_from_data_transport` |

I controlli ASGI eseguono veramente SDK, route OAuth e DataService in-process;
non sono una prova TCP/TLS/Claude. Il login backend e invocato direttamente,
non verificato via HTTP in questa suite. La UI usa mock delle API; i test
agente usano modelli simulati. Questi limiti non vengono nascosti dalla coverage.

## Coverage finale

Suite congiunta OAuth/connector: **26 test passati**, sette runtime coperti
integralmente, **487/487 statement e 130/130 branch, 100% per file**.
Report: `/tmp/gaia-final-validation/backend-coverage.json`.
Nessuna riga o branch mancante, zero righe escluse.

`make test-mcp-consent`: **23 test passati**; tre runtime frontend:
**67/67 statement, 34/34 branch, 14/14 funzioni e 63/63 linee, 100%**.
Verificati i tre path reali in `coverage-final.json`, non solo il riepilogo.
Report: `/tmp/gaia-mcp-consent-frontend-coverage/`.

Non e dichiarata coverage 100% dell'intero package MCP o del repository:
`make test-mcp` non completa e non produce evidenza finale valida.
Nessuna esclusione aggiunta ai gate repository; i filtri di regressione sotto
sono diagnostici espliciti, non sostituiscono il gate completo.

## Regression gate e comandi

Evidenze correnti sotto `/tmp/gaia-final-validation/`.

| Controllo eseguito | Risultato |
| --- | --- |
| `make test-mcp-connector test-mcp-oauth QUALITY_PYTHON=backend/.venv/bin/python` prima del test aggiuntivo | PASS: 25 + 18, coverage mirata 100% |
| Pytest OAuth/connector con tutti i sette `--cov`, branch/fail-under100 dopo il test aggiuntivo | PASS: 26, coverage sopra |
| Regressioni Docs/Data/HTTP/evaluation/experiment/discovery/OAuth/connector socket-free | PASS: 194, 6 deselected |
| Regressioni integrazione client/agente/provider simulate, senza gateway/TestClient e TCP | PASS: 22, 11 deselected |
| Audit filtri/persistenza senza TestClient | PASS: 8, 4 deselected |
| Wiki legacy indexer/RAG | PASS: 47 |
| `cd frontend && npm test` | PASS: 1 smoke |
| `cd frontend && npm run test:unit` | PASS: 270 file, 3820 test |
| `make test-mcp-consent` | PASS: 23, coverage100% |
| `npx tsc -p tsconfig.json --noEmit --incremental false` | PASS |
| ESLint mirato consenso/API/pagina/test | PASS, nessun warning |
| `npm run lint` | Exit0, warning legacy fuori consenso; non lint globalmente privo di warning |
| Ruff check e format mirati | PASS |
| `make lint-backend QUALITY_PYTHON=backend/.venv/bin/python` | Prima esecuzione PASS; riesecuzione finale FAIL su nuovi file concorrenti Presenze (I001/E731/F401/format), non sui runtime MCP |
| Ratchet autorevole mirato sui dieci runtime | PASS: findings vuoti, baseline invariata |
| `make complexity-ratchet QUALITY_PYTHON=backend/.venv/bin/python` | FAIL: 26 finding fuori dai dieci runtime |
| `docker compose -f docker-compose.yml -f docker-compose.mcp.yml config --quiet` | PASS, nessun container avviato |
| `git diff --check` | PASS |
| `backend/.venv/bin/python -m pip check` | PASS, warning cache pip non scrivibile |
| `make test-mcp` con timeout75s | NON COMPLETATO: blocco socket/SDK, exit124; non PASS |
| `npm run build:clean` | FAIL: `.next` contiene artefatti non eliminabili per permessi; compilazione non raggiunta |
| Playwright Wiki MCP preview mockata | FAIL all'avvio Chromium: `sandbox_host_linux.cc`, shutdown EPERM; browser non verificato |
| `nginx -t`, HTTPS remoto, Claude/provider live | NON VERIFICATI: Nginx assente, ingress/client non approvati, rete limitata |

I sei test deselected nella prima regressione sono i contratti Docs SDK/stdio,
Data stdio, comparison SDK HTTP reale e i due test HTTP basati su TestClient.
Una prima esecuzione con questi ultimi inclusi si blocca; riesecuzione filtrata
distinta in `backend-regression-final.log`. Una prova combinata integrazione/
console viene interrotta al TestClient; le due suite filtrate successive sono
le sole dichiarate passate. Test completi rimangono invariati, non indeboliti.

## Code quality e rischi

Scanner sui dieci runtime: **64 callable, 13 warning, zero error-level**.
Massimo: `ConnectorBearer.__call__`, cognitiva18/ciclomatica14/LOC62;
`useMCPConsent` cognitiva11/ciclomatica9/LOC59. Metriche e report in
`metrics.json`/`metrics.md`; nessun refactor o riduzione dichiarati.
Responsabilita distinte per store/provider/HTTP/auth/config/budget/UI.
Review manuale di import, lifecycle, contesto, rollback, logging e redirect:
nessuna nuova duplicazione/dead code o incoerenza bloccante nei dieci runtime.
Typecheck/frontend e Ruff danno evidenza statica, non prova formale di assenza
di dead code/duplicazioni o type safety backend completa.

Il ratchet globale rileva regressioni in GIS, Presenze, repository utenti,
bootstrap, Elaborazioni, frontend utenti/Organigramma e API core; nessuna nei
dieci runtime. Sono modifiche fuori tranche preservate, non failure dimostrate
sulla base pulita: non vengono classificate come preesistenti a HEAD senza
una riproduzione separata. Non aggiornata la baseline per assorbirle.
Il working tree e cambiato durante l'audit: nuovi file Presenze sono comparsi
dopo i test frontend/globali. Il PASS di 3820 test descrive lo snapshot di
quella esecuzione, non certifica automaticamente modifiche concorrenti future.
Il lint backend finale e rosso su questi nuovi file; non vengono corretti qui.

Debito/residui di rilascio: grants OAuth senza cap/cleanup periodico indipendente,
refresh rolling8h senza limite famiglia assoluto/revoca amministrativa,
input invalido rifiutato prima del budget utente (rate IP richiesto al bordo),
login/API/browser HTTPS e compatibilita Claude preregistrazione non provati,
proxy di esempio non incluso ne validato, env produzione minimo da preparare.
Questi residui sono documentati, non nuove feature avviate durante l'audit.

## Documentazione, Graphify e working tree

Aggiornati stato corrente/runbook, README MCP, piano produzione,
architettura MCP e PRD/implementation plan Wiki con rimando a questo audit.
Il presente report e il PROGRESS della tranche: implementazione completata,
gate finale e rilascio ancora pendenti. Il PROGRESS code-quality non viene
modificato: nessun cambio tooling/hotspot in questa verifica.

`make graphify-wiki-code graphify-frontend`: PASS AST-only, sorgenti riestratte,
nessun cambio topologico rilevato; grafi correnti conservati. Nessun simbolo
runtime rimosso, quindi nessun pruning forzato necessario. Query Wiki usata
per orientamento. Grafi non versionati. Graphify semantico docs NON eseguito:
il vincolo vieta inviare documenti reali al provider. Questo limite e esplicito.
Verificata presenza dei sette sorgenti backend e tre frontend nel JSON:
Wiki 1007 nodi/2383 relazioni, frontend 7373 nodi/17761 relazioni.

Snapshot working tree prima: 153 entry, 73 modificate e 80 non tracciate.
Snapshot successivo: 172 entry, inclusi documentazione audit e nuovi lavori
concorrenti Presenze. Snapshot completi `/tmp/gaia-final-status-before.txt`
e `/tmp/gaia-final-status-after.txt`; nessuno staging effettuato.
Modifiche concorrenti incluse in tale snapshot non sono ownership della tranche.
La verifica modifica solo il test connector e i documenti elencati; nessun
`git add`, cleanup di sorgenti, credenziale, config attiva o database operativo.
Build clean richiesta ha tentato la rimozione di cache `.next`, senza successo
completo per i permessi. Log/coverage/browser artefatti di questa verifica in
`/tmp`, non da committare. Nessuna promessa di worktree globale pulito.

Per chiudere: ripetere build e browser in ambiente autorizzato/scrivibile,
suite MCP senza vincoli IPC, risolvere il ratchet concorrente con ownership
separata, quindi validare ingress/Claude sintetico prima del rilascio.

**FINAL QUALITY GATE — FAIL**
