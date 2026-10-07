# MCP live: letture GAIA autorizzate — 2026-10-07

## Stato e confini

Il package `backend/app/modules/wiki/mcps/live/` implementa un server MCP
stdio separato, opt-in e read-only. Usa le API HTTPS GAIA con il bearer
dell'utente; non accede direttamente a database, NAS o filesystem applicativo.
Il gateway e il connector OAuth sintetici non montano questo catalogo e
continuano a usare la replica sintetica. Nessun deploy, client OAuth nuovo,
tunnel, ingresso Internet o invio di dati reali a modelli esterni e incluso.

Il codice e disponibile localmente: non equivale a un endpoint live attivo
su `gaia.lan`, ne a un collaudo nelle applicazioni Claude/ChatGPT/Codex.
Lo stato CED precedente resta in `CURRENT_STATUS_2026-10-06.md`.

## Catalogo implementato

Tutti gli strumenti richiedono inclusione esplicita nell'allowlist di avvio,
utente attivo e autorizzazioni GAIA rivalidate a ogni discovery/invocazione.
L'API sorgente continua ad applicare i propri controlli di accesso.

| Strumento | Fonte backend | Modulo / sezioni aggiuntive MCP |
| --- | --- | --- |
| `search_gaia` | `/api/search` | Utenze, Catasto e Ruolo; `utenze.subjects`, `catasto.dashboard`, `ruolo.avvisi`, tutti obbligatori |
| `get_subject` | `/utenze/subjects/{record_id}` | `utenze` / `utenze.subjects` |
| `get_role_notice` | `/ruolo/avvisi/{record_id}` | `ruolo` / `ruolo.avvisi` |
| `search_parcels` | `/catasto/parcels` | `ruolo` / `ruolo.avvisi`, coerente con l'API esistente |
| `search_assets` | `/api/dotazioni/assets` | `dotazioni` / `dotazioni.view` |
| `get_asset` | `/api/dotazioni/assets/{record_id}` | `dotazioni` / `dotazioni.view` |
| `get_asset_custody` | `/api/dotazioni/assets/{record_id}/custody` | `dotazioni` / `dotazioni.view` |
| `get_asset_history` | `/api/dotazioni/assets/{record_id}/events` | `dotazioni` / `dotazioni.history` |
| `get_my_summary` | `/me/summary` | Utente autenticato, riepilogo personale secondo i moduli GAIA abilitati |
| `get_my_presenze` | `/me/presenze/daily-records` | `presenze`, solo identita canonica dell'utente |
| `get_my_reports` | `/me/operazioni/reports` | `operazioni`, solo metadati dei rapporti personali |
| `get_operations_summary` | `/operazioni/dashboard/summary` | `operazioni` / `operazioni.dashboard` |
| `list_org_units` | `/organigramma/units` | `organigramma` / `organigramma.read` |
| `list_network_devices` | `/network/devices` | `rete` / `rete.devices` |
| `list_network_scans` | `/network/scans` | `rete` / `rete.scan`, senza avvio scansioni |
| `get_portal_health` | `/elaborazioni/portal-health` | `catasto` / `catasto.dashboard`, telemetria del solo utente |
| `get_processing_request` | `/elaborazioni/requests/{record_id}` | `catasto` / `catasto.dashboard`, richiesta del solo utente |

La tabella usa path backend, non URL esterni: Nginx rimuove il primo `/api`.
La custodia corrente puo essere `null` se il bene non e assegnato;
lo storico eventi accetta `page` e `page_size` bounded.
Il client aggiunge quindi `/api` a ciascun path, anche dove la route backend
contiene gia `/api`. Per esempio, Dotazioni usa `/api/api/dotazioni/assets`.
`record_id` deve essere un UUID; non tutti gli ID della ricerca globale
identificano soggetti o avvisi: controllare `module` e `type` prima del dettaglio.

## Privacy, limiti e audit

