from __future__ import annotations

import re

from app.models.catasto_phase1 import CatComune


def normalize_lookup_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def _score_comune_code(row: CatComune, source_code: int | None) -> int:
    if source_code is None:
        return 0
    score = 0
    if row.cod_comune_capacitas == source_code:
        score += 8
    if row.codice_comune_formato_numerico == source_code:
        score += 6
    if row.codice_comune_numerico_2017_2025 == source_code:
        score += 6
    return score


def _contains_lookup(source_name: str, candidate_name: str) -> bool:
    return source_name in candidate_name or candidate_name in source_name


def score_comune_candidate(row: CatComune, source_code: int | None, source_name: str) -> int:
    score = _score_comune_code(row, source_code)
    if not source_name:
        return score
    row_name = normalize_lookup_text(row.nome_comune)
    row_legacy_name = normalize_lookup_text(row.nome_comune_legacy)
    exact_score = next(
        (
            weight
            for candidate, weight in ((row_name, 8), (row_legacy_name, 7))
            if source_name == candidate
        ),
        0,
    )
    if exact_score:
        return score + exact_score
    if _contains_lookup(source_name, row_name):
        return score + 4
    if row_legacy_name and _contains_lookup(source_name, row_legacy_name):
        return score + 3
    return score
