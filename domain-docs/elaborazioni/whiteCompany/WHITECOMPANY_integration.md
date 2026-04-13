# WhiteCompany Integration — Note operative

> Stato documento: Prima bozza — 10 aprile 2026.
> Prodotto da analisi recon DevTools + HTML response.
> Sorgente primaria: codice runtime in `backend/app/modules/elaborazioni/bonifica_oristanese/`.

---

## Contesto tecnico

- **URL base**: `https://login.bonificaoristanese.it`
- **Stack server**: Laravel (cookie `laravel_session` + `XSRF-TOKEN`)
- **Auth**: form POST `/login` → cookie di sessione Laravel
- **Datatable**: tutte le liste usano jQuery DataTables in modalità server-side
- **Formato response**: JSON per endpoint `/datatable` e `/list`; HTML per le pagine di dettaglio/edit
- **CSRF**: ogni POST/PATCH/DELETE richiede `_token` (hidden field in ogni form, o header `X-CSRF-TOKEN`)
- **Keep-alive**: non necessario esplicitamente — la sessione Laravel dura finché il cookie è valido; verificare scadenza configurata sul sito (tipicamente 120 minuti)

---

## Flusso di autenticazione

```
GET  /login
  → estrai _token (hidden input nel form di login)

POST /login
  body: _token=<csrf>&email=<email>&password=<password>
  Content-Type: application/x-www-form-urlencoded
  → redirect 302 → imposta laravel_session + XSRF-TOKEN

Tutte le request successive:
  headers: Cookie: laravel_session=<val>; XSRF-TOKEN=<val>
  header X-XSRF-TOKEN: <val urlencoded> (per AJAX/XHR)
```

**Nota implementativa**: la sessione Laravel imposta sia `laravel_session` che `XSRF-TOKEN`.
Per le chiamate XHR (datatable/AJAX) il server valida `X-XSRF-TOKEN` nell'header oppure `_token` nel body.
`httpx` con `follow_redirects=True` e `cookies` gestisce tutto automaticamente.

---

## Struttura provider consigliata

```
backend/app/modules/elaborazioni/bonifica_oristanese/
  __init__.py
  session.py           ← login, test e sessione HTTP Laravel
  parsers.py           ← parser HTML comuni + utility extraction
  apps/
    client.py          ← fetch generico DataTables / detail page
    registry.py        ← mappa endpoint per feature
```

Route canonica esposta sotto `/elaborazioni/bonifica/...`, con alias compatibile `/elaborazioni/bonifica-oristanese/...`
Migration credenziali attuale: tabella `bonifica_oristanese_credentials`.

---

## Mappa azioni

### LOGIN

```
GET  /login
  → estrai campo: input[name="_token"]

POST /login
  body: _token, email, password
  risposta: redirect 302 + Set-Cookie laravel_session
  parsing: verifica redirect a /dashboard o simile; 
           se rimane su /login → credenziali errate
```

---

### AUTOMEZZI E ATTREZZATURE

#### Lista (DataTables paginata)

```
GET  /vehicles/datatable
  params DataTables standard: draw, start, length, search[value]
  params aggiuntivi: nessuno rilevato
  response: JSON DataTables
  data[i]: [0]=nome, [1]=targa/telaio, [2]=HTML con link edit/{id}
  parsing: estrarre id da href /vehicles/edit/{id}
  totale record: recordsTotal (229 nel campione)
```

#### Dettaglio singolo veicolo

```
GET  /vehicles/edit/{id}
  response: HTML
  campi estratti dal form:
    vehicle_id         → targa / n. telaio
    vehicle_name       → nome/modello
    vehicle_type       → 0=automezzo, 1=attrezzatura
    vehicle[km][start] → km iniziali
    vehicle[km][limit] → km limite
    vehicle_override_km_global         → bool
    vehicle_override_ask_km_overflow   → bool
  parsing: BeautifulSoup input[name=...]
```

---

### REGISTRO RIFORNIMENTI

#### Lista (DataTables paginata con filtri data)

```
GET  /vehicles/refuel/datatable
  params DataTables: draw, start, length
  params filtro:
    enable_date_filter  → 1
    date_start          → YYYY-MM-DD
    date_end            → YYYY-MM-DD
    filter_validity     → stringa opzionale
    filter_code[]       → targa/telaio (multi)
    filter_user[]       → operatore (multi)
  response: JSON DataTables
  data[i]: [0]=targa, [1]=operatore, [2]=data (DD/MM/YYYY HH:MM), [3]=lettura km, [4]=HTML azioni
  parsing: estrai id da href /vehicles/refuel/edit/{id}
  totale record: 5462 nel campione (aprile 2026)
```

