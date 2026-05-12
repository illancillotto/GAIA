from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import (
    CatAnomalia,
    CatDistretto,
    CatImportBatch,
    CatParticella,
    CatUtenzaIntestatario,
    CatUtenzaIrrigua,
)
from app.schemas.catasto_phase1 import (
    CatDashboardAnomaliaBucket,
    CatDashboardAnomalieSummary,
    CatDashboardDistrettoSummary,
    CatDashboardImportSummary,
    CatDashboardParticelleSummary,
    CatDashboardSummaryResponse,
    CatDashboardUtenzeSummary,
    CatImportBatchResponse,
)

router = APIRouter(prefix="/catasto/dashboard", tags=["catasto-dashboard"])


def _to_int(value: object) -> int:
    return int(value or 0)


def _to_float(value: object) -> float:
    return float(value or 0)


def _capacitas_distretto_num(num_distretto: str) -> int | None:
    special_codes = {
        "29a": 291,
        "29b": 292,
        "29c": 293,
    }
    normalized = num_distretto.strip()
    if normalized in special_codes:
        return special_codes[normalized]
    return int(normalized) if normalized.isdigit() else None


def _latest_imported_anno(db: Session) -> int | None:
    value = db.scalar(
        select(func.max(CatImportBatch.anno_campagna)).where(
            CatImportBatch.status == "completed",
            CatImportBatch.anno_campagna.is_not(None),
        )
    )
    return int(value) if value is not None else None


