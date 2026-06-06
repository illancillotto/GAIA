from __future__ import annotations

import re
from typing import Literal

WikiIntent = Literal["docs_only", "live_data", "logic"]

_DOCS_HINTS = [
    r"\bcos['’]e\b",
    r"\bdocumentazione\b",
    r"\bwiki\b",
    r"\bmanuale\b",
    r"\bguida\b",
    r"\boverview\b",
    r"\bpanoramica\b",
    r"\bwhat is\b",
    r"\bwhat does\b",
    r"\bhow does\b",
    r"\bdocumentation\b",
    r"\bguide\b",
]

_DOCS_OVERVIEW_HINTS = [
    r"\bche cosa fa il modulo\b",
    r"\bcosa fa il modulo\b",
    r"\bcome funziona il modulo\b",
    r"\bpanoramica del modulo\b",
    r"\boverview del modulo\b",
    r"\bwhat does the module\b",
    r"\bhow does the module\b",
    r"\bmodule overview\b",
]

_LOGIC_HINTS = [
    r"\bperche\b",
    r"\bperché\b",
    r"\bspiega\b",
    r"\bcome funziona\b",
    r"\bcome viene calcolato\b",
    r"\bcome si calcola\b",
    r"\bindicatore\b",
    r"\bmetrica\b",
    r"\bregola\b",
    r"\bworkflow\b",
    r"\bpermess[oi]\b",
    r"\bautorizzazion",
    r"\babilitat[oa]\b",
    r"\bposso vedere\b",
    r"\bnon vedo\b",
    r"\bcollegat[oi]\b",
    r"\bwhy\b",
    r"\bhow it works\b",
    r"\bexplain\b",
    r"\bpermission",
    r"\bauthoriz",
    r"\benabl",
]

_LIVE_DATA_HINTS = [
    r"\bquanti\b",
    r"\bquante\b",
    r"\bnumero\b",
    r"\btotale\b",
    r"\bstato attuale\b",
    r"\bdashboard\b",
    r"\bsummary\b",
    r"\bkpi\b",
    r"\bstatistiche\b",
    r"\bstats\b",
    r"\bmostrami\b",
    r"\bcerca\b",
    r"\btrova\b",
    r"\bdettaglio\b",
    r"\blookup\b",
    r"\bavvisi\b",
    r"\bshare\b",
    r"\bassegnazion",
    r"\bassignment\b",
    r"\bmanutenzion",
    r"\bmaintenance\b",
    r"\btagliando\b",
    r"\bsession[ei]\b",
    r"\busage session\b",
    r"\battivit[aà]\b",
    r"\bactivity\b",
    r"\bapprovazion",
    r"\bapproval\b",
    r"\breview\b",
    r"\bautodoc\b",
    r"\bsync\b",
    r"\bstorage\b",
    r"\bquota\b",
    r"\bspazio\b",
    r"\bmobile sync\b",
    r"\bconnettore mobile\b",
    r"\bworkset\b",
    r"\bcataloghi mobile\b",
    r"\banalytics\b",
    r"\banalisi\b",
    r"\briforniment",
    r"\bfuel log\b",
    r"\bcarburante\b",
    r"\bunresolved\b",
    r"\btransazioni? non risolt",
    r"\banomali",
    r"\bdriver mismatch\b",
    r"\borphan session\b",
    r"\bunmatched refuel\b",
    r"\bshow me\b",
    r"\bfind\b",
    r"\bdetails?\b",
    r"\bcurrent status\b",
    r"\bdashboard\b",
    r"\bstatistics?\b",
]

_IDENTIFIER_HINTS = [
    re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"),
    re.compile(r"\b[A-Z0-9]{16}\b"),
    re.compile(r"\b\d{11}\b"),
]


def classify_intent(question: str) -> WikiIntent:
    normalized = question.strip().lower()
    if any(re.search(pattern, normalized) for pattern in _DOCS_OVERVIEW_HINTS):
        return "docs_only"
    logic_score = sum(1 for pattern in _LOGIC_HINTS if re.search(pattern, normalized))
    live_score = sum(1 for pattern in _LIVE_DATA_HINTS if re.search(pattern, normalized))
    docs_score = sum(1 for pattern in _DOCS_HINTS if re.search(pattern, normalized))

    if any(pattern.search(question.strip().upper()) for pattern in _IDENTIFIER_HINTS):
        live_score += 3

    if logic_score > 0:
        return "logic"
    if live_score > docs_score and live_score > 0:
        return "live_data"
    if docs_score > 0:
        return "docs_only"
    return "docs_only"
