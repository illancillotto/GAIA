# GAIA — Modulo Catasto GIS
## Backend Implementation Codex v1
### Per Claude Code / Cursor / GSD CLI

---

## Contesto

Stai lavorando su **GAIA**, un monolite modulare FastAPI + PostgreSQL + PostGIS.
Repository: `github.com/illancillotto/GAIA`
Backend path: `backend/app/modules/catasto/`

Il modulo `catasto` esiste già e ha Fase 1 completata:
- Tabelle `cat_particelle`, `cat_distretti`, `cat_anomalie` (con indici GIST) ✅
- Modelli ORM in `backend/app/models/catasto_phase1.py` ✅
- Route distretti, particelle, anomalie, import già registrate ✅

Stai **aggiungendo** funzionalità GIS al modulo esistente.

**Non modificare** route, modelli o service esistenti che non siano citati esplicitamente in questo codex.

---

## STEP B1 — View PostgreSQL per Martin

**Obiettivo**: Creare una view che Martin userà per esporre le particelle correnti come tiles MVT.

Martin non supporta clausole WHERE nella configurazione — serve una view dedicata.

Crea una nuova migration Alembic: `backend/alembic/versions/xxxx_catasto_gis_view.py`

```python
"""catasto: add cat_particelle_current view for Martin tile server

Revision ID: xxxx_catasto_gis_view
Revises: <revision_id_di_catasto_fase1>
Create Date: ...
"""

from alembic import op

def upgrade():
    op.execute("""
        CREATE OR REPLACE VIEW cat_particelle_current AS
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
            p.fuori_distretto,
            p.geometry,
            EXISTS(
                SELECT 1 FROM cat_anomalie a
                WHERE a.particella_id = p.id
                  AND a.status = 'aperta'
            ) AS ha_anomalie
        FROM cat_particelle p
        WHERE p.is_current = TRUE;
    """)

def downgrade():
    op.execute("DROP VIEW IF EXISTS cat_particelle_current;")
```

**Acceptance**:
- `alembic upgrade head` → nessun errore
- `SELECT COUNT(*) FROM cat_particelle_current;` → stesso count di `SELECT COUNT(*) FROM cat_particelle WHERE is_current=TRUE`
- `SELECT f_table_name FROM geometry_columns WHERE f_table_name = 'cat_particelle_current';` → ritorna la view

---

## STEP B2 — Schemas Pydantic GIS

**File**: `backend/app/modules/catasto/schemas/gis_schemas.py`

Crea il file con questi schema esatti:

```python
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any, Dict
from enum import Enum


class GisFilters(BaseModel):
    comune: Optional[str] = None          # cod_comune_istat (es. "095049")
    foglio: Optional[str] = None          # es. "12"
    num_distretto: Optional[str] = None   # es. "D01"
    solo_anomalie: bool = False


class GisSelectRequest(BaseModel):
    geometry: Dict[str, Any] = Field(
        ...,
        description="GeoJSON Geometry object (Polygon o MultiPolygon)"
    )
    filters: Optional[GisFilters] = None

    @field_validator('geometry')
    @classmethod
    def validate_geometry_type(cls, v):
        allowed = {'Polygon', 'MultiPolygon'}
        if v.get('type') not in allowed:
            raise ValueError(f"geometry.type deve essere Polygon o MultiPolygon, ricevuto: {v.get('type')}")
        return v


class ParticellaGisSummary(BaseModel):
    id: str
    cfm: Optional[str] = None
    cod_comune_istat: Optional[str] = None
    foglio: Optional[str] = None
    particella: Optional[str] = None
    subalterno: Optional[str] = None
    superficie_mq: Optional[float] = None
    num_distretto: Optional[str] = None
    nome_distretto: Optional[str] = None
    ha_anomalie: bool = False

    model_config = {"from_attributes": True}


class FoglioAggr(BaseModel):
    foglio: str
    n_particelle: int
    superficie_ha: float


class DistrettoAggr(BaseModel):
    num_distretto: str
    nome_distretto: Optional[str] = None
    n_particelle: int
    superficie_ha: float


class GisSelectResult(BaseModel):
    n_particelle: int
    superficie_ha: float
    per_foglio: List[FoglioAggr] = []
    per_distretto: List[DistrettoAggr] = []
    particelle: List[ParticellaGisSummary] = []
    truncated: bool = False  # True se ci sono > 200 particelle nell'area


class GisExportFormat(str, Enum):
    geojson = "geojson"
    csv = "csv"


class ParticellaPopupData(BaseModel):
    id: str
    cfm: Optional[str] = None
    cod_comune_istat: Optional[str] = None
    foglio: Optional[str] = None
    particella: Optional[str] = None
    subalterno: Optional[str] = None
    superficie_mq: Optional[float] = None
    num_distretto: Optional[str] = None
    nome_distretto: Optional[str] = None
    n_anomalie_aperte: int = 0

    model_config = {"from_attributes": True}
```

