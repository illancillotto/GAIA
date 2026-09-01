from __future__ import annotations

import re
import tempfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.gis.models import GisLayer
from app.modules.gis.qgis_project import build_xml as _build_qgis_project_xml
from app.modules.gis.qgis_project import is_project_layer as _is_qgis_project_layer
from app.modules.gis.qgis_project import layer_id as _qgis_layer_id

PROJECT_FILENAME = "gaia-gis-platform.qgs"
SERVICE_FILENAME = "pg_service.conf"
SERVICE_NAME = "gaia_gis_server"
ROLE_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def _service_layer_name(layer: GisLayer) -> str:
    return f"{layer.workspace}__{layer.name}".replace("-", "_")


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _reader_role() -> tuple[str, str]:
    username = settings.gis_qgis_server_db_username.strip()
    password = settings.gis_qgis_server_db_password
    if not ROLE_PATTERN.fullmatch(username):
        raise RuntimeError("GIS QGIS Server database username is invalid")
    if not password:
        raise RuntimeError("GIS QGIS Server database password is not configured")
    return username, password


def _publishable_layers(db: Session) -> list[GisLayer]:
    layers = db.scalars(
        select(GisLayer)
        .where(GisLayer.is_active.is_(True), GisLayer.source_type == "postgis")
        .order_by(GisLayer.workspace.asc(), GisLayer.title.asc(), GisLayer.name.asc())
    ).all()
    return [layer for layer in layers if _is_qgis_project_layer(layer)]


def _provision_reader(db: Session, layers: list[GisLayer]) -> str:
    username, password = _reader_role()
    role = _quote_identifier(username)
    role_exists = db.scalar(
        text("SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :role)"),
        {"role": username},
    )
    if not role_exists:
        db.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD {_quote_literal(password)}"))
    db.execute(
        text(
            f"ALTER ROLE {role} WITH LOGIN PASSWORD {_quote_literal(password)} "
            "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
        )
    )
    database_name = make_url(settings.database_url).database
    if database_name:
        db.execute(
            text(f"GRANT CONNECT ON DATABASE {_quote_identifier(database_name)} TO {role}")
        )
    for schema_name in sorted({layer.postgis_schema or "public" for layer in layers}):
        db.execute(
            text(f"GRANT USAGE ON SCHEMA {_quote_identifier(schema_name)} TO {role}")
        )
    for layer in layers:
        schema_name = _quote_identifier(layer.postgis_schema or "public")
        table_name = _quote_identifier(layer.postgis_table or layer.name)
        db.execute(text(f"GRANT SELECT ON TABLE {schema_name}.{table_name} TO {role}"))
    db.commit()
    return username


def _service_value(value: object) -> str:
    normalized = str(value)
    if "\n" in normalized or "\r" in normalized:
        raise RuntimeError("GIS QGIS Server service value contains a newline")
    return normalized


def _server_service_config() -> bytes:
    username, password = _reader_role()
    url = make_url(settings.database_url)
    values = {
        "host": url.host or "postgres",
        "port": url.port or 5432,
        "dbname": url.database or "",
        "user": username,
        "password": password,
        "sslmode": "prefer",
    }
    lines = [f"[{SERVICE_NAME}]"]
    lines.extend(f"{key}={_service_value(value)}" for key, value in values.items())
    return ("\n".join(lines) + "\n").encode()


def _add_service_short_names(root: ET.Element, layers: list[GisLayer]) -> None:
    layers_by_id = {_qgis_layer_id(layer): layer for layer in layers}
    for map_layer in root.findall("./projectlayers/maplayer"):
        layer = layers_by_id.get(map_layer.findtext("id") or "")
        if layer is not None:
            ET.SubElement(map_layer, "shortname").text = _service_layer_name(layer)


def _replace_project_connection(root: ET.Element) -> None:
    for datasource in root.iter("datasource"):
        datasource.text = (datasource.text or "").replace(
            "service='gaia_gis'", f"service='{SERVICE_NAME}'"
        )


def _configure_read_only_wfs(root: ET.Element) -> None:
    properties = root.find("properties")
    if properties is None:
        raise RuntimeError("Generated QGIS project has no properties section")
    wfs_layers = ET.SubElement(properties, "WFSLayers", attrib={"type": "QStringList"})
    for map_layer in root.findall("./projectlayers/maplayer"):
        layer_id = map_layer.findtext("id")
        if layer_id:
            ET.SubElement(wfs_layers, "value").text = layer_id
    wfst_layers = ET.SubElement(properties, "WFSTLayers")
    for operation in ("Insert", "Update", "Delete"):
        ET.SubElement(wfst_layers, operation, attrib={"type": "QStringList"})


def _server_project_xml(layers: list[GisLayer], generated_at: datetime) -> bytes:
    root = ET.fromstring(_build_qgis_project_xml(layers, generated_at))
    _add_service_short_names(root, layers)
    _replace_project_connection(root)
    _configure_read_only_wfs(root)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _atomic_write(path: Path, content: bytes, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary_path = Path(handle.name)
        handle.write(content)
    temporary_path.chmod(mode)
    temporary_path.replace(path)


def bootstrap_qgis_server(db: Session) -> int:
    layers = _publishable_layers(db)
    if not layers:
        raise RuntimeError("No QGIS Server publishable layers are available")
    _provision_reader(db, layers)
    project_dir = Path(settings.gis_qgis_server_project_dir)
    _atomic_write(
        project_dir / PROJECT_FILENAME,
        _server_project_xml(layers, datetime.now(UTC)),
        mode=0o600,
    )
    _atomic_write(
        project_dir / SERVICE_FILENAME,
        _server_service_config(),
        mode=0o600,
    )
    return len(layers)


def main() -> None:
    db = SessionLocal()
    try:
        layer_count = bootstrap_qgis_server(db)
        print(f"QGIS Server project ready: {layer_count} layer(s)")
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover - exercised as a container entrypoint
    main()
