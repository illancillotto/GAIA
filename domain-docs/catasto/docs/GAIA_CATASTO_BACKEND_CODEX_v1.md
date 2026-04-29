# GAIA — Modulo Catasto
## Backend Implementation Prompt v1 (Fase 1)
### Per Cursor / Claude Code / GSD CLI

---

## Contesto

Stai lavorando su **GAIA**, un monolite modulare FastAPI + PostgreSQL.
Repository: `github.com/illancillotto/GAIA`
Backend path: `backend/app/modules/catasto/`
Documentazione di riferimento: `domain-docs/catasto/docs/GAIA_CATASTO_ARCHITECTURE_v1.md`

Il modulo `catasto` esiste già nel progetto (contiene logica SISTER/Playwright/Capacitas decoder).
Stai **estendendo** il modulo con la nuova anagrafica catastale, non sostituendo il codice esistente.

**Non modificare** route, modelli o service esistenti del modulo catasto che non siano citati esplicitamente in questo prompt.

---

## Step 1 — Abilita PostGIS + crea tutte le tabelle

Crea una nuova migration Alembic: `backend/alembic/versions/xxxx_catasto_postgis_tables.py`

### 1.1 Operazioni nella migration `upgrade()`

```python
# 1. Estensioni PostGIS
op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")

# 2. Crea le tabelle nell'ordine corretto (rispetta FK):
#    cat_import_batches
#    cat_schemi_contributo
#    cat_aliquote
#    cat_distretti
#    cat_distretto_coefficienti
#    cat_particelle              (con colonna geometry GEOMETRY(MultiPolygon, 4326))
#    cat_particelle_history
#    cat_utenze_irrigue
#    cat_intestatari
#    cat_anomalie
#    cat_sentinel_analisi
```

Usa lo schema completo definito in `GAIA_CATASTO_ARCHITECTURE_v1.md` sezione 3.2.

Per le colonne `geometry` usa il tipo `Geometry` di GeoAlchemy2:
```python
from geoalchemy2 import Geometry
# In colonna: sa.Column("geometry", Geometry("MULTIPOLYGON", srid=4326), nullable=True)
```

Aggiungi `geoalchemy2` a `backend/requirements.txt`.

### 1.2 Seed dati nella migration

Dopo aver creato le tabelle, inserisci:
```sql
INSERT INTO cat_schemi_contributo (id, codice, descrizione, attivo) VALUES
  (gen_random_uuid(), '0648', 'Contributo irriguo schema 0648', TRUE),
  (gen_random_uuid(), '0985', 'Contributo irriguo schema 0985', TRUE)
ON CONFLICT (codice) DO NOTHING;
```

### 1.3 Downgrade

Droppa le tabelle in ordine inverso e rimuovi le estensioni solo se non esistevano in precedenza (usa `DROP EXTENSION IF EXISTS postgis CASCADE` solo se aggiunte da questa migration).

### Acceptance Step 1
- [ ] `alembic upgrade head` completa senza errori
- [ ] `SELECT PostGIS_version();` ritorna una versione
- [ ] Tutte le 11 tabelle presenti: `\dt cat_*`
- [ ] Indici GIST creati: `\di idx_cat_part_geom`
- [ ] `cat_schemi_contributo` contiene i due record seed

---

## Step 2 — Modelli SQLAlchemy

Crea `backend/app/modules/catasto/models/registry.py`

Definisci i modelli ORM per:
- `CatParticella` (tabella `cat_particelle`)
- `CatParticellaHistory` (tabella `cat_particelle_history`)
- `CatDistretto` (tabella `cat_distretti`)
- `CatDistrettoCoefficienti` (tabella `cat_distretto_coefficienti`)
- `CatSchemaContributo` (tabella `cat_schemi_contributo`)
- `CatAliquota` (tabella `cat_aliquote`)
- `CatImportBatch` (tabella `cat_import_batches`)
- `CatUtenzeIrrigua` (tabella `cat_utenze_irrigue`)
- `CatIntestario` (tabella `cat_intestatari`)
- `CatAnomalia` (tabella `cat_anomalie`)

Note tecniche:
- Usa `geoalchemy2.types.Geometry` per la colonna `geometry` in `CatParticella` e `CatDistretto`
- I campi `GENERATED ALWAYS AS` (colonne calcolate come `fuori_distretto`, `ha_anomalie`) vanno dichiarati come `Column(..., Computed(..., persisted=True))` o come proprietà Python senza mapping DB diretto (preferisci la seconda per semplicità)
- Usa `UUID` come tipo primary key con `default=uuid4`
- Registra tutti i modelli nel `__init__.py` di `backend/app/modules/catasto/models/`

