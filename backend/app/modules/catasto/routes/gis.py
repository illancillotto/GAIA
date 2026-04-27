from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.catasto.schemas.gis_schemas import (
    GisExportFormat,
    GisSelectRequest,
    GisSelectResult,
    ParticellaPopupData,
)
from app.modules.catasto.services import gis_service


router = APIRouter(prefix="/catasto/gis", tags=["catasto-gis"])


@router.post(
    "/select",
    response_model=GisSelectResult,
    summary="Selezione spaziale particelle",
    description=(
        "Riceve una geometria GeoJSON Polygon/MultiPolygon, esegue query spaziale "
        "su cat_particelle e restituisce aggregazioni e lista preview."
    ),
)
def select_by_geometry(
    body: GisSelectRequest,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> GisSelectResult:
    return gis_service.select_by_geometry(db, body.geometry, body.filters)


@router.get(
    "/export",
    summary="Export selezione particelle",
    description="Export GeoJSON o CSV delle particelle selezionate per lista di ID.",
)
def export_selection(
    ids: str = Query(..., description="ID particelle separati da virgola"),
    format: GisExportFormat = Query(GisExportFormat.csv, description="Formato output"),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
):
    id_list = [item.strip() for item in ids.split(",") if item.strip()]
    return gis_service.export_particelle(db, id_list, format)


@router.get(
    "/particella/{particella_id}/popup",
    response_model=ParticellaPopupData,
    summary="Dati popup particella",
    description="Dati essenziali per il popup mappa, senza geometria.",
)
def get_particella_popup(
    particella_id: str,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> ParticellaPopupData:
    return gis_service.get_popup_data(db, particella_id)
