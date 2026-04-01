from __future__ import annotations

import os
import re

from app.modules.anagrafica.models import AnagraficaClassificationSource, AnagraficaDocType

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
