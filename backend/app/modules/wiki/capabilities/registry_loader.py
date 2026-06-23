from __future__ import annotations

from app.modules.wiki.capabilities.catalog import CAPABILITIES
from app.modules.wiki.capabilities.registry_schema import CapabilityDefinition


def select_capability(
    *,
    task_type: str,
    module_hint: str | None,
    extracted_slots: dict[str, str | None],
) -> CapabilityDefinition | None:
    candidates: list[tuple[int, CapabilityDefinition]] = []
    for capability in CAPABILITIES:
        if capability.task_type != task_type:
            continue
        module_score = 1 if module_hint is not None and capability.module_key == module_hint else 0
        generic_score = 0 if capability.module_key is None else -1
        if capability.module_key is not None and module_hint is not None and capability.module_key != module_hint:
            continue
        filled_bonus = 1 if not capability.missing_slots(extracted_slots) else 0
        candidates.append((module_score + generic_score + filled_bonus, capability))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]
