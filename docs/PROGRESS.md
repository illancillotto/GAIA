# Progress

## Data Riferimento

- ultima analisi repository: 2026-03-20

## Stato Generale

Il repository e in una fase di bootstrap avanzato: la base documentale, il backend, il frontend, il setup Docker e la CI minima sono presenti e coerenti. Il progetto ha ora sei capability backend reali: autenticazione applicativa con JWT, bootstrap admin idempotente, bootstrap dominio audit idempotente, dominio audit minimo in sola lettura, skeleton di integrazione NAS con parser iniziali e permission engine MVP con preview di calcolo. Sul frontend la milestone applicativa e in avanzamento concreto: login reale, stato sessione, dashboard collegata, viste utenti e gruppi NAS e prime viste backend-driven principali.

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
- endpoint protetti `POST /permissions/calculate-preview` e `GET /effective-permissions`
- configurazione centralizzata con `pydantic-settings`
- utility di sicurezza per password hash e token JWT
- modello `ApplicationUser`
- modelli `NasUser`, `NasGroup`, `Share`, `Review`
- modelli `PermissionEntry` ed `EffectivePermission`
- bootstrap admin idempotente via script backend e target Makefile
- config NAS centralizzata e client skeleton
- parser iniziali per passwd, group, share listing e ACL
- servizio di calcolo permessi con regole `deny` e `write implies read`
- bootstrap dominio audit idempotente via script backend e target Makefile
- struttura Alembic presente con migration iniziale `snapshots`
- seconda migration per `application_users`
- terza migration per il dominio audit minimo
- quarta migration per il permission engine MVP

### Frontend

- scaffold Next.js con App Router
- layout base in `src/app/layout.tsx`
- pagina home collegata a `GET /auth/me` e `GET /dashboard/summary`
- pagina `/login` collegata a `POST /auth/login`
- viste backend-driven per utenti NAS, gruppi NAS, share, review, sync ed effective permissions
- preview frontend del permission engine collegata a `POST /permissions/calculate-preview`
- struttura `src/` predisposta per crescita modulare

### DevOps

- `docker-compose.yml` e `docker-compose.override.yml`
- `Dockerfile` per backend e frontend
- `nginx/nginx.conf` con proxy frontend e backend
- script base in `scripts/`
- stack locale verificato in runtime con Docker
- fix runtime su `docker-compose.override.yml` per frontend `next dev` con `NODE_ENV=development`

### CI e Test

- workflow GitHub Actions per backend e frontend
- backend testato con `pytest`
- frontend smoke test con `node:test`

## Verifica Eseguita

### Backend

- suite `backend/tests`
- stato corrente: `42 passed`

Verifica runtime:

- `docker compose up -d --build`
- `docker compose exec backend alembic upgrade head`
- `docker compose exec backend python scripts/bootstrap_admin.py`
- `docker compose exec backend python scripts/bootstrap_domain.py`
- login reale verificato su `POST /auth/login`
- query reali verificate su `/dashboard/summary`, `/nas-users`, `/nas-groups`, `/shares`, `/reviews`, `/effective-permissions`

Copertura attuale:

- health endpoint
- login e current user
- dashboard summary e liste dominio audit
- sync capabilities e preview NAS
- permission preview e lista effective permissions
- metadata applicazione FastAPI
- settings e override ambiente
- wiring Alembic e migration iniziale
- wiring security e migration utenti applicativi
- migration dominio audit minimo
- migration permission engine MVP
- parser NAS e connector skeleton
- servizio calcolo permessi
- bootstrap admin service e script
- bootstrap dominio service e script
- scaffold repository e file chiave

### Frontend

- smoke suite `frontend/tests/smoke.test.mjs`
- stato corrente: `7 passed`

Verifica runtime:

- frontend raggiungibile su `http://localhost:3000`
- nginx raggiungibile su `http://localhost:8080`
- tutti i container compose verificati `healthy`

Copertura attuale:

- script principali `package.json`
- integrazione login e dashboard
- navigazione principale applicativa
- presenza di viste backend-driven
- presenza della preview permission engine
- mapping frontend piu leggibile tra id e nomi di dominio

## Gap Attuali

- dominio audit minimo presente ma senza sync reale persistente
- integrazione NAS solo a livello skeleton, senza SSH live
- permission engine presente ma non ancora alimentato da sync persistente
- frontend collegato a molte API di lettura ma non ancora completo sul dominio
- nessun test di build frontend completo
- nessun test di esecuzione compose/nginx
- sync reale verso NAS ancora assente

## Valutazione del Codice

### Punti Solidi

- bootstrap pulito e leggibile
- separazione dei moduli backend gia predisposta
- documentazione coerente con il perimetro reale
- primo flusso backend reale gia implementato e testato
- dominio audit minimo esposto con API protette e testato end-to-end
- skeleton NAS gia testabile senza dipendere da un host reale
- permission engine MVP gia calcolabile e testato
- bootstrap admin disponibile per sbloccare subito l'uso del frontend reale
- seed dominio disponibile per mostrare dati utili out-of-the-box
- frontend non e piu solo statico: login, sessione, utenti NAS e prime viste reali sono attivi
- stack Docker del progetto verificato end-to-end in ambiente locale
- test iniziali gia utili per evitare regressioni di scaffold

### Punti da Rafforzare Subito

- completare la copertura frontend sulle API backend principali
- aggiungere test su API future e servizi
- verificare build frontend in ambiente CI reale
- aggiungere test e smoke check su compose e health integrati

## Prossimi Passi Raccomandati

1. completare il frontend applicativo con UX piu vicina al dominio e dati seed piu utili
2. introdurre sync reale persistente dal NAS
3. collegare il permission engine ai dati persistiti
4. aggiungere seed iniziale gestito per dominio audit minimo
5. ampliare CI con test build/run piu vicini al runtime reale
6. aggiungere smoke check compose e runtime integrati

## Regola di Aggiornamento

Aggiornare questo file a ogni milestone o a ogni modifica che cambia uno di questi aspetti:

- stato di implementazione dei moduli
- test disponibili o risultati attesi
- rischi tecnici principali
- priorita operative successive
