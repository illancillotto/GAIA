# GAIA — Modulo Catasto
## Architecture Document v1

---

## 1. Stack tecnologico aggiuntivo

| Componente | Tecnologia | Note |
|---|---|---|
| Spatial DB | PostGIS (estensione PostgreSQL) | Abilitare con `CREATE EXTENSION postgis;` |
| Tile server | **Martin** (Rust, container Docker) | Serve MVT tiles da PostGIS, leggero, zero-config |
| Mappa frontend | **MapLibre GL JS** | Open source, nessuna API key, supporta MVT |
| Shapefile import | `ogr2ogr` (GDAL) | Script amministrativo one-shot |
| Sentinel API | `openeo` Python SDK | Copernicus Data Space, gratuito per enti EU |
| CF validation | `codicefiscale` Python lib | Validazione algoritmo CF italiano |
| ISTAT comuni | CSV statico in `backend/app/data/` | Aggiornato annualmente da ISTAT |

---

## 2. Nuovi container Docker

```yaml
# Aggiunta a docker-compose.yml

martin:
  image: ghcr.io/maplibre/martin:latest
  restart: unless-stopped
  environment:
    - DATABASE_URL=postgresql://gaia:${POSTGRES_PASSWORD}@postgres:5432/gaia
  depends_on:
    - postgres
  # NON esposto pubblicamente - solo via nginx interno

# nginx: aggiungere proxy verso martin per /tiles/
```

**Nginx route aggiuntiva**:
```nginx
location /tiles/ {
    proxy_pass http://martin:3000/;
    proxy_cache_valid 200 1h;
    add_header Cache-Control "public, max-age=3600";
}
```

---

## 3. Schema database completo

### 3.1 Abilitazione PostGIS

```sql
-- Migrare con Alembic (operazione una tantum)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
```

### 3.2 Tabelle

