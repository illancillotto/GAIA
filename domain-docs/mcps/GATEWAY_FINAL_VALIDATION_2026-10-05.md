# Verifica finale gateway MCP HTTP/HTTPS — 2026-10-05

## Perimetro e stato

Override Compose TLS opzionale, routing Nginx condiviso, redirect HTTP `308`
verso l'origin HTTPS configurato, headers/maintenance del connector e suite
Docker persistente. Nessun runtime Python, TypeScript o worker modificato;
nessun cambio a OAuth, dataset, manifest congelato, baseline o soglie.
Nessun deploy, certificato permanente, apertura pubblica o prova client cloud.

La verifica isolata parte da `c75fe0a2` e contiene esclusivamente la patch
gateway. Il checkout principale contiene lavori concorrenti di altri domini:
non fanno parte di questa change e non devono entrare nel relativo commit.
Durante la verifica HEAD principale e avanzato con quei lavori.

## Gate del perimetro

| Verifica | Risultato |
| --- | --- |
| `make test-mcp-gateway QUALITY_PYTHON=backend/.venv/bin/python` | 66 passed, zero skip; stesso risultato nello snapshot isolato |
| `make test-mcp-connector QUALITY_PYTHON=backend/.venv/bin/python` | 27 passed; quattro runtime: 334/334 statement, 96/96 branch, 100% |
| `make test-mcp-oauth QUALITY_PYTHON=backend/.venv/bin/python` | 18 passed; quattro runtime: 274/274 statement, 86/86 branch, 100% |
| `make test-mcp-consent` | 23 passed; 67/67 statement, 34/34 branch, 14/14 funzioni, 63/63 linee, 100% |
| `make test-mcp QUALITY_PYTHON=backend/.venv/bin/python` nel checkout corrente | 295 passed; 42 runtime: 1990/1990 statement, 420/420 branch, 100% |
| Ruff sul nuovo file test | `check` e `format --check` PASS |
| `make lint-backend BASE_REF=HEAD` nello snapshot isolato | compilazione PASS; zero sorgenti Python cambiate nel perimetro di stile |
| `make quality-test` nello snapshot isolato | 169 passed, con `NODE_PATH` alle dipendenze frontend locali |
| Routing applicativo condiviso | contenuto identico al corpo del precedente server HTTP, salvo rimozione dell'indentazione |
| Compose reale e `nginx -T` | PASS nel test dell'entry point, variabili Nginx preservate dopo envsubst |
| `git diff --check` | PASS |

La matrice completa dei comportamenti e in `HTTP_HTTPS_GATEWAY.md`.
I test gateway usano Nginx e TLS reali, con upstream HTTP di echo; i test
OAuth/connector esercitano il runtime applicativo reale su dati sintetici.
Le due misure sono complementari: non dichiarano una prova client cloud.
La coverage Python/V8 riguarda i sorgenti runtime misurati, non il codice dei
test. Nginx e Compose hanno copertura funzionale della matrice; non viene
attribuita loro una percentuale statement/branch Python inesistente.

## Complessita e controlli globali

Il ratchet autorevole e stato eseguito sul corpus completo nello snapshot
isolato prima e dopo la patch, usando la baseline del merge-base di
`origin/main` (`6b61fd27`). Entrambe le esecuzioni producono gli stessi
25 finding, confrontati come JSON: zero finding aggiunti o modificati dalla
patch. Il delta delle metriche del runtime Python/TypeScript/worker e zero,
perche quei sorgenti non cambiano. Non e stato aggiornato alcun baseline.
Questo dimostra non-regressione della change, non un gate globale verde.

Nel checkout principale `make lint-backend` contro `origin/main` segnala
formattazione di `daily_details.py` e `shift_assignments.py` (Presenze),
fuori dalla patch. Il ratchet globale include inoltre i lavori concorrenti;
nessuna correzione, esclusione o assorbimento in baseline e effettuato qui.

## Suite completa MCP e residui

`make test-mcp` nello snapshot isolato: **250 passed, 2 failed**, coverage
99,05% (17 statement non eseguiti in `evaluation.py`, dopo i fallimenti).
Entrambi i fallimenti sono riprodotti anche su `c75fe0a2` senza la patch:

- `test_frozen_repository_corpus_and_32_reviewed_queries`;
- `test_evaluation_cli_and_entrypoint[docs]`.

La causa e il manifest versionato Docs: SHA256 di
`domain-docs/wiki/docs/PRD_wiki.md` non piu corrispondente alla fonte su HEAD
(`Reviewed document hash has changed`). Nessun documento cambiato dal gateway
introduce una nuova discrepanza. Il checkout principale contiene gia un
aggiornamento del manifest e il relativo report di review, appartenenti al
lavoro Wiki concorrente; non vengono incorporati o modificati in questa change.
La riverifica del checkout principale, che comprende la correzione Wiki e
gli altri lavori concorrenti, supera invece `make test-mcp`: 295 test,
1990/1990 statement e 420/420 branch su 42 runtime (100%). Non e una prova
della sola patch gateway su HEAD pulito: il fix del manifest resta separato
e non entra nel commit gateway. Nessuna soglia e stata abbassata.

Residui esterni al gateway: chiusura/versionamento della review freeze Wiki,
rilievi globali di stile/complessita e obiettivo coverage repository-wide.
Residui operativi: certificati e hostname reali, client/callback approvati,
configurazione e attivazione esplicita, prova end-to-end dal client previsto.
Questi limiti sono distinti dalla correttezza locale del gateway verificato.

## Graphify

Il refresh codice e passato tramite `graphify-refresh-core-code`,
`graphify-backend`, `graphify-frontend` e `graphify-elaborazioni-worker-code`.
`graphify-platform-docs` e `graphify-docs` hanno entrambi completato
`chunk 1/1 done`, senza warning di fallimento semantico. Dopo la registrazione
degli esiti e eseguito anche il refresh incrementale finale della documentazione
aggregata. I grafi generati restano ignorati e non entrano nel commit.
