# IMPLEMENTATION PLAN — GAIA Wiki Live Agent
## Milestone 10 proposta: documentazione + dati live + logiche applicative

> Obiettivo: evolvere il modulo `wiki` da assistente RAG documentale a assistente operativo capace di rispondere anche su dati live e logiche del sistema, senza esporre accesso SQL libero agli utenti.
> Stato attuale: Fasi 1-3 completate e verificate sullo stato corrente del repository al 2026-06-23
> Evoluzione architetturale proposta per capability registry, slot filling e operational wiki persistente: `GAIA_OPERATIONAL_WIKI_ARCHITECTURE.md`

---

## 1. Obiettivo del milestone

Il Wiki Agent attuale risponde solo usando documentazione indicizzata.
Il milestone successivo introduce un **tool layer read-only e autorizzato** che permette al modello di:

- leggere KPI e lookup live dai moduli GAIA
- spiegare regole applicative e stati workflow
- distinguere chiaramente tra risposta documentale e risposta basata su dati runtime
- rispettare ruolo utente, modulo abilitato e section permissions

Non e previsto in questo milestone:

- esecuzione di SQL generato liberamente dal modello
- modifiche ai dati applicativi
- accesso diretto a credenziali, segreti, token o raw table dump

---

## 2. Principi architetturali

### 2.1 No SQL libero

L'assistente non deve tradurre prompt utente in SQL arbitrario da eseguire sul database.
Le interrogazioni live passano solo da:

- servizi applicativi backend esistenti
- query curate e tipizzate
- viste read-only whitelistate, se davvero necessarie

### 2.2 Tool-first, non DB-first

Il modello decide se:

- rispondere da documentazione
- chiamare un tool live
- combinare documentazione + dato live

Il dato applicativo deve restare dietro un boundary controllato.

### 2.3 Enforcement autorizzativo centralizzato

Ogni tool deve verificare:

- utente autenticato
- ruolo (`admin`, `super_admin`, `reviewer`, `user`)
- modulo abilitato (`enabled_modules`)
- `section permissions` quando la domanda tocca aree protette

### 2.4 Provenienza esplicita della risposta

Ogni risposta deve poter indicare da dove arriva:

- `docs`: documentazione indicizzata
- `live_data`: API/query runtime
- `logic`: regole applicative note
- `inference`: deduzione dell'assistente, sempre dichiarata come tale

---

## 3. Architettura target

```text
Frontend Wiki Widget / Wiki Page
    |
    v
POST /api/wiki/chat
    |
    v
Wiki Orchestrator
├── Intent classifier
├── Policy guard
├── Docs retriever (RAG esistente)
├── Tool router
│   ├── Catasto tools
│   ├── Operazioni tools
│   ├── Utenze tools
│   ├── NAS Control tools
│   ├── Ruolo tools
│   └── System logic tools
└── Response composer
    |
    v
Risposta finale con evidenze e provenance
```

---

## 4. Evoluzione backend proposta

### 4.1 Nuovi file backend

