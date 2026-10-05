# MCP — chiusura del ciclo di verifica

Data: 2026-10-03. Checkout: `main@e33d5c69`.
Esito complessivo: **FINAL QUALITY GATE — FAIL**.
Le evidenze nuove sono in `/tmp/gaia-mcp-close/`; quelle live/proxy della
tranche immediatamente precedente in `/tmp/gaia-mcp-recheck/`.

## 1. Scope verificato

Delta del ciclo rispetto a HEAD: un test TCP reale in
`backend/tests/test_wiki_mcp_connector.py`, documentazione MCP e guida alla
chiusura. Nessun nuovo codice runtime, API, schema, servizio o dipendenza.
Consolidata l'implementazione gia committata: OAuth/consenso/connettore,
console/audit, catalogo/scope, replica sintetica e agente Data-only.
Modifiche concorrenti Presenze, Dotazioni, Poste, GIS e frontend preservate.

## 2. Funzionalita e comportamento

Nessuna nuova funzionalita in questa fase. Il test aggiunto dimostra su TCP,
non solo ASGI, authorization-code PKCE/consenso, discovery per scope,
chiamata readonly con provenance, esclusione Docs, revoca e shutdown.
Riusa fixture sintetiche, login GAIA reale chiamato come funzione, helper
`delegate`/`rpc`, factory del dominio Wiki e SDK reali. Non introduce login
o autenticazione paralleli. Provider esterno simulato nelle suite; live
gpt-reserve verificato separatamente nella tranche precedente.

## 3. Matrice funzionalita → comportamento → test

Tutti i test sotto appartengono alla suite MCP completa eseguita. I nomi
senza prefisso sono in `backend/tests/test_wiki_mcp_connector.py`.
O = `test_wiki_mcp_oauth.py`, D = `test_wiki_mcp_discovery.py`,
I = `test_wiki_mcp_integration.py`, F = `frontend/tests/unit/mcp-consent.test.tsx`.
La matrice completa delle funzionalita consolidate e anche in
`CONNECTOR_FINAL_REVIEW_2026-10-03.md`; quella sotto caratterizza la tranche
e i suoi invarianti, non inventa comportamenti per aumentare coverage.

| Funzionalita | Atteso / failure path | Test |
| --- | --- | --- |
| Avvio/config | Default disattivato, env/client invalidi fail-closed, route non aperte | `test_configuration_fail_closed_and_preapproved_clients`, `test_disabled_and_failed_startup_do_not_expose_routes` |
| OAuth reale TCP | PKCE, code/resource/callback e consenso tramite API SDK | nuovo `test_real_tcp_oauth_connector_tool_call_and_revocation`; O `test_http_sdk_pkce_resource_consent_and_revocation` |
| Discovery | Utenze-only espone soltanto due tool, nessun tool Docs | nuovo test TCP; D `test_discovery_filters_at_server_for_every_scope` |
| Invocazione | Risultato sintetico con provenance; nome Docs inventato negato | nuovo test TCP; `test_real_gaia_login_oauth_data_tools_audit_permissions_and_revocation` |
| Revoca/permessi | Refresh revocato invalida access token, utente inattivo/scope rimossi negati | nuovo test TCP; test login/oauth; O `test_token_lifecycle_rotation_reuse_and_permissions` |
| Persistenza | Grants e budget persistono; contesto non trapela dopo richiesta/riavvio | `test_transport_security_and_persisted_grants_survive_gateway_restart`, `test_budget_window_persistence_and_rollback` |
| Budget | Shared per utente tra client/token, isolamento utenti,429/Retry-After | `test_principal_budget_shared_by_tokens_and_isolated_by_user` |
| Input/failure | Body invalido/disconnect/batch/oversize400, budgetDB503; context reset su eccezione | `test_body_limits_invalid_inputs_backend_failures_and_context_reset` |
| HTTP sicurezza | Host421, Origin403, content-type400; metadata CORS | `test_transport_security_and_persisted_grants_survive_gateway_restart` |
| Dataset | Falso sintetico con manifest coerente respinto prima di esporre tool | `test_gateway_rejects_dataset_merely_labelled_synthetic` |
| Lifecycle | Listener non rimane attivo e route svuotate dopo shutdown | nuovo test TCP, finally e assert finale |
| Messaggi modello | Catalogo autorizzato, evidenze Docs spurie respinte prima del modello | D `test_model_receives_full_tool_descriptions_with_authorized_schema`; I `test_data_only_agent_rejects_docs_evidence_from_data_transport` |
| UI consenso | Flag false, input invalido, login device-aware, allow/deny espliciti, errore generico, callback limitato | suite F:23 test, inclusi `explicit decision...`, `failed decision...`, `unregistered or unsafe callback...` |

