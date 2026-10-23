"""Recognise inCASS partitario dialogs saved without any partita.

For some avvisi (mostly fully discharged ones) inCASS returns the partitario
dialog with an empty content box: the stored HTML then holds only the dialog
script and its "Chiudi"/"Scarica" buttons, which must not be printed.
"""

import html
import re

_SCRIPT_RE = re.compile(r"<script\b.*?</script>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
PARTITE_HEADER = "ELENCO DELLE PARTITE SOGGETTE A CONTRIBUTO"
DIALOG_CONTROLS = frozenset({"chiudi", "scarica"})


def is_empty_partitario_dialog(text: str) -> bool:
    if PARTITE_HEADER in text:
        return False
    visible = html.unescape(_TAG_RE.sub(" ", _SCRIPT_RE.sub(" ", text)))
    return set(visible.casefold().split()) <= DIALOG_CONTROLS


def usable_partitario_text(text: str) -> str | None:
    """The stored partitario text, or ``None`` when inCASS saved an empty dialog."""
    return None if is_empty_partitario_dialog(text) else text
