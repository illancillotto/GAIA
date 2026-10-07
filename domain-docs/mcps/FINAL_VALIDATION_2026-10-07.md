# Verifica finale MCP live — 2026-10-07

## 1. Scope e inventario

Verifica del ciclo MCP live sul checkout `703f8411`, senza nuove feature,
commit, deploy, attivazione OAuth, tunnel o invio di dati reali a modelli.
Perimetro runtime: i sette file di
`backend/app/modules/wiki/mcps/live/`. Perimetro test:
`backend/tests/test_wiki_mcp_live.py` e
`backend/tests/test_wiki_mcp_live_integration.py`. Inclusi i target Make
`mcp-live`, `test-mcp-live`, ampliamento della suite `test-mcp` e docs correlate.

Le modifiche gia presenti a Elaborazioni, Presenze export, Ruolo tributi,
mobile sync, worker, script autosync e report GIS/complessita non appartengono
a questo ciclo: conservate, non corrette o selezionate per un commit MCP.
PKI e release LAN sono lavori antecedenti, riverificati come regressione
infrastrutturale senza considerarli nuove feature live.

## 2. Implementazione e dipendenze

- 17 tool stdio di pura lettura su API HTTPS GAIA; nessuna route HTTP live
  aggiunta al monolite. Catalogo e path dettagliati in `LIVE_READS_2026-10-07.md`.
- `catalog.py`: schema Pydantic per input, UUID, limiti, sezioni/moduli e campi.
- `api.py`: client HTTPX TLS verificato, timeout, streaming limitato, nessun
  redirect/proxy implicito, errori sorgente sanitizzati.
- `service.py`: allowlist esplicita, identita e permessi freschi, budget,
  proiezione dei dati, provenance e audit senza record/token/query.
- `server.py`: protocollo MCP, discovery, invocazione, schema e annotazioni
  read-only. `cli.py`/`__main__.py`: opt-in e chiusura delle risorse.
- Riutilizzati `AuditStore` e `serve_stdio` esistenti, non duplicati. Dipendenze
  gia installate: `httpx==0.28.1`, `mcp==2.0.0`, Pydantic, AnyIO e stdlib.
  Nessuna modifica ai requirements/lockfile.
- Nessuna migration, modello SQLAlchemy, frontend, contratto REST, sync o
  transazione applicativa modificati. Nei test integrazione: vere route,
  JWT, resolver permessi e modelli GAIA su SQLite effimero; audit SQLite dedicato.

## 3. Matrice funzionalita → comportamento → test

Abbreviazioni: **U** = `backend/tests/test_wiki_mcp_live.py`,
**I** = `backend/tests/test_wiki_mcp_live_integration.py`.
Per ogni tool della tabella sono eseguiti tre test parametrizzati U:
`test_catalog_routes_are_read_only_authorized_and_projected`,
`test_source_specific_projection_retains_useful_data_without_sensitive_fields`,
`test_each_tool_requires_explicit_allowlist_and_current_module_permissions`.
Questi verificano rispettivamente GET/provenance/audit, dati pertinenti
alla fonte e filtro campi sensibili, negazione prima della lettura sorgente.
Non si spaccia il mock delle fonti per verifica end-to-end dei singoli domini.

