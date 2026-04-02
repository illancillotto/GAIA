# CAPACITAS Integration — Note operative

> Stato documento
> Documento importato e riallineato al repository GAIA il 2 aprile 2026.
> La sorgente primaria resta il codice runtime in `backend/app/...`.

## Stato

- Modulo: `backend/app/modules/catasto/capacitas/`
- Service: `backend/app/services/catasto_capacitas.py`
- Routes: `backend/app/modules/catasto/capacitas_routes.py`
- Migration: `backend/alembic/versions/20260402_0027_capacitas_credentials.py`

## Decoder risposta

Le risposte di `ajaxRicerca.aspx` (e altri endpoint AJAX) sono Base64 + compressione
custom decodificata lato browser da:

```
/script/js-deflate/jquery.base64.min.js
/script/js-deflate/rawinflate.js
/script/custom.js   ← funzione Ajax() e Grid.LoadV2()
```

Lo step di decoder non e piu bloccante: il decoder e stato portato nel progetto in:

`backend/app/modules/catasto/capacitas/decoder.py`

### Payload di test

```
SZ7VLLbtswEPwV3nwJYfEhkepNlptCgGMbihMEKAqUIlcpAVsMaLmHFP2yHvpJ/YVyHdvpNUWP3YM0uzucXSzm14+fH8m3Zv6OTLiShQPGqAGlqOz6nppOldQJ6wxnrtCynFyRZv5QLavEz/qyE6UD6nTeU6nyjHagLe1sntnCaa7AJP7taMaA9ITXZox+FwaPBfoSK0qxEx9TSSQ09wnIBDbrBPCPwwiOXt/XKFSqhOvVDe6s8Uldr7BeZbrgRYmDrqN5Rj2OC9gvgG2MlM5g2/sQsfS+VEiow+4wYH5Tte3drLnDLWAIOz+YZx+OrXWI9kCqLez3ZnAxIMWMZmn21o/meL0py6as1Ki4OITH8Nqrqw+Lpmqb4yznLVz7vTXbo25bL26XmrdczUQuZ0iBOFab08XmYMEd/jhgHJNm8xVlyWvgmfwYtoGhZgxP0cNoPhM2lZfWwnfsdNFzzl/y5QZihAEPP/l+RU5+kHkOwDOgQjhGpbZAu1L2NNdCFpmUJn3/pR829BwXP/CzH/hf+kHlgov/frj4gU/FW/1APv0G
```

Ricerca effettuata: CF `PRCLSN82R27B354B` (tipo=2), risultato atteso: 2 righe (Porcu Alessandro).

## Flusso SSO — riepilogo

```
GET  sso.servizicapacitas.com/pages/login.aspx
  → estrai __VIEWSTATE, __EVENTVALIDATION

POST sso.servizicapacitas.com/pages/login.aspx
  body: username + password + viewstate
  → redirect a /pages/main.aspx?token=<UUID>

GET  involture1.servizicapacitas.com/pages/main.aspx?token=<UUID>&app=involture&tenant=
  → imposta cookie involture__AUTH_COOKIE

POST involture1.servizicapacitas.com/pages/ajax/ajaxRicerca.aspx
  body: q=<CF_urlenc>&tipo=ricanag&soloConBeni=false&opz=2
  headers: X-Requested-With: XMLHttpRequest
  → risposta Base64+compress

POST */pages/handler/handlerKeepSessionAlive.ashx  ogni 25s
```

## Credenziali — gestione

- Tabella: `capacitas_credentials`
- Cifratura: `CREDENTIAL_MASTER_KEY` (stessa del vault SISTER)
- Rotazione: `pick_credential()` seleziona la meno usata di recente, attiva, nella fascia oraria
- Fascia oraria: `allowed_hours_start`–`allowed_hours_end` (ora locale server)
- Auto-disable: dopo `_MAX_CONSECUTIVE_FAILURES` (default 5) fallimenti consecutivi

## Endpoints esposti

```
POST   /catasto/capacitas/credentials
GET    /catasto/capacitas/credentials
GET    /catasto/capacitas/credentials/{id}
PATCH  /catasto/capacitas/credentials/{id}
DELETE /catasto/capacitas/credentials/{id}
POST   /catasto/capacitas/credentials/{id}/test

POST   /catasto/capacitas/involture/search
```

## Mount in router.py

In `backend/app/modules/catasto/router.py` aggiungere:

```python
from app.modules.catasto.capacitas_routes import router as capacitas_router
router.include_router(capacitas_router)
```

## TODO successivi

- [ ] Verificare nomi campi form login (`Capacitas$ContentMain$txtUsername` ecc.)
- [ ] Aggiungere endpoint `/involture/search` con paginazione/cache opzionale
- [ ] Implementare `incass_routes.py` per inCASS
- [ ] Implementare `bollettini_routes.py` per inBOLLETTINI
- [ ] Frontend: pagina `/catasto/settings` → tab "Capacitas" con gestione credenziali
