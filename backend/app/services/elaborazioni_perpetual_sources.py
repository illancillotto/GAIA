from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoPerpetualSyncScope
from app.models.catasto_phase1 import CatParticella
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject
from app.services.catasto_comuni import get_catasto_comuni_lookup
from app.services.elaborazioni_batches import infer_subject_kind, normalize_lookup_value


@dataclass(frozen=True, slots=True)
class PerpetualSourceTarget:
    scope: str
    target_key: str
    priority: int
    search_mode: str
    source_updated_at: datetime | None
    ruolo_particella_id: UUID | None = None
    cat_particella_id: UUID | None = None
    subject_id: UUID | None = None
    comune: str | None = None
    comune_codice: str | None = None
    catasto: str | None = None
    sezione: str | None = None
    foglio: str | None = None
    particella: str | None = None
    subalterno: str | None = None
    subject_kind: str | None = None
    subject_identifier: str | None = None
    intestazione: str | None = None
    tipo_visura: str = "Sintetica"
    request_type: str = "ATTUALITA"


def _clean(value: object | None) -> str | None:
    cleaned = str(value).strip() if value is not None else ""
    return cleaned or None


def _parcel_key(comune: str | None, foglio: object, particella: object, subalterno: object) -> str:
    return "|".join(
        (
            normalize_lookup_value(comune or ""),
            _clean(foglio) or "",
            _clean(particella) or "",
            _clean(subalterno) or "",
        )
    )


def _latest_completed_import_id():
    return (
        select(RuoloImportJob.id)
        .where(RuoloImportJob.status == "completed")
        .order_by(
            RuoloImportJob.anno_tributario.desc(),
            RuoloImportJob.created_at.desc(),
            RuoloImportJob.id.desc(),
        )
        .limit(1)
        .scalar_subquery()
    )


def iter_ruolo_parcel_targets(db: Session) -> Iterator[PerpetualSourceTarget]:
    lookup = get_catasto_comuni_lookup(db)
    rows = db.execute(
        select(RuoloParticella, RuoloPartita.comune_nome)
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .join(RuoloAvviso, RuoloAvviso.id == RuoloPartita.avviso_id)
        .where(RuoloAvviso.import_job_id == _latest_completed_import_id())
        .order_by(RuoloParticella.anno_tributario.desc(), RuoloParticella.created_at.desc())
    ).yield_per(1_000)
    seen: set[str] = set()
    for parcel, comune_nome in rows:
        key = _parcel_key(comune_nome, parcel.foglio, parcel.particella, parcel.subalterno)
        if key in seen:
            continue
        seen.add(key)
        comune = lookup.get(normalize_lookup_value(comune_nome))
        yield PerpetualSourceTarget(
            scope=CatastoPerpetualSyncScope.RUOLO_PARTICELLA.value,
            target_key=key,
            priority=10,
            search_mode="immobile",
            source_updated_at=parcel.created_at,
            ruolo_particella_id=parcel.id,
            cat_particella_id=parcel.cat_particella_id,
            comune=comune.nome if comune else _clean(comune_nome),
            comune_codice=comune.codice_sister if comune else None,
            catasto="Terreni",
            foglio=_clean(parcel.foglio),
            particella=_clean(parcel.particella),
            subalterno=_clean(parcel.subalterno),
            request_type="STORICA",
        )


def load_ruolo_parcel_targets(db: Session) -> list[PerpetualSourceTarget]:
    return list(iter_ruolo_parcel_targets(db))


def _subject_target(
    *,
    scope: str,
    priority: int,
    subject_id: UUID | None,
    identifier: str | None,
    name: str | None,
    updated_at: datetime | None,
) -> PerpetualSourceTarget | None:
    normalized = (_clean(identifier) or "").upper()
    if not normalized:
        return None
    return PerpetualSourceTarget(
        scope=scope,
        target_key=normalized,
        priority=priority,
        search_mode="soggetto",
        source_updated_at=updated_at,
        subject_id=subject_id,
        subject_kind=infer_subject_kind(normalized),
        subject_identifier=normalized,
        intestazione=_clean(name),
        request_type="ATTUALITA",
    )


