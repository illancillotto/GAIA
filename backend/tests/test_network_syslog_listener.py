"""Syslog policy, session ownership and worker boundaries remain observable."""

import queue
from types import SimpleNamespace

import pytest

from app.modules.network import sophos_syslog_listener as module


@pytest.fixture
def message_case(monkeypatch):
    def prepare(*, enabled=True, fail=None, management_ip=None):
        trace = []

        def record(name, *args):
            trace.append((name, *args))
            if name == fail:
                raise RuntimeError(f"failed {name}")

        db = SimpleNamespace(rollback=lambda: record("rollback"), close=lambda: record("close"))

        def session():
            record("session")
            return db

        class Policy:
            @property
            def syslog_should_ingest(self):
                record("enabled")
                return enabled

            @property
            def is_within_window(self):
                record("window")
                return False

        def policy(session):
            assert session is db
            record("policy")
            return Policy()

        def ingest(session, **kwargs):
            assert session is db
            record("ingest", kwargs)

        monkeypatch.setattr(module, "get_sophos_runtime_policy", policy)
        monkeypatch.setattr(module, "ingest_sophos_syslog", ingest)
        monkeypatch.setattr(
            module,
            "logger",
            SimpleNamespace(
                debug=lambda *args: record("debug", *args),
                exception=lambda *args: record("exception", *args),
            ),
        )
        listener = module.SophosSyslogListener(session_factory=session)
        listener._management_ip = management_ip
        listener._firewall_name = "Firewall"
        return SimpleNamespace(listener=listener, trace=trace)

    return prepare


@pytest.mark.parametrize("client_ip", [None, "", "10.0.0.4"])
@pytest.mark.parametrize("management_ip", [None, "", "10.0.0.1"])
def test_enabled_policy_ingests_before_close_using_management_ip_or_client(
    message_case, management_ip, client_ip
):
    case = message_case(management_ip=management_ip)
    assert case.listener.handle_message(" raw message ", client_ip) is None
    assert case.trace == [
        ("session",),
        ("policy",),
        ("enabled",),
        (
            "ingest",
            {
                "message": " raw message ",
                "firewall_name": "Firewall",
                "management_ip": management_ip or client_ip,
            },
        ),
        ("close",),
    ]


@pytest.mark.parametrize("client_ip", [None, "", "10.0.0.4"])
def test_disabled_policy_logs_window_and_closes_without_ingesting_or_rollback(
    message_case, client_ip
):
    case = message_case(enabled=False)
    assert case.listener.handle_message("message", client_ip) is None
    assert [item[0] for item in case.trace] == [
        "session",
        "policy",
        "enabled",
        "window",
        "debug",
        "close",
    ]
    assert case.trace[-2] == (
        "debug",
        "Skipping Sophos syslog ingest from %s because runtime policy disabled processing (window=%s).",
        client_ip or "unknown",
        False,
    )


@pytest.mark.parametrize(
    "fail,enabled",
    [("policy", True), ("enabled", True), ("window", False), ("debug", False), ("ingest", True)],
)
def test_processing_errors_log_then_rollback_then_close(message_case, fail, enabled):
    case = message_case(fail=fail, enabled=enabled)
    assert case.listener.handle_message("message", None) is None
    assert [item[0] for item in case.trace[-3:]] == ["exception", "rollback", "close"]
    assert case.trace[-3] == (
        "exception",
        "Failed to ingest Sophos syslog message from %s",
        "unknown",
    )
    assert sum(item[0] == fail for item in case.trace) == 1


def test_session_factory_failure_propagates_without_cleanup_or_logging(message_case):
    case = message_case(fail="session")
    with pytest.raises(RuntimeError, match="failed session"):
        case.listener.handle_message("message")
    assert case.trace == [("session",)]


@pytest.mark.parametrize("enabled", [True, False])
def test_close_failure_propagates_without_rollback_or_retry(message_case, enabled):
    case = message_case(fail="close", enabled=enabled)
    with pytest.raises(RuntimeError, match="failed close"):
        case.listener.handle_message("message")
    assert case.trace[-1] == ("close",)
    assert not any(item[0] in ("exception", "rollback") for item in case.trace)


@pytest.mark.parametrize("fail", ["exception", "rollback"])
def test_error_handler_failure_still_closes_and_propagates(message_case, fail):
    case = message_case()
    case.listener._session_factory = lambda: SimpleNamespace(
        rollback=lambda: (_ for _ in ()).throw(RuntimeError("failed rollback")),
        close=lambda: case.trace.append(("close",)),
    )

    def failed_ingest(*_args, **_kwargs):
        raise ValueError("ingest unavailable")

    def failed_log(*_args):
        case.trace.append(("exception",))
        if fail == "exception":
            raise RuntimeError("failed exception")

    # Keep the policy independent of the original fixture session identity.
    module.get_sophos_runtime_policy = lambda _db: SimpleNamespace(syslog_should_ingest=True)
    module.ingest_sophos_syslog = failed_ingest
    module.logger.exception = failed_log
    with pytest.raises(RuntimeError, match=f"failed {fail}"):
        case.listener.handle_message("message")
    assert case.trace[-1] == ("close",)


