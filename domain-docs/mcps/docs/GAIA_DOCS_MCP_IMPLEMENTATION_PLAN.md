# GAIA Docs MCP — piano di implementazione

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

GAIA Wiki Agent deve ricevere il Docs MCP come source distinta dal Data MCP.

## Definition of Done

- [ ] manifest;
- [ ] corpus version;
- [ ] chunk ID stabili;
- [ ] retrieval baseline;
- [ ] tool MCP;
- [ ] provenance;
- [ ] telemetry;
- [ ] test;
- [ ] nessun codice sorgente nel corpus v1 salvo decisione esplicita;
- [ ] nessun routing globale.
