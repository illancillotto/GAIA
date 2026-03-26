from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.schemas.sync import SyncCapabilitiesResponse


class NasConnectorError(RuntimeError):
    """Raised when NAS live integration cannot be completed."""


@dataclass
class NasSSHClient:
    host: str
    port: int
    username: str
    timeout: int
    password: str | None = None
    private_key_path: str | None = None

    def run_command(self, command: str) -> str:
        try:
            import paramiko
        except ImportError as exc:
            raise NasConnectorError("Paramiko is not installed in the backend environment") from exc

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs: dict[str, Any] = {
            "hostname": self.host,
            "port": self.port,
            "username": self.username,
            "timeout": self.timeout,
            "look_for_keys": False,
            "allow_agent": False,
        }
        if self.private_key_path:
            connect_kwargs["key_filename"] = self.private_key_path
        else:
            connect_kwargs["password"] = self.password

        try:
            client.connect(**connect_kwargs)
            _, stdout, stderr = client.exec_command(command, timeout=self.timeout)
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode("utf-8")
            error_output = stderr.read().decode("utf-8").strip()
        except Exception as exc:  # pragma: no cover
            raise NasConnectorError(f"SSH command failed: {command}") from exc
        finally:
            client.close()

        if exit_status != 0:
            raise NasConnectorError(
                f"SSH command returned exit status {exit_status} for '{command}': {error_output}"
            )

        return output


def get_nas_client() -> NasSSHClient:
    return NasSSHClient(
        host=settings.nas_host,
        port=settings.nas_port,
        username=settings.nas_username,
        timeout=settings.nas_timeout,
        password=settings.nas_password,
        private_key_path=settings.nas_private_key_path,
    )


def get_sync_capabilities() -> SyncCapabilitiesResponse:
    ssh_configured = bool(settings.nas_host and settings.nas_username)
    supports_live_sync = ssh_configured and bool(settings.nas_password or settings.nas_private_key_path)
    auth_mode = "private_key" if settings.nas_private_key_path else "password"
    return SyncCapabilitiesResponse(
        ssh_configured=ssh_configured,
        host=settings.nas_host,
        port=settings.nas_port,
        username=settings.nas_username,
        timeout_seconds=settings.nas_timeout,
        supports_live_sync=supports_live_sync,
        auth_mode=auth_mode,
        retry_strategy=settings.sync_live_backoff_mode,
        retry_max_attempts=settings.sync_live_max_attempts,
        retry_base_delay_seconds=settings.sync_live_retry_delay_seconds,
        retry_max_delay_seconds=settings.sync_live_backoff_max_delay_seconds,
        retry_jitter_enabled=settings.sync_live_backoff_jitter_enabled,
        retry_jitter_ratio=settings.sync_live_backoff_jitter_ratio,
        live_sync_profiles=["quick", "full"],
        default_live_sync_profile="quick",
    )
