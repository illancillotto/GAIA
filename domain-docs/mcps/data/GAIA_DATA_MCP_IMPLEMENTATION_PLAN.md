# GAIA Data MCP — piano di implementazione

## Stato v1 al 2026-10-01

Runtime implementato nel package Wiki: database sintetico separato SQLite,
schema/migration v1, seed/reset atomico e manifest deterministico, query fisse,
dodici tool read-only, stdio/HTTP interno e gateway autorizzato GAIA. Integrazione
Wiki verificata tramite client SDK/HTTP con modello simulato e tramite gateway
autenticato con `gpt-reserve` reale su soli dati sintetici: 30/30 query live.
30 query strutturate con ground truth e test security/contract/coverage.
Runbook, decisioni e limiti in `../RUNTIME_AND_VALIDATION.md`.
Audit finale e matrice comportamento/test: `../FINAL_DEVELOPMENT_REVIEW.md`.
Le fasi 1–8 del core sono completate; il dettaglio sotto mantiene il brief
progettuale. Operazioni, deploy e ampliamento delle fonti restano fuori scope.
Il gate finale complessivo resta FAIL per smoke/build frontend non superati.

## Fase 0 — freeze progettuale

Approvare:
- analisi runtime;
- schema sintetico;
- catalogo tool;
- test plan.

## Fase 1 — package/server MCP

Creare un componente chiaramente separato dall'agente Wiki.

Possibile collocazione da valutare:
`backend/app/modules/wiki/mcps/data/`

Non creare una nuova architettura parallela al monolite senza motivazione.

## Fase 2 — synthetic DB

Implementare:
- schema;
- migration;
- generator;
- seed;
- reset command;
- manifest versione dataset.

## Fase 3 — service layer

Implementare query application-level riutilizzabili dal server MCP.

Nessun SQL costruito dal modello.

## Fase 4 — MCP tools

Registrare i tool approvati con:
- JSON schema;
- validation;
- scope;
- service call;
- serializer;
- provenance;
- telemetry.

## Fase 5 — transport

Sviluppo: stdio o HTTP interno.

Integrazione: endpoint interno coerente con `../MCP_PROTOCOL_BASELINE.md`.

## Fase 6 — auth e permission

Mappare identità GAIA → permission scope.

## Fase 7 — osservabilità

Integrare `../OBSERVABILITY_AND_EVALUATION.md`.

## Fase 8 — collegamento Wiki Agent

Collegare il Data MCP solo dopo i test indipendenti.

## Fase 9 — Operazioni decision gate

Dopo il core:
- analisi costi/benefici;
- decisione esplicita;
- nessuna inclusione automatica.

## Definition of Done

- [x] server avviabile;
- [x] tool list deterministica;
- [x] dataset riproducibile;
- [x] test passano;
- [x] no write tool;
- [x] no SQL libero;
- [x] provenance;
- [x] scope;
- [x] telemetry;
- [x] integrazione Wiki Agent verificata.