```sql
-- ============================================================
-- ANAGRAFICA CATASTALE BASE (da shapefile / Excel 288k)
-- ============================================================

CREATE TABLE cat_particelle (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificatori catastali
    national_code       VARCHAR(25),            -- NATIONALCA
    cod_comune_istat    INTEGER NOT NULL,        -- COM (ISTAT)
    nome_comune         VARCHAR(100),
    sezione_catastale   VARCHAR(10),             -- SEZI_CENS
    foglio              VARCHAR(10) NOT NULL,    -- VARCHAR: alcuni fogli sono alfanumerici
    particella          VARCHAR(20) NOT NULL,    -- VARCHAR: STRADA058, 25, ecc.
    subalterno          VARCHAR(10),             -- SUB (a, b, A, B...)
    cfm                 VARCHAR(30),             -- A357-19-7 (comune-foglio-mappale)

    -- Superfici
    superficie_mq       NUMERIC(12,2),           -- SUPE_PART

    -- Distretto
    num_distretto       VARCHAR(10),             -- NUM_DIST (numero o 'FD')
    nome_distretto      VARCHAR(100),
    fuori_distretto     BOOLEAN GENERATED ALWAYS AS (num_distretto = 'FD') STORED,

    -- Geometria (da shapefile)
    geometry            GEOMETRY(MultiPolygon, 4326),

    -- Metadati import
    source_type         VARCHAR(20) DEFAULT 'shapefile',  -- 'shapefile' | 'excel_288k'
    import_batch_id     UUID,
    valid_from          DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to            DATE,                    -- NULL = record corrente
    is_current          BOOLEAN DEFAULT TRUE,
    suppressed          BOOLEAN DEFAULT FALSE,   -- particella soppressa catastalmente

    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- Indici
CREATE INDEX idx_cat_part_geom         ON cat_particelle USING GIST (geometry) WHERE is_current;
CREATE INDEX idx_cat_part_distretto    ON cat_particelle (num_distretto) WHERE is_current;
CREATE INDEX idx_cat_part_cfm          ON cat_particelle (cfm) WHERE is_current;
CREATE INDEX idx_cat_part_lookup       ON cat_particelle (cod_comune_istat, foglio, particella, subalterno) WHERE is_current;
CREATE INDEX idx_cat_part_comune       ON cat_particelle (cod_comune_istat) WHERE is_current;

-- Storico variazioni (SCD Type 2)
CREATE TABLE cat_particelle_history (
    LIKE cat_particelle INCLUDING ALL,
    history_id      UUID DEFAULT gen_random_uuid(),
    changed_at      TIMESTAMPTZ DEFAULT now(),
    change_reason   VARCHAR(50)   -- 'import_shapefile' | 'accorpamento' | 'soppressione'
);

-- ============================================================
-- DISTRETTI IRRIGUI
-- ============================================================

CREATE TABLE cat_distretti (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    num_distretto       VARCHAR(10) UNIQUE NOT NULL,
    nome_distretto      VARCHAR(200),
    decreto_istitutivo  VARCHAR(200),
    data_decreto        DATE,
    geometry            GEOMETRY(MultiPolygon, 4326),
    attivo              BOOLEAN DEFAULT TRUE,
    note                TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_cat_distretti_geom ON cat_distretti USING GIST (geometry);

-- Coefficienti per anno (ind. spese fisse storico)
CREATE TABLE cat_distretto_coefficienti (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    distretto_id    UUID NOT NULL REFERENCES cat_distretti(id),
    anno            INTEGER NOT NULL,
    ind_spese_fisse NUMERIC(6,4) NOT NULL,
    note            TEXT,
    UNIQUE (distretto_id, anno)
);

-- ============================================================
-- SCHEMI CONTRIBUTO (0648, 0985, futuri)
-- ============================================================

CREATE TABLE cat_schemi_contributo (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codice          VARCHAR(10) UNIQUE NOT NULL,   -- '0648', '0985'
    descrizione     VARCHAR(200),
    attivo          BOOLEAN DEFAULT TRUE
);

CREATE TABLE cat_aliquote (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schema_id       UUID NOT NULL REFERENCES cat_schemi_contributo(id),
    anno            INTEGER NOT NULL,
    aliquota        NUMERIC(10,6) NOT NULL,
    note            TEXT,
    UNIQUE (schema_id, anno)
);

-- ============================================================
-- RUOLI TRIBUTI (import Capacitas)
-- ============================================================

CREATE TABLE cat_import_batches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename        VARCHAR(255) NOT NULL,
    tipo            VARCHAR(20) NOT NULL,   -- 'capacitas_ruolo' | 'shapefile' | 'excel_288k'
    anno_campagna   INTEGER,
    hash_file       VARCHAR(64),            -- SHA-256 per idempotenza
    righe_totali    INTEGER DEFAULT 0,
    righe_importate INTEGER DEFAULT 0,
    righe_anomalie  INTEGER DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'processing',
    -- 'processing' | 'completed' | 'failed' | 'replaced'
    report_json     JSONB,
    errore          TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    created_by      INTEGER REFERENCES application_users(id)
);

CREATE TABLE cat_utenze_irrigue (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_batch_id     UUID NOT NULL REFERENCES cat_import_batches(id) ON DELETE CASCADE,

    -- Anno campagna
    anno_campagna       INTEGER NOT NULL,

    -- Codici Capacitas
    -- NOTA: CCO è un identificativo interno Capacitas, NON corrisponde al wc_id White Company.
    -- Il collegamento con l'anagrafica consorziati GAIA avviene tramite codice_fiscale/P.IVA.
    cco                 VARCHAR(20),            -- codice consorziato Capacitas (opaco)
    cod_provincia       INTEGER,
    cod_comune_istat    INTEGER,
    cod_frazione        INTEGER,

    -- Identificazione distretto
    num_distretto       INTEGER,
    nome_distretto_loc  VARCHAR(200),

    -- Identificazione catastale
    nome_comune         VARCHAR(100),
    sezione_catastale   VARCHAR(10),
    foglio              VARCHAR(10),
    particella          VARCHAR(20),
    subalterno          VARCHAR(10),

    -- FK verso anagrafica (NULL se particella non trovata in cat_particelle)
    particella_id       UUID REFERENCES cat_particelle(id),

    -- Superfici
    sup_catastale_mq    NUMERIC(12,2),
    sup_irrigabile_mq   NUMERIC(12,2),

    -- Calcolo tributo
    ind_spese_fisse     NUMERIC(6,4),
    imponibile_sf       NUMERIC(14,2),

    -- Schema 0648 — CONTRIBUTO IRRIGUO
    -- Aliquota fissa per anno, stessa per tutte le particelle dello stesso distretto
    -- Ricalcolabile: importo = imponibile_sf * aliquota_0648
    esente_0648         BOOLEAN DEFAULT FALSE,
    aliquota_0648       NUMERIC(10,6),
    importo_0648        NUMERIC(12,2),

    -- Schema 0985 — QUOTE ORDINARIE CONSORZIO
    -- Costo variabile: l'aliquota incorpora la lettura dei contatori idrici
    -- NON ricalcolabile dalla sola superficie: importo trattato come dato autoritativo Capacitas
    -- Il check VAL-07 verifica solo la coerenza interna (importo ≈ imponibile * aliquota)
    aliquota_0985       NUMERIC(10,6),
    importo_0985        NUMERIC(12,2),

    -- Proprietario (da Capacitas)
    denominazione       VARCHAR(500),
    codice_fiscale      VARCHAR(16),            -- SEMPRE normalizzato MAIUSCOLO
    codice_fiscale_raw  VARCHAR(16),            -- valore originale file (per audit)

    -- Flag anomalie (popolati da pipeline validazione)
    anomalia_superficie         BOOLEAN DEFAULT FALSE,
    anomalia_cf_invalido        BOOLEAN DEFAULT FALSE,
    anomalia_cf_mancante        BOOLEAN DEFAULT FALSE,
    anomalia_comune_invalido    BOOLEAN DEFAULT FALSE,
    anomalia_particella_assente BOOLEAN DEFAULT FALSE,
    anomalia_imponibile         BOOLEAN DEFAULT FALSE,
    anomalia_importi            BOOLEAN DEFAULT FALSE,
    ha_anomalie                 BOOLEAN GENERATED ALWAYS AS (
        anomalia_superficie OR anomalia_cf_invalido OR anomalia_cf_mancante OR
        anomalia_comune_invalido OR anomalia_imponibile OR anomalia_importi
    ) STORED,

    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_cat_utenze_batch       ON cat_utenze_irrigue (import_batch_id);
CREATE INDEX idx_cat_utenze_anno        ON cat_utenze_irrigue (anno_campagna);
CREATE INDEX idx_cat_utenze_distretto   ON cat_utenze_irrigue (num_distretto);
CREATE INDEX idx_cat_utenze_cf          ON cat_utenze_irrigue (codice_fiscale);
CREATE INDEX idx_cat_utenze_cco         ON cat_utenze_irrigue (cco);
CREATE INDEX idx_cat_utenze_particella  ON cat_utenze_irrigue (particella_id);
CREATE INDEX idx_cat_utenze_anomalie    ON cat_utenze_irrigue (ha_anomalie) WHERE ha_anomalie;
CREATE INDEX idx_cat_utenze_lookup      ON cat_utenze_irrigue (cod_comune_istat, foglio, particella, subalterno, anno_campagna);

-- ============================================================
-- INTESTATARI (da visure Sister o estratto da Capacitas)
-- ============================================================

CREATE TABLE cat_intestatari (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codice_fiscale      VARCHAR(16) NOT NULL UNIQUE,
    denominazione       VARCHAR(500),
    tipo                VARCHAR(5),             -- 'PF' | 'PG'
    -- PF fields
    cognome             VARCHAR(100),
    nome                VARCHAR(100),
    data_nascita        DATE,
    luogo_nascita       VARCHAR(100),
    -- PG fields
    ragione_sociale     VARCHAR(500),
    -- Source
    source              VARCHAR(20),            -- 'capacitas' | 'sister'
    last_verified_at    TIMESTAMPTZ,
    deceduto            BOOLEAN,
    dati_sister_json    JSONB,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- ANOMALIE CATASTALI
-- ============================================================

CREATE TABLE cat_anomalie (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    particella_id       UUID REFERENCES cat_particelle(id),
    utenza_id           UUID REFERENCES cat_utenze_irrigue(id),
    anno_campagna       INTEGER,

    tipo                VARCHAR(50) NOT NULL,
    -- Tipi da validazione import:
    --   'sup_eccede_catastale' | 'cf_invalido' | 'cf_mancante'
    --   'comune_invalido' | 'particella_non_trovata'
    --   'imponibile_incoerente' | 'importi_incoerenti'
    -- Tipi da analisi Sentinel:
    --   'presunto_non_pagante' | 'fd_irrigante_da_verificare'
    -- Tipi manuali:
    --   'proprietario_cambiato' | 'particella_soppressa'

    severita            VARCHAR(10) NOT NULL,   -- 'error' | 'warning' | 'info'
    descrizione         TEXT,
    dati_json           JSONB,                  -- dettaglio tecnico anomalia

    status              VARCHAR(25) DEFAULT 'aperta',
    -- 'aperta' | 'in_revisione' | 'chiusa' | 'segnalazione_inviata' | 'ignorata'

    note_operatore      TEXT,
    assigned_to         INTEGER REFERENCES application_users(id),
    segnalazione_id     UUID,                   -- FK verso operazioni.segnalazioni (futuro)

    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_cat_anomalie_particella ON cat_anomalie (particella_id);
CREATE INDEX idx_cat_anomalie_tipo       ON cat_anomalie (tipo);
CREATE INDEX idx_cat_anomalie_status     ON cat_anomalie (status);
CREATE INDEX idx_cat_anomalie_anno       ON cat_anomalie (anno_campagna);

-- ============================================================
-- ANALISI SENTINEL-2 (Fase 4)
-- ============================================================

CREATE TABLE cat_sentinel_analisi (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    particella_id       UUID NOT NULL REFERENCES cat_particelle(id),
    data_inizio         DATE NOT NULL,
    data_fine           DATE NOT NULL,
    ndvi_medio          NUMERIC(6,4),
    ndvi_max            NUMERIC(6,4),
    ndwi_medio          NUMERIC(6,4),
    classe              VARCHAR(30),
    -- 'irrigata_probabile' | 'non_irrigata' | 'incerta' | 'dati_insufficienti'
    confidence          NUMERIC(5,4),
    cloud_coverage_pct  NUMERIC(5,2),
    job_id              UUID,                   -- job Sentinel di riferimento
    reviewed            BOOLEAN DEFAULT FALSE,
    note                TEXT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_cat_sentinel_particella ON cat_sentinel_analisi (particella_id);
CREATE INDEX idx_cat_sentinel_date       ON cat_sentinel_analisi (data_inizio, data_fine);
```

