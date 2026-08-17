# GAIA Data MCP — piano di implementazione

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

- [ ] server avviabile;
- [ ] tool list deterministica;
- [ ] dataset riproducibile;
- [ ] test passano;
- [ ] no write tool;
- [ ] no SQL libero;
- [ ] provenance;
- [ ] scope;
- [ ] telemetry;
- [ ] integrazione Wiki Agent verificata.
