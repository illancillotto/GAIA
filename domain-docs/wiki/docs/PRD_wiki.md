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
- Status: `pending` → `reviewed` → `planned` → `done`

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
    │   └── requests.py              ← POST/GET /wiki/requests
    └── services/
        ├── rag.py                   ← retrieval + completion
        ├── indexer.py               ← document parsing + embedding
        └── openai_client.py         ← wrapper OpenAI API
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

---

## 8. Metriche di successo

- Almeno 80% delle domande sui documenti riceve una risposta rilevante
- Meno di 5% di timeout sulla chat
- Almeno 3 richieste utente registrate entro il primo mese di deploy