**Nota**: il campo [3] può contenere HTML con icone warning (inserimento forzato).
Pulire con BeautifulSoup o regex prima di parsare il numero.

---

### REGISTRO PRESA IN CARICO AUTOMEZZI

#### Lista (DataTables paginata con filtri data)

```
GET  /vehicles/taken-charge/datatable
  params DataTables: draw, start, length
  params filtro:
    enable_date_filter  → 1
    date_start / date_end
    filter_code[]       → targa (multi)
    filter_validity     → opzionale
    filter_user[]       → operatore (multi, select2 AJAX)
  response: JSON DataTables (7 colonne)
  data[i]: [0]=targa, [1]=operatore, [2]=data_presa_in_carico,
           [3]=km_presa_in_carico, [4]=data_riconsegna,
           [5]=km_riconsegna, [6]=HTML azioni
  parsing: estrai id da href /vehicles/taken-charge/edit/{id}
```

**Nota operativa**: `filter_user[]` usa Select2 AJAX su `/contacts/search`
con `type=["employee"]`. Per filtrare è necessario conoscere l'id contatto.
In fase di fetch massivo ignorare il filtro e raccogliere tutto.

---

### ORGANIGRAMMI

#### Lista aree organigramma

```
GET  /areas/organizational-charts/list
  params DataTables standard
  response: JSON DataTables
  data[i]: [0]=nome_area, [1]=HTML azioni con id in href /edit/{id}
```

#### Dettaglio area organigramma

```
GET  /areas/organizational-charts/edit/{id}
  response: HTML (form)
  campi principali (da analisi HTML):
    name, description, color, referents
```

#### Lista utenti organigramma

```
GET  /users/organizational-charts/list
  params DataTables standard
  response: JSON DataTables
  data[i]: [0]=nome_area_utente, [1]=HTML azioni
```

#### Dettaglio utente organigramma

```
GET  /users/organizational-charts/edit/{id}
  response: HTML (form)
  parsing: BeautifulSoup
```

---

### TIPOLOGIE DI SEGNALAZIONE

```
GET  /reports/types/datatable
  params DataTables: draw, start, length
  params aggiuntivi: filter_usage (opzionale)
  response: JSON DataTables
  data[i]: [0]=nome_tipo, [1]=aree_associate (stringa CSV), [2]=HTML azioni
  parsing: estrai id da href /reports/types/edit/{id}
  totale: 38 nel campione
```

#### Dettaglio tipologia

```
GET  /reports/types/edit/{id}
  response: HTML (form)
  campi: nome, aree assegnate, colore, flag utilizzo
```

---

### UTENTI (operatori + consorziati)

#### Lista con filtri

```
GET  /users/list
  params DataTables: draw, start, length
  params filtro:
    filter_role     → "" | "Acquaiolo" | "Admin" | "Consorziato" | altri ruoli
    filter_enabled  → "" | "1" (abilitati) | "0" (disabilitati)
  response: JSON DataTables (5 colonne)
  data[i]: [0]=nome/ragione_sociale, [1]=ruolo, [2]=email HTML,
           [3]=HTML stato (check verde), [4]=HTML azioni con id in href /users/{id}
  parsing: estrai id da href /users/{id}
  totale: 560 abilitati nel campione
```

#### Dettaglio utente

```
GET  /users/{id}
  response: HTML (form)
  campi estratti:
    username            → nome utente
    email               → email di accesso
    user_type           → "company" | "private"
    business_name       → ragione sociale (se company)
    first_name          → nome (se private)
    last_name           → cognome (se private)
    tax                 → CF / P.IVA
    contact_phone       → telefono fisso
    contact_mobile      → cellulare
    contact_description → note
    enabled             → bool (checkbox)
    roles               → select (ruolo)
    type                → select (tipo account)
  parsing: BeautifulSoup input/select/textarea
```

**Regola di integrazione con modulo `utenze`**:
- Ruolo `Consorziato` → candidato per `ana_subjects` del modulo utenze
- Ruoli operativi (Acquaiolo, Admin, Tecnico, ecc.) → solo in `bonifica_users` locale
- Prima dell'import verificare match per `tax` (CF/PIVA) in `ana_subjects`
- Se trovato: confronto campi → flag `wc_data_mismatch` se ci sono discrepanze
- Se non trovato: staging in tabella separata `bonifica_user_staging` in attesa di revisione manuale
- Non creare automaticamente soggetti in `ana_subjects` senza approvazione

---

