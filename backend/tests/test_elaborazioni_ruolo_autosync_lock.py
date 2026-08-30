from __future__ import annotations

from contextlib import contextmanager

import pytest

import app.services.elaborazioni_ruolo_autosync as autosync


class _FakeDialect:
    name = "postgresql"


class _FakeTransaction:
    def __init__(self) -> None:
        self.rolled_back = False

    def rollback(self) -> None:
        self.rolled_back = True


class _FakeConnection:
    def __init__(self, acquired: bool) -> None:
        self.acquired = acquired
        self.transaction = _FakeTransaction()
        self.statement = ""
        self.closed = False

    def __enter__(self) -> _FakeConnection:
        return self

    def __exit__(self, *_args: object) -> None:
        self.closed = True

    def begin(self) -> _FakeTransaction:
        return self.transaction

    def scalar(self, statement: object) -> bool:
        self.statement = str(statement)
        return self.acquired


class _FakeEngine:
    dialect = _FakeDialect()

    def __init__(self, acquired: bool) -> None:
        self.connection = _FakeConnection(acquired)

    def connect(self) -> _FakeConnection:
        return self.connection


class _FakeDb:
    def __init__(self, acquired: bool) -> None:
        self.engine = _FakeEngine(acquired)

    def get_bind(self) -> _FakeEngine:
        return self.engine


def test_ruolo_autosync_lock_is_transaction_scoped_and_always_released() -> None:
    db = _FakeDb(acquired=True)

    with autosync._ruolo_autosync_xact_lock(db, 7) as acquired:
        assert acquired is True
        assert "pg_try_advisory_xact_lock" in db.engine.connection.statement
        assert db.engine.connection.transaction.rolled_back is False

    assert db.engine.connection.transaction.rolled_back is True
    assert db.engine.connection.closed is True


def test_manual_refresh_fails_fast_when_another_autosync_operation_holds_the_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def busy_lock(_db: object, _user_id: int):
        yield False

    monkeypatch.setattr(autosync, "_ruolo_autosync_xact_lock", busy_lock)

    @autosync._ruolo_autosync_serialized
    def operation(_db: object, _user_id: int) -> dict[str, int]:
        raise AssertionError("the operation must not run while the lock is busy")

    with pytest.raises(autosync.RuoloAutosyncBusyError) as exc_info:
        operation(object(), 7)

    assert exc_info.value.status_code == 409
    assert "già in corso" in str(exc_info.value.detail)
