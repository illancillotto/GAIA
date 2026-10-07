import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_lan_release_is_isolated_and_disabled_even_if_backend_env_enables_oauth(tmp_path):
    release = ROOT / "config/mcps/lan-release"
    shutil.copyfile(release / "compose.yml", tmp_path / "compose.yml")
    shutil.copyfile(release / "connector.env", tmp_path / "connector.env")
    backend_env = tmp_path / "backend.env"
    backend_env.write_text("GAIA_MCP_OAUTH_ENABLED=true\n")
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "-f",
            str(tmp_path / "compose.yml"),
            "config",
            "--format",
            "json",
        ],
        env={
            **os.environ,
            "GAIA_MCP_RELEASE_IMAGE": "gaia-mcp-release:test",
            "GAIA_MCP_BACKEND_ENV_FILE": str(backend_env),
            "GAIA_MCP_NETWORK": "gaia_default",
        },
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )
    config = json.loads(result.stdout)
    assert set(config["services"]) == {"connector"}
    connector = config["services"]["connector"]
    assert connector["environment"]["GAIA_MCP_OAUTH_ENABLED"] == "false"
    assert (
        connector["environment"]["GAIA_MCP_OAUTH_RESOURCE"]
        == "https://gaia.lan/api/wiki/mcp/connector/data"
    )
    assert connector["ports"][0]["host_ip"] == "127.0.0.1"
    assert connector["ports"][0]["published"] == "8769"
    assert connector["read_only"] is True
    assert connector["cap_drop"] == ["ALL"]
    assert connector["security_opt"] == ["no-new-privileges:true"]
    assert connector["entrypoint"] == []
    assert "--no-access-log" in connector["command"]
    assert {mount["target"] for mount in connector["volumes"]} == {
        "/mcp-config",
        "/mcp-data",
        "/mcp-oauth",
        "/mcp-audit",
    }
    readonly = {mount["target"] for mount in connector["volumes"] if mount.get("read_only")}
    assert readonly == {"/mcp-config", "/mcp-data"}
    assert config["networks"]["gaia"]["external"] is True
    assert config["networks"]["gaia"]["name"] == "gaia_default"


@pytest.mark.parametrize(
    "required", ["GAIA_MCP_RELEASE_IMAGE", "GAIA_MCP_BACKEND_ENV_FILE", "GAIA_MCP_NETWORK"]
)
def test_lan_release_refuses_missing_deployment_inputs(tmp_path, required):
    release = ROOT / "config/mcps/lan-release"
    shutil.copyfile(release / "compose.yml", tmp_path / "compose.yml")
    shutil.copyfile(release / "connector.env", tmp_path / "connector.env")
    backend_env = tmp_path / "backend.env"
    backend_env.write_text("GAIA_MCP_OAUTH_ENABLED=false\n")
    environ = {
        **os.environ,
        "GAIA_MCP_RELEASE_IMAGE": "gaia-mcp-release:test",
        "GAIA_MCP_BACKEND_ENV_FILE": str(backend_env),
        "GAIA_MCP_NETWORK": "gaia_default",
    }
    environ.pop(required)
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "-f",
            str(tmp_path / "compose.yml"),
            "config",
            "--quiet",
        ],
        env=environ,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert required in result.stderr