**Acceptance**:
- `from backend.app.modules.catasto.schemas.gis_schemas import GisSelectRequest, GisSelectResult` → nessun errore
- `GisSelectRequest(geometry={"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]]]})` → OK
- `GisSelectRequest(geometry={"type":"Point","coordinates":[0,0]})` → ValidationError

---

## STEP B3 — Service GIS

**File**: `backend/app/modules/catasto/services/gis_service.py`

```python
from __future__ import annotations
import json
import csv
import io
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from backend.app.modules.catasto.schemas.gis_schemas import (
    GisFilters, GisSelectResult, GisExportFormat,
    ParticellaGisSummary, FoglioAggr, DistrettoAggr, ParticellaPopupData
)

# Bounding box Sardegna (con margine)
SARDINIA_BBOX = {
    "min_lon": 7.8, "max_lon": 10.0,
    "min_lat": 38.5, "max_lat": 41.5
}

PREVIEW_LIMIT = 200


def _validate_geometry_bbox(geometry: dict) -> None:
    """Verifica che la geometria sia approssimativamente sulla Sardegna."""
    import shapely.geometry
    try:
        shape = shapely.geometry.shape(geometry)
        bounds = shape.bounds  # (minx, miny, maxx, maxy)
        if (bounds[0] < SARDINIA_BBOX["min_lon"] or bounds[2] > SARDINIA_BBOX["max_lon"] or
                bounds[1] < SARDINIA_BBOX["min_lat"] or bounds[3] > SARDINIA_BBOX["max_lat"]):
            raise HTTPException(
                status_code=400,
                detail="La geometria di selezione è fuori dall'area di interesse (Sardegna)."
            )
    except (ValueError, AttributeError) as e:
        raise HTTPException(status_code=400, detail=f"Geometria GeoJSON non valida: {e}")


def _build_where_clause(filters: Optional[GisFilters], geojson_str: str) -> tuple[str, dict]:
    """Costruisce WHERE clause e params per la query GIS."""
    conditions = [
        "p.is_current = TRUE",
        "ST_Intersects(p.geometry, ST_GeomFromGeoJSON(:geojson_str))"
    ]
    params: dict = {"geojson_str": geojson_str}

    if filters:
        if filters.comune:
            conditions.append("p.cod_comune_istat = :comune")
            params["comune"] = filters.comune
        if filters.foglio:
            conditions.append("p.foglio = :foglio")
            params["foglio"] = filters.foglio
        if filters.num_distretto:
            conditions.append("p.num_distretto = :num_distretto")
            params["num_distretto"] = filters.num_distretto
        if filters.solo_anomalie:
            conditions.append("""
                EXISTS(
                    SELECT 1 FROM cat_anomalie a
                    WHERE a.particella_id = p.id AND a.status = 'aperta'
                )
            """)

    return " AND ".join(conditions), params


async def select_by_geometry(
    db: AsyncSession,
    geometry: dict,
    filters: Optional[GisFilters]
) -> GisSelectResult:
    """
    Esegue analisi spaziale su cat_particelle e ritorna aggregazioni + lista preview.
    Query singola con CTE per minimizzare round-trip al DB.
    """
    _validate_geometry_bbox(geometry)
    geojson_str = json.dumps(geometry)
    where_clause, params = _build_where_clause(filters, geojson_str)

    sql = text(f"""
        WITH selected AS (
            SELECT
                p.id::text,
                p.cfm,
                p.cod_comune_istat,
                p.foglio,
                p.particella,
                p.subalterno,
                p.superficie_mq,
                p.num_distretto,
                p.nome_distretto,
                COALESCE(ST_Area(ST_Transform(p.geometry, 32632)) / 10000.0, 0) AS sup_ha,
                EXISTS(
                    SELECT 1 FROM cat_anomalie a
                    WHERE a.particella_id = p.id AND a.status = 'aperta'
                ) AS ha_anomalie
            FROM cat_particelle p
            WHERE {where_clause}
        ),
        totals AS (
            SELECT
                COUNT(*) AS n_totale,
                COALESCE(SUM(sup_ha), 0) AS superficie_ha_totale
            FROM selected
        ),
        per_foglio AS (
            SELECT
                foglio,
                COUNT(*) AS n_particelle,
                COALESCE(SUM(sup_ha), 0) AS superficie_ha
            FROM selected
            WHERE foglio IS NOT NULL
            GROUP BY foglio
            ORDER BY foglio
        ),
        per_distretto AS (
            SELECT
                num_distretto,
                MAX(nome_distretto) AS nome_distretto,
                COUNT(*) AS n_particelle,
                COALESCE(SUM(sup_ha), 0) AS superficie_ha
            FROM selected
            WHERE num_distretto IS NOT NULL
            GROUP BY num_distretto
            ORDER BY num_distretto
        ),
        preview AS (
            SELECT * FROM selected LIMIT :preview_limit
        )
        SELECT
            t.n_totale,
            t.superficie_ha_totale,
            (SELECT json_agg(row_to_json(f)) FROM per_foglio f) AS per_foglio,
            (SELECT json_agg(row_to_json(d)) FROM per_distretto d) AS per_distretto,
            (SELECT json_agg(row_to_json(pr)) FROM preview pr) AS particelle_preview,
            t.n_totale > :preview_limit AS truncated
        FROM totals t
    """)

    params["preview_limit"] = PREVIEW_LIMIT

    result = await db.execute(sql, params)
    row = result.fetchone()

    if row is None:
        return GisSelectResult(n_particelle=0, superficie_ha=0.0)

    def parse_aggr_foglio(data) -> List[FoglioAggr]:
        if not data:
            return []
        return [FoglioAggr(
            foglio=r["foglio"],
            n_particelle=r["n_particelle"],
            superficie_ha=round(r["superficie_ha"], 2)
        ) for r in data]

    def parse_aggr_distretto(data) -> List[DistrettoAggr]:
        if not data:
            return []
        return [DistrettoAggr(
            num_distretto=r["num_distretto"],
            nome_distretto=r.get("nome_distretto"),
            n_particelle=r["n_particelle"],
            superficie_ha=round(r["superficie_ha"], 2)
        ) for r in data]

    def parse_preview(data) -> List[ParticellaGisSummary]:
        if not data:
            return []
        return [ParticellaGisSummary(
            id=r["id"],
            cfm=r.get("cfm"),
            cod_comune_istat=r.get("cod_comune_istat"),
            foglio=r.get("foglio"),
            particella=r.get("particella"),
            subalterno=r.get("subalterno"),
            superficie_mq=r.get("superficie_mq"),
            num_distretto=r.get("num_distretto"),
            nome_distretto=r.get("nome_distretto"),
            ha_anomalie=r.get("ha_anomalie", False)
        ) for r in data]

    return GisSelectResult(
        n_particelle=row.n_totale or 0,
        superficie_ha=round(float(row.superficie_ha_totale or 0), 2),
        per_foglio=parse_aggr_foglio(row.per_foglio),
        per_distretto=parse_aggr_distretto(row.per_distretto),
        particelle=parse_preview(row.particelle_preview),
        truncated=bool(row.truncated)
    )


async def export_particelle(
    db: AsyncSession,
    id_list: List[str],
    fmt: GisExportFormat
) -> StreamingResponse:
    """Export GeoJSON o CSV per lista di ID particelle."""
    if not id_list:
        raise HTTPException(status_code=400, detail="Lista ID vuota")
    if len(id_list) > 10000:
        raise HTTPException(status_code=400, detail="Massimo 10.000 particelle per export")

    if fmt == GisExportFormat.geojson:
        return await _export_geojson(db, id_list)
    else:
        return await _export_csv(db, id_list)


async def _export_geojson(db: AsyncSession, id_list: List[str]) -> StreamingResponse:
    sql = text("""
        SELECT
            id::text, cfm, cod_comune_istat, foglio, particella, subalterno,
            superficie_mq, num_distretto, nome_distretto,
            ST_AsGeoJSON(geometry)::json AS geometry_json
        FROM cat_particelle
        WHERE id::text = ANY(:ids) AND is_current = TRUE
    """)
    result = await db.execute(sql, {"ids": id_list})
    rows = result.fetchall()

    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": row.geometry_json,
            "properties": {
                "id": row.id,
                "cfm": row.cfm,
                "comune": row.cod_comune_istat,
                "foglio": row.foglio,
                "particella": row.particella,
                "subalterno": row.subalterno,
                "superficie_mq": row.superficie_mq,
                "num_distretto": row.num_distretto,
                "nome_distretto": row.nome_distretto,
            }
        })

    geojson = {"type": "FeatureCollection", "features": features}
    content = json.dumps(geojson, ensure_ascii=False, indent=2)

    return StreamingResponse(
        io.StringIO(content),
        media_type="application/geo+json",
        headers={"Content-Disposition": "attachment; filename=selezione_catasto.geojson"}
    )


async def _export_csv(db: AsyncSession, id_list: List[str]) -> StreamingResponse:
    sql = text("""
        SELECT
            id::text, cfm, cod_comune_istat, foglio, particella, subalterno,
            superficie_mq, num_distretto, nome_distretto
        FROM cat_particelle
        WHERE id::text = ANY(:ids) AND is_current = TRUE
        ORDER BY num_distretto, foglio, particella
    """)
    result = await db.execute(sql, {"ids": id_list})
    rows = result.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "cfm", "comune", "foglio", "particella", "subalterno",
        "superficie_mq", "distretto", "nome_distretto"
    ])
    for row in rows:
        writer.writerow([
            row.id, row.cfm, row.cod_comune_istat, row.foglio,
            row.particella, row.subalterno, row.superficie_mq,
            row.num_distretto, row.nome_distretto
        ])
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=selezione_catasto.csv"}
    )


async def get_popup_data(db: AsyncSession, particella_id: str) -> ParticellaPopupData:
    """Dati leggeri per popup mappa — query ottimizzata, nessuna geometria."""
    sql = text("""
        SELECT
            p.id::text,
            p.cfm,
            p.cod_comune_istat,
            p.foglio,
            p.particella,
            p.subalterno,
            p.superficie_mq,
            p.num_distretto,
            p.nome_distretto,
            COUNT(a.id) FILTER (WHERE a.status = 'aperta') AS n_anomalie_aperte
        FROM cat_particelle p
        LEFT JOIN cat_anomalie a ON a.particella_id = p.id
        WHERE p.id::text = :particella_id AND p.is_current = TRUE
        GROUP BY p.id
    """)
    result = await db.execute(sql, {"particella_id": particella_id})
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Particella non trovata")

    return ParticellaPopupData(
        id=row.id,
        cfm=row.cfm,
        cod_comune_istat=row.cod_comune_istat,
        foglio=row.foglio,
        particella=row.particella,
        subalterno=row.subalterno,
        superficie_mq=row.superficie_mq,
        num_distretto=row.num_distretto,
        nome_distretto=row.nome_distretto,
        n_anomalie_aperte=row.n_anomalie_aperte or 0
    )
```

