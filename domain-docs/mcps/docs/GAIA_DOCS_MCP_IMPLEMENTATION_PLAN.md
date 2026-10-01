# GAIA Docs MCP — piano di implementazione

## Stato implementazione al 2026-10-01

Disponibile il runtime locale `backend/app/modules/wiki/mcps/docs/`: builder
manifest esplicito, snapshot con hash/versione/chunk ID stabili, baseline SQLite
FTS5, quattro tool MCP strutturati, telemetria e server stdio verificato con SDK
2.0.0. Comandi e limiti in `README.md`. Audit e freeze iniziale di due fonti
operative completati, due candidati incerti esclusi. 32 query di retrieval,
HTTP interno autenticato, propagazione del contesto GAIA e integrazione Wiki
sono verificati; dettagli in `../RUNTIME_AND_VALIDATION.md`. Retrieval candidato
e cache sono opzionali e non attivati senza evidenza di valore.
Il client interno Docs/Data e verificato con LLM simulato; Docs e escluso lato
server dall'agente esterno `gpt-reserve`. Non sono previsti esperimenti cloud
su documenti reali. Fasi 0–3, 5 e 7 completate per il corpus v1; fasi 4 e 6
opzionali residue. La fase 8 e limitata al client interno separato.
Matrice e gate finale: `../FINAL_DEVELOPMENT_REVIEW.md`.

## Fase 0 — audit

- verificare `docs/DOCS_STRUCTURE.md`;
- enumerare documenti reali;
- classificare current/historical/deprecated;
- identificare duplicati e aree ambigue.

## Fase 1 — manifest

Implementare build del manifest con:
- path;
- hash;
- dominio;
- categoria;
- status;
- included;
- reason.

## Fase 2 — pipeline ingest

```text
filesystem Git
   |
   v
policy filter
   |
   v
parser Markdown
   |
   v
chunking
   |
   v
metadata normalization
   |
   v
index
```

## Fase 3 — retrieval baseline

Riutilizzare o isolare il PostgreSQL FTS esistente come prima baseline se conveniente.

L'indice sperimentale deve rispettare il corpus manifest e non includere automaticamente codice/progress.

## Fase 4 — retrieval candidato

Solo dopo baseline, valutare:
- embedding;
- hybrid retrieval;
- reranking;
- Graphify/graph retrieval.

Ogni variante deve essere misurabile con lo stesso set di query.

## Fase 5 — server MCP

Implementare i tool definiti in `GAIA_DOCS_MCP_TOOLS.md`.

## Fase 6 — cache

Cache consentita se:
- non cambia ranking semanticamente;
- è invalidata per corpus version;
- è tracciabile.

## Fase 7 — osservabilità

Integrare `../OBSERVABILITY_AND_EVALUATION.md`.

## Fase 8 — integrazione Wiki

Il client interno mantiene Docs come source distinta dal Data MCP. Il gateway
esterno `/wiki/mcp/*` non riceve Docs e rifiuta le sue invocazioni.

## Definition of Done

- [x] manifest;
- [x] corpus version;
- [x] chunk ID stabili;
- [x] retrieval baseline;
- [x] tool MCP;
- [x] provenance;
- [x] telemetry;
- [x] test;
- [x] nessun codice sorgente nel corpus v1 salvo decisione esplicita;
- [x] nessun routing globale.
