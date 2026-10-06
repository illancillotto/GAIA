# Hardening OAuth e perimetro locale

## Stato implementato

Il listener opt-in Data-only dispone di limiti di retention, sessione assoluta
e revoca amministrativa. Rimane disabilitato per default: questa modifica non
crea certificati, client approvati, ingresso Internet o accesso ai documenti NAS.

| Variabile | Default | Contratto |
| --- | --- | --- |
| `GAIA_MCP_OAUTH_SESSION_SECONDS` | 28800 | Durata assoluta dalla prima coppia access/refresh |
| `GAIA_MCP_OAUTH_CLEANUP_SECONDS` | 60 | Manutenzione indipendente dalle richieste |
| `GAIA_MCP_OAUTH_MAX_GRANTS` | 10000 | Massimo record globali |
| `GAIA_MCP_OAUTH_MAX_CLIENT_GRANTS` | 1000 | Massimo record per client |

Valori interi positivi; limite client non superiore a quello globale.
Configurazione invalida: avvio impedito. Compose passa i quattro valori al
listener isolato; nessuna modifica alla sessione login GAIA.

I cap includono pending, code, access, refresh e tombstone non scaduti.
Controllo e inserimento sono atomici (`BEGIN IMMEDIATE`), anche fra worker.
Prima del controllo vengono rimossi i record scaduti; quelli validi non sono
espulsi. A cap raggiunto: `503 temporarily_unavailable`, `no-store`,
`Retry-After: 60`, senza dettagli storage. Consenso e coppie token sono atomici:
la mancata emissione preserva pending/code/refresh, senza access token parziale.

`session_expires_at` persiste nel payload; il refresh ruota senza prolungarlo.
Access token al massimo 300 secondi e mai oltre il termine assoluto. Riavvio:
nessun rinnovo. Access/refresh legacy senza termine sono rifiutati, richiedono
nuovo consenso; i code ancora validi possono iniziare una nuova sessione.
Tombstone refresh preservati fino alla scadenza per rilevare replay.

Manutenzione grant e finestre budget all'avvio e ogni intervallo configurato.
Errore iniziale: avvio impedito. Errore SQLite periodico: log senza dettagli
sensibili e retry al ciclo successivo. Shutdown: cancella/attende il task prima
di chiudere lo store. Nessuna chiamata Data necessaria.

## Revoca amministrativa interna

`POST /api/wiki/mcp/connector/oauth/admin/revoke`, **solo listener isolato**:
non nell'allowlist del gateway, nessuna porta host pubblicata. Usare dalla rete
container approvata; non aggiungerla alla proxy allowlist.

Bearer sessione GAIA, utente attivo, ruolo canonico `admin`/`super_admin`,
rivalutati ad ogni richiesta. Il token MCP non conferisce autorita admin.
Nessuna registration, CORS o UI amministrativa aggiunta.

JSON strict: `{"subject":"123"}`, `{"client_id":"client-approvato"}` o entrambi
(intersezione). `subject`: ID GAIA stringa, non username NAS. Nessun selettore:
400, mai revoca globale implicita. Risposta `{"revoked_grants":2}`, `no-store`:
numero di record attivi eliminati, non utenti/sessioni. Tombstone preservati,
altri utenti/client invariati. Log strutturato: actor e selettori SHA256,
conteggio e stato; niente bearer/token. Errore storage: 503 fail-closed.

## Decisioni e prerequisiti

- `gaia.lan`, solo LAN. HTTP MCP reindirizza a HTTPS (`HTTP_HTTPS_GATEWAY.md`).
  Nessuna apertura Internet implicita; certificati/CA approvati CED ancora necessari.
- Claude Desktop locale via stdio/bridge. Config stdio Data esistente solo
  sintetica; profilo Desktop ora configurato e handshake/discovery reali verificati
  (`LAN_DESKTOP_READINESS_2026-10-05.md`). Chiamata dal modello ancora da confermare.
- ChatGPT da valutare: il connettore cloud non raggiunge direttamente `gaia.lan`.
- NAS: permessi effettivi account NAS, deny e gruppi, non sola sezione GAIA.
  Prima delle letture serve mapping GAIA/NAS verificato e fonte ACL aggiornata;
  niente matching automatico nome/email. Nessun documento reale esposto/inviato.
- Trasparenza: catalogo approvato da definire; estensione non attivata.

## Verifica

`make test-mcp-oauth`, `make test-mcp-connector`, `make test-mcp`: test di policy,
cap concorrenti, rollback, sessione/restart/legacy, cleanup senza traffico,
errori/shutdown e revoca admin. Target 100% statement/branch dei runtime
toccati, senza abbassare soglie o escludere codice.

Esiti finali locali:

- Suite MCP: 320 passati, 2132 statement e 438 branch al 100% su 45 runtime.
  I nove runtime di questa tranche: 603 statement e 146 branch, tutti al 100%.
- Gateway Nginx/TLS: 67 passati, inclusa verifica HTTP/HTTPS che la revoca admin
  non sia inoltrata al listener connector. Non e una prova Claude Desktop live.
- Ruff/check-format mirati, diff-check e Compose config: PASS.
- Metriche prima/dopo: sei file esistenti piu tre nuovi, 47 -> 63 callable,
  warning 12 -> 11, error 0 -> 0. Configurazione transport estratta in un'unita
  coesa, invariata: factory LOC 53 -> 42, lifespan 46 -> 35; nessun nuovo debito.
- Ratchet autorevole full scan contro merge-base `6b61fd27`: nessun finding
  MCP. Restano 24 finding globali estranei, baseline/soglie/esclusioni invariate.
- Lint backend globale: FAIL formatter Presenze `daily_details.py` e
  `shift_assignments.py`, fuori tranche. Nessuna correzione opportunistica.
- Graphify codice Wiki forzato con patch pruning; corpus dominio e piattaforma
  aggiornati via Make, modello docs `gpt-reserve`, chunk completati senza failure
  semantiche. Artifact `graphify-out/` non versionati.

Non e un PASS globale o un rilascio HTTPS: niente commit finale implicito, nuovi
certificati o invio di documenti NAS cloud. Il profilo Desktop reale e stato
configurato nella successiva verifica operativa, preservando le preferenze.
Evidenze locali: `/tmp/gaia-hardening-final.log`,
`/tmp/gaia-hardening-full-file-coverage.json`, `/tmp/gaia-hardening-gateway.log`,
`/tmp/gaia-hardening-{before,after}.json`, `/tmp/gaia-hardening-ratchet-final.json`.
