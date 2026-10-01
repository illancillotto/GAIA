# GAIA Docs MCP

## Missione

Esporre all'agente principale una fonte documentale interna controllata, versionata e misurabile.

## Fonte

Corpus derivato principalmente da:
- `docs/`
- `domain-docs/`

Il corpus sperimentale è definito da una policy esplicita e non coincide automaticamente con l'indice della Wiki esistente.

## Nota sul runtime Wiki corrente

L'indicizzatore Wiki esistente include anche `progress/*.md`, codice Python e codice TypeScript/TSX.

Per la tesi il Docs MCP deve usare un corpus separato/filtrato per evitare di confondere documentazione operativa e codice sorgente.

## Documenti

1. `GAIA_DOCS_MCP_PROMPT.md`
2. `GAIA_DOCS_MCP_CORPUS_POLICY.md`
3. `GAIA_DOCS_MCP_TOOLS.md`
4. `GAIA_DOCS_MCP_IMPLEMENTATION_PLAN.md`
5. `GAIA_DOCS_MCP_TEST_PLAN.md`

## Runtime locale implementato (2026-09-30)

Il package `backend/app/modules/wiki/mcps/docs/` espone i quattro tool v1
tramite SDK Python `mcp==2.0.0`, con risultati strutturati e trasporto stdio.
L'handshake stdio dell'SDK negozia `2025-11-25`: la revisione piu recente
disponibile nell'SDK (`2026-07-28`) non e automaticamente quella usata da questo
trasporto. Il test di integrazione verifica la versione effettivamente negoziata.
Nessun endpoint HTTP e aggiunto al backend pubblico.

### Build e avvio

```bash
make mcp-docs-build QUALITY_PYTHON=backend/.venv/bin/python
make mcp-docs-serve QUALITY_PYTHON=backend/.venv/bin/python
make test-mcp-docs QUALITY_PYTHON=backend/.venv/bin/python
```

Installare prima `backend/requirements.txt` nell'ambiente scelto. SQLite deve
disporre di FTS5. Il client MCP locale puo avviare direttamente:

```text
command: /percorso/GAIA/backend/.venv/bin/python
cwd: /percorso/GAIA/backend
args: ["-m", "app.modules.wiki.mcps.docs", "serve", "--corpus", "/percorso/GAIA/runtime-data/mcps/docs/corpus.json"]
```

`config/mcps/docs-manifest.json` congela due fonti operative Catasto/Wiki con hash;
Utenze e Ruolo restano `uncertain` ed esclusi per divergenze dal runtime.
L'audit e il limite del corpus sono descritti in `../RUNTIME_AND_VALIDATION.md`.
Un manifest locale alternativo si passa tramite
`MCP_DOCS_MANIFEST`; la directory di output tramite `MCP_DOCS_OUTPUT`.
Il manifest non autorizza automaticamente file non elencati. Codice, prompt,
progress, archive, output generati e operational Wiki restano esclusi dal builder.
L'inclusione della operational Wiki richiede una futura estensione della policy
con un freeze separato. La revisione dei contenuti e esplicita: non e implementato
un rilevatore automatico di segreti o dati personali.

Il build scrive `corpus_manifest.csv`, `corpus_version.json` e `corpus.json` in
`runtime-data/mcps/docs/`, ignorata da Git. Hash, ordinamento, chunk ID UUIDv5 e
versione del corpus sono deterministici. Il manifest congelato contiene gli hash;
riutilizzarlo fa fallire il build se cambia un documento approvato. Il server
verifica integrita e policy del corpus congelato e legge soltanto lo snapshot.

### Retrieval e limiti

Baseline locale SQLite FTS5 `unicode61`, query OR su al massimo 64 termini,
BM25 con peso 2 per titolo/sezione e 1 per contenuto, spareggio per chunk ID.
Questa baseline evita una nuova dipendenza dal database operativo e non modifica
l'indice Wiki o gli schemi PostgreSQL esistenti. Non e un confronto sperimentale
con PostgreSQL FTS, embedding o hybrid retrieval: quella valutazione resta aperta.
Il chunker conserva gli heading Markdown, ignora gli heading dentro fence e
divide le sezioni a 2000 caratteri, senza overlap. Il manifest ammette al massimo
200 entry; ciascun documento ha un budget di 1 MB, il corpus sorgente 10 MB.

`search_docs` ammette query fino a 2000 caratteri e limit 1–10; `get_doc_section`
restituisce un singolo chunk con `max_chars` 1–6000; i metadati restituiscono al
massimo 100 sezioni e indicano il troncamento. Nessun parametro SQL o scope e
esposto al modello. La stima token e `ceil(caratteri / 4)`; la stima della busta
copre il JSON serializzato prima di aggiungere il campo `estimated_tokens`.

L'autorizzazione stdio dipende dal principal locale che avvia il processo e dai
permessi sullo snapshot. `docs.read` nella telemetria descrive la capability
locale. HTTP interno verifica il bearer e `docs.read`; avvio e mapping in
`../RUNTIME_AND_VALIDATION.md`. Il gateway Wiki con `gpt-reserve` esclude Docs
lato server: nessuna discovery, connessione o invocazione Docs entra nell'agente
esterno. Questo adapter resta disponibile per client interni autorizzati.
La telemetria JSON su stderr registra request ID, tool, durata, conteggi,
troncamento, versione e stato senza query o evidenze. Identificativi di
conversazione/esperimento e principal pseudonimizzato sono propagati dal
contesto autenticato dell'agente.

### Verifiche Docs e stato storico della prima tranche

Test di corpus, chunking, path traversal, symlink, integrita, filtri, hard cap,
provenance, minimizzazione dei log, discovery e handshake stdio reale.
Coverage statement e branch del package runtime: 100%.
Quality ratchet contro `origin/main`, merge-base `6b61fd27`: nessun finding.
Metriche della prima tranche Docs: prima nessun file runtime MCP; dopo 7 file,
26 callable, nessuna violation
error-level e 10 warning. Baseline ed eccezioni restano invariate. Il gate Ruff
e formatter passa su tutti gli 8 file Python aggiunti. Nel checkout locale
`compileall` richiede `PYTHONPYCACHEPREFIX=/tmp/gaia-mcp-pycache` per evitare una
cache bytecode preesistente non scrivibile; nessuna cache del progetto e rimossa.
Oltre ai test sintetici, 32 query curate verificano il corpus reale congelato:
Recall@10 1.0, MRR 0.9833, precisione@10 0.1393. Report riproducibile con
`make mcp-evaluate`; confronto con retrieval semantico/ibrido resta facoltativo.
Le verifiche finali dell'intero modulo sono in `../RUNTIME_AND_VALIDATION.md`.
