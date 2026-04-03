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

Nota di compatibilita:

- nel codice runtime possono essere ancora presenti superfici `anagrafica/`
- la documentazione di dominio consolidata vive sotto `domain-docs/utenze/`
