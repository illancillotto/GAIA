from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.catasto.schemas.gis_schemas import (
    AdeAlignmentApplyPreviewRequest,
    AdeAlignmentApplyPreviewResponse,
    AdeAlignmentReportResponse,
    AdeWfsSyncBboxRequest,
    AdeWfsSyncBboxResponse,
    GisExportFormat,
    GisResolveRefsRequest,
    GisResolveRefsResponse,
    GisSavedSelectionCreate,
    GisSavedSelectionDetail,
    GisSavedSelectionSummary,
    GisSavedSelectionUpdate,
    GisSelectRequest,
    GisSelectResult,
    ParticellaPopupData,
)
from app.modules.catasto.services.ade_wfs import (
    AdeWfsBbox,
    get_ade_alignment_report,
    preview_ade_alignment_apply,
    sync_ade_parcels_bbox,
)
from app.modules.catasto.services import gis_service


router = APIRouter(prefix="/catasto/gis", tags=["catasto-gis"])


@router.post(
    "/ade-wfs/sync-bbox",
    response_model=AdeWfsSyncBboxResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Scarica particelle catastali AdE per bbox",
    description=(
        "Interroga il WFS ufficiale Agenzia delle Entrate CP:CadastralParcel per una bbox limitata, "
        "riproietta le geometrie EPSG:6706 in EPSG:4326 e aggiorna la tabella di staging cat_ade_particelle. "
        "Non modifica cat_particelle."
    ),
)
def sync_ade_wfs_bbox(
    body: AdeWfsSyncBboxRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_active_user),
) -> AdeWfsSyncBboxResponse:
    try:
        result = sync_ade_parcels_bbox(
            db,
            AdeWfsBbox(
                min_lon=body.min_lon,
                min_lat=body.min_lat,
                max_lon=body.max_lon,
                max_lat=body.max_lat,
            ),
            max_tile_km2=body.max_tile_km2,
            max_tiles=body.max_tiles,
            count=body.count,
            max_pages_per_tile=body.max_pages_per_tile,
            created_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"WFS Agenzia Entrate non raggiungibile: {exc}") from exc
    return AdeWfsSyncBboxResponse(**result)


@router.get(
    "/ade-wfs/alignment-report/{run_id}",
    response_model=AdeAlignmentReportResponse,
    summary="Report differenze particelle AdE/GAIA",
    description=(
        "Restituisce il report di confronto per un download WFS AdE completato. "
        "Le particelle mancanti in AdE sono calcolate solo nello scope bbox del run."
    ),
)
def get_ade_wfs_alignment_report(
    run_id: str,
    geometry_threshold_m: float = Query(1.0, gt=0, le=25),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> AdeAlignmentReportResponse:
    try:
        result = get_ade_alignment_report(db, run_id, geometry_threshold_m=geometry_threshold_m)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AdeAlignmentReportResponse(**result)


@router.post(
    "/ade-wfs/alignment-apply-preview/{run_id}",
    response_model=AdeAlignmentApplyPreviewResponse,
    summary="Preview applicazione differenze AdE/GAIA",
    description=(
        "Calcola il piano di applicazione delle differenze AdE senza modificare cat_particelle. "
        "I match ambigui sono sempre esclusi dall'applicazione automatica."
    ),
)
def preview_ade_wfs_alignment_apply(
    run_id: str,
    body: AdeAlignmentApplyPreviewRequest,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> AdeAlignmentApplyPreviewResponse:
    try:
        result = preview_ade_alignment_apply(
            db,
            run_id,
            categories=body.categories,
            geometry_threshold_m=body.geometry_threshold_m,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AdeAlignmentApplyPreviewResponse(**result)


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


@router.post(
    "/resolve-refs",
    response_model=GisResolveRefsResponse,
    summary="Risolvi particelle da riferimenti catastali",
    description=(
        "Riceve una lista di riferimenti (comune/sezione/foglio/particella/sub) e prova a risolvere "
        "le particelle correnti. Il campo comune accetta nome comune, cod_comune_capacitas o codice catastale/Belfiore. "
        "Opzionalmente restituisce un GeoJSON FeatureCollection per visualizzazione su mappa."
    ),
)
def resolve_particelle_refs(
    body: GisResolveRefsRequest,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> GisResolveRefsResponse:
    return gis_service.resolve_particelle_refs(db, body)


@router.get(
    "/saved-selections",
    response_model=list[GisSavedSelectionSummary],
    summary="Lista selezioni GIS salvate",
)
def list_saved_selections(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_active_user),
) -> list[GisSavedSelectionSummary]:
    return gis_service.list_saved_selections(db, current_user.id)


@router.post(
    "/saved-selections",
    response_model=GisSavedSelectionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Salva una selezione GIS",
)
def create_saved_selection(
    body: GisSavedSelectionCreate,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_active_user),
) -> GisSavedSelectionDetail:
    return gis_service.create_saved_selection(db, body, current_user.id)


@router.get(
    "/saved-selections/{selection_id}",
    response_model=GisSavedSelectionDetail,
    summary="Dettaglio selezione GIS salvata",
)
def get_saved_selection(
    selection_id: str,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_active_user),
) -> GisSavedSelectionDetail:
    return gis_service.get_saved_selection(db, selection_id, current_user.id)


@router.patch(
    "/saved-selections/{selection_id}",
    response_model=GisSavedSelectionSummary,
    summary="Aggiorna metadati selezione GIS salvata",
)
def update_saved_selection(
    selection_id: str,
    body: GisSavedSelectionUpdate,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_active_user),
) -> GisSavedSelectionSummary:
    return gis_service.update_saved_selection(db, selection_id, body, current_user.id)


@router.delete(
    "/saved-selections/{selection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina selezione GIS salvata",
)
def delete_saved_selection(
    selection_id: str,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_active_user),
) -> Response:
    gis_service.delete_saved_selection(db, selection_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
