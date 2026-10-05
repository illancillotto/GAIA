# GAIA MCP — runtime, avvio e validazione

Chiusura corrente: `FINAL_CLOSURE_2026-10-03.md`. Coverage MCP completo100%,
build pulita locale e standalone/E2E preview passati. Gate complessivo ancora
FAIL per ratchet globale e verifiche di rilascio mancanti. Note seguenti storiche.

Riverifica dopo lo sblocco sandbox: `RECHECK_2026-10-03.md`. Suite MCP completa,
build isolata, E2E preview e gpt-reserve live con soli sintetici passati;
proxy di test HTTPS validato, non il dominio pubblico/Claude. Ratchet globale
ancora rosso, build in-place bloccata dai permessi. Nessuna attivazione.

Stato corrente 2026-10-03: fondazione OAuth, consenso GAIA e listener remoto
Data-only implementati ma disattivati. Contratto:
`CONNECTOR_RUNTIME_2026-10-03.md`; verifica finale e matrice test:
`CONNECTOR_FINAL_REVIEW_2026-10-03.md`. Gate complessivo FAIL; i risultati
precedenti sotto sono evidenze storiche, non attestazioni del checkout attuale.

Riverifica locale 2026-10-03 durante la preparazione dei commit: il manifest
Docs e stato riallineato al PRD Wiki del commit `1995a1fc`, dopo revisione
dell'aggiunta sul connettore sintetico. Il controllo hash rimane fail-closed.
`COVERAGE_FILE=/tmp/gaia-review-mcp-isolated.coverage make test-mcp
QUALITY_PYTHON=backend/.venv/bin/python` passa: 245 test, 1984/1984 statement
e 424/424 branch, 100% dei 42 runtime misurati. Il file coverage isolato evita
interferenze con le altre sessioni sul checkout. Il risultato chiude la suite
MCP locale, non i gate globali di complessita, il collaudo HTTPS o Claude live.

Catalogo semantico per LLM: `DATA_TOOL_CATALOG.md`. Tutti i 12 tool hanno
descrizioni complete; initialize espone istruzioni sintetiche, copertura,
paginazione e provenance. Distretti/domande non sono tool dedicati:
la console completa non equivale alla copertura completa del modello.

Hardening successivo: `SERVER_SCOPE_DISCOVERY_2026-10-02.md`. Discovery Data
filtrata lato server per scope, non solo nel gateway; test HTTP/ASGI con JWT
e scope concorrenti senza socket. OAuth/ingresso remoto restano da completare.

Valutazioni aggiuntive 2026-10-02: `VALIDATION_2026-10-02.md`.
30/30 query sintetiche, test locali e frontend passati; suite completa/live
bloccati dal sandbox. Confermato il gap di scope nella discovery del server
grezzo, da risolvere prima di esporlo al connettore remoto Claude.

Piano corrente di produzione e audit HTTPS Kiosk (2026-10-02):
`PRODUCTION_CONNECTOR_PLAN.md`. Il rilascio richiesto ora e il connettore
remoto Claude, distinto dalle prove locali/stdio documentate sotto.

Console dati/richieste/log e collegamento locale Claude:
`CONSOLE_AND_LOCAL_CLIENTS.md`. ChatGPT rimandato su scelta dell'utente.

## Riverifica del percorso gpt-reserve Data-only (2026-10-01)

Il recupero dal checkpoint conferma che il percorso richiesto e gia presente
nel commit `4a9af231`: non occorre ripetere l'implementazione. Configurazione,
gateway e test escludono Docs da discovery e invocazioni prima del trasporto;
le evidenze documentali spurie ricevute dal trasporto Data sono respinte prima
dei messaggi al modello. Server Docs separato e chat Wiki legacy preservati.

Riverifica corrente: `make test-mcp QUALITY_PYTHON=backend/.venv/bin/python`
passa con 193 test, 1351/1351 statement e 252/252 branch coperti (100%). Le
sei suite Wiki di regressione passano con 122 test. Ruff check/format MCP,
Compose `config --quiet` e `make graphify-wiki-code GRAPHIFY_CODE_FLAGS=--force`
passano. Graphify codice usa solo AST; nessun corpus docs e inviato al provider.

