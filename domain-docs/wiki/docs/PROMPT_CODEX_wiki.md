# PROMPT_CODEX — GAIA Wiki Agent
## Milestone 9: Assistente LLM con RAG integrato nella piattaforma

> Prompt operativo per Codex. Da usare come system prompt o primo messaggio in una sessione dedicata.
> Repository: `github.com/illancillotto/GAIA`
> Branch di lavoro consigliato: `feature/wiki-agent`

---

## Contesto del progetto

Stai lavorando su **GAIA**, una piattaforma IT governance per il Consorzio di Bonifica dell'Oristanese.

Lo stack è: FastAPI + SQLAlchemy + Alembic + PostgreSQL per il backend, Next.js + React + TypeScript + TailwindCSS per il frontend. L'infrastruttura è Docker Compose + Nginx.

Il backend è un **monolite modulare**. Ogni modulo vive in `backend/app/modules/<modulo>/`.
Il frontend usa App Router di Next.js 14 con `frontend/src/app/` e features in `frontend/src/features/`.

---

## Architettura del Wiki Agent

### LLM backend: codex-lb (locale, porta 2455)

Il wiki agent NON usa OpenAI direttamente. Usa **codex-lb**, un proxy OpenAI-compatibile
che gira sul PC host alla porta 2455 (`http://host.docker.internal:2455/v1` da Docker).

- Nessuna API key necessaria (auth disabilitata per richieste locali)
- Modello chat: `gpt-5.4-mini` (configurabile via env `WIKI_CHAT_MODEL`)
- Modelli disponibili: gpt-5.5, gpt-5.4, gpt-5.4-mini, gpt-5.3-codex, gpt-5.2

### Retrieval: PostgreSQL Full-Text Search (nessuna API esterna)

Il retrieval NON usa embedding vettoriali. Usa **PostgreSQL FTS** con:
- Colonna `search_vector TSVECTOR` su `wiki_chunks`
- Indice GIN per le performance
- `plainto_tsquery('simple', query)` per la ricerca
- Fallback ai chunk più recenti se nessun risultato

### Widget operativo — aggiornamento 2026-06-23

Nel widget embedded sulle pagine modulo:

- usare `module_key` e `page_path` per contestualizzare la risposta
- alla prima interazione della pagina, un saluto o una query molto generica deve produrre una mini presentazione contestuale
- su conversazione già aperta, un nuovo saluto deve essere breve e non ripetere l'introduzione
- per richieste vaghe ma plausibilmente su GAIA preferire `page_intro`, `module_overview`, `navigation_help` o `clarification_needed`
- evitare `out_of_scope` quando la domanda è ancora ragionevolmente collegata a modulo, pagina, procedura o dato interno
- per capability conversazionali del widget privilegiare documentazione operativa e filtrare chunk di codice UI/backend

---

## Stato attuale del modulo Wiki (già implementato)

**Tutto il seguente codice è già scritto e funzionante:**

### Backend — `backend/app/modules/wiki/`
```
__init__.py
router.py              ← registra chat, articles, requests, index router
models.py              ← WikiChunk (con search_vector TSVECTOR), WikiRequest
schemas.py             ← Pydantic: WikiChatRequest/Response, WikiArticleGroup, WikiRequestCreate/Read
routes/
  chat.py              ← POST /wiki/chat (RAG via PG FTS + codex-lb)
  articles.py          ← GET /wiki/articles, GET /wiki/articles/{path}
  requests.py          ← POST /wiki/requests, GET /wiki/requests, PATCH /wiki/requests/{id}
  index.py             ← POST /wiki/index (background task, solo admin)
services/
  openai_client.py     ← client codex-lb, CODEX_LB_URL, is_wiki_available()
  rag.py               ← retrieve_chunks() via PG FTS, answer_question() via codex-lb
  indexer.py           ← index_documents(): chunking + to_tsvector() SQL, NO chiamate API
```

### Backend — già integrato
- Migration `20260520_0089` — crea `wiki_chunks` (con GIN index su search_vector) e `wiki_requests`
- `backend/app/api/router.py` — include `wiki_router` con prefix `/wiki`
- `backend/requirements.txt` — aggiunto solo `openai>=1.30.0`

