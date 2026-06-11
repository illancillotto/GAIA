# IMPLEMENTATION PLAN — GAIA Wiki Agent
## Milestone 9

> Stato: OPERATIVO — streaming frontend, hardening client e copertura mirata completati al 2026-06-11
> Iniziato da: Claude Code (Sonnet 4.6)
> Completato quasi interamente da Claude Code (2026-05-20)

---

## Stato implementazione

### Completato da Claude Code

- [x] PRD (`PRD_wiki.md`)
- [x] Implementation Plan (`IMPLEMENTATION_PLAN_wiki.md`)
- [x] Prompt Codex (`PROMPT_CODEX_wiki.md`)
- [x] Migration `20260520_0089` — tabelle `wiki_chunks`, `wiki_requests`
- [x] `backend/app/modules/wiki/models.py`
- [x] `backend/app/modules/wiki/schemas.py`
- [x] `backend/app/modules/wiki/services/openai_client.py`
- [x] `backend/app/modules/wiki/services/rag.py`
- [x] `backend/app/modules/wiki/services/indexer.py`
- [x] `backend/app/modules/wiki/routes/chat.py`
- [x] `backend/app/modules/wiki/routes/articles.py`
- [x] `backend/app/modules/wiki/routes/requests.py`
- [x] `backend/app/modules/wiki/router.py`
- [x] `backend/app/modules/wiki/__init__.py`
- [x] Registrazione router in `backend/app/api/router.py`
- [x] Aggiunta dipendenze in `backend/requirements.txt` (`openai>=1.30.0`)
- [x] `frontend/src/features/wiki/types.ts`
- [x] `frontend/src/features/wiki/useWikiChat.ts`
- [x] `frontend/src/features/wiki/WikiWidget.tsx` — floating bottom-right
- [x] `frontend/src/features/wiki/WikiPage.tsx`
- [x] `frontend/src/app/wiki/layout.tsx`
- [x] `frontend/src/app/wiki/page.tsx`
- [x] Iniezione `WikiWidget` in `app-shell.tsx`
- [x] Funzioni API wiki in `frontend/src/lib/api.ts`
- [x] Voce "Wiki" in `platform-sidebar.tsx` + case in `sidebar.tsx`
- [x] `CODEX_LB_URL`, `WIKI_DOCS_ROOT`, `extra_hosts` in `docker-compose.override.yml`
- [x] Documenti spostati in `docs/` e `docs/wiki/`; indexer aggiornato (`docs/**/*.md`)

### Operativo — completato 2026-05-20

- [x] `make migrate` — tabelle `wiki_chunks` e `wiki_requests` create
- [x] `make wiki-proxy` — proxy HTTP `0.0.0.0:2455 → 127.0.0.1:2456` avviato (codex-lb su `127.0.0.1:2456`)
- [x] `make wiki-index` — 109 file indicizzati, 2319 chunk totali
- [x] RAG funzionante end-to-end (FTS + codex-lb gpt-5.4-mini)

> **Nota avvio**: al riavvio del PC, avviare codex-lb e il proxy prima di `make up`:
> ```bash
> nohup codex-lb --host 127.0.0.1 --port 2456 > /tmp/codex-lb.log 2>&1 &
> make wiki-proxy
> ```

### Residuo reale

- [x] Pagina admin `/wiki/requests` (lista richieste + cambio status)
- [x] Endpoint streaming SSE `/wiki/chat/stream`
- [x] Consumo frontend dello streaming SSE con fallback compatibile
- [x] Allineamento documentazione e coverage frontend delle superfici support/requests

### Verifiche aggiornate — 2026-06-11

- [x] `frontend/src/features/wiki/useWikiChat.ts` usa SSE con fallback sincrono, abort su unmount/cambio conversazione e reload conversazioni con error reporting esplicito
- [x] `frontend/src/features/wiki/WikiPage.tsx` e `WikiConversationsPage.tsx` allineate al contratto `frontend/src/lib/api.ts`
- [x] test frontend mirati verdi:
  - `wiki-chat-stream.test.tsx`
  - `wiki-chat-surfaces.test.tsx`
  - `wiki-conversations-page.test.tsx`
  - `wiki-support-surfaces.test.tsx`
- [x] `npm run typecheck` frontend verde
- [x] coverage backend router chat: `81%` su `backend/app/modules/wiki/routes/chat.py`
- [x] coverage frontend mirata sui file toccati:
  - `useWikiChat.ts`: `69.39%` statements, `49.64%` branch
  - `WikiPage.tsx`: `57.95%` statements, `55.96%` branch
  - `WikiConversationsPage.tsx`: `42.85%` statements, `38.77%` branch
- [x] richieste supporto Wiki con artifact del caso:
  - endpoint `POST /wiki/requests/with-artifacts`
  - tabella `wiki_request_artifacts`
  - screenshot pagina + snapshot UI strutturato
  - rendering artifact nel dettaglio admin richiesta
  - preview screenshot e download/export artifact dal dettaglio admin
  - snapshot tipizzati per `operazioni`, `catasto`, `rete`, `utenze` con route, entity id, filtri e campi operativi principali
  - redazione automatica di email, telefoni, CF/P.IVA, token e URL/query sensibili negli artifact