```text
backend/app/modules/wiki/
├── services/
│   ├── orchestrator.py              ← entrypoint chat docs + tools
│   ├── intent_classifier.py         ← docs vs live_data vs logic
│   ├── tool_registry.py             ← aggregatore registry per dominio
│   ├── tool_registry_common.py      ← helper condivisi matcher/UUID/pattern
│   ├── tool_registry_accessi.py     ← catalogo e handler accessi
│   ├── tool_registry_catasto.py     ← catalogo e handler catasto
│   ├── tool_registry_operazioni.py  ← catalogo e handler operazioni
│   ├── tool_registry_operazioni_analytics.py
│   ├── tool_registry_operazioni_workflow.py
│   ├── tool_registry_operazioni_technical.py
│   ├── tool_registry_riordino.py    ← catalogo e handler riordino
│   ├── tool_registry_ruolo_utenze.py← catalogo e handler ruolo/utenze
│   ├── policy.py                    ← enforcement modulo/ruolo/sezioni
│   ├── response_composer.py         ← risposta finale + provenance
│   ├── rag.py                       ← resta il path documentale esistente
│   ├── logic_catalog.py             ← facciata catalogo regole curate
│   ├── logic_catalog_accessi.py
│   ├── logic_catalog_catasto_ruolo.py
│   ├── logic_catalog_operazioni.py
│   ├── logic_catalog_operazioni_analytics.py
│   ├── logic_catalog_operazioni_workflow.py
│   ├── logic_catalog_operazioni_technical.py
│   ├── system_logic.py              ← facciata spiegazioni workflow/regole
│   ├── system_logic_accessi_catasto_ruolo.py
│   ├── system_logic_riordino.py
│   ├── system_logic_operazioni.py
│   ├── system_logic_operazioni_analytics.py
│   ├── system_logic_operazioni_workflow.py
│   ├── system_logic_operazioni_technical.py
│   ├── audit_read_models.py         ← read model filtri/proiezioni/aggregati audit
│   ├── telemetry.py                 ← snapshot persistenti e serie storiche Wiki
│   ├── telemetry_scheduler.py       ← job APScheduler dedicato alla telemetria Wiki
│   ├── accessi_read_models.py       ← read model live curati per accessi
│   ├── catasto_read_models.py       ← read model live curati per catasto
│   ├── ruolo_utenze_read_models.py  ← read model live curati per ruolo/utenze
│   └── operazioni_analytics_read_models.py ← read model live riusabile per analytics Operazioni
├── schemas.py                       ← nuovi schema tool call / provenance
└── routes/
    ├── chat.py                      ← delega a orchestrator
    ├── audit.py                     ← audit log + summary admin
    └── telemetry.py                 ← KPI storici e serie admin
```

### 4.2 Refactor minimo del flow chat

Stato attuale:

- `routes/chat.py` chiama `answer_question(...)`
- `answer_question(...)` usa solo RAG documentale

Stato target:

- `routes/chat.py` chiama `answer_with_orchestration(...)`
- l'orchestrator decide il path
- il path documentale continua a riusare `rag.py`

Pseudo-flow:

```python
def answer_with_orchestration(db, current_user, question, context_article=None):
    intent = classify_intent(question)
    allowed_tools = get_allowed_tools(current_user)

    if intent == "docs_only":
        return answer_question(db, question, context_article)

    if intent in {"live_data", "logic", "hybrid"}:
        tool_result = maybe_call_tool(db, current_user, question, allowed_tools)
        docs_result = maybe_retrieve_docs(db, question, context_article, intent)
        return compose_answer(question, tool_result, docs_result)
```

---

## 5. Schemi API proposti

### 5.1 Evoluzione `WikiChatResponse`

Schema attuale:

- `answer`
- `sources`
- `found`

Schema proposto:

```ts
type WikiEvidenceType = "docs" | "live_data" | "logic" | "inference";

interface WikiEvidence {
  type: WikiEvidenceType;
  label: string;
  source_key: string;
  excerpt?: string | null;
  payload?: Record<string, unknown> | null;
}

interface WikiToolCallSummary {
  tool_name: string;
  success: boolean;
  redacted: boolean;
}

interface WikiChatResponse {
  answer: string;
  sources: WikiChunkSource[];
  found: boolean;
  evidences?: WikiEvidence[];
  tool_calls?: WikiToolCallSummary[];
  mode?: "docs_only" | "live_data" | "logic" | "hybrid";
}
```

### 5.2 Nessun endpoint pubblico per SQL

Non introdurre endpoint tipo:

- `/wiki/sql`
- `/wiki/query`
- `/wiki/run`

Gli endpoint restano di dominio wiki, ma internamente usano servizi e tool controllati.

---

## 6. Tool MVP raccomandati

### 6.1 Catasto

- `get_catasto_dashboard_summary(anno?: int)`
- `find_particella_by_id(particella_id: int)`
- `search_catasto_anomalie(tipo?: str, limit?: int)`
- `explain_catasto_anomaly_rule(tipo: str)`

Use case:

- "quante anomalie aperte ci sono?"
- "cosa significa VAL-05-particella_assente?"
- "mostrami i dati della particella 12345"

### 6.2 NAS Control / Accessi

- `get_nas_dashboard_summary()`
- `find_nas_user(username: str)`
- `get_share_access_summary(share_id: int | path: str)`

Use case:

- "quanti deny sono attivi?"
- "chi accede a questa share?"
- "l'utente mario.rossi ha accesso a contabilita?"

### 6.3 Ruolo

- `get_ruolo_dashboard_summary(anno?: int)`
- `find_ruolo_subject(codice_fiscale?: str, nominativo?: str)`
- `explain_ruolo_status(subject_id: int)`

