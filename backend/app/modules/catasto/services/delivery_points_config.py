from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatDeliveryPointsImportConfig
from app.modules.catasto.services.delivery_points_import import (
    POINT_FOLDER_WITH_METER,
    POINT_FOLDER_WITHOUT_METER,
    import_delivery_points_2026_def,
)


def get_or_create_delivery_points_import_config(db: Session) -> CatDeliveryPointsImportConfig:
    config = db.get(CatDeliveryPointsImportConfig, 1)
    if config is not None:
        return config
    config = CatDeliveryPointsImportConfig(id=1)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def update_delivery_points_import_config(
    db: Session,
    *,
    root_path: str | None,
    current_user: ApplicationUser | None,
) -> CatDeliveryPointsImportConfig:
    config = get_or_create_delivery_points_import_config(db)
    if root_path and root_path.strip():
        stripped_path = root_path.strip()
        normalized_path = (
            stripped_path
            if stripped_path.lower().startswith("smb://")
            else str(Path(stripped_path).expanduser())
        )
    else:
        normalized_path = None
    config.root_path = normalized_path
    config.updated_by = current_user.username if current_user is not None else "system"
    db.commit()
    db.refresh(config)
    return config


def run_delivery_points_import_from_config(db: Session) -> tuple[CatDeliveryPointsImportConfig, dict[str, int]]:
    config = get_or_create_delivery_points_import_config(db)
    if not config.root_path:
        raise ValueError("Cartella sorgente NAS non configurata.")
    stats = import_delivery_points_2026_def(db, root_path=config.root_path)
    return config, stats


def config_metadata(config: CatDeliveryPointsImportConfig) -> dict[str, str | None]:
    return {
        "root_path": config.root_path,
        "expected_with_meter_dir": POINT_FOLDER_WITH_METER,
        "expected_without_meter_dir": POINT_FOLDER_WITHOUT_METER,
        "updated_by": config.updated_by,
    }
