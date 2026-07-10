from __future__ import annotations

import base64
import binascii
import logging
import math
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_mobile_connector
from app.core.datetime_compat import UTC
from app.core.config import settings
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import (
    CatDeliveryPoint,
    CatMeterReading,
    CatParticella,
    CatUtenzaIntestatario,
    CatUtenzaIrrigua,
)
from app.modules.operazioni.models.activities import (
    ActivityCatalog,
    OperatorActivity,
    OperatorActivityAttachment,
    OperatorActivityEvent,
)
from app.modules.operazioni.models.attachments import Attachment
from app.modules.operazioni.models.mobile_sync import MobileSyncEvent
from app.modules.operazioni.models.organizational import OperatorProfile, Team, TeamMembership
from app.modules.operazioni.models.reports import (
    FieldReport,
    FieldReportAttachment,
    FieldReportCategory,
    FieldReportSeverity,
    InternalCase,
    InternalCaseAttachment,
    InternalCaseEvent,
)
from app.modules.operazioni.models.vehicles import Vehicle, VehicleAssignment
from app.modules.operazioni.services.attachment_service import (
    build_storage_path,
    compute_checksum,
    create_attachment_record,
)
from app.modules.operazioni.schemas.operators import GateMobileConsoleRole
from app.modules.operazioni.models.wc_operator import WCOperator

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/mobile-sync",
    tags=["mobile-sync"],
    dependencies=[Depends(require_mobile_connector)],
)


class MobileSyncAPIError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        error_code: str,
        message: str,
        retryable: bool,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.retryable = retryable
        self.details = details or {}
        super().__init__(message)

    def to_response(self) -> JSONResponse:
        return JSONResponse(
            status_code=self.status_code,
            content={
                "error_code": self.error_code,
                "message": self.message,
                "retryable": self.retryable,
                "details": self.details,
            },
        )


class MobileOperatorResponseItem(BaseModel):
    operator_id: UUID
    gaia_user_id: str
    gaia_operator_profile_id: str | None
    gaia_username: str
    display_name: str
    email: str
    phone: str | None
    status: str
    gate_mobile_console_enabled: bool
    gate_mobile_console_role: GateMobileConsoleRole | None


class MobileOperatorsResponse(BaseModel):
    synced_from_gaia_at: datetime | None
    operators: list[MobileOperatorResponseItem]


class MobileCatalogItem(BaseModel):
    catalog_type: str
    version: str
    synced_from_gaia_at: datetime | None
    payload: dict[str, Any]


class MobileCatalogsResponse(BaseModel):
    catalogs: list[MobileCatalogItem]


class MobileWorksetItem(BaseModel):
    gaia_entity_id: str
    payload: dict[str, Any]


class MobileWorksetResponseItem(BaseModel):
    operator_id: UUID
    workset_type: str
    synced_from_gaia_at: datetime | None
    items: list[MobileWorksetItem]


class MobileWorksetsResponse(BaseModel):
    worksets: list[MobileWorksetResponseItem]


class MobileSyncAttachmentRef(BaseModel):
    client_attachment_id: UUID | None = None
    filename: str
    mime_type: str
    size_bytes: int | None = None
    sha256: str | None = None
    content_base64: str | None = None


class MobileGpsPoint(BaseModel):
    lat: float
    lng: float
    accuracy_m: float | None = None


class MobileFieldReportPayload(BaseModel):
    title: str
    description: str | None = None
    category_id: str
    severity_id: str | None = None
    occurred_at_device: datetime | None = None
    linked_gaia_activity_id: UUID | None = None
    gps_position: MobileGpsPoint | None = None
    gps_point: MobileGpsPoint | None = None


class MobileFieldReportRequest(BaseModel):
    client_event_id: UUID
    operator_id: UUID
    device_id: UUID | str
    payload_version: int = 1
    payload_hash: str = Field(min_length=8, max_length=128)
    payload: MobileFieldReportPayload
    attachments: list[MobileSyncAttachmentRef] = []


class MobileActivityStartPayload(BaseModel):
    activity_catalog_id: UUID
    team_id: UUID | None = None
    vehicle_id: UUID | None = None
    delivery_point_id: UUID | None = None
    meter_number: str | None = None
    meter_reading_value: Decimal | None = None
    notes: str | None = None
    started_at_device: datetime
    gps_start: MobileGpsPoint | None = None


class MobileActivityStartRequest(BaseModel):
    client_event_id: UUID
    operator_id: UUID
    device_id: UUID | str
    payload_version: int = 1
    payload_hash: str = Field(min_length=8, max_length=128)
    payload: MobileActivityStartPayload
    attachments: list[MobileSyncAttachmentRef] = []


class MobileActivityStopPayload(BaseModel):
    gaia_activity_id: UUID | None = None
    client_started_event_id: UUID | None = None
    stopped_at_device: datetime
    odometer_km: float | None = None
    notes: str | None = None
    gps_end: MobileGpsPoint | None = None


class MobileActivityStopRequest(BaseModel):
    client_event_id: UUID
    operator_id: UUID
    device_id: UUID | str
    payload_version: int = 1
    payload_hash: str = Field(min_length=8, max_length=128)
    payload: MobileActivityStopPayload
    attachments: list[MobileSyncAttachmentRef] = []


class MobileSyncApplyResponse(BaseModel):
    gaia_entity_type: str
    gaia_entity_id: str
    extra: dict[str, Any] | None = None


class MobileTetiFaultPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    plant_id: UUID = Field(alias="plantId")
    asset_id: UUID | None = Field(default=None, alias="assetId")
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    latitude: float | None = None
    longitude: float | None = None


class MobileTetiFaultWorkRequest(BaseModel):
    cloud_event_id: UUID
    client_event_id: UUID
    operator_id: UUID
    device_id: UUID | str
    payload_version: int = 1
    payload_hash: str = Field(min_length=8, max_length=128)
    teti_fault_id: str = Field(min_length=1, max_length=255)
    payload: MobileTetiFaultPayload
    attachments: list[MobileSyncAttachmentRef] = []


class MobileSyncAttachmentUploadResponse(BaseModel):
    attachment_id: UUID
    client_attachment_id: UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    checksum_sha256: str


class MobileConnectorHandshakeResponse(BaseModel):
    service: str
    authenticated: bool
    auth_scheme: str
    connector_header: str
    gaia_version: str
    server_time: datetime
    capabilities: list[str]


