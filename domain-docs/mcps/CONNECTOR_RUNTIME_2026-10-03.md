# Consenso GAIA e gateway MCP Data-only

Verifica finale corrente: `CONNECTOR_FINAL_REVIEW_2026-10-03.md`.
26 test OAuth/connector, sette runtime backend al 100% statement/branch;
23 test consenso frontend al 100%. Il lint backend globale e passato alla
prima esecuzione, poi fallito su nuovi lavori concorrenti Presenze. Build,
browser, suite completa e ratchet globale non superati. Le evidenze precedenti
in fondo restano cronologia della tranche.

Stato: implementato e testato localmente; **disattivato per default, nessun
deploy o prova Claude live**. Non pubblicare il listener direttamente.
Questa tranche completa la pagina consenso, il wiring del listener separato,
metadata OAuth/protected-resource, budget per principal e audit dei tool.
Wiki legacy, login GAIA, server Docs e listener interno restano invariati.

## Flusso

1. Il connettore avvia authorization code + PKCE S256, scope Data approvati e
   singola resource esatta. Client_id/callback devono essere preregistrati.
2. `/mcp/consent` sul frontend GAIA mostra nome client, endpoint e permessi.
   Riusa la sessione GAIA o il login username/password esistente, inclusi
   identificativo dispositivo e relativo controllo. Nessun consenso automatico.
3. L'utente seleziona Autorizza/Rifiuta. Il backend usa i permessi attuali;
   torna al redirect registrato con code/error e state. Il frontend controlla
   anche protocollo, origin e path del callback; nessun bearer GAIA al client.
4. `/token` verifica code, client, redirect, PKCE e audience/resource. Ogni
   richiesta Data rivalida utente attivo e scope, creando `CallContext` con
   principal canonico `gaia:<user.id>`, mantenendo audit e provenance.
5. Revoca, disabilitazione utente o perdita scope rendono inutilizzabili i
   token interessati. Le famiglie refresh ruotano con rilevamento del riuso.

Il login HTTP di GAIA non viene spostato sul nuovo listener. La pagina chiama
`/api/auth/login`, come il login esistente; non implementa password grant OAuth.

## Superficie e isolamento

| Path pubblico previsto | Funzione |
| --- | --- |
| `/mcp/consent` | pagina frontend con consenso esplicito e login GAIA |
| `/api/wiki/mcp/connector/oauth/authorize` | authorize SDK MCP |
| `/api/wiki/mcp/connector/oauth/consent` | GET dettagli/POST decisione, bearer sessione GAIA |
| `/api/wiki/mcp/connector/oauth/token` | code/refresh + resource, niente password/implicit |
| `/api/wiki/mcp/connector/oauth/revoke` | revoca famiglia per il client proprietario |
| `/api/wiki/mcp/connector/data` | Streamable HTTP stateless OAuth, solo Data |
| `/.well-known/oauth-authorization-server/api/wiki/mcp/connector/oauth` | discovery RFC 8414 per issuer con path |
| `/.well-known/oauth-protected-resource/api/wiki/mcp/connector/data` | discovery RFC 9728, anche nella challenge 401 |

Il gateway non monta `/docs`, `/inspection`, listener JWT legacy o una
registration dinamica. `docs.read` e `mcp.audit.read` non sono delegabili.
La discovery filtra i tool per scope e l'invocazione verifica nuovamente i
permessi anche se il client conosce il nome di un tool nascosto.

Il database e readonly e dedicato: nome `gaia-mcp-synthetic-*.sqlite`, manifest
e integrita gia verificati dal DataService. In aggiunta il gateway confronta
il manifest con l'output del generatore per lo stesso seed: una raccolta
arbitraria soltanto etichettata "synthetic" viene rifiutata prima di aprire le
route. Il volume e montato readonly. Non sostituire i dati con fonti reali.
Il listener non usa OpenAI, codex-lb, Ollama o documenti per servire i tool:
e il connettore esterno a ricevere le sole risposte sintetiche autorizzate.

