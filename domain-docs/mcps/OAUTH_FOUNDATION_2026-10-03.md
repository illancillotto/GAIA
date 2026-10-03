# Fondazione OAuth MCP — login GAIA

Tranche successiva: [consenso e gateway isolato](CONNECTOR_RUNTIME_2026-10-03.md)
ora implementati e verificati, sempre disattivati e non pubblicati.
Le note sotto descrivono lo stato precedente della sola fondazione.

Stato: componente backend verificato, **non montato nel router GAIA, non
pubblicato e non utilizzabile ancora come connettore Claude**. Nessun deploy.
Il login resta quello GAIA con username/password: le credenziali non devono
essere richieste dal connettore, inviate al modello o scambiate con un grant
OAuth `password`. La delega usa invece il token di sessione GAIA e un consenso
esplicito. Wiki legacy e server Docs non cambiano.

## Componenti e contratto

- `oauth_gaia.py`: callback di autenticazione sulla sessione GAIA esistente
  e verifica dei permessi canonici attuali. Nessun login alternativo.
- `oauth_provider.py`: client pubblici preregistrati/approvati, redirect HTTPS
  esatto, resource obbligatoria, codici monouso e token opachi. Scopes delegabili
  esclusivamente `utenze.read`, `catasto.read`, `ruolo.read`; niente Docs/audit.
- `oauth_store.py`: SQLite dedicato `gaia-mcp-oauth.sqlite`, permessi `0600`,
  token conservati solo come SHA256; emissione access/refresh e consumo in una
  transazione. Tombstone di refresh consumati fino alla scadenza originaria:
  un riuso revoca la famiglia attiva. DB da proteggere e non versionare.
- `oauth_http.py`: factory ASGI indipendente, handler SDK MCP per authorize e
  token/PKCE S256; guard aggiuntivo contro resource assente/diversa/duplicata.
  Revoca per client pubblici senza obbligo di `client_secret`: la versione SDK
  installata lo dichiara nullable ma obbligatorio nel proprio schema revoca.
  Metadata annunciano correttamente `none`, non le auth a secret di default SDK.

Durate: richiesta consenso 300 s, codice 60 s, access 300 s, refresh 8 h per
token emesso. Quest'ultimo e attualmente rolling, **non** un limite assoluto
di sessione; definire con il CED la durata massima prima del rilascio.
Utente disabilitato e riduzione permessi hanno effetto anche sull'access token
gia emesso. I token appartengono a subject GAIA, client e resource MCP.

## API della factory (non endpoint di produzione)

| Route relativa | Contratto |
| --- | --- |
| `/.well-known/oauth-authorization-server` | issuer/endpoint esplicitamente configurati, code + refresh, S256, nessuna registration |
| `/authorize` | client approvato, redirect registrato, scope data-only, resource; redirect alla futura UI consenso con request_id opaco |
| `/consent` GET | bearer della sessione GAIA; restituisce nome client, scope richiesti, resource |
| `/consent` POST | bearer GAIA; JSON strict `{request_id, allowed: boolean}`; restituisce redirect validato con code oppure access_denied e state |
| `/token` POST | form OAuth SDK + singola resource esatta; nessun password/implicit grant |
| `/revoke` POST | client_id e token; revoca solo la famiglia di quel client, sconosciuto => 200 |

La UI deve mostrare client e permessi, richiedere una scelta esplicita e usare
il login GAIA esistente se manca la sessione. Non approvare automaticamente,
non passare il bearer GAIA a Claude, non mettere token/password nei query
param. Consenso accetta solo bearer esplicito, non cookie ambientali; non
abilitare CORS per questa route. Redigere anche policy CSP, referrer e log
redaction: code, request_id, bearer e refresh sono sensibili.

## Configurazione e attivazione ancora da completare

La factory richiede store, mappa `OAuthClientInformationFull` approvata,
callback `user_scopes`, resource, consent_url e issuer HTTPS espliciti.
Le callback GAIA si ottengono con `gaia_oauth_callbacks(SessionLocal)`;
ogni lookup usa una sessione DB chiusa al termine. Non condividere lo store
SQLite tra thread: aprirlo, usarlo e chiuderlo nel lifecycle dello stesso
event loop; ogni worker deve avere la propria connessione.

I campi nel template environment sono **prenotazioni**, non flag gia collegati
al runtime. Nessuna route e abilitata dal loro inserimento. Restano necessari:

1. Hostname pubblico/tunnel approvato, certificato fidato dal servizio remoto
   e callback/client_id reali del connettore; nessun valore inventato.
2. UI consenso, wiring configurazione/lifecycle e metadata protected-resource
   RFC 9728 con routing corretto delle well-known anche per issuer con path.
3. Gateway remoto Data-only che converta il subject/scopes verificati nel
   `CallContext` GAIA. Non esporre listener legacy `/docs` o `/inspection`.
4. Budget/rate limit per principal, limiti richieste OAuth, cleanup periodico
   grants/tombstone, scadenza assoluta family e revoca amministrativa.
5. Test end-to-end OAuth -> discovery/tool call -> audit/provenance e prova
   reale Claude, sempre con database sintetico e senza Docs.

`https://gaia.lan` resta origine interna: non dimostra raggiungibilita del
servizio remoto Anthropic. La nuova CA interna resta decisione CED separata.

## Evidenze locali

`make test-mcp-oauth QUALITY_PYTHON=backend/.venv/bin/python`: 18 test verdi,
100% statement e branch su tutti e quattro i nuovi runtime. Test unitari e
ASGI in-process senza socket esterni; nessun test Claude o provider live.
Coperti PKCE valido/errato, redirect, state, resource, no Docs/audit, token
monouso, rotazione/replay, revoca cross-client, permessi/inactive, consenso
strict, rollback atomico, race consumo simulate e discovery/tool call SDK Data
con scope delegati e provenance sintetica. Il main target `test-mcp`
include la nuova suite, senza rimuovere i test precedenti.

Ruff/format mirati e ratchet autorevole sul perimetro OAuth contro merge-base
`origin/main` passati, nessuna nuova violation error-level, baseline invariata.
Il lint globale incontra I001 in `test_presenze_operations_postgres.py`, fuori
tranche; `compileall` richiede `PYTHONPYCACHEPREFIX=/tmp/gaia-oauth-pycache`
per evitare le directory cache preesistenti non scrivibili. Non e un PASS globale.

`make complexity-ratchet` globale rileva 23 finding fuori dai quattro file
OAuth (Presenze, gestione utenti/bootstrap, Elaborazioni, Organigramma e
API core frontend): non corretti in questa tranche, nessuna baseline aggiornata.
`make test-mcp` completo interrotto dal timeout di 45 s nel contratto Docs SDK
con socket; non e un PASS e non dimostra coverage full-package. La regressione
locale socket-free passa 182 test ed esclude esplicitamente quattro test SDK/stdio/live-HTTP,
senza modificarli. Log in `/tmp/gaia-oauth-{tests,regression,full-mcp,lint,ratchet,ratchet-global}.log`.
Graphify aggiornato via `make graphify-wiki-code`: 112 file AST, 986 nodi,
2330 archi. Nessuna estrazione docs verso un LLM esterno: vincolo privacy.
Metriche nuovi runtime (assenza al merge-base -> 4 file/36 callable): massimi
cognitiva 12, ciclomatica 10; 6 warning, 0 error. Baseline invariata.