### 6.4 Utenze

- `get_utenze_stats()`
- `find_subject_by_id(subject_id: int)`
- `find_subject_by_cf(cf: str)`

### 6.5 Operazioni

- `get_operazioni_dashboard_summary()`
- `find_vehicle_by_id(vehicle_id: int)`
- `find_operator_by_name(query: str)`

### 6.6 System logic

Tool senza accesso DB libero, basati su regole curate:

- `explain_workflow_transition(module_key: str, state: str, event?: str)`
- `explain_permission_rule(section_key: str)`
- `explain_module_access(module_key: str, role: str)`
- `explain_data_metric(metric_key: str)`

Questi tool servono per domande del tipo:

- "perche vedo questo blocco?"
- "come viene calcolato questo KPI?"
- "chi puo accedere a questa sezione?"

---

## 7. Fonti logiche applicative

Le logiche non devono essere inferite solo dal codice raw ad ogni richiesta.
Serve una knowledge layer curata.

### 7.1 Fonti iniziali

- enum backend
- schemi Pydantic
- service layer di dominio
- docs esistenti
- test backend significativi

### 7.2 Materializzazione consigliata

Introdurre un catalogo di regole applicative, ad esempio:

```text
backend/app/modules/wiki/logic_catalog/
├── catasto_rules.yaml
├── operazioni_rules.yaml
├── ruolo_rules.yaml
├── accessi_rules.yaml
└── platform_rules.yaml
```

Ogni file contiene:

- `rule_key`
- modulo
- descrizione naturale
- input attesi
- servizi o campi coinvolti
- note autorizzative

Questo evita di far dipendere la spiegazione delle regole da parsing fragile del codice.

---

## 8. Enforcement autorizzativo

### 8.1 Livello minimo per ogni tool

Ogni tool dichiara metadati:

```python
@dataclass
class WikiToolMeta:
    name: str
    module_key: str | None
    required_sections: list[str]
    allowed_roles: list[str] | None
    read_only: bool = True
```

### 8.2 Regole

- se il modulo non e abilitato per l'utente: tool non disponibile
- se la section non e concessa: tool non disponibile
- se il ruolo non e ammesso: tool non disponibile
- se il tool fallisce su autorizzazione: niente fallback a dati grezzi

### 8.3 Audit

Loggare ogni tool call con:

- utente
- tool invocato
- outcome
- durata
- eventuale denial

Tabella proposta futura:

- `wiki_tool_call_logs`

Campi:

- `id`
- `user_id`
- `tool_name`
- `question`
- `status`
- `latency_ms`
- `created_at`

---

## 9. Prompting e orchestration

### 9.1 System prompt aggiornato

L'assistente deve ricevere istruzioni esplicite:

- usa i documenti per spiegazioni generali
- usa i tool solo quando servono dati live o regole applicative
- non inventare risultati di query non eseguite
- dichiara se una parte della risposta e inferenza
- non restituire dati oltre i permessi utente

### 9.2 Strategia semplice MVP

Invece di partire con function-calling complesso, il MVP puo usare un router deterministico:

- regex/keyword per domini chiari
- pattern su metriche note
- fallback a RAG

Esempio:

- "quante", "numero", "totale", "stato attuale" → probabile `live_data`
- "come funziona", "perche", "cosa significa" → probabile `docs` o `logic`

Poi, in una fase successiva, si passa a tool calling nativo.

---

## 10. Frontend MVP

Il frontend wiki attuale puo restare quasi invariato.

### 10.1 Estensioni minime

- badge modalità risposta: `Docs`, `Live`, `Logic`, `Hybrid`
- lista evidenze sotto la risposta
- eventuale icona "dato live" per tool call avvenuta

### 10.2 Nessun nuovo flusso utente obbligatorio

L'utente continua a scrivere in chat naturale:

- "quante anomalie catasto ci sono oggi?"
- "come viene calcolato questo indicatore?"
- "chi puo vedere accessi.users?"

---

## 11. Piano implementativo per fasi

### Fase 1 — MVP read-only e sicuro

- [x] Creare `orchestrator.py`
- [x] Aggiungere `mode`, `evidences`, `tool_calls` a `WikiChatResponse`
- [x] Implementare `tool_registry.py`
- [x] Implementare 5 tool read-only:
  - [x] `get_catasto_dashboard_summary`
  - [x] `get_nas_dashboard_summary`
  - [x] `get_ruolo_dashboard_summary`
  - [x] `get_utenze_stats`
  - [x] `get_operazioni_dashboard_summary`