Nota:
il totale del report frontend resta basso se si include `frontend/src/lib/api.ts`, perché il file e monolitico e contiene centinaia di helper non esercitati dai test wiki. Per il modulo wiki il dato utile è la copertura dei file feature toccati sopra.

### Completato (Claude Code, 2026-05-20)

- [x] PRD, IMPLEMENTATION_PLAN, PROMPT_CODEX → `docs/wiki/`
- [x] Backend completo: models, schemas, routes, services, migration
- [x] LLM: codex-lb (porta 2455, proxy OpenAI-compatibile locale)
- [x] Retrieval: PostgreSQL FTS (`to_tsvector` + GIN index, no embedding API)
- [x] Frontend: WikiWidget (bottom-right), WikiPage, useWikiChat, route /wiki, layout
- [x] Sidebar: voce Wiki con `BookOpenIcon` visibile a tutti gli utenti autenticati
- [x] Docker: env vars + extra_hosts + volume docs montato in backend
- [x] Iniezione widget in app-shell.tsx
- [x] Makefile: wiki-index, wiki-reindex, test-wiki, coverage-wiki
- [x] `pytest.ini`, `.coveragerc`
- [x] **5 file di test**: test_wiki_indexer.py, test_wiki_rag.py, test_wiki_requests_api.py, test_wiki_articles_api.py, test_wiki_chat_api.py
- [x] 25/25 test unitari puri verdi in locale

---

## Ordine di deploy

1. `make migrate` → crea le tabelle `wiki_chunks` e `wiki_requests`
2. `docker compose restart backend` → carica le nuove env vars (CODEX_LB_URL, WIKI_DOCS_ROOT)
3. Verificare codex-lb: `docker compose exec backend curl http://host.docker.internal:2455/v1/models`
4. `make wiki-index` → indicizza i docs (nessuna API esterna, solo PostgreSQL FTS)
5. Verificare widget sul frontend (bottom-right su ogni pagina)
6. Verificare pagina `/wiki` — sidebar articoli + chat contestuale

---

## Decisioni architetturali

### Perché PostgreSQL FTS e non pgvector/embedding?

Evita di cambiare l'immagine Docker di PostgreSQL e di fare chiamate API esterne per l'indicizzazione.
La ricerca full-text con GIN index è sufficiente per documenti tecnici in italiano/inglese.
Upgrade a pgvector è triviale: cambia il tipo di colonna + usa `<=>` operator SQL.

### Perché streaming incrementale con fallback?

Il backend espone SSE su `/wiki/chat/stream`, ma il frontend deve restare tollerante
verso runtime/proxy che non propagano `ReadableStream`. Per questo il client deve
consumare SSE quando disponibile e ripiegare sul path sincrono senza rompere la UX.

### Perché non LangChain?

Zero dipendenze extra inutili. Il pipeline RAG è 50 righe di codice,
LangChain aggiungerebbe 50MB di dipendenze per fare la stessa cosa.

---

## Struttura file finale

```
GAIA/
├── docs/wiki/
│   ├── PRD_wiki.md
│   ├── IMPLEMENTATION_PLAN_wiki.md
│   └── PROMPT_CODEX_wiki.md
│
├── docker-compose.override.yml                   ← +CODEX_LB_URL, WIKI_DOCS_ROOT, extra_hosts, volume docs
│
├── backend/
│   ├── requirements.txt                          ← +openai>=1.30.0
│   ├── alembic/versions/
│   │   └── 20260520_0089_wiki_chunks_and_requests.py
│   └── app/
│       ├── api/router.py                         ← +wiki_router
│       └── modules/wiki/
│           ├── __init__.py
│           ├── router.py
│           ├── models.py
│           ├── schemas.py
│           ├── routes/
│           │   ├── __init__.py
│           │   ├── chat.py
│           │   ├── articles.py
│           │   ├── requests.py
│           │   └── index.py
│           └── services/
│               ├── __init__.py
│               ├── openai_client.py
│               ├── rag.py
│               └── indexer.py                    ← INCLUDE_PATTERNS: docs/**/*.md
│
└── frontend/
    └── src/
        ├── components/
        │   ├── ui/icons.tsx                      ← +BookOpenIcon
        │   └── layout/
        │       ├── app-shell.tsx                 ← +WikiWidget
        │       ├── platform-sidebar.tsx          ← +voce Wiki
        │       └── sidebar.tsx                   ← +case "wiki"
        ├── features/wiki/
        │   ├── types.ts
        │   ├── useWikiChat.ts
        │   ├── WikiWidget.tsx                    ← fixed bottom-6 right-6
        │   └── WikiPage.tsx
        └── app/wiki/
            ├── layout.tsx
            └── page.tsx
```
