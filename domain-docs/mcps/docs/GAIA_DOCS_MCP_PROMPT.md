# Prompt operativo — progettazione GAIA Docs MCP

## Obiettivo

Progettare e implementare **GAIA Docs MCP** come adapter documentale per l'agente principale di GAIA Wiki.

Il Docs MCP non è l'agente della tesi.

## Fase 1 — audit documentale

Usare come punto di partenza:
- `docs/DOCS_STRUCTURE.md`;
- `docs/`;
- `domain-docs/`;
- `domain-docs/wiki/operational/`.

Verificare contenuto reale e freschezza.

## Fase 2 — corpus policy

Applicare `GAIA_DOCS_MCP_CORPUS_POLICY.md`.

Produrre un manifest con:
- path;
- hash;
- dominio;
- categoria;
- stato;
- data/versione;
- include/exclude;
- motivazione.

## Fase 3 — retrieval

Non imporre subito una tecnologia.

Valutare almeno:
- PostgreSQL FTS esistente come baseline;
- retrieval semantico;
- retrieval ibrido;
- eventuale Graphify/grafo solo se aggiunge valore misurabile.

La scelta deve essere documentata e riproducibile.

## Fase 4 — tool catalog

Implementare solo tool definiti in `GAIA_DOCS_MCP_TOOLS.md`.

Il server deve restituire evidenze, non una risposta finale generata.

## Fase 5 — chunking

Il chunking deve essere:
- deterministico;
- versionato;
- tracciabile al documento;
- coerente con heading/sezioni quando possibile.

Registrare:
- chunk ID;
- source path;
- heading;
- posizione;
- hash;
- token estimate.

## Fase 6 — separazione dalla Wiki agentica

Non riusare automaticamente il classifier `docs_only/live_data/logic` come router del nuovo agente.

Il Docs MCP deve semplicemente rispondere a chiamate documentali.

## Fase 7 — privacy

Prima dell'indicizzazione verificare che il corpus non contenga:
- credenziali;
- secret;
- dati personali non necessari;
- dump;
- informazioni escluse dalla sperimentazione.

## Definition of Done

- corpus manifest congelabile;
- retrieval riproducibile;
- tool stabili;
- provenance completa;
- metriche;
- test retrieval;
- nessun routing globale;
- nessun accesso Data/NAS/Trasparenza.