| Funzionalita | Comportamento atteso | Test pertinenti aggiuntivi |
| --- | --- | --- |
| Ricerca GAIA | Richiede tutti i tre moduli/sezioni; input e risultati limitati | U: `test_invalid_boundary_inputs_never_reach_the_data_source`, `test_audit_metadata_persists_without_source_records_or_query` |
| Soggetto | UUID, dati nominativi consentiti, niente CF/documenti/NAS | U: `test_unknown_tool_invalid_arguments_and_unconfigured_sources_are_not_called` |
| Avviso Ruolo | UUID e importi consentiti, nessuna scrittura | U: contratti route GET esatti e proiezione source-specific |
| Particelle | Filtri bounded, paginazione, autorizzazione Ruolo della fonte | U: test limiti input e `test_paged_tools_forward_bounded_pagination_to_the_source` |
| Ricerca Dotazioni | Dati utili e paginati, niente note/seriali | I: `test_real_gaia_auth_asset_projection_and_permission_revocation`; U: paginazione |
| Dettaglio Dotazione | UUID, nome/stato, revoca effettiva | I: stesso test Dotazioni, JWT e resolver reali |
| Custodia corrente | Metadati autorizzati, `null` per bene non assegnato | U: `test_unassigned_asset_custody_returns_null_instead_of_a_source_error`; I: Dotazioni |
| Storico Dotazione | Eventi paginati, niente dettagli liberi | U: paginazione e input invalidi |
| Riepilogo personale | Solo utente autenticato, metriche allowlisted | U: schema/input extra e proiezione source-specific |
| Presenze personali | Identita canonica, niente altri utenti o causali mediche | I: `test_real_self_service_canonical_identity_isolation_and_no_medical_data`; U: paginazione e impersonazione rifiutata |
| Rapporti personali | Solo metadati, niente titolo/testo/attachment | U: proiezione source-specific e paginazione |
| Dashboard Operazioni | Aggregati consentiti, modulo/sezione obbligatori | U: proiezione source-specific e test permessi per ogni tool |
| Organigramma | Unita consentite dall'API, nomi/tipo/parent, niente scritture | U: route esatta, proiezione, modulo e allowlist |
| Dispositivi Rete | Dispositivi gia scoperti; nessuna scansione avviata | U: route GET, paginazione e proiezione |
| Scansioni Rete | Solo metadati di scansioni esistenti | U: route GET, sezioni, proiezione senza note |
| Salute portale | Finestra 1..72 ore, solo totali/stato dell'utente | U: limiti input e proiezione senza credenziali/eventi grezzi |
| Richiesta Elaborazioni | Stato della sola richiesta posseduta, niente captcha/errori grezzi | I: `test_processing_status_enforces_backend_ownership_and_never_writes`, incluso controllo SQL esclusivamente SELECT |

| Comportamento trasversale | Test U |
| --- | --- |
| Route backend reali e GET, integrazioni escluse non catalogate | `test_every_source_contract_matches_a_registered_backend_get_route` |
| Revoca dopo discovery e prima dell'invocazione | `test_discovery_and_invocation_recheck_revoked_module_and_sections`, `test_sdk_session_initialization_discovery_call_and_revocation` |
| Identita inattiva/malformata, moduli e permessi invalidi | `test_invalid_or_inactive_identity_is_fail_closed` |
| Tool sconosciuto, path traversal UUID, campi extra/impersonazione | `test_unknown_tool_invalid_arguments_and_unconfigured_sources_are_not_called` |
| Pagine, dimensioni, query, filtri e finestre fuori range | `test_invalid_boundary_inputs_never_reach_the_data_source` |
| Allowlist assente o tool non previsto | `test_allowlist_is_required`, test permessi per ogni tool |
| Budget discovery/chiamate e recupero al minuto successivo | `test_budget_enforces_tool_and_discovery_limits_and_recovers` |
| Audit persistente, metadata-only, file 0600, fallimento fail-closed | Test catalogo/audit persistente e `test_audit_failure_does_not_return_real_records` |
| Stringhe/liste/profondita eccedenti, campo non autorizzato | `test_projection_drops_unapproved_fields_and_marks_every_truncation` |
| Origine HTTP, userinfo/path/query/fragment, token vuoto/CRLF | `test_transport_rejects_insecure_origins_or_credentials` |
| 401/403/404/429/302/500; redirect non seguito | `test_transport_sanitizes_errors_and_never_follows_redirects` |
| JSON malformato/scalare, risposta oltre 64 KiB | `test_transport_bounds_and_validates_source_response` |
| 64 KiB esatti, overflow distribuito in chunk, response chiusa | `test_streaming_limit_counts_accumulated_chunks_and_closes_response` |
| Connect/read timeout, errore rete, path invalido, niente proxy env | `test_timeouts_are_sanitized_and_transport_has_no_implicit_proxy`, `test_transport_network_failure_and_invalid_path` |
| JSON 60 KiB con nesting patologico | `test_deeply_nested_source_json_fails_with_a_sanitized_error` |
| Schema e permission errors protocollo MCP | `test_mcp_protocol_handlers_preserve_schema_and_permission_errors` |
| Sessione SDK reale initialize/list/call e revoca | `test_sdk_session_initialization_discovery_call_and_revocation` |
| Avvio disabilitato e cleanup configurazione/stdio falliti | `test_cli_is_disabled_by_default_and_closes_resources`, `test_stdio_failure_closes_http_and_audit_resources` |
| Entrypoint selezionato e ambiente esplicito | `test_module_entrypoint_uses_the_explicit_environment` |

## 4. Consolidamento dei test e failure path

