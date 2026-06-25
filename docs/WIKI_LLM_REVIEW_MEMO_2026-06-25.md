# GAIA Wiki LLM Review Memo

Data: `2026-06-25`

## Obiettivo

Questo documento descrive un problema reale del sistema Wiki di GAIA, la logica oggi in uso, i failure mode osservati in produzione e le modifiche gia introdotte per migliorare il comportamento.

Il target di questo memo e un team di sviluppatori specializzati in LLM, routing semantico, retrieval e orchestrazione ibrida `rules + model`.

L'obiettivo non e chiedere una review generica del codice, ma una review mirata su:

- correttezza della separazione tra classificazione, navigazione, docs retrieval e live data
- robustezza del routing in presenza di ambiguita lessicali tra moduli
- rapporto corretto tra regole deterministiche e decisione LLM
- modalita corretta di costruzione del prompt, del catalogo delle pagine e del contesto pagina/modulo
- criteri di fallback quando il provider LLM e degradato o indisponibile

## Sintesi del problema

Il Wiki di GAIA e concepito come assistente operativo interno, contestuale alla pagina e al modulo in cui si trova l'utente.

In pratica, quando l'utente chiede:

- `dove trovo il gis?`
- `dove trovo le particelle?`
- `dove trovo le pratiche?`
- `dove trovo i mezzi?`
- `dove trovo le giornaliere?`

il sistema dovrebbe:

1. capire se la richiesta e di navigazione, documentazione, logica o live data
2. usare il contesto corrente di pagina e modulo come segnale forte
3. risolvere la pagina corretta tra piu candidati possibili
4. evitare risposte generiche del tipo "in questa pagina posso aiutarti..."
5. non deviare verso altri moduli se il modulo corrente ha gia una corrispondenza ragionevole

Il problema osservato e che oggi il sistema fallisce soprattutto su richieste brevi e ambigue di navigazione, con questi pattern:

- collisione tra moduli semanticamente vicini
- sovrauso di fallback generici
- caduta su `live_data` o `docs_only` non appropriati
- incapacita di usare bene il contesto pagina/modulo
- degradazione qualitativa forte quando il provider LLM non risponde o risponde male

## Contesto architetturale

### Punto di ingresso

La chat wiki passa principalmente da:

- `backend/app/modules/wiki/routes/chat.py`
- `backend/app/modules/wiki/services/orchestrator.py`

L'orchestrator decide:

- se fare preflight con regole locali
- se usare un tool `live_data` o `logic`
- se usare risposta docs
- se usare il router semantico LLM
- se usare fallback locale `agent`

### Componenti principali

#### 1. Fast router heuristico

File:

- `backend/app/modules/wiki/services/question_router.py`

Responsabilita:

- intercettare greeting, intro pagina, overview modulo, navigation help, richieste brevi o generiche
- classificare velocemente senza LLM

Problema:

- e utile per latenza e stabilita, ma oggi puo bypassare proprio i casi ambigui in cui servirebbe piu contesto o una disambiguazione migliore

#### 2. Semantic router LLM

File:

- `backend/app/modules/wiki/services/semantic_router.py`

Responsabilita:

- classificare `intent`, `capability`, `module_hint`, `task_type`
- riformulare `normalized_query`
- estrarre `slots`

Modifica introdotta il `2026-06-25`:

- il prompt e stato ampliato per includere:
  - `current_module`
  - `current_page_path`
  - catalogo dei moduli
  - catalogo delle pagine note
  - `page_path` risolto
  - `confidence`
  - `disambiguation_needed`
  - `disambiguation_question`

Problema residuo:

- il semantic router non e ancora l'unico decisore della navigazione
- la logica deterministica a valle puo ancora dominare o contraddire la decisione LLM

#### 3. Guardrails e resolver di navigazione

File:

- `backend/app/modules/wiki/services/guardrails.py`
- `backend/app/modules/wiki/services/context_hints.py`

Responsabilita:

- riconoscere richieste di navigazione
- risolvere una pagina in base a token e hint
- produrre risposte contestuali tipo `La funzione che stai cercando si trova in...`

Problema attuale:

- il resolver usa overlap lessicale tra token domanda, path, label, examples
- questo approccio non gestisce bene collisioni tra moduli con lessico simile
- l'algoritmo attuale tende a scegliere la miglior sovrapposizione superficiale, non la miglior scelta operativa nel contesto

