# Architettura MCP per GAIA Wiki

Aggiornamento 2026-10-05: `OAUTH_HARDENING_2026-10-05.md` descrive policy
retention/sessione, manutenzione lifespan e revoca admin interna. Host solo LAN
`gaia.lan`, client Claude Desktop locale. NAS/Trasparenza non esposti.

Aggiornamento 2026-10-03: il listener OAuth separato riusa il package Wiki
e la stessa immagine backend, autenticazione GAIA e DataService/AuditStore.
Solo dataset generato sintetico; nessuna route Docs/inspection. La UI consenso
vive in `features/wiki`, con callback `/mcp/consent`; non sostituisce la chat
Wiki legacy. Flag disattivate e rilascio non eseguito. Contratto e API:
`CONNECTOR_RUNTIME_2026-10-03.md`; gate: `CONNECTOR_FINAL_REVIEW_2026-10-03.md`.

## Scopo

Definire l'architettura dei due MCP interni a GAIA utilizzati dall'agente principale della tesi:
- GAIA Docs MCP;
- GAIA Data MCP.

La scelta di due MCP separati mantiene distinta la fonte documentale dalla fonte strutturata e rende misurabile la selezione dinamica delle fonti.

## Principio architetturale

L'orchestrazione appartiene a **GAIA Wiki Agent**, non agli MCP.

```text
                    GAIA Wiki Agent
                         |
          +--------------+--------------+
          |                             |
          v                             v
  GAIA Docs MCP                  GAIA Data MCP
          |                             |
          v                             v
 corpus documentale             dati strutturati
```

Gli MCP sono adapter di fonte.

Runtime v1 verificato al 2026-10-01: i package Docs/Data/HTTP/client/agente
vivono in `backend/app/modules/wiki/mcps/`, montati dal router Wiki del monolite.
Il processo MCP separato e una modalita di avvio della stessa immagine backend,
non un nuovo servizio di dominio. Nessuna nuova migration PostgreSQL operativa
introdotta; la replica sintetica usa SQLite dedicato e il corpus Docs
usa FTS5 locale. Il diagramma sopra descrive le fonti del client interno.

Il gateway autenticato `/wiki/mcp/token`, `/tools`, `/chat` abilita soltanto Data:
`docs_url=None`, rimozione `docs.read`, blocco discovery/session/invocazioni Docs.
L'agente usa `gpt-reserve` con URL/chiave codex-lb esistenti; nessuna fonte Docs,
NAS, Trasparenza o cronologia legacy entra nei messaggi. La chat Wiki legacy
mantiene le proprie route, configurazione e comportamento. Dettagli operativi
in `RUNTIME_AND_VALIDATION.md`; audit finale in `FINAL_DEVELOPMENT_REVIEW.md`.

Il recupero selettivo aggiunge `mcps/experiment_*` nello stesso dominio Wiki e
la preview `frontend/src/app/wiki/mcp/page.tsx`, che usa `/wiki/mcp/chat` senza
nuove API o servizi duplicati. La baseline sperimentale FTS5 viene costruita
solo dal database sintetico verificato; il runner delega tool calling all'agente
corrente. Nessun modello ORM, tabella operativa o migration nuova. Piano e
contratti: `SYNTHETIC_RECOVERY_PLAN.md`.

L'API Python interna e `run_comparison(cases, executor, output)`, con
`executor: ComparisonExecutor` costruito dalla CLI usando fonti, modello,
corpus e configurazione. Il runner usa corpus/config dell'executor anche per
manifest e schedule, senza duplicare questi parametri o crearne un altro.
Nel runner, `run_comparison` gestisce manifest, schedule e ciclo di vita del
journal; `ComparisonExecutor.execute_item` gestisce la ripresa e i retry del
singolo elemento. Un elemento gia completato non viene rieseguito; i tentativi
condividono il contesto e vengono persistiti prima di aggiornare i record in
memoria. Il limite di retry resta quello della configurazione dell'esperimento.
Il journal distingue lifecycle/lock nel costruttore da lettura e validazione
in `_read_rows`: controlla prima tutte le newline, poi JSON e manifest;
qualsiasi errore preserva il contenuto e rilascia file e lock.

## Contratto comune degli output

Ogni tool dovrebbe restituire una struttura equivalente a:

```json
{
  "tool": "tool_name",
  "source": "gaia_docs|gaia_synthetic_db",
  "results": [],
  "provenance": [],
  "result_count": 0,
  "truncated": false,
  "estimated_tokens": 0,
  "request_id": "uuid"
}
```

Devono sempre essere ricostruibili:
- tool invocato;
- fonte;
- evidenze;
- record o sezione di origine;
- numero risultati;
- eventuale troncamento;
- dimensione approssimativa dell'output;
- correlazione con audit/telemetria.

## Anti-pattern vietati

Evitare tool come:
- `answer_everything`;
- `get_full_subject_context`;
- `search_all_gaia`;
- `execute_sql`.

Gli MCP non devono:
- scegliere altre fonti;
- chiamare NAS o Trasparenza;
- decidere il piano globale;
- costruire il contesto finale;
- generare la risposta utente finale.

Ogni tool deve avere `limit`, hard cap server-side e output controllato.

## Feature MCP

### Tools
Interfaccia primaria.

### Resources
Utili per schema, manifest, metadati e documenti identificati.

### Prompts
Non necessari nella v1. Il prompting resta nell'agente principale.

## Ambienti

### Sviluppo locale
È ammesso stdio o un endpoint interno protetto.

### Integrazione GAIA
Preferenza per endpoint MCP interno, non pubblicamente esposto.

### Esperimenti
Registrare commit GAIA, versione dataset/corpus, configurazione retrieval, seed, limiti e versione server.