DeliveryPointCoordinates = dict[UUID, tuple[float, float]]
INVALID_MOBILE_METER_CODES = {"0", "N.L.", "NL", "N/L", "N.L", "N.D.", "ND", "NON LETTO", "NON RILEVATO"}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _coalesce_datetime(*values: datetime | None) -> datetime | None:
    filtered = [value for value in values if value is not None]
    return max(filtered) if filtered else None


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _mobile_error(
    *,
    status_code: int,
    error_code: str,
    message: str,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> MobileSyncAPIError:
    return MobileSyncAPIError(
        status_code=status_code,
        error_code=error_code,
        message=message,
        retryable=retryable,
        details=details,
    )


def _stable_catalog_id(*, uuid_value: UUID, wc_id: int | None = None) -> str:
    return str(wc_id) if wc_id is not None else str(uuid_value)


def _operator_display_name(operator: WCOperator, user: ApplicationUser | None) -> str:
    parts = [operator.first_name, operator.last_name]
    name = " ".join(part.strip() for part in parts if part and part.strip()).strip()
    if name:
        return name
    if user and user.username:
        return user.username
    if operator.username:
        return operator.username
    return str(operator.id)


def _stringify_uuid(value: UUID | None) -> str | None:
    return str(value) if value is not None else None


def _as_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _valid_wgs84_point(lat: float | None, lng: float | None) -> bool:
    return lat is not None and lng is not None and -90 <= lat <= 90 and -180 <= lng <= 180


def _delivery_point_coordinates(db: Session, points: list[CatDeliveryPoint]) -> DeliveryPointCoordinates:
    if not points:
        return {}

    if db.bind is not None and db.bind.dialect.name == "postgresql":
        rows = db.execute(
            select(
                CatDeliveryPoint.id,
                func.ST_Y(CatDeliveryPoint.geometry).label("lat"),
                func.ST_X(CatDeliveryPoint.geometry).label("lng"),
            ).where(
                CatDeliveryPoint.id.in_([point.id for point in points]),
                CatDeliveryPoint.geometry.is_not(None),
            )
        ).all()
        return {
            row.id: (float(row.lat), float(row.lng))
            for row in rows
            if _valid_wgs84_point(float(row.lat) if row.lat is not None else None, float(row.lng) if row.lng is not None else None)
        }

    coordinates: DeliveryPointCoordinates = {}
    for point in points:
        lat = _as_float(point.source_y)
        lng = _as_float(point.source_x)
        if _valid_wgs84_point(lat, lng):
            coordinates[point.id] = (lat, lng)
    return coordinates


def _meter_parcel_coordinates(db: Session, meters: list[CatMeterReading]) -> dict[UUID, tuple[float, float]]:
    subject_ids = sorted({meter.subject_id for meter in meters if meter.subject_id is not None})
    if not subject_ids or db.bind is None or db.bind.dialect.name != "postgresql":
        return {}

    rows = db.execute(
        select(
            CatMeterReading.id.label("meter_id"),
            func.ST_Y(func.ST_PointOnSurface(CatParticella.geometry)).label("lat"),
            func.ST_X(func.ST_PointOnSurface(CatParticella.geometry)).label("lng"),
        )
        .join(CatUtenzaIntestatario, CatUtenzaIntestatario.subject_id == CatMeterReading.subject_id)
        .join(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatUtenzaIntestatario.utenza_id)
        .join(CatParticella, CatParticella.id == CatUtenzaIrrigua.particella_id)
        .where(
            CatMeterReading.id.in_([meter.id for meter in meters]),
            CatParticella.geometry.is_not(None),
            CatParticella.is_current == True,
            CatParticella.suppressed == False,
        )
        .order_by(CatUtenzaIntestatario.anno_riferimento.desc().nullslast(), CatUtenzaIntestatario.collected_at.desc())
    ).all()

    coordinates: dict[UUID, tuple[float, float]] = {}
    for row in rows:
        if row.meter_id in coordinates:
            continue
        lat = float(row.lat) if row.lat is not None else None
        lng = float(row.lng) if row.lng is not None else None
        if _valid_wgs84_point(lat, lng):
            coordinates[row.meter_id] = (lat, lng)
    return coordinates


def _delivery_point_payload(
    point: CatDeliveryPoint,
    coordinates: tuple[float, float],
    reading: CatMeterReading | None,
) -> dict[str, Any]:
    lat, lng = coordinates
    meter_code = point.cod_cont or (reading.matricola if reading else None)
    label_parts = [point.punto_consegna_code, meter_code, point.tipologia]
    return {
        "id": str(point.id),
        "delivery_point_id": str(point.id),
        "label": " · ".join(part for part in label_parts if part),
        "code": point.punto_consegna_code,
        "punto_consegna": point.punto_consegna_code,
        "matricola": meter_code,
        "cod_cont": point.cod_cont,
        "distretto_code": point.distretto_code,
        "tipologia": point.tipologia,
        "tipo": point.tipo,
        "has_meter": point.has_meter,
        "gps_lat": lat,
        "gps_lng": lng,
        "lat": lat,
        "lng": lng,
        "source_dataset": point.source_dataset,
        "reading_id": str(reading.id) if reading else None,
        "reading_year": reading.anno if reading else None,
        "operational_state": reading.operational_state if reading else None,
    }


def _meter_catalog_payload(meter: CatMeterReading, parcel_coordinates: tuple[float, float] | None) -> dict[str, Any]:
    direct_lat = _as_float(meter.gps_lat)
    direct_lng = _as_float(meter.gps_lng)
    has_direct_gps = _valid_wgs84_point(direct_lat, direct_lng)
    lat, lng = (direct_lat, direct_lng) if has_direct_gps else (parcel_coordinates or (None, None))
    return {
        "id": str(meter.id),
        "label": " · ".join(part for part in [meter.punto_consegna, meter.matricola] if part),
        "punto_consegna": meter.punto_consegna,
        "matricola": meter.matricola,
        "anno": meter.anno,
        "record_type": meter.record_type,
        "record_kind": meter.record_kind,
        "operational_state": meter.operational_state,
        "gps_lat": lat,
        "gps_lng": lng,
        "lat": lat,
        "lng": lng,
        "position_source": "meter_gps" if has_direct_gps else ("parcel" if parcel_coordinates else None),
        "intervento_da_eseguire": meter.intervento_da_eseguire,
    }


def _attachment_metadata(attachment: Attachment) -> dict[str, Any]:
    return attachment.metadata_json if isinstance(attachment.metadata_json, dict) else {}


def _serialize_response(event: MobileSyncEvent) -> MobileSyncApplyResponse:
    return MobileSyncApplyResponse(
        gaia_entity_type=event.gaia_entity_type,
        gaia_entity_id=event.gaia_entity_id,
        extra=event.result_json if isinstance(event.result_json, dict) else None,
    )


def _serialize_response_with_status(event: MobileSyncEvent, *, status_value: str) -> MobileSyncApplyResponse:
    extra = event.result_json.copy() if isinstance(event.result_json, dict) else {}
    extra["status"] = status_value
    return MobileSyncApplyResponse(
        gaia_entity_type=event.gaia_entity_type,
        gaia_entity_id=event.gaia_entity_id,
        extra=extra,
    )


def _resolve_mobile_operator(db: Session, operator_id: UUID) -> tuple[WCOperator, ApplicationUser, OperatorProfile | None]:
    operator = db.get(WCOperator, operator_id)
    if operator is None:
        raise _mobile_error(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="GAIA_VALIDATION_ERROR",
            message="Operatore mobile non trovato",
            details={"field": "operator_id"},
        )
    if operator.gaia_user_id is None:
        raise _mobile_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="GAIA_VALIDATION_ERROR",
            message="Operatore mobile non collegato a un utente GAIA",
            details={"field": "operator_id"},
        )
    user = db.get(ApplicationUser, operator.gaia_user_id)
    if user is None:
        raise _mobile_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="GAIA_VALIDATION_ERROR",
            message="Utente GAIA collegato all'operatore non trovato",
            details={"field": "operator_id"},
        )
    if not user.is_active or not operator.enabled:
        raise _mobile_error(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="GAIA_VALIDATION_ERROR",
            message="Operatore disabilitato",
            details={"field": "operator_id"},
        )
    profile = db.scalar(select(OperatorProfile).where(OperatorProfile.user_id == user.id))
    return operator, user, profile


def _resolve_mobile_event(
    db: Session,
    *,
    client_event_id: UUID,
    event_type: str,
    payload_hash: str,
    conflict_error_code: str = "GAIA_CONFLICT_ERROR",
) -> MobileSyncEvent | None:
    event = db.scalar(select(MobileSyncEvent).where(MobileSyncEvent.client_event_id == client_event_id))
    if event is None:
        return None
    if event.event_type != event_type:
        raise _mobile_error(
            status_code=status.HTTP_409_CONFLICT,
            error_code=conflict_error_code,
            message="client_event_id gia usato per un tipo evento diverso",
            details={"field": "client_event_id"},
        )
    if event.payload_hash != payload_hash:
        raise _mobile_error(
            status_code=status.HTTP_409_CONFLICT,
            error_code=conflict_error_code,
            message="client_event_id gia presente con payload diverso",
            details={"field": "client_event_id"},
        )
    return event


def _resolve_mobile_event_by_external_reference(
    db: Session,
    *,
    event_type: str,
    external_reference: str,
    payload_hash: str,
) -> MobileSyncEvent | None:
    event = db.scalar(
        select(MobileSyncEvent).where(
            MobileSyncEvent.event_type == event_type,
            MobileSyncEvent.external_reference == external_reference,
        )
    )
    if event is None:
        return None
    if event.payload_hash != payload_hash:
        raise _mobile_error(
            status_code=status.HTTP_409_CONFLICT,
            error_code="GAIA_CONFLICT",
            message="teti_fault_id gia presente con payload diverso",
            details={"field": "teti_fault_id"},
        )
    return event


def _create_mobile_event(
    db: Session,
    *,
    client_event_id: UUID,
    event_type: str,
    operator_id: UUID,
    device_id: str,
    payload_version: int,
    payload_hash: str,
    cloud_event_id: UUID | None,
    external_reference: str | None,
    gaia_entity_type: str,
    gaia_entity_id: str,
    source_entity_id: UUID | None,
    payload_json: dict[str, Any],
    result_json: dict[str, Any] | None = None,
) -> MobileSyncEvent:
    event = MobileSyncEvent(
        client_event_id=client_event_id,
        event_type=event_type,
        operator_id=operator_id,
        device_id=device_id,
        payload_version=payload_version,
        payload_hash=payload_hash,
        cloud_event_id=cloud_event_id,
        external_reference=external_reference,
        gaia_entity_type=gaia_entity_type,
        gaia_entity_id=gaia_entity_id,
        source_entity_id=source_entity_id,
        payload_json=payload_json,
        result_json=result_json,
    )
    db.add(event)
    return event


