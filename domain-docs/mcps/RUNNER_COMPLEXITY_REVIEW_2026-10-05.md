# MCP — riduzione della complessita del runner sintetico

## Perimetro e comportamento

Prima slice, richiesta dopo il gateway HTTP/HTTPS: il massimo cognitivo MCP
corrente era `experiment_runner.py::run_comparison`. Gli altri refactoring MCP
e i lavori concorrenti del checkout non fanno parte di questa tranche.
La richiesta successiva sui warning legacy autorizza una slice distinta sul
costruttore del journal, descritta sotto. Una terza richiesta autorizza infine
la modifica dell'API Python interna, descritta nella sezione dedicata.

`run_comparison` mantiene manifest, schedule seeded e lifecycle del journal.
`ComparisonExecutor.execute_item` possiede skip completed, ripresa dei tentativi,
contesto per item e persistenza dei risultati. Il journal conserva il manifest
validato, fonte autorevole dell'identita esperimento. Restano invariati ordine,
budget, retry, scoring, append/flush/fsync prima dei record in memoria e close
in finally, anche su cancellazione o errore di scrittura. Nessun cambio a HTTP,
HTTPS, OAuth, API HTTP, DB o autorizzazioni.

Il manifest include l'hash del runner: i journal del codice precedente vengono
intenzionalmente rifiutati. Usare un nuovo output e preservare gli storici;
nessuna migrazione o riscrittura dei risultati.

## Metriche prima/dopo della prima slice

Motore corrente, snapshot iniziale HEAD `6997dbab`, baseline autorevole del
merge-base `6b61fd27` rispetto a `origin/main`.

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| `run_comparison` cognitive/cyclomatic/LOC/nesting | 21/9/34/4 | 4/4/11/2 |
| `execute_item` cognitive/cyclomatic/LOC/nesting | assente | 7/6/19/2 |
| File cognitive sum/max | 81/21 | 71/18 |
| File cyclomatic sum/max | 63/10 | 64/10 |
| Decisioni (somma cyclomatic meno base callable) | 48 | 48 |
| File LOC effettive | 210 | 207 |
| Callable | 15 | 16 |
| Warning / error | 5 / 0 | 3 / 0 |

Esito `IMPROVED`: diminuiscono cognitive e nesting senza trasferire violation.
Non diminuiscono le decisioni: +1 cyclomatic aggregata e la base del nuovo
callable, non nuovo branching. I tre warning residui sono cognitive 18 e
cyclomatic 10 del costruttore journal, piu sei parametri della firma pubblica
`run_comparison`. Questo era lo stato alla chiusura della prima slice.

## Verifiche della prima slice

- Baseline pre-change: 28 test experiment, runner 139 statement / 30 branch,
  tutti coperti. Tre nuovi casi pertinenti verdi anche prima del refactoring:
  resume parziale con item completato, contesto/UUID stabile e tentativi isolati;
  cancellazione e failure di scrittura con rilascio reale del lock.
- Suite experiment finale: 31 test verdi; runner 142/142 statement e 30/30
  branch, coverage 100%, nessuna parte del runtime modificato scoperta.
- Suite `make test-mcp QUALITY_PYTHON=backend/.venv/bin/python`: 298 test verdi,
  coverage statement e branch MCP/router 100%, incluse regressioni del gateway.
- Ruff check e Ruff format check sui due Python modificati: PASS.
  `git diff --check` del perimetro: PASS.
- Ratchet mirato: PASS, `findings: []`, baseline del merge-base; scan completo
  prima del filtro target, policy scope e motori verificati. Nessuna modifica
  della baseline, delle esclusioni, delle soglie o dei report versionati.

Per evitare collisioni con pytest concorrenti la riverifica usa un
`COVERAGE_FILE` dedicato. La prima prova post-change, con file condiviso e
formattazione mentre il processo era attivo, non e evidenza valida; e stata
sostituita dalla misura isolata completa.

Evidenze locali (non versionate): `/tmp/gaia-mcp-runner-final-tests.log`,
`/tmp/gaia-mcp-runner-final-coverage.json`,
`/tmp/gaia-runner-mcp-suite-final.log`, `/tmp/gaia-runner-ratchet-scoped.json`,
`/tmp/gaia-runner-ratchet-global.log`, `/tmp/gaia-runner-lint-global.log`.