- [x] Implementare `policy.py`
- [x] Test backend iniziali per orchestrazione e denial su modulo non abilitato
- [x] Estendere UI widget/pagina wiki con provenance minima
- [x] Raffinare il classifier oltre le keyword base
- [x] Aggiungere lookup read-only mirati oltre ai soli summary

### Fase 2 — Logiche applicative curate

- [x] Introdurre un primo tool `logic` su permessi `accessi`
- [x] Estrarre un primo `logic_catalog.py` dedicato
- [x] Aggiungere spiegazioni logiche curate per metriche `catasto`
- [x] Aggiungere spiegazioni logiche curate per metriche `ruolo`
- [x] Implementare `system_logic.py`
- [x] Aggiungere spiegazioni workflow per pratiche `riordino`
- [x] Aggiungere spiegazioni workflow per case `operazioni`
- [x] Aggiungere spiegazioni workflow per assegnazioni mezzo `operazioni`
- [x] Aggiungere spiegazioni workflow per manutenzioni `operazioni`
- [x] Aggiungere spiegazioni workflow per sessioni d'uso `operazioni`
- [x] Aggiungere spiegazioni workflow per attività `operazioni`
- [x] Aggiungere spiegazioni workflow per approvazioni attività `operazioni`
- [x] Aggiungere spiegazioni workflow per fuel log `operazioni`
- [x] Aggiungere spiegazioni workflow per transazioni non risolte `operazioni`
- [x] Aggiungere spiegazioni workflow per anomalie analytics `operazioni`
- [x] Aggiungere spiegazioni tecniche per storage alerts `operazioni`
- [x] Aggiungere spiegazioni tecniche per mobile sync `operazioni`
- [x] Mappare almeno 10 regole core di piattaforma/modulo
- [x] Restituire risposte ibride docs + logic

### Fase 3 — Tool coverage per domini

