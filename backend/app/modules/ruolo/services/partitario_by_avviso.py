"""Compose the attached partitario avviso by avviso.

The inCASS partitario of each avviso is printed when available. An avviso
without one (empty inCASS dialog) gets the partitario GAIA builds from its
partite, also when other avvisi of the same notice do have an inCASS one.
"""

from collections.abc import Callable
from typing import Any

Lines = list[str]
GENERATE_ONLY_KEY = "_partitario_generate_only"


def partitario_by_avviso(
    payload: dict[str, Any],
    stored: Callable[[dict[str, Any]], Lines],
    generate: Callable[[dict[str, Any]], Lines],
) -> Lines:
    """Stored partitari per avviso plus GAIA's for the avvisi without one.

    ``[]`` leaves the whole notice to ``generate`` (no stored partitario at all).
    """
    if payload.get(GENERATE_ONLY_KEY):
        return []
    if stored({key: value for key, value in payload.items() if key != "avvisi"}):
        return stored(payload)
    blocks, missing = _stored_blocks(payload, stored)
    if not blocks:
        return []
    printed = "\n".join(line for lines in blocks for line in lines)
    with_partite = _avvisi_with_unprinted_partite(missing, printed)
    if with_partite:
        blocks.append(generate({**payload, "avvisi": with_partite, GENERATE_ONLY_KEY: True}))
    return _joined(blocks)


def _stored_blocks(
    payload: dict[str, Any], stored: Callable[[dict[str, Any]], Lines]
) -> tuple[list[Lines], list[dict[str, Any]]]:
    """Distinct stored partitari, and the avvisi that have none."""
    blocks: list[Lines] = []
    missing: list[dict[str, Any]] = []
    for avviso in payload.get("avvisi", []):
        if not isinstance(avviso, dict):
            continue
        lines = stored({"avvisi": [avviso]})
        if not lines:
            missing.append(avviso)
        elif lines not in blocks:
            blocks.append(lines)
    return blocks, missing


def _avvisi_with_unprinted_partite(
    avvisi: list[dict[str, Any]], printed: str
) -> list[dict[str, Any]]:
    with_partite = []
    for avviso in avvisi:
        unprinted = _unprinted_partite(avviso, printed)
        if unprinted:
            with_partite.append({**avviso, "partite": unprinted})
    return with_partite


def _joined(blocks: list[Lines]) -> Lines:
    composed: Lines = []
    for lines in blocks:
        composed.extend([""] * bool(composed) + lines)
    return composed


def _unprinted_partite(avviso: dict[str, Any], printed: str) -> list[dict[str, Any]]:
    """Partite not already shown by an inCASS partitario of the same notice."""
    return [
        partita
        for partita in avviso.get("partite") or []
        if f"Partita {partita.get('codice_partita')} " not in printed
    ]