## Slice successiva — warning journal

Su richiesta esplicita successiva, separati lifecycle e lettura/validazione:
`ResultJournal.__init__` resta proprietario del lock e del cleanup,
`_read_rows` verifica newline, JSON e manifest senza scrivere. Precedenza
degli errori, conservazione byte, append/fsync e API restano invariati.

| Metrica | Prima della slice journal | Dopo |
| --- | ---: | ---: |
| Costruttore cognitive/cyclomatic/LOC/nesting | 18/10/19/2 | 5/4/13/2 |
| `_read_rows` cognitive/cyclomatic/LOC/nesting | assente | 8/7/9/1 |
| File cognitive sum/max | 71/18 | 66/8 |
| File cyclomatic sum/max | 64/10 | 65/7 |
| Decisioni aggregate | 48 | 48 |
| File LOC | 207 | 210 |
| Warning / error | 3 / 0 | 1 / 0 |

`IMPROVED`: entrambi i warning del costruttore eliminati, metodo sotto soglia,
cognitive aggregata ridotta senza trasferire debito. La crescita cyclomatic
e ancora solo la base del nuovo callable, non nuove decisioni.

Cinque nuovi casi pertinenti passano prima e dopo: file incompleto, priorita
incomplete sul JSON invalido, JSON invalido con newline, manifest diverso,
errore della prima scrittura. Verificano contenuto preservato, file chiuso
e lock realmente riacquisibile. Suite experiment: 36 test verdi, runtime
145/145 statement e 30/30 branch, coverage 100%; Ruff e format check verdi.
Suite MCP finale: 303 test verdi, 1996 statement e 420 branch al 100% sui
42 runtime MCP/router. Ratchet mirato da scan completo: PASS con
`findings: []`, merge-base `6b61fd27`; gate globali ancora 24 finding estranei
e i due formatter Presenze. Baseline, esclusioni e soglie invariati.
Evidenze `/tmp/gaia-journal-{before,after}.json`,
`/tmp/gaia-journal-{before,after}-tests.log`,
`/tmp/gaia-journal-after-coverage.json`.
Log finali `/tmp/gaia-journal-mcp-suite.log`,
`/tmp/gaia-journal-ratchet-scoped.json`, `/tmp/gaia-journal-ratchet-global.json`,
`/tmp/gaia-journal-lint.log`. Graphify aggiornato nuovamente dopo questa slice
tramite i medesimi target; log `/tmp/gaia-journal-graphify-{code,platform,domain}.log`.

Alla chiusura della slice journal restava il warning dei sei parametri di
`run_comparison`: non aggirato con variadic, wrapper o esclusioni. La successiva
autorizzazione dell'utente consente la slice API interna descritta sotto.

## Slice autorizzata — API Python interna

Nuovo contratto: `run_comparison(cases, executor, output)`, dove l'executor
e il `ComparisonExecutor` gia esistente, configurato con fonti, modello,
corpus e budget. Il runner usa i suoi corpus/config per manifest e schedule;
la CLI crea l'executor dentro il context manager del modello. Nessun wrapper
nuovo, nessuna duplicazione di stato e nessun alias della vecchia firma.
I chiamanti Python devono creare l'executor prima della chiamata; la firma a
sei argomenti viene intenzionalmente rimossa con autorizzazione esplicita.
CLI, HTTP, retry/resume, formato journal, scoring e ownership risorse invariati.

Parametri `run_comparison` 6 -> 3: warning del runner 1 -> 0, zero violation
anche nella CLI modificata. Cognitive/cyclomatic e callable dei due file
invariati: runner 66/65, CLI 8/6, 19 callable complessivi. Esito `IMPROVED`
limitato alla firma/debito dei parametri, non alla complessita decisionale.
LOC effettive runner 210 -> 211 e CLI 52 -> 59, inclusi firma tipizzata e
import esplicito; nessuna soglia file superata o debito trasferito.