- Proiezione ricorsiva su campi allowlisted per strumento. Esclusi credenziali,
  percorsi NAS, documenti/attachment, note libere, dettagli eventi Dotazioni,
  CF anagrafici strutturati, causali mediche, testi rapporti, captcha e errori
  grezzi delle elaborazioni. Nomi, titoli e metadati consentiti restano dati reali:
  non sono anonimizzati; i titoli della ricerca possono essere nomi file.
- Le Presenze usano l'API self-service fondata su `application_user_id`, senza
  matching per nome, email, matricola o ID numericamente uguali. Un'identita
  non assegnata non ottiene dati per fallback. Il MCP non corregge mapping.
- Pagine 1..1000, dimensione 1..50; ricerca globale 2..120 caratteri e
  massimo 30 risultati; telemetria 1..72 ore. Nessun parametro per impersonare
  altri utenti. Campi sconosciuti vengono rifiutati.
- Risposta sorgente massima 64 KiB, timeout 10 secondi, niente redirect o proxy
  impliciti dall'ambiente. Output con liste fino a 50 elementi, stringhe fino
  a 500 caratteri e profondita fino a 6; `truncated` segnala i tagli.
  Le sorgenti non paginate sono limitate nella risposta, non trasformate
  artificialmente in API paginate: oltre 64 KiB la lettura fallisce.
- Budget per processo: 60 richieste discovery/invocazione al minuto, di cui
  al massimo 20 invocazioni. Anche gli errori consumano budget; nessun limite
  distribuito tra piu processi viene dichiarato.
- Provenance: `source`, path chiamato e timestamp UTC. Audit locale dedicato
  con utente pseudonimizzato, strumento, request ID e stato; nessuna query,
  token o record. File `gaia-mcp-audit.sqlite` 0600, retention 1000 chiamate.
  Se la registrazione fallisce, i dati non vengono restituiti.
- Il bearer GAIA rimane nel processo; non vengono creati refresh token o
  sessioni OAuth live. Scadenza del token o disattivazione utente negano
  nuove chiamate. La revoca di permessi/moduli viene riletta dal backend.

## Avvio locale esplicito

Prerequisiti: ambiente backend installato, HTTPS GAIA attivo e raggiungibile,
CA attendibile, sessione GAIA valida e approvazione del perimetro dati per
il client scelto. Il certificato corrente copre `gaia.lan`, non l'IP.
Non avviare contro produzione prima di queste verifiche.

Esempio Bash dalla root GAIA, senza salvare il token nella configurazione:

```bash
export GAIA_MCP_LIVE_ENABLED=true
export GAIA_MCP_LIVE_ORIGIN=https://gaia.lan
export GAIA_MCP_LIVE_CA_FILE=/percorso/certificato-pubblico-ca.pem
export GAIA_MCP_LIVE_AUDIT="$HOME/.local/state/gaia-mcp-live/gaia-mcp-audit.sqlite"
export GAIA_MCP_LIVE_TOOLS=search_assets,get_asset
read -rs -p 'Bearer della sessione GAIA: ' GAIA_MCP_LIVE_TOKEN; printf '\n'
export GAIA_MCP_LIVE_TOKEN
make mcp-live QUALITY_PYTHON=backend/.venv/bin/python
unset GAIA_MCP_LIVE_TOKEN
```

Per un client MCP stdio usare direttamente Python con
`-m app.modules.wiki.mcps.live`, `PYTHONPATH=backend` e directory di lavoro
root GAIA: `make` stampa il comando e non va usato come trasporto stdio
del client. L'ambiente del processo client deve ereditare il token in modo
effimero; non inserirlo in JSON/TOML, `.env`, cronologia shell o repository.
Nessun profilo applicazione viene riconfigurato automaticamente. Anche
Claude Desktop/Code e Codex possono inviare i risultati al proprio servizio
modello: collegamento locale non significa elaborazione esclusivamente locale.
ChatGPT Desktop non viene dichiarato compatibile con questo avvio stdio;
nessun endpoint pubblico o tunnel e stato attivato.

## Integrazioni ancora escluse

