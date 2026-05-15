from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageFilter, ImageOps
import pytesseract


OCR_CONFIG = "--psm 7 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz"


class CaptchaSolver:
    def solve(self, image_bytes: bytes) -> str | None:
        image = Image.open(BytesIO(image_bytes)).convert("L")
        image = image.resize((image.width * 2, image.height * 2))
        image = ImageOps.autocontrast(image)
        image = image.point(lambda value: 255 if value > 145 else 0)
        image = image.filter(ImageFilter.MedianFilter(size=3))
        text = pytesseract.image_to_string(image, config=OCR_CONFIG)
        normalized = "".join(char for char in text if char.isalpha())
        return normalized or None
