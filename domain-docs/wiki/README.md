# Wiki Domain Docs

Questa directory raccoglie la documentazione del modulo `wiki`.

Struttura:

- `docs/`: PRD, piani implementativi, prompt e note architetturali del modulo
- `operational/`: corpus operativo persistente per il Wiki Agent

Il corpus `operational/` e pensato come base per il routing task-first del Wiki:

- descrive moduli, pagine, capability e workflow
- esplicita input minimi, output attesi ed errori frequenti
- riduce la dipendenza da fallback documentali generici

Contenuti recenti rilevanti per l'assistente widget:

- moduli: catasto, wiki, accessi, operazioni, utenze, ruolo, riordino, rete, inaz, organigramma, elaborazioni
- pagine: particelle, GIS, letture contatori, supporto Wiki, pratiche operazioni, shares NAS, visure elaborazioni, organigramma
- workflow: ricerca proprietario, navigazione

Dopo modifiche al corpus operativo: indicizzazione incrementale via `docker compose exec backend python -m app.modules.wiki.services.indexer` (senza `force=True`) oppure `make wiki-reindex` per rebuild completo.