---

## 4. Struttura moduli backend

```
backend/app/modules/catasto/
├── __init__.py
├── routes/
│   ├── __init__.py
│   ├── distretti.py          # CRUD distretti + GeoJSON
│   ├── particelle.py         # Lista, dettaglio, storico
│   ├── import_routes.py      # Upload + status import
│   ├── anomalie.py           # Lista, update status, assegnazione
│   └── sentinel.py           # Fase 4: trigger analisi, risultati
├── services/
│   ├── __init__.py
│   ├── import_capacitas.py   # Pipeline import + validazione
│   ├── import_shapefile.py   # Coordinamento post-ogr2ogr
│   ├── validation.py         # Check VAL-01..08, CF validator
│   ├── distretto_service.py  # KPI distretto, aggregazioni
│   └── sentinel_service.py   # Fase 4: openeo integration
├── models/
│   ├── __init__.py
│   ├── particelle.py
│   ├── distretti.py
│   ├── utenze.py
│   ├── anomalie.py
│   └── sentinel.py
├── schemas/
│   ├── __init__.py
│   ├── particelle.py
│   ├── distretti.py
│   ├── import_schemas.py
│   └── anomalie.py
└── data/
    └── comuni_istat.csv      # Tabella comuni italiani per validazione VAL-04
```

