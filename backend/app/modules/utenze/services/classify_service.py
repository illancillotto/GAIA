from __future__ import annotations

from dataclasses import dataclass
import os
import re

from app.modules.utenze.models import AnagraficaClassificationSource, AnagraficaDocType

PATTERNS: dict[str, list[re.Pattern[str]]] = {
    AnagraficaDocType.INGIUNZIONE.value: [
        re.compile(r"(?i)ingiunzione"),
        re.compile(r"(?i)[_\-]ing[_\-]"),
        re.compile(r"(?i)^ing_"),
    ],
    AnagraficaDocType.NOTIFICA.value: [
        re.compile(r"(?i)relata"),
        re.compile(r"(?i)notifica"),
    ],
    AnagraficaDocType.ESTRATTO_DEBITO.value: [
        re.compile(r"(?i)estratto.?debito"),
        re.compile(r"(?i)estrattoDebito"),
    ],
    AnagraficaDocType.PRATICA_INTERNA.value: [
        re.compile(r"(?i)^PE_"),
        re.compile(r"(?i)_prot\d"),
        re.compile(r"(?i)\bprot\.?\s*\d+"),
    ],
    AnagraficaDocType.VISURA.value: [
        re.compile(r"(?i)visura"),
    ],
    AnagraficaDocType.CORRISPONDENZA.value: [
        re.compile(r"(?i)lettera"),
        re.compile(r"(?i)comunicaz"),
    ],
    AnagraficaDocType.CONTRATTO.value: [
        re.compile(r"(?i)contratto"),
        re.compile(r"(?i)convenzione"),
    ],
}


@dataclass(frozen=True, slots=True)
class DocumentSmartClassification:
    category: str
    label: str
    priority: int
    confidence: float
    reason: str | None = None


SMART_CATEGORY_META: dict[str, tuple[str, int]] = {
    "legal_action": ("Azioni legali", 100),
    "notification": ("Notifiche e relate", 90),
    "delivery_proof": ("Prove invio e PEC", 80),
    "debt_payment": ("Pagamenti e debito", 70),
    "irrigation_application": ("Domande utenza irrigua", 65),
    "cadastral": ("Visure e catasto", 60),
    "contract": ("Contratti e convenzioni", 50),
    "internal_practice": ("Pratiche interne", 40),
    "other": ("Altro da classificare", 10),
}

SMART_PATTERNS: list[tuple[str, list[re.Pattern[str]], str]] = [
    (
        "legal_action",
        [re.compile(r"(?i)ingiun"), re.compile(r"(?i)(?:^|[_\-\s])ing(?:[_\-\s]|$)")],
        "nome file contiene riferimenti a ingiunzione",
    ),
    (
        "notification",
        [re.compile(r"(?i)notific"), re.compile(r"(?i)relata"), re.compile(r"(?i)messo")],
        "nome file contiene riferimenti a notifica/relata",
    ),
    (
        "delivery_proof",
        [
            re.compile(r"(?i)ricevut"),
            re.compile(r"(?i)\bpec\b"),
            re.compile(r"(?i)objman"),
            re.compile(r"(?i)accettazione"),
            re.compile(r"(?i)consegna"),
            re.compile(r"(?i)\.eml$"),
            re.compile(r"(?i)\bmail\b"),
        ],
        "nome file contiene riferimenti a ricevuta, PEC o email",
    ),
    (
        "debt_payment",
        [
            re.compile(r"(?i)estratto.?debito"),
            re.compile(r"(?i)estratto"),
            re.compile(r"(?i)debito"),
            re.compile(r"(?i)avviso"),
            re.compile(r"(?i)pagament"),
            re.compile(r"(?i)incass"),
            re.compile(r"(?i)bollett"),
        ],
        "nome file contiene riferimenti a debito, avviso o pagamento",
    ),
    (
        "irrigation_application",
        [
            re.compile(r"(?i)(?:^|[^a-z0-9])d\.?u\.?i\.?(?:[^a-z0-9]|$)"),
            re.compile(r"(?i)(?:^|[^a-z0-9])d\.?u\.?i\.?20\d{2}(?:[^a-z0-9]|$)"),
            re.compile(r"(?i)domanda.?utenza.?irrigua"),
            re.compile(r"(?i)domanda.?irrigua"),
            re.compile(r"(?i)verifica.?dui"),
            re.compile(r"(?i)verifica.?domanda.?utenza.?irrigua"),
            re.compile(r"(?i)annull\w*.?dui"),
            re.compile(r"(?i)regolarizz\w*.?dui"),
            re.compile(r"(?i)richiesta.?dui"),
        ],
        "nome file contiene riferimenti a domanda utenza irrigua/DUI",
    ),
    (
        "cadastral",
        [re.compile(r"(?i)visura"), re.compile(r"(?i)catast")],
        "nome file contiene riferimenti a visura o catasto",
    ),
    (
        "contract",
        [re.compile(r"(?i)contratt"), re.compile(r"(?i)convenzion")],
        "nome file contiene riferimenti a contratto/convenzione",
    ),
    (
        "internal_practice",
        [re.compile(r"(?i)^PE[_-]"), re.compile(r"(?i)_prot\d"), re.compile(r"(?i)\bprot(?:\.|ocollo)?\b")],
        "nome file contiene riferimenti a protocollo o pratica interna",
    ),
]