@router.get("/summary", response_model=CatDashboardSummaryResponse)
def get_dashboard_summary(
    anno: int | None = Query(None),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatDashboardSummaryResponse:
    effective_anno = anno if anno is not None else _latest_imported_anno(db)

    latest_import = db.scalars(select(CatImportBatch).order_by(desc(CatImportBatch.created_at)).limit(1)).first()
    latest_completed = db.scalars(
        select(CatImportBatch)
        .where(CatImportBatch.status == "completed")
        .order_by(desc(CatImportBatch.completed_at))
        .limit(1)
    ).first()
    import_counts = db.execute(
        select(
            func.coalesce(func.sum(case((CatImportBatch.status == "processing", 1), else_=0)), 0),
            func.coalesce(func.sum(case((CatImportBatch.status == "failed", 1), else_=0)), 0),
            func.coalesce(func.sum(case((CatImportBatch.status == "completed", 1), else_=0)), 0),
        )
    ).one()

    particelle_row = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(case((CatParticella.geometry.is_not(None), 1), else_=0)), 0),
            func.coalesce(func.sum(case((CatParticella.geometry.is_(None), 1), else_=0)), 0),
            func.coalesce(
                func.sum(
                    case(
                        (CatParticella.num_distretto.is_not(None) & (CatParticella.num_distretto != "FD"), 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(func.sum(case((CatParticella.num_distretto == "FD", 1), else_=0)), 0),
            func.coalesce(func.sum(case((CatParticella.num_distretto.is_(None), 1), else_=0)), 0),
            func.coalesce(func.sum(case((CatParticella.suppressed.is_(True), 1), else_=0)), 0),
        ).where(CatParticella.is_current.is_(True))
    ).one()

    utenze_filters = []
    if effective_anno is not None:
        utenze_filters.append(CatUtenzaIrrigua.anno_campagna == effective_anno)

    titolare_exists = (
        select(CatUtenzaIntestatario.id)
        .where(CatUtenzaIntestatario.utenza_id == CatUtenzaIrrigua.id)
        .limit(1)
        .exists()
    )
    utenze_row = db.execute(
        select(
            func.count(),
            func.count(func.distinct(CatUtenzaIrrigua.particella_id)),
            func.coalesce(func.sum(CatUtenzaIrrigua.sup_irrigabile_mq), 0),
            func.coalesce(func.sum(CatUtenzaIrrigua.importo_0648), 0),
            func.coalesce(func.sum(CatUtenzaIrrigua.importo_0985), 0),
            func.coalesce(func.sum(case((CatUtenzaIrrigua.anomalia_cf_mancante.is_(True), 1), else_=0)), 0),
            func.coalesce(func.sum(case((CatUtenzaIrrigua.anomalia_cf_invalido.is_(True), 1), else_=0)), 0),
            func.coalesce(
                func.sum(
                    case(
                        (
                            CatUtenzaIrrigua.anomalia_superficie.is_(True)
                            | CatUtenzaIrrigua.anomalia_cf_invalido.is_(True)
                            | CatUtenzaIrrigua.anomalia_cf_mancante.is_(True)
                            | CatUtenzaIrrigua.anomalia_comune_invalido.is_(True)
                            | CatUtenzaIrrigua.anomalia_particella_assente.is_(True)
                            | CatUtenzaIrrigua.anomalia_imponibile.is_(True)
                            | CatUtenzaIrrigua.anomalia_importi.is_(True),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(func.sum(case((~titolare_exists, 1), else_=0)), 0),
        ).where(*utenze_filters)
    ).one()

    anomalie_filters = [CatAnomalia.status == "aperta"]
    if effective_anno is not None:
        anomalie_filters.append(CatAnomalia.anno_campagna == effective_anno)
    anomalie_row = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(case((CatAnomalia.severita == "error", 1), else_=0)), 0),
            func.coalesce(func.sum(case((CatAnomalia.severita == "warning", 1), else_=0)), 0),
            func.coalesce(func.sum(case((CatAnomalia.severita == "info", 1), else_=0)), 0),
        ).where(*anomalie_filters)
    ).one()
    tipo_rows = db.execute(
        select(CatAnomalia.tipo, func.count())
        .where(*anomalie_filters)
        .group_by(CatAnomalia.tipo)
        .order_by(desc(func.count()))
        .limit(8)
    ).all()

    particelle_by_distretto = {
        str(num): _to_int(count)
        for num, count in db.execute(
            select(CatParticella.num_distretto, func.count())
            .where(CatParticella.is_current.is_(True), CatParticella.num_distretto.is_not(None))
            .group_by(CatParticella.num_distretto)
        ).all()
    }
    utenze_by_distretto = {
        int(num): (count, superficie, importo_0648, importo_0985)
        for num, count, superficie, importo_0648, importo_0985 in db.execute(
            select(
                CatUtenzaIrrigua.num_distretto,
                func.count(),
                func.coalesce(func.sum(CatUtenzaIrrigua.sup_irrigabile_mq), 0),
                func.coalesce(func.sum(CatUtenzaIrrigua.importo_0648), 0),
                func.coalesce(func.sum(CatUtenzaIrrigua.importo_0985), 0),
            )
            .where(CatUtenzaIrrigua.num_distretto.is_not(None), *utenze_filters)
            .group_by(CatUtenzaIrrigua.num_distretto)
        ).all()
    }
    anomalie_by_distretto = {
        int(num): (count, error)
        for num, count, error in db.execute(
            select(
                CatUtenzaIrrigua.num_distretto,
                func.count(CatAnomalia.id),
                func.coalesce(func.sum(case((CatAnomalia.severita == "error", 1), else_=0)), 0),
            )
            .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
            .where(CatUtenzaIrrigua.num_distretto.is_not(None), *utenze_filters, CatAnomalia.status == "aperta")
            .group_by(CatUtenzaIrrigua.num_distretto)
        ).all()
    }

    distretti: list[CatDashboardDistrettoSummary] = []
    for distretto in db.scalars(select(CatDistretto).order_by(CatDistretto.num_distretto)).all():
        distretto_num = _capacitas_distretto_num(distretto.num_distretto)
        utenze_data = utenze_by_distretto.get(distretto_num, (0, 0, 0, 0)) if distretto_num is not None else (0, 0, 0, 0)
        anomalie_data = anomalie_by_distretto.get(distretto_num, (0, 0)) if distretto_num is not None else (0, 0)
        distretti.append(
            CatDashboardDistrettoSummary(
                distretto_id=UUID(str(distretto.id)),
                num_distretto=distretto.num_distretto,
                nome_distretto=distretto.nome_distretto,
                attivo=distretto.attivo,
                totale_particelle=particelle_by_distretto.get(distretto.num_distretto, 0),
                totale_utenze=_to_int(utenze_data[0]),
                totale_anomalie_aperte=_to_int(anomalie_data[0]),
                anomalie_error=_to_int(anomalie_data[1]),
                superficie_irrigabile_mq=_to_float(utenze_data[1]),
                importo_totale=_to_float(utenze_data[2]) + _to_float(utenze_data[3]),
            )
        )

    importo_totale_0648 = _to_float(utenze_row[3])
    importo_totale_0985 = _to_float(utenze_row[4])
    return CatDashboardSummaryResponse(
        anno=effective_anno,
        generated_at=datetime.now(timezone.utc),
        imports=CatDashboardImportSummary(
            latest_import=CatImportBatchResponse.model_validate(latest_import) if latest_import else None,
            latest_completed=CatImportBatchResponse.model_validate(latest_completed) if latest_completed else None,
            processing_batch=_to_int(import_counts[0]),
            failed_batch=_to_int(import_counts[1]),
            completed_batch=_to_int(import_counts[2]),
            latest_imported_anno=_latest_imported_anno(db),
        ),
        particelle=CatDashboardParticelleSummary(
            totale_correnti=_to_int(particelle_row[0]),
            con_geometria=_to_int(particelle_row[1]),
            senza_geometria=_to_int(particelle_row[2]),
            in_distretto=_to_int(particelle_row[3]),
            fuori_distretto=_to_int(particelle_row[4]),
            senza_distretto=_to_int(particelle_row[5]),
            soppresse=_to_int(particelle_row[6]),
        ),
        utenze=CatDashboardUtenzeSummary(
            anno=effective_anno,
            totale_utenze=_to_int(utenze_row[0]),
            particelle_collegate=_to_int(utenze_row[1]),
            superficie_irrigabile_mq=_to_float(utenze_row[2]),
            importo_totale_0648=importo_totale_0648,
            importo_totale_0985=importo_totale_0985,
            importo_totale=importo_totale_0648 + importo_totale_0985,
            cf_mancante=_to_int(utenze_row[5]),
            cf_invalido=_to_int(utenze_row[6]),
            righe_con_anomalie=_to_int(utenze_row[7]),
            utenze_senza_titolare=_to_int(utenze_row[8]),
        ),
        anomalie=CatDashboardAnomalieSummary(
            aperte=_to_int(anomalie_row[0]),
            error=_to_int(anomalie_row[1]),
            warning=_to_int(anomalie_row[2]),
            info=_to_int(anomalie_row[3]),
            by_tipo=[
                CatDashboardAnomaliaBucket(key=str(tipo), label=str(tipo), count=_to_int(count))
                for tipo, count in tipo_rows
            ],
        ),
        distretti=distretti,
    )
