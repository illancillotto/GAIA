from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.gis import qgis_server_bootstrap
from app.modules.gis.models import GisLayer


class ScalarResult:
    def __init__(self, items: list[GisLayer]) -> None:
        self.items = items

    def all(self) -> list[GisLayer]:
        return self.items


class FakeDb:
    def __init__(self, layers: list[GisLayer] | None = None, *, role_exists: bool = False) -> None:
        self.layers = layers or []
        self.role_exists = role_exists
        self.executed: list[tuple[str, dict | None]] = []
        self.committed = False
        self.closed = False

    def scalars(self, query: object) -> ScalarResult:
        return ScalarResult(self.layers)

    def scalar(self, query: object, params: dict) -> bool:
        self.executed.append((str(query), params))
        return self.role_exists

    def execute(self, query: object) -> None:
        self.executed.append((str(query), None))

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


def layer(
    name: str = "rete_condotte", *, schema: str | None = "network"
) -> GisLayer:
    return GisLayer(
        id=uuid4(),
        workspace="rete",
        name=name,
        title=name.replace("_", " ").title(),
        source_type="postgis",
        postgis_schema=schema,
        postgis_table=name,
        geometry_column="geometry",
        geometry_type="MULTILINESTRING",
        srid=4326,
        is_active=True,
        metadata_json={"qgis": {"mode": "read_only"}},
    )


def configure_qgis(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, password: str = "secret"
) -> None:
    monkeypatch.setattr(
        qgis_server_bootstrap.settings,
        "gis_qgis_server_db_username",
        "gaia_gis_qgis_server",
    )
    monkeypatch.setattr(
        qgis_server_bootstrap.settings,
        "gis_qgis_server_db_password",
        password,
    )
    monkeypatch.setattr(
        qgis_server_bootstrap.settings,
        "gis_qgis_server_project_dir",
        str(tmp_path),
    )
    monkeypatch.setattr(
        qgis_server_bootstrap.settings,
        "database_url",
        "postgresql://admin:password@postgres:5432/gaia",
    )