#### 4. Retrieval docs / RAG

File:

- `backend/app/modules/wiki/services/rag.py`
- `backend/app/modules/wiki/services/openai_client.py`
- `backend/app/modules/wiki/services/agent_fallback.py`

Responsabilita:

- costruire risposte `docs_only`
- usare provider principale `codex-lb`
- usare fallback locale `agent` quando necessario

Problema osservato:

- quando il provider e degradato, il sistema puo recuperare documenti ma non sintetizzarli bene
- in questi casi il wiki scade in risposte incomplete, generiche o con testo di fallback poco utile

#### 5. Tool registry e live data

File:

- `backend/app/modules/wiki/services/tool_registry*.py`

Responsabilita:

- mappare richieste a tool di dati live o spiegazioni logiche

Problema osservato:

- alcune richieste di navigazione o documentazione scivolano impropriamente nel canale `live_data`
- esempio concreto sotto: anomalie visure utenze che finiscono in una risposta di dati live catasto

## Comportamento osservato live

Il `2026-06-25` e stata eseguita una batteria live su `http://gaia.lan/api/wiki/chat` con focus su:

- `catasto`
- `operazioni`
- `presenze/inaz`
- `ruolo`
- `utenze`
- `elaborazioni`

Script usato:

- `scripts/wiki-live-battery-ced.sh`

### Risultato sintetico

- `catasto`: `3/5` passati
- `operazioni`: `2/4` passati
- `presenze`: `1/4` passati
- `ruolo`: `4/4` passati
- `utenze`: `1/2` passati
- `elaborazioni`: `5/5` passati

### Failure mode concreti

#### 1. Collisione `catasto` vs `ruolo`

Domanda:

- `dove trovo le particelle?`

Atteso:

- `/catasto/particelle`

Osservato:

- `/ruolo/particelle`

Interpretazione:

- il termine `particelle` esiste in piu domini
- il sistema non applica un ranking abbastanza forte basato su contesto o priorita modulo

#### 2. Collisione `operazioni` vs `riordino`

Domanda:

- `dove trovo le pratiche?`

Atteso:

- `/operazioni/pratiche`

Osservato:

- `/riordino/pratiche`

Interpretazione:

- `pratiche` e token ad alta ambiguita
- serve disambiguazione o priorita per modulo corrente

#### 3. Collisione `operazioni` vs `elaborazioni`

Domanda:

- `dove trovo i mezzi?`

Atteso:

- `/operazioni/mezzi`

Osservato:

- `/elaborazioni/autodoc`

Interpretazione:

- il modello o il resolver aggancia il token `mezzi` all'area AUTODOC mezzi invece che alla pagina operativa principale

#### 4. Mancata risoluzione `inaz/presenze`

Domande:

- `dove trovo le giornaliere?`
- `dove trovo i collaboratori?`

Atteso:

- `/inaz/giornaliere`
- `/inaz/collaboratori`

Osservato:

- risposta generica: `In questa pagina posso aiutarti...`

Interpretazione:

- il catalogo pagina non viene sfruttato bene
- il sistema preferisce fallback generico invece di una navigazione esplicita

#### 5. Scivolamento improprio su `live_data`

Domanda:

- `dove vedo le anomalie delle visure routing?`

Atteso:

- `/utenze/visure-routing-anomalies`

Osservato:

- risposta `live_data` con metriche catasto

Interpretazione:

- classificazione intent errata oppure matching tool troppo permissivo

#### 6. Pagina corrente ignorata

Domanda su `/catasto/gis`:

- `cosa posso fare in questa pagina?`

Atteso:

- overview della pagina GIS Catasto

Osservato:

- risposta meta/generica sul `docs_lookup`

Interpretazione:

- il contesto pagina non viene propagato o onorato correttamente in tutto il flusso

## Problema infrastrutturale parallelo

Oltre al problema di routing/logica, e stato osservato un problema operativo separato:

- il provider `codex-lb` non era sempre raggiungibile o utilizzabile in produzione
- il deploy CED stava accidentalmente includendo una `docker-compose.override.yml` da sviluppo

Questo e stato corretto con:

- deploy che usa solo `docker-compose.yml`
- fallback locale `agent` montato correttamente nel container backend