def iter_ruolo_subject_targets(db: Session) -> Iterator[PerpetualSourceTarget]:
    rows = db.execute(
        select(
            RuoloAvviso.subject_id,
            RuoloAvviso.codice_fiscale_raw,
            RuoloAvviso.nominativo_raw,
            RuoloAvviso.updated_at,
            AnagraficaPerson.codice_fiscale,
            AnagraficaCompany.codice_fiscale,
            AnagraficaCompany.partita_iva,
        )
        .outerjoin(AnagraficaPerson, AnagraficaPerson.subject_id == RuoloAvviso.subject_id)
        .outerjoin(AnagraficaCompany, AnagraficaCompany.subject_id == RuoloAvviso.subject_id)
        .where(RuoloAvviso.import_job_id == _latest_completed_import_id())
        .order_by(RuoloAvviso.anno_tributario.desc(), RuoloAvviso.updated_at.desc())
    ).yield_per(1_000)
    seen: set[str] = set()
    for subject_id, raw_cf, name, updated_at, person_cf, company_cf, vat in rows:
        target = _subject_target(
            scope=CatastoPerpetualSyncScope.RUOLO_SOGGETTO.value,
            priority=20,
            subject_id=subject_id,
            identifier=person_cf or company_cf or vat or raw_cf,
            name=name,
            updated_at=updated_at,
        )
        if target is not None and target.target_key not in seen:
            seen.add(target.target_key)
            yield target


def load_ruolo_subject_targets(db: Session) -> list[PerpetualSourceTarget]:
    return list(iter_ruolo_subject_targets(db))


def iter_consortium_parcel_targets(db: Session) -> Iterator[PerpetualSourceTarget]:
    lookup = get_catasto_comuni_lookup(db)
    parcels = db.scalars(
        select(CatParticella)
        .where(CatParticella.is_current.is_(True), CatParticella.suppressed.is_(False))
        .order_by(CatParticella.updated_at.desc())
    ).yield_per(1_000)
    for parcel in parcels:
        comune = lookup.get(normalize_lookup_value(parcel.nome_comune or ""))
        yield PerpetualSourceTarget(
            scope=CatastoPerpetualSyncScope.CONSORZIO_PARTICELLA.value,
            target_key=str(parcel.id),
            priority=30,
            search_mode="immobile",
            source_updated_at=parcel.updated_at,
            cat_particella_id=parcel.id,
            comune=comune.nome if comune else _clean(parcel.nome_comune),
            comune_codice=comune.codice_sister if comune else None,
            catasto="Terreni",
            sezione=_clean(parcel.sezione_catastale),
            foglio=_clean(parcel.foglio),
            particella=_clean(parcel.particella),
            subalterno=_clean(parcel.subalterno),
            request_type="STORICA",
        )


def load_consortium_parcel_targets(db: Session) -> list[PerpetualSourceTarget]:
    return list(iter_consortium_parcel_targets(db))


def iter_registry_subject_targets(db: Session) -> Iterator[PerpetualSourceTarget]:
    rows = db.execute(
        select(
            AnagraficaSubject,
            AnagraficaPerson.codice_fiscale,
            AnagraficaCompany.codice_fiscale,
            AnagraficaCompany.partita_iva,
        )
        .outerjoin(AnagraficaPerson, AnagraficaPerson.subject_id == AnagraficaSubject.id)
        .outerjoin(AnagraficaCompany, AnagraficaCompany.subject_id == AnagraficaSubject.id)
        .order_by(AnagraficaSubject.updated_at.desc())
    ).yield_per(1_000)
    for subject, person_cf, company_cf, vat in rows:
        target = _subject_target(
            scope=CatastoPerpetualSyncScope.ANAGRAFE_SOGGETTO.value,
            priority=40,
            subject_id=subject.id,
            identifier=person_cf or company_cf or vat,
            name=subject.source_name_raw,
            updated_at=subject.updated_at,
        )
        if target is not None:
            yield target


def load_registry_subject_targets(db: Session) -> list[PerpetualSourceTarget]:
    return list(iter_registry_subject_targets(db))


def iter_enabled_targets(
    db: Session, *, primary: bool, secondary: bool
) -> Iterator[PerpetualSourceTarget]:
    if primary:
        yield from iter_ruolo_parcel_targets(db)
        yield from iter_ruolo_subject_targets(db)
    if secondary:
        yield from iter_consortium_parcel_targets(db)
        yield from iter_registry_subject_targets(db)


def load_enabled_targets(db: Session, *, primary: bool, secondary: bool) -> list[PerpetualSourceTarget]:
    return list(iter_enabled_targets(db, primary=primary, secondary=secondary))
