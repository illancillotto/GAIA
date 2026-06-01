from __future__ import annotations

from app.modules.wiki.services.tool_registry_accessi import ACCESSI_TOOLS
from app.modules.wiki.services.tool_registry_catasto import CATASTO_TOOLS
from app.modules.wiki.services.tool_registry_common import WikiToolDefinition
from app.modules.wiki.services.tool_registry_operazioni import OPERAZIONI_TOOLS
from app.modules.wiki.services.tool_registry_riordino import RIORDINO_TOOLS
from app.modules.wiki.services.tool_registry_ruolo_utenze import RUOLO_UTENZE_TOOLS

TOOLS: tuple[WikiToolDefinition, ...] = (
    *CATASTO_TOOLS,
    *ACCESSI_TOOLS,
    *RUOLO_UTENZE_TOOLS,
    *RIORDINO_TOOLS,
    *OPERAZIONI_TOOLS,
)


def find_matching_tool(question: str, intent: str) -> WikiToolDefinition | None:
    candidates: list[tuple[int, int, WikiToolDefinition]] = []
    for tool in TOOLS:
        if intent not in tool.intents:
            continue
        score = tool.matcher(question)
        if score > 0:
            candidates.append((tool.priority, score, tool))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]