def _resolve_report_category(db: Session, category_ref: str) -> FieldReportCategory:
    category = None
    if category_ref.isdigit():
        category = db.scalar(select(FieldReportCategory).where(FieldReportCategory.wc_id == int(category_ref)))
    if category is None:
        try:
            category_uuid = UUID(category_ref)
        except ValueError:
            category_uuid = None
        if category_uuid is not None:
            category = db.get(FieldReportCategory, category_uuid)
    if category is None or not category.is_active:
        raise _mobile_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="GAIA_VALIDATION_ERROR",
            message="Categoria segnalazione non valida",
            details={"field": "category_id"},
        )
    return category


def _resolve_report_severity(db: Session, severity_ref: str | None) -> FieldReportSeverity:
    severity = None
    if severity_ref:
        try:
            severity = db.get(FieldReportSeverity, UUID(severity_ref))
        except ValueError:
            severity = db.scalar(select(FieldReportSeverity).where(FieldReportSeverity.code == severity_ref))
    if severity is None:
        severity = db.scalar(
            select(FieldReportSeverity)
            .where(FieldReportSeverity.is_active == True)
            .order_by(FieldReportSeverity.rank_order.asc(), FieldReportSeverity.name.asc())
        )
    if severity is None or not severity.is_active:
        raise _mobile_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="GAIA_VALIDATION_ERROR",
            message="Severita segnalazione non configurata",
            details={"field": "severity_id"},
        )
    return severity


def _resolve_teti_category(db: Session) -> FieldReportCategory:
    for code in ("TETI_FAULT", "TETI", "FAULT", "GUASTO", "LOSS"):
        category = db.scalar(
            select(FieldReportCategory).where(
                FieldReportCategory.code == code,
                FieldReportCategory.is_active == True,
            )
        )
        if category is not None:
            return category

    category = db.scalar(
        select(FieldReportCategory)
        .where(FieldReportCategory.is_active == True)
        .order_by(FieldReportCategory.sort_order.asc(), FieldReportCategory.name.asc())
    )
    if category is None:
        raise _mobile_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="GAIA_VALIDATION_ERROR",
            message="Categoria segnalazione non configurata per fault TETI",
            details={"field": "payload"},
        )
    return category


def _resolve_teti_severity(db: Session, severity_code: str) -> FieldReportSeverity:
    direct = db.scalar(
        select(FieldReportSeverity).where(
            FieldReportSeverity.code == severity_code,
            FieldReportSeverity.is_active == True,
        )
    )
    if direct is not None:
        return direct

    severities = db.scalars(
        select(FieldReportSeverity)
        .where(FieldReportSeverity.is_active == True)
        .order_by(FieldReportSeverity.rank_order.asc(), FieldReportSeverity.name.asc())
    ).all()
    if not severities:
        raise _mobile_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="GAIA_VALIDATION_ERROR",
            message="Severita segnalazione non configurata per fault TETI",
            details={"field": "payload.severity"},
        )

    buckets = {
        "LOW": 0,
        "MEDIUM": max(0, round((len(severities) - 1) / 3)),
        "HIGH": max(0, round(((len(severities) - 1) * 2) / 3)),
        "CRITICAL": len(severities) - 1,
    }
    return severities[buckets[severity_code]]


def _build_activity_number(prefix: str, db: Session, model: type[FieldReport] | type[InternalCase]) -> str:
    year = _utcnow().year
    total = db.scalar(select(func.count(model.id))) or 0
    return f"{prefix}-{year}-{total + 1:06d}"


def _activity_payload_item(
    activity: OperatorActivity,
    catalog_lookup: dict[UUID, ActivityCatalog],
    team_lookup: dict[UUID, Team],
    vehicle_lookup: dict[UUID, Vehicle],
) -> MobileWorksetItem:
    catalog = catalog_lookup.get(activity.activity_catalog_id)
    team = team_lookup.get(activity.team_id) if activity.team_id else None
    vehicle = vehicle_lookup.get(activity.vehicle_id) if activity.vehicle_id else None
    return MobileWorksetItem(
        gaia_entity_id=str(activity.id),
        payload={
            "activity_catalog_id": str(activity.activity_catalog_id),
            "activity_catalog_code": catalog.code if catalog else None,
            "activity_catalog_name": catalog.name if catalog else None,
            "status": activity.status,
            "title": catalog.name if catalog else "Attivita operatore",
            "started_at": activity.started_at,
            "ended_at": activity.ended_at,
            "team_id": _stringify_uuid(activity.team_id),
            "team_label": team.name if team else None,
            "vehicle_id": _stringify_uuid(activity.vehicle_id),
            "plate": vehicle.plate_number if vehicle else None,
            "vehicle_label": " · ".join(
                part for part in [vehicle.code if vehicle else None, vehicle.name if vehicle else None] if part
            )
            if vehicle
            else None,
            "notes": activity.text_note,
        },
    )


def _vehicle_payload_item(vehicle: Vehicle) -> MobileWorksetItem:
    return MobileWorksetItem(
        gaia_entity_id=str(vehicle.id),
        payload={
            "id": str(vehicle.id),
            "code": vehicle.code,
            "label": " · ".join(part for part in [vehicle.code, vehicle.name, vehicle.plate_number] if part),
            "plate": vehicle.plate_number,
            "name": vehicle.name,
            "status": vehicle.current_status,
            "vehicle_type": vehicle.vehicle_type,
        },
    )


def _meter_payload_item(meter: CatMeterReading) -> MobileWorksetItem:
    return MobileWorksetItem(
        gaia_entity_id=str(meter.id),
        payload={
            "id": str(meter.id),
            "punto_consegna": meter.punto_consegna,
            "matricola": meter.matricola,
            "anno": meter.anno,
            "record_type": meter.record_type,
            "record_kind": meter.record_kind,
            "operational_state": meter.operational_state,
            "gps_lat": _as_float(meter.gps_lat),
            "gps_lng": _as_float(meter.gps_lng),
            "intervento_da_eseguire": meter.intervento_da_eseguire,
        },
    )


def _team_payload_item(team: Team) -> MobileWorksetItem:
    return MobileWorksetItem(
        gaia_entity_id=str(team.id),
        payload={
            "id": str(team.id),
            "team_id": str(team.id),
            "team_label": team.name,
            "team_code": team.code,
        },
    )


def _version_from_items(items: list[Any], *fields: str) -> str:
    latest: datetime | None = None
    for item in items:
        for field in fields:
            value = getattr(item, field, None)
            if isinstance(value, datetime):
                latest = value if latest is None or value > latest else latest
    return (latest or _utcnow()).isoformat()


def _fetch_mobile_uploaded_attachments(
    db: Session,
    *,
    operator_id: UUID,
    attachments: list[MobileSyncAttachmentRef],
) -> list[Attachment]:
    candidate_ids = [str(item.client_attachment_id) for item in attachments if item.client_attachment_id is not None]
    if not candidate_ids:
        return []

    rows = db.scalars(
        select(Attachment).where(
            Attachment.source_context == "mobile_sync_attachment",
            Attachment.is_deleted == False,
        )
    ).all()

    uploaded_attachments: list[Attachment] = []
    for item in attachments:
        if item.client_attachment_id is None:
            continue
        resolved = None
        for candidate in rows:
            metadata = _attachment_metadata(candidate)
            if (
                metadata.get("client_attachment_id") == str(item.client_attachment_id)
                and metadata.get("operator_id") == str(operator_id)
            ):
                resolved = candidate
                break
        if resolved is None:
            raise _mobile_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="GAIA_VALIDATION_ERROR",
                message="Allegato mobile non trovato per il client_attachment_id indicato",
                details={"field": "attachments"},
            )
        if item.sha256 and resolved.checksum_sha256 and item.sha256 != resolved.checksum_sha256:
            raise _mobile_error(
                status_code=status.HTTP_409_CONFLICT,
                error_code="GAIA_CONFLICT_ERROR",
                message="Checksum allegato non coerente con il file caricato",
                details={"field": "attachments"},
            )
        uploaded_attachments.append(resolved)
    return uploaded_attachments