- [x] Lookup particella (`find_particella_by_id`)
- [x] Lookup soggetto utenze (`find_subject_by_cf`)
- [x] Lookup soggetto ruolo (`find_ruolo_subject`)
- [x] Lookup utente NAS (`find_nas_user`)
- [x] Lookup share NAS (`find_share_by_name`)
- [x] Lookup mezzo (`find_vehicle_by_id`)
- [x] Lookup assegnazione mezzo Operazioni (`find_operazioni_assignment_by_id`)
- [x] Lookup manutenzione Operazioni (`find_operazioni_maintenance_by_id`)
- [x] Lookup sessione d'uso Operazioni (`find_operazioni_usage_session_by_id`)
- [x] Lookup attività Operazioni (`find_operazioni_activity_by_id`)
- [x] Lookup approvazione attività Operazioni (`find_operazioni_activity_approval_by_id`)
- [x] Lookup job AUTODOC Operazioni (`find_operazioni_autodoc_sync_job_by_id`)
- [x] Summary analytics Operazioni (`get_operazioni_analytics_summary`)
- [x] Top mezzi carburante analytics Operazioni (`get_operazioni_analytics_top_fuel_vehicles`)
- [x] Top operatori km analytics Operazioni (`get_operazioni_analytics_top_km_operators`)
- [x] Ore per team analytics Operazioni (`get_operazioni_analytics_work_hours_by_team`)
- [x] Summary storage alerts Operazioni (`get_operazioni_storage_status`)
- [x] Summary mobile sync Operazioni (`get_operazioni_mobile_sync_status`)
- [x] Lookup fuel log Operazioni (`find_operazioni_fuel_log_by_id`)
- [x] Lookup transazione non risolta Operazioni (`find_operazioni_unresolved_transaction_by_id`)
- [x] Lookup anomalia analytics Operazioni (`find_operazioni_analytics_anomaly_by_id`)
- [x] Lookup pratica Riordino (`find_riordino_practice_by_id`)
- [x] Lookup case Operazioni (`find_operazioni_case_by_id`)
- [x] Audit log tool calls
- [x] Persistenza leggera audit tool calls (`wiki_tool_audit_logs`)
- [x] Endpoint audit consultabile (`/wiki/audit/tool-calls`)
- [x] Endpoint summary/telemetria audit (`/wiki/audit/tool-calls/summary`)
- [x] Endpoint dettaglio audit (`/wiki/audit/tool-calls/{audit_id}`)
- [x] Vista frontend admin per audit Wiki (`/wiki/audit`)
- [x] Drill-down frontend audit con dettaglio record, fallback reason e contesto modulo
- [x] Trend audit e breakdown latenza/denied per osservabilità operativa
- [x] Registry Wiki aggregato per dominio (`accessi`, `catasto`, `operazioni`, `riordino`, `ruolo/utenze`)
- [x] Refactor completo registry per dominio con rimozione del monolite legacy `tool_registry_impl.py`
- [x] Split finale `system_logic*` e `logic_catalog*` per dominio/sottodominio
- [x] Primo read model dedicato per osservabilità Wiki (`audit_read_models.py`)
- [x] Primo read model live dedicato per analytics Operazioni (`operazioni_analytics_read_models.py`)
- [x] Snapshot persistenti telemetria Wiki (`wiki_telemetry_daily_metrics`)
- [x] Aggregati persistenti settimanali/mensili (`wiki_telemetry_period_metrics`)
- [x] Endpoint telemetria storica (`/wiki/telemetry/summary`, `/wiki/telemetry/series`)
- [x] Endpoint admin per refresh manuale e schedule telemetria (`/wiki/telemetry/refresh`, `/wiki/telemetry/schedule`)
- [x] Endpoint admin retention/prune/export telemetria (`/wiki/telemetry/retention`, `/wiki/telemetry/prune`, `/wiki/telemetry/series/export`)
- [x] Dashboard frontend telemetria Wiki (`/wiki/telemetry`)
- [x] Scheduler APScheduler dedicato per refresh telemetria Wiki
- [x] Drill-down frontend audit/telemetria verso contesto funzionale modulo
- [x] Export CSV e attività correlate nell'audit Wiki (`/wiki/audit/tool-calls/export`, `/wiki/audit/tool-calls/{id}/related`)
- [x] Persistenza conversazioni Wiki (`wiki_conversations`, `wiki_conversation_messages`)
- [x] Link audit → conversazione completa (`conversation_id` su tool audit + riapertura thread in `/wiki`)
- [x] Ricerca e consultazione conversazioni Wiki (`/wiki/conversations`, filtro `search` backend)
- [x] Stato conversazione Wiki e segnali sintetici (`open/resolved`, `last_mode`, `top_tool_name`)
- [x] KPI prodotto conversazioni Wiki e coda admin "da rivedere" (`/wiki/conversations/summary`)
- [x] Read model live dedicati per `accessi`, `catasto`, `ruolo/utenze`
- [x] Hardening policy con reason code di denial e sanitizzazione payload centralizzata
- [x] Endpoint SSE streaming chat (`/wiki/chat/stream`)

### Fase 4 — Query semantiche avanzate su viste curate

Solo se davvero necessario:

- [ ] introdurre viste SQL read-only specifiche per assistant
- [ ] mai esporre SQL arbitrario
- [ ] aggiungere query planner vincolato

---

## 12. Test richiesti

### Backend

- [x] `test_wiki_chat_api.py`
- [x] `test_wiki_intent_classifier.py`
- [x] `test_wiki_response_composer.py`
- [x] `test_wiki_tool_registry.py`
- [x] `test_wiki_tool_policy.py`
- [x] `test_wiki_system_logic.py`

### Frontend

- [x] rendering badge `Docs/Live/Logic/Hybrid`
- [x] visualizzazione evidenze
- [x] fallback corretto su errore tool
- [x] test unitari su metadata condivisi wiki
- [x] coverage su badge `Hybrid` ed evidenze `docs`
- [x] vista admin audit con filtri e paginazione
- [x] test unitari helper audit frontend
- [x] preview payload live/analytics nelle evidenze Wiki
- [x] aggregati frontend audit per top tool/modulo e latenza media
- [x] dettaglio frontend audit per record selezionato
- [x] preview payload workflow/tecnici nelle evidenze Wiki
- [x] preview payload business per `accessi`, `catasto`, `ruolo`, `utenze`, `riordino`
- [x] test componente frontend su `WikiAuditPage` con drill-down
- [x] test componente frontend su `WikiTelemetryPage`
- [x] test frontend su export/retention/related activity delle superfici admin Wiki
- [x] test backend/frontend su persistenza e riapertura conversazioni Wiki
- [x] test backend/frontend su ricerca conversazioni Wiki persistite
- [x] test backend/frontend su stato conversazione Wiki persistita
- [x] test backend/frontend su summary e review queue delle conversazioni Wiki
- [x] test superfici chat `WikiWidget` e `WikiPage`
- [x] test helper frontend `context-links`
- [x] test backend scheduler telemetria Wiki
- [x] self-hosted Material Symbols senza stylesheet esterno in `layout.tsx`
- [x] warning frontend attivi chiusi su build Wiki/Catasto correlata

