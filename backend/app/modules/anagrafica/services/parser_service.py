from __future__ import annotations

from dataclasses import dataclass, field
import re

from app.modules.anagrafica.models import AnagraficaSubjectType

CODICE_FISCALE_PATTERN = re.compile(
    r"^[A-Z]{6}[0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]$"
)
PARTITA_IVA_PATTERN = re.compile(r"^\d{11}$")
PARTITA_IVA_PARTIAL_PATTERN = re.compile(r"^\d{10}$")


@dataclass(slots=True)
class ParseResult:
    source_name_raw: str
    subject_type: str
    requires_review: bool
    confidence: float
    cognome: str | None = None
    nome: str | None = None
    codice_fiscale: str | None = None
    ragione_sociale: str | None = None
    partita_iva: str | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def is_person(self) -> bool:
        return self.subject_type == AnagraficaSubjectType.PERSON.value

    @property
    def is_company(self) -> bool:
        return self.subject_type == AnagraficaSubjectType.COMPANY.value


def _normalize_folder_name(folder_name: str) -> str:
    return re.sub(r"\s+", " ", folder_name.strip())


def _split_tokens(folder_name: str) -> list[str]:
    return [token.strip() for token in folder_name.split("_") if token.strip()]


def parse_folder_name(folder_name: str) -> ParseResult:
    normalized_name = _normalize_folder_name(folder_name)
    tokens = _split_tokens(normalized_name)

    if not normalized_name or not tokens:
        return ParseResult(
            source_name_raw=folder_name,
            subject_type=AnagraficaSubjectType.UNKNOWN.value,
            requires_review=True,
            confidence=0.0,
            warnings=["empty_folder_name"],
        )

    last_token = tokens[-1].upper()

    if CODICE_FISCALE_PATTERN.fullmatch(last_token):
        if len(tokens) < 3:
            return ParseResult(
                source_name_raw=folder_name,
                subject_type=AnagraficaSubjectType.UNKNOWN.value,
                requires_review=True,
                confidence=0.2,
                codice_fiscale=last_token,
                warnings=["person_name_incomplete"],
            )

        cognome = tokens[0].replace("_", " ").strip()
        nome = " ".join(tokens[1:-1]).replace("_", " ").strip()
        warnings: list[str] = []
        confidence = 0.98

        if not nome:
            warnings.append("missing_nome")
            confidence = 0.6

        return ParseResult(
            source_name_raw=folder_name,
            subject_type=AnagraficaSubjectType.PERSON.value,
            requires_review=bool(warnings),
            confidence=confidence,
            cognome=cognome or None,
            nome=nome or None,
            codice_fiscale=last_token,
            warnings=warnings,
        )

    if PARTITA_IVA_PATTERN.fullmatch(last_token):
        ragione_sociale = " ".join(tokens[:-1]).replace("_", " ").strip()
        if not ragione_sociale:
            return ParseResult(
                source_name_raw=folder_name,
                subject_type=AnagraficaSubjectType.UNKNOWN.value,
                requires_review=True,
                confidence=0.3,
                partita_iva=last_token,
                warnings=["company_name_missing"],
            )

        return ParseResult(
            source_name_raw=folder_name,
            subject_type=AnagraficaSubjectType.COMPANY.value,
            requires_review=False,
            confidence=0.95,
            ragione_sociale=ragione_sociale,
            partita_iva=last_token,
        )

    if PARTITA_IVA_PARTIAL_PATTERN.fullmatch(last_token):
        ragione_sociale = " ".join(tokens[:-1]).replace("_", " ").strip() or None
        return ParseResult(
            source_name_raw=folder_name,
            subject_type=AnagraficaSubjectType.COMPANY.value if ragione_sociale else AnagraficaSubjectType.UNKNOWN.value,
            requires_review=True,
            confidence=0.45 if ragione_sociale else 0.2,
            ragione_sociale=ragione_sociale,
            partita_iva=last_token,
            warnings=["partita_iva_length_anomaly"],
        )

    warnings = ["unclassified_folder_name"]
    if len(tokens) == 1 and tokens[0].isupper():
        warnings.append("special_folder_candidate")

    return ParseResult(
        source_name_raw=folder_name,
        subject_type=AnagraficaSubjectType.UNKNOWN.value,
        requires_review=True,
        confidence=0.1,
        warnings=warnings,
    )