def _resolve_existing_mobile_attachment(
    rows: list[Attachment],
    *,
    operator_id: UUID,
    client_attachment_id: UUID,
) -> Attachment | None:
    for candidate in rows:
        metadata = _attachment_metadata(candidate)
        if (
            metadata.get("client_attachment_id") == str(client_attachment_id)
            and metadata.get("operator_id") == str(operator_id)
        ):
            return candidate
    return None


def _decode_mobile_attachment_content(attachment: MobileSyncAttachmentRef) -> bytes:
    if attachment.content_base64 is None:
        raise _mobile_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="GAIA_VALIDATION_ERROR",
            message="content_base64 mancante per allegato inline",
            details={"field": "attachments"},
        )
    try:
        file_bytes = base64.b64decode(attachment.content_base64, validate=True)
    except (ValueError, binascii.Error):
        raise _mobile_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="GAIA_VALIDATION_ERROR",
            message="content_base64 allegato non valido",
            details={"field": "attachments"},
        )
    if attachment.size_bytes is not None and len(file_bytes) != attachment.size_bytes:
        raise _mobile_error(
            status_code=status.HTTP_409_CONFLICT,
            error_code="GAIA_CONFLICT_ERROR",
            message="Dimensione allegato non coerente con il contenuto inviato",
            details={"field": "attachments"},
        )
    return file_bytes


def _create_inline_mobile_attachment(
    db: Session,
    *,
    operator_id: UUID,
    device_id: str,
    attachment: MobileSyncAttachmentRef,
) -> Attachment:
    if attachment.client_attachment_id is None:
        raise _mobile_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="GAIA_VALIDATION_ERROR",
            message="client_attachment_id obbligatorio per allegato inline",
            details={"field": "attachments"},
        )

    existing_rows = db.scalars(
        select(Attachment).where(
            Attachment.source_context == "mobile_sync_attachment",
            Attachment.is_deleted == False,
        )
    ).all()
    existing = _resolve_existing_mobile_attachment(
        existing_rows,
        operator_id=operator_id,
        client_attachment_id=attachment.client_attachment_id,
    )

    file_bytes = _decode_mobile_attachment_content(attachment)
    computed_checksum = compute_checksum(file_bytes)
    if attachment.sha256 and attachment.sha256 != computed_checksum:
        raise _mobile_error(
            status_code=status.HTTP_409_CONFLICT,
            error_code="GAIA_CONFLICT_ERROR",
            message="Checksum allegato non coerente con il contenuto inviato",
            details={"field": "attachments"},
        )

    if existing is not None:
        if existing.checksum_sha256 and existing.checksum_sha256 != computed_checksum:
            raise _mobile_error(
                status_code=status.HTTP_409_CONFLICT,
                error_code="GAIA_CONFLICT_ERROR",
                message="client_attachment_id gia presente con file diverso",
                details={"field": "attachments"},
            )
        return existing

    storage_path = build_storage_path(attachment.filename or str(attachment.client_attachment_id))
    Path(storage_path).parent.mkdir(parents=True, exist_ok=True)
    Path(storage_path).write_bytes(file_bytes)

    created = create_attachment_record(
        db,
        storage_path=str(storage_path),
        filename=attachment.filename or str(attachment.client_attachment_id),
        mime_type=attachment.mime_type,
        file_size=len(file_bytes),
        source_context="mobile_sync_attachment",
        checksum=computed_checksum,
    )
    created.metadata_json = {
        "client_attachment_id": str(attachment.client_attachment_id),
        "operator_id": str(operator_id),
        "device_id": device_id,
        "upload_origin": "gaia_mobile_connector_inline",
    }
    return created


def _resolve_mobile_attachments(
    db: Session,
    *,
    operator_id: UUID,
    device_id: str,
    attachments: list[MobileSyncAttachmentRef],
) -> list[Attachment]:
    resolved: list[Attachment] = []
    uploaded = _fetch_mobile_uploaded_attachments(
        db,
        operator_id=operator_id,
        attachments=[item for item in attachments if item.content_base64 is None],
    )
    uploaded_by_id = {
        _attachment_metadata(item).get("client_attachment_id"): item
        for item in uploaded
    }
    for item in attachments:
        if item.content_base64 is not None:
            resolved.append(
                _create_inline_mobile_attachment(
                    db,
                    operator_id=operator_id,
                    device_id=device_id,
                    attachment=item,
                )
            )
            continue
        if item.client_attachment_id is None:
            raise _mobile_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="GAIA_VALIDATION_ERROR",
                message="client_attachment_id obbligatorio per allegato mobile",
                details={"field": "attachments"},
            )
        resolved.append(uploaded_by_id[str(item.client_attachment_id)])
    return resolved


def _link_activity_attachments(
    db: Session,
    *,
    activity: OperatorActivity,
    attachments: list[Attachment],
) -> None:
    for attachment in attachments:
        db.add(
            OperatorActivityAttachment(
                operator_activity_id=activity.id,
                attachment_id=attachment.id,
            )
        )
        attachment.source_entity_id = activity.id
        metadata = _attachment_metadata(attachment).copy()
        metadata["linked_activity_id"] = str(activity.id)
        attachment.metadata_json = metadata


