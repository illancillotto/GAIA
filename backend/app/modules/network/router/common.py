from fastapi import HTTPException, status

from app.models.application_user import ApplicationUser
from app.modules.network.models import (
    NetworkSophosConfig,
)
from app.modules.network.schemas import (
    NetworkSophosConfigRead,
)
from app.modules.network.sophos_runtime import (
    build_sophos_runtime_policy,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

def _require_network_module(current_user: ApplicationUser) -> None:
    if not current_user.module_rete and not current_user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Network module not enabled")


def _serialize_sophos_config(config: NetworkSophosConfig) -> NetworkSophosConfigRead:
    policy = build_sophos_runtime_policy(config)
    return NetworkSophosConfigRead(
        syslog_enabled=policy.syslog_enabled,
        snmp_enabled=policy.snmp_enabled,
        operation_window_enabled=policy.operation_window_enabled,
        operation_start_hour=policy.operation_start_hour,
        operation_end_hour=policy.operation_end_hour,
        operation_timezone=policy.operation_timezone,
        is_within_window=policy.is_within_window,
        syslog_effective_enabled=policy.syslog_should_ingest,
        snmp_effective_enabled=policy.snmp_should_poll,
        updated_at=config.updated_at,
    )


# fmt: on