---

## 5. Endpoints API — Fase 1

```
# Distretti
GET    /catasto/distretti                      Lista distretti con KPI anno
GET    /catasto/distretti/{id}                 Dettaglio distretto
GET    /catasto/distretti/{id}/geojson         GeoJSON poligono distretto
GET    /catasto/distretti/{id}/particelle      Particelle del distretto (paginato)
GET    /catasto/distretti/{id}/kpi             KPI aggregati (per anno)

# Particelle
GET    /catasto/particelle                     Lista con filtri (distretto, anno, anomalie, CF)
GET    /catasto/particelle/{id}                Dettaglio particella
GET    /catasto/particelle/{id}/storico        Variazioni nel tempo
GET    /catasto/particelle/{id}/utenze         Ruoli tributo per anno
GET    /catasto/particelle/{id}/anomalie       Anomalie associate
GET    /catasto/particelle/{id}/geojson        GeoJSON geometria particella

# Import
POST   /catasto/import/capacitas               Upload file Capacitas (multipart)
GET    /catasto/import/{batch_id}/status       Status + progress import
GET    /catasto/import/{batch_id}/report       Report anomalie dettagliato
GET    /catasto/import/history                 Lista batch storici

# Anomalie
GET    /catasto/anomalie                       Lista con filtri
PATCH  /catasto/anomalie/{id}                  Update status/note/assegnazione
POST   /catasto/anomalie/{id}/segnalazione     Apri segnalazione operatori

# Schemi contributo
GET    /catasto/schemi                         Lista schemi (0648, 0985)
GET    /catasto/schemi/{id}/aliquote           Aliquote per anno

# Tiles (servite da Martin, proxy nginx)
GET    /tiles/cat_distretti/{z}/{x}/{y}        MVT tiles distretti
GET    /tiles/cat_particelle/{z}/{x}/{y}       MVT tiles particelle
```

