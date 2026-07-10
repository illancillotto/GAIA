from __future__ import annotations

from datetime import datetime, timezone
import socket
from urllib.parse import quote


DISTRETTI_TILE_LAYER = "cat_distretti"
DISTRETTI_BOUNDARIES_TILE_LAYER = "cat_distretti_boundaries"
PARTICELLE_TILE_LAYER = "cat_particelle_current"
DELIVERY_POINTS_TILE_LAYER = "cat_delivery_points_current"
IRRIGATION_CANALS_TILE_LAYER = "cat_irrigation_canals_current"
DUI_TILE_LAYER = "cat_dui_2026_current"
DUI_2026_TILE_LAYER = DUI_TILE_LAYER
GIS_TILE_LAYERS = [
    DISTRETTI_TILE_LAYER,
    DISTRETTI_BOUNDARIES_TILE_LAYER,
    PARTICELLE_TILE_LAYER,
    DELIVERY_POINTS_TILE_LAYER,
    IRRIGATION_CANALS_TILE_LAYER,
    DUI_TILE_LAYER,
]
DEFAULT_DOCKER_SOCKET_PATH = "/var/run/docker.sock"
MARTIN_CONTAINER_NAME = "gaia-martin"


class MartinRestartError(RuntimeError):
    pass


def restart_martin_container(
    *,
    docker_socket_path: str = DEFAULT_DOCKER_SOCKET_PATH,
    container_name: str = MARTIN_CONTAINER_NAME,
    timeout_seconds: float = 10.0,
) -> None:
    encoded_container = quote(container_name, safe="")
    request = (
        f"POST /containers/{encoded_container}/restart?t=10 HTTP/1.1\r\n"
        "Host: docker\r\n"
        "Content-Length: 0\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("ascii")

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(timeout_seconds)
            client.connect(docker_socket_path)
            client.sendall(request)
            response = client.recv(4096)
    except OSError as exc:
        raise MartinRestartError(f"Riavvio Martin non disponibile: {exc}") from exc

    status_line = response.split(b"\r\n", 1)[0].decode("ascii", errors="replace")
    if " 204 " not in status_line and not status_line.endswith(" 204 No Content"):
        raise MartinRestartError(f"Riavvio Martin non completato: {status_line or 'risposta Docker vuota'}")


def generate_gis_tile_cache_revision(*, restart_martin: bool = True) -> dict[str, object]:
    refreshed_at = datetime.now(timezone.utc)
    revision = refreshed_at.strftime("%Y%m%d%H%M%S%f")
    martin_restarted = False
    restart_error = None
    if restart_martin:
        try:
            restart_martin_container()
            martin_restarted = True
        except MartinRestartError as exc:
            restart_error = str(exc)
    return {
        "tile_revision": revision,
        "refreshed_at": refreshed_at,
        "affected_layers": list(GIS_TILE_LAYERS),
        "martin_restarted": martin_restarted,
        "restart_error": restart_error,
        "message": (
            "Cache GIS aggiornata e Martin riavviato. Ricaricare la mappa se e gia aperta."
            if martin_restarted
            else "Revisione cache GIS aggiornata, ma Martin non e stato riavviato."
        ),
    }
