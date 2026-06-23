# GAIA Operational Wiki Architecture

## Obiettivo

Evolvere il modulo `wiki` da assistente `docs-first` con fallback generici a un sistema operativo capace di:

- riconoscere il tipo di compito richiesto dall'utente
- capire quali dati minimi servono per eseguire il compito
- usare documentazione persistente e strutturata invece di affidarsi solo a chunk RAG grezzi
- distinguere in modo esplicito tra `clarification`, `tool/live-data`, `docs`, `logic` e `unavailable`

Questo documento prende ispirazione dal modello "LLM Wiki" di Karpathy, ma lo adatta a GAIA con vincoli piu rigorosi su routing, permessi, provenance e superfici operative.

## Problema attuale

Il flusso attuale ha quattro limiti strutturali:

1. La decisione iniziale e troppo presto binaria tra `docs_only`, `live_data` e `logic`.
2. Il sistema dipende troppo da keyword e matcher locali per capire l'intento reale.
3. Se non esiste un tool esatto, la richiesta degrada spesso nel ramo `docs_only`.
4. Il fallback documentale non distingue tra:
   - mancano dati minimi per eseguire una ricerca
   - il sistema non ha un tool per quel compito
   - non esiste documentazione utile
   - il provider Wiki e indisponibile

Il risultato pratico e che domande operative valide possono ricevere una risposta del tipo "non ho trovato documentazione interna", anche quando il problema reale e solo la mancanza di parametri o di una capability ben modellata.

## Principi architetturali

### 1. Task-first, non docs-first

La prima decisione non deve essere "cerco nei documenti?" ma:

- che compito sta chiedendo l'utente?
- il compito e supportato?
- quali slot servono?
- ho gia gli input minimi?

### 2. Wiki operativo persistente

La conoscenza del sistema non deve vivere solo nei documenti sorgente o nei chunk indicizzati.
Serve un layer persistente di wiki operativo, mantenuto incrementalmente, che descrive:

- pagine e moduli
- capability applicative
- prerequisiti e input minimi
- procedure
- errori frequenti
- limiti noti

### 3. Capability registry esplicito

Il backend non deve inferire solo da matcher sparsi.
Ogni capability deve essere dichiarata come entita tipizzata con:

- `task_type`
- `module_key`
- `required_slots`
- `optional_slots`
- `tool_name` o `resolver`
- `clarification_prompt`
- `docs_pages`
- `permission_scope`

### 4. Slot filling prima del fallback

Se il task e riconosciuto ma mancano dati minimi, il sistema non deve entrare nel ramo `docs not found`.
Deve produrre una risposta `needs_clarification` che chiede solo gli slot mancanti.

### 5. Fallback taxonomy esplicita

I fallback devono essere classificati in stati distinti:

- `missing_parameters`
- `no_matching_capability`
- `tool_unavailable`
- `permission_denied`
- `docs_not_found`
- `provider_unavailable`

Ogni stato ha una UX diversa e un diverso piano di escalation.

## Architettura target

```text
User question
    |
    v
Semantic router
    |
    +--> language
    +--> normalized_query
    +--> module_hint
    +--> task_type
    +--> extracted_slots
    +--> confidence
    |
    v
Capability selector
    |
    +--> matching capability
    +--> required slots
    +--> permission scope
    |
    +--> if required slots missing -> clarification response
    +--> if capability missing -> capability-gap fallback
    +--> if tool available -> live resolver/tool path
    +--> if docs-backed task -> operational wiki retrieval path
    |
    v
Response composer
    |
    +--> mode
    +--> provenance
    +--> evidences
    +--> next_action_hint
```

## Nuovi concetti chiave

### Task type

Oltre a `intent`, il router deve emettere un `task_type`.

Esempi iniziali:

- `page_intro`
- `module_overview`
- `navigation_help`
- `entity_lookup`
- `owner_lookup`
- `metric_explanation`
- `workflow_explanation`
- `feature_gap`
- `docs_lookup`

Il `task_type` decide il ramo, non il contrario.

### Slots

Ogni `task_type` richiede slot minimi.

Esempi:

- `owner_lookup`
  - valid combinations:
    - `comune + foglio + particella`
    - `codice_fiscale`
    - `partita_iva`
    - `nominativo`
- `entity_lookup`
  - tipicamente `id`, `uuid`, `codice`, `cco`
- `navigation_help`
  - `module_key` o `page_path` opzionali ma utili

### Operational wiki page

Il wiki operativo non e solo testo libero. Ogni pagina deve avere una struttura minima.

Schema suggerito:

```md
# Capability: catasto.owner_lookup

## Scopo
Quando usare questa capability.

## Input minimi
- comune
- foglio
- particella

## Input alternativi
- nominativo
- codice fiscale
- partita IVA

## Procedura
Passi operativi lato GAIA.

## Output atteso
Cosa restituisce il sistema.

## Errori frequenti
Casi da chiarire o bloccare.

## Tool collegati
- wiki.catasto.owner_lookup

## Pagine correlate
- /catasto/particelle
- /catasto/gis
```

## Corpus operativo proposto

### 1. Raw sources

Fonti immutabili:

- `docs/`
- `domain-docs/`
- codice backend/frontend rilevante
- routing applicativo
- schemi API
- prompt e playbook esistenti

### 2. Operational wiki

Nuovo corpus generato/curato:

```text
domain-docs/wiki/operational/
├── modules/
│   ├── catasto.md
│   ├── operazioni.md
│   ├── ruolo.md
│   └── ...
├── pages/
│   ├── catasto__particelle.md
│   ├── catasto__gis.md
│   └── ...
├── capabilities/
│   ├── catasto.owner_lookup.md
│   ├── catasto.particella_lookup.md
│   └── ...
└── workflows/
    ├── catasto_owner_search.md
    └── ...
```

### 3. Capability registry

Machine-readable registry, separato dal markdown:

```text
backend/app/modules/wiki/capabilities/
├── registry_schema.py
├── registry_loader.py
└── catalog/
    ├── catasto.py
    ├── operazioni.py
    └── ...
```

Ogni record deve contenere almeno:

```python
CapabilityDefinition(
    name="catasto.owner_lookup",
    task_type="owner_lookup",
    module_key="catasto",
    required_slots=[["comune", "foglio", "particella"], ["codice_fiscale"], ["partita_iva"], ["nominativo"]],
    tool_name="wiki.catasto.owner_lookup",
    clarification_prompt="Per trovare il proprietario mi servono ...",
    docs_pages=["capabilities/catasto.owner_lookup.md"],
    permission_scope="catasto.read",
)
```

## Evoluzione del router

### Stato attuale

- `question_router.py`
- `semantic_router.py`
- `intent_classifier.py`
- `guardrails.py`

### Stato target

Il router deve produrre una struttura piu ricca:

```python
RoutedTask(
    language="it",
    normalized_query="trova proprietario terreno",
    intent="live_data",
    task_type="owner_lookup",
    module_hint="catasto",
    extracted_slots={
        "comune": None,
        "foglio": None,
        "particella": None,
        "nominativo": None,
        "codice_fiscale": None,
        "partita_iva": None,
    },
    confidence=0.82,
)
```

La presenza o assenza degli slot diventa parte del contratto del router, non un dettaglio occasionale delle guardrail.

## Evoluzione dell'orchestrator

### Nuovo flow

```text
1. route question
2. classify task_type
3. select capability
4. check permissions
5. check required slots
6. if missing slots -> clarification
7. if capability has tool -> execute tool
8. if capability is docs-backed -> query operational wiki
9. if both exist -> hybrid response
10. if nothing matches -> explicit capability-gap fallback
```

### Conseguenze pratiche

- `guardrails` non devono piu gestire casi di business specifici a mano uno per uno
- i chiarimenti diventano comportamento standard di capability
- il ramo `docs_not_found` resta solo per vere query documentali

## Fallback policy proposta

### Missing parameters

Risposta:
- riconosce il task
- elenca i dati mancanti
- propone il formato minimo richiesto

### No matching capability

Risposta:
- non finge copertura documentale
- dichiara che il sistema non ha ancora una capability operativa per quel compito
- invita a riformulare o aprire supporto

### Tool unavailable

Risposta:
- capability riconosciuta
- tool previsto ma non operativo
- suggerisce alternativa o escalation

### Docs not found

Da usare solo quando:
- il task e davvero documentale
- non esiste una capability operativa applicabile
- il retrieval su wiki operativo e fonti non trova supporto sufficiente

## Piano di migrazione

### Fase 1 - Routed task contract

Obiettivo:
- introdurre `task_type`, `slots`, `confidence`

File principali:

- `backend/app/modules/wiki/services/semantic_router.py`
- `backend/app/modules/wiki/services/question_router.py`
- `backend/app/modules/wiki/services/intent_classifier.py`

### Fase 2 - Capability registry

Obiettivo:
- centralizzare capability, slot richiesti, tool e prompt di chiarimento

File principali:

- nuova cartella `backend/app/modules/wiki/capabilities/`
- refactor di `tool_registry*.py`

### Fase 3 - Operational wiki corpus

Obiettivo:
- introdurre markdown operativi persistenti per modulo/pagina/capability/workflow

File principali:

- `domain-docs/wiki/operational/`
- adattamenti a `indexer.py` e `rag.py`

### Fase 4 - Orchestrator refactor

Obiettivo:
- far dipendere il flusso da `RoutedTask + CapabilityDefinition`

File principali:

- `backend/app/modules/wiki/services/orchestrator.py`
- `backend/app/modules/wiki/services/response_composer.py`
- `backend/app/modules/wiki/services/guardrails.py`

### Fase 5 - Telemetry and lint

Obiettivo:
- misurare i gap reali e mantenere il wiki operativo coerente

Metriche iniziali:

- percentuale `missing_parameters`
- percentuale `no_matching_capability`
- percentuale `docs_not_found`
- top task types non coperti
- top slot mancanti per capability

## Regole di implementazione

1. Non introdurre generation libera come fallback finale per richieste operative.
2. L'LLM puo chiarire, classificare, estrarre slot e sintetizzare, ma non deve fingere dati.
3. Le capability devono restare read-only salvo milestone espliciti futuri.
4. Ogni capability nuova deve includere:
   - registry entry
   - pagina operational wiki
   - test router
   - test orchestrator
   - test fallback/clarification

## Decisione consigliata

Adottare il modello "LLM Wiki" in versione ibrida:

- `operational wiki` persistente come base di conoscenza compilata
- `capability registry` come layer deterministico di esecuzione
- `slot filling` come precondizione standard
- `RAG` relegato a supporto documentale e arricchimento, non come primo fallback universale

Questo consente di uscire dalla logica "aggiungiamo una regola per ogni domanda" e di spostare il sistema verso una semantica di compiti, capability e input minimi.