### Acceptance Step 2
- [ ] Import dei modelli senza errori: `from backend.app.modules.catasto.models.registry import CatParticella`
- [ ] Relationship `CatUtenzeIrrigua.particella` → `CatParticella` funzionante
- [ ] Relationship `CatAnomalia.particella` → `CatParticella` funzionante

---

## Step 3 — Service validazione

Crea `backend/app/modules/catasto/services/validation.py`

### 3.1 Funzione `validate_codice_fiscale`

```python
def validate_codice_fiscale(cf_raw: str | None) -> dict:
    """
    Ritorna:
    {
      "cf_normalizzato": str,        # MAIUSCOLO, stripped
      "is_valid": bool,
      "tipo": "PF" | "PG" | "FORMATO_SCONOSCIUTO",
      "error_code": str | None       # "CHECKSUM_ERRATO" | "LUNGHEZZA_ERRATA" | None
    }
    """
```

Implementazione:
- Se `cf_raw` è None o stringa vuota: `is_valid=False`, `tipo="MANCANTE"`
- Normalizza a MAIUSCOLO e rimuovi spazi
- Lunghezza 16: valida come PF usando libreria `codicefiscale`
  ```python
  import codicefiscale
  result = codicefiscale.decode(cf)
  is_valid = result is not None
  ```
- Lunghezza 11, solo cifre: valida come PG con algoritmo check digit mod 11
  ```python
  def _luhn_piva(piva: str) -> bool:
      s = 0
      for i, c in enumerate(piva[:-1]):
          n = int(c)
          if i % 2 == 0:
              s += n
          else:
              m = n * 2
              s += m if m < 10 else m - 9
      check = (10 - s % 10) % 10
      return check == int(piva[-1])
  ```
- Altro: `FORMATO_SCONOSCIUTO`

### 3.2 Caricamento comuni ISTAT

```python
# Scarica da ISTAT o usa file statico
# File: backend/app/modules/catasto/data/comuni_istat.csv
# Colonne: cod_istat (int), nome_comune (str), cod_provincia (int), regione (str)

_comuni_df: pd.DataFrame | None = None

def get_comuni() -> pd.DataFrame:
    global _comuni_df
    if _comuni_df is None:
        path = Path(__file__).parent.parent / "data" / "comuni_istat.csv"
        _comuni_df = pd.read_csv(path, dtype={"cod_istat": int})
    return _comuni_df

def validate_comune(cod_istat: int | None, nome: str | None) -> dict:
    """
    Ritorna: {"is_valid": bool, "nome_ufficiale": str | None}
    """
```

Crea il file `comuni_istat.csv` con almeno i comuni della provincia di Oristano (PVC=97).
Scarica da: https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv
oppure usa un CSV minimale hardcoded con i comuni del Consorzio (ARBOREA=165, MARRUBIU=283, NURACHI=222 e altri).

### 3.3 Funzioni restanti

```python
def validate_superficie(sup_irr: float, sup_cata: float, tolerance_pct: float = 0.01) -> dict:
    """Ritorna: {"ok": bool, "delta_pct": float, "delta_mq": float}"""

def validate_imponibile(imponibile: float, sup_irr: float, ind_sf: float, tolerance: float = 0.01) -> dict:
    """Ritorna: {"ok": bool, "delta": float, "atteso": float}"""

def validate_importo_0648(importo: float, imponibile: float, aliquota: float, tolerance: float = 0.01) -> dict:
    """
    Schema 0648 — contributo irriguo a aliquota fissa.
    Ricalcolabile: importo atteso = imponibile * aliquota.
    Ritorna: {"ok": bool, "delta": float, "atteso": float}
    """

def validate_importo_0985(importo: float, imponibile: float, aliquota: float, tolerance: float = 0.01) -> dict:
    """
    Schema 0985 — Quote Ordinarie a costo variabile (lettura contatori).
    L'aliquota incorpora già il consumo effettivo da Capacitas: NON è ricalcolabile.
    Questo check verifica SOLO la coerenza interna (importo ≈ imponibile * aliquota)
    ma NON segnala anomalia se il valore assoluto dell'aliquota è diverso da anni precedenti.
    L'importo 0985 è sempre trattato come dato autoritativo di Capacitas.
    Ritorna: {"ok": bool, "delta": float, "atteso": float}
    """
```