## Budget e log

- Finestra fissa di 60 secondi: default 60 richieste Data con body JSON valido e 20 `tools/call`
  per utente. Limiti configurabili, `1 <= tools <= requests <= 600`.
- Counter SHA256 persistiti nel DB OAuth, transazione SQLite; token/client
  dello stesso utente condividono il budget. Utenti diversi sono isolati.
- Superamento => 429 e `Retry-After: 60`; errore counter => 503 fail-closed.
  Nessun token o filtro sensibile viene scritto nell'evento budget-denied.
- Body Data <= 65536 byte; JSON-RPC batch rifiutati. Restano attivi limiti
  righe/cursor/query del DataService. Il budget qui e di richieste/chiamate,
  **non** di costi o token del modello esterno.
- Chiamate tool autorizzate/negate passano dall'AuditStore esistente:
  richieste con filtri sanitizzati, risultati sintetici, request_id,
  principal pseudonimo e provenance. DB audit condivisibile con la console
  Wiki MCP interna; non esposto al connettore. I rifiuti HTTP pre-tool sono
  nei log strutturati del listener, non nello storico tool della console.
  La factory configura il logger MCP INFO con EventFormatter JSON e senza
  propagazione duplicata; nessun access log Uvicorn con token/query OAuth.
- OAuth store e counter scaduti vengono ripuliti alle richieste Data ammesse;
  prima del rilascio serve anche cleanup periodico indipendente dal traffico.
  I refresh restano rolling 8 h, non una sessione con scadenza assoluta.

## Configurazione, senza attivare

Per aggiungere HTTPS allo stack conservando HTTP, usare l'override opzionale
e la procedura in `HTTP_HTTPS_GATEWAY.md`. Con l'override le route MCP su HTTP
reindirizzano all'origin HTTPS canonico; OAuth continua a richiedere HTTPS.

`config/mcps/environment.example` documenta le variabili. Il backend richiede
`GAIA_MCP_OAUTH_ENABLED=true`; qualsiasi altro valore tranne `false` fallisce.
`false` (default) restituisce 404 senza aprire database o sessioni GAIA.
Issuer/resource devono avere stesso origin HTTPS e i path in tabella. La
consent URL deve finire con `/mcp/consent`; puo usare l'origine interna GAIA
se il browser utente la raggiunge e si fida del nuovo certificato CED.
Non inventare hostname pubblico, credenziali o callback Claude.

`GAIA_MCP_OAUTH_CLIENTS_FILE` punta a un JSON locale approvato. Il template
`approved-clients.example.json` e volutamente vuoto e non avviabile:
compilarlo solo con client_id/callback verificati, `token_endpoint_auth_method`
`none`, `response_types` `["code"]`, `grant_types`
`["authorization_code", "refresh_token"]` e scope Data espliciti.
Client_secret, scope Docs/audit, duplicati e metadata invalidi sono rifiutati;
gli errori di parsing non stampano i valori del file. Non versionare la
configurazione reale. Nessun file approvato e stato creato implicitamente.

Il frontend richiede `NEXT_PUBLIC_GAIA_MCP_CONNECTOR_ENABLED=true` **in build**;
`frontend/Dockerfile` e l'overlay Compose lo passano con default `false`.
Se disattivato, la pagina non legge credenziali o chiama il gateway.
Cambiare soltanto un env runtime del container frontend non cambia il bundle.

## Listener e proxy da revisionare con il CED

- `make mcp-connector QUALITY_PYTHON=backend/.venv/bin/python` avvia solo
  il listener su loopback 8769, quando richiesto dall'operatore; nessun avvio
  eseguito in questa tranche. Le variabili devono essere gia nell'ambiente.
- `docker-compose.mcp.yml`: servizio separato `gaia-mcp-connector`, profilo
  `mcp-connector`, porta solamente `expose`, nessuna porta host pubblicata.
  Usa le configurazioni auth/DB GAIA esistenti da `.env`; preparare un env
  dedicato minimo per produzione, senza credenziali provider non necessarie.
