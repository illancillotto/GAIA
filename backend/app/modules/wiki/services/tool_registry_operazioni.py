from __future__ import annotations

from app.modules.wiki.services.tool_registry_common import WikiToolDefinition
from app.modules.wiki.services.tool_registry_operazioni_analytics import OPERAZIONI_ANALYTICS_TOOLS
from app.modules.wiki.services.tool_registry_operazioni_technical import OPERAZIONI_TECHNICAL_TOOLS
from app.modules.wiki.services.tool_registry_operazioni_workflow import OPERAZIONI_WORKFLOW_TOOLS

OPERAZIONI_TOOLS: tuple[WikiToolDefinition, ...] = (
    *OPERAZIONI_WORKFLOW_TOOLS,
    *OPERAZIONI_ANALYTICS_TOOLS,
    *OPERAZIONI_TECHNICAL_TOOLS,
)