DOC_TYPE_SMART_CATEGORY: dict[str, str] = {
    AnagraficaDocType.INGIUNZIONE.value: "legal_action",
    AnagraficaDocType.NOTIFICA.value: "notification",
    AnagraficaDocType.ESTRATTO_DEBITO.value: "debt_payment",
    AnagraficaDocType.PRATICA_INTERNA.value: "internal_practice",
    AnagraficaDocType.VISURA.value: "cadastral",
    AnagraficaDocType.CORRISPONDENZA.value: "delivery_proof",
    AnagraficaDocType.CONTRATTO.value: "contract",
}


def _smart_classification(category: str, *, confidence: float, reason: str | None) -> DocumentSmartClassification:
    label, priority = SMART_CATEGORY_META.get(category, SMART_CATEGORY_META["other"])
    return DocumentSmartClassification(
        category=category,
        label=label,
        priority=priority,
        confidence=confidence,
        reason=reason,
    )


def classify_filename(filename: str) -> tuple[str, str]:
    basename = os.path.basename(filename).strip()
    if not basename:
        return AnagraficaDocType.ALTRO.value, AnagraficaClassificationSource.AUTO.value

    for doc_type, patterns in PATTERNS.items():
        if any(pattern.search(basename) for pattern in patterns):
            return doc_type, AnagraficaClassificationSource.AUTO.value

    return AnagraficaDocType.ALTRO.value, AnagraficaClassificationSource.AUTO.value


def classify_filenames(filenames: list[str]) -> list[tuple[str, str, str]]:
    return [(filename, *classify_filename(filename)) for filename in filenames]


def derive_document_smart_classification(
    *,
    filename: str,
    doc_type: str,
    classification_source: str | None = None,
    extension: str | None = None,
    notes: str | None = None,
) -> DocumentSmartClassification:
    normalized_doc_type = (doc_type or "").strip().lower()
    if normalized_doc_type in DOC_TYPE_SMART_CATEGORY and normalized_doc_type != AnagraficaDocType.ALTRO.value:
        confidence = 1.0 if classification_source == AnagraficaClassificationSource.MANUAL.value else 0.85
        return _smart_classification(
            DOC_TYPE_SMART_CATEGORY[normalized_doc_type],
            confidence=confidence,
            reason=f"tipo documento salvato: {normalized_doc_type}",
        )

    basename = os.path.basename(filename or "").strip()
    searchable_text = " ".join(part for part in [basename, extension or "", notes or ""] if part)
    for category, patterns, reason in SMART_PATTERNS:
        if any(pattern.search(searchable_text) for pattern in patterns):
            return _smart_classification(category, confidence=0.72, reason=reason)

    return _smart_classification("other", confidence=0.2, reason=None)
