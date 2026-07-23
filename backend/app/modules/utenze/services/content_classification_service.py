from __future__ import annotations

from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path
import re

from pypdf import PdfReader


MAX_TEXT_CHARS = 80_000
MAX_EXCERPT_CHARS = 260

CONTENT_CATEGORY_LABELS: dict[str, str] = {
    "legal_action": "Azioni legali",
    "notification": "Notifiche e relate",
    "delivery_proof": "Prove invio e PEC",
    "debt_payment": "Pagamenti e debito",
    "irrigation_application": "Domande utenza irrigua",
    "cadastral": "Visure e catasto",
    "contract": "Contratti e convenzioni",
    "internal_practice": "Pratiche interne",
    "other": "Altro da classificare",
}


@dataclass(frozen=True, slots=True)
class DocumentContentClassification:
    status: str
    category: str | None
    label: str | None
    confidence: float | None
    reason: str | None
    excerpt: str | None
    source: str | None
    error: str | None = None


CONTENT_PATTERNS: list[tuple[str, list[re.Pattern[str]], str]] = [
    (
        "legal_action",
        [
            re.compile(r"(?i)\bingiunzione\b"),
            re.compile(r"(?i)\bingiunge\b"),
            re.compile(r"(?i)riscossione coattiva"),
            re.compile(r"(?i)atto di ingiunzione"),
        ],
        "contenuto con riferimenti a ingiunzione o riscossione coattiva",
    ),
    (
        "notification",
        [
            re.compile(r"(?i)relata di notifica"),
            re.compile(r"(?i)messo notificatore"),
            re.compile(r"(?i)avvenuta notifica"),
            re.compile(r"(?i)notificato a"),
        ],
        "contenuto con riferimenti a notifica/relata",
    ),
    (
        "delivery_proof",
        [
            re.compile(r"(?i)ricevuta di accettazione"),
            re.compile(r"(?i)ricevuta di avvenuta consegna"),
            re.compile(r"(?i)\bposta elettronica certificata\b"),
            re.compile(r"(?i)\bpec\b"),
            re.compile(r"(?i)objman"),
        ],
        "contenuto con riferimenti a PEC o prove di consegna",
    ),
    (
        "debt_payment",
        [
            re.compile(r"(?i)avviso di pagamento"),
            re.compile(r"(?i)estratto debito"),
            re.compile(r"(?i)posizione debitoria"),
            re.compile(r"(?i)\bincass\b"),
            re.compile(r"(?i)\biuv\b"),
            re.compile(r"(?i)importo da pagare"),
        ],
        "contenuto con riferimenti a avvisi, debito o pagamento",
    ),
    (
        "irrigation_application",
        [
            re.compile(r"(?i)domanda di utenza irrigua"),
            re.compile(r"(?i)domanda utenza irrigua"),
            re.compile(r"(?i)\bd\.?u\.?i\.?\b"),
            re.compile(r"(?i)utenza irrigua"),
        ],
        "contenuto con riferimenti a domanda utenza irrigua/DUI",
    ),
    (
        "cadastral",
        [
            re.compile(r"(?i)agenzia delle entrate"),
            re.compile(r"(?i)visura catastale"),
            re.compile(r"(?i)catasto terreni"),
            re.compile(r"(?i)catasto fabbricati"),
            re.compile(r"(?i)\bfoglio\b.*\bparticella\b"),
        ],
        "contenuto con riferimenti catastali o visura",
    ),
    (
        "contract",
        [
            re.compile(r"(?i)\bcontratto\b"),
            re.compile(r"(?i)\bconvenzione\b"),
            re.compile(r"(?i)atto convenzionale"),
        ],
        "contenuto con riferimenti a contratto/convenzione",
    ),
    (
        "internal_practice",
        [
            re.compile(r"(?i)\bprotocollo\b"),
            re.compile(r"(?i)\bprot\.\s*\d+"),
            re.compile(r"(?i)pratica interna"),
        ],
        "contenuto con riferimenti a protocollo o pratica interna",
    ),
]


def classify_document_content_text(text: str, *, source: str = "provided_text") -> DocumentContentClassification:
    normalized = _compact_text(text)
    if not normalized:
        return DocumentContentClassification(
            status="empty",
            category=None,
            label=None,
            confidence=None,
            reason=None,
            excerpt=None,
            source=source,
            error="Testo documento assente o non estraibile",
        )

    searchable = normalized[:MAX_TEXT_CHARS]
    for category, patterns, reason in CONTENT_PATTERNS:
        for pattern in patterns:
            match = pattern.search(searchable)
            if match:
                return DocumentContentClassification(
                    status="classified",
                    category=category,
                    label=CONTENT_CATEGORY_LABELS[category],
                    confidence=0.82,
                    reason=reason,
                    excerpt=_excerpt_around(searchable, match.start(), match.end()),
                    source=source,
                )

    return DocumentContentClassification(
        status="unclassified",
        category="other",
        label=CONTENT_CATEGORY_LABELS["other"],
        confidence=0.25,
        reason="contenuto leggibile senza pattern documentale riconosciuto",
        excerpt=searchable[:MAX_EXCERPT_CHARS],
        source=source,
    )


def classify_document_content_file(path: Path, *, filename: str | None = None) -> DocumentContentClassification:
    source_name = (filename or path.name).lower()
    try:
        if source_name.endswith(".pdf"):
            return classify_document_content_text(_extract_pdf_text(path), source="pdf_text")
        if source_name.endswith(".eml"):
            return classify_document_content_text(_extract_eml_text(path), source="eml_text")
        if source_name.endswith((".txt", ".csv", ".log", ".xml", ".html", ".htm")):
            return classify_document_content_text(path.read_text(encoding="utf-8", errors="ignore"), source="plain_text")
    except Exception as exc:  # pragma: no cover - defensive boundary around third-party parsers/filesystem.
        return DocumentContentClassification(
            status="failed",
            category=None,
            label=None,
            confidence=None,
            reason=None,
            excerpt=None,
            source="file_extraction",
            error=str(exc),
        )

    return DocumentContentClassification(
        status="unsupported",
        category=None,
        label=None,
        confidence=None,
        reason=None,
        excerpt=None,
        source="file_extraction",
        error="Formato documento non supportato per classificazione contenutistica",
    )


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\x00", " ")).strip()


def _excerpt_around(text: str, start: int, end: int) -> str:
    left = max(0, start - 90)
    right = min(len(text), end + 170)
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(text) else ""
    return f"{prefix}{text[left:right].strip()}{suffix}"[:MAX_EXCERPT_CHARS]


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_eml_text(path: Path) -> str:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    parts: list[str] = []
    if message.get("subject"):
        parts.append(str(message.get("subject")))
    if message.get("from"):
        parts.append(str(message.get("from")))
    if message.get("to"):
        parts.append(str(message.get("to")))

    body = message.get_body(preferencelist=("plain", "html"))
    if body is not None:
        payload = body.get_content()
        if isinstance(payload, str):
            parts.append(payload)
    return "\n".join(parts)
