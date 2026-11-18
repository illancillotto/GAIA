"""Characterize telemetry lock ownership and resource cleanup, including failures."""

from types import SimpleNamespace

import pytest

from app.modules.network import telemetry_scheduler as module


@pytest.fixture
def anyio_backend():
    return "asyncio"


class SchedulerFailure(Exception):
    pass


class SchedulerCancellation(BaseException):
    pass


@pytest.fixture
def job_case(monkeypatch):
    def prepare(*, postgres=True, acquired=True, generator=False, close_kind="sync", errors=None):
        trace = []
        errors = errors or {}
        resource_holder = []
        cursor_count = 0

        def record(name, *args):
            trace.append((name, *args))
            if name in errors:
                raise errors[name](name)

        class Cursor:
            def __init__(self, name):
                self.name = name

            def execute(self, sql, params):
                record(f"{self.name}.execute", sql, params)

            def fetchone(self):
                record(f"{self.name}.fetchone")
                return (acquired,)

            def close(self):
                record(f"{self.name}.close")

        def cursor():
            nonlocal cursor_count
            cursor_count += 1
            name = "acquire" if cursor_count == 1 else "release"
            record(f"{name}.cursor")
            return Cursor(name)

        connection = SimpleNamespace(cursor=cursor, close=lambda: record("connection.close"))

        def raw_connection():
            record("raw_connection")
            return connection

        def close():
            record("db.close")
            if close_kind == "async":

                async def finish_close():
                    record("db.await_close")

                return finish_close()
            return None

        db = SimpleNamespace()
        if close_kind != "missing":
            db.close = None if close_kind == "noncallable" else close

        def factory():
            record("factory")
            if not generator:
                return db

            def resources():
                record("generator.start")
                yield db
                record("generator.finish")

            resource = resources()
            resource_holder.append(resource)
            return resource

        def refresh(session, **kwargs):
            assert session is db
            record("refresh", kwargs)

        def prune(session, **kwargs):
            assert session is db
            record("prune", kwargs)

        monkeypatch.setattr(
            module,
            "engine",
            SimpleNamespace(
                dialect=SimpleNamespace(name="postgresql" if postgres else "sqlite"),
                raw_connection=raw_connection,
            ),
        )
        monkeypatch.setattr(module, "refresh_network_firewall_hourly_rollups", refresh)
        monkeypatch.setattr(module, "prune_network_firewall_events", prune)
        monkeypatch.setattr(
            module, "logger", SimpleNamespace(info=lambda *args: record("log", *args))
        )
        monkeypatch.setattr(
            module,
            "settings",
            SimpleNamespace(
                network_telemetry_rollup_lookback_hours=37,
                network_firewall_raw_retention_days=11,
            ),
        )
        return SimpleNamespace(
            call=lambda: module._run_job_wrapper(factory),
            trace=trace,
            resources=resource_holder,
            db=db,
        )

    return prepare


@pytest.mark.anyio
@pytest.mark.parametrize("postgres", [False, True])
@pytest.mark.parametrize("acquired", [False, True])
@pytest.mark.parametrize("generator", [False, True])
@pytest.mark.parametrize("close_kind", ["sync", "async", "missing", "noncallable"])
async def test_job_preserves_lock_work_cleanup_order(
    job_case, postgres, acquired, generator, close_kind
):
    case = job_case(
        postgres=postgres, acquired=acquired, generator=generator, close_kind=close_kind
    )
    await case.call()
    expected = ["factory"] + (["generator.start"] if generator else [])
    if postgres:
        expected += [
            "raw_connection",
            "acquire.cursor",
            "acquire.execute",
            "acquire.fetchone",
            "acquire.close",
        ]
    expected += ["log"] if postgres and not acquired else ["refresh", "prune"]
    if close_kind in {"sync", "async"}:
        expected += ["db.close"]
    if close_kind == "async":
        expected += ["db.await_close"]
    if postgres:
        expected += ["release.cursor", "release.execute", "release.close", "connection.close"]
    if generator:
        expected += ["generator.finish"]
    assert [e[0] for e in case.trace] == expected
    if postgres:
        assert ("acquire.execute", "SELECT pg_try_advisory_lock(%s)", (2200615,)) in case.trace
        assert ("release.execute", "SELECT pg_advisory_unlock(%s)", (2200615,)) in case.trace
    if not postgres or acquired:
        assert ("refresh", {"lookback_hours": 37}) in case.trace
        assert ("prune", {"retention_days": 11}) in case.trace


