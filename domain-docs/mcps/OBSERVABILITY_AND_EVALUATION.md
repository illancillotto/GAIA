# Osservabilità e valutazione MCP

## Evento minimo per tool call

```json
{
  "request_id": "uuid",
  "experiment_run_id": "uuid",
  "conversation_id": "uuid",
  "tool_name": "search_parcels",
  "source": "gaia_synthetic_db",
  "duration_ms": 18,
  "status": "ok",
  "result_count": 3,
  "truncated": false,
  "estimated_output_tokens": 410,
  "permission_scope": "catasto.read",
  "server_version": "git-sha",
  "dataset_or_corpus_version": "version-id"
}
```

## Metriche

- accuratezza rispetto al ground truth;
- fonte corretta selezionata al primo tentativo;
- numero di tool call;
- numero di fonti consultate;
- latenza;
- token/equivalente di contesto recuperato;
- risposte corrette per unità di budget;
- retrieval precision/recall quando misurabile;
- tasso di risultati vuoti;
- tasso di fallback;
- tasso di astensione corretta;
- errori di permission;
- errori di tool selection.

## Budget di contesto

Ogni MCP deve rendere stimabile il costo informativo restituito con una regola deterministica e documentata.

## Versionamento

Ogni run fissa:
- commit repository;
- versione corpus;
- hash/manifest;
- versione schema sintetico;
- seed;
- tool catalog;
- configurazione retrieval;
- modello e parametri;
- budget.

## Riproducibilità

Produrre comandi per:
- build corpus;
- generazione dataset;
- test MCP;
- export metriche.
