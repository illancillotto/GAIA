import json
import os
import ssl
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    build_opener,
)
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = "/api/wiki/mcp/connector/data"
OAUTH_PATH = "/api/wiki/mcp/connector/oauth"
MCP_PATHS = (
    DATA_PATH,
    OAUTH_PATH + "/authorize?state=synthetic",
    OAUTH_PATH + "/consent",
    OAUTH_PATH + "/token",
    OAUTH_PATH + "/revoke",
    "/.well-known/oauth-authorization-server" + OAUTH_PATH,
    "/.well-known/oauth-protected-resource" + DATA_PATH,
    "/mcp/consent?request_id=synthetic",
)
UPSTREAM_SCRIPT = """
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class EchoHandler(BaseHTTPRequestHandler):
    def respond(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        source = {3000: "frontend", 8000: "backend", 8769: "connector", 3001: "tiles"}[self.server.server_port]
        status = 401 if source == "connector" and self.path == "/api/wiki/mcp/connector/data" and not self.headers.get("Authorization") else 200
        result = json.dumps({"source": source, "path": self.path, "method": self.command,
            "authorization": self.headers.get("Authorization"), "host": self.headers.get("Host"),
            "scheme": self.headers.get("X-Forwarded-Proto"), "body": body.decode()}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(result)))
        self.end_headers()
        self.wfile.write(result)

    do_GET = respond
    do_POST = respond
    do_DELETE = respond

    def log_message(self, *args):
        pass

for port in (3000, 8000, 8769, 3001):
    server = ThreadingHTTPServer(("0.0.0.0", port), EchoHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
threading.Event().wait()
"""


def docker(*arguments):
    return subprocess.run(
        ["docker", *arguments], check=True, capture_output=True, text=True, timeout=60
    ).stdout.strip()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


@dataclass
class Gateway:
    container: str
    http: str
    https: str
    origin: str
    opener: object

    def request(self, path, *, secure=True, method="GET", body=None, headers=None):
        request = Request(
            (self.https if secure else self.http) + path,
            data=body,
            method=method,
            headers=headers or {},
        )
        try:
            return self.opener.open(request, timeout=10)
        except HTTPError as response:
            return response


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    directory = tmp_path_factory.mktemp("mcp-gateway")
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(directory / "key.pem"),
            "-out",
            str(directory / "cert.pem"),
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return directory


