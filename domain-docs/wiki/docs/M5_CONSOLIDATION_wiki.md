# M5 Consolidation — GAIA Wiki

Ultimo aggiornamento: 2026-06-11

## Obiettivo

Portare il modulo `wiki` da prima piattaforma utile e operativa a sistema piu stabile, veloce e governabile, intervenendo su:

- latenza percepita e affidabilita del core assistant
- separazione delle responsabilita nel backend e nel frontend admin
- maturazione della governance supporto verso cluster persistiti e bridge col delivery reale

`M5` non introduce un nuovo perimetro funzionale principale.
Consolida quello esistente per preparare meglio i milestone successivi.

---

## Sintesi esecutiva

Ordine raccomandato:

1. `M5.1` Streaming reale + routing piu economico
2. `M5.2` Refactor del core orchestration e della UI admin richieste
3. `M5.3` Cluster persistiti + bridge ticket esterno

Stato al 2026-06-11:

- avviata la prima tranche di `M5.1`
  - fast-path deterministic prima del semantic router LLM
  - stream reale provider sul path documentale
  - contratto SSE invariato lato frontend
  - stato UI esplicito del routing nel frontend
  - misura client-side di `time_to_first_chunk`
- avviata la prima tranche di `M5.2`
  - estrazione del pannello artifact/snapshot del caso da `WikiRequestsPage.tsx`
  - estrazione dei blocchi `WikiRequestsFilters`, `WikiRequestsList`, `WikiRequestDetailPanel` e `WikiRequestDeliveryPanel`
  - primo refactor interno di `orchestrator.py` con helper espliciti per `guardrail`, `tool`, `docs`, `audit` e `synthetic stream`
  - estrazione da `routes/requests.py` dei service `request_artifacts.py` e `request_workflow.py`
  - split di `request-support.ts` in payload builder, snapshot capture, draft flow e facade di export
- avviata la prima tranche di `M5.3`
  - campi `external_ticket_*` e `delivery_*` sulla richiesta Wiki
  - sezione admin `Delivery` nel dettaglio richiesta
  - filtri admin per `delivery` e presenza ticket nella inbox richieste
  - metriche analytics supporto su `linked_ticket`, `delivery_started`, `released`, `wont_do` e `top_delivery_statuses`
  - export CSV delle richieste con ticket nel filtro corrente
  - analytics supporto filtrabili per `delivery_status` e `ticket_linked`

Criterio di successo globale:

- risposta assistant piu rapida e piu prevedibile
- codice meno concentrato in pochi file monolitici
- backlog supporto leggibile come flusso prodotto, non solo come lista richieste

---

## M5.1 — Core Assistant Performance

### Problema

Oggi il flusso chat:

- usa pseudo-streaming lato backend
- invoca il router semantico LLM troppo presto
- usa retrieval documentale ancora molto basato su FTS puro

Questo produce:

- latenza percepita alta
- costo non necessario sulle domande semplici
- no-match e fallback non sempre consistenti

### Obiettivi

- streaming reale token-by-token dal provider
- router a due livelli:
  - livello 1 deterministic fast-path
  - livello 2 semantic router LLM solo quando serve
- retrieval docs con ranking piu robusto

### Deliverable

#### Backend

- `routes/chat.py`
  - endpoint stream con vero forwarding dei delta dal client OpenAI-compatible
  - fallback sync solo in caso di stream non disponibile
- `services/orchestrator.py`
  - introdurre pipeline esplicita:
    - `route_question`
    - `authorize_capability`
    - `resolve_tool`
    - `retrieve_docs`
    - `compose_answer`
    - `persist_turn`
- `services/semantic_router.py`
  - usare LLM solo dopo fast-path deterministic
- nuovo modulo suggerito:
  - `services/question_router.py`
    - regole cheap per casi ovvi:
      - access request
      - external live
      - action request
      - docs-only ovvio
      - module hint ovvio
- `services/rag.py`
  - boosting per:
    - `context_article`
    - `module_key`
    - `page_path`
    - match su identificativi e token rari
  - opzionale seconda fase:
    - rerank leggero top N con LLM piccolo o heuristics

#### Frontend

- `useWikiChat.ts`
  - consumare stream reale
  - gestire meglio timeout, retry e abort
  - esporre metriche UI minime:
    - `time_to_first_chunk`
    - `stream_completed`
- `WikiWidget.tsx` e `WikiPage.tsx`
  - mostrare stato piu chiaro:
    - `sto cercando documentazione`
    - `sto verificando dati live`

### KPI

- riduzione `time_to_first_token`
- riduzione `avg_latency_ms` lato telemetry
- riduzione fallback sync dopo stream

### Test

- test backend su stream reale con mock chunk provider
- test frontend su parser stream e stato UI di avanzamento
- benchmark minimo su router deterministic vs router semantic

---

## M5.2 — Refactor Strutturale

### Problema

Il modulo funziona, ma alcune superfici sono ormai troppo dense:

- `backend/app/modules/wiki/services/orchestrator.py`
- `backend/app/modules/wiki/routes/requests.py`
- `frontend/src/features/wiki/WikiRequestsPage.tsx`
- `frontend/src/features/wiki/request-support.ts`

Questo rende piu difficile:

- estendere i flussi senza regressioni
- testare in isolamento
- delegare lavoro a piu persone

### Obiettivi

- ridurre file monolitici
- rendere espliciti i boundary tra orchestration, persistence, analytics e UI
- aumentare testabilita unitaria delle parti critiche

### Deliverable

#### Backend

- estrarre da `orchestrator.py`:
  - `routing_service.py`
  - `execution_service.py`
  - `persistence_service.py`
  - `audit_service.py` o equivalente
- estrarre da `routes/requests.py`:
  - service per artifact storage
  - service per workflow richieste
  - service per duplicate/canonical management
- centralizzare enum e costanti shared:
  - request status
  - request type
  - severity
  - priority
  - fallback reasons

#### Frontend

- spezzare `WikiRequestsPage.tsx` in sotto-componenti:
  - `WikiRequestsFilters`
  - `WikiRequestsList`
  - `WikiRequestDetailPanel`
  - `WikiRequestArtifactsPanel`
  - `WikiRequestDeliveryPanel`
- spezzare `request-support.ts` in:
  - payload builder
  - artifact capture
  - snapshot extractors
  - privacy sanitization
- introdurre tipi dedicati per snapshot admin renderizzati

### KPI

- riduzione line count dei file top critici
- coverage frontend migliore sul pannello admin
- minor numero di test end-to-end necessari per coprire la stessa logica

### Test

- test unit per i nuovi servizi backend estratti
- test unit per i panel frontend separati
- smoke test superfici esistenti dopo refactor

---

## M5.3 — Product Intelligence e Delivery Bridge

### Problema

Le analytics supporto sono gia utili, ma:

- il clustering e ancora runtime/euristico
- non esiste ancora un ponte nativo col backlog reale
- la triage intelligence e ancora quasi tutta manuale

### Obiettivi

- cluster persistiti e stabili nel tempo
- collegamento esplicito tra richiesta wiki e ticket di delivery
- basi per suggerimenti assistiti admin

### Deliverable

#### Data model

- nuova entita suggerita:
  - `wiki_request_clusters`
- nuova tabella suggerita:
  - `wiki_request_cluster_members`
- estensioni su `wiki_requests`:
  - `external_ticket_key`
  - `external_ticket_url`
  - `delivery_status`
  - `delivery_notes`

#### Backend

- job o comando admin per:
  - assegnazione cluster iniziale
  - ricalcolo cluster
  - storico split/merge cluster
- endpoint admin:
  - collega ticket esterno
  - aggiorna stato delivery
  - lista cluster persistiti
- suggester amministrativo fase 1:
  - severita suggerita
  - priorita suggerita
  - duplicate cluster suggerito

#### Frontend

- `WikiRequestsPage`
  - sezione `Delivery`
  - form rapido per ticket esterno
  - vista cluster persistito
- `WikiSupportAnalyticsPage`
  - distinzione tra:
    - cluster runtime
    - cluster persistiti
  - indicatori per casi collegati a delivery

### KPI

- percentuale richieste collegate a ticket reale
- stabilita cluster nel tempo
- riduzione duplicati non collegati

### Test

- backend API per cluster persistiti e bridge esterno
- analytics regression test
- frontend admin test su linking ticket e stato delivery

---

## Sequenza Sprint Consigliata

### Sprint 1

- streaming reale backend/frontend
- deterministic fast-path router
- telemetry su `time_to_first_chunk`

### Sprint 2

- refactor orchestrator
- refactor `WikiRequestsPage`
- refactor `request-support.ts`

### Sprint 3

- cluster persistiti schema + migration
- admin UI cluster
- link ticket esterno manuale

### Sprint 4

- suggerimenti assistiti admin
- reporting su delivery bridge
- hardening finale test e docs

---

## Rischi

### 1. Refactor troppo ampio insieme alla delivery

Mitigazione:
- non mischiare streaming, refactor e cluster nello stesso sprint

### 2. Semantic router ancora troppo centrale

Mitigazione:
- introdurre fast-path deterministic prima di toccare il prompt del router

### 3. Cluster persistiti troppo fragili

Mitigazione:
- partire con cluster `assistiti` e revisionabili da admin
- non automatizzare merge irreversibili nella prima iterazione

### 4. UI admin ancora troppo accoppiata

Mitigazione:
- prima separare i panel
- poi aggiungere nuove funzionalita sul pannello decomposto

---

## Definition of Done

`M5` puo considerarsi chiuso quando:

- la chat Wiki usa stream reale in produzione
- il router deterministic copre i casi ovvi senza chiamare sempre il modello
- `orchestrator.py` e `WikiRequestsPage.tsx` non sono piu il centro di troppe responsabilita
- esiste un cluster persistito leggibile e gestibile da admin
- una richiesta Wiki puo essere collegata a un ticket esterno reale
- docs, test e telemetry risultano aggiornati sul nuovo assetto
