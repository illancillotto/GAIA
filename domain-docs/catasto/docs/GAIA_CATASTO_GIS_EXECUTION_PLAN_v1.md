# GAIA — Modulo Catasto GIS
## Execution Plan v1

---

## Fasi e priorità

| Fase | Scope | Stima | Prerequisiti |
|---|---|---|---|
| **GIS-1** | Infrastruttura: Martin + nginx proxy + view DB | 2-4h | Catasto Fase 1 🟢, Docker attivo |
| **GIS-2** | Backend API GIS: route + service + schemas | 4-6h | GIS-1 |
| **GIS-3** | Frontend base: mappa + layer MVT + popup | 6-8h | GIS-1, GIS-2 |
| **GIS-4** | Drawing tools + selezione + analisi live | 6-8h | GIS-3 |
| **GIS-5** | Export + filtri alfanumerici + rifinitura UX | 3-4h | GIS-4 |

Stima totale: 3-5 giorni di sviluppo effettivo

---

## GIS-1 — Infrastruttura

### Step 1.1 — View PostgreSQL per Martin

Crea view che espone solo particelle correnti (Martin non supporta WHERE nella config):

```sql
-- Eseguire direttamente su DB o aggiungere come migration Alembic
CREATE OR REPLACE VIEW cat_particelle_current AS
SELECT
    id,
    cfm,
    cod_comune_istat,
    foglio,
    particella,
    subalterno,
    superficie_mq,
    num_distretto,
    nome_distretto,
    geometry,
    -- flag anomalie (subquery leggera)
    EXISTS(
        SELECT 1 FROM cat_anomalie a
        WHERE a.particella_id = cat_particelle.id
          AND a.status = 'aperta'
    ) AS ha_anomalie
FROM cat_particelle
WHERE is_current = TRUE;

-- Indice non necessario sulla view (usa l'indice della tabella base)
```

**Acceptance**:
- `SELECT COUNT(*) FROM cat_particelle_current;` ritorna N record (uguale a `SELECT COUNT(*) FROM cat_particelle WHERE is_current=TRUE`)
- La view include la colonna `geometry`

### Step 1.2 — Martin in docker-compose.yml

Aggiungere al file `docker-compose.yml` (o `docker-compose.override.yml` in sviluppo):

```yaml
martin:
  image: ghcr.io/maplibre/martin:latest
  restart: unless-stopped
  environment:
    DATABASE_URL: postgresql://gaia:${POSTGRES_PASSWORD}@postgres/gaia
  volumes:
    - ./config/martin.toml:/config.toml:ro
  command: ["--config", "/config.toml"]
  depends_on:
    postgres:
      condition: service_healthy
  networks:
    - gaia-network
  # NON esporre porte all'esterno: accesso solo via nginx
```

**Acceptance**:
- `docker compose up martin -d` parte senza errori
- `docker compose logs martin` mostra "Martin is ready"
- Dal container backend: `curl http://martin:3000/catalog` ritorna JSON con le tabelle/view rilevate

### Step 1.3 — config/martin.toml

Creare file `config/martin.toml`:

```toml
[postgres]
connection_string = "${DATABASE_URL}"

[[postgres.tables]]
schema = "public"
table = "cat_distretti"
srid = 4326
geometry_column = "geometry"
id_column = "id"
properties = ["id", "num_distretto", "nome_distretto", "attivo"]
minzoom = 7
maxzoom = 16

[[postgres.tables]]
schema = "public"
table = "cat_particelle_current"
srid = 4326
geometry_column = "geometry"
id_column = "id"
properties = ["id", "cfm", "foglio", "particella", "subalterno",
              "cod_comune_istat", "num_distretto", "superficie_mq", "ha_anomalie"]
minzoom = 13
maxzoom = 20

[cache]
size_mb = 512
```

