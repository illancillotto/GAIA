# GAIA Agent Rules

## Graphify maintenance

Usa Graphify come strumento di orientamento e impact analysis sui corpus locali del progetto, non sulla root grezza del repository.

Regole:

- Non eseguire `graphify` dalla root di `GAIA/` per analisi semantiche generiche.
- Usa sempre i target `make` dedicati, che lavorano dentro il corpus corretto e mantengono un `graphify-out/` separato per modulo.
- Per modifiche di codice, aggiorna il grafo del modulo toccato con il target `*-code`.
- Per modifiche di documentazione, aggiorna il grafo del dominio con il target `*-docs` se `OPENAI_API_KEY` o altra API key supportata e disponibile.
- Per modifiche alla documentazione tecnica generale in `docs/`, usa `make graphify-platform-docs`; `make graphify-docs` resta dedicato al corpus aggregato `domain-docs/`.
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
- `make graphify-platform-docs`
- `make graphify-refresh-core-code`
- `make graphify-refresh-core-docs`
- `make graphify-refresh-core`

Query:

- Entra prima nella directory del corpus desiderato.
- Poi usa `graphify query "..."` per domande architetturali o di impatto.

Configurazione locale:

- Le credenziali Graphify locali vivono in `.env.graphify`, ignorato da git.
- I target `make` lo caricano automaticamente se presente.

## Mapping identita GAIA-INAZ

Per audit, backfill, incidenti o sincronizzazioni che coinvolgono il legame tra
utenti GAIA e collaboratori INAZ/Presenze, leggere e applicare prima:

- `skills/gaia-presenze-identity-mapping/SKILL.md`;
- `domain-docs/presenze/docs/INAZ_GAIA_IDENTITY_MAPPING_RUNBOOK.md`.

Il mapping canonico e esclusivamente
`presenze_collaborators.application_user_id -> application_users.id`. Non sono
ammessi mapping automatici o fallback tramite nome, username, email, matricola,
codice fiscale o uguaglianze numeriche fra namespace. Nome e cognome possono
solo generare candidati `REVIEW_REQUIRED`, da approvare esplicitamente prima
del manifest canonico. Ogni collaboratore INAZ, attivo o storico, senza mapping
deve essere rilevato dall'audit e resta fail-closed.

## Sync verso GaTe Mobile

Per modifiche a `app/services/gate_mobile_sync.py`, alle route `mobile_sync`,
agli schemi operatori/presenze verso GATE, o per incidenti "le Presenze non
arrivano su GaTe Mobile", leggere prima `skills/gate-mobile-sync-contract/SKILL.md`.

Invariante: il ciclo del connector e tutto-o-niente
(`handshake -> catalogs -> mobile-operators -> worksets -> presenze/*`); il primo
endpoint non-2xx congela **tutte** le Presenze su GATE. Il fail-hard di
`required_personnel_area` in `build_mobile_operator_push_payload` e voluto e
testato: si sistema il dato (`personnel_area` canonica), non il codice.

## Test coverage policy

Data di entrata in vigore: `2026-06-19`.

Regole:

- Il requisito minimo immediato resta `100%` di coverage sui file runtime nuovi o modificati.
- L'obiettivo di repository e `100%` di coverage sul codice runtime versionato, non solo sui file toccati nella singola change.
- Quando introduci codice non coperto da test, la change non e conforme anche se la media globale resta alta.
- Se una modifica aggiorna la strategia di test, la configurazione coverage o il perimetro dei gate CI, aggiorna anche `docs/TEST_COVERAGE_100_PLAN.md` e la documentazione piattaforma impattata.

## Code style

- La policy e in `docs/CODE_STYLE.md`; la configurazione Python e `ruff.toml`.
- I file Python nuovi o modificati nel perimetro di stile devono passare
  `make lint-backend` / il ratchet Ruff. I file nuovi devono anche passare
  `ruff format --check`.
- Non riformattare alberi legacy per allineare lo stile.
- `noqa`, `ruff: noqa` e `eslint-disable` solo con motivazione.

## Code complexity program

Per modifiche sotto `backend/app`, `frontend/src` o
`modules/elaborazioni/worker`, leggere prima:

- `skills/gaia-complexity-reduction/SKILL.md` e i riferimenti richiesti;
- `docs/code-quality/README.md`;
- `docs/code-quality/PROGRESS.md`;
- `docs/code-quality/METRICS_AND_BASELINE.md`;
- `docs/code-quality/VALIDATION.md`.

Regole:

- La modalita predefinita durante feature, fix e manutenzione e il quality
  ratchet: il perimetro toccato non puo peggiorare, ma non va forzato un
  refactoring non correlato.
- Aprire una modalita hotspot dedicata soltanto su richiesta esplicita o quando
  la complessita ostacola concretamente sviluppo, test o manutenzione.
- Preservare comportamento, API, schema dati, autenticazione, autorizzazione,
  transazioni, concorrenza e comportamento della UI, salvo richiesta esplicita.
- Non eseguire refactoring massivi: una sola unita revisionabile per goal.
- Acquisire e registrare le metriche prima e dopo ogni refactoring.
- Il codice legacy sopra soglia puo restare temporaneamente, ma non puo
  peggiorare.
- Nuove violazioni sopra soglia e peggioramenti del debito esistente devono
  fallire.
- Il controllo ordinario della complessita deve essere read-only.
- Il confronto autorevole deve usare la baseline del merge-base, non quella
  modificata nella stessa change.
- Aggiornare la baseline solo con un comando esplicito dopo il ratchet. Il diff
  puo sincronizzare codice nuovo sotto soglia o debito eliminato, ma non puo
  assorbire nuove violation, regressioni o ampliamenti dello scope escluso.
- Non usare esclusioni larghe, ignore a livello file, duplicazioni, wrapper
  artificiali o split finalizzati esclusivamente ad abbassare le metriche.
- Mantenere il `100%` di coverage dei file runtime modificati secondo la policy
  GAIA.
- Preservare le modifiche non correlate gia presenti nel working tree.
- Aggiornare `docs/code-quality/PROGRESS.md` per cambi di programma/tooling e
  hotspot dedicati. Per il ratchet ordinario registrare comandi, risultati e
  metriche nel riepilogo della change.
- Dichiarare `IMPROVED` soltanto se diminuisce la metrica obiettivo senza
  trasferire il debito. Una estrazione neutra va classificata
  `REORGANIZED_AND_CHARACTERIZED`.
- Rispettare gli obblighi Graphify definiti in questo file.
- Usare la skill direttamente dal repository; non copiarla o installarla nel
  profilo globale Hermes.
- Non creare commit, push, pull request o merge senza richiesta esplicita.

Stop condition: fermarsi e chiedere una decisione se il refactoring richiede un
cambio funzionale, se gli invarianti non sono dimostrabili, se il matching della
baseline e ambiguo, se compare una nuova failure non spiegata o se il lavoro
supera un singolo hotspot revisionabile.

## Hermes project context

- Non aggiungere `.hermes.md` solo per il programma di complessita: avrebbe
  priorita sul presente `AGENTS.md` e potrebbe nascondere le regole Graphify,
  coverage e code quality.
- I goal Hermes devono leggere la skill di progetto da
  `skills/gaia-complexity-reduction/SKILL.md`.
- Usare `/goal` per audit, implementazione e singoli refactoring; riservare
  `/loop` al monitoraggio di stati esterni, come CI o review.