### Acceptance Step 3
- [ ] `validate_codice_fiscale("FNDGPP63E11B354D")` → `is_valid=True, tipo="PF"`
- [ ] `validate_codice_fiscale("Dnifse64c01l122y")` → `cf_normalizzato="DNIFSE64C01L122Y", is_valid=True`
- [ ] `validate_codice_fiscale("00588230953")` → `is_valid=True, tipo="PG"`
- [ ] `validate_codice_fiscale("XXXYYY")` → `is_valid=False, tipo="FORMATO_SCONOSCIUTO"`
- [ ] `validate_codice_fiscale(None)` → `is_valid=False, tipo="MANCANTE"`
- [ ] `validate_comune(165, "ARBOREA")` → `is_valid=True`
- [ ] `validate_superficie(16834, 16834)` → `ok=True`
- [ ] `validate_superficie(17000, 16834)` → `ok=False`

---

## Step 4 — Service import Capacitas

Crea `backend/app/modules/catasto/services/import_capacitas.py`

**Nota su CCO e collegamento consorziati**: Il campo `CCO` (es. `000000138`, `0A1146721`) è un identificativo interno Capacitas, **non corrisponde** al codice White Company. Per collegare una riga del ruolo all'anagrafica consorziati GAIA, usa `codice_fiscale` (PF: 16 car) o `codice_fiscale` come P.IVA (PG: 11 cifre). Il `CCO` viene salvato tel-quel come campo opaco per riconciliazione manuale futura.

### 4.1 Mapping colonne Excel → interni

```python
COLUMN_MAPPING = {
    "ANNO": "anno_campagna",
    "PVC": "cod_provincia",
    "COM": "cod_comune_istat",
    "CCO": "cco",
    "FRA": "cod_frazione",
    "DISTRETTO": "num_distretto",
    "Unnamed: 7": "nome_distretto_loc",
    "COMUNE": "nome_comune",
    "SEZIONE": "sezione_catastale",
    "FOGLIO": "foglio",
    "PARTIC": "particella",
    "SUB": "subalterno",
    "SUP.CATA.": "sup_catastale_mq",
    "SUP.IRRIGABILE": "sup_irrigabile_mq",
    "Ind. Spese Fisse": "ind_spese_fisse",
    "Imponibile s.f.": "imponibile_sf",
    "ESENTE 0648": "esente_0648",
    "ALIQUOTA 0648": "aliquota_0648",
    "IMPORTO 0648": "importo_0648",
    "ALIQUOTA 0985": "aliquota_0985",
    "IMPORTO 0985": "importo_0985",
    "DENOMINAZ": "denominazione",
    "CODFISC": "codice_fiscale",
}
```

### 4.2 Funzione principale

```python
async def import_capacitas(
    db: AsyncSession,
    file_bytes: bytes,
    filename: str,
    created_by: int,
    force: bool = False
) -> CatImportBatch:
```

Logica sequenziale:
1. Calcola `sha256(file_bytes)` → controlla duplicato su `cat_import_batches` dove `hash_file = sha256 AND status = 'completed'`
   - Se trovato e `force=False` → `raise HTTPException(409, "File già importato. Usa force=True per reimportare.")`
   - Se trovato e `force=True` → marca batch precedente come `replaced`
2. Leggi Excel: `pd.read_excel(BytesIO(file_bytes), sheet_name=None)`
   - Cerca sheet che inizia con `"Ruoli "` (case insensitive)
   - Se non trovato → raise con messaggio chiaro
3. Rinomina colonne con `COLUMN_MAPPING`
4. Normalizzazioni base:
   - `foglio` e `particella` → `str` (potrebbero essere numerici in pandas)
   - `subalterno` → str, None se NaN
   - `sezione_catastale` → str, None se NaN
   - `codice_fiscale` → strip whitespace, None se NaN
5. Crea record `CatImportBatch` con `status='processing'`, salva, ottieni `batch_id`
6. Costruisci lookup dict particelle:
   ```python
   # Pre-carica tutte le particelle del/dei comune(i) nel file
   comuni = df["cod_comune_istat"].unique().tolist()
   particelle_db = await db.execute(
       select(CatParticella).where(
           CatParticella.cod_comune_istat.in_(comuni),
           CatParticella.is_current == True
       )
   )
   # Indice: (cod_comune_istat, foglio, particella, subalterno) → id
   ```
