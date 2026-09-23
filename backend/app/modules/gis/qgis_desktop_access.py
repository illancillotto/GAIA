from __future__ import annotations

import secrets
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_user import ApplicationUser
from app.modules.gis.models import GisLayer
from app.modules.gis.qgis_governance import QGIS_SCHEMA, qgis_view_name
from app.modules.gis.qgis_project import is_project_layer

ROLE_PREFIX = "gaia_qgis_u_"


def _is_postgresql(db: Session) -> bool:
    return db.get_bind().dialect.name == "postgresql"


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def role_name(user: ApplicationUser) -> str:
    return f"{ROLE_PREFIX}{user.id}"


def _role_can_login(db: Session, username: str) -> bool | None:
    return db.execute(
        text("SELECT rolcanlogin FROM pg_roles WHERE rolname = :role"),
        {"role": username},
    ).scalar_one_or_none()


def _visible_layers(db: Session, user: ApplicationUser) -> list[GisLayer]:
    from app.modules.gis.services import _permission_flags

    layers = db.scalars(
        select(GisLayer)
        .where(GisLayer.is_active.is_(True), GisLayer.source_type == "postgis")
        .order_by(GisLayer.workspace.asc(), GisLayer.title.asc(), GisLayer.name.asc())
    ).all()
    return [
        layer
        for layer in layers
        if is_project_layer(layer) and _permission_flags(db, layer.id, user)["can_view"]
    ]


def _reconcile_layer_grants(db: Session, user: ApplicationUser, layers: list[GisLayer]) -> None:
    username = role_name(user)
    role = _quote_identifier(username)
    schema = _quote_identifier(QGIS_SCHEMA)
    db.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    for layer in layers:
        source_schema = _quote_identifier(layer.postgis_schema or "public")
        source_table = _quote_identifier(layer.postgis_table or layer.name)
        view = _quote_identifier(qgis_view_name(layer))
        db.execute(
            text(
                f"CREATE OR REPLACE VIEW {schema}.{view} "
                f"AS SELECT * FROM {source_schema}.{source_table}"
            )
        )
    db.execute(text(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema} FROM {role}"))
    if layers:
        db.execute(text(f"GRANT USAGE ON SCHEMA {schema} TO {role}"))
        for layer in layers:
            view = _quote_identifier(qgis_view_name(layer))
            db.execute(text(f"GRANT SELECT ON {schema}.{view} TO {role}"))
    else:
        db.execute(text(f"REVOKE USAGE ON SCHEMA {schema} FROM {role}"))


def access_status(db: Session, user: ApplicationUser) -> dict[str, Any]:
    username = role_name(user)
    if not _is_postgresql(db):
        return {"enabled": False, "username": username, "layer_count": 0}
    role_can_login = _role_can_login(db, username)
    layers = _visible_layers(db, user) if user.module_gis and user.is_active else []
    return {
        "enabled": bool(role_can_login and user.module_gis and user.is_active),
        "username": username,
        "layer_count": len(layers) if role_can_login else 0,
    }


def provision_access(db: Session, user: ApplicationUser) -> dict[str, Any]:
    if not _is_postgresql(db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="L'accesso QGIS Desktop richiede il database PostgreSQL di produzione.",
        )
    if not user.is_active or not user.module_gis:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Abilitare prima l'account e il modulo GIS in GAIA.",
        )
    layers = _visible_layers(db, user)
    if not layers:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="L'utente non ha layer GIS Desktop visibili in GAIA.",
        )

    username = role_name(user)
    role = _quote_identifier(username)
    password = secrets.token_urlsafe(24)
    if _role_can_login(db, username) is None:
        db.execute(text(f"CREATE ROLE {role} WITH LOGIN PASSWORD {_quote_literal(password)}"))
    db.execute(
        text(
            f"ALTER ROLE {role} WITH LOGIN PASSWORD {_quote_literal(password)} "
            "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
        )
    )
    database = make_url(settings.database_url).database
    if database:
        db.execute(text(f"GRANT CONNECT ON DATABASE {_quote_identifier(database)} TO {role}"))
    _reconcile_layer_grants(db, user, layers)
    db.commit()
    return {"enabled": True, "username": username, "password": password, "layer_count": len(layers)}


def disable_access(db: Session, user: ApplicationUser, *, commit: bool = True) -> None:
    if not _is_postgresql(db):
        return
    username = role_name(user)
    role = _quote_identifier(username)
    if _role_can_login(db, username) is None:
        return
    db.execute(text(f"ALTER ROLE {role} NOLOGIN"))
    db.execute(
        text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE usename = :role AND pid <> pg_backend_pid()"
        ),
        {"role": username},
    )
    schema = _quote_identifier(QGIS_SCHEMA)
    db.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    db.execute(text(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema} FROM {role}"))
    db.execute(text(f"REVOKE USAGE ON SCHEMA {schema} FROM {role}"))
    if commit:
        db.commit()


def sync_enabled_users(db: Session) -> None:
    if not _is_postgresql(db):
        return
    users = db.scalars(
        select(ApplicationUser).where(
            ApplicationUser.is_active.is_(True), ApplicationUser.module_gis.is_(True)
        )
    ).all()
    for user in users:
        username = role_name(user)
        if _role_can_login(db, username):
            _reconcile_layer_grants(db, user, _visible_layers(db, user))