---

## 6. Frontend — struttura pagine

```
frontend/src/app/catasto/
├── page.tsx                    # Dashboard catasto: KPI globali + accesso rapido
├── layout.tsx                  # Layout con sidebar catasto
├── import/
│   └── page.tsx                # Wizard import Capacitas
├── distretti/
│   ├── page.tsx                # Lista distretti con KPI
│   └── [id]/
│       └── page.tsx            # Dettaglio distretto
├── particelle/
│   ├── page.tsx                # Tabella particelle filtrabili
│   └── [id]/
│       └── page.tsx            # Scheda particella
├── anomalie/
│   └── page.tsx                # Lista anomalie + wizard revisione
└── mappa/
    └── page.tsx                # Mappa GIS (Fase 2)

frontend/src/components/catasto/
├── DistrettoCard.tsx
├── ParticellaDetail.tsx
├── ImportWizard.tsx
├── AnomalieTable.tsx
├── ValidationReport.tsx
├── DistrRettoMap.tsx           # Fase 2: MapLibre
└── ParticellaPopup.tsx         # Fase 2: popup mappa
```

---

## 7. Sequenza di avvio infrastruttura

### 7.1 Abilitare PostGIS (una tantum, tramite Alembic)
```python
# In migration Alembic
op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")
```

### 7.2 Import shapefile (script amministrativo)
```bash
# scripts/import_shapefile_catasto.sh
#!/bin/bash
SHAPEFILE=$1
ogr2ogr \
  -f PostgreSQL \
  "PG:host=localhost dbname=gaia user=gaia password=${POSTGRES_PASSWORD}" \
  "$SHAPEFILE" \
  -nln cat_particelle_staging \
  -nlt MULTIPOLYGON \
  -s_srs EPSG:3003 \
  -t_srs EPSG:4326 \
  -overwrite \
  -progress

# Poi chiamare endpoint GAIA per post-processing
curl -X POST http://localhost:8000/catasto/import/shapefile/finalize \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

### 7.3 Martin tile server
Martin rileva automaticamente le tabelle PostGIS con geometria. Configurazione minima:
```toml
# config/martin.toml
[postgres]
connection_string = "postgresql://gaia:${POSTGRES_PASSWORD}@postgres/gaia"

[[postgres.tables]]
schema = "public"
table = "cat_distretti"
srid = 4326
geometry_column = "geometry"

[[postgres.tables]]
schema = "public"
table = "cat_particelle"
srid = 4326
geometry_column = "geometry"
```

---

## 8. Note tecniche

### CF Validation
```python
# Usare libreria codicefiscale
# pip install codicefiscale
import codicefiscale

def validate_cf(cf_raw: str) -> tuple[str, bool, str]:
    cf = cf_raw.upper().strip()
    if len(cf) == 16:  # PF
        valid = codicefiscale.is_valid(cf)
        return cf, valid, "PF" if valid else "PF_INVALID"
    elif len(cf) == 11:  # PG
        valid = cf.isdigit() and luhn_check(cf)
        return cf, valid, "PG" if valid else "PG_INVALID"
    return cf, False, "FORMATO_SCONOSCIUTO"
```

### Spatial join per KPI distretto
```sql
-- Particelle per distretto (da shapefile, senza join tabellare)
SELECT d.id, d.num_distretto, COUNT(p.id) as n_particelle,
       SUM(p.superficie_mq) as sup_totale_mq
FROM cat_distretti d
LEFT JOIN cat_particelle p ON ST_Within(p.geometry, d.geometry)
WHERE p.is_current = TRUE
GROUP BY d.id, d.num_distretto;
```

### MapLibre GL JS — fonte dati
```javascript
// Sorgente tiles MVT da Martin
map.addSource('distretti', {
  type: 'vector',
  tiles: ['/tiles/cat_distretti/{z}/{x}/{y}'],
  minzoom: 8,
  maxzoom: 16
});

// GeoJSON dinamico per distretto selezionato
const response = await fetch(`/catasto/distretti/${id}/particelle/geojson`);
```