Prova live ripetuta con `/tmp/gaia-mcp-live.py`: credenziali esistenti di
`.env.graphify` lette in memoria, provider raggiungibile e `gpt-reserve`
disponibile. Agente e trasporto HTTP reali su DB e fixture Docs temporanei
interamente sintetici: una chiamata Data, due provenance, 283 token stimati
di evidenze e zero richieste Docs. Questa prova usa il modello reale; i test
unitari di orchestrazione usano invece risposte simulate. Log minimizzato:
`/tmp/gaia-mcp-recheck-live.log`. Nessun Ollama, documento reale o deploy.

I gate globali `make lint-backend` e `make complexity-ratchet` sono eseguiti
ma falliscono su modifiche estranee gia presenti nel checkout: stile in
Elaborazioni, test Presenze e read model Ruolo; complessita in Presenze,
Ruolo, gestione utenti ed Elaborazioni. Nessun finding del ratchet riguarda
MCP. Log: `/tmp/gaia-mcp-recheck-lint.log` e
`/tmp/gaia-mcp-recheck-ratchet.log`. Questi file estranei e la baseline sono
preservati; i gate globali non sono dichiarati superati.

Il ratchet mirato `backend/.venv/bin/python tools/code_quality/complexity.py
ratchet --base-ref origin/main backend/app/modules/wiki/mcps
backend/app/modules/wiki/router.py` passa con `findings: []`, usando la
baseline del merge-base `6b61fd27`. Log:
`/tmp/gaia-mcp-recheck-ratchet-scoped.log`. Nessuna modifica runtime durante
questa riverifica: metriche prima/dopo invariate.

Verifica successiva al commit: `POST_COMMIT_VALIDATION_2026-10-01.md`.
Include il nuovo scorer di assenza multi-hop, 193 test MCP, pilot diagnostico
ampliato e browser con login/provider reali. I risultati precedenti sotto sono
storici: non sostituiscono lo stato corrente dei gate globali.

## Confronto sintetico riproducibile e preview

Correzione multi-hop codice avviso: `MULTIHOP_NOTICE_CODE_REVIEW.md`.
`search_role_notices` supporta il filtro esatto opzionale `notice_code`, distinto
da `account_code`; l'UUID restituito alimenta `get_payments_by_notice`.
I manifest nuovi includono hash del catalogo/query/server Data: non riprendere
i journal precedenti dopo la modifica, usare un nuovo percorso di output.

`make mcp-comparison-plan QUALITY_PYTHON=backend/.venv/bin/python` genera solo
il piano locale, senza contattare il provider o scrivere il journal. Richiede
la SQLite sintetica verificata indicata da `MCP_DATA_DATABASE`.
`make mcp-comparison-live QUALITY_PYTHON=backend/.venv/bin/python` attiva
esplicitamente il modello: configurare il provider/signing gia descritti qui
e il server Data HTTP sullo stesso dataset. Dataset diverso o tool non Data
sono rifiutati prima di inviare evidenze al modello. Nessun parametro Docs.
Risultati ignorati da Git: `runtime-data/mcps/evaluation/comparison.jsonl`.
Eseguire lo stesso comando per resume; per un protocollo/dataset/budget diverso
usare un nuovo output, senza sovrascrivere il journal precedente. Opzioni CLI:
`--repeats`, `--seed`, `--database`, `--output`, `--live`.

Preview autenticata: `/wiki/mcp`, solo domande sintetiche predefinite, chiamata
`POST /wiki/mcp/chat` tramite client API GAIA. Nessuna credenziale provider nel
browser; nessun input libero/documento/allegato; chat legacy invariata.
Piano, matrice e limiti: `SYNTHETIC_RECOVERY_PLAN.md`; risultati realmente
misurati, distinti fra simulato e live: `SYNTHETIC_RECOVERY_REPORT.md`.

Stato: implementazione v1, percorso Wiki Data-only aggiornato al 2026-10-01,
commit base `6b61fd27`.
Il package e parte del monolite `backend/app/modules/wiki/mcps/`.
Docs e Data sono adapter deterministici separati; l'agente Wiki esterno seleziona
esclusivamente i tool Data sintetici. Docs rimane disponibile separatamente.

## Avvio locale