**Acceptance**:
- `curl http://martin:3000/cat_distretti/{z}/{x}/{y}` (con coordinate valide per la Sardegna) → risposta MVT binaria
- `curl http://martin:3000/cat_particelle_current/{z}/{x}/{y}` → risposta MVT o `204 No Content` se nessuna geometria nel tile

### Step 1.4 — Proxy nginx

Aggiungere al blocco `server` in `nginx/nginx.conf`:

```nginx
# Martin tile server — tiles catasto
location /tiles/ {
    proxy_pass         http://martin:3000/;
    proxy_set_header   Host $host;
    proxy_read_timeout 30s;
    add_header         Cache-Control "public, max-age=600";
    add_header         Access-Control-Allow-Origin "*";
}
```

**Acceptance**:
- `curl http://localhost/tiles/cat_distretti/10/516/395` (tile Sardegna) → risposta MVT
- `curl http://localhost/tiles/catalog` → JSON Martin catalog

---

## GIS-2 — Backend API GIS

### Step 2.1 — Schemas Pydantic

Crea `backend/app/modules/catasto/schemas/gis_schemas.py` con:
- `GisFilters`
- `GisSelectRequest`
- `ParticellaGisSummary`
- `FoglioAggr`
- `DistrettoAggr`
- `GisSelectResult`
- `GisExportFormat` (Enum: `geojson`, `csv`)

Schema completo in Architecture v1 sezione 6.1.

**Acceptance**:
- `from backend.app.modules.catasto.schemas.gis_schemas import GisSelectRequest` → nessun errore import
- `GisSelectRequest(geometry={"type":"Polygon","coordinates":[[...]]})` → instanziazione valida

### Step 2.2 — Service PostGIS

Crea `backend/app/modules/catasto/services/gis_service.py` con:

**Funzione `select_by_geometry(db, geojson_geometry, filters)`**:
1. Valida tipo geometria: accetta solo `Polygon` o `MultiPolygon`
2. Valida che la geometria sia nel bounding box ragionevole (Sardegna: lon 8.0–9.9, lat 38.8–41.3) — rifiuta geometrie fuori area con `400 Bad Request`
3. Costruisce query SQL con:
   - CTE `selected` con `ST_Intersects` + filtri opzionali
   - Aggregazioni per foglio e distretto
   - Preview particelle (LIMIT 200)
   - Flag `truncated`
4. Esegue query con `db.execute(text(sql), params)` — non ORM (troppo lento su join spaziali)
5. Deserializza risultato in `GisSelectResult`

**Funzione `export_particelle(db, id_list, format)`**:
1. Fetch particelle per lista ID con geometrie (se GeoJSON) o solo attributi (se CSV)
2. Se `format=geojson`: costruisce FeatureCollection con `geoalchemy2.shape.to_shape()` + `shapely.geometry.mapping()`
3. Se `format=csv`: usa `csv.DictWriter` su `io.StringIO`
4. Ritorna `StreamingResponse` con content-type corretto e header `Content-Disposition`

**Funzione `get_popup_data(db, particella_id)`**:
1. Query leggera: solo campi necessari per popup + count anomalie aperte
2. Nessun join pesante, nessuna geometria nel payload
3. Cache breve (5 min) se si usa Redis, altrimenti nessuna cache (query è già rapida)

**Acceptance**:
- Test con geometria poligono su area Oristano → ritorna `GisSelectResult` con dati
- Test con geometria non valida → `400 Bad Request`
- Test export CSV → file scaricabile con header corretti
- Test export GeoJSON → FeatureCollection valida

### Step 2.3 — Route GIS

Crea `backend/app/modules/catasto/routes/gis.py`:

```python
router = APIRouter(prefix="/catasto/gis", tags=["catasto-gis"])

@router.post("/select", response_model=GisSelectResult)
@router.get("/export")
@router.get("/particella/{id}/popup")
```

Implementazione completa in Architecture v1 sezione 6.2.

