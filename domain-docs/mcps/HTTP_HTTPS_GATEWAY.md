# Gateway HTTP e HTTPS per MCP

Lo stack base serve GAIA via HTTP sulla porta `NGINX_PORT` (default `8080`).
L'override `docker-compose.mcp-tls.yml` aggiunge HTTPS sulla porta
`GAIA_HTTPS_PORT` (default `8443`), usando lo stesso routing applicativo.
Le richieste HTTP alle route MCP, ai metadata OAuth e alla pagina consenso
ricevono un redirect `308` verso l'origin HTTPS configurato, preservando path,
query e metodo. Le altre pagine e API GAIA restano disponibili anche in HTTP.
OAuth mantiene issuer, resource e callback HTTPS.

## Configurazione

Fornire una certificate chain PEM e la relativa chiave privata PEM per
l'hostname scelto. Il client deve fidarsi della CA; per la CA CED seguire
`CLIENT_CA_INSTALLERS.md`. Non versionare chiavi o certificati locali.

Impostare nel proprio file env:

```dotenv
GAIA_HTTPS_PORT=8443
GAIA_TLS_CERTIFICATE=/percorso/assoluto/fullchain.pem
GAIA_TLS_PRIVATE_KEY=/percorso/assoluto/privkey.pem
GAIA_MCP_HTTPS_ORIGIN=https://gaia.lan:8443
```

Sostituire hostname e percorsi con quelli effettivi. Per la porta standard
usare `GAIA_HTTPS_PORT=443` e `GAIA_MCP_HTTPS_ORIGIN=https://gaia.lan`.
L'origin deve essere un URL HTTPS senza path, query o slash finale, identico
all'origin di issuer/resource. Il redirect usa questo valore esplicito e non
il `Host` ricevuto dal client. L'override rifiuta variabili richieste vuote.

Preparare dataset sintetico, client OAuth approvati, URL e feature flag secondo
`CONNECTOR_RUNTIME_2026-10-03.md`. La consent URL puo usare lo stesso origin,
con path `/mcp/consent`. Aggiungere l'origin HTTPS a `BACKEND_CORS_ORIGINS` se
necessario per il browser e ricostruire il frontend con la feature flag
consenso abilitata.

Validare prima dell'avvio:

```bash
docker compose -f docker-compose.yml -f docker-compose.mcp.yml \
  -f docker-compose.mcp-tls.yml --profile mcp-connector config --quiet
```

Avvio esplicito dopo aver completato la configurazione:

```bash
docker compose -f docker-compose.yml -f docker-compose.mcp.yml \
  -f docker-compose.mcp-tls.yml --profile mcp-connector up -d --build
```

Endpoint per il client: `https://gaia.lan:8443/api/wiki/mcp/connector/data`.
Anche `http://gaia.lan:8080/api/wiki/mcp/connector/data` conduce allo stesso
endpoint HTTPS. Configurare preferibilmente l'URL HTTPS nel client: alcuni
client MCP non seguono redirect e HTTP non protegge la prima richiesta.
HTTPS locale richiede comunque hostname raggiungibile e trust della CA per
il client utilizzato.

## Routing e verifiche

- `nginx/server-routes.conf` condivide il routing GAIA tra HTTP e HTTPS;
  `X-Forwarded-Proto` conserva lo schema effettivo per backend e frontend.
- Il server TLS include le route OAuth/Data allowlisted, prima del routing
  `/api/` generale: il connector riceve il path completo, senza rewrite.
- Il listener `8769` rimane interno a Docker. Rate limit, body 64 KiB,
  assenza di access log OAuth, buffering disabilitato e maintenance restano
  applicati. TLS ammette solo le versioni `1.2` e `1.3`.
- Verificare `nginx -t`, GAIA in HTTP/HTTPS, discovery OAuth, `401` del Data
  endpoint senza token e redirect `308` delle route MCP su HTTP.
- Questo virtual host include l'intera applicazione GAIA, per uso sulla rete
  GAIA. Un ingresso Internet dedicato MCP deve esporre solo le route approvate
  descritte nel runbook connector.

