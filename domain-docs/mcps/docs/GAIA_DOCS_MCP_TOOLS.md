# GAIA Docs MCP — catalogo tool v1

## `search_docs`

Input:
```json
{
  "query":"string",
  "domain":"catasto|utenze|ruolo|wiki|null",
  "category":"architecture|procedure|runbook|prd|workflow|null",
  "limit":5
}
```

Output per risultato:
```json
{
  "chunk_id":"string",
  "source_path":"domain-docs/...",
  "title":"string",
  "section":"string|null",
  "content":"string",
  "score":0.0,
  "domain":"catasto",
  "category":"procedure",
  "estimated_tokens":320
}
```

## `get_doc_section`

Input:
```json
{"chunk_id":"string","max_chars":6000}
```

Output: contenuto + provenance.

## `get_document_metadata`

Input:
```json
{"source_path":"string"}
```

Output:
- titolo;
- dominio;
- categoria;
- stato;
- hash;
- corpus version;
- sezioni disponibili.

Non restituire automaticamente l'intero documento.

## `list_doc_domains`

Restituisce domini disponibili e conteggio documenti/chunk.

## Tool opzionale successivo

### `search_related_sections`

Da valutare solo se retrieval/grafo dimostra valore.

## Non implementare

- `answer_from_docs`;
- `search_all_sources`;
- `ask_wiki_agent`;
- tool che chiamano Data MCP;
- tool che generano una risposta LLM finale.

## Provenance

Ogni evidenza deve riportare almeno:
- `source_path`;
- `chunk_id`;
- heading/sezione;
- hash documento;
- corpus version.