@pytest.mark.anyio
@pytest.mark.parametrize(
    "point", ["release.cursor", "release.execute", "release.close", "connection.close"]
)
async def test_unlock_exception_is_suppressed_and_remaining_cleanup_runs(job_case, point):
    case = job_case(generator=True, errors={point: SchedulerFailure})
    await case.call()
    names = [e[0] for e in case.trace]
    assert "connection.close" in names and names[-1] == "generator.finish"
    if point == "release.execute":
        assert (
            names.index("release.execute")
            < names.index("release.close")
            < names.index("connection.close")
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "point",
    [
        "factory",
        "generator.start",
        "raw_connection",
        "acquire.cursor",
        "acquire.execute",
        "acquire.fetchone",
        "acquire.close",
        "refresh",
        "prune",
        "db.close",
        "db.await_close",
        "generator.finish",
    ],
)
async def test_work_and_cleanup_failures_keep_original_boundaries(job_case, point):
    case = job_case(generator=True, close_kind="async", errors={point: SchedulerFailure})
    with pytest.raises(SchedulerFailure, match=point):
        await case.call()
    names = [e[0] for e in case.trace]
    if point in {"factory", "generator.start"}:
        assert "db.close" not in names
    elif point in {"db.close", "db.await_close"}:
        assert "release.cursor" not in names and "generator.finish" not in names
    else:
        assert "db.await_close" in names and "generator.finish" in names
    if point in {"acquire.execute", "acquire.fetchone"}:
        assert "acquire.close" in names
    if point not in {"factory", "generator.start", "raw_connection", "db.close", "db.await_close"}:
        assert "connection.close" in names


@pytest.mark.anyio
@pytest.mark.parametrize(
    "point",
    ["acquire.execute", "refresh", "prune", "release.execute", "release.close", "connection.close"],
)
async def test_base_exception_is_not_suppressed(job_case, point):
    case = job_case(generator=True, errors={point: SchedulerCancellation})
    with pytest.raises(SchedulerCancellation, match=point):
        await case.call()
    names = [e[0] for e in case.trace]
    if point.startswith("release") or point == "connection.close":
        assert "generator.finish" not in names
    else:
        assert names[-1] == "generator.finish"
    if point == "release.execute":
        assert names[-1] == "release.close" and "connection.close" not in names


@pytest.mark.anyio
async def test_cleanup_failure_overrides_work_error(job_case):
    case = job_case(errors={"refresh": SchedulerFailure, "db.close": SchedulerCancellation})
    with pytest.raises(SchedulerCancellation, match=r"db\.close"):
        await case.call()
    assert case.trace[-1][0] == "db.close"


@pytest.mark.anyio
async def test_registration_keeps_disabled_and_enabled_contract(monkeypatch):
    trace = []
    state = SimpleNamespace(
        network_telemetry_rollup_enabled=False,
        network_telemetry_rollup_cron="17 */2 * * *",
        network_telemetry_rollup_timezone="Europe/Rome",
        network_telemetry_rollup_lookback_hours=37,
        network_firewall_raw_retention_days=11,
    )
    monkeypatch.setattr(module, "settings", state)
    monkeypatch.setattr(
        module, "logger", SimpleNamespace(info=lambda *args: trace.append(("log", args)))
    )
    trigger = object()

    def from_crontab(*args, **kwargs):
        trace.append(("cron", args, kwargs))
        return trigger

    monkeypatch.setattr(module, "CronTrigger", SimpleNamespace(from_crontab=from_crontab))
    scheduler = SimpleNamespace(
        add_job=lambda *args, **kwargs: trace.append(("add_job", args, kwargs))
    )
    factory = object()
    await module.register_network_telemetry_scheduler(scheduler, factory)
    assert len(trace) == 1 and "disabled" in trace[0][1][0]
    trace.clear()
    state.network_telemetry_rollup_enabled = True
    await module.register_network_telemetry_scheduler(scheduler, factory)
    assert trace[0] == ("cron", ("17 */2 * * *",), {"timezone": "Europe/Rome"})
    assert trace[1] == (
        "add_job",
        (module._run_job_wrapper,),
        {
            "trigger": trigger,
            "id": "network_telemetry_rollup_refresh",
            "replace_existing": True,
            "max_instances": 1,
            "coalesce": True,
            "misfire_grace_time": 3600,
            "kwargs": {"get_db": factory},
        },
    )
    assert trace[2][0] == "log"