Installare `backend/requirements.txt` nell'ambiente Python. SDK MCP `2.0.0`;
SQLite con FTS5. Configurazione di esempio: `config/mcps/environment.example`.
Impostare `GAIA_MCP_SIGNING_SECRET` con almeno 32 caratteri casuali, distinta
dal segreto JWT GAIA. Non versionare il valore.

```bash
make mcp-docs-build QUALITY_PYTHON=backend/.venv/bin/python
make mcp-data-seed QUALITY_PYTHON=backend/.venv/bin/python
make mcp-http QUALITY_PYTHON=backend/.venv/bin/python
```

Il server HTTP ascolta su loopback `127.0.0.1:8768`, con `/docs/` e `/data/`.
Richiede sempre bearer interno, anche per discovery e initialize. Body massimo
64 KiB, host consentiti localhost/loopback/gaia-mcp e controllo DNS rebinding.
Trasporto stateless: nessuna autorizzazione deriva da session ID o parametri tool.
Stdio indipendente: `make mcp-docs-serve` e `make mcp-data-serve`, stessi parametri
Python. L'identita stdio e il principal locale; gli scope Data sono configurati
dal launcher tramite `--scopes`, mai da argomenti scelti dal modello.

### Ambiente Docker GAIA

```bash
docker compose -f docker-compose.yml -f docker-compose.mcp.yml --profile mcp config --quiet
docker compose -f docker-compose.yml -f docker-compose.mcp.yml --profile mcp up -d --build gaia-mcp backend
```

Eseguire prima i build offline degli artifact. L'override Compose assegna gli
URL interni al backend e avvia l'immagine backend con entrypoint MCP dedicato:
nessuna migration/bootstrap operativa. Il servizio MCP non riceve `.env`,
DATABASE_URL, credenziali PostgreSQL, volumi NAS o socket Docker. Riceve soltanto
il segreto di firma e gli artifact MCP montati read-only, senza porte pubblicate.
La configurazione Compose e verificata; nessun deploy e eseguito dalla change.

## Integrazione Wiki e autorizzazione

Nel router Wiki sono disponibili:

- `POST /wiki/mcp/token`: credenziale interna Data TTL 60 secondi;
- `GET /wiki/mcp/tools`: discovery Data filtrata per autorizzazioni effettive;
- `POST /wiki/mcp/chat`: agente MCP su soli dati sintetici con `gpt-reserve`.

Tutti usano l'identita GAIA autenticata e attiva. Il gateway controlla moduli e
sezioni nel database, non usa i moduli dichiarati dal modello o un parametro
`scopes`. Mappa `utenze.subjects` a `utenze.read`, `catasto.dashboard` a
`catasto.read` e insieme `ruolo.avvisi`/`ruolo.tributi.view` a `ruolo.read`;
Il gateway Data rimuove sempre `docs.read`, anche dagli scope dei token emessi.
Il server Docs separato mantiene il proprio contratto `docs.read`: un client
interno autorizzato puo usarlo indipendentemente dall'agente esterno.
Revoche successive all'emissione del token hanno una finestra massima di 60 s.
Issuer `gaia-wiki`, audience `gaia-mcp`, type `gaia_mcp`, algoritmo HS256 fisso.
Il server ricontrolla firma/scadenza/scope su ogni richiesta; scope extra sono
rifiutati. `conversation_id` ed `experiment_run_id` sono UUID facoltativi
propagati dal gateway autenticato alla telemetria delle fonti.

`WikiMCPClient` usa il vero SDK HTTP e nomi `docs__*`/`data__*`. Il gateway
costruisce il client con `docs_url=None`: non configura ne contatta `/docs/`,
non ne scopre tool e respinge ogni invocazione `docs__*` prima della connessione,
anche se il modello la inventa o il contesto possiede `docs.read`.
`GAIA_MCP_DOCS_URL` non abilita Docs nel gateway. L'agente non
riusa il classificatore legacy docs/live/logic: riceve il catalogo autorizzato,
sceglie i tool e costruisce il contesto. Budget: 8 chiamate e 6000 token stimati
di evidenze, con cap configurabili entro 16/12000. Il testo dei documenti e
sempre dato non attendibile; non modifica permessi o catalogo. Il nuovo endpoint
e separato dalla chat esistente per preservarne UI, contratti e comportamento.

