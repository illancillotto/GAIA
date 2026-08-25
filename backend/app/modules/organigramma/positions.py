from __future__ import annotations

import re

POSITION_MARKERS = (
    ("dirigente", ("dirigent", "direttor")),
    ("capo_settore", ("capo settore",)),
    ("capo_operai", ("capo operai", "capo operaio")),
    ("capo_reparto", ("capo reparto",)),
)


def position_code_from_title(title: str | None) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", " ", (title or "").casefold()).strip()
    return next((code for code, markers in POSITION_MARKERS if any(marker in normalized for marker in markers)), None)
