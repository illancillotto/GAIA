from __future__ import annotations

import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import HTTPException, WebSocketException

import logging

from app.core.datetime_compat import UTC
from app.core.database import get_db
from app.core.logging import configure_logging
from app.core.security import (
    create_access_token,
    create_action_token,
    decode_access_token,
    decode_action_token,
    hash_password,
    verify_password,
)
from app.modules.catasto.services.dashboard_queries import active_capacitas_batch_id
from app.modules.catasto.services import gis_flags
from app.modules.riordino.permissions import (
    RIORDINO_PRACTICE_CREATE,
    require_permission,
)
from app.modules.riordino.services import appeal_service
from app.modules.shared import http_shared
from app.modules.shared.datatable_helpers import build_datatable_params
from app.services import catasto_batches, catasto_captcha
from app.services import elaborazioni_batches, elaborazioni_captcha


def test_riordino_require_permission_allows_when_present() -> None:
    require_permission([RIORDINO_PRACTICE_CREATE, "other"], RIORDINO_PRACTICE_CREATE)


def test_riordino_require_permission_rejects_when_missing() -> None:
    with pytest.raises(HTTPException) as exc:
        require_permission(["riordino.practice.read"], RIORDINO_PRACTICE_CREATE)

    assert exc.value.status_code == 403
    assert "riordino.practice.create" in exc.value.detail


def test_refresh_cat_particelle_gis_flags_all() -> None:
    executed: list[str] = []

    class FakeResult:
        def scalar_one(self) -> int:
            return 7

    class FakeSession:
        def execute(self, statement, params=None):
            executed.append(str(statement))
            return FakeResult()

    assert gis_flags.refresh_cat_particelle_gis_flags(FakeSession(), None) == 7
    assert executed == ["SELECT refresh_cat_particelle_gis_flags_all()"]


def test_refresh_cat_particelle_gis_flags_deduplicates_particella_ids() -> None:
    executed: list[tuple[str, dict[str, str] | None]] = []

    class FakeSession:
        def execute(self, statement, params=None):
            executed.append((str(statement), params))
            return SimpleNamespace(scalar_one=lambda: 0)

    particella_id = uuid.uuid4()
    refreshed = gis_flags.refresh_cat_particelle_gis_flags(
        FakeSession(),
        [particella_id, str(particella_id), particella_id],
    )

    assert refreshed == 1
    assert len(executed) == 1
    assert executed[0][1] == {"particella_id": str(particella_id)}


def test_build_datatable_params_defaults_and_extra_params() -> None:
    params = build_datatable_params(
        draw=2,
        start=10,
        length=25,
        columns_count=2,
        search_value="abc",
        extra_params={"foo": "bar"},
    )

    assert params["draw"] == 2
    assert params["start"] == 10
    assert params["length"] == 25
    assert params["search[value]"] == "abc"
    assert params["columns[0][data]"] == "0"
    assert params["columns[1][orderable]"] == "true"
    assert params["foo"] == "bar"


def test_build_datatable_params_without_extra_params() -> None:
    params = build_datatable_params(columns_count=1)

    assert params["draw"] == 1
    assert params["columns[0][searchable]"] == "true"
    assert "foo" not in params


def test_datetime_compat_exposes_utc_alias() -> None:
    from datetime import timezone

    assert UTC is timezone.utc


