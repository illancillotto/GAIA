from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    name: str
    task_type: str
    module_key: str | None
    required_slots: tuple[tuple[str, ...], ...] = ()
    tool_name: str | None = None
    clarification_prompt: str | None = None
    docs_pages: tuple[str, ...] = ()
    permission_scope: str | None = None

    def missing_slots(self, extracted_slots: dict[str, str | None]) -> tuple[str, ...]:
        if not self.required_slots:
            return ()
        for slot_group in self.required_slots:
            if all((extracted_slots.get(slot) or "").strip() for slot in slot_group):
                return ()
        preferred_group = self.required_slots[0]
        return tuple(slot for slot in preferred_group if not (extracted_slots.get(slot) or "").strip())
