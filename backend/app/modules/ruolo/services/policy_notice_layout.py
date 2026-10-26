"""Slip layout and notice numbering chosen by a calculation rule."""

from typing import Any

NOTICE_NUMBER_SOURCES = frozenset({"gaia", "incass"})


def apply_notice_layout(policy: Any, command: Any) -> None:
    """ "incass" keeps the existing inCASS avviso number instead of a new GAIA number."""
    if command.notice_number_source not in NOTICE_NUMBER_SOURCES:
        raise ValueError("Numerazione avviso non valida")
    policy.bollettino_version = command.bollettino_version
    policy.notice_number_source = command.notice_number_source
