# GAIA — Modulo Catasto GIS
## Architecture v1

> Estensione del modulo `catasto` esistente — nessun nuovo modulo backend
> Base: Catasto Fase 1 🟢, Fase 2 🔴 (da completare come prerequisito)

---

## 1. Principio architetturale

Il GIS è un'**estensione del modulo catasto**, non un modulo separato. Non introduce:
- nuovi container applicativi (usa Martin come da piano Catasto Fase 2)
- nuova logica auth (usa JWT GAIA esistente)

Aggiunge:
- `backend/app/modules/catasto/routes/gis.py` — nuove route analisi spaziale
- `backend/app/modules/catasto/services/gis_service.py` — logica PostGIS
- `cat_distretti_geometry_versions` — storico geometrico dei confini distrettuali importati autonomamente
- `frontend/src/app/catasto/gis/` — pagina GIS (già pianificata Fase 2, da estendere)
- `frontend/src/components/catasto/gis/` — componenti GIS (DrawingTools, SelectionPanel, AnalysisPanel)

---

## 2. Stack tecnologico

| Layer | Tecnologia | Note |
|---|---|---|
| DB spaziale | PostgreSQL + PostGIS | Già presente, estensioni già abilitate in Fase 1 |
| Tile server | Martin (Rust) | Da aggiungere a docker-compose |
| Backend API | FastAPI | Estensione route catasto esistenti |
| ORM spaziale | GeoAlchemy2 + Shapely | Già in requirements.txt da Fase 1 |
| Frontend mappa | MapLibre GL JS | Da installare (`maplibre-gl`) |
| Drawing tools | MapLibre GL Draw | Da installare (`@mapbox/maplibre-gl-draw`) |
| Proxy | nginx | Da aggiungere proxy `/tiles/` |

---

## 3. Struttura repository

```
backend/app/modules/catasto/
├── models/
│   └── registry.py                  # Esistente — CatParticella, CatDistretto, ecc.
├── routes/
│   ├── distretti.py                 # Esistente
│   ├── particelle.py                # Esistente
│   ├── anomalie.py                  # Esistente
│   ├── import_routes.py             # Esistente
│   └── gis.py                       # NUOVO — analisi spaziale
├── services/
│   ├── import_shapefile.py          # Esistente
│   ├── validation.py                # Esistente
│   └── gis_service.py               # NUOVO — logica PostGIS
└── schemas/
    └── gis_schemas.py               # NUOVO — Pydantic request/response GIS

frontend/src/app/catasto/
├── mappa/
│   └── page.tsx                     # DA CREARE (era pianificata Fase 2)
│   └── layout.tsx                   # DA CREARE se necessario
└── ...

frontend/src/components/catasto/
├── gis/
│   ├── MapContainer.tsx             # NUOVO — wrapper MapLibre GL
│   ├── DrawingTools.tsx             # NUOVO — toolbar disegno (poligono, box, reset)
│   ├── LayerControls.tsx            # NUOVO — toggle layer (distretti, particelle)
│   ├── SelectionPanel.tsx           # NUOVO — lista particelle selezionate
│   ├── AnalysisPanel.tsx            # NUOVO — risultati aggregati
│   ├── ParticellaPopup.tsx          # NUOVO — popup click particella
│   └── FilterBar.tsx                # NUOVO — filtri alfanumerici integrati mappa
└── ...

config/
└── martin.toml                      # DA CREARE (era pianificata Fase 2)

nginx/
└── nginx.conf                       # DA MODIFICARE — aggiungere proxy /tiles/
```

---

## 4. Database — view per tiles correnti

Il layer GIS continua a leggere `cat_distretti.geometry` come geometria corrente, ma il governo dei confini è separato da `cat_particelle` e versionato in `cat_distretti_geometry_versions`. Gli indici GIST critici sono:

```sql
-- Già creato in migration Fase 1
CREATE INDEX idx_cat_part_geom ON cat_particelle USING GIST (geometry) WHERE is_current;
CREATE INDEX idx_cat_distretti_geom ON cat_distretti USING GIST (geometry);
```

I batch shapefile delle particelle non devono più eseguire `ST_Union` per popolare `cat_distretti`: il ricalcolo dei confini avviene solo tramite import shapefile distretti dedicato (`/catasto/import/distretti/*`), che aggiorna `cat_distretti` e scrive una nuova versione geometrica corrente.

