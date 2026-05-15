import asyncio
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


WORKER_ROOT = Path(__file__).resolve().parents[1]

if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from sister_exceptions import DocumentNonEvadibileError, DocumentNotYetProducedError
from visura_flow import ManualCaptchaDecision, execute_visura_flow


class FakeRequest:
    id = "req-1"
    search_mode = "immobile"
    purpose = "visura_pdf"


class FakeBrowser:
    def __init__(self, correct_answer: str = "neorave") -> None:
        self.submit_attempts: list[str] = []
        self.captcha_captures = 0
        self.reload_calls = 0
        self._correct = correct_answer

    async def open_visura_form(self) -> None: ...
    async def fill_visura_form(self, _request) -> None: ...
    async def prepare_captcha_or_download(self) -> str: return "captcha"
    async def open_subject_form(self, _kind: str) -> None: ...
    async def fill_subject_form(self, _request) -> None: ...
    async def search_subject_and_open_visura(self, _request) -> str | None: return None

    async def reload_captcha(self) -> None:
        self.reload_calls += 1

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

    async def poll_richieste_for_download(self, destination: Path, richieste_url: str | None = None) -> int:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"%PDF-1.4\n")
        return destination.stat().st_size


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


# ---------------------------------------------------------------------------
# Flusso soggetto (CF)
# ---------------------------------------------------------------------------

class SubjectRequest(FakeRequest):
    search_mode = "soggetto"
    subject_kind = "PF"
    subject_id = "RSSMRA80A01H501U"
    request_type = "ATTUALITA"


def test_subject_captcha_flow_completes() -> None:
    """Flusso soggetto: search → CAPTCHA → download."""
    class SubjectBrowser(FakeBrowser):
        def __init__(self) -> None:
            super().__init__(correct_answer="neorave")
            self.search_called = False

        async def open_subject_form(self, _kind: str) -> None: ...
        async def fill_subject_form(self, _request) -> None: ...
        async def search_subject_and_open_visura(self, _request) -> str | None:
            self.search_called = True
            return None

    browser = SubjectBrowser()

    async def fake_llm(_b: bytes) -> str | None:
        return "neorave"

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=SubjectRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            solve_llm_captcha=fake_llm,
        )

    assert result.status == "completed"
    assert browser.search_called
    assert browser.submit_attempts == ["neorave"]


def test_subject_skips_captcha_when_download_ready() -> None:
    """Se SISTER mostra il pulsante Salva subito dopo la ricerca soggetto, non chiede CAPTCHA."""
    class EarlyDownloadBrowser(FakeBrowser):
        async def open_subject_form(self, _kind: str) -> None: ...
        async def fill_subject_form(self, _request) -> None: ...
        async def search_subject_and_open_visura(self, _request) -> str | None:
            return None
        async def prepare_captcha_or_download(self) -> str:
            return "download"

    browser = EarlyDownloadBrowser()

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=SubjectRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
        )

    assert result.status == "completed"
    assert browser.captcha_captures == 0
    assert browser.submit_attempts == []


def test_subject_not_yet_produced_goes_to_polling() -> None:
    """DocumentNotYetProducedError da prepare_captcha_or_download nel branch soggetto."""
    class PollingBrowser(FakeBrowser):
        async def open_subject_form(self, _kind: str) -> None: ...
        async def fill_subject_form(self, _request) -> None: ...
        async def search_subject_and_open_visura(self, _request) -> str | None:
            return None
        async def prepare_captcha_or_download(self) -> str:
            raise DocumentNotYetProducedError(richieste_url="https://sister/richieste")

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=PollingBrowser(),
            request=SubjectRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
        )
        assert result.status == "completed"
        assert Path(result.file_path).exists()


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


# ---------------------------------------------------------------------------
# DocumentNotYetProducedError / polling
# ---------------------------------------------------------------------------

def test_document_not_yet_produced_during_submit_goes_to_polling() -> None:
    """SISTER accetta il CAPTCHA ma il documento non è ancora pronto → polling."""
    class PollingBrowser(FakeBrowser):
        async def submit_captcha(self, text: str) -> bool:
            raise DocumentNotYetProducedError(richieste_url="https://sister/richieste")

    browser = PollingBrowser()

    async def fake_llm(_b: bytes) -> str | None:
        return "qualsiasi"

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            solve_llm_captcha=fake_llm,
        )
        assert result.status == "completed"
        assert Path(result.file_path).exists()