Aggiunti test pertinenti per limiti input, timeout, limite streaming cumulativo,
chiusura response, persistenza audit, negazione per tutti i 17 tool e cleanup
alla disconnessione stdio. Nessun test escluso o policy coverage indebolita.

Unico fix runtime della verifica: normalizzare anche `RecursionError` del
decoder JSON in `SOURCE_UNAVAILABLE`. Un payload patologico sotto 64 KiB
prima poteva sfuggire alla sanitizzazione. Il test usa un payload reale,
non un'eccezione artificiale del mock decoder. Nessuna nuova capability.
Le prime esecuzioni hanno rilevato una profondita di fixture insufficiente
su Python 3.12; corretta prima dell'esecuzione finale, non nascosta come flaky.

## 5. Code quality, sicurezza e architettura

- Backend nel package Wiki del monolite modulare; nessun servizio parallelo
  distribuito, frontend nuovo o schema DB alternativo dei dati di dominio.
- Il processo stdio e un adapter opt-in sulle API esistenti, non una seconda
  implementazione delle query/permessi di dominio. Persistenza audit riusata.
- Ruff controlla import inutilizzati/dead imports e naming; AST scan dei
  corpi callable non trova duplicati esatti nel package live.
- Responsabilita distinte: catalogo, trasporto, autorizzazione/proiezione,
  protocollo, lifecycle. Coupling alle API/fonti e esplicito e testato;
  non introdotto SDK o ORM nuovo. Pydantic valida i confini degli input.
- Nessun type checker Python dedicato configurato per questo package:
  non viene dichiarata una verifica mypy/pyright mai eseguita; i callable
  interni restano in parte senza annotazioni, debito di manutenibilita.
- Errori HTTP/JSON non restituiscono body privati. Query/token/record non
  entrano nell'audit. File audit dedicato 0600 e retention esistente di 1000.
- I dati allowlisted non sono anonimizzati: nomi, titoli ricerca, IP e
  metadati possono essere personali/interni. Client locale non autorizza
  automaticamente l'invio al servizio modello. Nessun dato reale usato nei test.
- Authorization check e lettura dati sono richieste separate: non sono
  una transazione atomica di autorizzazione. Restano i controlli della fonte;
  non si promette revoca atomica durante una richiesta gia in corso.

### Complessita prima/dopo

Sette file, 14 callable, sette warning e zero error-level; invariati dopo
il fix del decoder. `GaiaAPI.get` cognitive/cyclomatic/LOC `17/11/25`,
`project` `15/11/16`, `identity` `12/11/18`, `admit` `13/10/7`,
`call` `13/9/44`. Nessun refactoring introdotto per abbassare metriche.
Ratchet mirato contro baseline del merge-base `703f8411`, non baseline
modificata nella change. Baseline/soglie/esclusioni restano invariate.
Evidenze: `/tmp/gaia-final-live-metrics.json` e
`/tmp/gaia-final-live-ratchet.json`.

## 6. Gate, coverage e regressioni

Le esecuzioni autorevoli di chiusura usano coverage file distinti per evitare
collisioni. Risultati e percentuali finali vengono registrati dopo il loro
completamento, non dedotti dai risultati del ciclo precedente.

| Controllo eseguito | Stato verificato |
| --- | --- |
| `make test-mcp-live` | PASS: 117 test, 187/187 statement e 40/40 branch, coverage 100% |
| `make test-mcp` completo | PASS: 437 test, 2319/2319 statement e 478/478 branch su 52 file, coverage 100% |
| Compileall live/test con cache isolata | PASS |
| Backend lint globale `make lint-backend BASE_REF=HEAD` | FAIL: 19 errori in `mobile_sync.py` fuori scope; stessi 19 riprodotti sul file di HEAD |
| Ruff e format-check sui nove file live/test | PASS |
| Ratchet complessita live contro merge-base | PASS: zero finding bloccanti |
| Ratchet globale contro lo stesso merge-base | FAIL: quattro finding fuori dal perimetro MCP |
| Frontend `npm test` | PASS: 18 smoke test |
| Frontend unit MCP preview/console/consent | PASS: 30 test, tre file |
| Frontend `npm run typecheck` | PASS |
| Frontend `npm run lint` | Exit 0, con 35 warning legacy fuori dal codice introdotto |
| Frontend `npm run build:clean` | PASS: build isolata in `/tmp/gaia-final-frontend-build.*`, exit 0; warning legacy presenti |
| Playwright preview sintetica e failure sorgente | PASS: un test Chromium contro build isolata, API mockate |
| Gateway TLS/HTTP con Docker reale | PASS: 67 test |
| Release Compose isolata | PASS: quattro test |
| PKI/OpenSSL infrastruttura | PASS: quattro test |
| Diff whitespace | PASS |

