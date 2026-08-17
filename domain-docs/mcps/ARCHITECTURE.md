# Architettura MCP per GAIA Wiki

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