**Acceptance**:
- Import del service senza errori
- Test con geometria Sardegna → `GisSelectResult` valido
- Test con geometria fuori Sardegna → `HTTPException(400)`
- Test export CSV → `StreamingResponse` con `Content-Type: text/csv`
- Test export GeoJSON → `StreamingResponse` con `Content-Type: application/geo+json`

---

## STEP B4 — Route GIS

**File**: `backend/app/modules/catasto/routes/gis.py`

```python
from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.auth import get_current_user
from backend.app.models.user import ApplicationUser
from backend.app.modules.catasto.schemas.gis_schemas import (
    GisSelectRequest, GisSelectResult, GisExportFormat, ParticellaPopupData
)
from backend.app.modules.catasto.services import gis_service

router = APIRouter(prefix="/catasto/gis", tags=["catasto-gis"])


@router.post(
    "/select",
    response_model=GisSelectResult,
    summary="Selezione spaziale particelle",
    description="Riceve una geometria GeoJSON (Polygon/MultiPolygon), "
                "esegue query spaziale su cat_particelle e restituisce "
                "aggregazioni e lista preview delle particelle selezionate."
)
async def select_by_geometry(
    body: GisSelectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user)
) -> GisSelectResult:
    return await gis_service.select_by_geometry(db, body.geometry, body.filters)


@router.get(
    "/export",
    summary="Export selezione particelle",
    description="Export GeoJSON o CSV delle particelle selezionate per lista di ID."
)
async def export_selection(
    ids: str = Query(..., description="ID particelle separati da virgola"),
    format: GisExportFormat = Query(GisExportFormat.csv, description="Formato output"),
    db: AsyncSession = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user)
):
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    return await gis_service.export_particelle(db, id_list, format)


@router.get(
    "/particella/{particella_id}/popup",
    response_model=ParticellaPopupData,
    summary="Dati popup particella",
    description="Dati essenziali per il popup mappa — query leggera senza geometria."
)
async def get_particella_popup(
    particella_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: ApplicationUser = Depends(get_current_user)
) -> ParticellaPopupData:
    return await gis_service.get_popup_data(db, particella_id)
```

