# GAIA — Catasto GIS
## GSD Sequential Implementation Prompt
### Per Claude Code — 10 Step Sequenziali

---

> **Prima di iniziare**: Leggi i documenti di riferimento in `domain-docs/catasto/docs/`:
> - `GAIA_CATASTO_GIS_ARCHITECTURE_v1.md`
> - `GAIA_CATASTO_GIS_BACKEND_CODEX_v1.md`
> - `GAIA_CATASTO_GIS_FRONTEND_CODEX_v1.md`
>
> Il modulo catasto Fase 1 è completato. Stai **estendendo** il modulo esistente.
> **Non modificare** nulla che non sia esplicitamente citato in ogni step.

---

## STEP 1 — Migration: view cat_particelle_current

**Obiettivo**: Creare la view PostgreSQL che Martin userà come sorgente tiles.

**Azione**:
Crea una nuova migration Alembic in `backend/alembic/versions/` con nome `xxxx_catasto_gis_view.py`.

Il `Revises` deve puntare alla revision ID della migration Catasto Fase 1 esistente. Cerca in `backend/alembic/versions/` la migration che contiene `cat_particelle` nel nome o nel corpo.

Contenuto migration: vedi BACKEND CODEX Step B1.

Esegui la migration:
```bash
docker compose exec backend alembic upgrade head
```

Verifica:
```bash
docker compose exec postgres psql -U gaia -d gaia -c "SELECT COUNT(*) FROM cat_particelle_current;"
```

**Acceptance**:
- Migration eseguita senza errori
- `SELECT COUNT(*) FROM cat_particelle_current` restituisce un risultato (può essere 0 se DB non ancora popolato)
- `\d cat_particelle_current` mostra le colonne inclusa `geometry` e `ha_anomalie`

---

## STEP 2 — Infrastruttura Martin

**Obiettivo**: Aggiungere Martin al docker-compose e configurarlo.

**Azioni**:

1. Crea `config/martin.toml` — vedi BACKEND CODEX Step B5.1

2. Modifica `docker-compose.yml` — aggiungi servizio `martin` — vedi BACKEND CODEX Step B5.2

3. Modifica `nginx/nginx.conf` — aggiungi location `/tiles/` — vedi BACKEND CODEX Step B5.3

4. Avvia e verifica:
```bash
docker compose up martin -d
docker compose logs martin --tail=20
curl http://localhost/tiles/catalog
```

**Acceptance**:
- `docker compose logs martin` mostra "Martin is ready"
- `curl http://localhost/tiles/catalog` → JSON (non errore connessione)
- `curl http://localhost/tiles/cat_distretti/9/260/197` → risposta (200 o 204, non 502)

---

## STEP 3 — Schemas Pydantic GIS

**Obiettivo**: Creare i tipi Pydantic per il modulo GIS backend.

**Azione**:
Crea `backend/app/modules/catasto/schemas/gis_schemas.py` — vedi BACKEND CODEX Step B2 per il contenuto completo.

Se la directory `schemas/` non esiste nel modulo catasto, creala con `__init__.py` vuoto.

Verifica che l'import funzioni:
```bash
docker compose exec backend python -c "
from app.modules.catasto.schemas.gis_schemas import GisSelectRequest, GisSelectResult
print('OK')
"
```

**Acceptance**:
- Import senza errori
- `GisSelectRequest(geometry={"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]]]})` → OK
- `GisSelectRequest(geometry={"type":"Point","coordinates":[0,0]})` → `ValidationError`

---

## STEP 4 — Service GIS (gis_service.py)

**Obiettivo**: Implementare la logica PostGIS server-side.

**Azione**:
Crea `backend/app/modules/catasto/services/gis_service.py` — vedi BACKEND CODEX Step B3 per il contenuto completo.

Verifica che `shapely` sia disponibile nel container:
```bash
docker compose exec backend python -c "import shapely; print(shapely.__version__)"
```

Se mancante, aggiungi `shapely>=2.0` a `backend/requirements.txt` e ricostruisci:
```bash
docker compose build backend
docker compose up backend -d
```

Verifica import service:
```bash
docker compose exec backend python -c "
from app.modules.catasto.services import gis_service
print('OK')
"
```

**Acceptance**:
- Import senza errori
- `shapely` disponibile nel container

---

## STEP 5 — Route GIS (gis.py) e registrazione

**Obiettivo**: Esporre gli endpoint GIS su FastAPI.

**Azioni**:

1. Crea `backend/app/modules/catasto/routes/gis.py` — vedi BACKEND CODEX Step B4.

