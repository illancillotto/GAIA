# Baseline del protocollo MCP

## Stato di riferimento

Alla data di redazione (agosto 2026), la revisione MCP pubblicata il 28 luglio 2026 introduce un core stateless e aggiornamenti al trasporto e all'autorizzazione.

Prima dell'implementazione finale il team deve verificare la revisione corrente della specifica e la versione dell'SDK scelta.

Riferimenti ufficiali:
- https://modelcontextprotocol.io/
- https://blog.modelcontextprotocol.io/posts/2026-07-28/

## Decisioni GAIA

### Interfaccia primaria
Usare **tools** come interfaccia principale.

### Resources
Possono essere esposte per schema, manifest, metadati e documenti identificati.

### Prompts
Non richiesti nella v1. Il prompting resta responsabilità di GAIA Wiki Agent.

### Trasporto
Per integrazione server-to-server interna è preferibile un trasporto HTTP MCP supportato dall'SDK corrente. Per sviluppo locale è ammesso stdio.

### Statelessness
Non dipendere da stato di sessione nascosto nel server MCP.

## Compatibilità

Documentare:
- SDK;
- versione;
- transport;
- versione protocollo;
- eventuali estensioni.
