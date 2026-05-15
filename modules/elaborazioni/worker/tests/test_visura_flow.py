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
    purpose = "visura_pdf"


class FakeBrowser:
    def __init__(self, correct_answer: str = "neorave") -> None:
        self.submit_attempts: list[str] = []
        self.captcha_captures = 0
        self._correct = correct_answer

    async def open_visura_form(self) -> None: ...
    async def fill_visura_form(self, _request) -> None: ...
    async def prepare_captcha_or_download(self) -> str: return "captcha"
    async def open_subject_form(self, _kind: str) -> None: ...
    async def fill_subject_form(self, _request) -> None: ...
    async def search_subject_and_open_visura(self, _request) -> str | None: return None

    async def reload_captcha(self) -> None:
        pass

    async def capture_captcha_image(self) -> bytes:
        self.captcha_captures += 1
        return b"fake-captcha"

    async def submit_captcha(self, text: str) -> bool:
        self.submit_attempts.append(text)
        return text == self._correct

    async def download_pdf(self, document_path: Path) -> int:
        document_path.parent.mkdir(parents=True, exist_ok=True)
        document_path.write_bytes(b"%PDF-1.4\n")
        return document_path.stat().st_size


def _no_manual(_image_path: Path) -> ManualCaptchaDecision:
    raise AssertionError("Manual CAPTCHA should not be requested")


async def _no_manual_async(image_path: Path) -> ManualCaptchaDecision:
    return _no_manual(image_path)


def run_flow(**kwargs):
    return asyncio.run(execute_visura_flow(**kwargs))


# ---------------------------------------------------------------------------
# LLM (Agent locale)
# ---------------------------------------------------------------------------

def test_llm_solver_succeeds_on_first_attempt() -> None:
    browser = FakeBrowser(correct_answer="neorave")
    operations: list[str] = []

    async def fake_llm(_bytes: bytes) -> str | None:
        return "neorave"

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            solve_llm_captcha=fake_llm,
            update_operation=operations.append,
        )

    assert result.status == "completed"
    assert result.captcha_method == "llm"
    assert browser.submit_attempts == ["neorave"]
    assert any("Agent (1/3)" in op for op in operations)


def test_llm_solver_retries_up_to_max_attempts() -> None:
    browser = FakeBrowser(correct_answer="neorave")
    call_count = 0

    async def fake_llm(_bytes: bytes) -> str | None:
        nonlocal call_count
        call_count += 1
        return "neorave" if call_count == 3 else "wrong"

    async def manual(_p: Path) -> ManualCaptchaDecision:
        raise AssertionError("should not reach manual")

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=manual,
            solve_llm_captcha=fake_llm,
            max_llm_attempts=3,
        )

    assert result.status == "completed"
    assert call_count == 3
    assert browser.submit_attempts == ["wrong", "wrong", "neorave"]


def test_llm_solver_images_are_numbered_per_attempt() -> None:
    browser = FakeBrowser(correct_answer="neorave")

    async def always_wrong(_bytes: bytes) -> str | None:
        return "wrong"

    async def manual(p: Path) -> ManualCaptchaDecision:
        return ManualCaptchaDecision(text=None, skip=True)

    with TemporaryDirectory() as tmp:
        captcha_dir = Path(tmp) / "captcha"
        run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=captcha_dir,
            get_manual_captcha_decision=manual,
            solve_llm_captcha=always_wrong,
            max_llm_attempts=3,
        )
        saved = sorted(captcha_dir.glob("*_llm_*.png"))

    assert len(saved) == 3
    assert saved[0].name.endswith("_llm_1.png")
    assert saved[2].name.endswith("_llm_3.png")


# ---------------------------------------------------------------------------
# External (Anti-Captcha)
# ---------------------------------------------------------------------------

def test_external_solver_used_after_llm_exhausted() -> None:
    browser = FakeBrowser(correct_answer="neorave")
    operations: list[str] = []

    async def always_wrong_llm(_bytes: bytes) -> str | None:
        return "wrong"

    async def correct_external(_bytes: bytes) -> str | None:
        return "neorave"

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            solve_llm_captcha=always_wrong_llm,
            solve_external_captcha=correct_external,
            max_llm_attempts=2,
            max_external_attempts=3,
            update_operation=operations.append,
        )

    assert result.status == "completed"
    assert result.captcha_method == "external"
    assert any("Anti-Captcha" in op for op in operations)


def test_external_solver_retries_up_to_max_attempts() -> None:
    browser = FakeBrowser(correct_answer="neorave")
    ext_calls = 0

    async def flaky_external(_bytes: bytes) -> str | None:
        nonlocal ext_calls
        ext_calls += 1
        return "neorave" if ext_calls == 2 else "wrong"

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            solve_llm_captcha=None,
            solve_external_captcha=flaky_external,
            max_external_attempts=3,
        )

    assert result.status == "completed"
    assert ext_calls == 2