Registra il router nel punto di montaggio del modulo catasto (stesso pattern degli altri router del modulo).

**Acceptance**:
- `GET /docs` → le 3 route GIS appaiono in Swagger UI sotto tag `catasto-gis`
- `POST /catasto/gis/select` con geometria valida → `200 OK` con JSON
- `POST /catasto/gis/select` senza auth → `401 Unauthorized`

---

## GIS-3 — Frontend base: mappa + layer MVT + popup

### Step 3.1 — Installazione dipendenze npm

```bash
cd frontend
npm install maplibre-gl @mapbox/maplibre-gl-draw
npm install -D @types/mapbox__maplibre-gl-draw
```

Aggiungere a `frontend/next.config.js` se necessario per gestire import MapLibre:
```javascript
// Potrebbe essere necessario per alcuni ambienti Next.js 14
transpilePackages: ['maplibre-gl']
```

### Step 3.2 — MapContainer.tsx

Crea `frontend/src/components/catasto/gis/MapContainer.tsx`.

Requisiti implementativi:
- Usa `useRef` per il container DOM, `useEffect` per inizializzazione mappa
- Basemap: `https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png` (raster tile, nessun token)
- Centra sulla Sardegna: `center: [8.7, 40.1], zoom: 9`
- Aggiunge sorgente + layer distretti all'avvio
- Aggiunge sorgente + layer particelle (visibili da zoom 13+)
- Click su layer `distretti-fill` → `onDistrettoClick(feature.properties)`
- Click su layer `particelle-fill` → fetch `/catasto/gis/particella/{id}/popup` → mostra `ParticellaPopup`
- Hover su particella → cambia cursore a pointer
- Espone `ref` o callback per ricevere geometria selezione da `DrawingTools`
- Cleanup `map.remove()` in return dell'useEffect

**Stili layer**:
```typescript
// Distretti
'fill-color': '#3B82F6',
'fill-opacity': 0.2,
'fill-outline-color': '#1D4ED8'

// Particelle — colore condizionale su ha_anomalie
'fill-color': ['case', ['==', ['get', 'ha_anomalie'], true], '#EF4444', '#6366F1'],
'fill-opacity': 0.5

// Particelle selezionate (layer separato, sorgente GeoJSON aggiornata dopo selezione)
'fill-color': '#F59E0B',
'fill-opacity': 0.8
```

### Step 3.3 — ParticellaPopup.tsx

Popup MapLibre che monta React via `ReactDOM.createRoot` (pattern standard MapLibre + React):

```typescript
const popup = new maplibregl.Popup({ closeButton: true, maxWidth: '300px' })
  .setLngLat(coordinates)
  .setDOMContent(container)
  .addTo(map);

const root = createRoot(container);
root.render(<ParticellaPopup data={popupData} />);
```

### Step 3.4 — Pagina `/catasto/mappa`

Crea `frontend/src/app/catasto/mappa/page.tsx`:
- Import dinamico `MapContainer` con `ssr: false`
- Layout 3 colonne (sidebar sx, mappa centro, pannello dx)
- Placeholder per `DrawingTools`, `AnalysisPanel`, `SelectionPanel` (stub in GIS-3, implementati in GIS-4)
- Titolo sidebar: "Catasto GIS" con breadcrumb GAIA standard

**Acceptance**:
- `/catasto/mappa` carica senza errori
- Mappa appare centrata sulla Sardegna
- Layer distretti visibile a zoom 9-12 (se geometrie presenti in DB)
- Click su distretto → log in console (stub)
- Layer particelle appare a zoom 13+ (se geometrie presenti in DB)
- Click su particella → popup con dati (o "Nessun dato" se DB vuoto)

---

## GIS-4 — Drawing tools + selezione + analisi live

### Step 4.1 — DrawingTools.tsx

Crea `frontend/src/components/catasto/gis/DrawingTools.tsx`.