### AREE TERRITORIALI

#### Lista aree (pagina HTML, datatable separata)

```
GET  /areas/datatable
  params DataTables: draw, start, length
  response: JSON DataTables
  data[i]: [0]=nome_area, [1...]=altri campi, [n]=HTML azioni
```

#### Dettaglio area

```
GET  /areas/edit/{id}
  response: HTML (form)
  campi estratti:
    name               → nome area
    area_color         → colore HEX
    area_is_district   → bool (è distretto)
    description        → testo libero
    areas_users_assign_mode → "check" | "chart"
    areas_referents[]  → lista referenti (select multi)
    areas_charts[]     → organigrammi associati
    area_position_lat  → lat GPS (può essere vuoto)
    area_position_lng  → lng GPS
    area_polygon       → polygon GeoJSON o WKT (può essere vuoto)
```

---

### SEGNALAZIONI (esportazione)

#### Lista con filtri data e tipo

```
GET  /statistics/export-reports-datatable
  params DataTables: draw, start, length (21 colonne)
  params filtro:
    enable_date_filter  → 1
    date_start / date_end → YYYY-MM-DD
    show_archived       → 0 | 1
    report_type_filter  → id tipo segnalazione (opzionale)
    area_filter         → id area (opzionale)
    export_details      → "simplified" | "detailed"
  response: JSON DataTables (21 colonne)
  data[i] (indici significativi):
    [0]  = id segnalazione
    [1]  = tipo segnalazione
    [2]  = urgente (Si/No)
    [3]  = testo/descrizione
    [4]  = operatore che ha inserito
    [5]  = distretto/area
    [6]  = data (DD/MM/YYYY HH:MM)
    [7]  = lat
    [8]  = lng
    [9]  = foto (url o vuoto)
    [10] = allegati
    [11] = flag (0/1)
    [12] = prese_in_carico (count)
    [13] = completate (count)
    [14] = altro_count
    [15] = archiviata (Si/No)
    [16] = allegato_2
    [17] = stato (Non presa in carico / In lavorazione / ...)
    [18] = operatori_notificati (lista nomi separati da virgola)
    [19] = campo extra
    [20] = campo extra
  totale: 826 nel campione aprile 2026
```

---

### RICHIESTE MAGAZZINO

```
GET  /warehouse-requests/datatable
  params DataTables: draw, start, length
  params filtro:
    enable_date_filter / date_start / date_end
    enable_report_date_filter / report_date_start / report_date_end
    user_filter         → id utente
    area_filter         → id area
    show_archived       → "all" | "1" | "0"
    show_status         → "all" | "1" | "0"
  response: JSON DataTables (6 colonne)
  data[i]: [0]=id_segnalazione_ref, [1]=tipo_segnalaz, [2]=segnalato_da,
           [3]=richiesta_da, [4]=data_segnalaz, [5]=data_richiesta
```

**Nota runtime GAIA**: il sync attuale importa queste righe nel modulo `inventory`
come `warehouse_request` tramite l'entity `warehouse_requests` di
`POST /elaborazioni/bonifica/sync/run`. Gli endpoint applicativi esposti sono:

```
GET  /api/inventory/warehouse-requests
GET  /api/inventory/warehouse-requests/{id}
```

In assenza di un `wc_id` nativo nel datatable White, il runtime usa un
identificativo deterministico derivato dal contenuto della riga per garantire
idempotenza sugli import successivi.

---

## Endpoint di ricerca contatti (utile per filtri)

```
GET  /contacts/search
  params: q=<stringa> (min 3 char), type[]=employee | consorziato, page=1
  response: JSON array
  item: { id, fullName, signboard, city, phone, mobile, email, fiscalCode, vatNumber }
```

---

## Strategia di paginazione DataTables

Tutti gli endpoint `/datatable` e `/list` sono server-side:

```python
async def fetch_all_pages(session, url, extra_params=None, page_size=250):
    """Recupera tutte le pagine di un endpoint DataTables."""
    start = 0
    records = []
    while True:
        params = build_dt_params(draw=start//page_size+1, start=start, length=page_size)
        if extra_params:
            params.update(extra_params)
        r = await session.get(url, params=params)
        data = r.json()
        records.extend(data["data"])
        if start + page_size >= data["recordsTotal"]:
            break
        start += page_size
    return records, data["recordsTotal"]
```

`build_dt_params` deve generare i campi `columns[N][data]`, `columns[N][searchable]`, ecc.
Un helper condiviso in `backend/app/modules/shared/datatable_helpers.py` evita la duplicazione.

---

## Parser HTML — pattern comune

