"""Editable starting texts; reading the catalogue never saves or approves a template."""

import json
from pathlib import Path


def load_catalog() -> dict:
    return json.loads(Path(__file__).with_name("template_catalog.json").read_text(encoding="utf-8"))
