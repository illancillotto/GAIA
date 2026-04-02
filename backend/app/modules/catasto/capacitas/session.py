from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import re

import httpx

logger = logging.getLogger(__name__)

SSO_BASE = "https://sso.servizicapacitas.com"
LOGIN_URL = f"{SSO_BASE}/pages/login.aspx"
KEEP_ALIVE_PATH = "/pages/handler/handlerKeepSessionAlive.ashx"
KEEP_ALIVE_INTERVAL = 25

APP_HOSTS = {
    "involture": "https://involture1.servizicapacitas.com",
    "incass": "https://incass3.servizicapacitas.com",
    "inbollettini": "https://inbollettini.servizicapacitas.com",
}


@dataclass
class CapacitasSession:
    token: str
    app_cookies: dict[str, dict] = field(default_factory=dict)
    authenticated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_keepalive: dict[str, datetime] = field(default_factory=dict)

    def is_alive(self) -> bool:
        return bool(self.token)


class CapacitasSessionManager:
    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self._session: CapacitasSession | None = None
        self._http: httpx.AsyncClient | None = None
        self._keepalive_tasks: dict[str, asyncio.Task] = {}

    async def __aenter__(self) -> "CapacitasSessionManager":
        await self.login()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    async def login(self) -> CapacitasSession:
        self._http = httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/148.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )

        logger.info("Capacitas login: GET %s", LOGIN_URL)
        response = await self._http.get(LOGIN_URL)
        response.raise_for_status()

        viewstate, eventvalidation = self._extract_aspnet_fields(response.text)
        if not viewstate:
            raise RuntimeError("Capacitas login: __VIEWSTATE non trovato nella pagina di login")

        form_data = {
            "__VIEWSTATE": viewstate,
            "__EVENTVALIDATION": eventvalidation,
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "Capacitas$ContentMain$txtUsername": self.username,
            "Capacitas$ContentMain$txtPassword": self.password,
            "Capacitas$ContentMain$btnLogin": "Entra",
        }
        logger.info("Capacitas login: POST credenziali per %s", self.username)
        response = await self._http.post(
            LOGIN_URL,
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()

        token = self._extract_token(str(response.url)) or self._extract_token_from_cookies()
        if not token:
            raise RuntimeError(
                f"Capacitas login fallito: token non trovato. URL finale: {response.url}. "
                "Verifica credenziali e nomi campi form.",
            )

        logger.info("Capacitas login OK: token=%s...", token[:8])
        self._session = CapacitasSession(token=token)
        return self._session

    async def activate_app(self, app: str) -> None:
        if app not in APP_HOSTS:
            raise ValueError(f"App '{app}' non configurata. Disponibili: {list(APP_HOSTS)}")
        if self._session is None or self._http is None:
            raise RuntimeError("Sessione non inizializzata. Chiamare login() prima.")

        host = APP_HOSTS[app]
        url = f"{host}/pages/main.aspx?token={self._session.token}&app={app}&tenant="
        logger.info("Capacitas activate_app: GET %s", url)
        response = await self._http.get(url)
        response.raise_for_status()

        app_cookie_name = f"{app}__AUTH_COOKIE"
        cookies = dict(self._http.cookies)
        if app_cookie_name not in cookies:
            logger.warning("Cookie %s non impostato dopo activate_app", app_cookie_name)
        self._session.app_cookies[app] = cookies

    async def start_keepalive(self, app: str) -> None:
        if app in self._keepalive_tasks and not self._keepalive_tasks[app].done():
            return
        host = APP_HOSTS[app]
        task = asyncio.create_task(self._keepalive_loop(app, host), name=f"capacitas-keepalive-{app}")
        self._keepalive_tasks[app] = task

    async def _keepalive_loop(self, app: str, host: str) -> None:
        if self._session is None or self._http is None:
            return
        url = f"{host}{KEEP_ALIVE_PATH}"
        while True:
            await asyncio.sleep(KEEP_ALIVE_INTERVAL)
            try:
                response = await self._http.post(url, headers={"X-Requested-With": "XMLHttpRequest"})
                if response.status_code == 200:
                    self._session.last_keepalive[app] = datetime.now(timezone.utc)
            except Exception as exc:  # pragma: no cover - external network
                logger.warning("Capacitas keep-alive error: app=%s err=%s", app, exc)

    def stop_keepalive(self, app: str) -> None:
        task = self._keepalive_tasks.get(app)
        if task and not task.done():
            task.cancel()

    def get_http_client(self) -> httpx.AsyncClient:
        if self._http is None:
            raise RuntimeError("Sessione non inizializzata. Chiamare login() prima.")
        return self._http

    def get_token(self) -> str:
        if self._session is None:
            raise RuntimeError("Sessione non inizializzata.")
        return self._session.token

    async def close(self) -> None:
        for app in list(self._keepalive_tasks):
            self.stop_keepalive(app)
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    @staticmethod
    def _extract_aspnet_fields(html: str) -> tuple[str, str]:
        viewstate_match = re.search(r'<input[^>]+id="__VIEWSTATE"[^>]+value="([^"]*)"', html)
        eventvalidation_match = re.search(r'<input[^>]+id="__EVENTVALIDATION"[^>]+value="([^"]*)"', html)
        return (
            viewstate_match.group(1) if viewstate_match else "",
            eventvalidation_match.group(1) if eventvalidation_match else "",
        )

    @staticmethod
    def _extract_token(url: str) -> str | None:
        match = re.search(r"[?&]token=([0-9a-f-]{36})", url, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_token_from_cookies(self) -> str | None:
        if self._http is None:
            return None
        auth_cookie = self._http.cookies.get("AUTH_COOKIE", "")
        return auth_cookie.split("|")[0] if auth_cookie and "|" in auth_cookie else None
