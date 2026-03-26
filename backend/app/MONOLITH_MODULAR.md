# GAIA Backend — Monolite Modulare

> Regola vincolante
> Nessuna nuova feature backend deve nascere nei path legacy fuori da `app/modules/`, salvo wrapper di compatibilita.

> Path fisico corrente
> Il backend condiviso della piattaforma vive in `backend/`.

## Struttura target

Il backend GAIA resta un singolo servizio FastAPI con:

- autenticazione condivisa
- database PostgreSQL unico
- Alembic unico
- router per modulo
- worker/container separati solo per compiti tecnici specializzati

Struttura applicativa target:

```text
app/
  modules/
    core/
    accessi/
    network/
    inventory/
    catasto/
  core/
  db/
  api/
```

## Stato attuale del refactor

- `core`, `accessi`, `catasto`, `network` introdotti sotto `app/modules/`
- `network` migrato nella nuova struttura canonica
- `accessi` migrato a livello di route canoniche in `app/modules/accessi/routes/`
- `accessi` dotato anche di entrypoint canonici `models.py`, `schemas.py`, `services.py`, `repositories.py`
- `catasto` migrato a livello di route implementation canonica e surface di modulo (`models.py`, `schemas.py`, `services.py`, `routes.py`)
- i vecchi path `app/api/routes/network.py`, `app/models/network.py`,
  `app/schemas/network.py`, `app/services/network_*.py` restano come wrapper compatibili
- i vecchi path `app/api/routes/auth.py`, `audit.py`, `sync.py`, `permissions.py`,
  `admin_users.py`, `section_permissions.py` restano come wrapper compatibili

## Regole

- nuovi moduli backend vanno creati in `app/modules/<modulo>/`
- i package legacy fuori da `app/modules/` vanno considerati area di compatibilita
- `app/api/router.py` include i router di modulo, non i router di dettaglio
