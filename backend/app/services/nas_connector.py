from dataclasses import dataclass

from app.core.config import settings
from app.schemas.sync import SyncCapabilitiesResponse, SyncPreviewRequest, SyncPreviewResponse
from app.services.nas_parsers import (
    parse_acl_output,
    parse_group_output,
    parse_passwd_output,
    parse_share_listing,
)


class NasConnectorError(RuntimeError):
    """Raised when live NAS integration is requested but not yet implemented."""


@dataclass
class NasSSHClient:
    host: str
    port: int
    username: str
    timeout: int

    def run_command(self, command: str) -> str:
        raise NasConnectorError(
            f"Live NAS command execution is not implemented yet for command: {command}"
        )


def get_nas_client() -> NasSSHClient:
    return NasSSHClient(
        host=settings.nas_host,
        port=settings.nas_port,
        username=settings.nas_username,
        timeout=settings.nas_timeout,
    )


def get_sync_capabilities() -> SyncCapabilitiesResponse:
    ssh_configured = bool(settings.nas_host and settings.nas_username)
    return SyncCapabilitiesResponse(
        ssh_configured=ssh_configured,
        host=settings.nas_host,
        port=settings.nas_port,
        username=settings.nas_username,
        timeout_seconds=settings.nas_timeout,
        supports_live_sync=False,
    )


def build_sync_preview(payload: SyncPreviewRequest) -> SyncPreviewResponse:
    return SyncPreviewResponse(
        users=parse_passwd_output(payload.passwd_text or ""),
        groups=parse_group_output(payload.group_text or ""),
        shares=parse_share_listing(payload.shares_text or ""),
        acl_entries=[
            entry
            for acl_text in payload.acl_texts
            for entry in parse_acl_output(acl_text)
        ],
    )
