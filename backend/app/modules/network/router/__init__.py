import urllib.error
import urllib.request

from fastapi import APIRouter

from app.modules.network.router.helpers.devices import _resolve_device_label
from app.modules.network.router.routes.devices import router as devices_router
from app.modules.network.router.routes.firewalls import router as firewalls_router
from app.modules.network.router.routes.floor_plans import router as floor_plans_router
from app.modules.network.router.routes.overview import router as overview_router
from app.modules.network.router.routes.scans import router as scans_router
from app.modules.network.router.routes.tracking import router as tracking_router
from app.modules.network.router.routes.vpn_access import router as vpn_access_router
from app.modules.network.services import run_network_scan
from app.modules.network.sophos_snmp import poll_sophos_firewall_metrics

router = APIRouter(prefix="/network", tags=["network"])
router.include_router(vpn_access_router)
router.include_router(overview_router)
router.include_router(devices_router)
router.include_router(tracking_router)
router.include_router(firewalls_router)
router.include_router(scans_router)
router.include_router(floor_plans_router)

__all__ = [
    "_resolve_device_label",
    "poll_sophos_firewall_metrics",
    "router",
    "run_network_scan",
    "urllib",
]