7. Loop su righe DataFrame:
   - Esegui tutti i check VAL-01..08 usando le funzioni di `validation.py`
   - Costruisci oggetto `CatUtenzeIrrigua` con tutti i flag anomalia
   - Costruisci lista `CatAnomalia` per ogni check fallito
   - Accumula in liste per bulk insert
8. `db.bulk_save_objects(utenze_list)` + `db.bulk_save_objects(anomalie_list)`
9. Aggiorna batch con `status='completed'`, contatori, `report_json`
10. Upsert `CatDistrettoCoefficienti` per i coefficienti rilevati
11. Upsert `CatAliquote` per le aliquote rilevate

### 4.3 Schema `report_json`

```json
{
  "anno_campagna": 2025,
  "righe_totali": 90000,
  "righe_importate": 89750,
  "righe_con_anomalie": 1250,
  "anomalie": {
    "VAL-01-sup_eccede": {"count": 45, "severita": "error"},
    "VAL-02-cf_invalido": {"count": 320, "severita": "error"},
    "VAL-03-cf_mancante": {"count": 180, "severita": "warning"},
    "VAL-04-comune_invalido": {"count": 5, "severita": "warning"},
    "VAL-05-particella_assente": {"count": 700, "severita": "info"},
    "VAL-06-imponibile": {"count": 0, "severita": "warning"},
    "VAL-07-importi": {"count": 0, "severita": "warning"}
  },
  "preview_anomalie": [
    {"riga": 2, "tipo": "VAL-02-cf_invalido", "cf_raw": "Dnifse64c01l122y", "cf_norm": "DNIFSE64C01L122Y", "validato": true},
    ...
  ],
  "distretti_rilevati": [8, 26, 28, 35],
  "comuni_rilevati": ["ARBOREA", "MARRUBIU", "NURACHI"]
}
```

### Acceptance Step 4
- [ ] Import file esempio (24 righe) completa < 2s
- [ ] Batch creato con `status='completed'`
- [ ] Record `cat_utenze_irrigue` = 24
- [ ] CF `Dnifse64c01l122y` normalizzato a `DNIFSE64C01L122Y` e validato correttamente
- [ ] Re-import stesso file → 409 Conflict
- [ ] Re-import con `force=True` → batch precedente in `status='replaced'`, nuovo batch creato

---

## Step 5 — Service import shapefile

Crea `backend/app/modules/catasto/services/import_shapefile.py`

```python
async def finalize_shapefile_import(db: AsyncSession, created_by: int) -> CatImportBatch:
    """
    Assume che ogr2ogr abbia già popolato cat_particelle_staging.
    Questa funzione:
    1. Conta righe staging
    2. Upsert cat_particelle (SCD Type 2):
       - Record esistente con stesso (cod_comune_istat, foglio, particella, subalterno):
         se geometry o superficie cambiano: archivia vecchio in cat_particelle_history,
         aggiorna is_current=True con nuovi valori
       - Record nuovo: insert con is_current=True
    3. Aggiorna/crea CatImportBatch
    """
```

Aggiornamento architetturale successivo:
- `finalize_shapefile_import()` governa solo `cat_particelle` e `cat_particelle_history`
- i confini distrettuali sono importati tramite un finalize separato dedicato ai distretti
- `cat_distretti` resta la tabella corrente usata dal GIS, ma la tracciabilita delle geometrie va mantenuta in `cat_distretti_geometry_versions`

**Nota**: La tabella `cat_particelle_staging` viene creata da ogr2ogr e ha le stesse colonne dello shapefile. Il mapping colonne shapefile → `cat_particelle` va documentato qui con i nomi esatti delle colonne QGIS.

Crea lo script shell `scripts/import_shapefile_catasto.sh`:
```bash
#!/bin/bash
set -e
SHAPEFILE="${1:?Specificare path shapefile}"
PG_CONN="PG:host=${POSTGRES_HOST:-localhost} dbname=${POSTGRES_DB:-gaia} user=${POSTGRES_USER:-gaia} password=${POSTGRES_PASSWORD}"

echo "Import shapefile: $SHAPEFILE"
echo "Proiezione sorgente: EPSG:3003 (Monte Mario / Italy zone 1) → EPSG:4326"
ogr2ogr \
  -f PostgreSQL "$PG_CONN" \
  "$SHAPEFILE" \
  -nln cat_particelle_staging \
  -nlt MULTIPOLYGON \
  -s_srs EPSG:3003 \
  -t_srs EPSG:4326 \
  -overwrite \
  -progress

echo "Shapefile caricato in staging. Avvio finalize..."
curl -s -X POST http://localhost:8000/catasto/import/shapefile/finalize \
  -H "Authorization: Bearer ${GAIA_ADMIN_TOKEN}" \
  | python3 -m json.tool
```