Caratterizzazione cleanup CLI su failure del runner verde prima del cambio;
test di wiring aggiornato per verificare l'identita di tutte le dipendenze
nell'executor passato al runner. Tutti i test resume/retry/abort restano.
Suite experiment finale: 37 test verdi; runner 144/144 statement e 30/30
branch, CLI 37/37 statement e 4/4 branch, coverage 100% su entrambi i file.
Suite MCP completa: 304 test verdi, 1996 statement e 420 branch al 100% sui
42 runtime MCP/router. Ruff/check-format/diff-check e ratchet sui due file
PASS, `findings: []`, full scan contro merge-base `6b61fd27`. Nessuna parte
del runtime modificato scoperta e nessuna regressione MCP rilevata.

Evidenze `/tmp/gaia-api-{before,after}.json`,
`/tmp/gaia-mcp-api-{before,final}-tests.log`,
`/tmp/gaia-mcp-api-final-coverage.json`, `/tmp/gaia-api-mcp-suite.log`,
`/tmp/gaia-api-ratchet-scoped.json`, `/tmp/gaia-api-ratchet-global.json`,
`/tmp/gaia-api-lint.log`. Gate globali ancora 24 finding estranei e due
formatter Presenze; baseline invariata, nessun commit/push.

Graphify aggiornato nuovamente tramite target dedicati. AST Wiki forzato dopo
la patch pruning per rimuovere le vecchie relazioni della costruzione executor
nel runner; ora la costruzione appartiene alla CLI. Log
`/tmp/gaia-api-graphify-{code,platform,domain}.log`.
Poiche il refresh incrementale conservava alcuni edge verso simboli ancora
esistenti, il grafo codice e stato ricostruito dal medesimo corpus Wiki con il
target dedicato, dopo backup in `/tmp/gaia-api-wiki-graph-before-rebuild.json`.
Verificati `live -> ComparisonExecutor`, `live -> run_comparison` e l'assenza
dei vecchi edge di costruzione/retry nel runner. Risultato finale: 987 nodi,
2333 archi; log `/tmp/gaia-api-graphify-code-rebuild.log`. Nessuna modifica
ai grafi docs o al runtime durante questa rigenerazione.

## Limiti e gate globali

Il ratchet globale conserva 24 finding estranei al runner: GIS, Presenze,
application user, Capacitas, frontend utenti/Organigramma/API core e SISTER.
Il lint globale fallisce per formattazione dei due runtime Presenze
`daily_details.py` e `shift_assignments.py`. Queste modifiche concorrenti sono
preservate: nessuna failure o regressione MCP rilevata dai controlli eseguiti,
ma i gate dell'intero repository non sono dichiarati superati.

La baseline globale non viene sincronizzata in questo checkout concorrente.
Alle verifiche sopra il commit era sospeso per i gate globali non superati.
L'utente ha successivamente richiesto il commit isolato delle nostre modifiche:
solo runner, CLI, test e documentazione delle tre slice; nessun altro refactoring
MCP, manifest freeze o lavoro concorrente incluso. I documenti code-quality
condivisi sono staged per le sole sezioni del runner. Nessun push e nessuna
dichiarazione di superamento dei gate globali.
Snapshot isolato dell'index verificato prima del commit: 37 test experiment
verdi, coverage statement/branch 100% su runner e CLI, Ruff verde. La prova
non dipende dai refactoring concorrenti rimasti fuori dallo staging.

## Graphify

Aggiornati tramite `make graphify-wiki-code`, `make graphify-platform-docs`
e `make graphify-docs`. La query Wiki verifica gli edge estratti
`ComparisonExecutor -> execute_item` e `run_comparison -> execute_item`.
Entrambi i batch semantici docs terminano con `chunk 1/1 done`, senza warning
di chunk falliti. Il refresh conclusivo aggregato forza `gpt-reserve` dopo il
caricamento di `.env.graphify`, che contiene un override locale legacy; la
configurazione locale non viene modificata. Evidenze in
`/tmp/gaia-runner-graphify-{code-final,platform,domain-final,query}.log`.
Gli artifact `graphify-out/` restano ignorati e non sono versionati.