```python
from bs4 import BeautifulSoup

def parse_form_fields(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    for inp in soup.find_all(["input", "select", "textarea"]):
        name = inp.get("name")
        if not name or name in ("_token", "_method"):
            continue
        if inp.name == "input":
            result[name] = inp.get("value", "")
        elif inp.name == "select":
            selected = inp.find("option", selected=True)
            result[name] = selected["value"] if selected else ""
        elif inp.name == "textarea":
            result[name] = inp.get_text()
    return result
```

---

## Credenziali — gestione

- Tabella: `bonifica_oristanese_credentials`
- Cifratura: `CREDENTIAL_MASTER_KEY` (stessa chiave vault SISTER/Capacitas)
- Schema: `id`, `label`, `email`, `password_enc`, `active`, `last_used_at`, `consecutive_failures`
- Auto-disable dopo N fallimenti consecutivi (configurabile, default 5)

---

## Endpoints GAIA esposti

```
POST   /elaborazioni/bonifica/credentials
GET    /elaborazioni/bonifica/credentials
GET    /elaborazioni/bonifica/credentials/{id}
PATCH  /elaborazioni/bonifica/credentials/{id}
DELETE /elaborazioni/bonifica/credentials/{id}
POST   /elaborazioni/bonifica/credentials/{id}/test

POST   /elaborazioni/bonifica/sync/run             ← orchestratore sync Bonifica
GET    /elaborazioni/bonifica/sync/status          ← stato ultima sync per entity
```

### Stato implementazione endpoint sync

- `POST /elaborazioni/bonifica/sync/run` crea un `wc_sync_job` per ogni entity richiesta
- `GET /elaborazioni/bonifica/sync/status` legge l'ultimo job persistito per entity e restituisce `never` solo come stato derivato della response quando non esistono run precedenti
- Entity attive su runtime: `report_types`, `reports`, `vehicles`, `refuels`, `taken_charge`, `users`, `areas`
- `refuels` usa parsing difensivo del dettaglio `GET /vehicles/refuel/edit/{id}`: i record senza litri validi vengono saltati, non inventati
- `users` sincronizza oggi solo gli operatori WhiteCompany non `Consorziato`, con upsert locale su tabella `wc_operator` e collegamento opzionale a `application_users` via email
- `areas` sincronizza la lookup geografica WhiteCompany in tabella `wc_area`
- API attiva lato operazioni: `GET /operazioni/operators`, `GET /operazioni/operators/{id}`
- API attiva lato operazioni: `GET /operazioni/areas`, `GET /operazioni/areas/{id}`
- Fasi successive pianificate ma non ancora attive su runtime: `warehouse`

---

## Mount in router

In `backend/app/modules/elaborazioni/router.py`:

```python
from app.modules.elaborazioni.bonifica_oristanese_routes import router as bonifica_router
router.include_router(bonifica_router, prefix="/elaborazioni/bonifica")
router.include_router(bonifica_router, prefix="/elaborazioni/bonifica-oristanese")
```

---

## TODO

- [ ] Verificare durata sessione Laravel (controllare `SESSION_LIFETIME` in `.env` del sito)
- [ ] Verificare se `/areas/datatable` restituisce le stesse aree di `/areas/organizational-charts/list` (sembrano entità diverse: aree geografiche vs aree org)
- [ ] Implementare `bonifica_user_staging` + logica mismatch con `ana_subjects`
- [ ] Verificare in produzione l'insieme completo dei field names del dettaglio rifornimento `GET /vehicles/refuel/edit/{id}` per ridurre gli skip dei record senza litri
- [ ] Verificare endpoint dettaglio presa in carico: `GET /vehicles/taken-charge/edit/{id}`
- [ ] Mappare endpoint segnalazioni individuali (non solo export bulk): `GET /reports/{id}` (da verificare)
- [ ] Estendere `POST /elaborazioni/bonifica/sync/run` alle entity restanti (`warehouse`)
- [ ] Aggiungere il link strutturato `field_report.wc_area_id` per collegare le segnalazioni alle aree sincronizzate
- [ ] Portare lo stato sync Bonifica nel workspace frontend `/elaborazioni/settings`

---

## Regole di manutenzione

- Se cambiano i selettori HTML del form login, aggiornare `session.py`
- Se cambiano le colonne DataTables, aggiornare gli indici nei parser
- Se la struttura dei campi HTML dei form di dettaglio cambia, aggiornare `parse_form_fields` per ogni entity
- Il `_token` CSRF cambia ad ogni sessione — non cachearlo tra sessioni diverse
