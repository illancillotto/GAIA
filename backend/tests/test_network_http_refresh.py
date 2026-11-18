"""HTTP enrichment preserves refresh fallback and response/body failure state."""

from types import SimpleNamespace

import pytest

from app.modules.network import services


class HttpCancellation(BaseException):
    pass


@pytest.fixture
def http_case(monkeypatch):
    def prepare(*, target="/status", status=200, fail=None, failure=RuntimeError, empty=False):
        trace = []
        clients = []

        def record(name, *args):
            trace.append((name, *args))
            if name == fail:
                raise failure(name)

        class Response:
            def __init__(self, attempt, number):
                self.attempt = attempt
                self.number = number

            @property
            def text(self):
                record(f"text{self.attempt}.{self.number}")
                return "" if empty else ("initial" if self.number == 1 else "follow")

            @property
            def status_code(self):
                record(f"status{self.attempt}.{self.number}")
                return status

            @property
            def headers(self):
                record(f"headers{self.attempt}.{self.number}")
                return {
                    "server": ""
                    if empty
                    else ("initial-server" if self.number == 1 else "follow-server")
                }

        class Client:
            def __init__(self, **kwargs):
                self.attempt = len(clients) + 1
                self.number = 0
                clients.append(self)
                record(f"client{self.attempt}", kwargs)

            def __enter__(self):
                record(f"enter{self.attempt}")
                return self

            def __exit__(self, kind, error, traceback):
                record(f"exit{self.attempt}", kind.__name__ if kind else None)
                # Match httpx.Client.__exit__: cleanup does not suppress errors.
                return None

            def get(self, url, **kwargs):
                self.number += 1
                record(f"get{self.attempt}.{self.number}", url, kwargs)
                return Response(self.attempt, self.number)

        def refresh_target(body):
            record("refresh_target", body)
            return target

        def title(body):
            record("title", body)
            return f"title:{body}" if body else None

        def device_name(body):
            record("device_name", body)
            return f"device:{body}" if body else None

        def safe(value):
            record("safe", value)
            return value or None

        def classify(title, server, name):
            record("classify", title, server, name)
            return ("Vendor", "Model", "OS") if title or server or name else (None, None, None)

        monkeypatch.setattr(services, "httpx", SimpleNamespace(Client=Client))
        monkeypatch.setattr(
            services, "settings", SimpleNamespace(network_enrichment_timeout_seconds=1.5)
        )
        monkeypatch.setattr(services, "_extract_meta_refresh_target", refresh_target)
        monkeypatch.setattr(services, "_extract_html_title", title)
        monkeypatch.setattr(services, "_extract_device_name", device_name)
        monkeypatch.setattr(services, "_safe_text", safe)
        monkeypatch.setattr(services, "_classify_http_identity", classify)
        return SimpleNamespace(
            call=lambda ports=(80, 443): services._resolve_http_metadata("192.0.2.7", ports),
            trace=trace,
            clients=clients,
        )

    return prepare


@pytest.mark.parametrize("target", ["/status", "https://other/status"])
@pytest.mark.parametrize("status", [200, 499, 500])
def test_refresh_url_cutoff_headers_and_source_are_preserved(http_case, target, status):
    case = http_case(target=target, status=status)
    result = case.call()
    body = "follow" if status < 500 else "initial"
    assert result.http_title == f"title:{body}"
    assert result.http_server == ("follow-server" if status < 500 else "initial-server")
    assert result.metadata_sources == {
        "http_title": f"title:{body}",
        "http_device_name": f"device:{body}",
        "http_server": result.http_server,
        "http_refresh_target": target,
        "http": "http:80",
    }
    assert case.trace[0] == ("client1", {"follow_redirects": True, "verify": False, "timeout": 1.5})
    gets = [event for event in case.trace if event[0].startswith("get")]
    assert gets == [
        ("get1.1", "http://192.0.2.7:80/", {"headers": {"User-Agent": "GAIA-Network-Monitor/1.0"}}),
        (
            "get1.2",
            target if target.startswith("http") else f"http://192.0.2.7:80{target}",
            {"headers": {"User-Agent": "GAIA-Network-Monitor/1.0"}},
        ),
    ]
    names = [event[0] for event in case.trace]
    assert (
        names.index("exit1")
        < names.index("title")
        < names.index("headers1.2" if status < 500 else "headers1.1")
    )
    assert len(case.clients) == 1


@pytest.mark.parametrize("point", ["get1.2", "status1.2", "text1.2"])
def test_refresh_exception_preserves_partial_response_replacement(http_case, point):
    case = http_case(fail=point)
    result = case.call()
    assert result.http_title == "title:initial"
    assert result.http_server == ("follow-server" if point == "text1.2" else "initial-server")
    assert ("exit1", None) in case.trace
    assert len(case.clients) == 1


@pytest.mark.parametrize("point", ["client1", "enter1", "get1.1", "text1.1", "exit1"])
def test_initial_request_exception_tries_https_before_parsing(http_case, point):
    case = http_case(target=None, fail=point)
    result = case.call()
    assert result.metadata_sources["http"] == "https:443"
    assert any(event[:2] == ("get2.1", "https://192.0.2.7:443/") for event in case.trace)
    names = [event[0] for event in case.trace]
    assert names.index("exit2") < names.index("title")
    assert len(case.clients) == 2


@pytest.mark.parametrize("point", ["get1.1", "get1.2", "text1.2"])
def test_base_exception_propagates_through_client_cleanup(http_case, point):
    case = http_case(fail=point, failure=HttpCancellation)
    with pytest.raises(HttpCancellation, match=point):
        case.call()
    assert case.trace[-1] == ("exit1", "HttpCancellation")
    assert len(case.clients) == 1


@pytest.mark.parametrize("point", ["title", "device_name", "classify"])
def test_parse_errors_after_client_close_are_not_connection_fallbacks(http_case, point):
    case = http_case(target=None, fail=point)
    with pytest.raises(RuntimeError, match=point):
        case.call()
    assert ("exit1", None) in case.trace and case.trace[-1][0] == point
    assert len(case.clients) == 1


@pytest.mark.parametrize(
    "ports,expected", [([], None), ([22], None), ([443, 80, 443], "http:80"), ([443], "https:443")]
)
def test_candidates_keep_http_first_and_skip_unrelated_ports(http_case, ports, expected):
    case = http_case(target=None)
    result = case.call(iter(ports))
    if expected is None:
        assert result == services.EnrichmentMetadata() and case.trace == []
    else:
        assert result.metadata_sources["http"] == expected and len(case.clients) == 1


def test_unavailable_http_client_does_not_consume_ports(http_case, monkeypatch):
    case = http_case()
    monkeypatch.setattr(services, "httpx", None)

    def ports():
        pytest.fail("ports consumed while HTTP dependency unavailable")
        yield

    assert case.call(ports()) == services.EnrichmentMetadata() and not case.trace


def test_port_iteration_error_precedes_client_creation(http_case):
    case = http_case()

    def ports():
        raise RuntimeError("ports")
        yield

    with pytest.raises(RuntimeError, match="ports"):
        case.call(ports())
    assert not case.trace


def test_empty_page_does_not_try_the_second_scheme(http_case):
    case = http_case(target=None, empty=True)
    assert case.call() == services.EnrichmentMetadata()
    assert len(case.clients) == 1