@pytest.fixture(scope="module")
def gateway(request, certificates):
    secure = getattr(request, "param", True)
    identifier = "gaia-mcp-test-" + uuid4().hex[:12]
    upstream = identifier + "-upstream"
    container = identifier + "-nginx"
    image = os.environ.get("MCP_GATEWAY_NGINX_IMAGE", "nginx:1.29-alpine")
    upstream_image = os.environ.get("MCP_GATEWAY_UPSTREAM_IMAGE", "gaia-backend:latest")
    origin = "https://canonical.example:8443"
    script = certificates / (identifier + ".py")
    script.write_text(UPSTREAM_SCRIPT)
    arguments = [
        "run",
        "-d",
        "--name",
        container,
        "--network",
        identifier,
        "-p",
        "127.0.0.1::80",
    ]
    volumes = {
        ROOT / "nginx/nginx.conf": "/etc/nginx/conf.d/default.conf",
        ROOT / "nginx/server-routes.conf": "/etc/nginx/gaia/server-routes.conf",
        ROOT / "nginx/maintenance": "/usr/share/nginx/html/maintenance",
    }
    if secure:
        arguments += [
            "-p",
            "127.0.0.1::443",
            "-e",
            "GAIA_MCP_HTTPS_ORIGIN=" + origin,
            "-e",
            "NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx/gaia",
            "-e",
            "NGINX_ENVSUBST_FILTER=^GAIA_MCP_HTTPS_ORIGIN$",
        ]
        volumes.update(
            {
                ROOT / "nginx/mcp-tls.conf": "/etc/nginx/conf.d/mcp-tls.conf",
                ROOT
                / "nginx/mcp-http-redirect.conf.template": "/etc/nginx/templates/mcp-http-redirect.conf.template",
                ROOT / "nginx/mcp-connector-http.example.conf": "/etc/nginx/gaia/mcp-http.conf",
                ROOT / "nginx/mcp-connector-server.example.conf": "/etc/nginx/gaia/mcp-server.conf",
                certificates / "cert.pem": "/etc/nginx/tls/fullchain.pem",
                certificates / "key.pem": "/etc/nginx/tls/privkey.pem",
            }
        )
    for source, destination in volumes.items():
        arguments += ["-v", f"{source}:{destination}:ro"]
    docker("network", "create", identifier)
    try:
        docker(
            "run",
            "-d",
            "--name",
            upstream,
            "--network",
            identifier,
            "--network-alias",
            "frontend",
            "--network-alias",
            "backend",
            "--network-alias",
            "gaia-mcp-connector",
            "--network-alias",
            "martin",
            "-v",
            f"{script}:/tmp/echo.py:ro",
            "--entrypoint",
            "python",
            upstream_image,
            "/tmp/echo.py",
        )
        docker(*arguments, image)
        docker("exec", container, "nginx", "-t")
        http_port = docker("port", container, "80/tcp").rsplit(":", 1)[1]
        https_port = docker("port", container, "443/tcp").rsplit(":", 1)[1] if secure else None
        context = ssl.create_default_context(cafile=str(certificates / "cert.pem"))
        runtime = Gateway(
            container,
            "http://localhost:" + http_port,
            "https://localhost:" + https_port if secure else "",
            origin,
            build_opener(NoRedirect(), HTTPSHandler(context=context)),
        )
        for _attempt in range(40):
            try:
                with runtime.request("/", secure=False) as response:
                    if response.status == 200:
                        break
            except URLError:
                pass
            time.sleep(0.1)
        else:
            pytest.fail(
                "Gateway failed to become ready: " + docker("logs", "--tail", "15", container)
            )
        yield runtime
    finally:
        subprocess.run(["docker", "rm", "-f", container, upstream], capture_output=True, timeout=60)
        subprocess.run(["docker", "network", "rm", identifier], capture_output=True, timeout=60)


@pytest.fixture
def tls_gateway(gateway):
    assert gateway.https
    return gateway


@pytest.mark.parametrize(
    "path,source,upstream_path",
    [
        ("/", "frontend", "/"),
        ("/wiki?view=mcp", "frontend", "/wiki?view=mcp"),
        ("/api/auth/login", "backend", "/auth/login"),
        ("/api/auth/me?probe=1", "backend", "/auth/me?probe=1"),
    ],
)
@pytest.mark.parametrize(
    "gateway", [False, True], indirect=True, ids=["http-only", "http-and-https"]
)
def test_existing_http_routing_remains_available(gateway, path, source, upstream_path):
    with gateway.request(path, secure=False) as response:
        assert response.status == 200
        payload = json.load(response)
    assert (payload["source"], payload["path"], payload["scheme"]) == (
        source,
        upstream_path,
        "http",
    )


@pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
@pytest.mark.parametrize("path", MCP_PATHS)
def test_mcp_http_redirect_preserves_request_target(tls_gateway, method, path):
    with tls_gateway.request(path, secure=False, method=method) as response:
        assert response.status == 308
        assert response.headers["Location"] == tls_gateway.origin + path
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Referrer-Policy"] == "no-referrer"


def test_http_redirect_uses_configured_origin(tls_gateway):
    with tls_gateway.request(
        DATA_PATH, secure=False, headers={"Host": "untrusted.example"}
    ) as response:
        assert response.status == 308
        assert response.headers["Location"] == tls_gateway.origin + DATA_PATH


@pytest.mark.parametrize("path", MCP_PATHS)
def test_https_routes_reach_the_correct_upstream(tls_gateway, path):
    with tls_gateway.request(path) as response:
        assert response.status == (401 if path == DATA_PATH else 200)
        payload = json.load(response)
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Referrer-Policy"] == "no-referrer"
    assert payload["source"] == ("frontend" if path.startswith("/mcp/") else "connector")
    assert payload["path"] == path
    assert payload["scheme"] == "https"


