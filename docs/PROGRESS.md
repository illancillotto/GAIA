# Progress

## Data Riferimento

- ultima analisi repository: 2026-03-20

## Stato Generale

Il repository e in una fase di bootstrap avanzato: la base documentale, il backend, il frontend, il setup Docker e la CI minima sono presenti e coerenti. Il progetto ha ora tre capability backend reali: autenticazione applicativa con JWT, dominio audit minimo in sola lettura e skeleton di integrazione NAS con parser iniziali e preview di sync.

## Completato

### Repository e Convenzioni

- file root inizializzati: `README.md`, `.gitignore`, `.editorconfig`, `.env.example`, `Makefile`
- naming coerente tra `backend/`, `frontend/`, `docs/`, `scripts/`, `nginx/`
- documentazione iniziale centralizzata in `docs/`

### Backend

- scaffold FastAPI avviabile
- routing modulare base in `backend/app/api`
- endpoint `GET /health` disponibile
- endpoint `POST /auth/login` e `GET /auth/me`
- endpoint protetti `GET /dashboard/summary`, `GET /nas-users`, `GET /nas-groups`, `GET /shares`, `GET /reviews`
- endpoint protetti `GET /sync/capabilities` e `POST /sync/preview`
- configurazione centralizzata con `pydantic-settings`
- utility di sicurezza per password hash e token JWT
- modello `ApplicationUser`
- modelli `NasUser`, `NasGroup`, `Share`, `Review`
- config NAS centralizzata e client skeleton
- parser iniziali per passwd, group, share listing e ACL
- struttura Alembic presente con migration iniziale `snapshots`
- seconda migration per `application_users`
- terza migration per il dominio audit minimo

### Frontend

- scaffold Next.js con App Router
- layout base in `src/app/layout.tsx`
- pagina home bootstrap
- pagina `/login` placeholder
- struttura `src/` predisposta per crescita modulare

### DevOps

- `docker-compose.yml` e `docker-compose.override.yml`
- `Dockerfile` per backend e frontend
- `nginx/nginx.conf` con proxy frontend e backend
- script base in `scripts/`

### CI e Test

- workflow GitHub Actions per backend e frontend
- backend testato con `pytest`
- frontend smoke test con `node:test`

## Verifica Eseguita

### Backend

- suite `backend/tests`
- stato corrente: `34 passed`

Copertura attuale:

- health endpoint
- login e current user
- dashboard summary e liste dominio audit
- sync capabilities e preview NAS
- metadata applicazione FastAPI
- settings e override ambiente
- wiring Alembic e migration iniziale
- wiring security e migration utenti applicativi
- migration dominio audit minimo
- parser NAS e connector skeleton
- scaffold repository e file chiave

### Frontend

- smoke suite `frontend/tests/smoke.test.mjs`
- stato corrente: `4 passed`

Copertura attuale:

- script principali `package.json`
- contenuto base home page
- contenuto base login page
- label della navigazione principale

## Gap Attuali

- auth applicativa presente ma senza bootstrap admin
- dominio audit minimo presente ma senza sync reale persistente
- integrazione NAS solo a livello skeleton, senza SSH live
- nessuna dashboard con dati reali
- nessun test di build frontend completo
- nessun test di esecuzione compose/nginx

## Valutazione del Codice

### Punti Solidi

- bootstrap pulito e leggibile
- separazione dei moduli backend gia predisposta
- documentazione coerente con il perimetro reale
- primo flusso backend reale gia implementato e testato
- dominio audit minimo esposto con API protette e testato end-to-end
- skeleton NAS gia testabile senza dipendere da un host reale
- test iniziali gia utili per evitare regressioni di scaffold

### Punti da Rafforzare Subito

- introdurre sync reale persistente dal NAS
- aggiungere test su API future e servizi
- verificare build frontend in ambiente CI reale
- aggiungere test e smoke check su compose e health integrati

## Prossimi Passi Raccomandati

1. iniziare il permission engine MVP
2. introdurre sync reale persistente dal NAS
3. esporre dati mock o reali nella dashboard frontend
4. aggiungere bootstrap admin o seed iniziale gestito
5. ampliare CI con test build/run piu vicini al runtime reale
6. aggiungere smoke check compose e runtime integrati

## Regola di Aggiornamento

Aggiornare questo file a ogni milestone o a ogni modifica che cambia uno di questi aspetti:

- stato di implementazione dei moduli
- test disponibili o risultati attesi
- rischi tecnici principali
- priorita operative successive
