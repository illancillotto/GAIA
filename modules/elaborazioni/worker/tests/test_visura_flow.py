import asyncio
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


WORKER_ROOT = Path(__file__).resolve().parents[1]

if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from visura_flow import ManualCaptchaDecision, execute_visura_flow


class FakeRequest:
    id = "req-1"
    search_mode = "immobile"


class FakeCaptchaSolver:
    def solve(self, _image_bytes: bytes) -> str | None:
        return None


class FakeBrowser:
    def __init__(self) -> None:
        self.submit_attempts: list[str] = []
        self.captcha_captures = 0

    async def open_visura_form(self) -> None:
        return None

    async def fill_visura_form(self, _request) -> None:
        return None

    async def prepare_captcha_or_download(self) -> str:
        return "captcha"

    async def open_subject_form(self, _subject_kind: str) -> None:
        return None

    async def fill_subject_form(self, _request) -> None:
        return None

    async def search_subject_and_open_visura(self, _request) -> str | None:
        return None

    async def capture_captcha_image(self) -> bytes:
        self.captcha_captures += 1
        return b"fake-captcha"

    async def submit_captcha(self, text: str) -> bool:
        self.submit_attempts.append(text)
        return text == "AB12"

    async def download_pdf(self, document_path: Path) -> int:
        document_path.parent.mkdir(parents=True, exist_ok=True)
        document_path.write_bytes(b"%PDF-1.4\n")
        return document_path.stat().st_size


def test_visura_flow_uses_external_fallback_before_manual() -> None:
    browser = FakeBrowser()
    operations: list[str] = []

    async def fake_external_solver(_image_bytes: bytes) -> str | None:
        return "AB12"

    async def fake_manual_solver(_image_path: Path) -> ManualCaptchaDecision:
        raise AssertionError("Manual CAPTCHA should not be requested")

    with TemporaryDirectory() as tmp_dir:
        result = asyncio.run(
            execute_visura_flow(
                browser=browser,
                request=FakeRequest(),
                document_path=Path(tmp_dir) / "visura.pdf",
                captcha_dir=Path(tmp_dir) / "captcha",
                captcha_solver=FakeCaptchaSolver(),
                max_ocr_attempts=1,
                get_manual_captcha_decision=fake_manual_solver,
                solve_external_captcha=fake_external_solver,
                update_operation=operations.append,
            )
        )

    assert result.status == "completed"
    assert result.captcha_method == "external"
    assert "Tentativo CAPTCHA servizio esterno" in operations
    assert browser.submit_attempts == ["AB12"]


def test_visura_flow_marks_subject_not_found_as_terminal() -> None:
    class SubjectRequest(FakeRequest):
        search_mode = "soggetto"
        subject_kind = "PF"
        subject_id = "RSSMRA80A01H501U"
        request_type = "ATTUALITA"

    class SubjectNotFoundBrowser(FakeBrowser):
        async def search_subject_and_open_visura(self, _request) -> str | None:
            return "Nessuna corrispondenza catastale per PF 'RSSMRA80A01H501U'"

    browser = SubjectNotFoundBrowser()
    operations: list[str] = []

    async def fake_manual_solver(_image_path: Path) -> ManualCaptchaDecision:
        raise AssertionError("Manual CAPTCHA should not be requested for not_found")

    with TemporaryDirectory() as tmp_dir:
        result = asyncio.run(
            execute_visura_flow(
                browser=browser,
                request=SubjectRequest(),
                document_path=Path(tmp_dir) / "visura.pdf",
                captcha_dir=Path(tmp_dir) / "captcha",
                captcha_solver=FakeCaptchaSolver(),
                max_ocr_attempts=1,
                get_manual_captcha_decision=fake_manual_solver,
                solve_external_captcha=None,
                update_operation=operations.append,
            )
        )

    assert result.status == "not_found"
    assert "Nessuna corrispondenza" in (result.error_message or "")
    assert "Ricerca soggetto" in operations


def test_visura_flow_status_scan_downloads_historical_pdf() -> None:
    class ScanRequest(FakeRequest):
        purpose = "ade_status_scan"
        search_mode = "immobile"
        request_type = "STORICA"
        tipo_visura = "Sintetica"

    class StatusBrowser(FakeBrowser):
        pass

    browser = StatusBrowser()
    operations: list[str] = []

    async def fake_external_solver(_image_bytes: bytes) -> str | None:
        return "AB12"

    async def fake_manual_solver(_image_path: Path) -> ManualCaptchaDecision:
        raise AssertionError("Manual CAPTCHA should not be requested")

    with TemporaryDirectory() as tmp_dir:
        result = asyncio.run(
            execute_visura_flow(
                browser=browser,
                request=ScanRequest(),
                document_path=Path(tmp_dir) / "visura.pdf",
                captcha_dir=Path(tmp_dir) / "captcha",
                captcha_solver=FakeCaptchaSolver(),
                max_ocr_attempts=1,
                get_manual_captcha_decision=fake_manual_solver,
                solve_external_captcha=fake_external_solver,
                update_operation=operations.append,
            )
        )

    assert result.status == "completed"
    assert result.file_path is not None
    assert result.file_size is not None
    assert "Download PDF in corso" in operations
    assert browser.submit_attempts == ["AB12"]