Il modello e fissato a `gpt-reserve` tramite codex-lb; una configurazione con un
altro modello viene rifiutata. Il client usa URL e chiave gia configurati in
`CODEX_LB_URL` / `CODEX_LB_API_KEY`, oppure gli override dedicati
`GAIA_MCP_MODEL_BASE_URL` / `GAIA_MCP_MODEL_API_KEY`. Valori vuoti degli override
riusano la configurazione codex-lb. Nessun URL, chiave o provider di fallback e
inventato: configurazione assente o URL non HTTP(S), con credenziali incorporate,
query o frammento produce 503. Non usa Ollama. Timeout 60 s, zero retry.
Compose eredita la configurazione esistente e passa la chiave soltanto al
backend, mai al server MCP. Non stampare `docker compose config` completo con
credenziali risolte: usare `config --quiet`.

Il modello riceve soltanto domanda, catalogo Data autorizzato e risultati
sintetici con provenance, oppure errori minimizzati. Nessuna cronologia Wiki,
retrieval legacy o evidenza Docs entra nel contesto. La chat Wiki legacy conserva
configurazione e comportamento. Usare soltanto domande sintetiche; non incollare
documenti o dati reali nella domanda. Il controllo delle fonti e lato server,
non dipende da istruzioni nel prompt. La chat restituisce un 503 minimizzato
se il provider non e disponibile.

Le prove simulate del modello usano trasporto HTTP e SDK reali, verificano il
catalogo di 12 tool Data, tentativi Docs rifiutati e l'assenza di contenuti e
provenance Docs nei messaggi inviati al modello. Le prove Docs/Data combinate
verificano il client interno separato, non il gateway esterno.

## Replica Data e contratti

SQLite dedicato `gaia-mcp-synthetic-*.sqlite`, separato fisicamente dal database
operativo: non accetta URL PostgreSQL o host reali. Questo rende il guardrail
di separazione verificabile prima di qualsiasi connessione. La migration locale
`data/schema.sql` fissa `PRAGMA user_version=1`, FK, unique, check e indici;
gli schemi sperimentali PostgreSQL della migration storica `20260817_0200`
restano invariati e non sono usati dalla v1. Non si crea un altro backend.

Il seed `GAIA_SYNTHETIC_SEED`, default `gaia-v1`, produce UUIDv5, contenuti e
manifest deterministici: 300 soggetti, 12 distretti, 1000 particelle, 450 utenze,
600 legami soggetto-utenza, 1500 legami utenza-particella, 500 domande irrigue,
800 avvisi su tre anni, 1500 righe e 500 pagamenti. Esistono omonimi, piu
intestatari/utenze, legami per anno, pagamenti assenti/parziali/completi,
particelle senza ruolo e particelle storiche referenziate dal ruolo.

`make mcp-data-reset` rigenera atomicamente il solo DB sintetico riconosciuto;
un file preesistente senza manifest valido non puo essere sovrascritto.
Il server verifica hash delle tabelle, versione e FK, apre `mode=ro&immutable=1`
e abilita `query_only`: scritture SQL sono negate anche fuori dal catalogo tool.
I test dimostrano che stesso seed produce gli stessi byte del DB.
Gli importi sono interi in centesimi nel DB e stringhe decimali negli output.

I dodici tool v1 sono i precedenti undici piu `get_role_lines_by_notice`,
necessario al caso avviso → righe → particella senza espansione automatica.
Gli input Pydantic sono strict, extra vietati, UUID validati. Query fisse e
parametrizzate, nessun SQL scelto dal modello. I search atomici restituiscono
liste per gli omonimi: non scelgono automaticamente un'identita. I cursor sono
legati a principal, tool, filtri e dataset; non sono una nuova autorizzazione.
Ordinamento stabile per UUID; hard cap search 25, relazioni/righe 100, pagamenti
50. Errori tipizzati e minimizzati, provenienza per entity/UUID/versione.

## Corpus documentale e audit

Il freeze iniziale include due fonti operative canoniche con hash in
`config/mcps/docs-manifest.json`: Catasto PRD e Wiki PRD, 58 chunk.
Utenze e Ruolo restano `uncertain` ed esclusi: la verifica ha trovato sezioni
legacy `anagrafica.*`/`module_anagrafica` e parser/import file-based che
divergono dal runtime corrente `utenze.*` e dal read model inCASS.
Questo e un limite esplicito del primo corpus, non un'autorizzazione a
includere fonti storiche. Il Data MCP copre comunque tutti e tre i domini.