def test_document_not_yet_produced_during_prepare_goes_to_polling() -> None:
    """SISTER non mostra CAPTCHA ma il documento non è pronto → polling diretto."""
    class EarlyPollingBrowser(FakeBrowser):
        async def prepare_captcha_or_download(self) -> str:
            raise DocumentNotYetProducedError(richieste_url="https://sister/richieste")

    browser = EarlyPollingBrowser()

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


def test_non_evadibile_during_polling_returns_correct_status() -> None:
    """Il polling ConsultazioneRichieste rileva richiesta non evadibile."""
    class NonEvadibileBrowser(FakeBrowser):
        async def submit_captcha(self, text: str) -> bool:
            raise DocumentNotYetProducedError(richieste_url="https://sister/richieste")

        async def poll_richieste_for_download(self, destination: Path, richieste_url: str | None = None) -> int:
            raise DocumentNonEvadibileError("non evadibile")

    async def fake_llm(_b: bytes) -> str | None:
        return "qualsiasi"

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=NonEvadibileBrowser(),
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            solve_llm_captcha=fake_llm,
        )

    assert result.status == "non_evadibile"
    assert result.error_message is not None


# ---------------------------------------------------------------------------
# reload_captcha tra i tentativi
# ---------------------------------------------------------------------------

def test_reload_captcha_called_between_llm_attempts() -> None:
    """reload_captcha deve essere chiamato dopo ogni tentativo fallito, non dopo l'ultimo."""
    browser = FakeBrowser(correct_answer="neorave")
    call_count = 0

    async def fake_llm(_b: bytes) -> str | None:
        nonlocal call_count
        call_count += 1
        return "neorave" if call_count == 3 else "wrong"

    with TemporaryDirectory() as tmp:
        run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            solve_llm_captcha=fake_llm,
            max_llm_attempts=3,
        )

    # 2 tentativi falliti → 2 reload; il terzo riesce → nessun reload dopo
    assert browser.reload_calls == 2


def test_reload_captcha_called_between_external_attempts() -> None:
    ext_calls = 0

    async def flaky_ext(_b: bytes) -> str | None:
        nonlocal ext_calls
        ext_calls += 1
        return "neorave" if ext_calls == 2 else "wrong"

    browser = FakeBrowser(correct_answer="neorave")
    with TemporaryDirectory() as tmp:
        run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            solve_llm_captcha=None,
            solve_external_captcha=flaky_ext,
            max_external_attempts=3,
        )

    assert browser.reload_calls == 1


# ---------------------------------------------------------------------------
# LLM restituisce None / stringa vuota
# ---------------------------------------------------------------------------

def test_llm_none_result_falls_through_to_manual() -> None:
    """Se LLM restituisce sempre None, il flusso deve arrivare al manuale."""
    browser = FakeBrowser(correct_answer="neorave")
    manual_called = False

    async def none_llm(_b: bytes) -> str | None:
        return None

    async def manual(_p: Path) -> ManualCaptchaDecision:
        nonlocal manual_called
        manual_called = True
        return ManualCaptchaDecision(text="neorave")

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=manual,
            solve_llm_captcha=none_llm,
            max_llm_attempts=3,
        )

    assert result.status == "completed"
    assert result.captcha_method == "manual"
    assert manual_called
    assert browser.submit_attempts == ["neorave"]


# ---------------------------------------------------------------------------
# update_operation callback
# ---------------------------------------------------------------------------

def test_update_operation_fires_during_polling() -> None:
    """update_operation deve essere chiamata quando il flusso entra in polling."""
    class PollingBrowser(FakeBrowser):
        async def submit_captcha(self, text: str) -> bool:
            raise DocumentNotYetProducedError(richieste_url="https://sister/richieste")

    operations: list[str] = []

    async def fake_llm(_b: bytes) -> str | None:
        return "qualsiasi"

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=PollingBrowser(),
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            solve_llm_captcha=fake_llm,
            update_operation=operations.append,
        )

    assert result.status == "completed"
    assert any("ConsultazioneRichieste" in op for op in operations)


