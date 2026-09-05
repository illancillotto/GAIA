from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.network.models import (
    DevicePosition,
    FloorPlan,
)
from app.modules.network.router.common import _require_network_module
from app.modules.network.router.helpers.devices import _serialize_device
from app.modules.network.schemas import (
    DevicePositionResponse,
    FloorPlanCreateRequest,
    FloorPlanDetailResponse,
    FloorPlanDeviceResponse,
    FloorPlanResponse,
)
from app.modules.network.services import (
    create_floor_plan,
    get_floor_plan_devices,
)

router = APIRouter()


# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

@router.get("/floor-plans", response_model=list[FloorPlanResponse])
def get_floor_plans(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[FloorPlanResponse]:
    _require_network_module(current_user)
    return [FloorPlanResponse.model_validate(item) for item in db.scalars(select(FloorPlan).order_by(FloorPlan.name.asc())).all()]


@router.post("/floor-plans", response_model=FloorPlanResponse, status_code=status.HTTP_201_CREATED)
def post_floor_plan(
    payload: FloorPlanCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FloorPlanResponse:
    _require_network_module(current_user)
    floor_plan = create_floor_plan(
        db,
        name=payload.name,
        floor_label=payload.floor_label,
        building=payload.building,
        svg_content=payload.svg_content,
        image_url=payload.image_url,
        width=payload.width,
        height=payload.height,
    )
    return FloorPlanResponse.model_validate(floor_plan)


@router.get("/floor-plans/{floor_plan_id}", response_model=FloorPlanDetailResponse)
def get_floor_plan(
    floor_plan_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FloorPlanDetailResponse:
    _require_network_module(current_user)
    floor_plan = db.get(FloorPlan, floor_plan_id)
    if floor_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    payload = FloorPlanResponse.model_validate(floor_plan).model_dump()
    payload["positions"] = [
        DevicePositionResponse.model_validate(position)
        for position in db.scalars(
            select(DevicePosition).where(DevicePosition.floor_plan_id == floor_plan_id).order_by(DevicePosition.id.asc())
        ).all()
    ]
    return FloorPlanDetailResponse(**payload)


@router.get("/floor-plans/{floor_plan_id}/devices", response_model=list[FloorPlanDeviceResponse])
def get_floor_plan_devices_endpoint(
    floor_plan_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[FloorPlanDeviceResponse]:
    _require_network_module(current_user)
    floor_plan = db.get(FloorPlan, floor_plan_id)
    if floor_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    return [
        FloorPlanDeviceResponse(
            position=DevicePositionResponse.model_validate(position),
            device=_serialize_device(device),
        )
        for position, device in get_floor_plan_devices(db, floor_plan_id)
    ]


# fmt: on
