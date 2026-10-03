# Discovery MCP Data filtrata lato server

La discovery del server Data ora risolve il contesto autenticato a ogni
richiesta e include soltanto i tool il cui scope e presente nel contesto.
Non dipende dal prompt o dal filtro aggiuntivo WikiMCPClient. Nessun caching
di scope fra principal: senza scope, o con il solo docs.read, il catalogo
Data e vuoto. Contesto mancante: errore fail-closed, mai catalogo completo.

Il catalogo completo conserva 12 tool per i tre scope Data; utenze.read
da solo espone get_subject e search_subjects. L'autorizzazione di ogni
invocazione resta nel servizio: conoscere o inventare il nome di un tool
nascosto non consente di chiamarlo. Docs rimane separato e non viene montato
quando si usa Data-only. Chat Wiki legacy, budget e provenance invariati.

## Test e coverage

```bash
make test-mcp-discovery QUALITY_PYTHON=backend/.venv/bin/python
```

Il target verifica tutti i singoli scope, scope vuoti/Docs-only, catalogo
completo, cambio contesto fra richieste e contesto assente. Verifica chiamate
consentite, negate e Docs non eseguibile; i vecchi test HTTP/stdio sono
aggiornati al catalogo ristretto invece di aspettarsi sempre 12 tool.

La prova HTTP usa il vero stack ASGI e il protocollo JSON-RPC/MCP con JWT:
richieste concorrenti con scope diversi, successiva richiesta ristretta,
401 senza bearer, 404 su Docs e chiamata Ruolo negata. Usa trasporto ASGI
in-process, non socket TCP o TestClient cross-thread; funziona nel sandbox
senza aggirare restrizioni di rete. Non e un test del connettore Claude live.
Il lifecycle stdio e simulato; handshake stdio reale resta da rieseguire.

Il target completo make test-mcp include la nuova suite e conserva il gate
100% sul perimetro MCP/router. Il target mirato e aggiuntivo e non sostituisce
quel gate. Coverage del runtime modificato data/server.py: 24/24 statement,
100%; il reporter Python 3.12 non conta branch per la comprehension, quindi
gli esiti del filtro sono verificati esplicitamente dalla matrice dei test.

Risultati: target mirato 11 PASS; regressioni locali Docs/Data/evaluation/
experiment/discovery 160 PASS, 4 test di SDK/stdio/socket deselezionati per
il limite del sandbox gia diagnosticato. Non equivale al gate completo.
Ruff check e format dei quattro file Python toccati PASS, ratchet mirato
PASS, Graphify Wiki tramite Make PASS. Lint globale resta bloccato dall'I001
preesistente in test_presenze_operations_postgres.py: non corretto qui.
Anche il ratchet globale fallisce su regressioni estranee gia presenti,
inclusa elaborazioni_capacitas_incass.py; il ratchet della slice server
passa. Non si dichiarano verdi i gate globali e non si modifica la baseline.
Log `/tmp/gaia-mcp-discovery-*`. Nessuna baseline modificata e nessuna
estrazione Graphify docs verso provider esterni.

## Metriche e stato produzione

Ratchet ordinario, baseline del merge-base origin/main invariata.
create_server: LOC 28→30, cognitiva 3 e ciclomatica 4 invariate;
list_tools: LOC 17→19, cognitiva 1 e ciclomatica 2 invariate.
Nessun refactoring o trasferimento di debito. Nessun warning/violazione nuovo.

Questo chiude il gap del catalogo grezzo registrato nella valutazione
VALIDATION_2026-10-02.md, che resta evidenza storica prima del fix.
Non rende ancora il listener pubblicabile: OAuth, ingress HTTPS pubblico,
allowlist host/origin e limiti per principal sono passi distinti ancora
necessari per Claude remoto. La nuova CA interna resta da concordare col CED.
Nessun live provider, dato reale, Ollama, deploy, commit o push in questa tranche.