### Registrazione router

Nel file che registra i router del modulo catasto (cerca il pattern esistente usato da `distretti_router`, `particelle_router` ecc.), aggiungi:

```python
from backend.app.modules.catasto.routes.gis import router as catasto_gis_router
app.include_router(catasto_gis_router)
# oppure, se usi un router aggregatore catasto:
catasto_router.include_router(catasto_gis_router)
```

**Acceptance**:
- `GET /docs` → route `POST /catasto/gis/select`, `GET /catasto/gis/export`, `GET /catasto/gis/particella/{id}/popup` presenti
- `POST /catasto/gis/select` con JWT valido e geometria Sardegna → `200 OK`
- `POST /catasto/gis/select` senza JWT → `401 Unauthorized`
- `GET /catasto/gis/export?ids=...&format=csv` → file CSV scaricabile
- `GET /catasto/gis/particella/nonexistent/popup` → `404 Not Found`

---

## STEP B5 — Configurazione Martin e docker-compose

### 5.1 File `config/martin.toml`

Crea il file nella root del repository (dove risiede `docker-compose.yml`):

```toml
# Martin tile server configuration
# Docs: https://martin.maplibre.org/

[postgres]
connection_string = "${DATABASE_URL}"

# Distretti irrigui — visibili da zoom 7
[[postgres.tables]]
schema = "public"
table = "cat_distretti"
srid = 4326
geometry_column = "geometry"
id_column = "id"
minzoom = 7
maxzoom = 16
properties = ["id", "num_distretto", "nome_distretto", "attivo"]

# Particelle correnti (via view) — visibili da zoom 13
[[postgres.tables]]
schema = "public"
table = "cat_particelle_current"
srid = 4326
geometry_column = "geometry"
id_column = "id"
minzoom = 13
maxzoom = 20
properties = [
    "id", "cfm", "foglio", "particella", "subalterno",
    "cod_comune_istat", "num_distretto", "superficie_mq", "ha_anomalie"
]

[cache]
size_mb = 512
```