## 4. Test aggiunti/modificati

Un solo test aggiunto nel ciclo: TCP OAuth/tool/revoca. Import socket,
threading e Uvicorn necessari al trasporto reale. Bind loopback su porta
effimera; fixture GAIA e dataset temporanei; access log disattivato.
`finally` richiede shutdown/join/close anche su failure delle assert.
Nessun test rimosso, skip o filtro aggiunto alla suite MCP completa.

## 5. Risultati test

- `make test-mcp QUALITY_PYTHON=backend/.venv/bin/python`: **246 passed**,
  nessuna deselection, suite unitarie/SDK/HTTP/stdio/integrazione incluse.
- `make test-mcp-consent`: **23 passed** con coverage.
- `npm test`: smoke PASS.
- Frontend globale: prima esecuzione 3827 passati/1 timeout a5s in
  `ruolo-pages.test.tsx`, fuori MCP. Rerun mirato:22/22 passati senza cambiare
  timeout o test. Riesecuzione globale con parallelismo limitato registrata
  separatamente in `frontend-unit-final.log`: **271 file, 3828 test PASS**
  con `--maxWorkers=2`; non nascondere la prima failure.
- Wiki legacy: prima esecuzione interrotta da timeout150s; riesecuzione
  separata in `wiki-final.log`: **182 PASS, 260 warning fixture JWT**,
  senza filtri o cambi alle fixture.

## 6. Coverage

42 runtime MCP/router: **1984/1984 statement, 424/424 branch, 100%**.
Report corrente `backend/coverage-mcp.json`: zero righe/branch mancanti,
zero righe escluse e zero branch parziali. Nessuna esclusione nuova.
I test non sono codice runtime e non sono artificiosamente inclusi nel gate.

Tre runtime consenso frontend: **67/67 statement, 34/34 branch,
14/14 funzioni, 63/63 linee, 100%**. Percorsi reali del report verificati;
non e un riepilogo ottenuto coprendo soltanto mock. Non si dichiara coverage
100% del repository intero. Nessuna modifica ai gate CI o alla policy coverage.

## 7–8. Code quality e complessita

Ruff check/format test TCP PASS; lint backend globale PASS prima del ratchet.
Typecheck frontend PASS; ESLint mirato MCP PASS. Build evidenzia warning legacy
fuori dai componenti MCP: non rimossi tramite ignore o refactoring estranei.

Ratchet autorevole MCP/backend/router/UI PASS, merge-base `origin/main`;
baseline invariata. Ratchet globale FAIL con26 finding fuori MCP: GIS,
Presenze, utenti/bootstrap, Elaborazioni, frontend utenti/Organigramma/API core.
Non sono assorbiti nella baseline ne classificati come failure della base
pulita, che non e stata rieseguita separatamente.

Dieci runtime OAuth/consenso:64 callable,13 warning,zero error-level;
`ConnectorBearer.__call__` cognitiva18/ciclomatica14/LOC62;
`useMCPConsent` cognitiva11/ciclomatica9/LOC59. Metriche invariate, nessun
refactor o miglioramento di complessita dichiarato. Review di import,
duplicazioni, responsabilita, naming, lifecycle, logging e errori: test
riusa componenti esistenti, nessun dead code/servizio duplicato introdotto.
La review non equivale a una prova formale di assenza di duplicazioni/dead code.

## 9. Regressioni e limiti