Per Martin è stata aggiunta una migration dedicata che crea la view `cat_particelle_current`, filtrata su `is_current = TRUE` e arricchita con `ha_anomalie`. La view evita di pubblicare nei tiles lo storico particelle non corrente.

L'unica verifica da fare è che PostGIS sia abilitato con `ST_Transform` disponibile (richiede PROJ). Questo è garantito dall'immagine Docker `postgis/postgis` già usata in GAIA.

**Nota SRID**: Le query di superficie usano `ST_Transform(geometry, 32632)` (UTM zone 32N) per ottenere aree in metri quadri accurate per la Sardegna. Il DB continua a memorizzare geometrie in EPSG:4326.

---

## 5. Martin tile server

### 5.1 Aggiunta a docker-compose.yml

```yaml
martin:
  image: ghcr.io/maplibre/martin:latest
  restart: unless-stopped
  environment:
    - DATABASE_URL=postgresql://gaia:${POSTGRES_PASSWORD}@postgres/gaia
  volumes:
    - ./config/martin.toml:/config.toml:ro
  command: ["--config", "/config.toml"]
  depends_on:
    - postgres
  networks:
    - gaia-network
```

Martin non espone porte pubbliche: le tiles transitano esclusivamente via nginx.

### 5.2 config/martin.toml

Nota implementativa: Martin v1.7 legge il file di configurazione in formato YAML anche se il mount mantiene il nome `config/martin.toml` previsto dal piano.

```toml
[postgres]
connection_string = "postgresql://gaia:${POSTGRES_PASSWORD}@postgres/gaia"

# Tabella distretti
[[postgres.tables]]
schema = "public"
table = "cat_distretti"
srid = 4326
geometry_column = "geometry"
# Colonne da includere nei tiles
properties = ["id", "num_distretto", "nome_distretto", "attivo"]

# Tabella particelle (300k+ righe — Martin gestisce automaticamente la semplificazione MVT)
[[postgres.tables]]
schema = "public"
table = "cat_particelle"
srid = 4326
geometry_column = "geometry"
# Filtro: solo record correnti
# Martin non supporta WHERE clause nella config — filtrare via view
source_id = "cat_particelle_current"
properties = ["id", "cfm", "foglio", "particella", "subalterno",
              "cod_comune_istat", "num_distretto", "superficie_mq"]

[cache]
# Cache in-memory per tiles frequenti
size_mb = 512
```

**Nota**: Per il filtro `is_current = TRUE` creare una view PostgreSQL:

```sql
CREATE OR REPLACE VIEW cat_particelle_current AS
SELECT * FROM cat_particelle WHERE is_current = TRUE;
```

E referenziare `cat_particelle_current` nel `martin.toml` invece di `cat_particelle`.

### 5.3 Proxy nginx

Aggiungere a `nginx/nginx.conf` dentro il blocco `server`:

```nginx
# Martin tile server
location /tiles/ {
    proxy_pass http://martin:3000/;
    proxy_set_header Host $host;
    proxy_cache_valid 200 10m;
    add_header Cache-Control "public, max-age=600";
}
```

---

## 6. API Backend — nuove route GIS

### 6.1 Schema Pydantic — `gis_schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class GisSelectRequest(BaseModel):
    """Geometria di selezione in formato GeoJSON Geometry (non Feature)."""
    geometry: dict  # GeoJSON Geometry object (Polygon o MultiPolygon)
    filters: Optional[GisFilters] = None

class GisFilters(BaseModel):
    comune: Optional[str] = None        # cod_comune_istat
    foglio: Optional[str] = None
    num_distretto: Optional[str] = None
    solo_anomalie: Optional[bool] = False

class GisSelectResult(BaseModel):
    n_particelle: int
    superficie_ha: float
    per_foglio: List[FoglioAggr]
    per_distretto: List[DistrettoAggr]
    particelle: List[ParticellaGisSummary]  # max 200 in preview
    truncated: bool  # True se > 200 risultati

class FoglioAggr(BaseModel):
    foglio: str
    n_particelle: int
    superficie_ha: float

class DistrettoAggr(BaseModel):
    num_distretto: str
    nome_distretto: Optional[str]
    n_particelle: int
    superficie_ha: float

