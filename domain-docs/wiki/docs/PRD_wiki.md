# PRD — GAIA Wiki Agent
## Milestone 9: Assistente LLM integrato con knowledge base documentale

> Documento di prodotto per il modulo `wiki`.
> Implementazione tecnica dettagliata in `IMPLEMENTATION_PLAN_wiki.md`.
> Prompt operativo per Codex in `PROMPT_CODEX_wiki.md`.

---

## 1. Visione

Il modulo **Wiki Agent** aggiunge a GAIA un assistente LLM sempre disponibile, capace di rispondere a domande sul sistema, sulla documentazione tecnica, sullo stato di implementazione e sulle funzionalità esistenti. L'agente è alimentato da GPT-4o via OpenAI API, con un pipeline RAG che indicizza i documenti del progetto.

---

## 2. Obiettivi di prodotto

| Priorità | Obiettivo |
|---|---|
| P0 | Widget chat floating presente su ogni pagina dell'applicazione |
| P0 | Risposta contestuale basata sui documenti GAIA indicizzati |
| P0 | Pagina `/wiki` dedicata con browser degli articoli e chat |
| P1 | Salvataggio richieste utente (feature request) nel database |
| P1 | Citazione delle fonti nelle risposte (file + sezione) |
| P2 | Re-indicizzazione manuale via endpoint admin |
| P2 | Elenco e gestione richieste per admin |

---

## 3. Utenti target

- **Utenti operativi** — vogliono sapere come usare una funzione senza leggere i docs
- **Sviluppatori** — vogliono capire l'architettura, le API, le convenzioni
- **Admin** — vogliono vedere le richieste utente non soddisfatte per pianificare le milestone

---

## 4. Funzionalità

### 4.1 Widget floating (presente su ogni pagina)

- Pulsante circolare in basso a destra (`fixed bottom-6 right-6`)
- Click apre overlay chat (non modale, non blocca il contenuto)
- Chat con storico della sessione (non persistito lato server, solo in memoria React)
- Input testo + invio con Enter o pulsante
- Mostra spinner durante la risposta
- Ogni risposta include le fonti (file citato)
- Pulsante "Segnala come richiesta" se la risposta è "non trovato"

### 4.2 Pagina `/wiki`

- Sidebar sinistra: lista degli articoli indicizzati, raggruppati per categoria
- Area centrale: contenuto dell'articolo selezionato (testo chunks)
- Chat panel destro: chat contestuale all'articolo visualizzato
- La chat pre-popola il contesto con l'articolo corrente

### 4.3 Pipeline RAG

- **Documenti indicizzati**: tutti i file `.md` in `docs/`, `docs/wiki/`, `domain-docs/`, `progress/`
- **Chunking**: divisione per sezioni (heading `##`) con overlap di 200 caratteri
- **Retrieval**: PostgreSQL Full-Text Search (`to_tsvector` + GIN index) — nessuna API esterna
- **LLM**: `gpt-5.4-mini` via **codex-lb** (proxy OpenAI-compatibile locale, porta 2455)

### 4.4 Salvataggio richieste

- Se l'utente chiede una feature non implementata, può cliccare "Registra richiesta"
- La richiesta viene salvata in `wiki_requests` con stato `pending`
- Admin può vedere la lista in `/wiki/requests` (endpoint protetto)
- Workflow operativo richieste:
  - `new`
  - `triaged`
  - `investigating`
  - `waiting_user`
  - `planned`
  - `resolved`
  - `duplicate`
  - `rejected`
- Ogni richiesta può avere:
  - `priority`: `low` / `medium` / `high` / `urgent`
  - `assigned_to`: operatore GAIA assegnato alla presa in carico
  - `admin_notes`: contesto operativo, ticket o decisione
- `severity`: `low` / `medium` / `high` / `critical`
- Campi contestuali strutturati:
  - `request_type`
  - `module_key`
  - `page_path`
  - `source_channel`
  - `impact_scope`
  - `conversation_id`
  - `context_article`
  - `context_entity_key`
  - `desired_outcome`
  - `observed_behavior`
  - `expected_behavior`
- La pagina admin consente filtro, presa in carico, aggiornamento inline e timeline eventi del caso

### 4.5 Supporto Wiki dedicato

- Pagina utente: `/wiki/support`
- Scopo: trasformare domande, anomalie o richieste di prodotto in casi strutturati
- Ingressi utente principali:
  - `Supporto operativo`
  - `Problema / anomalia`
  - `Nuova funzionalità`
  - `Problema di accesso`
  - `Problema dati`
  - `Altro`
- Il widget e la pagina Wiki non mostrano più solo `Registra come richiesta`, ma:
  - `Chiedi supporto`
  - `Segnala problema`
  - `Richiedi funzionalità`
  - `Apri supporto completo`
