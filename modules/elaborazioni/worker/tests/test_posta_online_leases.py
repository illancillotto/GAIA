from types import SimpleNamespace

import pytest
import test_worker as worker_test_support  # noqa: F401 - installs isolated worker dependencies

from posta_online_leases import PortalLease, acquire_portal_lease


class Connection:
    def __init__(self, answers):
        self.answers = iter(answers)
        self.calls = []
        self.closed = False
        self.invalidated = False

    def scalar(self, query, parameters):
        self.calls.append((str(query), parameters))
        value = next(self.answers)
        if isinstance(value, BaseException):
            raise value
        return value

    def commit(self):
        pass

    def invalidate(self):
        self.invalidated = True

    def close(self):
        self.closed = True


def engine(connection, dialect="postgresql"):
    return SimpleNamespace(dialect=SimpleNamespace(name=dialect), connect=lambda: connection)


def test_accounts_share_the_portal_gate_but_have_a_stable_exclusive_account_lock():
    first, second = Connection([True] * 4), Connection([True] * 4)
    a = acquire_portal_lease(engine(first), "  Account@Example.it ")
    b = acquire_portal_lease(engine(second), "account@example.IT")
    assert first.calls[:2] == second.calls[:2]
    assert "lock_shared" in first.calls[0][0]
    assert "lock_shared" not in first.calls[1][0]
    a.close()
    a.close()
    b.close()
    assert "unlock_shared" in first.calls[-1][0]
    assert "unlock(" in first.calls[-2][0]
    assert first.closed and second.closed


def test_legacy_sessions_require_exclusive_access():
    connection = Connection([True, True])
    lease = acquire_portal_lease(engine(connection), None)
    assert len(connection.calls) == 1 and "shared" not in connection.calls[0][0]
    lease.close()
    assert "shared" not in connection.calls[-1][0]


@pytest.mark.parametrize("answers", [[False], [True, False, True]])
def test_a_busy_gate_or_account_releases_any_partial_locks(answers):
    connection = Connection(answers)
    assert acquire_portal_lease(engine(connection), "account") is None
    assert connection.closed


def test_acquisition_failure_closes_the_connection():
    connection = Connection([RuntimeError("disconnected")])
    with pytest.raises(RuntimeError, match="disconnected"):
        acquire_portal_lease(engine(connection), "account")
    assert connection.closed


def test_unlock_failure_discards_the_connection_instead_of_returning_a_locked_session():
    connection = Connection([True, RuntimeError("unlock failed")])
    lease = acquire_portal_lease(engine(connection), None)
    with pytest.raises(RuntimeError, match="unlock failed"):
        lease.close()
    assert connection.closed and connection.invalidated


def test_non_postgresql_execution_is_rejected():
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        PortalLease(engine(Connection([]), "sqlite"))
