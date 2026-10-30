import fcntl
import subprocess
from pathlib import Path

import pytest

from app.modules.ruolo.services import notice_html_pdf


def _lock_is_free(path: Path) -> bool:
    with path.open("a") as other:
        try:
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(other, fcntl.LOCK_UN)
        return True


def test_chromium_renders_one_at_a_time_with_a_time_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / "render.lock"
    monkeypatch.setattr(notice_html_pdf, "RENDER_LOCK_PATH", lock_path)
    seen = {}

    def fake_run(args: list[str], **kwargs: object) -> None:
        seen["args"], seen["timeout"] = args, kwargs["timeout"]
        seen["lock_free_during_render"] = _lock_is_free(lock_path)
        Path(args[-2].removeprefix("--print-to-pdf=")).write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(notice_html_pdf.subprocess, "run", fake_run)
    pdf = notice_html_pdf._render_gaia_html_to_pdf(
        "<p>avviso</p>", chromium_binary="chrome", working_dir=tmp_path, stem="a"
    )

    assert pdf.read_bytes() == b"%PDF-1.4"
    assert seen["timeout"] == notice_html_pdf.RENDER_TIMEOUT_SECONDS
    assert "--disable-dev-shm-usage" in seen["args"]
    assert seen["lock_free_during_render"] is False
    assert _lock_is_free(lock_path)


def test_a_stuck_chromium_releases_the_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / "render.lock"
    monkeypatch.setattr(notice_html_pdf, "RENDER_LOCK_PATH", lock_path)

    def stuck(args: list[str], **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    monkeypatch.setattr(notice_html_pdf.subprocess, "run", stuck)
    with pytest.raises(subprocess.TimeoutExpired):
        notice_html_pdf._render_gaia_html_to_pdf(
            "<p>avviso</p>", chromium_binary="chrome", working_dir=tmp_path, stem="a"
        )
    assert _lock_is_free(lock_path)
