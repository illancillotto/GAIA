# GAIA Organigramma

## Stato

Modulo canonico implementato su:

- backend: `backend/app/modules/organigramma/`
- frontend: `frontend/src/app/organigramma/page.tsx`
- migration principale: `backend/alembic/versions/20260608_0134_organigramma_canonical_layer.py`

## Obiettivo

Fornire una verita canonica per la struttura organizzativa di GAIA senza
trasformare WhiteCompany nella fonte di verita applicativa.

Decisione architetturale adottata:

- nuove tabelle canoniche GAIA come fonte primaria
- WhiteCompany come sorgente esterna
- bridge verso dati legacy `operazioni` e `wc_*`
- override manuali non sovrascritti dal sync se il link sorgente e bloccato

## Modello dati canonico

Tabelle principali:

- `org_unit`: albero unita organizzative (`direzione|distretto|settore|squadra`)
- `org_assignment`: assegnazione `application_user -> org_unit` con manager diretto e title operativo
- `org_visibility_override`: eccezioni esplicite di visibilita
- `org_source_link`: mapping idempotente con sorgenti WhiteCompany

Vincoli chiave:

- `application_users.id` resta `Integer` e tutte le FK verso utenti usano `Integer`
- PK canoniche `org_*` in `Uuid`
- `title` operativo non coincide con ruolo RBAC
- solo `super_admin` bypassa la visibilita; `admin` no

## RBAC e visibilita

Sono due layer distinti.

RBAC sezione/modulo:

- flag utente `module_organigramma`
- sezione `organigramma.read`
- sezione `organigramma.manage`

Visibilita dati:

- base gerarchica: un viewer vede le unita dove e manager diretto dei membri e tutti i discendenti
- override: un viewer puo ricevere visibilita aggiuntiva su un utente o su un sottoalbero
- la provenienza della visibilita e tracciata come `gerarchia` oppure `override`

## API principali

Prefix modulo: `/organigramma`

Read:

- `GET /units/tree`
- `GET /units`
- `GET /units/{id}`
- `GET /assignments`
- `GET /visibility/{user_id}`

Manage:

- `POST|PUT|DELETE /units`
- `POST|PUT|DELETE /assignments`
- `GET|POST|PUT|DELETE /overrides`
- `POST /sync/whitecompany`

Il router applica:

- `require_module("organigramma")` a livello modulo
- `require_section("organigramma.read")` o `require_section("organigramma.manage")` per route

## Frontend

La pagina canonica e `/organigramma` e include:

- albero ricorsivo espandibile
- dettaglio unita con responsabile e assegnazioni
- evidenza della provenienza `manuale|whitecompany|bridge_team`
- pannello override
- simulatore "Chi vede chi"

Tipi frontend:

- `frontend/src/types/api.ts`
- `frontend/src/types/organigramma.ts`

Client API:

- `frontend/src/lib/api.ts`

## Sync WhiteCompany

Stato attuale:

- sync unita da `wc_area` implementato
- sync assegnazioni operatori lasciato come follow-up documentato

Regole MVP:

- mapping idempotente via `org_source_link`
- righe con `is_manual_locked=True` non sovrascritte
- `last_synced_at` aggiornato sui link processati

## Test e verifica

Backend:

- `backend/tests/organigramma/test_visibility_service.py`
- `backend/tests/organigramma/test_schemas.py`
- `backend/tests/organigramma/test_api.py`
- `backend/tests/test_bootstrap_admin.py`
- `backend/tests/test_section_permissions.py`

Frontend:

- `frontend/tests/unit/organigramma-helpers.test.ts`
- `frontend/tests/unit/organigramma-page.test.tsx`

Comandi usati per la verifica locale:

```bash
cd backend && pytest tests/organigramma tests/test_bootstrap_admin.py tests/test_section_permissions.py -q
cd frontend && npm run typecheck
cd frontend && npm run test:unit -- tests/unit/organigramma-helpers.test.ts tests/unit/organigramma-page.test.tsx
cd backend && ./.venv/bin/python -m alembic heads
docker compose exec -T backend sh -lc 'python -m alembic current && python -m alembic upgrade head'
```

Esito di riferimento alla chiusura:

- head Alembic corrente: `20260608_0135`
- catena rilevante: `20260608_0133 -> 20260608_0134 -> 20260608_0135`
