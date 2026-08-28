from __future__ import annotations

from copy import deepcopy

import pytest
from app.core.database import Base
from app.modules.gis.models import GisLayer, GisLayerPermission
from app.modules.gis.territorio_bootstrap import (
    TERRITORIO_GIS_LAYER_DEFINITIONS,
    ensure_territorio_gis_catalog,
)
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_seed_is_idempotent_and_creates_exact_catalog(db: Session) -> None:
    assert ensure_territorio_gis_catalog(db) == 21
    assert ensure_territorio_gis_catalog(db) == 0

    layers = db.scalars(
        select(GisLayer).where(GisLayer.workspace == "territorio")
    ).all()
    assert len(layers) == 21
    assert {layer.name for layer in layers} == {
        definition["name"] for definition in TERRITORIO_GIS_LAYER_DEFINITIONS
    }
    assert {layer.metadata_json["theme"] for layer in layers} == {
        "bonifica",
        "colture",
        "vincoli",
        "idrografia",
        "amministrativo",
        "eventi",
        "catasto_ufficiale",
        "ortofoto",
        "morfologia",
    }


@pytest.mark.parametrize("missing", ["license", "attribution"])
def test_seed_rejects_missing_legal_metadata(db: Session, missing: str) -> None:
    definition = deepcopy(TERRITORIO_GIS_LAYER_DEFINITIONS[0])
    definition[missing] = ""

    with pytest.raises(ValueError, match="Invalid territorio layer definition"):
        ensure_territorio_gis_catalog(db, (definition,))


def test_seed_applies_read_only_policy_and_viewer_permissions(db: Session) -> None:
    ensure_territorio_gis_catalog(db)
    layers = db.scalars(select(GisLayer)).all()
    permissions = db.scalars(select(GisLayerPermission)).all()

    assert len(permissions) == len(layers)
    assert all(permission.principal_key == "viewer" for permission in permissions)
    assert all(permission.can_view for permission in permissions)
    assert all(not permission.can_edit for permission in permissions)
    assert all(layer.source_type == "wms_external" for layer in layers)
    assert all(layer.metadata_json["export"]["shapefile"] is False for layer in layers)
    assert all(
        layer.metadata_json["qgis"]["mode"] == "not_published" for layer in layers
    )
    assert all(
        layer.metadata_json["external"]["license"] == "CC BY 4.0" for layer in layers
    )


def test_seed_preserves_governance_descriptions(db: Session) -> None:
    ensure_territorio_gis_catalog(db)
    districts = db.scalar(
        select(GisLayer).where(GisLayer.name == "ras_distretti_irrigui")
    )
    rivers = db.scalar(select(GisLayer).where(GisLayer.name == "ras_fascia_150m_fiumi"))

    assert (
        districts is not None
        and "fonte autorevole per il distretto resta GAIA" in districts.description
    )
    assert (
        rivers is not None
        and "dichiarato indicativo dalla sorgente" in rivers.description
    )