2. Trova il file dove vengono registrati i router del modulo catasto. Cerca pattern come:
   ```python
   app.include_router(catasto_distretti_router)
   ```
   o un file `__init__.py` del modulo che aggrega i router.

3. Aggiungi la registrazione del router GIS seguendo lo stesso pattern esistente.

4. Riavvia il backend e verifica:
```bash
docker compose restart backend
curl http://localhost/api/catasto/gis/select \
  -H "Content-Type: application/json" \
  -d '{"geometry":{"type":"Polygon","coordinates":[[[8.0,39.0],[9.0,39.0],[9.0,40.0],[8.0,40.0],[8.0,39.0]]]}}}'
```
(Senza token JWT restituirà 401 — questo è corretto)

Verifica in Swagger:
```
http://localhost/api/docs
```
→ Cerca sezione `catasto-gis` con 3 endpoint.

**Acceptance**:
- `GET /api/docs` mostra i 3 endpoint GIS
- `POST /catasto/gis/select` senza JWT → `401`
- `GET /catasto/gis/particella/nonexistent/popup` senza JWT → `401`

---

## STEP 6 — Installazione dipendenze npm frontend

**Obiettivo**: Aggiungere MapLibre GL e Drawing tools al frontend.

**Azioni**:
```bash
docker compose exec frontend npm install maplibre-gl @mapbox/maplibre-gl-draw
docker compose exec frontend npm install -D @types/mapbox__maplibre-gl-draw @types/geojson
```

Oppure se lavori in locale:
```bash
cd frontend
npm install maplibre-gl @mapbox/maplibre-gl-draw
npm install -D @types/mapbox__maplibre-gl-draw @types/geojson
```

Aggiungi CSS import in `frontend/src/app/globals.css`:
```css
@import 'maplibre-gl/dist/maplibre-gl.css';
@import '@mapbox/maplibre-gl-draw/dist/maplibre-gl-draw.css';
```

Se necessario, aggiorna `next.config.js` per alias webpack — vedi FRONTEND CODEX Step F1.

Verifica build TypeScript:
```bash
docker compose exec frontend npm run build 2>&1 | grep -i error | head -20
```

**Acceptance**:
- `npm install` completato senza errori
- `npm run build` senza errori relativi a maplibre o mapbox

---

## STEP 7 — Tipi TypeScript GIS e hook useGisSelection

**Obiettivo**: Creare types e hook condivisi per il GIS frontend.

**Azioni**:

1. Crea `frontend/src/types/gis.ts` — vedi FRONTEND CODEX Step F2.

2. Crea `frontend/src/hooks/useGisSelection.ts` — vedi FRONTEND CODEX Step F3.

   **Nota importante**: Nel hook, adatta il recupero del token JWT al meccanismo esistente nel progetto. Guarda come le altre pagine catasto fanno le chiamate API autenticate. Cerca pattern come `useSession`, `useAuth`, cookie httpOnly, o header passati automaticamente.

Verifica TypeScript:
```bash
docker compose exec frontend npx tsc --noEmit 2>&1 | head -30
```

**Acceptance**:
- Nessun errore TypeScript sui file creati
- Import di `GisSelectResult` funzionante in altri file

---

## STEP 8 — Componenti GIS: DrawingTools, AnalysisPanel, SelectionPanel

**Obiettivo**: Creare i componenti UI del pannello analisi (non la mappa).

**Azioni**:
Crea la directory `frontend/src/components/catasto/gis/` e i 3 componenti:

1. `DrawingTools.tsx` — vedi FRONTEND CODEX Step F5
2. `AnalysisPanel.tsx` — vedi FRONTEND CODEX Step F6
3. `SelectionPanel.tsx` — vedi FRONTEND CODEX Step F7

Questi componenti non dipendono da MapLibre GL e non richiedono `ssr: false`.

Verifica TypeScript:
```bash
docker compose exec frontend npx tsc --noEmit 2>&1 | grep -i "gis" | head -20
```

**Acceptance**:
- Nessun errore TypeScript
- I componenti accettano le prop definite nelle interfacce

---

## STEP 9 — MapContainer.tsx e pagina /catasto/mappa

**Obiettivo**: Creare il componente mappa e la pagina principale GIS.

**Azioni**:

1. Crea `frontend/src/components/catasto/gis/MapContainer.tsx` — vedi FRONTEND CODEX Step F4.

   **Note di adattamento**:
   - Il recupero token per le fetch popup: adatta al pattern auth del progetto
   - Il path delle API: adatta al proxy Next.js esistente o al base URL del backend
   - Il `as unknown as maplibregl.IControl` per Draw è intenzionale — non rimuovere