def test_base_exception_is_not_swallowed_but_session_is_closed(message_case, monkeypatch):
    case = message_case()

    def stop(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(module, "ingest_sophos_syslog", stop)
    with pytest.raises(KeyboardInterrupt):
        case.listener.handle_message("message")
    assert [item[0] for item in case.trace] == ["session", "policy", "enabled", "close"]


def test_start_is_idempotent_and_stop_joins_workers(monkeypatch):
    trace = []

    class Thread:
        def __init__(self, **kwargs):
            trace.append(("thread", kwargs))

        def start(self):
            trace.append(("start",))

        def join(self, **kwargs):
            trace.append(("join", kwargs))

    monkeypatch.setattr(module.threading, "Thread", Thread)
    listener = module.SophosSyslogListener(
        session_factory=lambda: None, worker_count=2, queue_size=4
    )
    listener.stop()
    listener.start()
    listener.start()
    listener.stop()
    listener.stop()
    assert [event[0] for event in trace] == ["thread", "start", "thread", "start", "join", "join"]
    assert [event[1]["name"] for event in trace if event[0] == "thread"] == [
        "sophos-syslog-worker-1",
        "sophos-syslog-worker-2",
    ]
    assert all(event[1] == {"timeout": 2.0} for event in trace if event[0] == "join")
    assert listener._workers == [] and listener._started is False


def test_full_queue_logs_drop_and_stop_still_joins(monkeypatch):
    trace = []
    monkeypatch.setattr(module.logger, "warning", lambda *args: trace.append(args))
    listener = module.SophosSyslogListener(session_factory=lambda: None, queue_size=1)
    listener.enqueue_message("first")
    listener.enqueue_message("dropped")
    listener._workers = [SimpleNamespace(join=lambda **kwargs: trace.append(kwargs))]
    listener._started = True
    listener.stop()
    assert trace[0][1:] == ("unknown", 1)
    assert trace[1] == {"timeout": 2.0}
    assert listener._message_queue.get_nowait() == ("first", None)


@pytest.mark.parametrize("failure", [False, True])
def test_worker_marks_task_done_on_success_failure_and_sentinel(monkeypatch, failure):
    listener = module.SophosSyslogListener(session_factory=lambda: None)
    calls = []

    def handle(*args):
        calls.append(args)
        if failure:
            raise RuntimeError("processing failed")

    monkeypatch.setattr(listener, "handle_message", handle)
    listener._message_queue.put(("message", "client"))
    if failure:
        with pytest.raises(RuntimeError, match="processing failed"):
            listener._worker_loop()
    else:
        listener._message_queue.put(None)
        listener._worker_loop()
    assert listener._message_queue.unfinished_tasks == 0
    assert calls == [("message", "client")]


@pytest.mark.parametrize(
    "data,address,has_listener,expected",
    [
        ("text", ("client", 1), True, []),
        (b" \n", ("client", 1), True, []),
        (b"hello", ("client", 1), False, []),
        (b" \xff hello\n", ("client", 1), True, [("\ufffd hello", "client")]),
        (b"hello", None, True, [("hello", None)]),
    ],
)
def test_udp_handler_preserves_decoding_guards_and_client_ip(data, address, has_listener, expected):
    calls = []
    server = SimpleNamespace()
    if has_listener:
        server.listener = SimpleNamespace(enqueue_message=lambda *args: calls.append(args))
    module._SophosSyslogUDPHandler((data, None), address, server)
    assert calls == expected


def test_udp_server_attaches_listener(monkeypatch):
    calls = []
    monkeypatch.setattr(
        module.socketserver.UDPServer, "__init__", lambda _self, *args: calls.append(args)
    )
    listener = object()
    server = module._SophosSyslogUDPServer(("127.0.0.1", 1514), listener)
    assert calls == [(("127.0.0.1", 1514), module._SophosSyslogUDPHandler)]
    assert server.listener is listener


@pytest.mark.parametrize("failure", [False, True])
def test_server_runner_stops_listener_when_serving_ends_or_fails(monkeypatch, failure):
    trace = []
    listener = SimpleNamespace(
        start=lambda: trace.append("start"),
        stop=lambda: trace.append("stop"),
        _worker_count=1,
        _message_queue=queue.Queue(maxsize=2),
    )

    class Server:
        def __init__(self, address, received):
            assert received is listener
            trace.append(("bind", address))

        def __enter__(self):
            trace.append("enter")
            return self

        def serve_forever(self, **kwargs):
            trace.append(("serve", kwargs))
            if failure:
                raise RuntimeError("server failed")

        def __exit__(self, *_args):
            trace.append("exit")

    monkeypatch.setattr(module, "SophosSyslogListener", lambda **_kwargs: listener)
    monkeypatch.setattr(module, "_SophosSyslogUDPServer", Server)
    monkeypatch.setattr(module.logger, "info", lambda *_args: trace.append("info"))
    if failure:
        with pytest.raises(RuntimeError, match="server failed"):
            module.run_sophos_syslog_listener()
    else:
        module.run_sophos_syslog_listener()
    assert trace[0] == "start"
    assert trace[-2:] == ["exit", "stop"]
    assert ("serve", {"poll_interval": 0.5}) in trace