def test_update_operation_fires_on_immobile_direct_download() -> None:
    """update_operation('Download PDF in corso') deve essere chiamata nel branch download diretto immobile."""
    class DownloadReadyBrowser(FakeBrowser):
        async def prepare_captcha_or_download(self) -> str:
            return "download"

    operations: list[str] = []

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=DownloadReadyBrowser(),
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            update_operation=operations.append,
        )

    assert result.status == "completed"
    assert any("Download PDF" in op for op in operations)


def test_update_operation_fires_on_subject_flow() -> None:
    """update_operation deve essere chiamata nelle fasi apertura/compilazione/ricerca soggetto."""
    class SubjectBrowser(FakeBrowser):
        async def open_subject_form(self, _kind: str) -> None: ...
        async def fill_subject_form(self, _request) -> None: ...
        async def search_subject_and_open_visura(self, _request) -> str | None:
            return None

    operations: list[str] = []

    async def fake_llm(_b: bytes) -> str | None:
        return "neorave"

    browser = SubjectBrowser(correct_answer="neorave")

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=SubjectRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            solve_llm_captcha=fake_llm,
            update_operation=operations.append,
        )

    assert result.status == "completed"
    assert any("soggetto" in op.lower() for op in operations)


def test_update_operation_fires_on_subject_direct_download() -> None:
    """update_operation('Download PDF in corso') nel branch download diretto soggetto."""
    class EarlyDownloadBrowser(FakeBrowser):
        async def open_subject_form(self, _kind: str) -> None: ...
        async def fill_subject_form(self, _request) -> None: ...
        async def search_subject_and_open_visura(self, _request) -> str | None:
            return None
        async def prepare_captcha_or_download(self) -> str:
            return "download"

    operations: list[str] = []

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=EarlyDownloadBrowser(),
            request=SubjectRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=_no_manual_async,
            update_operation=operations.append,
        )

    assert result.status == "completed"
    assert any("Download PDF" in op for op in operations)


def test_update_operation_fires_before_manual_captcha() -> None:
    """update_operation('Richiesta CAPTCHA manuale') deve essere chiamata prima del manuale."""
    operations: list[str] = []

    async def manual(_p: Path) -> ManualCaptchaDecision:
        return ManualCaptchaDecision(text="neorave")

    browser = FakeBrowser(correct_answer="neorave")

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=manual,
            update_operation=operations.append,
        )

    assert result.status == "completed"
    assert any("manuale" in op.lower() for op in operations)


# ---------------------------------------------------------------------------
# External solver: stringa vuota
# ---------------------------------------------------------------------------

def test_external_empty_string_falls_through_to_manual() -> None:
    """Se external restituisce '' (stringa vuota) il flusso deve arrivare al manuale."""
    browser = FakeBrowser(correct_answer="neorave")
    manual_called = False

    async def empty_ext(_b: bytes) -> str | None:
        return ""

    async def manual(_p: Path) -> ManualCaptchaDecision:
        nonlocal manual_called
        manual_called = True
        return ManualCaptchaDecision(text="neorave")

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=manual,
            solve_llm_captcha=None,
            solve_external_captcha=empty_ext,
            max_external_attempts=2,
        )

    assert result.status == "completed"
    assert result.captcha_method == "manual"
    assert manual_called


# ---------------------------------------------------------------------------
# Manuale: text=None senza skip
# ---------------------------------------------------------------------------

def test_manual_null_text_without_skip_returns_failed() -> None:
    """ManualCaptchaDecision(text=None, skip=False) deve restituire status=failed."""
    browser = FakeBrowser()

    async def manual(_p: Path) -> ManualCaptchaDecision:
        return ManualCaptchaDecision(text=None, skip=False)

    with TemporaryDirectory() as tmp:
        result = run_flow(
            browser=browser,
            request=FakeRequest(),
            document_path=Path(tmp) / "visura.pdf",
            captcha_dir=Path(tmp) / "captcha",
            get_manual_captcha_decision=manual,
        )

    assert result.status == "failed"
    assert "missing" in (result.error_message or "").lower()
    assert result.captcha_method == "manual"