Build isolata: sorgenti frontend copiati con rsync, dipendenze esistenti
collegate senza nuova installazione; `.next` del checkout non cancellata,
nessun container GAIA reale riavviato. Il server Next temporaneo e fermato
al termine. Log `/tmp/gaia-final-frontend-{build,smoke,unit,type,lint}.log`,
`/tmp/gaia-final-e2e.log`, `/tmp/gaia-final-{gateway,release,pki}.log`.
Log backend autorevoli: `/tmp/gaia-closure-live.log` e
`/tmp/gaia-closure-mcp.log`; report `backend/coverage-mcp.json` e
`/tmp/gaia-mcp-live-coverage.json`. In entrambi: zero righe e branch
mancanti, zero righe escluse. Nessun file/linea runtime live non coperto.
Le prime esecuzioni con fixture JSON insufficiente non sono considerate
PASS: l'ultimo rerun di entrambi i target avviene dopo la correzione.
Nessuna regressione MCP rilevata dai 437 test finali.
Il server temporaneo `next start` segnala il warning preesistente sulla
configurazione `output: standalone`; E2E riuscito, server terminato.
Non e una prova del comando di avvio standalone di produzione.

Non eseguiti: collaudi Claude Desktop/Code, Codex/ChatGPT nelle app,
E2E con provider esterno/dati reali, HTTPS reale CED e database PostgreSQL
per il catalogo live. L'E2E browser mockato e i test ASGI non li sostituiscono.
Nessun frontend live e introdotto: non esiste una nuova UI da collaudare.
Nessuna migration o query ORM runtime introdotta: la compatibilita driver
e demandata alle API GAIA esistenti, non certificata dai test SQLite.
Non viene dichiarata eseguita l'intera suite di tutti i domini del repository.

## 7. Documentazione, Graphify e working tree

Documentazione del ciclo: README root, PRD, implementation plan, architettura,
struttura docs, piano coverage; indici/architettura/sicurezza/runtime/piano
connector e guide Data MCP. Guida operativa `LIVE_READS_2026-10-07.md`;
stato di avanzamento `PROGRESS.md`. Report datati antecedenti restano storici.
Questo report e la fonte per la chiusura di verifica, non prova di deploy.

Graphify aggiornato esclusivamente con target Make dei corpus:
`graphify-wiki-code`, `graphify-docs`, `graphify-platform-docs`.
Il codice non rimuove simboli/route, quindi non richiede pruning forzato;
AST re-estratto, nessuna nuova topologia rispetto alla feature gia indicizzata.
Per docs si verifica completion dei chunk e assenza di warning semantici,
non il solo exit code. `graphify-out/` non viene versionato.

Working tree non pulito e con modifiche concorrenti: snapshot
`/tmp/gaia-mcp-final-worktree-before.txt` e snapshot finale separato.
Non eseguiti stash/reset/clean/add/commit. Nessun segreto o configurazione
di produzione aggiunti. Coverage report, build/E2E/log e grafi sono artefatti
ignorati o sotto `/tmp`, non selezionati per versionamento.

## 8. Residui e criterio finale

Il lint backend globale fallisce anche su sorgente HEAD: e debito preesistente,
non regressione MCP, ma impedisce di dichiarare tutti i gate verdi. Le altre
modifiche concorrenti non vengono certificate da questa verifica.
Il ratchet globale rileva quattro regressioni nelle modifiche concorrenti:
LOC callable worker `test_observability_initializes_recorder_and_retention`
18→19, LOC file `mobile_sync.py` 1907→1910, `xlsm_export.py` 528→533 e
`tributi_repositories.py` 3694→3749. Non sono finding del package live e
non vengono assorbiti aggiornando la baseline. Evidenza snapshot:
`/tmp/gaia-final-global-ratchet.json`.
Restano sette warning di complessita live, callable interni non completamente
annotati e warning frontend legacy. NAS/Trasparenza e batch GET con side
effect restano intenzionalmente esclusi, non implementazioni concluse.
Budget per processo, proiezione per campo e token di sessione GAIA non
equivalgono a quote distribuite, DLP o OAuth live integrato.

Nessun commit/deploy: la chiusura richiesta e una verifica, non autorizza
rilascio dati reali o correzioni estese dei domini concorrenti.

FINAL QUALITY GATE — FAIL
