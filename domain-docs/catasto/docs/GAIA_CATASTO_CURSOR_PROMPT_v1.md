# GAIA — Catasto Fase 1
## Prompt di implementazione per Cursor / Claude Code

---

## Contesto

Stai lavorando su **GAIA**, monolite modulare FastAPI + PostgreSQL + Next.js 14 App Router.
Repository root: `/opt/gaia` (o path locale del repo)
Documentazione di riferimento: `domain-docs/catasto/docs/`

Il modulo `catasto` esiste già in `backend/app/modules/catasto/` con logica SISTER/Playwright/Capacitas decoder. Stai **estendendo** quel modulo. Non toccare nulla di ciò che esiste già nel modulo a meno che non sia esplicitamente indicato.

Prima di iniziare: leggi i file seguenti per capire i pattern del progetto:
- `backend/app/modules/network/` — prendi come riferimento per struttura modulo
- `backend/app/main.py` — per capire come vengono registrati i router
- `backend/alembic/env.py` e una migration recente — per capire il pattern Alembic usato
- `frontend/src/app/operazioni/` — prendi come riferimento per struttura pagine frontend
- `frontend/src/lib/api/` — per capire come funziona il client API esistente

---

## STEP 1 — Dipendenze Python

**File**: `backend/requirements.txt`

Aggiungi le seguenti righe se non già presenti:
```
geoalchemy2>=0.14.0
codicefiscale>=2.1.0
```

