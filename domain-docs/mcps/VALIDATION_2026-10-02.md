# MCP — ulteriori valutazioni sintetiche

Data: 2026-10-02. Questa tranche aggiunge verifiche e un report, non modifica
runtime, autenticazione, budget, scorer o gate. Working tree concorrente,
Docs separato e chat Wiki legacy preservati. Nessun commit, push o deploy.

## Esiti nuovi

| Verifica | Esito | Natura della prova |
| --- | --- | --- |
| Query Data con ground truth | 30/30, success_rate 1.0 | SQLite e servizi reali, senza modello |
| Test MCP locali | 149 PASS, 5 deselezionati nel sottoinsieme | Servizi/oracle reali, risposte modello simulate dove previste |
| Regressioni indexer/RAG Wiki | 47 PASS | Solo due suite; non la regressione HTTP completa |
| Preview e console frontend | 7 PASS, 100% statement/branch/function/line sui tre file | API simulate, non browser live |
| Ruff MCP | PASS | Perimetro runtime MCP e test experiment/console |
| Ratchet mirato MCP/router | PASS, findings vuoti | Baseline merge-base origin/main, invariata |
| Graphify Wiki codice | PASS | AST locale; nessun documento inviato a modelli esterni |
| Suite Make completa e HTTP/SDK | NON CONCLUSA | Blocco sandbox sulle comunicazioni socket |
| Nuovo pilot gpt-reserve | NON ESEGUITO CON SUCCESSO | Probe sincrono APIConnectionError; nessuna chat live conclusa |

Query offline: `config/mcps/data-queries.json`, seed `gaia-v1`, SQLite
isolata `runtime-data/mcps/evaluation/20261002-validation/gaia-mcp-synthetic-v1.sqlite`.
Dataset verificato: `b4e0ea2f82a4a79dbf6601a630edb5ebe9636e62592e8a8020b55f3bd24afff1`.
Latenza locale su 30 query: p50 0.207 ms, p95 0.464 ms, p99 0.474 ms.
Sono tempi dei servizi SQLite, NON latenza dell'agente, HTTP o modello,
e non costituiscono un benchmark di produzione o SLA.

Gli esiti live precedenti (incluso 14/15 MCP strict e l'errore reale di
citazione nella paginazione) restano storici, non diventano risultati nuovi.
Non si conclude che il modello abbia corretto quell'errore.

## Limite riprodotto del sandbox

La suite completa si blocca nel contratto SDK Docs, prima di concludere
coverage; TestClient si blocca nell'avvio del portal AnyIO e il probe async
del provider resta in attesa. Diagnosi minimale indipendente da GAIA:
`socket.socketpair()` riesce, ma `send(b'x')` fallisce con
`PermissionError: [Errno 1] Operation not permitted`. Questo impedisce anche
il wake-up cross-thread di asyncio. Non e una failure applicativa dimostrata.

Il probe provider sincrono usa URL e chiave gia presenti in `.env.graphify`,
letti solo in memoria e mai stampati: `APIConnectionError`, senza HTTP status.
Questo non dimostra un guasto codex-lb: l'ambiente ha accesso rete ristretto.
Nessun provider alternativo, Ollama, URL o credenziale inventati.

Sono stati interrotti i tentativi bloccati; i successivi hanno timeout esplicito.
Il gate `make test-mcp` resta invariato e NON e dichiarato superato oggi.
La coverage backend storica al 100% non sostituisce una nuova esecuzione completa.

Comando diagnostico del sottoinsieme locale:

```bash
backend/.venv/bin/python -m pytest backend/tests/test_wiki_docs_mcp.py backend/tests/test_wiki_data_mcp.py backend/tests/test_wiki_mcp_evaluation.py backend/tests/test_wiki_mcp_experiment.py -k 'not sdk and not stdio'
```

Cinque test deselezionati: contratto SDK Docs, handshake stdio Docs,
handler/runner SDK Data, handshake stdio Data e confronto HTTP/SDK reale.
Le suite HTTP, integrazione e console backend non sono incluse in questo
sottoinsieme. Questo comando diagnostico non sostituisce il gate completo.

## Finding per il connettore remoto

Probe diretto del vero handler SDK Data, usando principal sintetico con il
solo scope `utenze.read`:

- catalogo grezzo: 12 tool; 10 richiedono scope non presenti;
- chiamata diretta al servizio Ruolo: `PERMISSION_DENIED`;
- app creata Data-only: nessuna route Docs registrata;
- nessun dato non autorizzato restituito e nessuna chiamata al modello.

Il probe usa handler/servizi reali, NON richieste HTTP: il test end-to-end
del medesimo scenario resta da eseguire in un ambiente abilitato.
Artefatto: `runtime-data/mcps/evaluation/20261002-validation/data-only-direct-surface.json`.

Il gateway Wiki filtra gia il catalogo tramite WikiMCPClient prima del
modello; il finding riguarda il server grezzo che un client remoto potrebbe
interrogare direttamente. Non rendere pubblico quel listener cosi com'e.
Prima del rilascio Claude occorrono discovery filtrata lato server per scope,
OAuth, limiti per principal e gateway pubblico Data-only, senza console/Docs.
Il piano produzione gia registra questi gap: questa prova li conferma,
non introduce automaticamente modifiche funzionali al protocollo.

## Evidenze e prossimo passo

Artefatti nuovi separati dai journal storici in
`runtime-data/mcps/evaluation/20261002-validation/`; nessun resume o
sovrascrittura dei pilot precedenti, nessun retry per migliorare lo scoring.
Log minimizzati in `/tmp/gaia-mcp-next-*`; le credenziali non sono versionate.

Prossima priorita: discovery server-side per il futuro endpoint remoto con
test scope/Docs, poi autenticazione OAuth e budget per principal. Rilanciare
il gate completo e un nuovo pilot gpt-reserve con casi multi-hop/paginazione
in ambiente con IPC/rete consentiti. La nuova CA interna, ancora da creare
con il CED, non risolve l'ingresso pubblico del connettore Claude.
