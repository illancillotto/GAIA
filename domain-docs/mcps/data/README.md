# GAIA Data MCP

Il catalogo operativo live sviluppato al 2026-10-07 appartiene al server
stdio separato `live/`, non a questo Data MCP sintetico. Contratti e
abilitazione esplicita: `../LIVE_READS_2026-10-07.md`.

## Runtime v1 implementato

Dodici tool read-only, replica SQLite sintetica isolata e deterministica,
input tipizzati, cap, cursori, scope, provenance e telemetria. Server stdio e
HTTP interno, integrato con l'agente Wiki. Dettagli e motivazione dello schema
isolato in `../RUNTIME_AND_VALIDATION.md`. Nessun accesso ai dati operativi.

## Missione

Esporre all'agente principale un accesso **read-only, tipizzato e misurabile** ai dati strutturati utili alla tesi.

## Perimetro core

- Catasto
- Utenze
- Ruolo

## Operazioni

Il modulo Operazioni deve essere analizzato come possibile estensione. Non entra automaticamente nel core sperimentale.

## Non obiettivi

- esporre l'intero database;
- fornire SQL libero;
- rispondere direttamente all'utente;
- interrogare Docs, NAS o Trasparenza;
- fare routing globale;
- usare dati reali nei test cloud.

## Documenti

1. `GAIA_DATA_MCP_PROMPT.md`
2. `GAIA_DATA_MCP_ANALYSIS.md`
3. `GAIA_DATA_MCP_SYNTHETIC_SCHEMA.md`
4. `GAIA_DATA_MCP_TOOLS.md`
5. `GAIA_DATA_MCP_IMPLEMENTATION_PLAN.md`
6. `GAIA_DATA_MCP_TEST_PLAN.md`