File toccati:

- `docker-compose.yml`
- `scripts/deploy-ced-gaia.sh`
- `backend/app/modules/wiki/services/agent_fallback.py`
- `backend/app/modules/wiki/services/openai_client.py`

Nota importante:

- questo fix migliora la disponibilita del wiki
- non risolve il problema logico di navigazione e ambiguita

## Modifiche gia introdotte lato logica

### 1. Nuovo prompt strutturato nel semantic router

File:

- `backend/app/modules/wiki/services/semantic_router.py`

Modifica:

- introdotto prompt di routing molto piu esplicito
- aggiunti:
  - catalogo moduli
  - catalogo pagine note
  - regole esplicite per casi ambigui
  - output strutturato con `page_path`, `confidence`, `disambiguation_needed`

Obiettivo:

- trasformare il semantic router da classificatore generico a router di navigazione vero e proprio

### 2. Wiring nell'orchestrator per non saltare il semantic router

File:

- `backend/app/modules/wiki/services/orchestrator.py`

Modifica:

- per capability come `navigation_help`, `page_intro`, `module_overview`, `platform_overview`, `clarification_needed`, l'orchestrator prova il semantic router contestuale prima di affidarsi solo al fast path

Obiettivo:

- evitare che le richieste piu ambigue vengano cristallizzate troppo presto da euristiche locali

### 3. Batteria live di test

File:

- `scripts/wiki-live-battery-ced.sh`

Funzione:

- login automatico
- invio di casi live a `/api/wiki/chat`
- verifica `status`, testo atteso e testo proibito
- riepilogo per modulo

Obiettivo:

- avere un benchmark ripetibile contro il sistema reale

### 4. Test unitari sul semantic router

File:

- `backend/tests/test_wiki_semantic_router.py`

Copertura:

- parsing JSON
- normalizzazione campi
- supporto nuovi campi di navigazione
- verifica che il prompt includa contesto e catalogo

## Diagnosi attuale

La diagnosi piu probabile e che il sistema soffra di un problema strutturale a tre livelli.

### Livello 1. Routing semantico non allineato al catalogo reale

Il modello non lavora su un catalogo ristretto e prioritizzato abbastanza bene.

Conseguenza:

- termini come `particelle`, `pratiche`, `mezzi` vengono agganciati in modo semanticamente plausibile ma operativamente errato

### Livello 2. Resolver deterministico troppo semplice

`guardrails.py` usa una strategia di overlap token-based sufficiente per casi facili ma fragile sui casi ambigui.

Conseguenza:

- se il modello non risolve o viene bypassato, il fallback deterministic sceglie candidati sbagliati

### Livello 3. Separazione intent/navigation/live_data non abbastanza rigida

Alcune richieste di navigazione vengono deviate verso `docs_only` generico o `live_data`.

Conseguenza:

- l'utente riceve o una metrica non richiesta o una risposta generica che non porta da nessuna parte

## Aspetti da far analizzare al team LLM

### A. Design del router

Domande:

- il semantic router deve restare solo un classificatore o deve diventare il resolver primario di pagina?
- conviene introdurre un ranking a due stadi:
  1. shortlist deterministica di pagine candidate
  2. scelta finale LLM su shortlist
- conviene spostare la disambiguazione come output obbligatorio per termini ad alta collisione?

### B. Prompt design

Domande:

- il catalogo delle pagine va dato sempre intero o ristretto al modulo corrente piu alcune alternative globali?
- il formato migliore e elenco testuale, JSON, tabella o few-shot strutturato?
- per questi task e meglio un prompt classificatorio puro o un prompt di constrained selection?

### C. Schema dell'output

Domande:

- e corretto richiedere sempre `page_path`, `confidence`, `disambiguation_needed`?
- serve anche `candidate_pages` con top-k e score qualitativo?
- serve distinguere tra:
  - `resolved_navigation`
  - `needs_disambiguation`
  - `generic_help`

### D. Orchestrazione con regole

Domande:

- quali capability devono passare sempre dal modello e quali possono restare deterministiche?
- ha senso lasciare `greeting` e `page_intro` al fast path e mandare solo la navigazione ambigua al semantic router?
- come evitare conflitti tra decisione del semantic router e resolver di `guardrails.py`?

### E. Strategy per i fallback

Domande:

