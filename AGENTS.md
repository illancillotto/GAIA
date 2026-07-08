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
- Per `make graphify-wiki-docs`, usa il target `make` dedicato: applica gia `GRAPHIFY_OPENAI_MODEL=gpt-5.4-mini`, `--max-concurrency 1` e `--api-timeout 60` per evitare l'hang osservato con `gpt-5.5` sul path docs di Graphify.
- Per i target `*-docs`, il default operativo raccomandato e `gpt-5.4-mini`: su Graphify privilegiamo stabilita, costo e latenza rispetto alla massima qualita del modello, perche l'estrazione semantica dei corpus docs e un carico batch ripetitivo. Usa `gpt-5.4` solo se serve una qualita semantica piu alta su un corpus specifico e il profilo resta stabile; evita `gpt-5.5` sui target docs che hanno gia mostrato hang o timeout.
- Per diagnosi del corpus wiki usa `make graphify-wiki-docs-debug`: salva il trace in `/tmp/graphify-wiki-docs-debug.log` con timeout corto e output non bufferizzato.

Target supportati:

- `make graphify-catasto-code`
- `make graphify-catasto-docs`
- `make graphify-presenze-code`
- `make graphify-presenze-docs`
- `make graphify-presenze-query`
- `make graphify-inaz-code`
- `make graphify-inaz-docs`
- `make graphify-inaz-query`
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

## Test coverage policy

Data di entrata in vigore: `2026-06-19`.

Regole:

- Il requisito minimo immediato resta `100%` di coverage sui file runtime nuovi o modificati.
- L'obiettivo di repository e `100%` di coverage sul codice runtime versionato, non solo sui file toccati nella singola change.
- Quando introduci codice non coperto da test, la change non e conforme anche se la media globale resta alta.
- Se una modifica aggiorna la strategia di test, la configurazione coverage o il perimetro dei gate CI, aggiorna anche `docs/TEST_COVERAGE_100_PLAN.md` e la documentazione piattaforma impattata.