1. NAS: servono share approvate, mapping canonico GAIA/NAS e verifica ACL
   per documento sul NAS a ogni accesso; non basta leggere una vecchia scansione.
2. Trasparenza: servono sorgente/catalogo approvati e policy di distribuzione.
3. Batch Elaborazioni: le GET esistenti chiamano `sync_batch_counters`;
   non sono inserite nel catalogo read-only. Serve un contratto separato di pura lettura.
4. Scritture, sync, scansioni, export/download e tool calling automatico su
   dati reali: non implementati o abilitati da questo ciclo.

## Verifiche riproducibili

```bash
make test-mcp-live QUALITY_PYTHON=backend/.venv/bin/python
make test-mcp QUALITY_PYTHON=backend/.venv/bin/python
backend/.venv/bin/ruff check backend/app/modules/wiki/mcps/live backend/tests/test_wiki_mcp_live*.py
backend/.venv/bin/ruff format --check backend/app/modules/wiki/mcps/live backend/tests/test_wiki_mcp_live*.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/wiki/mcps/live
```

Le suite usano esclusivamente dati sintetici: route GET esatte, proiezione
pertinente a ogni fonte, schema, budget, errori sanitizzati, HTTPS, redirect,
limiti, audit e cleanup. Integrazione SDK MCP con initialize/list/call/revoca;
integrazione ASGI con vere route GAIA, JWT, resolver permessi e SQLite
effimero per isolamento Presenze e revoca Dotazioni. Non certificano TLS
del CED, PostgreSQL, installazioni desktop o autorizzazione all'invio cloud.

### Evidenze locali e residui

Le evidenze sotto descrivono la fine dell'implementazione iniziale. La
riverifica finale successiva, i test aggiunti e il fix JSON patologico sono
registrati in `FINAL_VALIDATION_2026-10-07.md`; progress in `PROGRESS.md`.
Non usare i conteggi iniziali come risultato dell'ultima esecuzione.

- `test-mcp` completo: 402 test PASS, 2319/2319 statement e 478/478
  branch, coverage 100% sui 52 file misurati. Nessuna regressione rilevata
  dalla suite MCP. Log `/tmp/gaia-mcp-suite-final.log` e report
  `backend/coverage-mcp.json` (generato, non da versionare).
- `test-mcp-live`: 82 test PASS, 187/187 statement e 40/40 branch,
  zero esclusioni e zero warning. Report `/tmp/gaia-mcp-live-coverage.json`;
  log `/tmp/gaia-live-isolated-final.log`. Coverage file separato dalla suite
  completa per evitare interferenze fra processi.
- Ruff check, format-check dei nove file Python live/test e `git diff --check`
  PASS. Compileall del gate backend completato.
- Ratchet del solo runtime live contro merge-base `703f8411` di
  `origin/main`: zero finding bloccanti; baseline, soglie e scope invariati.
  Report `/tmp/gaia-live-ratchet-final.json`. Codice nuovo, quindi nessun
  debito legacy di questo package da confrontare o assorbire nella baseline.
- Metriche finali: sette file, 14 callable, zero violation error-level,
  sette warning non bloccanti. Massimo cognitive 17 in `GaiaAPI.get`,
  cyclomatic 11; restano segnalazioni anche su proiezione, validazione
  identita e budget. Report `/tmp/gaia-live-metrics-final.json`; non viene
  dichiarata eliminata tutta la complessita.
- `make lint-backend BASE_REF=HEAD`: FAIL globale, 19 errori Ruff in
  `backend/app/modules/operazioni/routes/mobile_sync.py`, modificato da
  lavoro concorrente fuori dal perimetro MCP. Nessuna di quelle modifiche
  viene corretta o inclusa in un commit MCP. Log
  `/tmp/gaia-live-lint-backend.log`; il gate globale non e dichiarato verde.
- Nessun commit o deploy: restano verifiche reali HTTPS/client e approvazioni
  NAS/Trasparenza; questo ciclo non certifica l'intero repository.