def test_https_login_preserves_credentials_and_scheme(tls_gateway):
    body = b'{"username":"synthetic","password":"synthetic"}'
    with tls_gateway.request(
        "/api/auth/login", method="POST", body=body, headers={"Content-Type": "application/json"}
    ) as response:
        payload = json.load(response)
    assert payload["source"] == "backend"
    assert payload["path"] == "/auth/login"
    assert payload["method"] == "POST"
    assert payload["body"] == body.decode()
    assert payload["scheme"] == "https"


def test_mcp_proxy_preserves_authorization_and_json_rpc(tls_gateway):
    body = b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
    with tls_gateway.request(
        DATA_PATH,
        method="POST",
        body=body,
        headers={"Authorization": "Bearer synthetic-token", "Content-Type": "application/json"},
    ) as response:
        assert response.status == 200
        payload = json.load(response)
    assert payload["source"] == "connector"
    assert payload["path"] == DATA_PATH
    assert payload["authorization"] == "Bearer synthetic-token"
    assert payload["body"] == body.decode()
    assert payload["method"] == "POST"


def test_mcp_proxy_rejects_oversized_body(tls_gateway):
    with tls_gateway.request(DATA_PATH, method="POST", body=b"x" * 65537) as response:
        assert response.status == 413


def test_mcp_proxy_accepts_body_at_the_limit(tls_gateway):
    body = b"x" * 65536
    with tls_gateway.request(
        DATA_PATH, method="POST", body=body, headers={"Authorization": "Bearer synthetic-token"}
    ) as response:
        assert response.status == 200
        assert json.load(response)["body"] == body.decode()