def test_visura_flow_downloads_when_sister_skips_captcha_after_inoltra() -> None:
    class DownloadReadyBrowser(FakeBrowser):
        async def prepare_captcha_or_download(self) -> str:
            return "download"

    browser = DownloadReadyBrowser()
    operations: list[str] = []

    async def fake_manual_solver(_image_path: Path) -> ManualCaptchaDecision:
        raise AssertionError("Manual CAPTCHA should not be requested")

    with TemporaryDirectory() as tmp_dir:
        result = asyncio.run(
            execute_visura_flow(
                browser=browser,
                request=FakeRequest(),
                document_path=Path(tmp_dir) / "visura.pdf",
                captcha_dir=Path(tmp_dir) / "captcha",
                captcha_solver=FakeCaptchaSolver(),
                max_ocr_attempts=1,
                get_manual_captcha_decision=fake_manual_solver,
                solve_external_captcha=None,
                update_operation=operations.append,
            )
        )

    assert result.status == "completed"
    assert result.file_path is not None
    assert result.file_size is not None
    assert "Download PDF in corso" in operations
    assert browser.captcha_captures == 0
    assert browser.submit_attempts == []


def test_visura_flow_accepts_manual_captcha_after_ocr_failure() -> None:
    browser = FakeBrowser()
    operations: list[str] = []
    manual_paths: list[Path] = []

    async def fake_manual_solver(image_path: Path) -> ManualCaptchaDecision:
        manual_paths.append(image_path)
        assert image_path.exists()
        return ManualCaptchaDecision(text="AB12")

    with TemporaryDirectory() as tmp_dir:
        result = asyncio.run(
            execute_visura_flow(
                browser=browser,
                request=FakeRequest(),
                document_path=Path(tmp_dir) / "visura.pdf",
                captcha_dir=Path(tmp_dir) / "captcha",
                captcha_solver=FakeCaptchaSolver(),
                max_ocr_attempts=1,
                get_manual_captcha_decision=fake_manual_solver,
                solve_external_captcha=None,
                update_operation=operations.append,
            )
        )

    assert result.status == "completed"
    assert result.captcha_method == "manual"
    assert result.last_ocr_text == "AB12"
    assert browser.submit_attempts == ["AB12"]
    assert len(manual_paths) == 1
    assert "Richiesta CAPTCHA manuale" in operations


def test_visura_flow_skips_when_manual_captcha_is_skipped() -> None:
    browser = FakeBrowser()

    async def fake_manual_solver(_image_path: Path) -> ManualCaptchaDecision:
        return ManualCaptchaDecision(text=None, skip=True)

    with TemporaryDirectory() as tmp_dir:
        result = asyncio.run(
            execute_visura_flow(
                browser=browser,
                request=FakeRequest(),
                document_path=Path(tmp_dir) / "visura.pdf",
                captcha_dir=Path(tmp_dir) / "captcha",
                captcha_solver=FakeCaptchaSolver(),
                max_ocr_attempts=1,
                get_manual_captcha_decision=fake_manual_solver,
                solve_external_captcha=None,
                update_operation=None,
            )
        )

    assert result.status == "skipped"
    assert result.captcha_method == "manual"
    assert "Skipped after manual CAPTCHA request" in (result.error_message or "")
    assert browser.submit_attempts == []


def test_visura_flow_fails_when_manual_captcha_is_rejected() -> None:
    browser = FakeBrowser()

    async def fake_manual_solver(_image_path: Path) -> ManualCaptchaDecision:
        return ManualCaptchaDecision(text="WRONG")

    with TemporaryDirectory() as tmp_dir:
        result = asyncio.run(
            execute_visura_flow(
                browser=browser,
                request=FakeRequest(),
                document_path=Path(tmp_dir) / "visura.pdf",
                captcha_dir=Path(tmp_dir) / "captcha",
                captcha_solver=FakeCaptchaSolver(),
                max_ocr_attempts=1,
                get_manual_captcha_decision=fake_manual_solver,
                solve_external_captcha=None,
                update_operation=None,
            )
        )

    assert result.status == "failed"
    assert result.captcha_method == "manual"
    assert "Manual CAPTCHA solution rejected" in (result.error_message or "")
    assert browser.submit_attempts == ["WRONG"]