### Acceptance Step 5
- [ ] Script shell eseguibile e documentato
- [ ] Endpoint `/catasto/import/shapefile/finalize` funzionante
- [ ] Dopo import: `cat_particelle` popolata con geometrie valide
- [ ] `cat_distretti` non viene alterata dall'import particelle
- [ ] Confini distrettuali gestiti dal flusso `/catasto/import/distretti/*` con storico geometrico dedicato

---

## Step 6 — Routes API

Crea i file route in `backend/app/modules/catasto/routes/`:

### `distretti.py`

```python
router = APIRouter(prefix="/catasto/distretti", tags=["catasto-distretti"])

@router.get("/")              # Lista distretti
@router.get("/{id}")          # Dettaglio
@router.get("/{id}/kpi")      # KPI per anno (query param: anno=2025)
@router.get("/{id}/geojson")  # GeoJSON poligono distretto
```

Per il GeoJSON usa:
```python
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
geojson = mapping(to_shape(distretto.geometry))
```

### `particelle.py`

```python
router = APIRouter(prefix="/catasto/particelle", tags=["catasto-particelle"])

@router.get("/")              # Lista paginata (filtri: distretto, comune, anno, ha_anomalie, cf)
@router.get("/{id}")          # Dettaglio
@router.get("/{id}/utenze")   # Ruoli tributo per anno
@router.get("/{id}/anomalie") # Anomalie della particella
@router.get("/{id}/geojson")  # GeoJSON geometria
```

### `import_routes.py`

```python
router = APIRouter(prefix="/catasto/import", tags=["catasto-import"])

@router.post("/capacitas")                        # Upload multipart, admin only
@router.post("/shapefile/finalize")               # Post-elaborazione ogr2ogr, admin only
@router.get("/{batch_id}/status")                 # Status + progress
@router.get("/{batch_id}/report")                 # Report anomalie paginato
@router.get("/history")                           # Lista batch
```

Per l'upload Capacitas avvia il processing come `BackgroundTask` di FastAPI e ritorna immediatamente il `batch_id`.

### `anomalie.py`

```python
router = APIRouter(prefix="/catasto/anomalie", tags=["catasto-anomalie"])

@router.get("/")              # Lista filtrata
@router.patch("/{id}")        # Update status, note, assigned_to
```

### Registrazione routes

Aggiungi al router principale del modulo catasto (o al `backend/app/main.py` se seguendo il pattern del progetto):
```python
from backend.app.modules.catasto.routes import distretti, particelle, import_routes, anomalie
app.include_router(distretti.router)
app.include_router(particelle.router)
app.include_router(import_routes.router)
app.include_router(anomalie.router)
```

### Acceptance Step 6
- [ ] `GET /catasto/distretti` → 200 con lista
- [ ] `GET /catasto/distretti/{id}/kpi?anno=2025` → 200 con KPI
- [ ] `GET /catasto/particelle?distretto=26&ha_anomalie=true` → 200, solo particelle distretto 26 con anomalie
- [ ] `POST /catasto/import/capacitas` con file test → 202 Accepted con `batch_id`
- [ ] `GET /catasto/import/{batch_id}/status` → 200 con progress
- [ ] Tutti gli endpoint richiedono JWT valido (401 senza token)

---

## Regole generali

- Segui i pattern SQLAlchemy e FastAPI già presenti nel progetto (async, dependency injection `get_db`)
- Usa `UUID` come PK, mai `int` per le nuove tabelle
- Tutti i timestamp in `TIMESTAMPTZ`
- Non modificare tabelle o route esistenti fuori dal modulo `catasto`
- Non rimuovere import o route esistenti nel modulo `catasto` (SISTER, elaborazioni, Capacitas decoder)
- Aggiungi `geoalchemy2` e `codicefiscale` a `backend/requirements.txt` se non presenti
- Ogni route che modifica dati richiede ruolo `admin`; letture richiedono qualsiasi ruolo autenticato
- Gestisci sempre le eccezioni nelle pipeline di import (un errore su una riga non deve bloccare tutto il batch)