def test_consent_has_browser_security_headers(tls_gateway):
    with tls_gateway.request("/mcp/consent") as response:
        assert response.status == 200
        assert (
            response.headers["Content-Security-Policy"]
            == "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )


@pytest.mark.parametrize("path", ["/", "/api/auth/login", DATA_PATH, "/mcp/consent"])
@pytest.mark.parametrize(
    "gateway", [False, True], indirect=True, ids=["http-only", "http-and-https"]
)
def test_maintenance_applies_to_both_protocols(gateway, path):
    docker("exec", gateway.container, "mkdir", "-p", "/var/lib/gaia-nginx-maintenance")
    docker("exec", gateway.container, "touch", "/var/lib/gaia-nginx-maintenance/on")
    try:
        for secure in [False, True] if gateway.https else [False]:
            with gateway.request(path, secure=secure) as response:
                assert response.status == 503
                assert response.headers["Retry-After"] == "120"
    finally:
        docker("exec", gateway.container, "rm", "/var/lib/gaia-nginx-maintenance/on")


def test_https_requires_a_trusted_certificate(tls_gateway):
    opener = build_opener(HTTPSHandler(context=ssl.create_default_context()))
    with pytest.raises(URLError, match="CERTIFICATE_VERIFY_FAILED"):
        opener.open(tls_gateway.https + "/", timeout=10)


@pytest.mark.parametrize("version", [ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3])
def test_https_supports_current_tls_versions(tls_gateway, certificates, version):
    context = ssl.create_default_context(cafile=str(certificates / "cert.pem"))
    context.minimum_version = version
    context.maximum_version = version
    opener = build_opener(HTTPSHandler(context=context))
    with opener.open(tls_gateway.https + "/", timeout=10) as response:
        assert response.status == 200
        assert json.load(response)["scheme"] == "https"


def test_https_rejects_obsolete_tls(tls_gateway):
    address = tls_gateway.https.removeprefix("https://")
    result = subprocess.run(
        ["openssl", "s_client", "-connect", address, "-tls1_1", "-cipher", "DEFAULT:@SECLEVEL=0"],
        input="",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "alert protocol version" in result.stderr


def test_mcp_query_identifiers_are_absent_from_access_logs(tls_gateway):
    identifier = "synthetic-private-" + uuid4().hex
    for secure in (False, True):
        with tls_gateway.request(
            "/mcp/consent?request_id=" + identifier, secure=secure
        ) as response:
            assert response.status == (200 if secure else 308)
    assert identifier not in docker("logs", tls_gateway.container)


def test_mcp_rate_limit_returns_429(tls_gateway):
    def probe(_index):
        with tls_gateway.request(DATA_PATH) as response:
            return response.status

    try:
        with ThreadPoolExecutor(max_workers=8) as executor:
            statuses = list(executor.map(probe, range(50)))
        assert 429 in statuses
        assert set(statuses) <= {401, 429}
    finally:
        time.sleep(3)


def compose_environment(certificates):
    return {
        **os.environ,
        "GAIA_TLS_CERTIFICATE": str(certificates / "cert.pem"),
        "GAIA_TLS_PRIVATE_KEY": str(certificates / "key.pem"),
        "GAIA_MCP_HTTPS_ORIGIN": "https://canonical.example:8443",
    }


def compose_config(environ, *, tls=True):
    arguments = ["docker", "compose", "--env-file", "/dev/null", "-f", "docker-compose.yml"]
    if tls:
        arguments += [
            "-f",
            "docker-compose.mcp.yml",
            "-f",
            "docker-compose.mcp-tls.yml",
            "--profile",
            "mcp-connector",
        ]
    return subprocess.run(
        [*arguments, "config", "--format", "json"],
        cwd=ROOT,
        env=environ,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_compose_adds_tls_without_replacing_http(certificates):
    result = compose_config(compose_environment(certificates))
    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)
    nginx = config["services"]["nginx"]
    assert {port["target"] for port in nginx["ports"]} == {80, 443}
    volumes = {volume["target"]: volume for volume in nginx["volumes"]}
    assert volumes["/etc/nginx/tls/privkey.pem"]["read_only"] is True
    assert volumes["/etc/nginx/tls/fullchain.pem"]["read_only"] is True
    assert "/etc/nginx/gaia/server-routes.conf" in volumes
    assert "ports" not in config["services"]["gaia-mcp-connector"]


@pytest.mark.parametrize(
    "missing", ["GAIA_TLS_CERTIFICATE", "GAIA_TLS_PRIVATE_KEY", "GAIA_MCP_HTTPS_ORIGIN"]
)
def test_tls_compose_requires_explicit_settings(certificates, missing):
    environ = compose_environment(certificates)
    environ[missing] = ""
    result = compose_config(environ)
    assert result.returncode != 0
    assert missing in result.stderr


def test_base_compose_does_not_require_tls_settings():
    environ = dict(os.environ)
    for name in ("GAIA_TLS_CERTIFICATE", "GAIA_TLS_PRIVATE_KEY", "GAIA_MCP_HTTPS_ORIGIN"):
        environ[name] = ""
    result = compose_config(environ, tls=False)
    assert result.returncode == 0, result.stderr
    nginx = json.loads(result.stdout)["services"]["nginx"]
    assert {port["target"] for port in nginx["ports"]} == {80}


def test_compose_entrypoint_renders_a_valid_nginx_configuration(certificates):
    project = "gaia-mcp-compose-" + uuid4().hex[:12]
    environ = compose_environment(certificates)
    environ["POSTGRES_VOLUME_NAME"] = project + "-postgres-data"
    command = [
        "docker",
        "compose",
        "--project-name",
        project,
        "--env-file",
        "/dev/null",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.mcp.yml",
        "-f",
        "docker-compose.mcp-tls.yml",
    ]
    try:
        result = subprocess.run(
            [*command, "run", "--rm", "--no-deps", "nginx", "nginx", "-T"],
            cwd=ROOT,
            env=environ,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr
        assert "return 308 https://canonical.example:8443$request_uri;" in result.stdout
        assert "if ($maintenance_mode = 1)" in result.stdout
        assert "proxy_set_header X-Forwarded-Proto $scheme;" in result.stdout
        assert "${GAIA_MCP_HTTPS_ORIGIN}" not in result.stdout
    finally:
        subprocess.run([*command, "down"], cwd=ROOT, env=environ, capture_output=True, timeout=60)
        volumes = docker(
            "volume",
            "ls",
            "--filter",
            "label=com.docker.compose.project=" + project,
            "--format",
            "{{.Name}}",
        )
        if volumes:
            docker("volume", "rm", *volumes.splitlines())
