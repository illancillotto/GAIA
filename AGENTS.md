# GAIA Agent Rules

## Graphify maintenance

Usa Graphify come strumento di orientamento e impact analysis sui corpus locali del progetto, non sulla root grezza del repository.

Regole:

- Non eseguire `graphify` dalla root di `GAIA/` per analisi semantiche generiche.
- Usa sempre i target `make` dedicati, che lavorano dentro il corpus corretto e mantengono un `graphify-out/` separato per modulo.
- Per modifiche di codice, aggiorna il grafo del modulo toccato con il target `*-code`.
- Per modifiche di documentazione, aggiorna il grafo del dominio con il target `*-docs` se `OPENAI_API_KEY` o altra API key supportata e disponibile.
- Se cambia struttura, routing, servizi, workflow o superfici di un modulo supportato, aggiorna Graphify prima di chiudere il lavoro.
- Se manca una API key valida, non bloccare il lavoro sul grafo docs: aggiorna almeno il grafo codice e segnala il limite.
- Se Graphify deve usare `codex-lb`, assicurati che la patch locale per `OPENAI_BASE_URL` sia applicata tramite `make graphify-patch-openai-base-url`.

Target supportati:

- `make graphify-catasto-code`
- `make graphify-catasto-docs`
- `make graphify-inaz-code`
- `make graphify-inaz-docs`
- `make graphify-network-code`
- `make graphify-network-docs`
- `make graphify-operazioni-code`
- `make graphify-operazioni-docs`
- `make graphify-organigramma-code`
- `make graphify-organigramma-docs`
- `make graphify-riordino-code`
- `make graphify-riordino-docs`
- `make graphify-ruolo-code`
- `make graphify-ruolo-docs`
- `make graphify-utenze-code`
- `make graphify-utenze-docs`
- `make graphify-wiki-code`
- `make graphify-wiki-docs`
- `make graphify-backend`
- `make graphify-frontend`
- `make graphify-docs`
- `make graphify-refresh-core-code`
- `make graphify-refresh-core-docs`
- `make graphify-refresh-core`

Query:

- Entra prima nella directory del corpus desiderato.
- Poi usa `graphify query "..."` per domande architetturali o di impatto.

Configurazione locale:

- Le credenziali Graphify locali vivono in `.env.graphify`, ignorato da git.
- I target `make` lo caricano automaticamente se presente.