class ParticellaGisSummary(BaseModel):
    id: str
    cfm: Optional[str]
    comune: Optional[str]
    foglio: Optional[str]
    particella: Optional[str]
    superficie_mq: Optional[float]
    num_distretto: Optional[str]
    ha_anomalie: bool

class GisExportFormat(str, Enum):
    geojson = "geojson"
    csv = "csv"
```

### 6.2 Route — `gis.py`

```python
router = APIRouter(prefix="/catasto/gis", tags=["catasto-gis"])

@router.post("/select", response_model=GisSelectResult)
async def select_by_geometry(
    body: GisSelectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user)
):
    """
    Riceve una geometria GeoJSON, esegue query spaziale su cat_particelle,
    restituisce aggregazioni e lista particelle selezionate.
    """
    return await gis_service.select_by_geometry(db, body.geometry, body.filters)

@router.get("/export")
async def export_selection(
    ids: str,  # comma-separated UUIDs
    format: GisExportFormat = GisExportFormat.csv,
    db: AsyncSession = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user)
):
    """Export GeoJSON o CSV delle particelle selezionate per ID."""
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    return await gis_service.export_particelle(db, id_list, format)

@router.get("/particella/{id}/popup")
async def get_particella_popup(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user)
):
    """Dati rapidi per popup mappa — ottimizzato, senza relazioni pesanti."""
    return await gis_service.get_popup_data(db, id)
```

### 6.3 Service — `gis_service.py`

```python
async def select_by_geometry(
    db: AsyncSession,
    geojson_geometry: dict,
    filters: Optional[GisFilters]
) -> GisSelectResult:
    """
    1. Valida il GeoJSON in input (deve essere Polygon o MultiPolygon)
    2. Costruisce query con ST_Intersects + filtri alfanumerici opzionali
    3. Calcola aggregazioni in un'unica query SQL
    4. Ritorna struttura GisSelectResult
    """

    # Serializza geometria per PostGIS
    geojson_str = json.dumps(geojson_geometry)

    # Query principale — un solo round-trip al DB
    sql = text("""
        WITH selected AS (
            SELECT
                p.id,
                p.cfm,
                p.cod_comune_istat,
                p.foglio,
                p.particella,
                p.subalterno,
                p.superficie_mq,
                p.num_distretto,
                p.nome_distretto,
                ST_Area(ST_Transform(p.geometry, 32632)) / 10000 AS sup_ha,
                EXISTS(
                    SELECT 1 FROM cat_anomalie a
                    WHERE a.particella_id = p.id AND a.status = 'aperta'
                ) AS ha_anomalie
            FROM cat_particelle p
            WHERE p.is_current = TRUE
              AND ST_Intersects(p.geometry, ST_GeomFromGeoJSON(:geojson))
              -- filtri opzionali aggiunti dinamicamente
        )
        SELECT
            COUNT(*) as n_particelle,
            COALESCE(SUM(sup_ha), 0) as superficie_ha,
            json_agg(json_build_object(
                'foglio', foglio,
                'n_particelle', cnt_f,
                'superficie_ha', sup_f
            )) FILTER (WHERE foglio IS NOT NULL) as per_foglio,
            json_agg(json_build_object(
                'num_distretto', num_distretto,
                'nome_distretto', nome_distretto,
                'n_particelle', cnt_d,
                'superficie_ha', sup_d
            )) FILTER (WHERE num_distretto IS NOT NULL) as per_distretto,
            -- lista particelle (max 200)
            (SELECT json_agg(sub) FROM (
                SELECT id, cfm, cod_comune_istat, foglio, particella,
                       superficie_mq, num_distretto, ha_anomalie
                FROM selected LIMIT 200
            ) sub) as particelle_preview,
            (SELECT COUNT(*) FROM selected) > 200 as truncated
        FROM (
            SELECT *,
                COUNT(*) OVER (PARTITION BY foglio) as cnt_f,
                SUM(sup_ha) OVER (PARTITION BY foglio) as sup_f,
                COUNT(*) OVER (PARTITION BY num_distretto) as cnt_d,
                SUM(sup_ha) OVER (PARTITION BY num_distretto) as sup_d
            FROM selected
        ) agg
    """)
    # Nota: i filtri alfanumerici vengono aggiunti come WHERE clause dinamiche
    # prima dell'esecuzione usando SQLAlchemy text() con parametri bindati.