Integra `MapLibre GL Draw`:
```typescript
import MapboxDraw from '@mapbox/maplibre-gl-draw';
// Nota: il package supporta MapLibre GL nonostante il nome Mapbox

const draw = new MapboxDraw({
  displayControlsDefault: false,
  controls: { polygon: true, trash: true }
});
map.addControl(draw, 'top-left');
```

Toolbar custom (non i controlli default di Draw):
- `[◊ Poligono]` → `draw.changeMode('draw_polygon')`
- `[▭ Rettangolo]` → `draw.changeMode('draw_rectangle')` (se supportato) o `draw_polygon` guidato
- `[✕ Cancella]` → `draw.deleteAll()` + callback `onSelectionCleared()`

Listener eventi:
```typescript
map.on('draw.create', (e) => onGeometryDrawn(e.features[0].geometry));
map.on('draw.update', (e) => onGeometryDrawn(e.features[0].geometry));
map.on('draw.delete', () => onSelectionCleared());
```

### Step 4.2 — Integrazione select → analisi

In `MapContainer` o in un hook `useGisSelection`:

```typescript
const handleGeometryDrawn = async (geometry: GeoJSON.Geometry) => {
  setIsLoading(true);
  try {
    const result = await fetch('/catasto/gis/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ geometry, filters: activeFilters })
    });
    const data: GisSelectResult = await result.json();
    setSelectionResult(data);

    // Aggiorna layer highlight su mappa
    const selectedIds = data.particelle.map(p => p.id);
    updateSelectionLayer(selectedIds);
  } finally {
    setIsLoading(false);
  }
};
```

Layer highlight selezione:
```typescript
// Sorgente GeoJSON aggiornata con le particelle selezionate (via bbox o IDs nel layer MVT)
// Alternativa più semplice: filtro MapLibre sul layer particelle
map.setFilter('particelle-selected', ['in', 'id', ...selectedIds]);
```

### Step 4.3 — AnalysisPanel.tsx

Crea `frontend/src/components/catasto/gis/AnalysisPanel.tsx`.

Mostra `GisSelectResult` ricevuto come prop:
- Header: "Selezione attiva" + badge N particelle
- KPI: superficie in ha (formattata con separatore migliaia), conteggio
- Tabella aggregazione per foglio (max 10 righe, poi collapse)
- Tabella aggregazione per distretto
- Indicatore `truncated`: "Mostrando 200 di N particelle"
- Pulsanti export (GIS-5)
- Stato loading: skeleton loader durante fetch
- Stato vuoto: "Disegna un'area sulla mappa per iniziare"

### Step 4.4 — SelectionPanel.tsx

Crea `frontend/src/components/catasto/gis/SelectionPanel.tsx`.

Lista tabellare delle `particelle` da `GisSelectResult.particelle` (max 200):
- Colonne: CFM, Foglio, Superficie (mq), Distretto, Anomalie
- Ogni riga → link `/catasto/particelle/{id}`
- Badge rosso per `ha_anomalie = true`
- Footer: "e altri N..." se `truncated`

**Acceptance**:
- Disegnare poligono su mappa → spinner → risultati appaiono in < 2s (su DB popolato)
- AnalysisPanel mostra KPI aggiornati
- SelectionPanel mostra lista particelle con link funzionanti
- Cancella disegno → pannelli tornano a stato vuoto
- Particelle selezionate evidenziate in giallo su mappa

---

## GIS-5 — Export + filtri + rifinitura UX

### Step 5.1 — Export GeoJSON e CSV

In `AnalysisPanel`, pulsanti export che chiamano:
```
GET /catasto/gis/export?ids={id1,id2,...}&format=geojson
GET /catasto/gis/export?ids={id1,id2,...}&format=csv
```

Trigger download browser:
```typescript
const blob = await response.blob();
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = `selezione_catasto.${format === 'geojson' ? 'geojson' : 'csv'}`;
a.click();
```

