from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.core.database import Base

try:
    from geoalchemy2 import Geometry  # type: ignore
except Exception:  # pragma: no cover
    Geometry = None  # type: ignore[misc,assignment]


class GeometryCompat(TypeDecorator):
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and Geometry is not None:
            return dialect.type_descriptor(Geometry("MULTIPOLYGON", srid=4326))
        return dialect.type_descriptor(Text())


MULTIPOLYGON_4326 = GeometryCompat()


class CatImportBatch(Base):
    __tablename__ = "cat_import_batches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    anno_campagna: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    hash_file: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    righe_totali: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    righe_importate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    righe_anomalie: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="processing", nullable=False, index=True)
    report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    errore: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("application_users.id"), nullable=True)

    utenze: Mapped[list["CatUtenzaIrrigua"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class CatSchemaContributo(Base):
    __tablename__ = "cat_schemi_contributo"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    codice: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    descrizione: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tipo_calcolo: Mapped[str] = mapped_column(String(20), default="fisso", nullable=False)
    attivo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    aliquote: Mapped[list["CatAliquota"]] = relationship(back_populates="schema", cascade="all, delete-orphan")


class CatAliquota(Base):
    __tablename__ = "cat_aliquote"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    schema_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cat_schemi_contributo.id"), nullable=False, index=True)
    anno: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    aliquota: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    schema: Mapped["CatSchemaContributo"] = relationship(back_populates="aliquote")


class CatDistretto(Base):
    __tablename__ = "cat_distretti"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    num_distretto: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    nome_distretto: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decreto_istitutivo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    data_decreto: Mapped[date | None] = mapped_column(Date, nullable=True)
    geometry: Mapped[object | None] = mapped_column(MULTIPOLYGON_4326, nullable=True)
    attivo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    coefficienti: Mapped[list["CatDistrettoCoefficiente"]] = relationship(
        back_populates="distretto", cascade="all, delete-orphan"
    )
    geometry_versions: Mapped[list["CatDistrettoGeometryVersion"]] = relationship(
        back_populates="distretto", cascade="all, delete-orphan"
    )


class CatDistrettoGeometryVersion(Base):
    __tablename__ = "cat_distretti_geometry_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    distretto_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cat_distretti.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_import_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    num_distretto: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    nome_distretto: Mapped[str | None] = mapped_column(String(200), nullable=True)
    geometry: Mapped[object] = mapped_column(MULTIPOLYGON_4326, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    distretto: Mapped["CatDistretto"] = relationship(back_populates="geometry_versions")


class CatDistrettoCoefficiente(Base):
    __tablename__ = "cat_distretto_coefficienti"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    distretto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cat_distretti.id"), nullable=False, index=True)
    anno: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ind_spese_fisse: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    distretto: Mapped["CatDistretto"] = relationship(back_populates="coefficienti")


class CatComune(Base):
    __tablename__ = "cat_comuni"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nome_comune: Mapped[str] = mapped_column(String(100), nullable=False)
    codice_catastale: Mapped[str] = mapped_column(String(4), nullable=False, unique=True, index=True)
    cod_comune_capacitas: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    codice_comune_formato_numerico: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    codice_comune_numerico_2017_2025: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    nome_comune_legacy: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cod_provincia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sigla_provincia: Mapped[str | None] = mapped_column(String(2), nullable=True)
    regione: Mapped[str | None] = mapped_column(String(100), nullable=True)


class CatParticella(Base):
    __tablename__ = "cat_particelle"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    comune_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cat_comuni.id"), nullable=True, index=True)
    national_code: Mapped[str | None] = mapped_column(String(25), nullable=True)
    cod_comune_capacitas: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    codice_catastale: Mapped[str | None] = mapped_column(String(4), nullable=True, index=True)
    nome_comune: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sezione_catastale: Mapped[str | None] = mapped_column(String(10), nullable=True)
    foglio: Mapped[str] = mapped_column(String(10), nullable=False)
    particella: Mapped[str] = mapped_column(String(20), nullable=False)
    subalterno: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cfm: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    superficie_mq: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    superficie_grafica_mq: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    num_distretto: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    nome_distretto: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geometry: Mapped[object | None] = mapped_column(MULTIPOLYGON_4326, nullable=True)
    source_type: Mapped[str] = mapped_column(String(20), default="shapefile", nullable=False)
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    capacitas_last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    capacitas_last_sync_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    capacitas_last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    capacitas_last_sync_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    capacitas_anomaly_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    capacitas_anomaly_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    utenze: Mapped[list["CatUtenzaIrrigua"]] = relationship(back_populates="particella_record")
    anomalie: Mapped[list["CatAnomalia"]] = relationship(back_populates="particella")
    consorzio_units: Mapped[list["CatConsorzioUnit"]] = relationship(back_populates="particella_record")
    comune: Mapped["CatComune | None"] = relationship(foreign_keys=[comune_id])
    gis_saved_selection_items: Mapped[list["CatGisSavedSelectionItem"]] = relationship(
        back_populates="particella_record"
    )

    @property
    def fuori_distretto(self) -> bool:
        return self.num_distretto == "FD"


class CatGisSavedSelection(Base):
    __tablename__ = "cat_gis_saved_selections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    color: Mapped[str] = mapped_column(String(16), default="#10B981", nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    n_particelle: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    n_with_geometry: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    import_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    items: Mapped[list["CatGisSavedSelectionItem"]] = relationship(
        back_populates="selection",
        cascade="all, delete-orphan",
        order_by="CatGisSavedSelectionItem.position",
    )


class CatGisSavedSelectionItem(Base):
    __tablename__ = "cat_gis_saved_selection_items"
    __table_args__ = (
        UniqueConstraint("selection_id", "particella_id", name="uq_cat_gis_saved_selection_particella"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    selection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cat_gis_saved_selections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    particella_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cat_particelle.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_ref: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    selection: Mapped["CatGisSavedSelection"] = relationship(back_populates="items")
    particella_record: Mapped["CatParticella"] = relationship(back_populates="gis_saved_selection_items")


class CatParticellaHistory(Base):
    __tablename__ = "cat_particelle_history"

    history_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    particella_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    comune_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cat_comuni.id"), nullable=True, index=True)
    national_code: Mapped[str | None] = mapped_column(String(25), nullable=True)
    cod_comune_capacitas: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    codice_catastale: Mapped[str | None] = mapped_column(String(4), nullable=True, index=True)
    foglio: Mapped[str] = mapped_column(String(10), nullable=False)
    particella: Mapped[str] = mapped_column(String(20), nullable=False)
    subalterno: Mapped[str | None] = mapped_column(String(10), nullable=True)
    superficie_mq: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    superficie_grafica_mq: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    num_distretto: Mapped[str | None] = mapped_column(String(10), nullable=True)
    geometry: Mapped[object | None] = mapped_column(MULTIPOLYGON_4326, nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)

class CatUtenzaIrrigua(Base):
    __tablename__ = "cat_utenze_irrigue"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cat_import_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    anno_campagna: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cco: Mapped[str | None] = mapped_column(String(20), nullable=True)
    comune_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cat_comuni.id"), nullable=True, index=True)
    cod_provincia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cod_comune_capacitas: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    cod_frazione: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_distretto: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    nome_distretto_loc: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nome_comune: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sezione_catastale: Mapped[str | None] = mapped_column(String(10), nullable=True)
    foglio: Mapped[str | None] = mapped_column(String(10), nullable=True)
    particella: Mapped[str | None] = mapped_column(String(20), nullable=True)
    subalterno: Mapped[str | None] = mapped_column(String(10), nullable=True)
    particella_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cat_particelle.id"), nullable=True, index=True)
    sup_catastale_mq: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    sup_irrigabile_mq: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    ind_spese_fisse: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    imponibile_sf: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    esente_0648: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    aliquota_0648: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    importo_0648: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    aliquota_0985: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    importo_0985: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    denominazione: Mapped[str | None] = mapped_column(String(500), nullable=True)
    codice_fiscale: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    codice_fiscale_raw: Mapped[str | None] = mapped_column(String(16), nullable=True)
    anomalia_superficie: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anomalia_cf_invalido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anomalia_cf_mancante: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anomalia_comune_invalido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anomalia_particella_assente: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anomalia_imponibile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anomalia_importi: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    batch: Mapped["CatImportBatch"] = relationship(back_populates="utenze")
    # Keep the textual cadastral identifier on `particella`; use a distinct ORM
    # relationship name to avoid shadowing the column attribute.
    particella_record: Mapped["CatParticella | None"] = relationship(back_populates="utenze")
    anomalie: Mapped[list["CatAnomalia"]] = relationship(back_populates="utenza")
    occupancies: Mapped[list["CatConsorzioOccupancy"]] = relationship(back_populates="utenza_record")
    intestatari_annuali: Mapped[list["CatUtenzaIntestatario"]] = relationship(back_populates="utenza_record")
    comune: Mapped["CatComune | None"] = relationship(foreign_keys=[comune_id])

    @property
    def ha_anomalie(self) -> bool:
        return any(
            [
                self.anomalia_superficie,
                self.anomalia_cf_invalido,
                self.anomalia_cf_mancante,
                self.anomalia_comune_invalido,
                self.anomalia_particella_assente,
                self.anomalia_imponibile,
                self.anomalia_importi,
            ]
        )

class CatIntestatario(Base):
    __tablename__ = "cat_intestatari"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    codice_fiscale: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    denominazione: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(5), nullable=True)
    cognome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_nascita: Mapped[date | None] = mapped_column(Date, nullable=True)
    luogo_nascita: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ragione_sociale: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deceduto: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    dati_sister_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CatConsorzioUnit(Base):
    __tablename__ = "cat_consorzio_units"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    particella_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_particelle.id", ondelete="SET NULL"), nullable=True, index=True
    )
    comune_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_comuni.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cod_comune_capacitas: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_comune_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_comuni.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_cod_comune_capacitas: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_codice_catastale: Mapped[str | None] = mapped_column(String(4), nullable=True, index=True)
    source_comune_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    comune_resolution_mode: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    sezione_catastale: Mapped[str | None] = mapped_column(String(10), nullable=True)
    foglio: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    particella: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    subalterno: Mapped[str | None] = mapped_column(String(10), nullable=True)
    descrizione: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_first_seen: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_last_seen: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    particella_record: Mapped["CatParticella | None"] = relationship(back_populates="consorzio_units")
    comune: Mapped["CatComune | None"] = relationship(foreign_keys=[comune_id])
    source_comune: Mapped["CatComune | None"] = relationship(foreign_keys=[source_comune_id])
    segments: Mapped[list["CatConsorzioUnitSegment"]] = relationship(
        back_populates="unit", cascade="all, delete-orphan"
    )
    occupancies: Mapped[list["CatConsorzioOccupancy"]] = relationship(
        back_populates="unit", cascade="all, delete-orphan"
    )
    terreno_rows: Mapped[list["CatCapacitasTerrenoRow"]] = relationship(back_populates="unit")


class CatConsorzioUnitSegment(Base):
    __tablename__ = "cat_consorzio_unit_segments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cat_consorzio_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    segment_type: Mapped[str] = mapped_column(String(40), default="full", nullable=False, index=True)
    surface_declared_mq: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    surface_irrigable_mq: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    riordino_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    riordino_maglia: Mapped[str | None] = mapped_column(String(20), nullable=True)
    riordino_lotto: Mapped[str | None] = mapped_column(String(20), nullable=True)
    current_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    unit: Mapped["CatConsorzioUnit"] = relationship(back_populates="segments")
    occupancies: Mapped[list["CatConsorzioOccupancy"]] = relationship(back_populates="segment")


class CatConsorzioOccupancy(Base):
    __tablename__ = "cat_consorzio_occupancies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cat_consorzio_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_consorzio_unit_segments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    utenza_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_utenze_irrigue.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cco: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    fra: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ccs: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pvc: Mapped[str | None] = mapped_column(String(10), nullable=True)
    com: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source_type: Mapped[str] = mapped_column(String(40), default="ruolo_0648_0985", nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(40), default="utilizzatore_reale", nullable=False, index=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    unit: Mapped["CatConsorzioUnit"] = relationship(back_populates="occupancies")
    segment: Mapped["CatConsorzioUnitSegment | None"] = relationship(back_populates="occupancies")
    utenza_record: Mapped["CatUtenzaIrrigua | None"] = relationship(back_populates="occupancies")


class CatCapacitasTerrenoRow(Base):
    __tablename__ = "cat_capacitas_terreni_rows"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_consorzio_units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    search_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    external_row_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    cco: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    fra: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ccs: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pvc: Mapped[str | None] = mapped_column(String(10), nullable=True)
    com: Mapped[str | None] = mapped_column(String(10), nullable=True)
    belfiore: Mapped[str | None] = mapped_column(String(10), nullable=True)
    foglio: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    particella: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    sub: Mapped[str | None] = mapped_column(String(10), nullable=True)
    anno: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    voltura: Mapped[str | None] = mapped_column(String(20), nullable=True)
    opcode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    data_reg: Mapped[str | None] = mapped_column(String(20), nullable=True)
    superficie_mq: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    bac_descr: Mapped[str | None] = mapped_column(String(255), nullable=True)
    row_visual_state: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    raw_payload_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    unit: Mapped["CatConsorzioUnit | None"] = relationship(back_populates="terreno_rows")
    detail_snapshots: Mapped[list["CatCapacitasTerrenoDetail"]] = relationship(back_populates="terreno_row")


class CatCapacitasCertificato(Base):
    __tablename__ = "cat_capacitas_certificati"
    __table_args__ = (
        UniqueConstraint("cco", "fra", "ccs", "pvc", "com", "collected_at", name="uq_cat_cap_cert_snapshot"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cco: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    fra: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ccs: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pvc: Mapped[str | None] = mapped_column(String(10), nullable=True)
    com: Mapped[str | None] = mapped_column(String(10), nullable=True)
    partita_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    utenza_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    utenza_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ruolo_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    intestatari_snapshots: Mapped[list["CatCapacitasIntestatario"]] = relationship(
        back_populates="certificato", cascade="all, delete-orphan"
    )


class CatCapacitasIntestatario(Base):
    __tablename__ = "cat_capacitas_intestatari"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    certificato_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cat_capacitas_certificati.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    idxana: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    idxesa: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    codice_fiscale: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    denominazione: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_nascita: Mapped[date | None] = mapped_column(Date, nullable=True)
    luogo_nascita: Mapped[str | None] = mapped_column(String(255), nullable=True)
    residenza: Mapped[str | None] = mapped_column(String(500), nullable=True)
    comune_residenza: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    cap: Mapped[str | None] = mapped_column(String(16), nullable=True)
    titoli: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deceduto: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_payload_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    certificato: Mapped["CatCapacitasCertificato"] = relationship(back_populates="intestatari_snapshots")


class CatUtenzaIntestatario(Base):
    __tablename__ = "cat_utenza_intestatari"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    utenza_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cat_utenze_irrigue.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    idxana: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    idxesa: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    history_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    anno_riferimento: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    data_agg: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    at: Mapped[str | None] = mapped_column(String(10), nullable=True)
    site: Mapped[str | None] = mapped_column(String(20), nullable=True)
    voltura: Mapped[str | None] = mapped_column(String(20), nullable=True)
    op: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    codice_fiscale: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    partita_iva: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    denominazione: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_nascita: Mapped[date | None] = mapped_column(Date, nullable=True)
    luogo_nascita: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sesso: Mapped[str | None] = mapped_column(String(4), nullable=True)
    residenza: Mapped[str | None] = mapped_column(String(500), nullable=True)
    comune_residenza: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cap: Mapped[str | None] = mapped_column(String(16), nullable=True)
    titoli: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deceduto: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    raw_payload_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    utenza_record: Mapped["CatUtenzaIrrigua"] = relationship(back_populates="intestatari_annuali")


class CatCapacitasTerrenoDetail(Base):
    __tablename__ = "cat_capacitas_terreno_details"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    terreno_row_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_capacitas_terreni_rows.id", ondelete="SET NULL"), nullable=True, index=True
    )
    external_row_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    foglio: Mapped[str | None] = mapped_column(String(10), nullable=True)
    particella: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sub: Mapped[str | None] = mapped_column(String(10), nullable=True)
    riordino_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    riordino_maglia: Mapped[str | None] = mapped_column(String(20), nullable=True)
    riordino_lotto: Mapped[str | None] = mapped_column(String(20), nullable=True)
    irridist: Mapped[str | None] = mapped_column(String(20), nullable=True)
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    terreno_row: Mapped["CatCapacitasTerrenoRow | None"] = relationship(back_populates="detail_snapshots")


class CatAnomalia(Base):
    __tablename__ = "cat_anomalie"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    particella_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cat_particelle.id"), nullable=True, index=True)
    utenza_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cat_utenze_irrigue.id"), nullable=True, index=True)
    anno_campagna: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severita: Mapped[str] = mapped_column(String(10), nullable=False)
    descrizione: Mapped[str | None] = mapped_column(Text, nullable=True)
    dati_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(25), default="aperta", nullable=False, index=True)
    note_operatore: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("application_users.id"), nullable=True)
    segnalazione_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    particella: Mapped["CatParticella | None"] = relationship(back_populates="anomalie")
    utenza: Mapped["CatUtenzaIrrigua | None"] = relationship(back_populates="anomalie")


__all__ = [
    "CatAliquota",
    "CatAnomalia",
    "CatCapacitasCertificato",
    "CatCapacitasIntestatario",
    "CatCapacitasTerrenoDetail",
    "CatCapacitasTerrenoRow",
    "CatDistretto",
    "CatDistrettoGeometryVersion",
    "CatDistrettoCoefficiente",
    "CatGisSavedSelection",
    "CatGisSavedSelectionItem",
    "CatConsorzioOccupancy",
    "CatConsorzioUnit",
    "CatConsorzioUnitSegment",
    "CatImportBatch",
    "CatIntestatario",
    "CatParticella",
    "CatParticellaHistory",
    "CatSchemaContributo",
    "CatUtenzaIntestatario",
    "CatUtenzaIrrigua",
]
