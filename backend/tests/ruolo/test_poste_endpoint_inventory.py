import importlib.util
import json
import runpy
import stat
import sys
from pathlib import Path

import pytest

from app.modules.ruolo.services.poste_endpoint_inventory import inventory_har

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "poste_endpoint_inventory.py"


def entry(url="https://corrispondenza.poste.it/col/archivio.do?token=SECRET", **request):
    return {
        "startedDateTime": "SECRET",
        "request": {
            "method": "POST",
            "url": url,
            "cookies": [{"name": "SECRET", "value": "SECRET"}],
            "headers": [{"name": "Authorization", "value": "SECRET"}],
            "queryString": [{"name": "SECRET", "value": "SECRET"}],
            "postData": {"mimeType": "multipart/form-data; boundary=SECRET", "text": "SECRET"},
            **request,
        },
        "response": {
            "status": 200,
            "headers": [{"name": "Set-Cookie", "value": "SECRET"}],
            "content": {"mimeType": "text/html; charset=UTF-8", "text": "SECRET"},
        },
    }


def har(*entries):
    return json.dumps({"log": {"entries": list(entries)}}).encode()


def test_report_discards_secrets_and_groups_unknown_paths_only_with_per_run_hmac():
    data = har(
        entry(),
        entry("https://corrispondenza.poste.it/SECRET"),
        entry("https://corrispondenza.poste.it/SECRET?secret=another"),
    )
    result = inventory_har(data)
    assert "SECRET" not in json.dumps(result)
    assert result["submission_enabled"] is False
    observations = result["observations"]
    assert observations[0]["path"] == "/col/archivio.do"
    assert observations[0]["request_media_type"] == "multipart/form-data"
    assert observations[0]["response_media_type"] == "text/html"
    assert observations[1]["path"] == "[review-required]"
    assert observations[1]["endpoint_id"] == observations[2]["endpoint_id"]
    assert observations[0]["endpoint_id"] != observations[1]["endpoint_id"]
    assert observations[1]["endpoint_id"] != inventory_har(data)["observations"][1]["endpoint_id"]
    assert all(item["operation"] == "unclassified" for item in observations)


@pytest.mark.parametrize(
    "url",
    [
        "http://corrispondenza.poste.it/col/archivio.do",
        "https://corrispondenza.poste.it.evil.test/col/archivio.do",
        "https://evil.test/",
        "https://SECRET@corrispondenza.poste.it/",
        "https://user:SECRET@corrispondenza.poste.it/",
        "https://corrispondenza.poste.it:8080/",
    ],
)
def test_foreign_insecure_or_credential_bearing_urls_are_omitted(url):
    result = inventory_har(har(entry(url)))
    assert result["observations"] == []
    assert result["ignored_entries"] == 1


def test_reviewed_path_and_media_type_allowlist():
    row = entry("https://corrispondenza.poste.it:443/col/reviewed.do#SECRET", postData={})
    row["response"]["content"] = {"mimeType": "SECRET"}
    observation = inventory_har(har(row), reviewed_paths=frozenset({"/col/reviewed.do"}))[
        "observations"
    ][0]
    assert observation["path"] == "/col/reviewed.do"
    assert not observation["path_review_required"]
    assert observation["request_media_type"] == observation["response_media_type"] == "other"
    assert "SECRET" not in json.dumps(observation)
    row["request"].pop("postData")
    row["response"].pop("content")
    assert inventory_har(har(row))["observations"][0]["request_media_type"] == "other"


@pytest.mark.parametrize(
    "content",
    [
        b"SECRET",
        b"\xff",
        b"[]",
        b"{}",
        b'{"log":{"entries":{}}}',
        har({}),
        har(None),
        har(entry(method="SECRET")),
        har(entry("https://corrispondenza.poste.it:SECRET/")),
        har(entry(postData=None)),
        har({"request": entry()["request"], "response": {"status": True}}),
        har({"request": entry()["request"], "response": {"status": 600}}),
        har({"request": entry()["request"], "response": {"status": -1}}),
    ],
)
def test_malformed_input_has_redacted_errors(content):
    with pytest.raises(ValueError) as exc:
        inventory_har(content)
    assert "SECRET" not in str(exc.value)
    assert exc.value.__suppress_context__


def test_resource_limits_and_empty_capture():
    with pytest.raises(ValueError, match="32 MiB"):
        inventory_har(b" " * (32 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="HAR non valido"):
        inventory_har(har(*([{}] * 20001)))
    with pytest.raises(ValueError, match="HAR non valido"):
        inventory_har(b"[" * 2000 + b"0" + b"]" * 2000)
    assert inventory_har(har())["observations"] == []


def test_cli_writes_private_file_and_never_overwrites(tmp_path, monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location("poste_inventory_cli", SCRIPT)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    source, output = tmp_path / "capture.har", tmp_path / "inventory.json"
    source.write_bytes(har(entry()))
    assert cli.main([str(source), "--output", str(output)]) == 0
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert "SECRET" not in output.read_text()
    with pytest.raises(SystemExit) as exc:
        cli.main([str(source), "--output", str(output)])
    assert exc.value.code == 2
    assert "SECRET" not in capsys.readouterr().err
    assert json.loads(output.read_text())["submission_enabled"] is False
    with pytest.raises(SystemExit):
        cli.main([str(tmp_path / "SECRET"), "--output", str(output)])
    assert "SECRET" not in capsys.readouterr().err
    source.write_bytes(b"SECRET")
    with pytest.raises(SystemExit):
        cli.main([str(source), "--output", str(tmp_path / "new")])
    assert not (tmp_path / "new").exists()

    source.write_bytes(har(entry()))
    monkeypatch.setattr(
        sys, "argv", [str(SCRIPT), str(source), "--output", str(tmp_path / "run.json")]
    )
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert exc.value.code == 0
