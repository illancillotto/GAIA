from __future__ import annotations

from app.modules.wiki.capabilities.registry_loader import select_capability


def test_select_capability_prefers_catasto_owner_lookup() -> None:
    capability = select_capability(
        task_type="owner_lookup",
        module_hint="catasto",
        extracted_slots={"comune": "Oristano", "foglio": "24", "particella": "191"},
    )

    assert capability is not None
    assert capability.name == "catasto.owner_lookup"
    assert capability.missing_slots({"comune": "Oristano", "foglio": "24", "particella": "191"}) == ()


def test_select_capability_keeps_owner_lookup_even_without_slots() -> None:
    capability = select_capability(
        task_type="owner_lookup",
        module_hint="catasto",
        extracted_slots={"comune": None, "foglio": None, "particella": None},
    )

    assert capability is not None
    assert capability.name == "catasto.owner_lookup"
    assert capability.missing_slots({"comune": None, "foglio": None, "particella": None}) == (
        "comune",
        "foglio",
        "particella",
    )


def test_select_capability_resolves_catasto_particella_lookup_tool() -> None:
    capability = select_capability(
        task_type="entity_lookup",
        module_hint="catasto",
        extracted_slots={"uuid": "11111111-1111-1111-1111-111111111111"},
    )

    assert capability is not None
    assert capability.name == "catasto.particella_lookup"
    assert capability.tool_name == "find_particella_by_id"