L'audit del corpus candidato ha verificato heading, sezioni funzionali,
freschezza rispetto al runtime e assenza di valori letterali di credenziali,
email personali e CF reali. Non e un rilevatore generale di segreti. Le fonti
incluse contengono descrizioni e riferimenti tecnici; alcuni path Catasto del
barrel precedente e i riferimenti Wiki al provider legacy sono documentazione
del Wiki esistente, non istruzioni per il nuovo agente MCP.

Non sono inclusi codice sorgente, progress, archive, prompt, Graphify, dump,
`.env` o operational Wiki non congelata. Non sono creati documenti a partire
dal ground truth. Build produce CSV manifest, versione e snapshot JSON;
il server legge solo lo snapshot e verifica integrita/policy. Una modifica di
fonte approvata richiede aggiornamento esplicito del manifest/hash e nuova
valutazione, non viene assorbita automaticamente.

## Valutazione riproducibile

```bash
make test-mcp QUALITY_PYTHON=backend/.venv/bin/python
make mcp-evaluate QUALITY_PYTHON=backend/.venv/bin/python
```

Query Docs: 32 in `config/mcps/docs-queries.json`, di cui 30 con target
documento/sezione e 2 no-answer. Baseline FTS5/BM25, nessuna API cloud:
Recall@10 1.0, MRR 0.9833, precisione@10 0.1393. La precisione mostra che la
baseline lessicale recupera anche sezioni irrilevanti: embedding, hybrid e
reranking restano esperimenti facoltativi, non sono dichiarati miglioramenti.
Il set e un ground truth iniziale di retrieval, non misura la qualita del LLM.

Query Data: 30 in `config/mcps/data-queries.json`, seed `gaia-v1`: 8 lookup,
8 relazionali, 6 multi-hop, 4 ambigue e 4 no-answer. Confronto su UUID attesi,
successo 30/30. Report JSON in `runtime-data/mcps/evaluation/`, con p50/p95/p99,
conteggi, token e byte payload. Latenze osservate su questa macchina: Docs
0.204/0.289/0.417 ms e Data 0.171/0.420/0.440 ms; non sono SLA di produzione.
Ogni run registra versione corpus/dataset; seed e tool catalog sono congelati
negli artifact/config versionati. Nessun risultato LLM viene usato come oracolo.

I test verificano schemi, input mancanti/errati, UUID inesistenti, omonimi,
paginazione, cap, no-answer, permessi, injection, traversal, symlink,
manomissione, read-only, telemetry, stdio, HTTP autenticato e integrazione Wiki.
Suite MCP finale: 164 test passati; 1080 statement e 208 branch, tutti coperti.
Regressioni Wiki indexer, router, policy, registry, orchestrator e capability:
122 test passati. Smoke aggiuntivo del CLI reale sugli artifact congelati:
discovery di 16 tool del client interno, retrieval Docs/Data e catalogo docs-only
filtrato. Il gateway esterno espone invece soltanto i 12 tool Data autorizzati.
Il test concorrente forza anche l'interleaving di due principal con scope
diversi e verifica isolamento e cleanup del contesto autorizzativo.
Coverage statement/branch di tutti i runtime MCP e del router Wiki modificato:
100%. Gate di stile, ratchet contro merge-base `6b61fd27` e Compose config
sono verificati. Baseline ed eccezioni non modificate. Per una cache bytecode
preesistente non scrivibile il lint locale usa
`PYTHONPYCACHEPREFIX=/tmp/gaia-mcp-pycache`; non rimuove cache del repository.
Metriche prima del passaggio Data-only: 26 file, 84 callable, 0 error e 24 warning;
metriche dopo: 26 file, 84 callable, 0 error e 26 warning. Il ratchet mirato
`backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref
origin/main backend/app/modules/wiki/mcps backend/app/modules/wiki/router.py`
passa con `findings: []`. Ruff check e format-check del perimetro MCP passano.
prima dell'implementazione v1 non esistevano file runtime MCP. I warning restano
sotto il gate error-level e non vengono assorbiti nella baseline. Il controllo
ratchet e read-only e non introduce refactoring nel codice legacy.