- Il flusso precompila automaticamente il contesto:
  - modulo GAIA
  - pagina corrente
  - conversazione Wiki sorgente
  - eventuale articolo/documento di contesto
  - risposta agente già vista dall'utente

### 4.6 Inbox supporto admin

- Pagina dedicata: `/wiki/support/inbox`
- Vista focalizzata sui casi non puramente “feature request”
- Perimetro:
  - `help_request`
  - `bug_report`
  - `access_issue`
  - `data_issue`
  - `other_request`
- L'admin vede:
  - severità
  - priorità
  - assegnatario
  - modulo e pagina
  - timeline degli eventi
  - note operative

### 4.7 Timeline eventi richieste

- Nuova tabella: `wiki_request_events`
- Audit append-only generato dal backend sui casi Wiki
- Eventi registrati:
  - `created`
  - `status_changed`
  - `priority_changed`
  - `severity_changed`
  - `assignee_changed`
  - `notes_updated`
- La timeline viene esposta lato admin e aiuta triage, handoff e audit operativo

### 4.8 Router semantico e guardrail strutturali

- Il Wiki usa un **semantic router multilingua** prima del retrieval
- La domanda viene:
  - classificata per capacità (`docs_supported`, `internal_live_data`, `internal_explanation`, `unsupported_*`, `out_of_scope`)
  - normalizzata in italiano per retrieval e tool matching
  - associata a un `module_hint` coerente con i moduli GAIA
- Le richieste fuori perimetro vengono bloccate in modo strutturale, non keyword-only:
  - news live / meteo / mercati / fonti esterne
  - concessione accessi o sblocco risorse
  - azioni operative o modifiche di stato
- La risposta finale viene restituita nella lingua dell'utente quando il router entra in blocco o fallback

### 4.9 Tool live interni

- Oltre alla documentazione, il Wiki può interrogare tool read-only interni per risposte `live_data`
- Copertura iniziale:
  - `accessi`
  - `catasto`
  - `ruolo`
  - `riordino`
  - `operazioni`
  - `rete`
- Per il modulo `rete` sono disponibili almeno:
  - riepilogo dashboard rete
  - riepilogo firewall Sophos
  - lookup dispositivo rete per IP o identificatore riconoscibile

### 4.10 Console amministrativa Wiki

- La sezione admin del modulo Wiki espone viste operative dedicate:
  - `/wiki/requests`
  - `/wiki/requests/:id`
  - `/wiki/support/inbox`
  - `/wiki/support/analytics`
  - `/wiki/audit`
  - `/wiki/conversations/analytics`
  - `/wiki/telemetry`
- `Richieste`:
  - backlog richieste registrate dal widget
  - filtri per stato, categoria, tipo richiesta, priorità, severità e assegnatario
  - aggiornamento inline di `status`, `priority`, `severity`, `assigned_to`, `admin_notes`
  - timeline del caso con audit eventi
- `Dettaglio richiesta`:
  - URL stabile per ogni caso
  - gestione operativa condivisibile tra admin
  - stessa timeline ed editing del backlog con focus su un solo item
- `Analytics supporto`:
  - trend richieste, anomalie, problemi accesso/dati e feature request
  - lettura per modulo, severità, impatto, assegnatario e pagina applicativa
  - serie storiche per backlog aperto, risolti, urgenze e bisogni prodotto
- `Audit`:
  - consultazione delle tool call del Wiki Agent
  - lettura rapida di mode, intent, modulo, successo/failure e fallback
  - filtri rapidi e pannello dettaglio per analisi operativa
- `Analytics conversazioni`:
  - trend backlog dei thread Wiki
  - breakdown per stato, priorità, owner ed eventi workflow
  - KPI su tempi review/resolve e pressione sul backlog
- `Telemetria`:
  - KPI storici sul comportamento del Wiki Agent
  - top tool, moduli, fallback reason e trend giornalieri
  - retention e stato scheduler per le metriche aggregate

### 4.11 Analytics supporto Wiki

- Pagina dedicata: `/wiki/support/analytics`
- Scopo: trasformare richieste e segnalazioni in insight operativi per admin e prodotto
- KPI chiave:
  - richieste totali
  - richieste aperte
  - richieste assegnate
  - richieste risolte
  - urgenze
  - severità alte / critiche
  - richieste duplicate
  - casi canonici
  - richieste riaperte dall’utente
  - richieste nate da `no_match`
  - richieste nate da `guardrail`
  - richieste nate in `docs_only`