```

---

## 7. Frontend — struttura componenti

### 7.1 Pagina GIS — `/catasto/gis`

```
frontend/src/app/catasto/gis/
└── page.tsx
```

Layout operativo:
- **Canvas mappa full-height**: `MapContainer` occupa tutta l'altezza utile della pagina, senza card gestionale intermedia.
- **Toolbar flottante**: brand/contesto GIS, azione `Vista estesa` e strumenti di disegno restano sovrapposti alla mappa.
- **Sidebar destra persistente**: layer visibili, filtro distretto, import Excel, layer in mappa, archivio, analisi e selezione restano in un pannello laterale stile console GIS.
- **Pannello distretti**: accordion `Distretti irrigui` alimentato da `/catasto/distretti`; la selezione applica il filtro `num_distretto`, centra la geometria via `/catasto/distretti/{id}/geojson` e usa la stessa palette colore del layer MVT.
- **Vista estesa**: conserva la mappa come canvas principale e sposta i controlli operativi in una sidebar destra dedicata.

### 7.2 MapContainer.tsx

Responsabilità:
- Inizializza MapLibre GL JS con basemap OSM
- Aggiunge sorgente MVT distretti (`/tiles/cat_distretti/{z}/{x}/{y}`)
- Aggiunge sorgente MVT confini distretti (`/tiles/cat_distretti_boundaries/{z}/{x}/{y}`), derivata da una view PostGIS `MULTILINESTRING` dissolta
- Aggiunge sorgente MVT particelle (`/tiles/cat_particelle_current/{z}/{x}/{y}`)
- Gestisce click su particella → fetch `/catasto/gis/particella/{id}/popup` → aggiorna una scheda React contestuale con CTA per `ParticellaDetailDialog`
- Gestisce click su distretto → emette evento verso SelectionPanel
- Riceve geometria disegnata da DrawingTools → chiama `POST /catasto/gis/select`
- Evidenzia le particelle a ruolo direttamente nel fill MVT usando la property booleana `ha_ruolo` esposta dalla view `cat_particelle_current`; la property viene calcolata via `catasto_parcels` su codice catastale comune/foglio/particella/subalterno, non tramite UUID diretto tra `ruolo_particelle` e `cat_particelle`
- Permette di cambiare sfondo tra OpenStreetMap, imagery satellite raster e Google Map Tiles API; Google resta disabilitato finche non e disponibile `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`
- Stile layer: particelle colorate per `ha_anomalie` (rosso/grigio), distretto per status

```typescript
// Sorgenti tiles
map.addSource('distretti', {
  type: 'vector',
  tiles: [`${window.location.origin}/tiles/cat_distretti/{z}/{x}/{y}`],
  minzoom: 7,
  maxzoom: 16
});

map.addSource('particelle', {
  type: 'vector',
  tiles: [`${window.location.origin}/tiles/cat_particelle_current/{z}/{x}/{y}`],
  minzoom: 13,  // particelle visibili solo da zoom 13 in su
  maxzoom: 20
});

// Layer particelle
map.addLayer({
  id: 'particelle-fill',
  type: 'fill',
  source: 'particelle',
  'source-layer': 'cat_particelle_current',
  minzoom: 13,
  paint: {
    'fill-color': ['case',
      ['get', 'ha_anomalie'], '#EF4444',  // rosso se anomalie
      '#6366F1'                            // viola default
    ],
    'fill-opacity': 0.4
  }
});
```

### 7.3 DrawingTools.tsx

Toolbar con:
- Pulsante "Disegna poligono" (attiva MapLibre Draw in modalità polygon)
- Pulsante "Disegna rettangolo" (modalità draw_rectangle)
- Pulsante "Cancella selezione" (reset draw + reset risultati)
- Indicatore stato: "Nessuna selezione" / "Selezione in corso..." / "N particelle selezionate"

Quando MapLibre Draw emette `draw.create` o `draw.update`:
1. Estrae la geometria dal feature GeoJSON
2. Chiama `POST /catasto/gis/select` con la geometria + filtri attivi
3. Propaga risultati a `SelectionPanel` e `AnalysisPanel`
4. Aggiorna highlight su mappa per le particelle selezionate

### 7.4 AnalysisPanel.tsx

Mostra i risultati di `GisSelectResult`:
```
Selezione attiva
────────────────
Particelle: 1.247
Superficie: 3.841,2 ha

