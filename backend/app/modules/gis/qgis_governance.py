from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from app.modules.gis.models import GisLayer


QGIS_SCHEMA = "gis_qgis"
QGIS_READER_ROLE = "gaia_gis_qgis_reader"
QGIS_EDITOR_ROLE = "gaia_gis_qgis_editor"
QGIS_ADMIN_ROLE = "gaia_gis_qgis_admin"


@dataclass(frozen=True)
class QgisLayerGrant:
    layer_id: str
    workspace: str
    layer_name: str
    source_table: str
    view_name: str
    read_role: str
    edit_role: str | None
    editable: bool
    edit_reason: str


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")
    return cleaned or "layer"


def _view_name(layer: GisLayer) -> str:
    base = _slug(f"{layer.workspace}__{layer.name}")
    digest = hashlib.sha1(f"{layer.workspace}:{layer.name}".encode("utf-8")).hexdigest()[:8]
    return f"{base[:54]}_{digest}"


def _source_table(layer: GisLayer) -> str:
    schema = layer.postgis_schema or "public"
    table = layer.postgis_table or layer.name
    return f"{_quote_identifier(schema)}.{_quote_identifier(table)}"


def _qgis_metadata(layer: GisLayer) -> dict[str, Any]:
    metadata = layer.metadata_json or {}
    qgis = metadata.get("qgis") if isinstance(metadata, dict) else {}
    return qgis if isinstance(qgis, dict) else {}


def _is_publishable(layer: GisLayer) -> bool:
    return layer.is_active and layer.source_type == "postgis" and bool(layer.postgis_table or layer.name)


def _edit_reason(layer: GisLayer) -> str:
    qgis = _qgis_metadata(layer)
    if layer.workspace == "catasto" or layer.domain_module == "catasto":
        return "catasto_read_only"
    if qgis.get("editable") is not True:
        return "not_opted_in"
    if qgis.get("edit_policy") != "controlled":
        return "missing_controlled_edit_policy"
    return "controlled_edit_enabled"


def _layer_grant(layer: GisLayer) -> QgisLayerGrant:
    reason = _edit_reason(layer)
    editable = reason == "controlled_edit_enabled"
    return QgisLayerGrant(
        layer_id=str(layer.id),
        workspace=layer.workspace,
        layer_name=layer.name,
        source_table=_source_table(layer),
        view_name=_view_name(layer),
        read_role=QGIS_READER_ROLE,
        edit_role=QGIS_EDITOR_ROLE if editable else None,
        editable=editable,
        edit_reason=reason,
    )


def build_qgis_governance(layers: list[GisLayer]) -> dict[str, Any]:
    grants = [_layer_grant(layer) for layer in layers if _is_publishable(layer)]
    statements = [
        f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(QGIS_SCHEMA)};",
        f"CREATE ROLE {_quote_identifier(QGIS_ADMIN_ROLE)} NOLOGIN;",
        f"CREATE ROLE {_quote_identifier(QGIS_READER_ROLE)} NOLOGIN;",
        f"CREATE ROLE {_quote_identifier(QGIS_EDITOR_ROLE)} NOLOGIN;",
        f"GRANT USAGE ON SCHEMA {_quote_identifier(QGIS_SCHEMA)} TO {_quote_identifier(QGIS_READER_ROLE)}, {_quote_identifier(QGIS_EDITOR_ROLE)};",
    ]
    for grant in grants:
        view_identifier = f"{_quote_identifier(QGIS_SCHEMA)}.{_quote_identifier(grant.view_name)}"
        statements.extend(
            [
                f"CREATE OR REPLACE VIEW {view_identifier} AS SELECT * FROM {grant.source_table};",
                f"GRANT SELECT ON {view_identifier} TO {_quote_identifier(QGIS_READER_ROLE)}, {_quote_identifier(QGIS_EDITOR_ROLE)};",
            ]
        )
        if grant.editable:
            statements.append(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {grant.source_table} TO {_quote_identifier(QGIS_EDITOR_ROLE)};"
            )
        else:
            statements.append(f"REVOKE INSERT, UPDATE, DELETE ON TABLE {grant.source_table} FROM {_quote_identifier(QGIS_EDITOR_ROLE)};")
    return {
        "schema": QGIS_SCHEMA,
        "roles": {
            "admin": QGIS_ADMIN_ROLE,
            "reader": QGIS_READER_ROLE,
            "editor": QGIS_EDITOR_ROLE,
        },
        "connection_policy": {
            "default_mode": "read_only",
            "login_roles": "create environment-specific LOGIN roles and grant one of the NOLOGIN group roles",
            "password_rotation": "rotate QGIS login role passwords on staff change or at least every 180 days",
            "nas_shapefile_policy": "export_backup_only",
        },
        "layers": [grant.__dict__ for grant in grants],
        "statements": statements,
        "sql": "\n".join(statements) + "\n",
    }
