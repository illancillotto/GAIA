# Progress — Wiki Agent (Milestone 9)
**Data**: 2026-05-20
**Stato**: IN CORSO — backend e frontend implementati, da completare con Codex

---

## Implementato (Claude Code, 2026-05-20)

### Documentazione
- `PRD_wiki.md` — requisiti di prodotto completi
- `IMPLEMENTATION_PLAN_wiki.md` — piano con checklist stato
- `PROMPT_CODEX_wiki.md` — prompt operativo per Codex con tutto il contesto

### Backend
- Modulo completo `backend/app/modules/wiki/` con 20 file
- Pipeline RAG: embedding con `text-embedding-3-small`, cosine similarity numpy, completamento GPT-4o
- Endpoint: POST /wiki/chat, GET /wiki/articles, POST /wiki/requests, GET /wiki/requests, PATCH /wiki/requests/{id}, POST /wiki/index
- Migration `20260520_0089` — tabelle `wiki_chunks` e `wiki_requests`
- Indicizzatore documenti con chunking per heading e sub-chunking
- Dipendenze: openai, numpy, tiktoken aggiunte a requirements.txt

### Frontend
- `WikiWidget.tsx` — bubble floating + chat overlay, presente su tutte le pagine autenticate
- `WikiPage.tsx` — pagina /wiki a tre colonne (sidebar articoli, contenuto, chat)
- `useWikiChat.ts` — hook per la gestione della chat
- Route `/wiki` con layout
- Iniezione widget in `app-shell.tsx`

---

## Da completare (Codex)

1. **Configurare** `OPENAI_API_KEY` e `WIKI_DOCS_ROOT` in docker-compose.override.yml
2. **Aggiungere** voce "Wiki" nella sidebar (`platform-sidebar.tsx` + `sidebar.tsx`)
3. **Eseguire** `make migrate && make wiki-index`
4. **Scrivere** test: `test_wiki_rag.py` e `test_wiki_requests.py`
5. **Opzionale**: streaming SSE, pagina admin richieste

---

## Note tecniche

- Embedding storage: JSON text in PostgreSQL (no pgvector extension richiesta)
- Upgrade a pgvector è triviale: cambiare tipo colonna e usare operatore `<=>`
- Indicizzatore scansiona tutti i `.md` del progetto, domain-docs/, progress/
- Fallback graceful se OPENAI_API_KEY non configurata (widget mostra errore 503)
