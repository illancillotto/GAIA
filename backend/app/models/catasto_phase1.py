from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, Uuid, func
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


class CatDistrettoCoefficiente(Base):
    __tablename__ = "cat_distretto_coefficienti"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    distretto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cat_distretti.id"), nullable=False, index=True)
    anno: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ind_spese_fisse: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    distretto: Mapped["CatDistretto"] = relationship(back_populates="coefficienti")


class CatParticella(Base):
    __tablename__ = "cat_particelle"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    national_code: Mapped[str | None] = mapped_column(String(25), nullable=True)
    cod_comune_istat: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    nome_comune: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sezione_catastale: Mapped[str | None] = mapped_column(String(10), nullable=True)
    foglio: Mapped[str] = mapped_column(String(10), nullable=False)
    particella: Mapped[str] = mapped_column(String(20), nullable=False)
    subalterno: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cfm: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    superficie_mq: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    num_distretto: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    nome_distretto: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geometry: Mapped[object | None] = mapped_column(MULTIPOLYGON_4326, nullable=True)
    source_type: Mapped[str] = mapped_column(String(20), default="shapefile", nullable=False)
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    utenze: Mapped[list["CatUtenzaIrrigua"]] = relationship(back_populates="particella")
    anomalie: Mapped[list["CatAnomalia"]] = relationship(back_populates="particella")

    @property
    def fuori_distretto(self) -> bool:
        return self.num_distretto == "FD"


class CatParticellaHistory(Base):
    __tablename__ = "cat_particelle_history"

    history_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    particella_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    national_code: Mapped[str | None] = mapped_column(String(25), nullable=True)
    cod_comune_istat: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    foglio: Mapped[str] = mapped_column(String(10), nullable=False)
    particella: Mapped[str] = mapped_column(String(20), nullable=False)
    subalterno: Mapped[str | None] = mapped_column(String(10), nullable=True)
    superficie_mq: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
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
    cod_provincia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cod_comune_istat: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
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
    particella: Mapped["CatParticella | None"] = relationship(back_populates="utenze")
    anomalie: Mapped[list["CatAnomalia"]] = relationship(back_populates="utenza")

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
    "CatDistretto",
    "CatDistrettoCoefficiente",
    "CatImportBatch",
    "CatIntestatario",
    "CatParticella",
    "CatParticellaHistory",
    "CatSchemaContributo",
    "CatUtenzaIrrigua",
]
