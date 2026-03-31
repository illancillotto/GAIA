from dataclasses import dataclass
import shlex
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
    _client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            get_transport = getattr(self._client, "get_transport", None)
            if get_transport is None:
                return self._client
            transport = get_transport()
            if transport is not None and transport.is_active():
                return self._client
            self.close()

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
        except Exception as exc:  # pragma: no cover
            raise NasConnectorError("SSH connection failed") from exc

        self._client = client
        return client

    def run_command(self, command: str) -> str:
        try:
            client = self._get_client()
            _, stdout, stderr = client.exec_command(command, timeout=self.timeout)
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode("utf-8")
            error_output = stderr.read().decode("utf-8").strip()
        except NasConnectorError:
            raise
        except Exception as exc:  # pragma: no cover
            raise NasConnectorError(f"SSH command failed: {command}") from exc

        if exit_status != 0:
            raise NasConnectorError(
                f"SSH command returned exit status {exit_status} for '{command}': {error_output}"
            )

        return output

    def download_file(self, path: str) -> bytes:
        client = self._get_client()
        try:
            sftp = client.open_sftp()
            try:
                with sftp.file(path, "rb") as remote_file:
                    return remote_file.read()
            finally:
                sftp.close()
        except Exception as exc:  # pragma: no cover
            try:
                return self._download_file_via_shell(client, path)
            except Exception as fallback_exc:  # pragma: no cover
                raise NasConnectorError(f"SSH file download failed: {path}") from fallback_exc

    def ensure_directory(self, path: str) -> None:
        quoted_path = shlex.quote(path)
        self.run_command(f"mkdir -p {quoted_path}")

    def path_exists(self, path: str) -> bool:
        quoted_path = shlex.quote(path)
        output = self.run_command(f"if [ -e {quoted_path} ]; then printf '1'; else printf '0'; fi")
        return output.strip() == "1"

    def upload_file(self, path: str, content: bytes) -> None:
        client = self._get_client()
        parent_path = path.rsplit("/", 1)[0] if "/" in path else None
        if parent_path:
            self.run_command(f"mkdir -p {shlex.quote(parent_path)}")

        try:
            sftp = client.open_sftp()
            try:
                with sftp.file(path, "wb") as remote_file:
                    remote_file.write(content)
                    remote_file.flush()
            finally:
                sftp.close()
        except Exception as exc:  # pragma: no cover
            raise NasConnectorError(f"SSH file upload failed: {path}") from exc

    def _download_file_via_shell(self, client: Any, path: str) -> bytes:
        quoted_path = shlex.quote(path)
        _, stdout, stderr = client.exec_command(f"cat {quoted_path}", timeout=self.timeout)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read()
        error_output = stderr.read().decode("utf-8", errors="replace").strip()
        if exit_status != 0:
            raise NasConnectorError(
                f"SSH command returned exit status {exit_status} for 'cat {quoted_path}': {error_output}"
            )
        return output

    def close(self) -> None:
        if self._client is None:
            return
        try:
            self._client.close()
        finally:
            self._client = None


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