Per foglio
foglio  n.part  sup.ha
──────────────────────
  12     341    987,3
  13     211    654,1
  ...

Per distretto
distretto  n.part  sup.ha
──────────────────────────
  D01       712   2.104,5
  ...

[Esporta GeoJSON] [Esporta CSV]
```

### 7.5 SelectionPanel.tsx

Lista paginata delle particelle selezionate (max 200 in preview):
- Tabella con: CFM, Comune, Foglio, Superficie, Distretto, Badge anomalie
- Link → `/catasto/particelle/{id}`
- Indicatore "e altri N..." se `truncated = true`

### 7.6 ParticellaPopup.tsx

Popup MapLibre che appare on click:
```
CFM: A357-12-45
Comune: Oristano
Foglio: 12 — Particella: 45
Superficie: 2.340 mq
Distretto: D01 — Distretto Nord
● 2 anomalie aperte
[Apri scheda completa →]
```

---

## 8. Flusso dati completo

```
Utente disegna poligono
        │
        ▼
DrawingTools (frontend)
  → Emette geometria GeoJSON
        │
        ▼
MapContainer
  → POST /catasto/gis/select
    { geometry: {...}, filters: {...} }
        │
        ▼
gis.py route (FastAPI)
  → gis_service.select_by_geometry()
        │
        ▼
gis_service.py
  → Query PostGIS con ST_Intersects
  → Aggregazioni SQL (foglio, distretto)
  → Lista preview (max 200)
        │
        ▼
GisSelectResult (JSON)
        │
        ▼
Frontend
  → AnalysisPanel: mostra KPI aggregati
  → SelectionPanel: lista particelle
  → MapContainer: highlight particelle selezionate
        │
        ▼ (opzionale)
Utente clicca "Esporta"
  → GET /catasto/gis/export?ids=...&format=csv
  → Download file
```

---

## 9. Dipendenze Python aggiuntive

Verificare in `backend/requirements.txt`:
```
geoalchemy2>=0.14      # già presente da Fase 1
shapely>=2.0           # per manipolazione geometrie server-side
```

Nessun altro pacchetto Python è necessario. La serializzazione GeoJSON delle geometrie avviene via `geoalchemy2.shape.to_shape()` + `shapely.geometry.mapping()` (già usato nelle route distretti esistenti).

---

## 10. Dipendenze npm aggiuntive

```bash
npm install maplibre-gl @mapbox/maplibre-gl-draw
npm install -D @types/mapbox__maplibre-gl-draw
```

Da aggiungere a `frontend/package.json`.

**Compatibilità Next.js 14**: MapLibre GL richiede `ssr: false` con `next/dynamic` — il componente `MapContainer` deve essere importato con dynamic import per evitare errori SSR.

```typescript
// In page.tsx
const MapContainer = dynamic(() => import('@/components/catasto/gis/MapContainer'), {
  ssr: false,
  loading: () => <div className="animate-pulse bg-gray-200 w-full h-full" />
});
```

---

## 11. Considerazioni performance su 300k+ particelle

### Lato DB
- Indice GIST già presente → `ST_Intersects` usa l'indice automaticamente
- `ST_Transform` in query superficie: eseguito solo sulle righe già filtrate da `ST_Intersects`
- Query con CTE `selected` + window functions: singolo round-trip al DB
- Timeout query: impostare `statement_timeout = 10s` sulla connessione GIS per evitare query runaway

### Lato tiles
- Martin serve MVT con semplificazione geometrica automatica per zoom level
- Zoom ≤ 12: solo distretti visibili (poche decine di geometrie)
- Zoom 13-15: particelle con semplificazione aggressiva
- Zoom ≥ 16: geometrie complete
- Martin mantiene cache in-memory (configurata a 512MB)

### Lato frontend
- MapLibre GL renderizza con WebGL: 300k tile features sono gestibili (test su dataset simili confermano fluidità)
- Selezione highlight: aggiornare solo la paint property del layer, non ricaricare sorgente
- SelectionPanel: paginazione client-side sui 200 risultati in preview (nessuna ulteriore fetch)