2. Crea `frontend/src/app/catasto/mappa/page.tsx` — vedi FRONTEND CODEX Step F8.

   **Note di adattamento**:
   - Il layout (`flex flex-col h-full`) deve integrarsi nel layout catasto esistente
   - Se il layout catasto usa un contenitore con altezza fissa, adatta
   - Il trigger "Disegna area" verso MapLibre Draw: implementa comunicazione tramite `useImperativeHandle` + `forwardRef` su MapContainer, esponendo un metodo `startDraw()`

3. Avvia il frontend in dev e verifica:
```bash
docker compose up frontend -d
# Poi apri http://localhost/catasto/mappa
```

**Acceptance**:
- Pagina carica senza errori console
- Mappa appare centrata sulla Sardegna
- Controlli zoom visibili in alto a destra
- Se DB ha geometrie: layer distretti visibile a zoom 9
- Click "Disegna area" → cursore cambia (inizio disegno)
- Dopo disegno poligono → spinner nel pannello → risultati

---

## STEP 10 — Navigazione + rifinitura + test E2E

**Obiettivo**: Collegare la pagina GIS alla navigazione catasto e validare il flusso completo.

**Azioni**:

1. Aggiungi link "Mappa GIS" alla sidebar/navigazione del modulo catasto — vedi FRONTEND CODEX Step F9. Trova il file che definisce i link di navigazione catasto (cerca `href: '/catasto/` nel codice).

2. Verifica che la sezione `catasto/mappa` sia coperta dai permessi GAIA. Se il backend ha un catalogo `sections`, aggiungi `catasto_mappa` con accesso per tutti i ruoli attivi.

3. Test flusso completo (se DB ha geometrie):
   - Apri `/catasto/mappa`
   - Clicca "Disegna area"
   - Disegna poligono su un distretto
   - Verifica: spinner → risultati con superficie e conteggio
   - Clicca "Esporta CSV" → file scaricato
   - Clicca "Esporta GeoJSON" → file scaricato
   - Clicca su particella sulla mappa (zoom 14+) → popup → link scheda funzionante
   - Clicca "Cancella selezione" → pannello vuoto

4. Test flusso con DB vuoto:
   - Mappa carica senza errori
   - Tile requests tornano 204 (no content) — nessun errore console
   - Disegno + select → risultati `n_particelle: 0`

5. Verifica performance backend (con DB popolato):
   ```bash
   curl -X POST http://localhost/api/catasto/gis/select \
     -H "Authorization: Bearer <TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"geometry": <geojson_distretto>}' \
     -w "\nTime: %{time_total}s\n"
   ```
   → Target: < 1s per distretto, < 3s per intera AOI

**Acceptance finale**:
- Link "Mappa GIS" visibile e funzionante dalla sidebar catasto
- Flusso completo draw → analisi → export funzionante
- Popup particella con link scheda funzionante
- Nessun errore console in produzione (`npm run build` pulito)
- Backend risponde in < 1s per selezioni di dimensione distretto

---

## Troubleshooting frequente

**Martin non si avvia**:
- Verifica `DATABASE_URL` nel service docker-compose
- `docker compose logs martin` → cerca errore connessione DB
- Martin richiede PostGIS installato: `SELECT PostGIS_version();` nel DB

**Tiles 404 da nginx**:
- Verifica location `/tiles/` in nginx.conf
- `docker compose restart nginx`
- Testa da dentro il container backend: `curl http://martin:3000/catalog`

**MapLibre GL errore SSR**:
- Verifica `dynamic(..., { ssr: false })` sulla pagina
- Non importare `maplibre-gl` direttamente in componenti non-dynamic

**`@mapbox/maplibre-gl-draw` errore import**:
- Aggiungi alias webpack in `next.config.js`: `'mapbox-gl': 'maplibre-gl'`
- Se persiste, aggiorna alla versione compatibile: `npm install @mapbox/maplibre-gl-draw@^1.4`

**`ST_Intersects` lento**:
- Verifica indice GIST: `\di idx_cat_part_geom`
- Se mancante: `CREATE INDEX idx_cat_part_geom ON cat_particelle USING GIST (geometry) WHERE is_current;`

**View `cat_particelle_current` non in `geometry_columns`**:
- Le views PostgreSQL non vengono automaticamente registrate in `geometry_columns` nelle versioni PostGIS più recenti
- Martin usa direttamente la colonna `geometry` dalla view — non richiede registrazione in `geometry_columns`
- Verifica: `SELECT * FROM information_schema.columns WHERE table_name = 'cat_particelle_current' AND column_name = 'geometry';`