def _normalize_meter_number(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _build_mobile_meter_reading(
    *,
    operator: WCOperator,
    activity: OperatorActivity,
    data: MobileActivityStartRequest,
    attachments: list[Attachment],
    delivery_point: CatDeliveryPoint | None = None,
) -> CatMeterReading:
    gps = data.payload.gps_start
    meter_number = _normalize_meter_number(data.payload.meter_number)
    if meter_number is None and delivery_point is not None:
        meter_number = _normalize_meter_number(delivery_point.cod_cont)
    started_at = _normalize_datetime(data.payload.started_at_device)
    first_attachment = attachments[0] if attachments else None
    return CatMeterReading(
        anno=started_at.year,
        punto_consegna=delivery_point.punto_consegna_code if delivery_point else (meter_number or f"MOBILE-{activity.id}"),
        matricola=meter_number,
        delivery_point_id=delivery_point.id if delivery_point else None,
        record_type="CONT_NO_TES",
        record_kind="meter_reading",
        operational_state="active",
        lettura_finale=data.payload.meter_reading_value,
        data_lettura=date.fromisoformat(started_at.date().isoformat()),
        operatore_lettura=_operator_display_name(operator, None),
        note=data.payload.notes,
        source="mobile",
        mobile_session_id=str(activity.id),
        gps_lat=Decimal(str(gps.lat)) if gps else None,
        gps_lng=Decimal(str(gps.lng)) if gps else None,
        photo_url=first_attachment.storage_path if first_attachment is not None else None,
        offline_created_at=data.payload.started_at_device,
        synced_at=_utcnow(),
        sync_status="applied_to_gaia",
        device_id=str(data.device_id),
        mobile_operator_id=str(operator.id),
        import_payload_json={
            "client_event_id": str(data.client_event_id),
            "activity_id": str(activity.id),
            "activity_catalog_id": str(data.payload.activity_catalog_id),
            "delivery_point_id": str(delivery_point.id) if delivery_point else None,
            "operator_id": str(operator.id),
            "meter_number": meter_number,
            "meter_reading_value": str(data.payload.meter_reading_value) if data.payload.meter_reading_value is not None else None,
            "attachments": [
                {
                    "attachment_id": str(item.id),
                    "client_attachment_id": _attachment_metadata(item).get("client_attachment_id"),
                    "filename": item.original_filename,
                    "mime_type": item.mime_type,
                    "storage_path": item.storage_path,
                }
                for item in attachments
            ],
            "payload": data.model_dump(mode="json"),
        },
    )


def _link_report_attachments(
    db: Session,
    *,
    report: FieldReport,
    case: InternalCase,
    attachments: list[Attachment],
    actor_user_id: int,
) -> None:
    for attachment in attachments:
        db.add(
            FieldReportAttachment(
                field_report_id=report.id,
                attachment_id=attachment.id,
            )
        )
        db.add(
            InternalCaseAttachment(
                internal_case_id=case.id,
                attachment_id=attachment.id,
                uploaded_by_user_id=actor_user_id,
            )
        )
        attachment.source_entity_id = report.id
        metadata = _attachment_metadata(attachment).copy()
        metadata["linked_report_id"] = str(report.id)
        metadata["linked_case_id"] = str(case.id)
        attachment.metadata_json = metadata


@router.post(
    "/attachments/upload",
    response_model=MobileSyncAttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_mobile_attachment(
    operator_id: UUID = Form(...),
    device_id: str = Form(...),
    client_attachment_id: UUID = Form(...),
    file: UploadFile = File(...),
    checksum_sha256: str | None = Form(None),
    db: Annotated[Session, Depends(get_db)] = None,
) -> MobileSyncAttachmentUploadResponse | JSONResponse:
    try:
        operator, _, _ = _resolve_mobile_operator(db, operator_id)
        file_bytes = await file.read()
        computed_checksum = compute_checksum(file_bytes)
        if checksum_sha256 and checksum_sha256 != computed_checksum:
            raise _mobile_error(
                status_code=status.HTTP_409_CONFLICT,
                error_code="GAIA_CONFLICT_ERROR",
                message="Checksum allegato non coerente con il file inviato",
                details={"field": "checksum_sha256"},
            )

        existing_rows = db.scalars(
            select(Attachment).where(
                Attachment.source_context == "mobile_sync_attachment",
                Attachment.is_deleted == False,
            )
        ).all()
        for existing in existing_rows:
            metadata = _attachment_metadata(existing)
            if (
                metadata.get("client_attachment_id") == str(client_attachment_id)
                and metadata.get("operator_id") == str(operator.id)
            ):
                if existing.checksum_sha256 != computed_checksum:
                    raise _mobile_error(
                        status_code=status.HTTP_409_CONFLICT,
                        error_code="GAIA_CONFLICT_ERROR",
                        message="client_attachment_id gia presente con file diverso",
                        details={"field": "client_attachment_id"},
                    )
                return MobileSyncAttachmentUploadResponse(
                    attachment_id=existing.id,
                    client_attachment_id=client_attachment_id,
                    original_filename=existing.original_filename,
                    mime_type=existing.mime_type,
                    file_size_bytes=existing.file_size_bytes,
                    checksum_sha256=existing.checksum_sha256 or computed_checksum,
                )

        storage_path = build_storage_path(file.filename or f"{client_attachment_id}")
        Path(storage_path).parent.mkdir(parents=True, exist_ok=True)
        Path(storage_path).write_bytes(file_bytes)

        attachment = create_attachment_record(
            db,
            storage_path=str(storage_path),
            filename=file.filename or f"{client_attachment_id}",
            mime_type=file.content_type or "application/octet-stream",
            file_size=len(file_bytes),
            source_context="mobile_sync_attachment",
            checksum=computed_checksum,
        )
        attachment.metadata_json = {
            "client_attachment_id": str(client_attachment_id),
            "operator_id": str(operator.id),
            "device_id": device_id,
            "upload_origin": "gaia_mobile_connector",
        }
        db.commit()
        db.refresh(attachment)
        return MobileSyncAttachmentUploadResponse(
            attachment_id=attachment.id,
            client_attachment_id=client_attachment_id,
            original_filename=attachment.original_filename,
            mime_type=attachment.mime_type,
            file_size_bytes=attachment.file_size_bytes,
            checksum_sha256=attachment.checksum_sha256 or computed_checksum,
        )
    except MobileSyncAPIError as exc:
        db.rollback()
        return exc.to_response()
    except ValueError as exc:
        db.rollback()
        return _mobile_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="GAIA_VALIDATION_ERROR",
            message=str(exc),
            details={"field": "file"},
        ).to_response()
    except Exception:
        db.rollback()
        logger.exception("Unexpected error while uploading mobile attachment")
        return _mobile_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="GAIA_RETRYABLE_ERROR",
            message="Errore temporaneo durante l'upload allegato",
            retryable=True,
        ).to_response()


@router.get("/connector/handshake", response_model=MobileConnectorHandshakeResponse)
def mobile_connector_handshake() -> MobileConnectorHandshakeResponse:
    return MobileConnectorHandshakeResponse(
        service="gaia-mobile-sync",
        authenticated=True,
        auth_scheme="header_token",
        connector_header=settings.mobile_connector_header_name,
        gaia_version=settings.app_version,
        server_time=_utcnow(),
        capabilities=[
            "mobile_operators.read",
            "catalogs.read",
            "worksets.read",
            "field_reports.create",
            "activity_starts.create",
            "activity_stops.create",
            "teti_fault_work_requests.create",
            "idempotency.client_event_id",
            "idempotency.teti_fault_id",
            "errors.structured",
        ],
    )


@router.get("/mobile-operators", response_model=MobileOperatorsResponse)
def get_mobile_operators(
    db: Annotated[Session, Depends(get_db)],
):
    rows = db.execute(
        select(WCOperator, ApplicationUser, OperatorProfile)
        .join(ApplicationUser, ApplicationUser.id == WCOperator.gaia_user_id)
        .join(OperatorProfile, OperatorProfile.user_id == ApplicationUser.id, isouter=True)
        .where(WCOperator.email.is_not(None))
        .order_by(WCOperator.last_name.asc(), WCOperator.first_name.asc(), WCOperator.email.asc())
    ).all()

    synced_from = _coalesce_datetime(
        *[operator.wc_synced_at for operator, _, _ in rows],
        *[operator.updated_at for operator, _, _ in rows],
    )
    operators = [
        MobileOperatorResponseItem(
            operator_id=operator.id,
            gaia_user_id=str(user.id),
            gaia_operator_profile_id=str(profile.id) if profile else None,
            gaia_username=user.username,
            display_name=_operator_display_name(operator, user),
            email=operator.email or user.email,
            phone=profile.phone if profile else None,
            status="ACTIVE" if operator.enabled and user.is_active else "DISABLED",
            gate_mobile_console_enabled=operator.gate_mobile_console_enabled,
            gate_mobile_console_role=operator.gate_mobile_console_role,
        )
        for operator, user, profile in rows
    ]
    return MobileOperatorsResponse(synced_from_gaia_at=synced_from, operators=operators)


@router.get("/catalogs", response_model=MobileCatalogsResponse)
def get_mobile_catalogs(
    db: Annotated[Session, Depends(get_db)],
):
    activities = db.scalars(
        select(ActivityCatalog)
        .where(ActivityCatalog.is_active == True)
        .order_by(ActivityCatalog.sort_order.asc(), ActivityCatalog.name.asc())
    ).all()
    categories = db.scalars(
        select(FieldReportCategory)
        .where(FieldReportCategory.is_active == True)
        .order_by(FieldReportCategory.sort_order.asc(), FieldReportCategory.name.asc())
    ).all()
    severities = db.scalars(
        select(FieldReportSeverity)
        .where(FieldReportSeverity.is_active == True)
        .order_by(FieldReportSeverity.rank_order.asc(), FieldReportSeverity.name.asc())
    ).all()
    vehicles = db.scalars(
        select(Vehicle)
        .where(Vehicle.is_active == True)
        .order_by(Vehicle.code.asc(), Vehicle.name.asc())
    ).all()
    delivery_points = db.scalars(
        select(CatDeliveryPoint)
        .where(
            CatDeliveryPoint.is_active == True,
            CatDeliveryPoint.has_meter == True,
            func.nullif(func.trim(CatDeliveryPoint.cod_cont), "").is_not(None),
            func.upper(func.trim(CatDeliveryPoint.cod_cont)).notin_(INVALID_MOBILE_METER_CODES),
        )
        .order_by(CatDeliveryPoint.distretto_code.asc(), CatDeliveryPoint.punto_consegna_code.asc())
    ).all()
    delivery_point_coordinates = _delivery_point_coordinates(db, list(delivery_points))

    meter_rows = db.scalars(
        select(CatMeterReading)
        .where(CatMeterReading.record_kind == "meter_reading")
        .order_by(CatMeterReading.updated_at.desc(), CatMeterReading.created_at.desc())
    ).all()

    meters_by_point: dict[str, CatMeterReading] = {}
    meters_by_delivery_point: dict[UUID, CatMeterReading] = {}
    for row in meter_rows:
        meters_by_point.setdefault(row.punto_consegna, row)
        if row.delivery_point_id is not None:
            meters_by_delivery_point.setdefault(row.delivery_point_id, row)

    delivery_point_meter_items = [
        _delivery_point_payload(
            point,
            delivery_point_coordinates[point.id],
            meters_by_delivery_point.get(point.id) or meters_by_point.get(point.punto_consegna_code),
        )
        for point in delivery_points
        if point.id in delivery_point_coordinates
    ]
    meters = delivery_point_meter_items

    catalogs = [
        MobileCatalogItem(
            catalog_type="activity_types",
            version=_version_from_items(activities, "updated_at", "created_at"),
            synced_from_gaia_at=_coalesce_datetime(*[item.updated_at for item in activities]),
            payload={
                "items": [
                    {"id": str(item.id), "label": item.name, "code": item.code, "category": item.category}
                    for item in activities
                ]
            },
        ),
        MobileCatalogItem(
            catalog_type="report_types",
            version=_version_from_items(categories, "updated_at", "created_at"),
            synced_from_gaia_at=_coalesce_datetime(*[item.updated_at for item in categories]),
            payload={
                "items": [
                    {
                        "id": _stable_catalog_id(uuid_value=item.id, wc_id=item.wc_id),
                        "gaia_category_id": str(item.id),
                        "wc_id": item.wc_id,
                        "label": item.name,
                        "code": item.code,
                    }
                    for item in categories
                ]
            },
        ),
        MobileCatalogItem(
            catalog_type="report_severities",
            version=_version_from_items(severities, "updated_at", "created_at"),
            synced_from_gaia_at=_coalesce_datetime(*[item.updated_at for item in severities]),
            payload={
                "items": [
                    {
                        "id": str(item.id),
                        "label": item.name,
                        "code": item.code,
                        "rank_order": item.rank_order,
                    }
                    for item in severities
                ]
            },
        ),
        MobileCatalogItem(
            catalog_type="vehicles",
            version=_version_from_items(vehicles, "updated_at", "created_at"),
            synced_from_gaia_at=_coalesce_datetime(*[item.updated_at for item in vehicles]),
            payload={
                "items": [
                    {
                        "id": str(item.id),
                        "label": " · ".join(part for part in [item.code, item.name, item.plate_number] if part),
                        "code": item.code,
                        "name": item.name,
                        "plate": item.plate_number,
                        "status": item.current_status,
                    }
                    for item in vehicles
                ]
            },
        ),
        MobileCatalogItem(
            catalog_type="meters",
            version=_version_from_items([*delivery_points, *meter_rows], "updated_at", "created_at"),
            synced_from_gaia_at=_coalesce_datetime(*[item.updated_at for item in [*delivery_points, *meter_rows]]),
            payload={"items": meters},
        ),
    ]
    return MobileCatalogsResponse(catalogs=catalogs)