Verifica che `pandas` e `openpyxl` siano già presenti (servono per l'import Excel). Se non ci sono, aggiungili.

**Acceptance**: `pip install -r backend/requirements.txt` completa senza errori.

---

## STEP 2 — Migration Alembic: PostGIS + tutte le tabelle

**File**: `backend/alembic/versions/XXXX_catasto_postgis_and_tables.py`
(sostituisci XXXX con il timestamp Alembic generato da `alembic revision`)

La migration deve:

### 2.1 — upgrade()

```python
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

def upgrade():
    # ── Estensioni PostGIS ──────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")

    # ── cat_import_batches ──────────────────────────────────────────────
    op.create_table("cat_import_batches",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("anno_campagna", sa.Integer(), nullable=True),
        sa.Column("hash_file", sa.String(64), nullable=True),
        sa.Column("righe_totali", sa.Integer(), server_default="0"),
        sa.Column("righe_importate", sa.Integer(), server_default="0"),
        sa.Column("righe_anomalie", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(20), server_default="'processing'"),
        sa.Column("report_json", sa.JSON(), nullable=True),
        sa.Column("errore", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=True),
    )

    # ── cat_schemi_contributo ───────────────────────────────────────────
    op.create_table("cat_schemi_contributo",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("codice", sa.String(10), nullable=False, unique=True),
        sa.Column("descrizione", sa.String(200), nullable=True),
        sa.Column("tipo_calcolo", sa.String(20), server_default="'fisso'"),
        # 'fisso' = aliquota fissa (0648), 'contatori' = variabile da lettura (0985)
        sa.Column("attivo", sa.Boolean(), server_default="true"),
    )

    # ── cat_aliquote ────────────────────────────────────────────────────
    op.create_table("cat_aliquote",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("schema_id", sa.UUID(), sa.ForeignKey("cat_schemi_contributo.id"), nullable=False),
        sa.Column("anno", sa.Integer(), nullable=False),
        sa.Column("aliquota", sa.Numeric(10, 6), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.UniqueConstraint("schema_id", "anno", name="uq_cat_aliquote_schema_anno"),
    )

    # ── cat_distretti ───────────────────────────────────────────────────
    op.create_table("cat_distretti",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("num_distretto", sa.String(10), nullable=False, unique=True),
        sa.Column("nome_distretto", sa.String(200), nullable=True),
        sa.Column("decreto_istitutivo", sa.String(200), nullable=True),
        sa.Column("data_decreto", sa.Date(), nullable=True),
        sa.Column("geometry", Geometry("MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("attivo", sa.Boolean(), server_default="true"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_cat_distretti_geom", "cat_distretti", ["geometry"], postgresql_using="gist")

    # ── cat_distretto_coefficienti ──────────────────────────────────────
    op.create_table("cat_distretto_coefficienti",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("distretto_id", sa.UUID(), sa.ForeignKey("cat_distretti.id"), nullable=False),
        sa.Column("anno", sa.Integer(), nullable=False),
        sa.Column("ind_spese_fisse", sa.Numeric(6, 4), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.UniqueConstraint("distretto_id", "anno", name="uq_cat_dc_distretto_anno"),
    )

    # ── cat_particelle ──────────────────────────────────────────────────
    op.create_table("cat_particelle",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("national_code", sa.String(25), nullable=True),
        sa.Column("cod_comune_istat", sa.Integer(), nullable=False),
        sa.Column("nome_comune", sa.String(100), nullable=True),
        sa.Column("sezione_catastale", sa.String(10), nullable=True),
        sa.Column("foglio", sa.String(10), nullable=False),
        sa.Column("particella", sa.String(20), nullable=False),
        sa.Column("subalterno", sa.String(10), nullable=True),
        sa.Column("cfm", sa.String(30), nullable=True),
        sa.Column("superficie_mq", sa.Numeric(12, 2), nullable=True),
        sa.Column("num_distretto", sa.String(10), nullable=True),
        sa.Column("nome_distretto", sa.String(100), nullable=True),
        sa.Column("geometry", Geometry("MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("source_type", sa.String(20), server_default="'shapefile'"),
        sa.Column("import_batch_id", sa.UUID(), nullable=True),
        sa.Column("valid_from", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default="true"),
        sa.Column("suppressed", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_cat_part_geom",       "cat_particelle", ["geometry"], postgresql_using="gist",
                    postgresql_where=sa.text("is_current = true"))
    op.create_index("idx_cat_part_distretto",  "cat_particelle", ["num_distretto"],
                    postgresql_where=sa.text("is_current = true"))
    op.create_index("idx_cat_part_cfm",        "cat_particelle", ["cfm"],
                    postgresql_where=sa.text("is_current = true"))
    op.create_index("idx_cat_part_lookup",     "cat_particelle",
                    ["cod_comune_istat", "foglio", "particella", "subalterno"],
                    postgresql_where=sa.text("is_current = true"))

    # ── cat_particelle_history ──────────────────────────────────────────
    op.create_table("cat_particelle_history",
        sa.Column("history_id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("particella_id", sa.UUID(), nullable=False),
        sa.Column("national_code", sa.String(25), nullable=True),
        sa.Column("cod_comune_istat", sa.Integer(), nullable=False),
        sa.Column("foglio", sa.String(10), nullable=False),
        sa.Column("particella", sa.String(20), nullable=False),
        sa.Column("subalterno", sa.String(10), nullable=True),
        sa.Column("superficie_mq", sa.Numeric(12, 2), nullable=True),
        sa.Column("num_distretto", sa.String(10), nullable=True),
        sa.Column("geometry", Geometry("MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=False),
        sa.Column("changed_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("change_reason", sa.String(50), nullable=True),
    )

    # ── cat_utenze_irrigue ──────────────────────────────────────────────
    op.create_table("cat_utenze_irrigue",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("import_batch_id", sa.UUID(), sa.ForeignKey("cat_import_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("anno_campagna", sa.Integer(), nullable=False),
        sa.Column("cco", sa.String(20), nullable=True),
        sa.Column("cod_provincia", sa.Integer(), nullable=True),
        sa.Column("cod_comune_istat", sa.Integer(), nullable=True),
        sa.Column("cod_frazione", sa.Integer(), nullable=True),
        sa.Column("num_distretto", sa.Integer(), nullable=True),
        sa.Column("nome_distretto_loc", sa.String(200), nullable=True),
        sa.Column("nome_comune", sa.String(100), nullable=True),
        sa.Column("sezione_catastale", sa.String(10), nullable=True),
        sa.Column("foglio", sa.String(10), nullable=True),
        sa.Column("particella", sa.String(20), nullable=True),
        sa.Column("subalterno", sa.String(10), nullable=True),
        sa.Column("particella_id", sa.UUID(), sa.ForeignKey("cat_particelle.id"), nullable=True),
        sa.Column("sup_catastale_mq", sa.Numeric(12, 2), nullable=True),
        sa.Column("sup_irrigabile_mq", sa.Numeric(12, 2), nullable=True),
        sa.Column("ind_spese_fisse", sa.Numeric(6, 4), nullable=True),
        sa.Column("imponibile_sf", sa.Numeric(14, 2), nullable=True),
        sa.Column("esente_0648", sa.Boolean(), server_default="false"),
        sa.Column("aliquota_0648", sa.Numeric(10, 6), nullable=True),
        sa.Column("importo_0648", sa.Numeric(12, 2), nullable=True),
        sa.Column("aliquota_0985", sa.Numeric(10, 6), nullable=True),
        sa.Column("importo_0985", sa.Numeric(12, 2), nullable=True),
        # NOTA: importo_0985 dipende da lettura contatori, è dato autoritativo Capacitas
        sa.Column("denominazione", sa.String(500), nullable=True),
        sa.Column("codice_fiscale", sa.String(16), nullable=True),       # sempre MAIUSCOLO
        sa.Column("codice_fiscale_raw", sa.String(16), nullable=True),   # originale file
        sa.Column("anomalia_superficie", sa.Boolean(), server_default="false"),
        sa.Column("anomalia_cf_invalido", sa.Boolean(), server_default="false"),
        sa.Column("anomalia_cf_mancante", sa.Boolean(), server_default="false"),
        sa.Column("anomalia_comune_invalido", sa.Boolean(), server_default="false"),
        sa.Column("anomalia_particella_assente", sa.Boolean(), server_default="false"),
        sa.Column("anomalia_imponibile", sa.Boolean(), server_default="false"),
        sa.Column("anomalia_importi", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_cat_utenze_batch",      "cat_utenze_irrigue", ["import_batch_id"])
    op.create_index("idx_cat_utenze_anno",       "cat_utenze_irrigue", ["anno_campagna"])
    op.create_index("idx_cat_utenze_distretto",  "cat_utenze_irrigue", ["num_distretto"])
    op.create_index("idx_cat_utenze_cf",         "cat_utenze_irrigue", ["codice_fiscale"])
    op.create_index("idx_cat_utenze_particella", "cat_utenze_irrigue", ["particella_id"])
    op.create_index("idx_cat_utenze_lookup",     "cat_utenze_irrigue",
                    ["cod_comune_istat", "foglio", "particella", "subalterno", "anno_campagna"])

    # ── cat_intestatari ─────────────────────────────────────────────────
    op.create_table("cat_intestatari",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("codice_fiscale", sa.String(16), nullable=False, unique=True),
        sa.Column("denominazione", sa.String(500), nullable=True),
        sa.Column("tipo", sa.String(5), nullable=True),   # 'PF' | 'PG'
        sa.Column("cognome", sa.String(100), nullable=True),
        sa.Column("nome", sa.String(100), nullable=True),
        sa.Column("data_nascita", sa.Date(), nullable=True),
        sa.Column("luogo_nascita", sa.String(100), nullable=True),
        sa.Column("ragione_sociale", sa.String(500), nullable=True),
        sa.Column("source", sa.String(20), nullable=True),   # 'capacitas' | 'sister'
        sa.Column("last_verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deceduto", sa.Boolean(), nullable=True),
        sa.Column("dati_sister_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    # ── cat_anomalie ────────────────────────────────────────────────────
    op.create_table("cat_anomalie",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("particella_id", sa.UUID(), sa.ForeignKey("cat_particelle.id"), nullable=True),
        sa.Column("utenza_id", sa.UUID(), sa.ForeignKey("cat_utenze_irrigue.id"), nullable=True),
        sa.Column("anno_campagna", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("severita", sa.String(10), nullable=False),   # 'error' | 'warning' | 'info'
        sa.Column("descrizione", sa.Text(), nullable=True),
        sa.Column("dati_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(25), server_default="'aperta'"),
        sa.Column("note_operatore", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=True),
        sa.Column("segnalazione_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_cat_anomalie_particella", "cat_anomalie", ["particella_id"])
    op.create_index("idx_cat_anomalie_tipo",       "cat_anomalie", ["tipo"])
    op.create_index("idx_cat_anomalie_status",     "cat_anomalie", ["status"])
    op.create_index("idx_cat_anomalie_anno",       "cat_anomalie", ["anno_campagna"])

    # ── Seed schemi contributo ──────────────────────────────────────────
    op.execute("""
        INSERT INTO cat_schemi_contributo (id, codice, descrizione, tipo_calcolo, attivo) VALUES
        (gen_random_uuid(), '0648', 'Contributo Irriguo - Opere Irrigue', 'fisso', true),
        (gen_random_uuid(), '0985', 'Quote Ordinarie Consorzio - Costo Variabile Contatori', 'contatori', true)
        ON CONFLICT (codice) DO NOTHING;
    """)
```

### 2.2 — downgrade()
Droppa le tabelle nell'ordine inverso: `cat_anomalie`, `cat_intestatari`, `cat_utenze_irrigue`, `cat_particelle_history`, `cat_particelle`, `cat_distretto_coefficienti`, `cat_distretti`, `cat_aliquote`, `cat_schemi_contributo`, `cat_import_batches`.
Non droppare le estensioni PostGIS (potrebbero essere usate da altre parti del sistema).

### Acceptance Step 2
- [ ] `alembic upgrade head` senza errori
- [ ] `SELECT PostGIS_version();` ritorna versione
- [ ] `SELECT tablename FROM pg_tables WHERE tablename LIKE 'cat_%';` → 10 tabelle
- [ ] `SELECT codice FROM cat_schemi_contributo;` → `0648` e `0985`

---

## STEP 3 — Modelli SQLAlchemy

**File**: `backend/app/modules/catasto/models/registry.py`

Crea i modelli ORM. Segui il pattern dei modelli esistenti nel progetto.

```python
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, Numeric, Date, Text, JSON, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from backend.app.database import Base  # adatta al path corretto del progetto

class CatImportBatch(Base):
    __tablename__ = "cat_import_batches"
    id = Column(sa.UUID, primary_key=True, default=uuid4)
    filename = Column(String(255), nullable=False)
    tipo = Column(String(20), nullable=False)
    anno_campagna = Column(Integer)
    hash_file = Column(String(64))
    righe_totali = Column(Integer, default=0)
    righe_importate = Column(Integer, default=0)
    righe_anomalie = Column(Integer, default=0)
    status = Column(String(20), default="processing")
    report_json = Column(JSON)
    errore = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    created_by = Column(Integer, ForeignKey("application_users.id"))
    utenze = relationship("CatUtenzeIrrigua", back_populates="batch", cascade="all, delete-orphan")

class CatSchemaContributo(Base):
    __tablename__ = "cat_schemi_contributo"
    id = Column(sa.UUID, primary_key=True, default=uuid4)
    codice = Column(String(10), nullable=False, unique=True)
    descrizione = Column(String(200))
    tipo_calcolo = Column(String(20), default="fisso")
    attivo = Column(Boolean, default=True)
    aliquote = relationship("CatAliquota", back_populates="schema")

class CatAliquota(Base):
    __tablename__ = "cat_aliquote"
    id = Column(sa.UUID, primary_key=True, default=uuid4)
    schema_id = Column(sa.UUID, ForeignKey("cat_schemi_contributo.id"), nullable=False)
    anno = Column(Integer, nullable=False)
    aliquota = Column(Numeric(10, 6), nullable=False)
    note = Column(Text)
    schema = relationship("CatSchemaContributo", back_populates="aliquote")

class CatDistretto(Base):
    __tablename__ = "cat_distretti"
    id = Column(sa.UUID, primary_key=True, default=uuid4)
    num_distretto = Column(String(10), nullable=False, unique=True)
    nome_distretto = Column(String(200))
    decreto_istitutivo = Column(String(200))
    data_decreto = Column(Date)
    geometry = Column(Geometry("MULTIPOLYGON", srid=4326))
    attivo = Column(Boolean, default=True)
    note = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))
    coefficienti = relationship("CatDistrettoCoefficienti", back_populates="distretto")

class CatDistrettoCoefficienti(Base):
    __tablename__ = "cat_distretto_coefficienti"
    id = Column(sa.UUID, primary_key=True, default=uuid4)
    distretto_id = Column(sa.UUID, ForeignKey("cat_distretti.id"), nullable=False)
    anno = Column(Integer, nullable=False)
    ind_spese_fisse = Column(Numeric(6, 4), nullable=False)
    note = Column(Text)
    distretto = relationship("CatDistretto", back_populates="coefficienti")

class CatParticella(Base):
    __tablename__ = "cat_particelle"
    id = Column(sa.UUID, primary_key=True, default=uuid4)
    national_code = Column(String(25))
    cod_comune_istat = Column(Integer, nullable=False)
    nome_comune = Column(String(100))
    sezione_catastale = Column(String(10))
    foglio = Column(String(10), nullable=False)
    particella = Column(String(20), nullable=False)
    subalterno = Column(String(10))
    cfm = Column(String(30))
    superficie_mq = Column(Numeric(12, 2))
    num_distretto = Column(String(10))
    nome_distretto = Column(String(100))
    geometry = Column(Geometry("MULTIPOLYGON", srid=4326))
    source_type = Column(String(20), default="shapefile")
    import_batch_id = Column(sa.UUID)
    valid_from = Column(Date)
    valid_to = Column(Date)
    is_current = Column(Boolean, default=True)
    suppressed = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))

    @property
    def fuori_distretto(self) -> bool:
        return self.num_distretto == "FD"

    utenze = relationship("CatUtenzeIrrigua", back_populates="particella")
    anomalie = relationship("CatAnomalia", back_populates="particella")

class CatUtenzeIrrigua(Base):
    __tablename__ = "cat_utenze_irrigue"
    id = Column(sa.UUID, primary_key=True, default=uuid4)
    import_batch_id = Column(sa.UUID, ForeignKey("cat_import_batches.id", ondelete="CASCADE"), nullable=False)
    anno_campagna = Column(Integer, nullable=False)
    cco = Column(String(20))
    cod_provincia = Column(Integer)
    cod_comune_istat = Column(Integer)
    cod_frazione = Column(Integer)
    num_distretto = Column(Integer)
    nome_distretto_loc = Column(String(200))
    nome_comune = Column(String(100))
    sezione_catastale = Column(String(10))
    foglio = Column(String(10))
    particella = Column(String(20))
    subalterno = Column(String(10))
    particella_id = Column(sa.UUID, ForeignKey("cat_particelle.id"))
    sup_catastale_mq = Column(Numeric(12, 2))
    sup_irrigabile_mq = Column(Numeric(12, 2))
    ind_spese_fisse = Column(Numeric(6, 4))
    imponibile_sf = Column(Numeric(14, 2))
    esente_0648 = Column(Boolean, default=False)
    aliquota_0648 = Column(Numeric(10, 6))
    importo_0648 = Column(Numeric(12, 2))
    aliquota_0985 = Column(Numeric(10, 6))
    importo_0985 = Column(Numeric(12, 2))
    denominazione = Column(String(500))
    codice_fiscale = Column(String(16))
    codice_fiscale_raw = Column(String(16))
    anomalia_superficie = Column(Boolean, default=False)
    anomalia_cf_invalido = Column(Boolean, default=False)
    anomalia_cf_mancante = Column(Boolean, default=False)
    anomalia_comune_invalido = Column(Boolean, default=False)
    anomalia_particella_assente = Column(Boolean, default=False)
    anomalia_imponibile = Column(Boolean, default=False)
    anomalia_importi = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True))

    @property
    def ha_anomalie(self) -> bool:
        return any([
            self.anomalia_superficie, self.anomalia_cf_invalido,
            self.anomalia_cf_mancante, self.anomalia_comune_invalido,
            self.anomalia_imponibile, self.anomalia_importi,
        ])

    batch = relationship("CatImportBatch", back_populates="utenze")
    particella = relationship("CatParticella", back_populates="utenze")
    anomalie = relationship("CatAnomalia", back_populates="utenza")

class CatIntestario(Base):
    __tablename__ = "cat_intestatari"
    id = Column(sa.UUID, primary_key=True, default=uuid4)
    codice_fiscale = Column(String(16), nullable=False, unique=True)
    denominazione = Column(String(500))
    tipo = Column(String(5))
    cognome = Column(String(100))
    nome = Column(String(100))
    data_nascita = Column(Date)
    luogo_nascita = Column(String(100))
    ragione_sociale = Column(String(500))
    source = Column(String(20))
    last_verified_at = Column(TIMESTAMP(timezone=True))
    deceduto = Column(Boolean)
    dati_sister_json = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))

class CatAnomalia(Base):
    __tablename__ = "cat_anomalie"
    id = Column(sa.UUID, primary_key=True, default=uuid4)
    particella_id = Column(sa.UUID, ForeignKey("cat_particelle.id"))
    utenza_id = Column(sa.UUID, ForeignKey("cat_utenze_irrigue.id"))
    anno_campagna = Column(Integer)
    tipo = Column(String(50), nullable=False)
    severita = Column(String(10), nullable=False)
    descrizione = Column(Text)
    dati_json = Column(JSON)
    status = Column(String(25), default="aperta")
    note_operatore = Column(Text)
    assigned_to = Column(Integer, ForeignKey("application_users.id"))
    segnalazione_id = Column(sa.UUID)
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))

    particella = relationship("CatParticella", back_populates="anomalie")
    utenza = relationship("CatUtenzeIrrigua", back_populates="anomalie")
```

Assicurati che tutti i modelli siano importati nell'`__init__.py` del package `models/`.

### Acceptance Step 3
- [ ] `from backend.app.modules.catasto.models.registry import CatParticella` senza errori
- [ ] `CatParticella().fuori_distretto` property funzionante
- [ ] Relationship `CatUtenzeIrrigua.batch`, `CatUtenzeIrrigua.particella`, `CatAnomalia.particella` configurate

---

## STEP 4 — Service validazione

**File**: `backend/app/modules/catasto/services/validation.py`
**File**: `backend/app/modules/catasto/data/comuni_istat.csv`

### 4.1 Scarica o crea il CSV comuni italiani

Crea `backend/app/modules/catasto/data/comuni_istat.csv` con almeno le colonne:
`cod_istat,nome_comune,cod_provincia,sigla_provincia,regione`

Puoi ottenerlo da: https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv
oppure crealo con i comuni della provincia di Oristano (cod_prov=95) come minimo funzionale:
```
cod_istat,nome_comune,cod_provincia,sigla_provincia,regione
95001,Abbasanta,95,OR,Sardegna
95002,Aidomaggiore,95,OR,Sardegna
...
95165,Arborea,95,OR,Sardegna
95283,Marrubiu,95,OR,Sardegna  
95222,Nurachi,95,OR,Sardegna
```
(nota: usa i codici ISTAT reali della provincia di Oristano)

### 4.2 Implementa le funzioni

```python
import pandas as pd
from pathlib import Path
import codicefiscale

_comuni_df = None

def _get_comuni() -> pd.DataFrame:
    global _comuni_df
    if _comuni_df is None:
        csv_path = Path(__file__).parent.parent / "data" / "comuni_istat.csv"
        _comuni_df = pd.read_csv(csv_path, dtype={"cod_istat": int})
    return _comuni_df

def validate_codice_fiscale(cf_raw: str | None) -> dict:
    """
    Returns: {cf_normalizzato, is_valid, tipo, error_code}
    tipo: 'PF' | 'PG' | 'MANCANTE' | 'FORMATO_SCONOSCIUTO'
    """
    if not cf_raw or str(cf_raw).strip() == "" or str(cf_raw).upper() == "NAN":
        return {"cf_normalizzato": None, "is_valid": False, "tipo": "MANCANTE", "error_code": "CF_MANCANTE"}
    cf = str(cf_raw).upper().strip()
    if len(cf) == 16:
        try:
            decoded = codicefiscale.decode(cf)
            is_valid = decoded is not None
            return {"cf_normalizzato": cf, "is_valid": is_valid, "tipo": "PF",
                    "error_code": None if is_valid else "CHECKSUM_ERRATO"}
        except Exception:
            return {"cf_normalizzato": cf, "is_valid": False, "tipo": "PF", "error_code": "CHECKSUM_ERRATO"}
    elif len(cf) == 11 and cf.isdigit():
        is_valid = _check_digit_piva(cf)
        return {"cf_normalizzato": cf, "is_valid": is_valid, "tipo": "PG",
                "error_code": None if is_valid else "CHECKSUM_ERRATO"}
    else:
        return {"cf_normalizzato": cf, "is_valid": False, "tipo": "FORMATO_SCONOSCIUTO",
                "error_code": "FORMATO_NON_RICONOSCIUTO"}

def _check_digit_piva(piva: str) -> bool:
    s = 0
    for i, c in enumerate(piva[:-1]):
        n = int(c)
        if i % 2 == 0:
            s += n
        else:
            m = n * 2
            s += m if m < 10 else m - 9
    return (10 - s % 10) % 10 == int(piva[-1])

def validate_comune(cod_istat: int | None) -> dict:
    """Returns: {is_valid, nome_ufficiale}"""
    if cod_istat is None:
        return {"is_valid": False, "nome_ufficiale": None}
    comuni = _get_comuni()
    match = comuni[comuni["cod_istat"] == int(cod_istat)]
    if match.empty:
        return {"is_valid": False, "nome_ufficiale": None}
    return {"is_valid": True, "nome_ufficiale": match.iloc[0]["nome_comune"]}

def validate_superficie(sup_irr: float | None, sup_cata: float | None, tolerance_pct: float = 0.01) -> dict:
    if sup_irr is None or sup_cata is None:
        return {"ok": True, "delta_pct": 0.0, "delta_mq": 0.0}  # non possiamo validare
    delta = float(sup_irr) - float(sup_cata)
    delta_pct = delta / float(sup_cata) if sup_cata > 0 else 0
    ok = delta_pct <= tolerance_pct
    return {"ok": ok, "delta_pct": round(delta_pct, 6), "delta_mq": round(delta, 2)}

def validate_imponibile(imponibile: float | None, sup_irr: float | None, ind_sf: float | None, tolerance: float = 0.01) -> dict:
    if any(v is None for v in [imponibile, sup_irr, ind_sf]):
        return {"ok": True, "delta": 0.0, "atteso": None}
    atteso = float(sup_irr) * float(ind_sf)
    delta = abs(float(imponibile) - atteso)
    return {"ok": delta <= tolerance, "delta": round(delta, 4), "atteso": round(atteso, 2)}

def validate_importo_0648(importo: float | None, imponibile: float | None, aliquota: float | None, tolerance: float = 0.01) -> dict:
    """Schema 0648 - aliquota fissa, importo ricalcolabile."""
    if any(v is None for v in [importo, imponibile, aliquota]):
        return {"ok": True, "delta": 0.0, "atteso": None}
    atteso = float(imponibile) * float(aliquota)
    delta = abs(float(importo) - atteso)
    return {"ok": delta <= tolerance, "delta": round(delta, 4), "atteso": round(atteso, 4)}

def validate_importo_0985(importo: float | None, imponibile: float | None, aliquota: float | None, tolerance: float = 0.01) -> dict:
    """
    Schema 0985 - costo variabile da lettura contatori.
    L'importo è dato autoritativo Capacitas: non segnaliamo anomalia sul valore assoluto.
    Verifichiamo solo la coerenza matematica interna (importo ≈ imponibile * aliquota).
    """
    if any(v is None for v in [importo, imponibile, aliquota]):
        return {"ok": True, "delta": 0.0, "atteso": None}
    atteso = float(imponibile) * float(aliquota)
    delta = abs(float(importo) - atteso)
    return {"ok": delta <= tolerance, "delta": round(delta, 4), "atteso": round(atteso, 4)}
```

### Acceptance Step 4
- [ ] `validate_codice_fiscale("FNDGPP63E11B354D")` → `{is_valid: True, tipo: "PF"}`
- [ ] `validate_codice_fiscale("Dnifse64c01l122y")` → `{cf_normalizzato: "DNIFSE64C01L122Y", is_valid: True}`
- [ ] `validate_codice_fiscale("00588230953")` → `{is_valid: True, tipo: "PG"}`
- [ ] `validate_codice_fiscale(None)` → `{is_valid: False, tipo: "MANCANTE"}`
- [ ] `validate_comune(165)` → `{is_valid: True, nome_ufficiale: "Arborea"}` (o nome ISTAT ufficiale)
- [ ] `validate_superficie(16834, 16834)` → `{ok: True}`
- [ ] `validate_superficie(17100, 16834)` → `{ok: False}`

---

## STEP 5 — Service import Capacitas

**File**: `backend/app/modules/catasto/services/import_capacitas.py`

```python
import hashlib
import pandas as pd
from io import BytesIO
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
    "PARTIC": "particella",     # VARCHAR: può essere "STRADA058"
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

async def import_capacitas(
    db: AsyncSession,
    file_bytes: bytes,
    filename: str,
    created_by: int,
    force: bool = False,
) -> "CatImportBatch":
    from backend.app.modules.catasto.models.registry import (
        CatImportBatch, CatUtenzeIrrigua, CatAnomalia,
        CatParticella, CatDistrettoCoefficienti, CatAliquota, CatSchemaContributo
    )
    from backend.app.modules.catasto.services.validation import (
        validate_codice_fiscale, validate_comune, validate_superficie,
        validate_imponibile, validate_importo_0648, validate_importo_0985
    )

    # ── 1. Hash + idempotenza ──────────────────────────────────────────
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    existing = await db.execute(
        select(CatImportBatch).where(
            CatImportBatch.hash_file == file_hash,
            CatImportBatch.status == "completed"
        )
    )
    existing_batch = existing.scalar_one_or_none()
    if existing_batch and not force:
        raise ValueError(f"File già importato (batch {existing_batch.id}). Usa force=True per reimportare.")
    if existing_batch and force:
        existing_batch.status = "replaced"
        await db.flush()

    # ── 2. Leggi Excel ─────────────────────────────────────────────────
    all_sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None, dtype=str)
    sheet_name = next((k for k in all_sheets if k.lower().startswith("ruoli")), None)
    if not sheet_name:
        raise ValueError("Sheet 'Ruoli ANNO' non trovato nel file Excel.")
    df = all_sheets[sheet_name]

    # ── 3. Rinomina + normalizzazioni base ─────────────────────────────
    df = df.rename(columns={k: v for k, v in COLUMN_MAPPING.items() if k in df.columns})
    df["foglio"] = df["foglio"].fillna("").astype(str).str.strip()
    df["particella"] = df["particella"].fillna("").astype(str).str.strip()
    df["subalterno"] = df["subalterno"].where(df["subalterno"].notna() & (df["subalterno"] != "nan"), None)
    df["sezione_catastale"] = df["sezione_catastale"].where(df["sezione_catastale"].notna() & (df["sezione_catastale"] != "nan"), None)
    df["codice_fiscale"] = df["codice_fiscale"].where(df["codice_fiscale"].notna() & (df["codice_fiscale"] != "nan"), None)

    # Conversione numerici
    for col in ["anno_campagna", "cod_provincia", "cod_comune_istat", "cod_frazione", "num_distretto"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["sup_catastale_mq", "sup_irrigabile_mq", "ind_spese_fisse", "imponibile_sf",
                "aliquota_0648", "importo_0648", "aliquota_0985", "importo_0985"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── 4. Crea batch ─────────────────────────────────────────────────
    anno = int(df["anno_campagna"].dropna().iloc[0]) if "anno_campagna" in df.columns else None
    batch = CatImportBatch(
        filename=filename,
        tipo="capacitas_ruolo",
        anno_campagna=anno,
        hash_file=file_hash,
        righe_totali=len(df),
        status="processing",
        created_by=created_by,
        created_at=datetime.now(timezone.utc),
    )
    db.add(batch)
    await db.flush()  # ottieni batch.id

    # ── 5. Pre-carica lookup particelle ───────────────────────────────
    comuni = [int(c) for c in df["cod_comune_istat"].dropna().unique().tolist()]
    result = await db.execute(
        select(CatParticella).where(
            CatParticella.cod_comune_istat.in_(comuni),
            CatParticella.is_current == True
        )
    )
    particelle_list = result.scalars().all()
    # Indice: (cod_comune_istat, foglio, particella, subalterno|None) → particella.id
    particelle_idx = {
        (p.cod_comune_istat, p.foglio, p.particella, p.subalterno): p.id
        for p in particelle_list
    }

    # ── 6. Loop righe ─────────────────────────────────────────────────
    utenze_batch = []
    anomalie_batch = []
    anomalie_count = {
        "VAL-01-sup_eccede": 0, "VAL-02-cf_invalido": 0,
        "VAL-03-cf_mancante": 0, "VAL-04-comune_invalido": 0,
        "VAL-05-particella_assente": 0, "VAL-06-imponibile": 0,
        "VAL-07-importi": 0,
    }
    preview_anomalie = []

    for idx, row in df.iterrows():
        def get(col):
            v = row.get(col)
            return None if pd.isna(v) else v

        # Normalizza CF
        cf_raw = get("codice_fiscale")
        cf_result = validate_codice_fiscale(cf_raw)
        cf_norm = cf_result["cf_normalizzato"]

        # Check VAL-01
        v01 = validate_superficie(get("sup_irrigabile_mq"), get("sup_catastale_mq"))
        # Check VAL-02/03
        anom_cf_inv = cf_result["tipo"] not in ("MANCANTE",) and not cf_result["is_valid"]
        anom_cf_man = cf_result["tipo"] == "MANCANTE"
        # Check VAL-04
        v04 = validate_comune(get("cod_comune_istat"))
        # Check VAL-05
        lookup_key = (
            int(get("cod_comune_istat")) if get("cod_comune_istat") else None,
            str(get("foglio") or ""),
            str(get("particella") or ""),
            str(get("subalterno")) if get("subalterno") else None,
        )
        particella_id = particelle_idx.get(lookup_key) if lookup_key[0] else None
        anom_part_assente = particella_id is None and lookup_key[0] is not None
        # Check VAL-06
        v06 = validate_imponibile(get("imponibile_sf"), get("sup_irrigabile_mq"), get("ind_spese_fisse"))
        # Check VAL-07
        v07_648 = validate_importo_0648(get("importo_0648"), get("imponibile_sf"), get("aliquota_0648"))
        v07_985 = validate_importo_0985(get("importo_0985"), get("imponibile_sf"), get("aliquota_0985"))
        anom_importi = not v07_648["ok"] or not v07_985["ok"]

        # Crea utenza
        utenza = CatUtenzeIrrigua(
            import_batch_id=batch.id,
            anno_campagna=int(get("anno_campagna")) if get("anno_campagna") else anno,
            cco=str(get("cco")) if get("cco") else None,
            cod_provincia=int(get("cod_provincia")) if get("cod_provincia") else None,
            cod_comune_istat=int(get("cod_comune_istat")) if get("cod_comune_istat") else None,
            cod_frazione=int(get("cod_frazione")) if get("cod_frazione") else None,
            num_distretto=int(get("num_distretto")) if get("num_distretto") else None,
            nome_distretto_loc=get("nome_distretto_loc"),
            nome_comune=get("nome_comune"),
            sezione_catastale=get("sezione_catastale"),
            foglio=str(get("foglio") or ""),
            particella=str(get("particella") or ""),
            subalterno=str(get("subalterno")) if get("subalterno") else None,
            particella_id=particella_id,
            sup_catastale_mq=get("sup_catastale_mq"),
            sup_irrigabile_mq=get("sup_irrigabile_mq"),
            ind_spese_fisse=get("ind_spese_fisse"),
            imponibile_sf=get("imponibile_sf"),
            esente_0648=bool(get("esente_0648")) if get("esente_0648") is not None else False,
            aliquota_0648=get("aliquota_0648"),
            importo_0648=get("importo_0648"),
            aliquota_0985=get("aliquota_0985"),
            importo_0985=get("importo_0985"),
            denominazione=get("denominazione"),
            codice_fiscale=cf_norm,
            codice_fiscale_raw=cf_raw,
            anomalia_superficie=not v01["ok"],
            anomalia_cf_invalido=anom_cf_inv,
            anomalia_cf_mancante=anom_cf_man,
            anomalia_comune_invalido=not v04["is_valid"],
            anomalia_particella_assente=anom_part_assente,
            anomalia_imponibile=not v06["ok"],
            anomalia_importi=anom_importi,
            created_at=datetime.now(timezone.utc),
        )
        utenze_batch.append(utenza)

        # Crea anomalie
        def add_anomalia(tipo, severita, descrizione, dati):
            anomalie_count[tipo] = anomalie_count.get(tipo, 0) + 1
            if len(preview_anomalie) < 50:
                preview_anomalie.append({"riga": idx + 2, "tipo": tipo, **dati})
            return CatAnomalia(
                utenza_id=None,  # verrà linkato dopo flush
                anno_campagna=utenza.anno_campagna,
                tipo=tipo,
                severita=severita,
                descrizione=descrizione,
                dati_json=dati,
                status="aperta",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

        if not v01["ok"]:
            anomalie_batch.append(add_anomalia(
                "VAL-01-sup_eccede", "error",
                f"Sup. irrigabile ({get('sup_irrigabile_mq')}) eccede catastale ({get('sup_catastale_mq')})",
                {"delta_mq": v01["delta_mq"], "delta_pct": v01["delta_pct"]},
            ))
        if anom_cf_inv:
            anomalie_batch.append(add_anomalia(
                "VAL-02-cf_invalido", "error",
                f"CF non valido: {cf_raw} (normalizzato: {cf_norm})",
                {"cf_raw": cf_raw, "cf_norm": cf_norm, "error_code": cf_result["error_code"]},
            ))
        if anom_cf_man:
            anomalie_batch.append(add_anomalia("VAL-03-cf_mancante", "warning", "CF mancante", {}))
        if not v04["is_valid"]:
            anomalie_batch.append(add_anomalia(
                "VAL-04-comune_invalido", "warning",
                f"Codice comune ISTAT {get('cod_comune_istat')} non trovato",
                {"cod_istat": get("cod_comune_istat")},
            ))
        if anom_part_assente:
            anomalie_batch.append(add_anomalia(
                "VAL-05-particella_assente", "info",
                "Particella non presente in anagrafica catastale",
                {"foglio": str(get("foglio")), "particella": str(get("particella"))},
            ))
        if not v06["ok"]:
            anomalie_batch.append(add_anomalia(
                "VAL-06-imponibile", "warning",
                f"Imponibile incoerente: atteso {v06['atteso']}, trovato {get('imponibile_sf')}",
                v06,
            ))
        if anom_importi:
            anomalie_batch.append(add_anomalia(
                "VAL-07-importi", "warning",
                "Importi 0648/0985 incoerenti con imponibile×aliquota",
                {"v07_648": v07_648, "v07_985": v07_985},
            ))

    # ── 7. Bulk insert ────────────────────────────────────────────────
    db.add_all(utenze_batch)
    await db.flush()

    # Linka utenza_id nelle anomalie (dopo flush le utenze hanno id)
    for i, anomalia in enumerate(anomalie_batch):
        if i < len(utenze_batch):
            anomalia.utenza_id = utenze_batch[i].id
    db.add_all(anomalie_batch)

    # ── 8. Upsert coefficienti distretto ──────────────────────────────
    # (upsert tramite merge o insert on conflict - vedi pattern progetto)
    # Per ogni distretto/anno unico nel file, upserta CatDistrettoCoefficienti se il distretto esiste

    # ── 9. Aggiorna batch ─────────────────────────────────────────────
    righe_con_anomalie = sum(1 for u in utenze_batch if u.ha_anomalie)
    batch.righe_importate = len(utenze_batch)
    batch.righe_anomalie = righe_con_anomalie
    batch.status = "completed"
    batch.completed_at = datetime.now(timezone.utc)
    batch.report_json = {
        "anno_campagna": anno,
        "righe_totali": len(df),
        "righe_importate": len(utenze_batch),
        "righe_con_anomalie": righe_con_anomalie,
        "anomalie": {k: {"count": v} for k, v in anomalie_count.items()},
        "preview_anomalie": preview_anomalie,
        "distretti_rilevati": [int(d) for d in df["num_distretto"].dropna().unique().tolist()],
        "comuni_rilevati": df["nome_comune"].dropna().unique().tolist(),
    }

    await db.commit()
    return batch
```

### Acceptance Step 5
- [ ] Import del file esempio 24 righe → `status='completed'`, 24 utenze create
- [ ] CF `Dnifse64c01l122y` → `codice_fiscale='DNIFSE64C01L122Y'`, `codice_fiscale_raw='Dnifse64c01l122y'`
- [ ] Re-import stesso file → `ValueError` con messaggio idempotenza
- [ ] Re-import con `force=True` → batch precedente in `replaced`, nuovo batch `completed`

---

## STEP 6 — Routes API

### 6.1 `backend/app/modules/catasto/routes/import_routes.py`

```python
from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
# imports progetto...

router = APIRouter(prefix="/catasto/import", tags=["catasto-import"])

@router.post("/capacitas", status_code=202)
async def upload_capacitas(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),   # solo admin
):
    """Avvia import Capacitas in background. Ritorna batch_id subito."""
    file_bytes = await file.read()
    # Crea batch placeholder prima di passare al background
    batch_id = str(uuid4())
    background_tasks.add_task(_run_import, db_factory(), file_bytes, file.filename, current_user.id, force, batch_id)
    return {"batch_id": batch_id, "status": "processing"}

@router.get("/{batch_id}/status")
async def get_import_status(batch_id: str, db: AsyncSession = Depends(get_db)):
    batch = await db.get(CatImportBatch, batch_id)
    if not batch:
        raise HTTPException(404)
    return batch

@router.get("/{batch_id}/report")
async def get_import_report(
    batch_id: str,
    tipo: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Lista anomalie del batch, con filtro per tipo, paginata."""
    ...

@router.get("/history")
async def get_import_history(db: AsyncSession = Depends(get_db)):
    ...
```

### 6.2 `backend/app/modules/catasto/routes/distretti.py`

```python
router = APIRouter(prefix="/catasto/distretti", tags=["catasto-distretti"])

@router.get("/")         # Lista con KPI base per anno
@router.get("/{id}")     # Dettaglio
@router.get("/{id}/kpi") # KPI aggregati query param: anno=int

@router.get("/{id}/geojson")
async def get_distretto_geojson(id: str, db: AsyncSession = Depends(get_db)):
    from geoalchemy2.shape import to_shape
    from shapely.geometry import mapping
    import json
    distretto = await db.get(CatDistretto, id)
    if not distretto or distretto.geometry is None:
        raise HTTPException(404, "Distretto o geometria non trovata")
    geom = to_shape(distretto.geometry)
    return {"type": "Feature", "geometry": mapping(geom), "properties": {"num_distretto": distretto.num_distretto}}
```

### 6.3 `backend/app/modules/catasto/routes/particelle.py`

```python
router = APIRouter(prefix="/catasto/particelle", tags=["catasto-particelle"])

@router.get("/")          # Lista paginata: filtri distretto, comune, anno, ha_anomalie, cf
@router.get("/{id}")      # Dettaglio
@router.get("/{id}/utenze")   # Ruoli tributo per anno
@router.get("/{id}/anomalie") # Anomalie della particella
@router.get("/{id}/geojson")  # GeoJSON geometria
```

### 6.4 `backend/app/modules/catasto/routes/anomalie.py`

```python
router = APIRouter(prefix="/catasto/anomalie", tags=["catasto-anomalie"])

@router.get("/")       # Lista filtrata: tipo, severita, anno, distretto, status
@router.patch("/{id}") # Update: status, note_operatore, assigned_to
```

### 6.5 Registrazione router

Nel file del progetto dove vengono registrati i router del modulo catasto, aggiungi:
```python
from backend.app.modules.catasto.routes.import_routes import router as catasto_import_router
from backend.app.modules.catasto.routes.distretti import router as catasto_distretti_router
from backend.app.modules.catasto.routes.particelle import router as catasto_particelle_router
from backend.app.modules.catasto.routes.anomalie import router as catasto_anomalie_router

app.include_router(catasto_import_router)
app.include_router(catasto_distretti_router)
app.include_router(catasto_particelle_router)
app.include_router(catasto_anomalie_router)
```

### Acceptance Step 6
- [ ] `GET /catasto/distretti` → 200
- [ ] `GET /catasto/anomalie?tipo=VAL-02-cf_invalido` → 200 con lista filtrata
- [ ] `POST /catasto/import/capacitas` con file test → 202 con `batch_id`
- [ ] `GET /catasto/import/{batch_id}/status` → 200 con status aggiornato
- [ ] `POST /catasto/import/capacitas` senza JWT → 401

---

## STEP 7 — Script import shapefile

**File**: `scripts/import_shapefile_catasto.sh`

```bash
#!/bin/bash
set -e
SHAPEFILE="${1:?Usage: $0 <path/to/shapefile.shp>}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_DB="${POSTGRES_DB:-gaia}"
POSTGRES_USER="${POSTGRES_USER:-gaia}"
GAIA_API="${GAIA_API:-http://localhost:8000}"

PG_CONN="PG:host=$POSTGRES_HOST dbname=$POSTGRES_DB user=$POSTGRES_USER password=$POSTGRES_PASSWORD"

echo "=== GAIA Catasto — Import Shapefile ==="
echo "File: $SHAPEFILE"
echo "Proiezione: EPSG:3003 → EPSG:4326"
echo ""

ogr2ogr \
  -f PostgreSQL "$PG_CONN" \
  "$SHAPEFILE" \
  -nln cat_particelle_staging \
  -nlt MULTIPOLYGON \
  -s_srs EPSG:3003 \
  -t_srs EPSG:4326 \
  -overwrite \
  -progress

echo ""
echo "Shapefile caricato in staging. Avvio finalize via API..."
curl -sf -X POST "$GAIA_API/catasto/import/shapefile/finalize" \
  -H "Authorization: Bearer $GAIA_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  | python3 -m json.tool

echo "=== Import completato ==="
```

Rendi eseguibile: `chmod +x scripts/import_shapefile_catasto.sh`

Crea anche l'endpoint `POST /catasto/import/shapefile/finalize` in `import_routes.py` che:
1. Conta righe in `cat_particelle_staging`
2. Esegue upsert SCD Type 2 verso `cat_particelle`
3. Deriva e upserta `cat_distretti` via `ST_Union` per `NUM_DIST`
4. Crea `CatImportBatch` con tipo `shapefile`
5. Ritorna report con conteggi

---

## STEP 8 — Frontend: tipi, API client, componenti base

**File**: `frontend/src/types/catasto.ts`

Crea i tipi TypeScript (vedi `domain-docs/catasto/docs/GAIA_CATASTO_FRONTEND_CODEX_v1.md` Step F1).

**File**: `frontend/src/lib/api/catasto.ts`

Crea il client API usando la stessa factory/fetch wrapper già usata nel progetto (controlla `frontend/src/lib/api/` per il pattern esistente).

**Componenti** in `frontend/src/components/catasto/`:
- `AnomaliaStatusBadge.tsx` — badge severità colorato (error=rosso, warning=giallo, info=blu)
- `AnomaliaStatusPill.tsx` — pill status workflow
- `CfBadge.tsx` — CF con indicatore validità verde/rosso
- `KpiCard.tsx` — card KPI riutilizzabile
- `ImportStatusBadge.tsx` — badge status batch import

---

## STEP 9 — Frontend: pagine

Implementa nell'ordine, ogni pagina deve avere skeleton loading e gestione errori.

### 9.1 Layout `frontend/src/app/catasto/layout.tsx`
Sidebar/breadcrumb con link: Dashboard | Distretti | Particelle | Anomalie | Import
Aggiungi voce "Catasto" al menu principale di navigazione.

### 9.2 Dashboard `frontend/src/app/catasto/page.tsx`
- KPI strip (particelle totali, distretti attivi, anomalie error aperte, data ultimo import)
- Selector anno campagna (default anno corrente)
- Grid di cards distretto con KPI e badge anomalie
- Link rapido a Import e Anomalie

### 9.3 Wizard Import `frontend/src/app/catasto/import/page.tsx`
3 step: Upload → Progress (polling ogni 2s) → Report anomalie.
Il report deve mostrare i contatori per tipo con filtro e tabella prime 50 righe di preview.

### 9.4 Lista Distretti `frontend/src/app/catasto/distretti/page.tsx`
Tabella con TanStack Table: N.Distretto, Nome, Sup.Irrigabile (ha), Importo tot 0648, Importo tot 0985, N.Anomalie.

### 9.5 Dettaglio Distretto `frontend/src/app/catasto/distretti/[id]/page.tsx`
KPI header + tabs: Particelle | Anomalie. Tab Particelle ha filtri inline.

### 9.6 Scheda Particella `frontend/src/app/catasto/particelle/[id]/page.tsx`
Dati catastali + storico ruoli tributo per anno + lista anomalie con azioni.

### 9.7 Lista Anomalie `frontend/src/app/catasto/anomalie/page.tsx`
Tabella TanStack con filtri, selezione bulk, azioni (chiudi/ignora/assegna).

### Acceptance Step 9
- [ ] Tutte le pagine senza errori di compilazione TypeScript
- [ ] Import wizard completa end-to-end con file test
- [ ] Superfici visualizzate in ettari (m² / 10.000, 2 decimali)
- [ ] Importi in € formato italiano (`Intl.NumberFormat('it-IT', ...)`)
- [ ] Zero `any` nel codice TypeScript

---

## Regole globali per tutto l'implementation

1. **Non toccare** route, modelli e service già esistenti nel modulo `catasto` (SISTER, elaborazioni, inVOLTURE)
2. **Non bloccare** l'import su un'anomalia singola — ogni riga viene salvata comunque con i flag anomalia
3. **Tutti i timestamp** in `TIMESTAMPTZ` / `datetime.now(timezone.utc)`
4. **Tutte le PK** UUID
5. **CF sempre MAIUSCOLO** nel campo `codice_fiscale`, raw nel campo `codice_fiscale_raw`
6. **EPSG:3003 → 4326** in ogr2ogr (shapefile Monte Mario / Italy zone 1)
7. **0985** è dato autoritativo Capacitas: non ricalcolabile, non segnalare anomalia sul valore assoluto
8. **CCO** è identificativo opaco Capacitas: salvarlo ma non usarlo come FK verso consorziati
9. Segui i pattern SQLAlchemy async già presenti nel progetto (`AsyncSession`, `Depends(get_db)`)
10. Segui i pattern auth già presenti (JWT, `require_admin`, `require_authenticated`)