I target globali `make lint-backend` e `make complexity-ratchet` sono stati
eseguiti. Il primo lint passa; una verifica successiva rileva import e formato
non conformi nel test GATE concorrente `backend/tests/test_gate_collaborator_refresh.py`.
Il ratchet globale rileva una nuova violation in `_refresh_target` e regressioni
in `_presenze_mobile_record_items_for_month`, rispettivamente nei file concorrenti
`backend/app/modules/presenze/services/gate_collaborator_refresh.py` e
`backend/app/services/gate_mobile_sync.py`. Sono modifiche estranee al lavoro MCP,
apparse durante la sessione: non sono corrette o assorbite nella baseline.
I risultati globali descrivono questo snapshot del working tree, non una
regressione del perimetro MCP. Compose `config --quiet` e `git diff --check`
passano.

### Prova live gpt-reserve (2026-10-01)

Codex-lb raggiungibile, `gpt-reserve` presente nel catalogo modelli. Il test
effimero usa URL e chiave esistenti in `.env.graphify`, esclusivamente in memoria;
nessun valore e stampato o copiato nei file versionati. Esegue l'agente reale
con SDK HTTP, server MCP locale, bearer interno e principal sintetico di test,
su un database `gaia-v1` appena generato in una directory temporanea.
Anche la fixture Docs del server e interamente sintetica e non viene interrogata.
Non viene usata la sessione autenticata di un utente GAIA reale.

Domanda sintetica: cercare `Omonimo` tramite `search_subjects` e riportare due
soggetti con UUID. Risultato live: una chiamata tool, due provenance Data,
283 token stimati di evidenze, zero richieste `/docs/`. Il provider produce
effettivamente il tool call e riceve il risultato prima della risposta finale:
questa prova non usa risposte LLM simulate. Evidenza minimizzata in
`/tmp/gaia-mcp-live.log`; nessun contenuto o credenziale nel report.
Nessun processo persistente, deploy o documento reale coinvolto.

Graphify codice aggiornato tramite `make graphify-wiki-code
GRAPHIFY_CODE_FLAGS=--force`, senza LLM. L'aggiornamento semantico Graphify docs
non viene eseguito: invierebbe documentazione reale al provider esterno, vietato
dal vincolo di questa change anche se le credenziali sono disponibili.

### Login e permessi del gateway (2026-10-01)

Il test `test_gateway_real_login_permissions_revocation_and_inactive_user`
usa `/auth/login` e `/wiki/mcp/token` con un utente sintetico viewer, database
SQLite temporaneo e implementazioni GAIA di password hashing e JWT. Solo `get_db` viene sostituito
per isolare la persistenza: autenticazione, `require_active_user`, resolver dei
permessi e calcolo degli scope non sono simulati. Anche la registrazione del
dispositivo VPN del login usa tabelle temporanee dedicate.

Verificati: 401 senza autenticazione o con password errata, scope Data
autorizzati e assenza `docs.read`; revoca immediata dei nuovi scope disabilitando
un modulo e introducendo dinieghi di sezione per utente/ruolo; 401 sul token
esistente dopo disattivazione utente e 403 al successivo login. Nessun account
reale viene creato, modificato o impersonato nel database operativo.

### Benchmark live del gateway

La prova effimera `/tmp/gaia-mcp-live-gateway.py` esegue login GAIA, emissione
del bearer MCP, discovery e richieste a `/wiki/mcp/chat` con il provider reale
`gpt-reserve`. L'applicazione di prova monta i router di produzione Auth e MCP;
solo la dipendenza DB punta alle tabelle sintetiche temporanee. Non e un deploy
del backend e non usa un account operativo. Il trasporto HTTP MCP e reale.

I 30 casi di `config/mcps/data-queries.json` diventano domande con i soli filtri
iniziali sintetici espliciti: UUID, codici e annualita necessari alla ricerca.
Gli UUID attesi e i risultati intermedi del ground truth non sono forniti al
modello. Nei casi multi-hop la domanda specifica l'ordinamento UUID della
scelta della prima relazione. Il modello sceglie i tool dal catalogo.

