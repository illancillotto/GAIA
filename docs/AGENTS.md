## Documentation policy

Prima di ogni commit, se cambiano feature, moduli, API, flussi, modelli dati, job, servizi, pagine frontend, componenti o struttura del repository, aggiorna la documentazione impattata.

La documentazione del progetto è organizzata in due aree principali:

1. Root del repository:
   - README.md
2. Directory `docs/`:
   - docs/ARCHITECTURE.md
   - docs/PRD.md
   - docs/IMPLEMENTATION_PLAN.md
   - docs/DOCS_STRUCTURE.md

3. domain-docs/<dominio>/docs/:
   - accessi
   - catasto
   - inventory
   - network
   - utenze

## Documentation routing rules

Regole generali:
- Non riscrivere da zero i file se non necessario.
- Aggiorna solo le sezioni strettamente impattate dal diff.
- Mantieni stile tecnico, sintetico e coerente.
- Non modificare file prompt o documenti fuori whitelist.
- Se cambia la struttura delle cartelle, dei moduli o dei percorsi, aggiorna anche `docs/DOCS_STRUCTURE.md`.

Regole di routing:
- Se una modifica riguarda un singolo dominio, aggiorna prima la documentazione del dominio corrispondente in `domain-docs/<dominio>/docs/`.
- Se una modifica ha impatto trasversale o di piattaforma, aggiorna `README.md` e i documenti di piattaforma in `docs/`.
- Per modifiche locali a un dominio, non aggiornare documenti di altri domini se non strettamente necessario.

Domini supportati:
- accessi
- catasto
- inventory
- network
- utenze
