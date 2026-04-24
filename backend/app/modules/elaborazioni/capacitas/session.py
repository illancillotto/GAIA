from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import html
import json
import logging
from pathlib import Path
import re
from urllib.parse import quote, unquote_plus
from uuid import uuid4

import httpx

from app.core.config import settings
from app.modules.elaborazioni.capacitas.apps import get_app_hosts, get_capacitas_app
from app.modules.elaborazioni.capacitas.decoder import decode_response

logger = logging.getLogger(__name__)

SSO_BASE = "https://sso.servizicapacitas.com"
LOGIN_URL = f"{SSO_BASE}/pages/login.aspx"
SSO_TILES_URL = f"{SSO_BASE}/pages/ajax/ajaxTiles.aspx"
KEEP_ALIVE_PATH = "/pages/handler/handlerKeepSessionAlive.ashx"
KEEP_ALIVE_INTERVAL = 25
SSO_MAIN_URL_TEMPLATE = f"{SSO_BASE}/pages/main.aspx?token={{token}}&app=&tenant="

APP_HOSTS = get_app_hosts()


@dataclass
class CapacitasSession:
    token: str
    app_cookies: dict[str, list[dict[str, str]]] = field(default_factory=dict)
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
        self._debug_dir: Path | None = None
        self._last_login_page: str | None = None

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

        login_url = self._build_login_url()
        logger.info("Capacitas login: GET %s", login_url)
        response = await self._http.get(login_url)
        response.raise_for_status()
        self._last_login_page = response.text

        form_data = self._build_login_form_data(response.text, self.username, self.password)
        if "__VIEWSTATE" not in form_data:
            raise RuntimeError("Capacitas login: __VIEWSTATE non trovato nella pagina di login")
        logger.info("Capacitas login: POST credenziali per %s", self.username)
        response = await self._http.post(
            login_url,
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()

        token = (
            self._extract_token_from_response(response)
            or self._extract_token_from_cookies()
            or self._extract_token_from_html(response.text)
        )
        if not token:
            diagnostics = self._build_login_diagnostics(response)
            artifact_path = self._write_login_debug_artifacts(response, diagnostics)
            logger.error("Capacitas login fallito per %s: %s", self.username, diagnostics)
            raise RuntimeError(
                "Capacitas login fallito: token non trovato dopo il POST credenziali. "
                f"{diagnostics}"
                + (f" | artifact={artifact_path}" if artifact_path else ""),
            )

        logger.info("Capacitas login OK: token=%s...", token[:8])
        self._session = CapacitasSession(token=token)
        return self._session

    async def activate_app(self, app: str) -> None:
        if self._session is None or self._http is None:
            raise RuntimeError("Sessione non inizializzata. Chiamare login() prima.")

        app_config = get_capacitas_app(app)
        url = await self._resolve_app_launch_url(app_config.key)
        logger.info("Capacitas activate_app: GET %s", url)
        response = await self._http.get(url)
        response.raise_for_status()

        final_url = str(response.url)
        if "/pages/errore.aspx" in final_url:
            raise RuntimeError(
                "Capacitas activate_app fallito: il portale ha rediretto su errore.aspx "
                f"per app={app_config.key}. URL finale={final_url}"
            )

        cookies = self._snapshot_cookies()
        if not any(cookie["name"] == app_config.auth_cookie_name for cookie in cookies):
            logger.warning("Cookie %s non impostato dopo activate_app", app_config.auth_cookie_name)
        self._session.app_cookies[app_config.key] = cookies

    def _build_login_url(self) -> str:
        cod_cons = (settings.capacitas_cod_cons or "").strip()
        if not cod_cons:
            return LOGIN_URL
        return f"{LOGIN_URL}?op=&codCons={quote(cod_cons, safe='')}&app=&tenant="

    async def _resolve_app_launch_url(self, app: str) -> str:
        if self._session is None or self._http is None:
            raise RuntimeError("Sessione non inizializzata. Chiamare login() prima.")

        app_config = get_capacitas_app(app)
        response = await self._http.post(
            SSO_TILES_URL,
            data={"op": "tiles", "key": quote("root", safe="")},
            headers={
                "Accept": "*/*",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": SSO_MAIN_URL_TEMPLATE.format(token=self._session.token),
            },
        )
        response.raise_for_status()

        try:
            tiles_payload = decode_response(response.text)
        except Exception as exc:
            logger.warning("Capacitas activate_app: decode tile root fallito per app=%s err=%s", app_config.key, exc)
            return app_config.main_url(self._session.token)

        if not isinstance(tiles_payload, list):
            logger.warning(
                "Capacitas activate_app: payload tiles inatteso per app=%s type=%s",
                app_config.key,
                type(tiles_payload).__name__,
            )
            return app_config.main_url(self._session.token)

        launch = self._match_app_launch_url(tiles_payload, app_config)
        return launch or app_config.main_url(self._session.token)

    def _match_app_launch_url(self, tiles_payload: list[object], app_config) -> str | None:
        normalized_targets = {app_config.key, *app_config.aliases, app_config.display_name.lower()}
        for item in tiles_payload:
            if not isinstance(item, dict):
                continue
            tile_payload = item.get("tile")
            if not isinstance(tile_payload, str) or not tile_payload.strip():
                continue

            tile_html = unquote_plus(tile_payload)
            tile_app = self._extract_tile_attr(tile_html, "app").lower()
            tile_descr = self._extract_tile_attr(tile_html, "descriz").lower()
            tile_url = unquote_plus(self._extract_tile_attr(tile_html, "url"))
            tile_cod_cons = self._extract_tile_attr(tile_html, "codcons")
            tile_id_run = self._extract_tile_attr(tile_html, "idrun")

            if tile_app not in normalized_targets and tile_descr not in normalized_targets:
                continue
            if not tile_url or not tile_id_run:
                continue

            return (
                f"{tile_url}?token={self._session.token}"
                f"&codConsApp={quote(tile_cod_cons, safe='')}"
                f"&idRun={quote(tile_id_run, safe='')}"
            )
        return None

    @staticmethod
    def _extract_tile_attr(tile_html: str, attr_name: str) -> str:
        match = re.search(rf"data-{re.escape(attr_name)}='([^']*)'", tile_html, re.IGNORECASE)
        return html.unescape(match.group(1)) if match else ""

    async def start_keepalive(self, app: str) -> None:
        app_config = get_capacitas_app(app)
        if app_config.key in self._keepalive_tasks and not self._keepalive_tasks[app_config.key].done():
            return
        task = asyncio.create_task(
            self._keepalive_loop(app_config.key, app_config.keepalive_url(KEEP_ALIVE_PATH)),
            name=f"capacitas-keepalive-{app_config.key}",
        )
        self._keepalive_tasks[app_config.key] = task

    async def _keepalive_loop(self, app: str, url: str) -> None:
        if self._session is None or self._http is None:
            return
        while True:
            await asyncio.sleep(KEEP_ALIVE_INTERVAL)
            try:
                response = await self._http.post(url, headers={"X-Requested-With": "XMLHttpRequest"})
                if response.status_code == 200:
                    self._session.last_keepalive[app] = datetime.now(timezone.utc)
            except Exception as exc:  # pragma: no cover - external network
                logger.warning("Capacitas keep-alive error: app=%s err=%s", app, exc)

    def stop_keepalive(self, app: str) -> None:
        app_key = get_capacitas_app(app).key
        task = self._keepalive_tasks.get(app_key)
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
    def _build_login_form_data(html_text: str, username: str, password: str) -> dict[str, str]:
        form_data: dict[str, str] = {}

        for match in re.finditer(r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]+value="([^"]*)"', html_text, re.IGNORECASE):
            form_data[html.unescape(match.group(1))] = html.unescape(match.group(2))

        username_name = CapacitasSessionManager._extract_input_name_by_id(html_text, "ContentMain_txtUsername")
        password_name = CapacitasSessionManager._extract_input_name_by_id(html_text, "ContentMain_txtPassword")
        submit_name, submit_value = CapacitasSessionManager._extract_submit_name_and_value(html_text, "ContentMain_btnAccedi")
        gau_name = CapacitasSessionManager._extract_input_name_by_id(html_text, "ContentMain_txtGAUerInput")

        if username_name:
            form_data[username_name] = username
        if password_name:
            form_data[password_name] = password
        if submit_name:
            form_data[submit_name] = submit_value or "Accedi"
        if gau_name and gau_name not in form_data:
            form_data[gau_name] = ""

        form_data.setdefault("__LASTFOCUS", "")
        form_data.setdefault("__EVENTTARGET", "")
        form_data.setdefault("__EVENTARGUMENT", "")
        return form_data

    @staticmethod
    def _extract_input_name_by_id(html_text: str, element_id: str) -> str:
        match = re.search(
            rf'<input[^>]+name="([^"]+)"[^>]+id="{re.escape(element_id)}"[^>]*>',
            html_text,
            re.IGNORECASE,
        )
        if not match:
            match = re.search(
                rf'<input[^>]+id="{re.escape(element_id)}"[^>]+name="([^"]+)"[^>]*>',
                html_text,
                re.IGNORECASE,
            )
        return html.unescape(match.group(1)) if match else ""

    @staticmethod
    def _extract_submit_name_and_value(html_text: str, element_id: str) -> tuple[str, str]:
        match = re.search(
            rf'<input[^>]+type="submit"[^>]+name="([^"]+)"[^>]+value="([^"]*)"[^>]+id="{re.escape(element_id)}"[^>]*>',
            html_text,
            re.IGNORECASE,
        )
        if not match:
            match = re.search(
                rf'<input[^>]+type="submit"[^>]+id="{re.escape(element_id)}"[^>]+name="([^"]+)"[^>]+value="([^"]*)"[^>]*>',
                html_text,
                re.IGNORECASE,
            )
        if not match:
            return "", ""
        return html.unescape(match.group(1)), html.unescape(match.group(2))

    @staticmethod
    def _extract_token(url: str) -> str | None:
        match = re.search(r"[?&]token=([0-9a-f-]{36})", url, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_token_from_response(self, response: httpx.Response) -> str | None:
        candidates = [str(response.url)]
        candidates.extend(str(item.url) for item in response.history)
        for candidate in candidates:
            token = self._extract_token(candidate)
            if token:
                return token
        return None

    def _extract_token_from_cookies(self) -> str | None:
        if self._http is None:
            return None
        cookie_values: list[str] = []
        for cookie in self._http.cookies.jar:
            if cookie.name.upper().endswith("AUTH_COOKIE") or cookie.name.upper() == "AUTH_COOKIE":
                cookie_values.append(cookie.value)
        for value in cookie_values:
            match = re.search(r"([0-9a-f-]{36})", value, re.IGNORECASE)
            if match:
                return match.group(1)
            if "|" in value and value.split("|", maxsplit=1)[0]:
                return value.split("|", maxsplit=1)[0]
        return None

    @staticmethod
    def _extract_token_from_html(html_text: str) -> str | None:
        patterns = [
            r"[?&]token=([0-9a-f-]{36})",
            r'["\']token["\']\s*[:=]\s*["\']([0-9a-f-]{36})["\']',
            r'name=["\']token["\'][^>]+value=["\']([0-9a-f-]{36})["\']',
            r'id=["\']token["\'][^>]+value=["\']([0-9a-f-]{36})["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html_text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _build_login_diagnostics(self, response: httpx.Response) -> str:
        title = self._extract_html_title(response.text)
        snippet = self._extract_html_snippet(response.text)
        cookie_names = self._list_cookie_names()
        page_signals = self._detect_login_signals(response.text)

        diagnostics = [
            f"URL finale={response.url}",
            f"title={title or 'n/d'}",
            f"cookies={cookie_names or 'nessuno'}",
        ]
        if page_signals:
            diagnostics.append(f"segnali={page_signals}")
        if snippet:
            diagnostics.append(f"snippet={snippet}")
        return " | ".join(diagnostics)

    def _write_login_debug_artifacts(self, response: httpx.Response, diagnostics: str) -> str | None:
        try:
            base_dir = Path(settings.capacitas_debug_storage_path)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            safe_username = re.sub(r"[^a-zA-Z0-9._-]+", "_", self.username)[:80] or "credential"
            debug_dir = base_dir / f"{timestamp}-{safe_username}-{uuid4().hex[:8]}"
            debug_dir.mkdir(parents=True, exist_ok=True)
            self._debug_dir = debug_dir

            metadata = {
                "username": self.username,
                "login_url": LOGIN_URL,
                "login_request_url": self._build_login_url(),
                "final_url": str(response.url),
                "history_urls": [str(item.url) for item in response.history],
                "status_code": response.status_code,
                "diagnostics": diagnostics,
                "cookies": [
                    {
                        "name": cookie.name,
                        "domain": cookie.domain,
                        "path": cookie.path,
                        "value_preview": cookie.value[:80],
                    }
                    for cookie in self._http.cookies.jar
                ] if self._http is not None else [],
            }
            (debug_dir / "login-get.html").write_text(self._last_login_page or "", encoding="utf-8")
            (debug_dir / "login-post.html").write_text(response.text, encoding="utf-8")
            (debug_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=True, indent=2), encoding="utf-8")
            return str(debug_dir)
        except Exception as exc:  # pragma: no cover - diagnostics fallback
            logger.warning("Capacitas debug artifact write failed for %s: %s", self.username, exc)
            return None

    def _list_cookie_names(self) -> str:
        if self._http is None:
            return ""
        names = sorted({cookie.name for cookie in self._http.cookies.jar})
        return ",".join(names[:12])

    def _snapshot_cookies(self) -> list[dict[str, str]]:
        if self._http is None:
            return []
        return [
            {
                "name": cookie.name,
                "domain": cookie.domain,
                "path": cookie.path,
                "value_preview": cookie.value[:80],
            }
            for cookie in self._http.cookies.jar
        ]

    @staticmethod
    def _extract_html_title(html_text: str) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return CapacitasSessionManager._clean_html_fragment(match.group(1), limit=160)

    @staticmethod
    def _extract_html_snippet(html_text: str) -> str:
        interesting_patterns = [
            r"Credenziali[^<]{0,120}",
            r"utente[^<]{0,120}",
            r"password[^<]{0,120}",
            r"errore[^<]{0,160}",
            r"sessione[^<]{0,160}",
            r"accesso[^<]{0,160}",
            r"login[^<]{0,160}",
        ]
        for pattern in interesting_patterns:
            match = re.search(pattern, html_text, re.IGNORECASE)
            if match:
                return CapacitasSessionManager._clean_html_fragment(match.group(0), limit=220)

        body_text = CapacitasSessionManager._clean_html_fragment(html_text, limit=220)
        return body_text

    @staticmethod
    def _detect_login_signals(html_text: str) -> str:
        normalized = CapacitasSessionManager._clean_html_fragment(html_text, limit=1200).lower()
        signals: list[str] = []
        if "__viewstate" in html_text.lower():
            signals.append("login_form")
        if "capacitias$contentmain$txtusername".lower() in html_text.lower() or "txtusername" in html_text.lower():
            signals.append("username_field")
        if "txtpassword" in html_text.lower():
            signals.append("password_field")
        if "token=" in html_text.lower():
            signals.append("token_in_body")
        if "credenzial" in normalized:
            signals.append("credential_message")
        if "errore" in normalized:
            signals.append("error_message")
        if "sessione" in normalized:
            signals.append("session_message")
        return ",".join(signals[:8])

    @staticmethod
    def _clean_html_fragment(fragment: str, limit: int = 220) -> str:
        cleaned = re.sub(r"<[^>]+>", " ", fragment)
        cleaned = html.unescape(cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) > limit:
            return f"{cleaned[:limit].rstrip()}..."
        return cleaned