Per ogni risposta si confrontano gli UUID della provenance dell'entita finale
con il ground truth offline, si verifica che gli UUID attesi siano citati nel
testo e si registrano HTTP status, latenza, budget 8 chiamate/6000 token di
evidenze, source sintetica e correlation ID. Questo verifica retrieval e
citazioni, non costituisce una valutazione semantica completa del testo del LLM.
Per i no-answer si controllano evidenze vuote e `found=false`.

Il report minimizzato e `runtime-data/mcps/evaluation/live-gateway.json`, ignorato
da git; non contiene credenziali, risposte complete o contenuti documentali.
Il log effimero e `/tmp/gaia-mcp-live-gateway.log`. Il server include una fixture
Docs interamente sintetica e conta le richieste per provare che `/docs/` non e
raggiunto. Al termine vengono verificati scope/catalogo dopo revoca, domanda su
un dominio negato e blocco dell'utente disattivato; i processi e i DB temporanei
sono eliminati dal teardown.

Esito del run live 2026-10-01: 30/30 HTTP 200, UUID finali corrispondenti al
ground truth e UUID attesi presenti nelle risposte. Anche i quattro no-answer
hanno eseguito tool e restituito evidenze vuote. Scope/catalogo dopo revoca,
rifiuto della ricerca su Utenze negato e blocco dell'utente inattivo: PASS.
Provenance esclusivamente `gaia_synthetic_db`, correlation ID preservati,
zero richieste Docs e nessuna violazione dei budget. Latenza del gateway:
p50 16.152 s, p95 30.736 s, p99 34.886 s; un singolo run, non uno SLA.
Latenze comprensive del provider reale, distinte dalle misure offline Data.

Verifiche della tranche gateway: 156 test MCP con coverage statement/branch
100%, Ruff sul test modificato e Compose quiet PASS. Il ratchet globale ora
passa (`findings: []`, `/tmp/gaia-mcp-ratchet-gateway.log`), dopo aggiornamenti
concorrenti fuori dal perimetro MCP. Il lint globale continua a rilevare
import/formato nel test concorrente `backend/tests/test_gate_mobile_team_delete.py`
(`/tmp/gaia-mcp-lint-gateway-final.log`); il file non viene modificato da questa
tranche. Graphify wiki-code conferma topologia invariata; docs remoto escluso.
Gli esiti dei gate globali nella sezione precedente descrivono lo snapshot
storico della tranche Data-only, non quello finale della prova gateway.

## Telemetria

Audit finale e stato complessivo dei gate: `FINAL_DEVELOPMENT_REVIEW.md`.

JSON su stderr: request ID, principal pseudonimizzato, correlation ID, tool,
scope, timestamp, durata, stato/errore tipizzato, result count, truncation,
token stimati, versione server e versione corpus/dataset. Nessun argomento,
contenuto o record completo nei log applicativi. Stima deterministica dei
token: `ceil(caratteri/4)` sul JSON restituito prima di aggiungere il campo
di stima. Le evidenze MCP non generano risposte LLM, non chiamano altre fonti.
# Installer HTTPS interno

Per preparare gli installer della nuova CA GAIA richiesta dall'utente, vedere
`CLIENT_CA_INSTALLERS.md` e `make mcp-ca-bundle` / `make test-mcp-tls`.
Non confondere il trust interno `gaia.lan` con l'ingresso pubblico necessario
al connettore remoto Claude: quest'ultimo resta da implementare e pubblicare.
# Fondazione OAuth (2026-10-03)

Il backend delega al login GAIA esistente, senza grant password al connettore.
Componente verificato ma non montato/pubblicato; configurazione prenotata e
disattivata. Contratto, limiti e gate residui:
[OAUTH_FOUNDATION_2026-10-03.md](OAUTH_FOUNDATION_2026-10-03.md).
Gate mirato: `make test-mcp-oauth QUALITY_PYTHON=backend/.venv/bin/python`.

Tranche successiva: pagina `/mcp/consent` e listener OAuth Data-only separato,
disattivati per default. Configurazione, proxy da revisionare e gate live:
[CONNECTOR_RUNTIME_2026-10-03.md](CONNECTOR_RUNTIME_2026-10-03.md).
Gate: `make test-mcp-connector` e `make test-mcp-consent`.