- quando il provider e degradato, conviene:
  - mostrare risposta minima di navigazione deterministica
  - usare fallback locale LLM
  - bloccare solo la sintesi docs ma non la navigazione
- la navigazione dovrebbe essere disaccoppiata del tutto dalla disponibilita del provider?

### F. Valutazione

Domande:

- come costruire un dataset di eval per navigation resolution?
- quali metriche usare:
  - top-1 route accuracy
  - ambiguity recall
  - wrong-module rate
  - generic-fallback rate
  - live-data false-positive rate

## Proposta tecnica da valutare

La proposta piu ragionevole da valutare e questa:

### Step 1. Separare nettamente i task

- `navigation resolution`
- `page intro / module overview`
- `docs QA`
- `live_data`
- `logic explanation`

Ognuno con prompt, output schema e criteri di fallback propri.

### Step 2. Rendere la navigazione un task di selection, non di generazione

Invece di chiedere al modello una risposta libera, chiedere:

- seleziona una route da un insieme candidato
- oppure segnala `needs_disambiguation`

### Step 3. Costruire shortlist candidate deterministicamente

Esempio:

- candidate set da `module_key`, `page_path`, alias, sinonimi, sidebar reale
- solo dopo usare LLM per scegliere tra i candidati

### Step 4. Introdurre alias espliciti e weight per modulo

Esempio:

- `particelle` peso alto per `catasto` se current module e `catasto`
- `particelle ruolo` peso alto per `ruolo`
- `mezzi` peso primario per `/operazioni/mezzi`, secondario per `/elaborazioni/autodoc`

### Step 5. Ridurre al minimo le risposte generiche

Le risposte tipo:

- `In questa pagina posso aiutarti...`

vanno emesse solo se:

- non esiste una route candidata sufficientemente forte
- oppure il sistema ha gia chiesto disambiguazione

### Step 6. Benchmark automatico continuo

Usare `scripts/wiki-live-battery-ced.sh` come base per:

- test in CI contro stub/mock
- test periodici contro ambiente integrato
- confronto prima/dopo sulle route errate

## File da revisionare con priorita

Priorita alta:

- `backend/app/modules/wiki/services/orchestrator.py`
- `backend/app/modules/wiki/services/semantic_router.py`
- `backend/app/modules/wiki/services/question_router.py`
- `backend/app/modules/wiki/services/guardrails.py`
- `backend/app/modules/wiki/services/context_hints.py`

Priorita media:

- `backend/app/modules/wiki/services/rag.py`
- `backend/app/modules/wiki/services/openai_client.py`
- `backend/app/modules/wiki/services/agent_fallback.py`
- `backend/app/modules/wiki/capabilities/catalog.py`

Supporto e observability:

- `backend/app/modules/wiki/routes/audit.py`
- `backend/app/modules/wiki/routes/telemetry.py`
- `backend/app/modules/wiki/routes/support_analytics.py`
- `scripts/wiki-live-battery-ced.sh`
- `backend/tests/test_wiki_semantic_router.py`

## Reproduzione minima consigliata

Sequenza consigliata per il team:

1. Eseguire la batteria live:

```bash
./scripts/wiki-live-battery-ced.sh
```

2. Verificare i casi falliti di navigazione ambigua:

- `dove trovo le particelle?`
- `dove trovo le pratiche?`
- `dove trovo i mezzi?`
- `dove trovo le giornaliere?`
- `dove vedo le anomalie delle visure routing?`

3. Verificare lo stesso set passando `module_key` e `page_path` diversi.

4. Ispezionare quale layer sta decidendo il risultato finale:

- fast router
- semantic router
- guardrail navigation resolver
- docs fallback
- tool registry live_data

## Conclusione

Il problema non sembra essere un semplice "prompt da migliorare".

Il problema reale e una composizione non ancora robusta tra:

- euristiche locali
- routing LLM
- catalogo delle pagine
- disambiguazione tra moduli
- fallback docs/live_data

In altre parole:

- il sistema ha gia abbastanza informazione per rispondere bene in molti casi
- ma non ha ancora una politica affidabile per scegliere la route giusta quando il lessico e condiviso tra moduli

La review richiesta al team LLM dovrebbe quindi focalizzarsi non solo sul testo del prompt, ma sul design complessivo del `navigation resolution pipeline`.
