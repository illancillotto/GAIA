from __future__ import annotations

import pytest

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


def test_select_capability_prefers_module_specific_overview() -> None:
    capability = select_capability(
        task_type="module_overview",
        module_hint="catasto",
        extracted_slots={},
    )

    assert capability is not None
    assert capability.name == "catasto.module_overview"
    assert capability.docs_pages == ("modules/catasto.md",)


def test_select_capability_prefers_wiki_navigation_help() -> None:
    capability = select_capability(
        task_type="navigation_help",
        module_hint="wiki",
        extracted_slots={},
    )

    assert capability is not None
    assert capability.name == "wiki.navigation_help"
    assert "pages/wiki__support.md" in capability.docs_pages


@pytest.mark.parametrize(
    "module_key",
    ["accessi", "operazioni", "utenze", "ruolo", "riordino", "rete", "presenze", "organigramma", "elaborazioni"],
)
def test_select_capability_resolves_module_specific_overviews(module_key: str) -> None:
    capability = select_capability(
        task_type="module_overview",
        module_hint=module_key,
        extracted_slots={},
    )

    assert capability is not None
    assert capability.name == f"{module_key}.module_overview"
    assert capability.docs_pages == (f"modules/{module_key}.md",)