### Stato test al 2026-05-29

- suite backend Wiki separata in test API + unit test classifier/registry/composer/policy/system_logic
- test eseguiti con `.venv` locale dopo installazione dipendenze backend (`shapely`, `bs4`, resto di `backend/requirements.txt`)
- esito backend: suite Wiki completa verde dopo telemetria persistente giornaliera + periodica, hardening policy e read model live aggiuntivi
- scheduler telemetria Wiki registrabile via APScheduler con config dedicata (`WIKI_TELEMETRY_SCHEDULE_*`)
- retention configurabile via backend settings (`WIKI_AUDIT_RETENTION_DAYS`, `WIKI_TELEMETRY_*_RETENTION_DAYS`)
- conversazioni Wiki persistite e riapribili da pagina Wiki e drill-down audit
- summary conversazioni Wiki con KPI `open/resolved`, `needs_review`, `open_denied`, `open_fallback`
- `npm run typecheck` frontend: ok dopo fix tipizzazione pagina `inaz` e rebuild `.next`
- `npm run test:unit -- wiki-message-metadata wiki-audit-utils wiki-audit-page wiki-telemetry-page wiki-chat-surfaces wiki-context-links`: verde
- `npm run build` frontend: ok senza warning ESLint residui nell'area Wiki/Catasto toccata e con font icone self-hosted

---

## 13. Rischi principali

### Rischio 1 — tool troppo generici

Se i tool accettano input troppo liberi, si ricrea di fatto un SQL layer mascherato.
Mitigazione: tool piccoli, tipizzati, orientati a use case reali.

### Rischio 2 — risposta convincente ma sbagliata

Mitigazione:

- evidenze esplicite
- risposta strutturata
- no free-form DB access
- test su query business critiche

### Rischio 3 — leakage autorizzativo

Mitigazione:

- policy centralizzata
- audit tool calls
- denial esplicito

---

## 14. Decisione raccomandata

Per GAIA la soluzione raccomandata e:

1. mantenere il RAG documentale attuale
2. aggiungere un orchestrator con tool read-only per dati live
3. modellare le logiche applicative come catalogo di regole spiegabili
4. rimandare eventuali query semantiche SQL a una fase successiva e sempre su viste curate

Questa strada massimizza:

- sicurezza
- affidabilita
- governance
- utilita operativa reale

senza trasformare il Wiki Agent in un accesso diretto e incontrollato al database.

---

## 15. Prossimo passo raccomandato

Il prossimo step ad alto valore e basso rischio e passare dalla sola governance di thread a metriche di prodotto più profonde sulle conversazioni, ora che audit, telemetria e conversazioni persistite sono collegati.

### Step successivo consigliato

- estendere i read model live a ulteriori flussi oltre `accessi`, `catasto`, `ruolo/utenze`, `operazioni analytics`
- ampliare i read model live su flussi ancora runtime-coupled e usare l'export per revisioni operative
- aumentare ancora la copertura frontend delle risposte `hybrid`, `denied` e `no_match`
- introdurre KPI temporali sui thread (`open/resolved`, denial/fallback per thread, backlog review nel tempo)

### Subito dopo

- valutare una pagina separata di analytics prodotto Wiki oltre ad audit e telemetria operativa
- estendere l'export anche ad aggregati audit/telemetria summary se serve reporting periodico
- valutare full-text search più forte e code di review specializzate sulle conversazioni Wiki persistite
- valutare query semantiche avanzate solo sopra read model e viste curate

I lookup puntuali su particella Catasto, soggetto Utenze, soggetto Ruolo, utente NAS, share NAS, mezzo Operazioni, pratica Riordino e case Operazioni sono ora presenti e dimostrano che il modello puo instradare richieste non solo aggregate ma anche puntuali.