### Frontend — `frontend/src/features/wiki/`
```
types.ts               ← tipi TypeScript (WikiChatMessage, WikiArticleGroup, ecc.)
useWikiChat.ts         ← hook React: sendMessage, messages, loading, error
WikiWidget.tsx         ← floating button + chat overlay (fixed bottom-6 right-6)
WikiPage.tsx           ← pagina /wiki: sidebar articoli + contenuto + chat panel
```

### Frontend — già integrato
- `frontend/src/app/wiki/layout.tsx` e `page.tsx` — route `/wiki`
- `frontend/src/components/layout/app-shell.tsx` — `<WikiWidget />` iniettato sotto `<main>`
- `Makefile` — target `wiki-index` e `wiki-reindex`

---

## Cosa resta da fare

### Priorità 1 — Deploy (tutto il resto è già implementato)

#### 1. Configurazione docker-compose ✅ GIÀ FATTO

`docker-compose.override.yml` ha già nel servizio `backend`:
```yaml
environment:
  CODEX_LB_URL: http://host.docker.internal:2455/v1
  WIKI_DOCS_ROOT: /app/docs
extra_hosts:
  - "host.docker.internal:host-gateway"
volumes:
  - .:/app/docs:ro
```

#### 2. Verificare raggiungibilità codex-lb dal container

```bash
docker compose exec backend curl -s http://host.docker.internal:2455/v1/models | python3 -m json.tool | head -10
```
Se fallisce, codex-lb non è raggiungibile — controllare `extra_hosts` e che codex-lb ascolti su `0.0.0.0` e non solo `127.0.0.1`.

Se codex-lb ascolta solo su `127.0.0.1` (verifica con `ss -tlnp | grep 2455`), avviarlo con `--host 0.0.0.0`.

#### 3. Eseguire migration e indicizzazione

```bash
make migrate        # crea wiki_chunks e wiki_requests
make wiki-index     # indicizza i docs in docs/ e domain-docs/ (nessuna API esterna, solo PG FTS)
```

#### 4. Sidebar ✅ GIÀ FATTO

- `platform-sidebar.tsx`: voce "Wiki" con `BookOpenIcon` aggiunta a `platformModules`
- `sidebar.tsx`: case `pathname.startsWith("/wiki") ? "wiki"` e label "Wiki" già presenti

---

### Priorità 2 — Test (già scritti, da eseguire nel container)

I test sono già implementati nei seguenti file:

| File | Cosa testa | Note |
|---|---|---|
| `tests/test_wiki_indexer.py` | `_split_by_heading`, `_sub_chunk`, `_find_docs` | Puro Python, gira anche localmente |
| `tests/test_wiki_rag.py` | `retrieve_chunks`, `answer_question`, `_build_context` | Mock DB e codex-lb |
| `tests/test_wiki_requests_api.py` | CRUD WikiRequest via API, RBAC | Richiede Docker (shapely) |
| `tests/test_wiki_articles_api.py` | GET articoli, raggruppamento, ordinamento | Richiede Docker |
| `tests/test_wiki_chat_api.py` | Chat endpoint, 503/500, ruoli | Richiede Docker |

Per eseguirli:
```bash
make test-wiki        # tutti i test wiki
make coverage-wiki    # con report HTML in backend/htmlcov/wiki/
```

Coverage storico (Milestone 9 iniziale, test unitari puri senza Docker): **55%** totale, **100% su rag.py e schemas.py**.
Policy corrente: per file runtime nuovi o modificati la soglia richiesta e **100%**.
Verifica più recente sul refactor widget operativo 2026-06-23:

- `guardrails.py`: `100%`
- `orchestrator.py`: `100%`
- `question_router.py`: `100%`
- `rag.py`: `100%`
- `semantic_router.py`: `100%`

---

### Priorità 3 — Streaming SSE (opzionale)

