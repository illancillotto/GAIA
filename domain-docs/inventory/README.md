# GAIA Inventario

> Regola modulo
> L'Inventario va implementato come modulo del monolite backend GAIA sotto `app/modules/inventory/`, con frontend in `frontend/src/app/inventory/`.

## Scopo

Questa directory raccoglie documentazione e materiale di lavoro del modulo Inventario.

## Regole strutturali

- nessun backend separato per il modulo
- frontend condiviso sotto `frontend/src/app/inventory/`
- backend condiviso sotto `backend/app/modules/inventory/`

## Runtime attuale

Il modulo backend `inventory` espone ora il perimetro iniziale di integrazione
WhiteCompany / Bonifica Oristanese per le richieste magazzino.

Componenti attivi:

- model SQLAlchemy `WarehouseRequest` in `backend/app/modules/inventory/models.py`
- schemi API in `backend/app/modules/inventory/schemas.py`
- servizio `sync_white_warehouse_requests()` in `backend/app/modules/inventory/services.py`
- router FastAPI in `backend/app/modules/inventory/router.py`

Endpoint attivi:

- `GET /api/inventory/warehouse-requests`
- `GET /api/inventory/warehouse-requests/{id}`

Il popolamento avviene tramite il provider `Bonifica Oristanese` del modulo
`elaborazioni`, usando l'entity `warehouse_requests` dell'orchestratore
`POST /elaborazioni/bonifica/sync/run`.
