from io import BytesIO
from pathlib import Path
import sys

from PIL import Image


WORKER_ROOT = Path(__file__).resolve().parents[1]

if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from captcha_solver import CaptchaSolver, OCR_CONFIG


def test_captcha_solver_uses_expected_tesseract_profile(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_image_to_string(_image, config: str) -> str:
        captured["config"] = config
        return " ab-12 \n"

    monkeypatch.setattr("captcha_solver.pytesseract.image_to_string", fake_image_to_string)

    image = Image.new("RGB", (12, 6), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    solver = CaptchaSolver()
    result = solver.solve(buffer.getvalue())

    assert result == "AB12"
    assert captured["config"] == OCR_CONFIG
    assert "--psm 7" in OCR_CONFIG
    assert "--oem 3" in OCR_CONFIG