Senza l'override lo stack non richiede certificati e non apre HTTPS. Per il
rollback rimuovere l'override, ricreare nginx con lo stack base e disattivare
i flag OAuth/consenso. Il template redirect viene generato nel container,
senza modificare la configurazione versionata.

## Validazione locale

Risultati finali, complessita, coverage e residui globali:
`GATEWAY_FINAL_VALIDATION_2026-10-05.md`. I gate gateway/OAuth sono verdi;
il report distingue le failure Docs congelati gia presenti su HEAD.

Suite ripetibile, senza attivare lo stack applicativo:

```bash
make test-mcp-gateway QUALITY_PYTHON=backend/.venv/bin/python
make test-mcp-connector QUALITY_PYTHON=backend/.venv/bin/python
```

Il primo target richiede Docker/Compose, OpenSSL, pytest e immagini locali
`nginx:1.29-alpine` e `gaia-backend:latest`. Le immagini si possono selezionare
con `MCP_GATEWAY_NGINX_IMAGE` e `MCP_GATEWAY_UPSTREAM_IMAGE`; quest'ultima deve
contenere Python. Non scarica immagini preventivamente e non salta test se
mancano prerequisiti. Genera una CA/certificato temporaneo, container/network
isolati, porte loopback casuali e rimuove le risorse Docker create dai test.
Non modifica gli store di trust o i servizi GAIA avviati.

Matrice comportamento/test in `tests/infrastructure/test_mcp_tls_gateway.py`:

| Comportamento | Test pertinente |
| --- | --- |
| HTTP applicativo conservato con/senza override | `test_existing_http_routing_remains_available` |
| Redirect MCP/metadata/consenso, GET/POST/DELETE e query | `test_mcp_http_redirect_preserves_request_target` |
| Origin del redirect indipendente dal Host ricevuto | `test_http_redirect_uses_configured_origin` |
| Path connector completo e schema HTTPS corretto | `test_https_routes_reach_the_correct_upstream` |
| Login backend: path, metodo, body e schema | `test_https_login_preserves_credentials_and_scheme` |
| Bearer e JSON-RPC inoltrati al connector | `test_mcp_proxy_preserves_authorization_and_json_rpc` |
| Body al limite 64 KiB e oltre limite | `test_mcp_proxy_accepts_body_at_the_limit`, `test_mcp_proxy_rejects_oversized_body` |
| CSP consenso e assenza identificativi dai log | `test_consent_has_browser_security_headers`, `test_mcp_query_identifiers_are_absent_from_access_logs` |
| Maintenance HTTP/HTTPS e Retry-After | `test_maintenance_applies_to_both_protocols` |
| CA verificata, TLS 1.2/1.3 ammessi, TLS 1.1 rifiutato | `test_https_requires_a_trusted_certificate`, `test_https_supports_current_tls_versions`, `test_https_rejects_obsolete_tls` |
| Rate limit IP con risposta 429 | `test_mcp_rate_limit_returns_429` |
| Compose conserva HTTP e listener connector privato | `test_compose_adds_tls_without_replacing_http` |
| Variabili TLS richieste, stack base senza certificati | `test_tls_compose_requires_explicit_settings`, `test_base_compose_does_not_require_tls_settings` |
| Entry point Compose reale e template Nginx validi | `test_compose_entrypoint_renders_a_valid_nginx_configuration` |

Gli upstream nel test gateway sono server HTTP di echo: verificano davvero
socket, TLS e proxy, ma non implementano OAuth. Il secondo target esercita
il connector reale con identita e dataset sintetici, consenso/PKCE,
discovery/tool call, revoca e budget; misura statement/branch al 100% sui
quattro runtime inclusi dal target. Nginx/Compose non sono sorgenti Python:
la relativa copertura e dimostrata dalla matrice funzionale, non da una
percentuale di pytest-cov sui test stessi. Nessuna nuova esclusione coverage.
Resta da provare l'accesso da un client MCP esterno con DNS/certificati reali;
non e stato eseguito alcun deploy o rilascio pubblico.