Se `truncated = true`, avvisa l'utente: "L'export includerà tutte le N particelle (non solo le 200 in preview)".

**Acceptance**:
- Export CSV: file scaricato con intestazioni corrette
- Export GeoJSON: FeatureCollection valida apribile in QGIS

### Step 5.2 — FilterBar.tsx

Crea `frontend/src/components/catasto/gis/FilterBar.tsx`:

```
[Comune ▾] [Foglio ____] [Distretto ▾] [☐ Solo anomalie]
                                               [Applica filtri]
```

- `Comune`: select popolato da `GET /catasto/distretti` (lista valori unici comuni)
- `Foglio`: input testo libero
- `Distretto`: select da `GET /catasto/distretti` (lista esistente)
- `Solo anomalie`: checkbox

I filtri vengono passati come `GisFilters` nel body di `POST /catasto/gis/select`. Il bottone "Applica filtri" riesegue la selezione corrente con i nuovi filtri (se esiste una geometria disegnata).

### Step 5.3 — LayerControls.tsx

Toggle layer:
```
[● Distretti]
[● Particelle]
[○ Particelle con anomalie only]
```

Aggiorna visibility dei layer MapLibre:
```typescript
map.setLayoutProperty('distretti-fill', 'visibility', show ? 'visible' : 'none');
```

### Step 5.4 — Rifinitura e integrazione sidebar GAIA

- Aggiungere link "Catasto GIS" alla sidebar del modulo catasto (se non già presente)
- Verificare che la pagina `/catasto/mappa` sia coperta dalla navbar catasto esistente
- Aggiungere sezione "GIS" nella sezione `sections` del bootstrap backend (se necessario per i permessi)
- Test E2E: flusso completo draw → selezione → analisi → export

**Acceptance finale**:
- Pagina `/catasto/mappa` accessibile e funzionante
- Tutti i layer caricano correttamente (se geometrie presenti)
- Flusso completo: disegno → risultati → export funzionante end-to-end
- Popup particella con link alla scheda funzionante
- Filtri applicati correttamente ai risultati
- Nessun errore console in produzione
- Performance: selezione su area 1 distretto < 1s (con indice GIST)

---

## Dipendenze esterne da preparare

| Dipendenza | Azione | Responsabile | Fase |
|---|---|---|---|
| View `cat_particelle_current` in DB | SQL su DB GAIA | Dev | GIS-1 |
| Martin in docker-compose | Modifica docker-compose.yml | Dev | GIS-1 |
| `config/martin.toml` | Nuovo file | Dev | GIS-1 |
| Proxy nginx `/tiles/` | Modifica nginx.conf + restart nginx | Dev | GIS-1 |
| `maplibre-gl` npm | `npm install` | Dev | GIS-3 |
| `@mapbox/maplibre-gl-draw` npm | `npm install` | Dev | GIS-3 |
| Shapefile particelle importato | Verifica `COUNT(*)` su `cat_particelle` | Operatore | Sviluppo (test reale) |

---

## Note critiche

**DB vuoto durante sviluppo**: Se il DB non ha geometrie, la mappa funziona ma i layer appaiono vuoti. È normale e non blocca lo sviluppo. Le tiles Martin restituiranno `204 No Content` per tile senza dati.

**Martin e views**: Martin rileva automaticamente le tabelle PostGIS. Le views PostgreSQL sono supportate se hanno una colonna geometry. Verificare con `SELECT * FROM geometry_columns WHERE f_table_name = 'cat_particelle_current';` che la view sia registrata.

**MapLibre Draw e Next.js**: Il package `@mapbox/maplibre-gl-draw` potrebbe richiedere alias webpack se importa dipendenze Mapbox. Testare import e aggiungere alias in `next.config.js` se necessario:
```javascript
webpack: (config) => {
  config.resolve.alias = {
    ...config.resolve.alias,
    'mapbox-gl': 'maplibre-gl'
  };
  return config;
}
```