- Breakdown principali:
  - top `request_type`
  - top moduli GAIA coinvolti
  - top stati workflow
  - top severità e priorità
  - top pagine applicative
  - top assegnatari e autori
  - top `impact_scope`
  - top `source_channel`
- Serie storiche:
  - nuove richieste per giorno
  - casi risolti per giorno
  - pressione backlog aperto
  - feature richieste nel tempo
  - bug / anomalie nel tempo
  - urgenze nel tempo

### 4.14 Cluster supporto e duplicate pressure

- La dashboard `/wiki/support/analytics` espone anche cluster pragmatici di richieste simili.
- Il clustering non usa un modello ML esterno in questa milestone:
  - privilegia il `canonical_request_id` quando esiste
  - altrimenti usa una chiave semantica leggera basata su:
    - `request_type`
    - `module_key`
    - `page_path`
    - token significativi del testo utente
- Ogni cluster mostra:
  - volume totale casi
  - casi ancora aperti
  - numero duplicati
  - utenti impattati
  - numero casi canonici
  - esempi reali di richieste nel gruppo
- Obiettivo:
  - capire dove il prodotto genera frizioni ripetute
  - stimare la `duplicate pressure`
  - evidenziare aree dove il Wiki non risolve da solo il bisogno utente

### 4.15 Insight automatici per admin e prodotto

- La dashboard `/wiki/support/analytics` espone una sezione `Insight automatici`.
- Gli insight sono una sintesi operativa dei segnali, non una semplice replica dei KPI.
- Prima versione implementata:
  - `duplicate_pressure`
  - `wiki_coverage_gap`
  - `docs_only_pressure`
  - `guardrail_pressure`
  - `negative_feedback_loop`
  - `feature_demand`
  - `bug_hotspot`
  - `top_cluster`
- Ogni insight contiene:
  - livello severità (`info`, `warning`, `critical`)
  - descrizione del segnale
  - metrica sintetica
  - `action_hint` per l’admin o il prodotto
  - eventuale `related_key` (modulo, pagina o cluster)
- Obiettivo:
  - trasformare i dati del supporto in priorità operative leggibili
  - capire rapidamente dove migliorare documentazione, tool live o prodotto

### 4.12 Deduplica e caso canonico

- Le richieste Wiki possono essere confrontate con casi simili già aperti o chiusi
- Il backend calcola un segnale di similarità pragmatica su:
  - `request_type`
  - `module_key`
  - `page_path`
  - `context_entity_key`
  - testo normalizzato della richiesta
- La console admin mostra una sezione `Deduplica casi simili` nel dettaglio richiesta
- L'admin può:
  - aprire i casi suggeriti
  - marcare la richiesta corrente come `duplicate`
  - collegarla a un `canonical_request_id`
- Quando un caso viene marcato come duplicato:
  - la richiesta assume stato `duplicate`
  - viene salvato il riferimento al caso canonico
  - la timeline registra:
    - `marked_duplicate`
    - `duplicate_linked`
- La console admin mostra anche i `duplicati collegati` al caso canonico:
  - elenco del gruppo già accorpato
  - `family_size`
  - numero di utenti coinvolti
  - ultimo caso registrato nel gruppo
  - possibilità di `sganciare` un duplicato dal canonico
  - possibilità di promuovere un altro caso a `nuovo canonico`
- Lo sgancio di un duplicato:
  - rimuove `canonical_request_id`
  - riporta il caso a `triaged` se era in stato `duplicate`
  - registra evento `duplicate_unlinked`
- Il backend espone una vista famiglia dedicata:
  - `GET /wiki/requests/{id}/family`
  - restituisce il caso canonico attuale e i duplicati collegati
- L'admin può promuovere un duplicato come nuovo canonico con:
  - `POST /wiki/requests/{id}/make-canonical`
- Quando cambia il canonico:
  - il caso promosso diventa il riferimento del gruppo
  - il vecchio canonico viene declassato a `duplicate`
  - tutti i duplicati collegati vengono riallineati al nuovo canonico
  - la timeline registra:
    - `canonical_promoted`
    - `canonical_demoted`
    - `canonical_reassigned`

### 4.13 Inbox utente e feedback loop

- La pagina `/wiki/support` non è solo form di inserimento, ma anche inbox personale delle richieste aperte dall’utente.
- Il backend espone:
  - `GET /wiki/requests/mine`
  - `GET /wiki/requests/mine/summary`
  - `POST /wiki/requests/{id}/mark-viewed`
  - `POST /wiki/requests/{id}/reopen`
  - `PATCH /wiki/requests/{id}/feedback`
- Il riepilogo personale include:
  - numero totale richieste
  - richieste aperte
  - aggiornamenti admin non letti
  - casi `waiting_user`
  - casi `resolved` in attesa di feedback