- Volumi: dataset/config readonly, OAuth e audit writable separati. Non
  monta repository Docs, corpus reale, runtime-data generico o Docker socket.
- `nginx/mcp-connector-http.example.conf`: zona rate limit in contesto http.
  `nginx/mcp-connector-server.example.conf`: sole route allowlisted,
  body 64k, rate limit IP, buffering off, token/query non in access log.
  Consenso ha no-referrer/no-store e protezione framing; completare CSP
  compatibile con il frontend durante il rilascio.
  Lo snippet server usa `$maintenance_mode`, definito dal routing condiviso
  `nginx/server-routes.conf`: su un altro virtual host definire la stessa
  variabile e la gestione maintenance prima di includerlo.
- Esempi **non inclusi** in `nginx.conf`: integrarli soltanto nel virtual
  host HTTPS approvato, preservando host/origin e path senza rewrite `/api`.
  Sul bordo Internet esporre solo route MCP/metadata, non tutte le API GAIA.
  Il browser GAIA deve raggiungere anche il backend login sul proxy interno.
- `https://gaia.lan` e la CA interna non rendono raggiungibile il servizio
  Anthropic: ingresso pubblico e trust del servizio remoto restano gate.

## Verifiche

- `make test-mcp-connector`: login GAIA reale con utenti sintetici, consenso,
  PKCE, metadata, discovery, tool call, audit/provenance, permessi, revoca,
  utente inattivo, budget condiviso/isolamento, fail-closed startup e dataset
  falso. Login invocato come funzione route reale, non via HTTP; OAuth/Data
  provati con ASGI in-process senza socket TCP o bypass sandbox.
- `make test-mcp-consent`: UI, login con metadata dispositivo, password reset
  dopo submit, nessun consenso automatico, authorize/deny, errori sanitizzati,
  remount su cambio request_id e redirect limitato al callback registrato.
- Runtime nuovi/modificati backend e tre frontend al 100% statement/branch;
  frontend anche funzioni/linee. Provider remoto e Claude **non provati live**.
- Gate completi MCP con socket e lint/ratchet globali restano distinti dai
  gate mirati. Non dichiarare produzione pronta con i soli test ASGI.

Evidenze locali: 25 test backend OAuth/connettore verdi, statement 334/334 e
branch 96/96 sui quattro runtime nuovi/modificati; 23 test UI al 100%
su tre file (statement 67/67, branch 34/34, funzioni 14/14, linee 63/63).
Regressione socket-free 189 verdi, quattro test SDK/stdio/live-HTTP esclusi
esplicitamente senza modificarli; frontend Wiki MCP + consenso 30 verdi.
Ruff/format backend mirati, ESLint e typecheck frontend verdi; ratchet mirato
autorevole contro merge-base `origin/main` passato, nessuna baseline cambiata.
Compose `config --quiet` passato, nessun container avviato. Gli esempi Nginx
non hanno ancora un `nginx -t`: binario locale non disponibile.
Il lint globale resta fermo a I001 in `test_presenze_operations_postgres.py`,
fuori tranche; ratchet globale fallisce su modifiche concorrenti esterne al
perimetro connettore. Non dichiarati PASS globali, nessuna correzione estranea.
Graphify Wiki/frontend aggiornati via Make, AST-only; nessun documento reale
inviato a un LLM per Graphify. Log e coverage mirati `/tmp/gaia-consent-*`,
`/tmp/gaia-connector-*`, `/tmp/gaia-mcp-consent-frontend-*`.

Prima dell'attivazione: hostname/tunnel e callback reali approvati, nuova CA
interna CED/trust remoto, proxy HTTPS con negative test pubblici, cleanup/cap
grants OAuth e scadenza assoluta/revoca amministrativa, test interfaccia e
connettore Claude live solo sul dataset sintetico, rollback delle feature flag.
