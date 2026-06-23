from __future__ import annotations

from app.modules.wiki.services.tool_registry_accessi import ACCESSI_TOOLS
from app.modules.wiki.services.tool_registry_catasto import CATASTO_TOOLS
from app.modules.wiki.services.tool_registry_common import WikiToolDefinition
from app.modules.wiki.services.tool_registry_network import RETE_TOOLS
from app.modules.wiki.services.tool_registry_operazioni import OPERAZIONI_TOOLS
from app.modules.wiki.services.tool_registry_riordino import RIORDINO_TOOLS
from app.modules.wiki.services.tool_registry_ruolo_utenze import RUOLO_UTENZE_TOOLS

TOOLS: tuple[WikiToolDefinition, ...] = (
    *CATASTO_TOOLS,
    *ACCESSI_TOOLS,
    *RUOLO_UTENZE_TOOLS,
    *RIORDINO_TOOLS,
    *OPERAZIONI_TOOLS,
    *RETE_TOOLS,
)


def find_tool_by_name(tool_name: str) -> WikiToolDefinition | None:
    for tool in TOOLS:
        if tool.meta.name == tool_name:
            return tool
    return None


def find_matching_tool(question: str, intent: str, *, preferred_module_key: str | None = None) -> WikiToolDefinition | None:
    candidates: list[tuple[int, int, WikiToolDefinition]] = []
    module_aliases = {
        "network": "rete",
    }
    normalized_module_key = module_aliases.get(preferred_module_key or "", preferred_module_key)
    for tool in TOOLS:
        if intent not in tool.intents:
            continue
        score = tool.matcher(question)
        if score > 0:
            module_boost = 1000 if normalized_module_key and tool.meta.module_key == normalized_module_key else 0
            candidates.append((module_boost + tool.priority, score, tool))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]