def test_reader_role_requires_safe_username_and_password(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_qgis(monkeypatch, tmp_path)
    monkeypatch.setattr(
        qgis_server_bootstrap.settings,
        "gis_qgis_server_db_username",
        "unsafe-role",
    )
    with pytest.raises(RuntimeError, match="username is invalid"):
        qgis_server_bootstrap._reader_role()

    configure_qgis(monkeypatch, tmp_path, password="")
    with pytest.raises(RuntimeError, match="password is not configured"):
        qgis_server_bootstrap._reader_role()


def test_sql_quoting_helpers_escape_values() -> None:
    assert qgis_server_bootstrap._quote_identifier('a"b') == '"a""b"'
    assert qgis_server_bootstrap._quote_literal("a'b") == "'a''b'"


def test_publishable_layers_are_filtered(monkeypatch: pytest.MonkeyPatch) -> None:
    included = layer("included")
    excluded = layer("excluded")
    db = FakeDb([included, excluded])
    monkeypatch.setattr(
        qgis_server_bootstrap,
        "_is_qgis_project_layer",
        lambda item: item.name == "included",
    )

    assert qgis_server_bootstrap._publishable_layers(db) == [included]


def test_provision_reader_creates_restricted_role_and_grants_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_qgis(monkeypatch, tmp_path, password="s'ecret")
    db = FakeDb(role_exists=False)

    username = qgis_server_bootstrap._provision_reader(
        db, [layer(), layer("public_layer", schema=None)]
    )

    sql = "\n".join(statement for statement, _ in db.executed)
    assert username == "gaia_gis_qgis_server"
    assert "CREATE ROLE" in sql
    assert "s''ecret" in sql
    assert "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION" in sql
    assert 'GRANT CONNECT ON DATABASE "gaia"' in sql
    assert 'GRANT USAGE ON SCHEMA "network"' in sql
    assert 'GRANT USAGE ON SCHEMA "public"' in sql
    assert 'GRANT SELECT ON TABLE "network"."rete_condotte"' in sql
    assert db.committed is True


def test_provision_reader_reuses_existing_role(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_qgis(monkeypatch, tmp_path)
    db = FakeDb(role_exists=True)

    qgis_server_bootstrap._provision_reader(db, [layer()])

    assert not any("CREATE ROLE" in statement for statement, _ in db.executed)
    assert any("ALTER ROLE" in statement for statement, _ in db.executed)


def test_atomic_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_qgis(monkeypatch, tmp_path)
    destination = tmp_path / "nested" / "project.qgs"
    qgis_server_bootstrap._atomic_write(destination, b"project", mode=0o640)
    assert destination.read_bytes() == b"project"
    assert destination.stat().st_mode & 0o777 == 0o640


def test_server_project_embeds_only_the_restricted_connection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_qgis(monkeypatch, tmp_path, password="s'ecret\\value")
    monkeypatch.setattr(
        qgis_server_bootstrap,
        "_build_qgis_project_xml",
        lambda layers, generated_at: (
            b"<QGIS><properties/><projectlayers><maplayer><id>rete-id</id>"
            b"<datasource>service='gaia_gis' table=network.rete_condotte</datasource>"
            b"</maplayer><maplayer><datasource /></maplayer></projectlayers></QGIS>"
        ),
    )

    project = qgis_server_bootstrap._server_project_xml([layer()], SimpleNamespace())
    project_text = project.decode("utf-8")

    assert "service='gaia_gis'" not in project_text
    assert "host='postgres'" in project_text
    assert "user='gaia_gis_qgis_server'" in project_text
    assert "password='s\\'ecret\\\\value'" in project_text
    assert "table=network.rete_condotte" in project_text
    assert "<value>rete-id</value>" in project_text
    assert '<Insert type="QStringList"' in project_text
    assert '<Update type="QStringList"' in project_text
    assert '<Delete type="QStringList"' in project_text


def test_server_project_requires_properties_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_qgis(monkeypatch, tmp_path)
    monkeypatch.setattr(
        qgis_server_bootstrap,
        "_build_qgis_project_xml",
        lambda layers, generated_at: b"<QGIS />",
    )

    with pytest.raises(RuntimeError, match="no properties section"):
        qgis_server_bootstrap._server_project_xml([layer()], SimpleNamespace())


def test_bootstrap_writes_server_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_qgis(monkeypatch, tmp_path)
    db = FakeDb([layer()])
    monkeypatch.setattr(
        qgis_server_bootstrap, "_publishable_layers", lambda current_db: db.layers
    )
    monkeypatch.setattr(
        qgis_server_bootstrap,
        "_provision_reader",
        lambda current_db, layers: "reader",
    )
    monkeypatch.setattr(
        qgis_server_bootstrap,
        "_server_project_xml",
        lambda layers, generated_at: b"<QGIS />",
    )

    assert qgis_server_bootstrap.bootstrap_qgis_server(db) == 1
    assert (tmp_path / qgis_server_bootstrap.PROJECT_FILENAME).read_bytes() == b"<QGIS />"


def test_bootstrap_rejects_empty_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_qgis(monkeypatch, tmp_path)
    db = FakeDb()
    monkeypatch.setattr(qgis_server_bootstrap, "_publishable_layers", lambda db: [])
    with pytest.raises(RuntimeError, match="No QGIS Server publishable layers"):
        qgis_server_bootstrap.bootstrap_qgis_server(db)


def test_main_closes_database_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_qgis(monkeypatch, tmp_path)
    db = FakeDb()
    monkeypatch.setattr(qgis_server_bootstrap, "SessionLocal", lambda: db)
    monkeypatch.setattr(qgis_server_bootstrap, "bootstrap_qgis_server", lambda current_db: 3)

    qgis_server_bootstrap.main()

    assert db.closed is True
    assert capsys.readouterr().out == "QGIS Server project ready: 3 layer(s)\n"