@router.get("/worksets", response_model=MobileWorksetsResponse)
def get_mobile_worksets(
    db: Annotated[Session, Depends(get_db)],
    operator_id: UUID | None = Query(None),
):
    operator_query = select(WCOperator).where(WCOperator.gaia_user_id.is_not(None))
    if operator_id is not None:
        operator_query = operator_query.where(WCOperator.id == operator_id)
    operators = db.scalars(operator_query.order_by(WCOperator.last_name.asc(), WCOperator.first_name.asc())).all()

    if not operators:
        return MobileWorksetsResponse(worksets=[])

    now = _utcnow()
    operator_ids = [item.id for item in operators]
    user_ids = [item.gaia_user_id for item in operators if item.gaia_user_id is not None]

    memberships = db.scalars(
        select(TeamMembership).where(
            TeamMembership.user_id.in_(user_ids),
            TeamMembership.valid_from <= now,
            or_(TeamMembership.valid_to.is_(None), TeamMembership.valid_to >= now),
        )
    ).all() if user_ids else []
    team_ids = sorted({membership.team_id for membership in memberships})
    team_lookup = {
        item.id: item
        for item in db.scalars(select(Team).where(Team.id.in_(team_ids))).all()
    } if team_ids else {}
    teams_by_user_id: dict[int, list[Team]] = {}
    for membership in memberships:
        team = team_lookup.get(membership.team_id)
        if team is not None:
            teams_by_user_id.setdefault(membership.user_id, []).append(team)

    activities = db.scalars(
        select(OperatorActivity).where(OperatorActivity.operator_user_id.in_(user_ids))
    ).all() if user_ids else []
    catalog_lookup = {
        item.id: item
        for item in db.scalars(select(ActivityCatalog).where(ActivityCatalog.id.in_({a.activity_catalog_id for a in activities}))).all()
    } if activities else {}
    vehicle_ids = {activity.vehicle_id for activity in activities if activity.vehicle_id is not None}

    active_assignments = db.scalars(
        select(VehicleAssignment).where(
            or_(VehicleAssignment.end_at.is_(None), VehicleAssignment.end_at >= now)
        )
    ).all()
    vehicle_ids.update({assignment.vehicle_id for assignment in active_assignments})

    vehicle_lookup = {
        item.id: item
        for item in db.scalars(select(Vehicle).where(Vehicle.id.in_(vehicle_ids))).all()
    } if vehicle_ids else {}

    vehicle_assignments_by_user: dict[int, list[Vehicle]] = {}
    vehicle_assignments_by_team: dict[UUID, list[Vehicle]] = {}
    for assignment in active_assignments:
        vehicle = vehicle_lookup.get(assignment.vehicle_id)
        if vehicle is None or not vehicle.is_active:
            continue
        if assignment.operator_user_id is not None:
            vehicle_assignments_by_user.setdefault(assignment.operator_user_id, []).append(vehicle)
        if assignment.team_id is not None:
            vehicle_assignments_by_team.setdefault(assignment.team_id, []).append(vehicle)

    meters = db.scalars(
        select(CatMeterReading)
        .where(cast(CatMeterReading.mobile_operator_id, String).in_([str(item) for item in operator_ids]))
        .order_by(CatMeterReading.updated_at.desc())
    ).all() if operator_ids else []
    meters_by_operator: dict[str, list[CatMeterReading]] = {}
    for meter in meters:
        if meter.mobile_operator_id:
            meters_by_operator.setdefault(meter.mobile_operator_id, []).append(meter)

    worksets: list[MobileWorksetResponseItem] = []
    for operator in operators:
        if operator.gaia_user_id is None:
            continue
        user_teams = teams_by_user_id.get(operator.gaia_user_id, [])
        team_ids_for_user = {team.id for team in user_teams}
        user_activities = [item for item in activities if item.operator_user_id == operator.gaia_user_id]
        assigned_activities = [item for item in user_activities if item.status in {"draft", "in_progress", "submitted"}]
        open_activities = [item for item in user_activities if item.status == "in_progress"]

        available_vehicles_map: dict[UUID, Vehicle] = {}
        for vehicle in vehicle_assignments_by_user.get(operator.gaia_user_id, []):
            available_vehicles_map[vehicle.id] = vehicle
        for team_id_value in team_ids_for_user:
            for vehicle in vehicle_assignments_by_team.get(team_id_value, []):
                available_vehicles_map[vehicle.id] = vehicle
        for vehicle in vehicle_lookup.values():
            if vehicle.is_active and vehicle.current_status == "available":
                available_vehicles_map.setdefault(vehicle.id, vehicle)

        operator_meters = meters_by_operator.get(str(operator.id), [])

        worksets.extend(
            [
                MobileWorksetResponseItem(
                    operator_id=operator.id,
                    workset_type="assigned_activities",
                    synced_from_gaia_at=_coalesce_datetime(*[item.updated_at for item in assigned_activities]),
                    items=[
                        _activity_payload_item(item, catalog_lookup, team_lookup, vehicle_lookup)
                        for item in assigned_activities
                    ],
                ),
                MobileWorksetResponseItem(
                    operator_id=operator.id,
                    workset_type="open_activities",
                    synced_from_gaia_at=_coalesce_datetime(*[item.updated_at for item in open_activities]),
                    items=[
                        _activity_payload_item(item, catalog_lookup, team_lookup, vehicle_lookup)
                        for item in open_activities
                    ],
                ),
                MobileWorksetResponseItem(
                    operator_id=operator.id,
                    workset_type="assigned_teams",
                    synced_from_gaia_at=_coalesce_datetime(*[item.updated_at for item in user_teams]),
                    items=[_team_payload_item(item) for item in user_teams],
                ),
                MobileWorksetResponseItem(
                    operator_id=operator.id,
                    workset_type="available_vehicles",
                    synced_from_gaia_at=_coalesce_datetime(*[item.updated_at for item in available_vehicles_map.values()]),
                    items=[_vehicle_payload_item(item) for item in available_vehicles_map.values()],
                ),
                MobileWorksetResponseItem(
                    operator_id=operator.id,
                    workset_type="assigned_meters",
                    synced_from_gaia_at=_coalesce_datetime(*[item.updated_at for item in operator_meters]),
                    items=[_meter_payload_item(item) for item in operator_meters],
                ),
            ]
        )

    return MobileWorksetsResponse(worksets=worksets)