**Backend** — nuovo endpoint `POST /wiki/chat/stream`:
```python
from fastapi.responses import StreamingResponse
import json

@router.post("/chat/stream")
def wiki_chat_stream(payload: WikiChatRequest, db=Depends(get_db), _=Depends(get_current_user)):
    def generate():
        chunks = retrieve_chunks(db, payload.question)
        context = _build_context(chunks)
        client = get_openai_client()
        stream = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{context}\n\nDomanda: {payload.question}"},
            ],
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield f"data: {json.dumps({'delta': delta})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Frontend** — modificare `useWikiChat.ts` per consumare SSE con `fetch` + `ReadableStream`.

---

### Priorità 4 — Pagina admin richieste

Creare `frontend/src/app/wiki/requests/page.tsx`:
- Tabella: domanda, categoria, status, utente, data
- Filtro per status (pending / reviewed / planned / done)
- Dropdown cambio status (PATCH /wiki/requests/{id})
- Solo visibile se `currentUser.role === "admin" || "super_admin"`

---

## Variabili d'ambiente

| Variabile | Default (in Docker) | Descrizione |
|---|---|---|
| `CODEX_LB_URL` | `http://host.docker.internal:2455/v1` | URL proxy codex-lb |
| `CODEX_LB_API_KEY` | `sk-codex-lb-local` | Chiave API (dummy, auth disabilitata localmente) |
| `WIKI_CHAT_MODEL` | `gpt-5.4-mini` | Modello chat su codex-lb |
| `WIKI_DOCS_ROOT` | `/app` | Directory root dei file .md da indicizzare |
| `WIKI_TOP_K` | `5` | Numero massimo chunk da usare come contesto |

---

## Endpoints API wiki (già implementati)

| Method | Path | Auth | Descrizione |
|---|---|---|---|
| POST | /api/wiki/chat | utente | Risposta RAG (PG FTS + codex-lb) |
| GET | /api/wiki/articles | utente | Lista documenti indicizzati |
| GET | /api/wiki/articles/{path} | utente | Chunk di un documento specifico |
| POST | /api/wiki/requests | utente | Salva richiesta utente |
| GET | /api/wiki/requests | admin | Lista richieste |
| PATCH | /api/wiki/requests/{id} | admin | Aggiorna status richiesta |
| POST | /api/wiki/index | admin | Avvia re-indicizzazione background |

---

## Vincoli e convenzioni

- **Nessun hardcoding** di URL o segreti
- **TypeScript strict** nel frontend — nessun `any`
- **Type hints completi** in Python
- **Stile UI GAIA**: TailwindCSS, colore primario `#1D4E35`, `rounded-xl` / `rounded-2xl`, `text-sm`
- **Errori HTTP**: 400 bad request, 401 non autenticato, 403 non autorizzato, 404 not found, 503 proxy non raggiungibile
- **Logging** delle operazioni con `logger.info/warning/error`
- **Test** backend con il pattern esistente nel progetto

---

## Checklist di completamento

### Già completato ✅
- [x] `CODEX_LB_URL` configurata in `docker-compose.override.yml`
- [x] `extra_hosts: host.docker.internal:host-gateway` nel servizio backend
- [x] `WIKI_DOCS_ROOT: /app/docs` + volume `.:/app/docs:ro`
- [x] Widget floating bottom-right su ogni pagina
- [x] Link "Wiki" nella sidebar principale (`BookOpenIcon`)
- [x] Pagina `/wiki` con sidebar articoli + chat contestuale
- [x] POST /wiki/requests, GET /wiki/requests (admin), PATCH /wiki/requests/{id}

### Da verificare in produzione
- [ ] `make migrate` eseguito con successo
- [ ] `make wiki-index` eseguito — almeno 5 file indicizzati
- [ ] `docker compose exec backend curl http://host.docker.internal:2455/v1/models` restituisce modelli
- [ ] Widget: primo `ciao` su pagina modulo -> mini presentazione contestuale
- [ ] Widget: secondo `ciao` su conversazione esistente -> risposta breve
- [ ] Chat risponde a "Cos'è GAIA?" con overview operativa coerente col contesto pagina
- [ ] Chat risponde a "Quali moduli esistono?" con lista da `docs/PRD.md`
- [ ] GET /wiki/requests restituisce 403 per utente non admin
- [ ] Test backend verdi (`make test-wiki`)
- [ ] Nessun import rotto, nessun test pre-esistente rotto
