# Vincoli GAIA

## Architettura

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- Nuovo codice di dominio backend: `backend/app/modules/<module>`.
- Frontend: Next.js 15, React 18, TypeScript in `frontend/src`.
- Worker: `modules/elaborazioni/worker`.
- Workflow distinti backend e frontend.

Verificare sempre le versioni e i percorsi nel checkout corrente.

## Invarianti ad alto rischio

- contratti REST, payload, status e semantica errori;
- ordine/precedenza delle route;
- transazioni e query SQLAlchemy;
- migration e schema PostgreSQL;
- autenticazione e autorizzazione;
- calcoli Catasto, Utenze, Ruolo e Presenze;
- GIS e trasformazioni geografiche;
- retry, timeout, polling e concorrenza del worker;
- dipendenze e sequenza degli hook React;
- rendering, accessibilita e interazioni UI.

## Test e documentazione

- Rispettare la policy di coverage al 100% dei file runtime modificati.
- Non nascondere failure preesistenti.
- Aggiornare Graphify quando richiesto dal `AGENTS.md` autorevole.
- Documentare ogni eccezione di complessita.

## Git

- Preservare modifiche non correlate.
- Nessun commit, push, merge o branch protection senza richiesta.
- Baseline e report sono parte del diff e devono essere revisionabili.
