# GAIA Docs MCP — piano di test

## Corpus test

Verificare:
- file esclusi davvero esclusi;
- archive esclusi;
- prompt di sviluppo esclusi;
- codice sorgente escluso;
- nessun `.env`;
- nessun secret;
- nessun path fuori root consentita.

## Chunking test

- heading preservato;
- chunk non vuoto;
- dimensione massima;
- overlap deterministico se usato;
- chunk ID stabile;
- provenance corretta.

## Retrieval test

Costruire 30–50 query con documenti target noti.

Metriche:
- Recall@k;
- MRR;
- precisione top-k;
- nDCG se utile;
- token recuperati;
- latenza.

Categorie:
- definizioni;
- procedure;
- workflow;
- moduli;
- domande con lessico diverso dal documento;
- ambigue;
- no-answer.

## Regression test

Ogni modifica a chunking, tokenizer, FTS, embedding, reranking o corpus policy deve produrre un report comparativo.

## Security test

- path traversal;
- resource URI non valida;
- documento escluso richiesto direttamente;
- query contenente prompt injection;
- tentativo di richiedere secret;
- payload eccessivo.

## MCP contract test

Verificare:
- tool discovery;
- schema;
- error handling;
- hard cap;
- provenance;
- corpus version.

## Thesis separation test

Assicurarsi che il Docs MCP:
- non interroghi il Data MCP;
- non interroghi NAS;
- non interroghi Trasparenza;
- non produca direttamente la risposta finale dell'agente.
