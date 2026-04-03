# Domain Docs

Questa directory contiene esclusivamente documentazione di dominio:

- PRD
- prompt operativi
- execution plan
- progress tracking

Il codice runtime dei moduli non vive qui.

Riferimenti canonici:

- backend: `backend/app/modules/<modulo>/`
- frontend: `frontend/src/app/<modulo>/`

Esempio:

- documentazione Utenze: `domain-docs/utenze/docs/`
- backend Utenze: `backend/app/modules/utenze/`
- frontend Utenze: `frontend/src/app/utenze/`
- documentazione Elaborazioni: `domain-docs/elaborazioni/docs/`
- backend Elaborazioni: `backend/app/modules/elaborazioni/`
- frontend Elaborazioni: `frontend/src/app/elaborazioni/`

Nota per Elaborazioni:

- i file `domain-docs/elaborazioni/GAIA_VISURE_PROMPT_*` restano fuori da `docs/` finche sono ancora input di lavoro non consolidati
- la documentazione canonica stabile del modulo resta in `domain-docs/elaborazioni/docs/`

Nota di compatibilita:

- nel codice runtime possono essere ancora presenti superfici `anagrafica/`
- la documentazione di dominio consolidata vive sotto `domain-docs/utenze/`
