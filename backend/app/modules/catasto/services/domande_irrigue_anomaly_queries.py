"""Lightweight read projections for the cross-application irrigation checks.

The checks only read these fields. Loading mapped entities also materializes
retained source JSON, geometries and ORM state for hundreds of thousands of
records. Bundles retain attribute access without those allocations.
"""

from sqlalchemy import select
from sqlalchemy.orm import Bundle, Session

from app.models.catasto_phase1 import CatParticella
from app.modules.catasto.models.domande_irrigue import (
    CatDomandaIrrigua,
    CatDomandaIrriguaParticella,
)


def anomaly_scan_queries(anno: int):
    domanda = Bundle(
        "domanda",
        CatDomandaIrrigua.id,
        CatDomandaIrrigua.anno,
        CatDomandaIrrigua.stato,
        CatDomandaIrrigua.autorinnovo,
        CatDomandaIrrigua.data_ins,
        CatDomandaIrrigua.utenza_id,
        CatDomandaIrrigua.domanda_numero,
        CatDomandaIrrigua.external_id,
        CatDomandaIrrigua.cco,
        CatDomandaIrrigua.com,
        CatDomandaIrrigua.fra,
        CatDomandaIrrigua.ccs,
    )
    detail = Bundle(
        "detail",
        CatDomandaIrriguaParticella.id,
        CatDomandaIrriguaParticella.domanda_id,
        CatDomandaIrriguaParticella.particella_id,
        CatDomandaIrriguaParticella.utenza_id,
        CatDomandaIrriguaParticella.part_com,
        CatDomandaIrriguaParticella.foglio,
        CatDomandaIrriguaParticella.particella,
        CatDomandaIrriguaParticella.sub,
        CatDomandaIrriguaParticella.coltura,
        CatDomandaIrriguaParticella.sup_cat_mq,
        CatDomandaIrriguaParticella.sup_irr_mq,
    )
    parcel = Bundle("particella", CatParticella.superficie_mq)
    domande = select(domanda).where(CatDomandaIrrigua.anno == anno)
    details = (
        select(detail, domanda, parcel)
        .join(CatDomandaIrrigua, CatDomandaIrriguaParticella.domanda_id == CatDomandaIrrigua.id)
        .outerjoin(CatParticella, CatDomandaIrriguaParticella.particella_id == CatParticella.id)
        .where(CatDomandaIrrigua.anno == anno)
    )
    return domande, details


def iter_anomaly_scan_data(db: Session, anno: int | None):
    """Surface groups are year-scoped; release each year's data before continuing."""
    years = (
        [anno] if anno is not None else db.scalars(select(CatDomandaIrrigua.anno).distinct()).all()
    )
    for year in years:
        domande, details = anomaly_scan_queries(year)
        yield db.execute(domande).scalars().all(), db.execute(details).all()