def test_external_images_are_numbered_per_attempt() -> None:
    browser = FakeBrowser(correct_answer="x")

    async def always_wrong(_bytes: bytes) -> str | None:
        return "wrong"

    async def manual(p: Path) -> ManualCaptchaDecision:
        return ManualCaptchaDecision(text=None, skip=True)

    with TemporaryDirectory() as tmp:
        captcha_dir = Path(tmp) / "captcha"
        run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=captcha_dir,
            get_manual_captcha_decision=manual,
            solve_llm_captcha=None,
            solve_external_captcha=always_wrong,
            max_external_attempts=3,
        )
        saved = sorted(captcha_dir.glob("*_external_*.png"))

    assert len(saved) == 3
    assert saved[0].name.endswith("_external_1.png")
    assert saved[2].name.endswith("_external_3.png")


# ---------------------------------------------------------------------------
# Manuale
# ---------------------------------------------------------------------------

def test_manual_reached_after_all_automated_fail() -> None:
    browser = FakeBrowser(correct_answer="neorave")
    manual_called = False

    async def fake_llm(_b: bytes) -> str | None:
        return "wrong"

    async def fake_ext(_b: bytes) -> str | None:
        return "wrong"

    async def manual(p: Path) -> ManualCaptchaDecision:
        nonlocal manual_called
        manual_called = True
        assert p.exists()
        return ManualCaptchaDecision(text="neorave")

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=manual,
            solve_llm_captcha=fake_llm,
            solve_external_captcha=fake_ext,
            max_llm_attempts=2,
            max_external_attempts=2,
        )

    assert result.status == "completed"
    assert result.captcha_method == "manual"
    assert manual_called


def test_manual_skip_returns_skipped_status() -> None:
    browser = FakeBrowser()

    async def manual(_p: Path) -> ManualCaptchaDecision:
        return ManualCaptchaDecision(text=None, skip=True)

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=manual,
        )

    assert result.status == "skipped"
    assert result.captcha_method == "manual"


def test_manual_wrong_answer_returns_failed_status() -> None:
    browser = FakeBrowser(correct_answer="neorave")

    async def manual(_p: Path) -> ManualCaptchaDecision:
        return ManualCaptchaDecision(text="wrong")

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=manual,
        )

    assert result.status == "failed"
    assert "rejected" in (result.error_message or "")


# ---------------------------------------------------------------------------
# Casi speciali
# ---------------------------------------------------------------------------

def test_no_captcha_when_sister_skips_after_inoltra() -> None:
    class DownloadReadyBrowser(FakeBrowser):
        async def prepare_captcha_or_download(self) -> str:
            return "download"

    browser = DownloadReadyBrowser()

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
        )

    assert result.status == "completed"
    assert browser.captcha_captures == 0
    assert browser.submit_attempts == []


def test_subject_not_found_returns_terminal_status() -> None:
    class SubjectRequest(FakeRequest):
        search_mode = "soggetto"
        subject_kind = "PF"
        subject_id = "RSSMRA80A01H501U"
        request_type = "ATTUALITA"

    class NotFoundBrowser(FakeBrowser):
        async def search_subject_and_open_visura(self, _r) -> str | None:
            return "Nessuna corrispondenza catastale per PF 'RSSMRA80A01H501U'"

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=NotFoundBrowser(),
            request=SubjectRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
        )

    assert result.status == "not_found"
    assert "Nessuna corrispondenza" in (result.error_message or "")


def test_ade_scan_rejects_soggetto_mode() -> None:
    class ScanSoggettoRequest(FakeRequest):
        purpose = "ade_status_scan"
        search_mode = "soggetto"

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=FakeBrowser(),
            request=ScanSoggettoRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
        )

    assert result.status == "failed"
    assert "immobile" in (result.error_message or "")


def test_llm_exception_does_not_crash_flow() -> None:
    browser = FakeBrowser(correct_answer="neorave")

    async def crashing_llm(_b: bytes) -> str | None:
        raise RuntimeError("agent crashed")

    async def manual(_p: Path) -> ManualCaptchaDecision:
        return ManualCaptchaDecision(text="neorave")

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=manual,
            solve_llm_captcha=crashing_llm,
            max_llm_attempts=2,
        )

    assert result.status == "completed"


def test_external_exception_does_not_crash_flow() -> None:
    browser = FakeBrowser(correct_answer="neorave")

    async def crashing_ext(_b: bytes) -> str | None:
        raise RuntimeError("anti-captcha down")

    async def manual(_p: Path) -> ManualCaptchaDecision:
        return ManualCaptchaDecision(text="neorave")

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=manual,
            solve_llm_captcha=None,
            solve_external_captcha=crashing_ext,
            max_external_attempts=2,
        )

    assert result.status == "completed"
