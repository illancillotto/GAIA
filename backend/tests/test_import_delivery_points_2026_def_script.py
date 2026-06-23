from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "import_delivery_points_2026_def.py"
SPEC = spec_from_file_location("import_delivery_points_2026_def_script", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
script = module_from_spec(SPEC)
SPEC.loader.exec_module(script)


def test_script_main_success(monkeypatch, capsys) -> None:
    class _FakeDb:
        def rollback(self) -> None:
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr(script, "SessionLocal", lambda: _FakeDb())
    monkeypatch.setattr(
        script,
        "import_delivery_points_2026_def",
        lambda db, root_path: {
            "points_processed": 2,
            "canals_processed": 1,
            "meter_readings_linked": 3,
            "meter_readings_unlinked": 0,
        },
    )
    monkeypatch.setattr(
        script.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(root_path="/tmp/punti"),
    )

    result = script.main()

    assert result == 0
    assert "punti=2" in capsys.readouterr().out


def test_script_main_failure(monkeypatch, capsys) -> None:
    class _FakeDb:
        def __init__(self) -> None:
            self.rolled_back = False

        def rollback(self) -> None:
            self.rolled_back = True

        def close(self) -> None:
            return None

    fake_db = _FakeDb()
    monkeypatch.setattr(script, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(
        script,
        "import_delivery_points_2026_def",
        lambda db, root_path: (_ for _ in ()).throw(ValueError("boom")),
    )
    monkeypatch.setattr(
        script.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(root_path="/tmp/punti"),
    )

    result = script.main()

    assert result == 1
    assert fake_db.rolled_back is True
    assert "Import fallito" in capsys.readouterr().err
