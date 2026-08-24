from __future__ import annotations

import importlib.util
from pathlib import Path
import runpy
import sys

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "backfill_catasto_document_audits.py"


def _load_script(*, without_backend_path: bool = False):
    backend_root = str(SCRIPT_PATH.parents[1])
    original_path = list(sys.path)
    if without_backend_path:
        sys.path[:] = [entry for entry in sys.path if entry != backend_root]
    spec = importlib.util.spec_from_file_location("backfill_catasto_document_audits_under_test", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original_path
    return module


class _Session:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_positive_int_validation() -> None:
    module = _load_script()
    assert module._positive_int("2") == 2
    with pytest.raises(Exception, match="maggiore di zero"):
        module._positive_int("0")


def test_script_adds_backend_root_when_missing() -> None:
    assert _load_script(without_backend_path=True).BACKEND_ROOT == SCRIPT_PATH.parents[1]


@pytest.mark.parametrize("apply", [False, True])
def test_main_passes_cli_options_and_prints_summary(monkeypatch, capsys, apply) -> None:
    module = _load_script()
    calls = []
    monkeypatch.setattr(module, "SessionLocal", _Session)
    monkeypatch.setattr(
        module,
        "backfill_document_audits",
        lambda _db, **kwargs: calls.append(kwargs) or {"selected": 2, "updated": int(apply)},
    )
    args = [str(SCRIPT_PATH), "--batch-id", "00000000-0000-0000-0000-000000000001", "--limit", "2"]
    if apply:
        args.extend(["--apply", "--force", "--commit-every", "1"])
    monkeypatch.setattr(sys, "argv", args)

    assert module.main() == 0
    assert calls[0]["dry_run"] is not apply
    assert calls[0]["force"] is apply
    expected_mode = "APPLY" if apply else "DRY-RUN"
    assert expected_mode in capsys.readouterr().out


def test_script_main_entrypoint(monkeypatch) -> None:
    import app.core.database as database_module
    import app.modules.catasto.services.ade_document_audit_backfill as service_module

    monkeypatch.setattr(database_module, "SessionLocal", _Session)
    monkeypatch.setattr(service_module, "backfill_document_audits", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH)])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
    assert exc_info.value.code == 0