@router.post("/field-reports", response_model=MobileSyncApplyResponse, status_code=status.HTTP_201_CREATED)
def create_mobile_field_report(
    data: MobileFieldReportRequest,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        existing = _resolve_mobile_event(
            db,
            client_event_id=data.client_event_id,
            event_type="FIELD_REPORT_CREATED",
            payload_hash=data.payload_hash,
        )
        if existing is not None:
            return _serialize_response(existing)

        operator, user, _ = _resolve_mobile_operator(db, data.operator_id)
        category = _resolve_report_category(db, data.payload.category_id)
        severity = _resolve_report_severity(db, data.payload.severity_id)
        uploaded_attachments = _fetch_mobile_uploaded_attachments(
            db,
            operator_id=operator.id,
            attachments=data.attachments,
        )

        linked_activity_id = data.payload.linked_gaia_activity_id
        if linked_activity_id is not None and db.get(OperatorActivity, linked_activity_id) is None:
            raise _mobile_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="GAIA_VALIDATION_ERROR",
                message="Attivita collegata non trovata",
                details={"field": "linked_gaia_activity_id"},
            )

        gps = data.payload.gps_position or data.payload.gps_point
        report = FieldReport(
            report_number=_build_activity_number("REP", db, FieldReport),
            reporter_user_id=user.id,
            category_id=category.id,
            severity_id=severity.id,
            title=data.payload.title,
            description=data.payload.description,
            reporter_name=_operator_display_name(operator, user),
            operator_activity_id=linked_activity_id,
            latitude=Decimal(str(gps.lat)) if gps else None,
            longitude=Decimal(str(gps.lng)) if gps else None,
            gps_accuracy_meters=Decimal(str(gps.accuracy_m)) if gps and gps.accuracy_m is not None else None,
            gps_source="mobile",
            source_system="gaia_mobile",
            offline_client_uuid=data.client_event_id,
            client_created_at=data.payload.occurred_at_device,
            server_received_at=_utcnow(),
            created_by_user_id=user.id,
            status="submitted",
        )
        db.add(report)
        db.flush()

        case = InternalCase(
            case_number=_build_activity_number("CAS", db, InternalCase),
            source_report_id=report.id,
            title=report.title,
            description=report.description,
            category_id=report.category_id,
            severity_id=report.severity_id,
            created_by_user_id=user.id,
        )
        db.add(case)
        db.flush()

        report.internal_case_id = case.id
        report.status = "linked"

        db.add(
            InternalCaseEvent(
                internal_case_id=case.id,
                event_type="created",
                event_at=_utcnow(),
                actor_user_id=user.id,
                note="Pratica creata automaticamente da segnalazione mobile",
                payload_json={"attachments": [item.model_dump(mode="json") for item in data.attachments]},
            )
        )
        _link_report_attachments(
            db,
            report=report,
            case=case,
            attachments=uploaded_attachments,
            actor_user_id=user.id,
        )

        mobile_event = _create_mobile_event(
            db,
            client_event_id=data.client_event_id,
            event_type="FIELD_REPORT_CREATED",
            operator_id=operator.id,
            device_id=str(data.device_id),
            payload_version=data.payload_version,
            payload_hash=data.payload_hash,
            cloud_event_id=None,
            external_reference=None,
            gaia_entity_type="field_report",
            gaia_entity_id=str(report.id),
            source_entity_id=report.id,
            payload_json=data.model_dump(mode="json"),
            result_json={"gaia_case_id": str(case.id)},
        )
        db.commit()
        db.refresh(mobile_event)
        return _serialize_response(mobile_event)
    except MobileSyncAPIError as exc:
        db.rollback()
        return exc.to_response()
    except Exception:
        db.rollback()
        logger.exception("Unexpected error while creating mobile field report")
        return _mobile_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="GAIA_RETRYABLE_ERROR",
            message="Errore temporaneo durante la creazione della segnalazione",
            retryable=True,
        ).to_response()


@router.post("/activity-starts", response_model=MobileSyncApplyResponse, status_code=status.HTTP_201_CREATED)
def create_mobile_activity_start(
    data: MobileActivityStartRequest,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        existing = _resolve_mobile_event(
            db,
            client_event_id=data.client_event_id,
            event_type="ACTIVITY_START_REQUESTED",
            payload_hash=data.payload_hash,
        )
        if existing is not None:
            return _serialize_response_with_status(existing, status_value="already_exists")

        operator, user, _ = _resolve_mobile_operator(db, data.operator_id)
        catalog = db.get(ActivityCatalog, data.payload.activity_catalog_id)
        if catalog is None or not catalog.is_active:
            raise _mobile_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="GAIA_VALIDATION_ERROR",
                message="Catalogo attivita non valido",
                details={"field": "activity_catalog_id"},
            )
        if data.payload.team_id is not None and db.get(Team, data.payload.team_id) is None:
            raise _mobile_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="GAIA_VALIDATION_ERROR",
                message="Squadra non trovata",
                details={"field": "team_id"},
            )
        if data.payload.vehicle_id is not None:
            vehicle = db.get(Vehicle, data.payload.vehicle_id)
            if vehicle is None or not vehicle.is_active:
                raise _mobile_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    error_code="GAIA_VALIDATION_ERROR",
                    message="Mezzo non valido",
                    details={"field": "vehicle_id"},
                )
        delivery_point = None
        if data.payload.delivery_point_id is not None:
            delivery_point = db.get(CatDeliveryPoint, data.payload.delivery_point_id)
            if delivery_point is None or not delivery_point.is_active:
                raise _mobile_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    error_code="GAIA_VALIDATION_ERROR",
                    message="Punto di consegna non valido",
                    details={"field": "delivery_point_id"},
                )

        gps = data.payload.gps_start
        resolved_attachments = _resolve_mobile_attachments(
            db,
            operator_id=operator.id,
            device_id=str(data.device_id),
            attachments=data.attachments,
        )
        activity = OperatorActivity(
            activity_catalog_id=data.payload.activity_catalog_id,
            operator_user_id=user.id,
            team_id=data.payload.team_id,
            vehicle_id=data.payload.vehicle_id,
            status="in_progress",
            started_at=data.payload.started_at_device,
            start_latitude=Decimal(str(gps.lat)) if gps else None,
            start_longitude=Decimal(str(gps.lng)) if gps else None,
            text_note=data.payload.notes,
            offline_client_uuid=data.client_event_id,
            client_created_at=data.payload.started_at_device,
            server_received_at=_utcnow(),
            created_by_user_id=user.id,
        )
        db.add(activity)
        db.flush()

        db.add(
            OperatorActivityEvent(
                operator_activity_id=activity.id,
                event_type="started",
                event_at=activity.started_at,
                actor_user_id=user.id,
                payload_json=data.model_dump(mode="json"),
            )
        )
        _link_activity_attachments(
            db,
            activity=activity,
            attachments=resolved_attachments,
        )

        meter_reading = None
        if (
            data.payload.delivery_point_id is not None
            or data.payload.meter_number is not None
            or data.payload.meter_reading_value is not None
        ):
            meter_reading = _build_mobile_meter_reading(
                operator=operator,
                activity=activity,
                data=data,
                attachments=resolved_attachments,
                delivery_point=delivery_point,
            )
            db.add(meter_reading)
            db.flush()

        mobile_event = _create_mobile_event(
            db,
            client_event_id=data.client_event_id,
            event_type="ACTIVITY_START_REQUESTED",
            operator_id=operator.id,
            device_id=str(data.device_id),
            payload_version=data.payload_version,
            payload_hash=data.payload_hash,
            cloud_event_id=None,
            external_reference=None,
            gaia_entity_type="activity",
            gaia_entity_id=str(activity.id),
            source_entity_id=activity.id,
            payload_json=data.model_dump(mode="json"),
            result_json={"meter_reading_id": str(meter_reading.id)} if meter_reading is not None else None,
        )
        db.commit()
        db.refresh(mobile_event)
        return _serialize_response(mobile_event)
    except MobileSyncAPIError as exc:
        db.rollback()
        return exc.to_response()
    except Exception:
        db.rollback()
        logger.exception("Unexpected error while creating mobile activity start")
        return _mobile_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="GAIA_RETRYABLE_ERROR",
            message="Errore temporaneo durante l'avvio attivita",
            retryable=True,
        ).to_response()


