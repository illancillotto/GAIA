# Progress

> Nota stato
> Il refactor strutturale di GAIA converge su `app/modules/<modulo>/` come layout canonico del backend condiviso.

## Data Riferimento

- ultima analisi repository: 2026-03-20

## Stato Generale

Il repository e in una fase di bootstrap avanzato: la base documentale, il backend, il frontend, il setup Docker e la CI minima sono presenti e coerenti. Il progetto ha ora dodici capability backend reali: autenticazione applicativa con JWT, bootstrap admin idempotente, bootstrap dominio audit idempotente, dominio audit minimo in sola lettura, sync persistente minimale da payload testuale, live apply singolo via SSH, job/script di live sync con retry controllato, audit trail persistente delle sync, metadata operativi sui sync run, scheduling operativo minimale, backoff configurabile dei retry, skeleton di integrazione NAS con parser iniziali e permission engine MVP con preview di calcolo. Sul frontend la milestone applicativa e in avanzamento concreto: login reale, stato sessione, dashboard collegata, viste utenti e gruppi NAS e prime viste backend-driven principali, inclusa la pagina `Sync` operativa con storico run esteso.

## Completato

### Repository e Convenzioni

- file root inizializzati: `README.md`, `.gitignore`, `.editorconfig`, `.env.example`, `Makefile`
- naming coerente tra `backend/`, `frontend/`, `domain-docs/accessi/docs/`, `scripts/`, `nginx/`
- documentazione iniziale centralizzata in `domain-docs/accessi/docs/`

### Backend

- scaffold FastAPI avviabile
- routing modulare base in `backend/app/api`
- endpoint `GET /health` disponibile
- endpoint `POST /auth/login` e `GET /auth/me`
- endpoint protetti `GET /dashboard/summary`, `GET /nas-users`, `GET /nas-groups`, `GET /shares`, `GET /reviews`
- endpoint protetti `GET /sync/capabilities` e `POST /sync/preview`
- endpoint protetto `POST /sync/apply` con persistenza di snapshot, dominio e permission engine derivato
- endpoint protetto `POST /sync/live-apply` con acquisizione SSH e fallback di errore controllato
- endpoint protetto `GET /sync-runs` per audit trail sync
- endpoint protetti `POST /permissions/calculate-preview` e `GET /effective-permissions`
- configurazione centralizzata con `pydantic-settings`
- utility di sicurezza per password hash e token JWT
- modello `ApplicationUser`
- modelli `NasUser`, `NasGroup`, `Share`, `Review`
- modelli `PermissionEntry` ed `EffectivePermission`
- bootstrap admin idempotente via script backend e target Makefile
- config NAS centralizzata e client skeleton
- parser iniziali per passwd, group, share listing e ACL
- parser ACL corretti per soggetti `user:<name>` e `group:<name>`
- servizio di calcolo permessi con regole `deny` e `write implies read`
- bootstrap dominio audit idempotente via script backend e target Makefile
- servizio di sync persistente minimale da input testuale
- connector SSH live con `paramiko` e comandi configurabili
- job backend di live sync con retry configurabile e script dedicato
- modello persistente `sync_runs` con migration dedicata
- metadata `duration_ms`, `initiated_by`, `source_label` sui sync run
- runner schedulato configurabile via env e script dedicato
- backoff retry configurabile `fixed` o `exponential`
- struttura Alembic presente con migration iniziale `snapshots`
- seconda migration per `application_users`
- terza migration per il dominio audit minimo
- quarta migration per il permission engine MVP
- staging WhiteCompany per organigrammi in `wc_org_chart` e `wc_org_chart_entry`
- servizio backend `sync_white_org_charts()` integrato nell'orchestratore Bonifica

### Frontend

- scaffold Next.js con App Router
- layout base in `src/app/layout.tsx`
- pagina home collegata a `GET /auth/me` e `GET /dashboard/summary`
- pagina `/login` collegata a `POST /auth/login`
- viste backend-driven per utenti NAS, gruppi NAS, share, review, sync ed effective permissions
- pagina `Sync` con form testuale per preview e apply persistente
- pagina `Sync` predisposta anche per live apply via backend
- pagina `Sync` con storico run backend-driven
- pagina `Sync` con metadata operativi dei run
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
- stato corrente: `59 passed`

Verifica runtime:

- `docker compose up -d --build`
- `docker compose exec backend alembic upgrade head`
- `docker compose exec backend python scripts/bootstrap_admin.py`
- `docker compose exec backend python scripts/bootstrap_domain.py`
- `POST /sync/preview` e `POST /sync/apply` verificati contro stack locale
- `GET /sync/capabilities` verificato con supporto live attivo
- `POST /sync/live-apply` verificato contro stack locale con `503` esplicito per NAS non raggiungibile
- script `python scripts/live_sync.py` verificato contro stack locale con fallimento controllato
- `POST /sync/apply` verificato con creazione record audit in `sync_runs`
- `GET /sync-runs` verificato contro stack locale
- `python scripts/scheduled_live_sync.py` verificato con ciclo singolo e record audit completo
- backoff retry verificato con test unitari su modalita `fixed`, `exponential` e cap massimo
- login reale verificato su `POST /auth/login`
- query reali verificate su `/dashboard/summary`, `/nas-users`, `/nas-groups`, `/shares`, `/reviews`, `/effective-permissions`

Copertura attuale:

- health endpoint
- login e current user
- dashboard summary e liste dominio audit
- sync capabilities, preview NAS e apply persistente
- live apply via SSH con gestione errore controllata
- job di live sync con retry testato
- audit trail sync persistente esposto via API
- metadata e scheduling operativo minimale verificati
- policy di backoff verificata
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
- servizio sync persistente e frontend collegato
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
- integrazione NAS live disponibile ma non ancora verificata contro host reale raggiungibile
- permission engine alimentato da sync persistente e live apply, ma senza scheduling o sync incrementale
- frontend collegato a molte API di lettura e alla sync, ma non ancora completo sul dominio
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
- la sync persistente puo gia popolare snapshot e permessi effettivi senza dipendere da seed manuali
- la live sync fallisce in modo esplicito e gestito quando il NAS non e raggiungibile
- il progetto espone gia un entrypoint operativo `make live-sync` per esecuzione manuale o schedulata
- le sync applicate sono ora tracciate in modo persistente con esito e tentativi
- il progetto espone anche un runner schedulato configurabile per la live sync
- il retry della live sync non e piu a pausa fissa: supporta backoff configurabile e jitter opzionale
- stack Docker del progetto verificato end-to-end in ambiente locale
- test iniziali gia utili per evitare regressioni di scaffold

### Punti da Rafforzare Subito

- completare la copertura frontend sulle API backend principali
- aggiungere test su API future e servizi
- verificare build frontend in ambiente CI reale
- aggiungere test e smoke check su compose e health integrati

## Prossimi Passi Raccomandati

1. verificare la live sync contro un host NAS reale o staging
2. introdurre persistenza dello scheduler
3. completare il frontend applicativo con UX piu vicina al dominio operativo
4. ampliare CI con test build/run piu vicini al runtime reale
5. verificare la live sync contro un NAS reale o staging

## Regola di Aggiornamento

Aggiornare questo file a ogni milestone o a ogni modifica che cambia uno di questi aspetti:

- stato di implementazione dei moduli
- test disponibili o risultati attesi
- rischi tecnici principali
- priorita operative successive

- 2026-03-24: Milestone 8 avviata: introdotto sistema moduli/ruoli/sezioni con resolver permessi e API admin utenti.