- L’utente vede per ogni caso:
  - stato attuale
  - eventuale messaggio admin / risoluzione
  - badge `Nuovo aggiornamento`
  - possibilità di lasciare feedback finale
  - possibilità di riaprire il caso con motivazione
- La riapertura di un caso:
  - sposta lo stato a `investigating`
  - sgancia il caso dal canonico se era `duplicate`
  - registra evento `reopened_by_user`
  - trasforma il feedback implicito in `not_helpful` se il caso era già chiuso
    - `duplicate_linked`
  - il backlog resta leggibile senza perdere il contesto originale dell'utente

### 4.13 Notifiche utente e feedback finale

- Ogni richiesta Wiki mantiene un piccolo ciclo di comunicazione utente-admin
- Il backend salva:
  - `resolution_message`: messaggio sintetico rivolto all'utente
  - `last_admin_update_at`: ultimo aggiornamento amministrativo visibile all'utente
  - `user_last_viewed_at`: ultima presa visione lato utente
  - `user_feedback_rating`: `helpful` / `not_helpful`
  - `user_feedback_notes`
  - `user_feedback_submitted_at`
- La pagina utente `/wiki/support` diventa anche inbox personale:
  - badge `aggiornamenti da leggere`
  - messaggio admin o di risoluzione
  - note operative visibili all'utente
  - invio feedback finale sul caso
- Endpoint principali:
  - `POST /wiki/requests/{id}/mark-viewed`
  - `PATCH /wiki/requests/{id}/feedback`
- La console admin delle richieste espone:
  - `Messaggio per l'utente`
  - visibilità del feedback ricevuto
  - timeline evento `user_feedback_submitted`
- Nessuna nuova tabella dedicata: la vista viene derivata da `wiki_requests`

---

## 5. Architettura tecnica

```
Frontend (Next.js)
├── components/layout/app-shell.tsx  ← WikiWidget iniettato qui
├── features/wiki/
│   ├── WikiWidget.tsx               ← floating bubble + chat overlay
│   ├── WikiPage.tsx                 ← pagina /wiki
│   ├── WikiChat.tsx                 ← componente chat riusabile
│   ├── useWikiChat.ts               ← hook stato chat
│   └── types.ts                     ← tipi TypeScript
└── app/wiki/
    ├── layout.tsx
    └── page.tsx

Backend (FastAPI)
└── modules/wiki/
    ├── router.py
    ├── models.py                    ← WikiChunk, WikiRequest
    ├── schemas.py
    ├── routes/
    │   ├── chat.py                  ← POST /wiki/chat
    │   ├── articles.py              ← GET /wiki/articles
    │   └── requests.py              ← POST/GET/PATCH /wiki/requests + assignees
    └── services/
        ├── rag.py                   ← retrieval + completion
        ├── indexer.py               ← document parsing + embedding
        └── openai_client.py         ← wrapper OpenAI API
        ├── semantic_router.py       ← routing multilingua + capability classification
        ├── guardrails.py            ← blocchi strutturali pre/post retrieval
        ├── tool_registry*.py        ← tool interni live per modulo
        ├── conversation_metrics.py  ← metriche backlog thread Wiki
        └── telemetry.py             ← metriche aggregate audit/fallback/mode
```

---

## 6. Variabili d'ambiente richieste

| Variabile | Descrizione | Default |
|---|---|---|
| `CODEX_LB_URL` | URL proxy codex-lb | `http://host.docker.internal:2455/v1` |
| `CODEX_LB_API_KEY` | API key (dummy, auth locale disabilitata) | `sk-codex-lb-local` |
| `WIKI_CHAT_MODEL` | Modello chat su codex-lb | `gpt-5.4-mini` |
| `WIKI_DOCS_ROOT` | Path root documentazione dentro container | `/app` |
| `WIKI_TOP_K` | Numero chunks per retrieval | `5` |

---

## 7. Requisiti non funzionali

- Latenza risposta chat < 5s (P50)
- Re-indicizzazione completa < 30s (nessuna API esterna, solo PG FTS)
- Widget non deve bloccare la navigazione (overlay, non modale)
- Nessun dato sensibile incluso nei chunks (no credenziali, no token)
- Fallback graceful se codex-lb non raggiungibile (widget mostra errore 503)
- Nessuna richiesta di accesso, modifica o news esterne deve produrre una risposta “inventata”
- Le richieste multilingua devono essere instradate sullo stesso perimetro funzionale della variante italiana

---

## 8. Metriche di successo

- Almeno 80% delle domande sui documenti riceve una risposta rilevante
- Meno di 5% di timeout sulla chat
- Almeno 3 richieste utente registrate entro il primo mese di deploy