@router.post("/activity-stops", response_model=MobileSyncApplyResponse, status_code=status.HTTP_201_CREATED)
def create_mobile_activity_stop(
    data: MobileActivityStopRequest,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        existing = _resolve_mobile_event(
            db,
            client_event_id=data.client_event_id,
            event_type="ACTIVITY_STOP_REQUESTED",
            payload_hash=data.payload_hash,
        )
        if existing is not None:
            return _serialize_response(existing)

        operator, user, _ = _resolve_mobile_operator(db, data.operator_id)

        activity = None
        if data.payload.gaia_activity_id is not None:
            activity = db.get(OperatorActivity, data.payload.gaia_activity_id)
        if activity is None and data.payload.client_started_event_id is not None:
            start_event = db.scalar(
                select(MobileSyncEvent).where(
                    MobileSyncEvent.client_event_id == data.payload.client_started_event_id,
                    MobileSyncEvent.event_type == "ACTIVITY_START_REQUESTED",
                )
            )
            if start_event is not None:
                try:
                    activity = db.get(OperatorActivity, UUID(start_event.gaia_entity_id))
                except ValueError:
                    activity = None
        if activity is None:
            raise _mobile_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="GAIA_VALIDATION_ERROR",
                message="Attivita da chiudere non trovata",
                details={"field": "gaia_activity_id"},
            )
        if activity.operator_user_id != user.id:
            raise _mobile_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="GAIA_VALIDATION_ERROR",
                message="Attivita non valida per l'operatore",
                details={"field": "gaia_activity_id"},
            )
        if activity.status != "in_progress":
            raise _mobile_error(
                status_code=status.HTTP_409_CONFLICT,
                error_code="GAIA_CONFLICT_ERROR",
                message="Attivita non in corso",
                details={"field": "gaia_activity_id"},
            )

        gps = data.payload.gps_end
        activity.ended_at = data.payload.stopped_at_device
        activity.end_latitude = Decimal(str(gps.lat)) if gps else None
        activity.end_longitude = Decimal(str(gps.lng)) if gps else None
        activity.status = "submitted"
        if data.payload.notes:
            activity.text_note = "\n".join(part for part in [activity.text_note, data.payload.notes] if part)
        if activity.started_at and activity.ended_at:
            activity.duration_minutes_calculated = math.floor(
                (_normalize_datetime(activity.ended_at) - _normalize_datetime(activity.started_at)).total_seconds() / 60
            )

        db.add(
            OperatorActivityEvent(
                operator_activity_id=activity.id,
                event_type="stopped",
                event_at=data.payload.stopped_at_device,
                actor_user_id=user.id,
                payload_json=data.model_dump(mode="json"),
                notes=data.payload.notes,
            )
        )

        mobile_event = _create_mobile_event(
            db,
            client_event_id=data.client_event_id,
            event_type="ACTIVITY_STOP_REQUESTED",
            operator_id=operator.id,
            device_id=str(data.device_id),
            payload_version=data.payload_version,
            payload_hash=data.payload_hash,
            cloud_event_id=None,
            external_reference=None,
            gaia_entity_type="activity",
            gaia_entity_id=str(activity.id),
            source_entity_id=activity.id,
            payload_json=data.model_dump(mode="json"),
        )
        db.commit()
        db.refresh(mobile_event)
        return _serialize_response(mobile_event)
    except MobileSyncAPIError as exc:
        db.rollback()
        return exc.to_response()
    except Exception:
        db.rollback()
        logger.exception("Unexpected error while creating mobile activity stop")
        return _mobile_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="GAIA_RETRYABLE_ERROR",
            message="Errore temporaneo durante la chiusura attivita",
            retryable=True,
        ).to_response()


@router.post(
    "/teti/fault-work-requests",
    response_model=MobileSyncApplyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_mobile_teti_fault_work_request(
    data: MobileTetiFaultWorkRequest,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        existing = _resolve_mobile_event(
            db,
            client_event_id=data.client_event_id,
            event_type="TETI_FAULT_WORK_REQUESTED",
            payload_hash=data.payload_hash,
            conflict_error_code="GAIA_CONFLICT",
        )
        if existing is not None:
            return _serialize_response_with_status(existing, status_value="already_exists")

        existing_by_fault = _resolve_mobile_event_by_external_reference(
            db,
            event_type="TETI_FAULT_WORK_REQUESTED",
            external_reference=data.teti_fault_id,
            payload_hash=data.payload_hash,
        )
        if existing_by_fault is not None:
            return _serialize_response_with_status(existing_by_fault, status_value="already_exists")

        operator, user, _ = _resolve_mobile_operator(db, data.operator_id)
        category = _resolve_teti_category(db)
        severity = _resolve_teti_severity(db, data.payload.severity)
        uploaded_attachments = _fetch_mobile_uploaded_attachments(
            db,
            operator_id=operator.id,
            attachments=data.attachments,
        )

        report = FieldReport(
            report_number=_build_activity_number("REP", db, FieldReport),
            external_code=data.teti_fault_id[:50],
            reporter_user_id=user.id,
            category_id=category.id,
            severity_id=severity.id,
            title=data.payload.title,
            description=data.payload.description,
            reporter_name=_operator_display_name(operator, user),
            area_code=str(data.payload.plant_id),
            latitude=Decimal(str(data.payload.latitude)) if data.payload.latitude is not None else None,
            longitude=Decimal(str(data.payload.longitude)) if data.payload.longitude is not None else None,
            source_system="gaia_mobile_teti",
            gps_source="mobile_teti" if data.payload.latitude is not None and data.payload.longitude is not None else None,
            offline_client_uuid=data.client_event_id,
            server_received_at=_utcnow(),
            created_by_user_id=user.id,
            status="submitted",
        )
        db.add(report)
        db.flush()

        metadata_payload = {
            "source": "teti_fault",
            "teti_fault_id": data.teti_fault_id,
            "cloud_event_id": str(data.cloud_event_id),
            "plant_id": str(data.payload.plant_id),
            "asset_id": str(data.payload.asset_id) if data.payload.asset_id else None,
            "severity": data.payload.severity,
            "attachments": [item.model_dump(mode="json") for item in data.attachments],
        }
        case = InternalCase(
            case_number=_build_activity_number("CAS", db, InternalCase),
            source_report_id=report.id,
            title=report.title,
            description=report.description,
            category_id=report.category_id,
            severity_id=report.severity_id,
            created_by_user_id=user.id,
            priority_rank=severity.rank_order,
        )
        db.add(case)
        db.flush()

        report.internal_case_id = case.id
        report.status = "linked"

        db.add(
            InternalCaseEvent(
                internal_case_id=case.id,
                event_type="teti_fault_imported",
                event_at=_utcnow(),
                actor_user_id=user.id,
                note="Pratica creata automaticamente da fault TETI via mobile-sync",
                payload_json=metadata_payload,
            )
        )
        _link_report_attachments(
            db,
            report=report,
            case=case,
            attachments=uploaded_attachments,
            actor_user_id=user.id,
        )

        result_json = {
            "status": "created",
            "teti_fault_id": data.teti_fault_id,
            "gaia_case_id": str(case.id),
            "plant_id": str(data.payload.plant_id),
            "asset_id": str(data.payload.asset_id) if data.payload.asset_id else None,
        }
        mobile_event = _create_mobile_event(
            db,
            client_event_id=data.client_event_id,
            event_type="TETI_FAULT_WORK_REQUESTED",
            operator_id=operator.id,
            device_id=str(data.device_id),
            payload_version=data.payload_version,
            payload_hash=data.payload_hash,
            cloud_event_id=data.cloud_event_id,
            external_reference=data.teti_fault_id,
            gaia_entity_type="gaia_work",
            gaia_entity_id=str(case.id),
            source_entity_id=case.id,
            payload_json=data.model_dump(mode="json", by_alias=True),
            result_json=result_json,
        )
        logger.info(
            "Created TETI fault work request",
            extra={
                "client_event_id": str(data.client_event_id),
                "cloud_event_id": str(data.cloud_event_id),
                "teti_fault_id": data.teti_fault_id,
                "gaia_case_id": str(case.id),
                "gaia_report_id": str(report.id),
                "operator_id": str(operator.id),
            },
        )
        db.commit()
        db.refresh(mobile_event)
        return _serialize_response(mobile_event)
    except MobileSyncAPIError as exc:
        db.rollback()
        return exc.to_response()
    except Exception:
        db.rollback()
        logger.exception("Unexpected error while creating TETI fault work request")
        return _mobile_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="GAIA_RETRYABLE_ERROR",
            message="Errore temporaneo durante la creazione dell'intervento TETI",
            retryable=True,
        ).to_response()