### 5.2 Modifica `docker-compose.yml`

Aggiungere il servizio `martin` dopo il servizio `postgres`:

```yaml
martin:
  image: ghcr.io/maplibre/martin:latest
  restart: unless-stopped
  environment:
    DATABASE_URL: postgresql://${POSTGRES_USER:-gaia}:${POSTGRES_PASSWORD}@postgres/${POSTGRES_DB:-gaia}
  volumes:
    - ./config/martin.toml:/config.toml:ro
  command: ["--config", "/config.toml"]
  depends_on:
    postgres:
      condition: service_healthy
  networks:
    - gaia-network
  # Porta interna 3000 — NON esposta all'host, accessibile solo via nginx
```

### 5.3 Modifica `nginx/nginx.conf`

Nel blocco `server`, aggiungere prima delle location esistenti:

```nginx
# Martin tile server — proxy pass per tiles MVT Catasto GIS
location /tiles/ {
    proxy_pass         http://martin:3000/;
    proxy_http_version 1.1;
    proxy_set_header   Host $host;
    proxy_set_header   X-Real-IP $remote_addr;
    proxy_read_timeout 30s;
    proxy_connect_timeout 10s;

    # Cache tiles (MVT sono deterministic per zoom/x/y)
    add_header Cache-Control "public, max-age=600";

    # CORS per MapLibre GL (stesso dominio, ma aggiungere per sicurezza)
    add_header Access-Control-Allow-Origin $http_origin always;
    add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
}
```

**Acceptance Step B5**:
- `docker compose up martin -d` → avvia senza errori
- `docker compose logs martin` → "Martin is ready to accept connections"
- `curl http://localhost/tiles/catalog` → JSON con lista tiles disponibili
- `curl http://localhost/tiles/cat_distretti/9/260/197` → risposta binaria MVT (o 204 se DB vuoto)

---

## Note per l'implementatore

**Import path**: Adatta tutti i path di import (`backend.app.database`, `backend.app.auth`, ecc.) al pattern effettivo del progetto. Usa come riferimento i file route esistenti in `backend/app/modules/catasto/routes/distretti.py`.

**AsyncSession vs Session**: Se il progetto usa sessioni sincrone (non async), rimuovi `async`/`await` dal service e usa `db.execute(sql, params)` diretto.

**`shapely` disponibilità**: Verifica con `import shapely` nel container backend. Se mancante, aggiungere a `requirements.txt` e ricostruire l'immagine.

**Query timeout**: Aggiungere `SET LOCAL statement_timeout = '10000';` prima della query `select_by_geometry` se si vuole proteggere contro query runaway su DB non indicizzato.

**Nota UUID**: Il cast `p.id::text` nelle query SQL è necessario se `id` è di tipo UUID nativo PostgreSQL e il driver Python lo restituisce come oggetto `uuid.UUID`. Semplifica la serializzazione JSON.