def test_configure_logging_sets_info_level_and_format(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_basic_config(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

    configure_logging()

    assert captured["level"] == logging.INFO
    assert "%(asctime)s %(levelname)s %(name)s %(message)s" == captured["format"]


def test_hash_password_and_verify_password_roundtrip() -> None:
    password_hash = hash_password("secret-value")

    assert password_hash.startswith("pbkdf2_sha256$")
    assert verify_password("secret-value", password_hash) is True
    assert verify_password("wrong-value", password_hash) is False


def test_verify_password_rejects_malformed_and_unknown_scheme() -> None:
    assert verify_password("secret", "not-a-valid-hash") is False
    assert verify_password("secret", "bcrypt$12$salt$hash") is False


def test_create_and_decode_access_token() -> None:
    token = create_access_token("user-42", "admin", ["presenze", "operazioni"], expires_minutes=5)
    payload = decode_access_token(token)

    assert payload["sub"] == "user-42"
    assert payload["role"] == "admin"
    assert payload["modules"] == ["presenze", "operazioni"]
    assert payload["type"] == "access"


def test_decode_action_token_rejects_wrong_purpose() -> None:
    token = create_action_token("user-1", "password_reset", expires_minutes=5)
    with pytest.raises(jwt.InvalidTokenError):
        decode_action_token(token, expected_purpose="invite")


def test_create_and_decode_action_token_with_extra_claims() -> None:
    token = create_action_token(
        "user-1",
        "password_reset",
        expires_minutes=5,
        extra_claims={"email": "user@example.com"},
    )
    payload = decode_action_token(token, expected_purpose="password_reset")
    assert payload["email"] == "user@example.com"


def test_appeal_service_phase_and_step_requires_phase_one() -> None:
    db = MagicMock()
    db.scalar.return_value = None
    with pytest.raises(HTTPException) as exc:
        appeal_service._phase_and_step(db, uuid.uuid4())

    assert exc.value.status_code == 404
    assert exc.value.detail == "Phase 1 not found"


def test_get_db_yields_and_closes_session() -> None:
    generator = get_db()
    session = next(generator)
    try:
        assert session is not None
    finally:
        generator.close()


def test_database_sqlite_engine_options_in_subprocess() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import os; "
                "os.environ['DATABASE_URL']='sqlite:///./coverage-subprocess.db'; "
                "os.environ['JWT_SECRET_KEY']='coverage-subprocess-secret'; "
                "from app.core import database; "
                "assert 'connect_args' in database.engine_options; "
                "assert 'pool_size' not in database.engine_options"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_http_shared_build_batch_detail_response() -> None:
    now = datetime.now(timezone.utc)
    batch_id = uuid.uuid4()
    batch = SimpleNamespace(
        id=batch_id,
        user_id=1,
        credential_id=None,
        name="Batch",
        batch_kind="visura",
        status="completed",
        total_items=1,
        completed_items=1,
        failed_items=0,
        skipped_items=0,
        not_found_items=0,
        source_filename="input.csv",
        current_operation="done",
        report_json_path=None,
        report_md_path=None,
        created_at=now,
        started_at=now,
        completed_at=now,
    )
    request = SimpleNamespace(
        id=uuid.uuid4(),
        batch_id=batch_id,
        user_id=1,
        row_index=1,
        purpose="visura",
        target_ruolo_particella_id=None,
        search_mode="particella",
        comune="Comune",
        comune_codice="H501",
        catasto="F",
        sezione=None,
        foglio="1",
        particella="10",
        subalterno=None,
        tipo_visura="particella",
        subject_kind=None,
        subject_id=None,
        request_type=None,
        intestazione=None,
        status="completed",
        current_operation="done",
        error_message=None,
        attempts=1,
        captcha_image_path=None,
        captcha_requested_at=None,
        captcha_expires_at=None,
        captcha_skip_requested=False,
        artifact_dir=None,
        document_id=None,
        created_at=now,
        processed_at=now,
    )

    response = http_shared.build_batch_detail_response(batch, [request])

    assert response.requests[0].id == request.id


def test_http_shared_build_document_response_resolves_batch_id() -> None:
    request_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    document = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=1,
        request_id=request_id,
        search_mode="particella",
        comune="Comune",
        foglio="1",
        particella="10",
        subalterno=None,
        catasto="F",
        tipo_visura="particella",
        subject_kind=None,
        subject_id=None,
        request_type=None,
        intestazione=None,
        filename="doc.pdf",
        file_size=10,
        codice_fiscale=None,
        created_at=now,
    )
    db = MagicMock()
    db.scalar.return_value = batch_id

    response = http_shared.build_document_response(db, document)

    assert response.batch_id == batch_id


def test_http_shared_build_connection_test_response_status_branches() -> None:
    now = datetime.now(timezone.utc)
    completed = SimpleNamespace(
        id=uuid.uuid4(),
        credential_id=None,
        status="completed",
        mode="live",
        reachable=True,
        authenticated=True,
        message="ok",
        created_at=now,
        started_at=now,
        completed_at=now,
    )
    failed = SimpleNamespace(**{**completed.__dict__, "status": "failed"})
    pending = SimpleNamespace(**{**completed.__dict__, "status": "pending"})
    with_credential = SimpleNamespace(**{**completed.__dict__, "credential_id": uuid.uuid4()})

    db = MagicMock()
    db.get.return_value = SimpleNamespace(verified_at=now)
    assert http_shared.build_connection_test_response(db, completed).success is True
    assert http_shared.build_connection_test_response(db, failed).success is False
    assert http_shared.build_connection_test_response(db, pending).success is None
    assert http_shared.build_connection_test_response(db, with_credential).verified_at == now


def test_http_shared_build_zip_response_skips_missing_files(tmp_path: Path) -> None:
    existing = tmp_path / "present.txt"
    existing.write_text("payload", encoding="utf-8")
    documents = [
        SimpleNamespace(filepath=str(existing), filename="present.txt"),
        SimpleNamespace(filepath=str(tmp_path / "missing.txt"), filename="missing.txt"),
    ]

    response = http_shared.build_zip_response("bundle.zip", documents)

    assert response.media_type == "application/zip"
    assert response.headers["Content-Disposition"] == 'attachment; filename="bundle.zip"'


def test_http_shared_websocket_db_session_with_and_without_override() -> None:
    class FakeSession:
        closed = False

        def close(self) -> None:
            self.closed = True

    fake_session = FakeSession()
    websocket = SimpleNamespace(app=SimpleNamespace(dependency_overrides={}))

    with http_shared.websocket_db_session(websocket) as db:
        assert db is not None

    def override_get_db():
        yield fake_session

    websocket_with_override = SimpleNamespace(
        app=SimpleNamespace(dependency_overrides={http_shared.get_db: override_get_db}),
    )
    with http_shared.websocket_db_session(websocket_with_override) as db:
        assert db is fake_session
    assert fake_session.closed is False


def test_http_shared_get_websocket_token_from_query_header_or_error() -> None:
    token_ws = SimpleNamespace(query_params={"token": "query-token"}, headers={})
    assert http_shared.get_websocket_token(token_ws) == "query-token"

    header_ws = SimpleNamespace(query_params={}, headers={"authorization": "Bearer header-token"})
    assert http_shared.get_websocket_token(header_ws) == "header-token"

    missing_ws = SimpleNamespace(query_params={}, headers={})
    with pytest.raises(WebSocketException):
        http_shared.get_websocket_token(missing_ws)


def test_http_shared_build_request_state_and_connection_signature() -> None:
    request = SimpleNamespace(
        id=uuid.uuid4(),
        status="running",
        current_operation="fetch",
        document_id=uuid.uuid4(),
        captcha_image_path="/tmp/captcha.png",
        artifact_dir="/tmp/artifacts",
        captcha_requested_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    state_map = http_shared.build_request_state_map([request])
    assert state_map[str(request.id)]["status"] == "running"

    signature = http_shared.build_connection_test_signature(
        SimpleNamespace(
            status="completed",
            mode="live",
            reachable=True,
            authenticated=True,
            message="ok",
            started_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
            completed_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
        )
    )
    assert signature[0] == "completed"


def test_catasto_compat_reexports_expose_elaborazioni_symbols() -> None:
    assert catasto_batches.ElaborazioneBatch is elaborazioni_batches.ElaborazioneBatch
    assert (
        catasto_captcha.ElaborazioneCaptchaRequestNotFoundError
        is elaborazioni_captcha.ElaborazioneCaptchaRequestNotFoundError
    )


def test_active_capacitas_batch_id_returns_none_without_year() -> None:
    db = MagicMock()

    assert active_capacitas_batch_id(db, None) is None
    db.scalars.assert_not_called()


def test_active_capacitas_batch_id_returns_latest_completed_batch() -> None:
    batch_id = uuid.uuid4()
    db = MagicMock()
    db.scalars.return_value.first.return_value = batch_id

    assert active_capacitas_batch_id(db, 2025) == batch_id
    db.scalars.assert_called_once()
