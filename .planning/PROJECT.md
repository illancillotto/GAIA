# PROJECT.md — GAIA Operazioni

## Vision
Implementare il modulo **Operazioni** per la piattaforma GAIA del Consorzio di Bonifica dell'Oristanese, coprendo:
- Gestione mezzi (anagrafica, assegnazioni, sessioni, carburante, manutenzioni)
- Attività operatori (catalogo, start/stop, approvazioni)
- Segnalazioni e pratiche interne (workflow completo)
- Allegati multimediali e storage governance
- Mini-app operatori mobile-first
- GPS e consuntivazione

## Principi
- Monolite modulare: backend unico FastAPI, frontend unico Next.js, DB PostgreSQL condiviso
- Implementazione incrementale per milestone
- Priorità ai workflow core prima delle ottimizzazioni
- Mini-app semplice fin dall'inizio
- Audit trail e integrità dati come requisiti core

## Non-negotiables
- Nessun microservizio separato
- Nessun backend duplicato
- Nuovo codice di dominio solo in `backend/app/modules/operazioni/`
- Frontend solo in `frontend/src/app/operazioni/`
- Distanza chiara tra dato dichiarato, rilevato (GPS) e validato
- Ogni segnalazione genera sempre una pratica
- Storage server-side con soglia 50GB e alert progressivi (70/85/95%)

## Stack
- Backend: FastAPI + SQLAlchemy + Alembic + Pydantic
- Frontend: Next.js + React + TailwindCSS
- Database: PostgreSQL condiviso
- Tabella utenti: `application_users` (Integer PK)

## User Preferences
- Documentazione in italiano
- Label UI in italiano
- Componenti riusabili
- Mini-app: pulsanti grandi, pochi input, testi chiari, max 3 click per azione

## Domini
- operazioni

## Technical Decisions
- UUID come PK per tutte le nuove tabelle Operazioni
- JSONB solo per payload dinamici
- Stringhe validate per stati interni (no enum PostgreSQL per stati evolutivi)
- offline_client_uuid per dedup sync mobile
- Tabella attachment centralizzata con tabelle ponte
