"""Pure operator name indexing and identity annotations for orphan sessions."""

from collections.abc import Iterable, Mapping
from typing import NamedTuple

from app.modules.operazioni.models.vehicles import VehicleUsageSession
from app.modules.operazioni.models.wc_operator import WCOperator


class OrphanOperatorIdentity(NamedTuple):
    name: str | None
    operator_id: str | None


def normalize_orphan_session_name(name: str | None) -> str:
    return (name or "").strip().lower()


def _orphan_operator_name(first_name: str | None, last_name: str | None) -> str:
    return " ".join(filter(None, (first_name, last_name))).strip()


def index_orphan_operator_names(
    operators: Iterable[WCOperator], requested_names: set[str]
) -> dict[str, WCOperator]:
    by_name: dict[str, WCOperator] = {}
    for operator in operators:
        variants = (
            _orphan_operator_name(operator.first_name, operator.last_name).lower(),
            _orphan_operator_name(operator.last_name, operator.first_name).lower(),
        )
        for name in variants:
            if name in requested_names:
                by_name.setdefault(name, operator)
    return by_name


def orphan_operator_identity(
    session: VehicleUsageSession,
    by_gaia: Mapping[int | None, WCOperator],
    by_name: Mapping[str, WCOperator],
) -> OrphanOperatorIdentity:
    operator = (
        by_gaia.get(session.actual_driver_user_id)
        if session.actual_driver_user_id is not None
        else None
    )
    normalized_name = normalize_orphan_session_name(session.operator_name)
    if operator is None and normalized_name:
        operator = by_name.get(normalized_name)
    if operator is None:
        return OrphanOperatorIdentity(session.operator_name or None, None)
    return OrphanOperatorIdentity(
        _orphan_operator_name(operator.first_name, operator.last_name), str(operator.id)
    )