MCP completo non mostra regressioni. Il timeout frontend e la prima
interruzione Wiki restano evidenze separate; il test Ruolo passa in isolamento.
Non e dimostrata formalmente la causa del timeout (carico concorrente durante
build/test e un'ipotesi, non una correzione applicativa). Nessun timeout del
test aumentato. Warning JWT nelle suite Wiki legacy riguardano fixture con
chiave HMAC corta, non password/token reali o il nuovo listener.

## 10. Build/lint/type-check/E2E

La build locale iniziale fallisce sui permessi della cache. Con nessun
container GAIA attivo e nessun listener3000/8080, la vecchia `.next` viene
**preservata tramite rename sullo stesso filesystem** in
`/tmp/gaia-mcp-close/previous-next-cache`, senza sudo/chown o cancellazioni.
La successiva `cd frontend && npm run build:clean` e **PASS nel checkout**.
Anche la build della copia isolata e PASS; il limite in-place precedente e
risolto per questa esecuzione, senza modifica di Dockerfile/config/app.

E2E preview:PASS Chromium contro la build locale eseguita con il vero
`node .next/standalone/server.js`, static/public predisposti come nel packaging.
API mockate sintetiche: prova rendering/errore sorgente, non loginOAuth/Claude.
Server loopback temporaneo, arrestato dopo la verifica; nessun deploy.
Compose configquiet e whitespace PASS. Nessuna build immagine Docker dichiarata.

## 11. Documentazione aggiornata

Questo report consolida scope, matrice, progress e residui. Aggiornati README,
runbook, PRD/implementation plan Wiki e piano produzione con rimando corrente.
I report precedenti restano storici; non vengono trasformati retroattivamente
in PASS. PROGRESS code-quality non modificato: nessun hotspot/tooling nuovo.

## 12. Architettura e Graphify

Backend riusato da `backend/app/modules/wiki/mcps`, UI da `features/wiki`.
Callback `/mcp/consent` gia prevista, non nuova architettura parallela.
Nessuna migration/schema PostgreSQL operativa; OAuth/audit/Data SQLite
dedicati sono esistenti, test usano solo temporanei sintetici. SDK/Uvicorn
gia dipendenze del progetto. Auth/scopes/budget/provenance e Docs separato
preservati; Wiki legacy verificata, non riprogettata.

`make graphify-wiki-code graphify-frontend` PASS AST-only, nessun cambio
topologico runtime; nessun simbolo runtime rimosso, pruning non necessario.
Nodi OAuth/consenso gia verificati nella tranche precedente. Nessun grafo
versionato. Graphify semantico docs non eseguito per il vincolo di privacy:
nessun documento reale inviato a provider esterni.

## 13. Working tree

Snapshot `/tmp/gaia-mcp-close-status-{before,current}.txt`:113 entry iniziali,
118 finali, comprendenti documentazione MCP e lavori concorrenti. Preservati lavori
concorrenti e documenti Presenze comparsi durante la verifica. Delta MCP:
test TCP e report/link documentali. Log, coverage, cache precedente e fixture
restano artefatti non da committare. Nessuna credenziale/config attiva cambiata,
nessun database operativo toccato, nessun git add/commit/push/deploy.

## 14–15. Residui e debito

Prove gia realmente eseguite nella tranche precedente, non ripetute qui:
gpt-reserve live con una toolcall/due provenance/zero Docs e soli sintetici;
Nginx di test con TLSlocalhost fidato, allowlist404/path invariato/body413/
rate429, backend stub. Non equivalgono a Claude o ingresso di produzione.

Restano bloccanti:26 regressioni globali con ownership esterna; hostname/
tunnel pubblico e callbackClaude non approvati; browserOAuth/console/backend
reale e HTTPS produzione non provati. Debito di rilascio:cap grants e cleanup
periodico, scadenza assoluta famiglia/revoca amministrativa; warning legacy
lint/JWT e sensibilita al timeout frontend. Non implementati durante l'audit.
Flags connettore restano false; nessuna CA creata o attivazione eseguita.

**FINAL QUALITY GATE — FAIL**
