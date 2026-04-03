from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CapacitasAppDefinition:
    key: str
    display_name: str
    base_url: str
    auth_cookie_name: str
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def main_url(self, token: str) -> str:
        return f"{self.base_url}/pages/main.aspx?token={token}&app={self.key}&tenant="

    def keepalive_url(self, path: str) -> str:
        return f"{self.base_url}{path}"


CAPACITAS_APPS: dict[str, CapacitasAppDefinition] = {
    "involture": CapacitasAppDefinition(
        key="involture",
        display_name="inVOLTURE",
        base_url="https://involture1.servizicapacitas.com",
        auth_cookie_name="involture__AUTH_COOKIE",
        aliases=("involture", "visure", "invisure"),
    ),
    "incass": CapacitasAppDefinition(
        key="incass",
        display_name="inCASS",
        base_url="https://incass3.servizicapacitas.com",
        auth_cookie_name="incass__AUTH_COOKIE",
        aliases=("incass", "cass"),
    ),
    "inbollettini": CapacitasAppDefinition(
        key="inbollettini",
        display_name="inBOLLETTINI",
        base_url="https://inbollettini.servizicapacitas.com",
        auth_cookie_name="inbollettini__AUTH_COOKIE",
        aliases=("inbollettini", "bollettini"),
    ),
}


def get_capacitas_app(app_key: str) -> CapacitasAppDefinition:
    normalized_key = app_key.strip().lower()

    if normalized_key in CAPACITAS_APPS:
        return CAPACITAS_APPS[normalized_key]

    for app in CAPACITAS_APPS.values():
        if normalized_key in app.aliases:
            return app

    available = ", ".join(sorted(CAPACITAS_APPS))
    raise ValueError(f"App '{app_key}' non configurata. Disponibili: {available}")


def get_app_hosts() -> dict[str, str]:
    return {key: app.base_url for key, app in CAPACITAS_APPS.items()}
