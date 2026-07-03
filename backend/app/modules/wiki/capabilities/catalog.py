from __future__ import annotations

from app.modules.wiki.capabilities.registry_schema import CapabilityDefinition


COMMON_CAPABILITIES: tuple[CapabilityDefinition, ...] = (
    CapabilityDefinition(
        name="common.page_intro",
        task_type="page_intro",
        module_key=None,
        docs_pages=("pages/page_intro.md",),
    ),
    CapabilityDefinition(
        name="common.module_overview",
        task_type="module_overview",
        module_key=None,
        docs_pages=("modules/module_overview.md",),
    ),
    CapabilityDefinition(
        name="common.platform_overview",
        task_type="platform_overview",
        module_key=None,
        docs_pages=("modules/platform_overview.md",),
    ),
    CapabilityDefinition(
        name="common.navigation_help",
        task_type="navigation_help",
        module_key=None,
        docs_pages=("workflows/navigation_help.md",),
    ),
    CapabilityDefinition(
        name="common.docs_lookup",
        task_type="docs_lookup",
        module_key=None,
        docs_pages=("docs_lookup.md",),
    ),
    CapabilityDefinition(
        name="common.workflow_explanation",
        task_type="workflow_explanation",
        module_key=None,
        docs_pages=("workflows/workflow_explanation.md",),
    ),
    CapabilityDefinition(
        name="common.metric_explanation",
        task_type="metric_explanation",
        module_key=None,
        docs_pages=("workflows/metric_explanation.md",),
    ),
)


CATASTO_CAPABILITIES: tuple[CapabilityDefinition, ...] = (
    CapabilityDefinition(
        name="catasto.module_overview",
        task_type="module_overview",
        module_key="catasto",
        docs_pages=("modules/catasto.md",),
    ),
    CapabilityDefinition(
        name="catasto.owner_lookup",
        task_type="owner_lookup",
        module_key="catasto",
        required_slots=(
            ("comune", "foglio", "particella"),
            ("codice_fiscale",),
            ("partita_iva",),
            ("nominativo",),
        ),
        clarification_prompt=(
            "Ciao. Per aiutarti a trovare il proprietario di un terreno mi servono almeno comune, foglio e particella, "
            "oppure un nominativo, codice fiscale o partita IVA. Se me li indichi, posso guidarti nella ricerca Catasto "
            "in modo operativo."
        ),
        docs_pages=("capabilities/catasto.owner_lookup.md",),
        permission_scope="catasto.read",
    ),
    CapabilityDefinition(
        name="catasto.particella_lookup",
        task_type="entity_lookup",
        module_key="catasto",
        required_slots=(("uuid",),),
        tool_name="find_particella_by_id",
        clarification_prompt="Per cercare una particella Catasto in questo flusso devo ricevere un UUID valido.",
        docs_pages=("capabilities/catasto.particella_lookup.md",),
        permission_scope="catasto.read",
    ),
)


WIKI_CAPABILITIES: tuple[CapabilityDefinition, ...] = (
    CapabilityDefinition(
        name="wiki.module_overview",
        task_type="module_overview",
        module_key="wiki",
        docs_pages=("modules/wiki.md",),
    ),
    CapabilityDefinition(
        name="wiki.navigation_help",
        task_type="navigation_help",
        module_key="wiki",
        docs_pages=("pages/wiki__support.md", "workflows/navigation_help.md"),
    ),
)

_OVERVIEW_MODULE_KEYS = (
    "accessi",
    "operazioni",
    "utenze",
    "ruolo",
    "riordino",
    "rete",
    "presenze",
    "organigramma",
    "elaborazioni",
    "inventario",
)

MODULE_OVERVIEW_CAPABILITIES: tuple[CapabilityDefinition, ...] = tuple(
    CapabilityDefinition(
        name=f"{module_key}.module_overview",
        task_type="module_overview",
        module_key=module_key,
        docs_pages=(f"modules/{module_key}.md",),
    )
    for module_key in _OVERVIEW_MODULE_KEYS
)


CAPABILITIES: tuple[CapabilityDefinition, ...] = (
    *CATASTO_CAPABILITIES,
    *WIKI_CAPABILITIES,
    *MODULE_OVERVIEW_CAPABILITIES,
    *COMMON_CAPABILITIES,
)
