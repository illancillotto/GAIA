from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import html
import json
import logging
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://login.bonificaoristanese.it"
LOGIN_URL = f"{BASE_URL}/login"


@dataclass
class BonificaOristaneseSession:
    authenticated_url: str
    cookie_names: list[str] = field(default_factory=list)
    authenticated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BonificaOristaneseSessionManager:
    def __init__(self, login_identifier: str, password: str, remember_me: bool = False) -> None:
        self.login_identifier = login_identifier
        self.password = password
        self.remember_me = remember_me
        self._http: httpx.AsyncClient | None = None
        self._session: BonificaOristaneseSession | None = None
        self._last_login_page: str | None = None
        self._debug_dir: Path | None = None

    async def __aenter__(self) -> "BonificaOristaneseSessionManager":
        await self.login()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    async def login(self) -> BonificaOristaneseSession:
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
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

        logger.info("Bonifica Oristanese login: GET %s", LOGIN_URL)
        response = await self._http.get(LOGIN_URL)
        response.raise_for_status()
        self._last_login_page = response.text

        csrf_token = self._extract_csrf_token(response.text)
        if not csrf_token:
            raise RuntimeError("Bonifica Oristanese login: token CSRF `_token` non trovato nella pagina login")

        form_data = {
            "_token": csrf_token,
            "email": self.login_identifier,
            "password": self.password,
        }
        if self.remember_me:
            form_data["remember"] = "on"

        logger.info("Bonifica Oristanese login: POST credenziali per %s", self.login_identifier)
        post_response = await self._http.post(
            LOGIN_URL,
            data=form_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": LOGIN_URL,
            },
        )
        post_response.raise_for_status()

        if self._is_login_failure(post_response):
            diagnostics = self._build_login_diagnostics(post_response)
            artifact_path = self._write_login_debug_artifacts(post_response, diagnostics)
            logger.error("Bonifica Oristanese login fallito per %s: %s", self.login_identifier, diagnostics)
            raise RuntimeError(
                "Bonifica Oristanese login fallito: autenticazione non completata. "
                f"{diagnostics}"
                + (f" | artifact={artifact_path}" if artifact_path else ""),
            )

        authenticated_url = str(post_response.url)
        cookie_names = self._list_cookie_names()
        self._session = BonificaOristaneseSession(
            authenticated_url=authenticated_url,
            cookie_names=cookie_names,
        )
        logger.info(
            "Bonifica Oristanese login OK: identifier=%s authenticated_url=%s cookies=%s",
            self.login_identifier,
            authenticated_url,
            ",".join(cookie_names[:8]) if cookie_names else "none",
        )
        return self._session

    async def fetch_page(self, path: str) -> httpx.Response:
        if self._http is None or self._session is None:
            raise RuntimeError("Sessione non inizializzata. Chiamare login() prima.")
        target_url = self.resolve_url(path)
        response = await self._http.get(target_url)
        response.raise_for_status()
        return response

    def resolve_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return urljoin(f"{BASE_URL}/", path.lstrip("/"))

    def get_http_client(self) -> httpx.AsyncClient:
        if self._http is None:
            raise RuntimeError("Sessione non inizializzata. Chiamare login() prima.")
        return self._http

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    @staticmethod
    def _extract_csrf_token(html_text: str) -> str | None:
        match = re.search(r'<input[^>]+name="_token"[^>]+value="([^"]+)"', html_text, re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def _extract_failure_message(html_text: str) -> str | None:
        patterns = [
            r"Credenziali non valide",
            r"Hai dimenticato la password\?",
            r"Sei gi[aà] un consorziato\?",
        ]
        for pattern in patterns:
            match = re.search(pattern, html_text, re.IGNORECASE)
            if match:
                return BonificaOristaneseSessionManager._clean_html_fragment(match.group(0), limit=180)
        return None

    @classmethod
    def _is_login_form_present(cls, html_text: str) -> bool:
        lowered = html_text.lower()
        return (
            '<form' in lowered
            and 'name="_token"' in lowered
            and 'name="email"' in lowered
            and 'name="password"' in lowered
            and '/login' in lowered
        )

    @classmethod
    def _is_login_failure(cls, response: httpx.Response) -> bool:
        failure_message = cls._extract_failure_message(response.text)
        path = urlparse(str(response.url)).path.rstrip("/") or "/"
        if failure_message == "Credenziali non valide":
            return True
        if path == "/login" and cls._is_login_form_present(response.text):
            return True
        return False

    def _build_login_diagnostics(self, response: httpx.Response) -> str:
        title = self._extract_html_title(response.text)
        snippet = self._extract_html_snippet(response.text)
        cookie_names = ",".join(self._list_cookie_names()) or "nessuno"
        failure_message = self._extract_failure_message(response.text) or "n/d"
        diagnostics = [
            f"URL finale={response.url}",
            f"title={title or 'n/d'}",
            f"cookies={cookie_names}",
            f"esito={failure_message}",
        ]
        if snippet:
            diagnostics.append(f"snippet={snippet}")
        return " | ".join(diagnostics)

    def _write_login_debug_artifacts(self, response: httpx.Response, diagnostics: str) -> str | None:
        try:
            base_dir = Path(settings.bonifica_oristanese_debug_storage_path)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            safe_identifier = re.sub(r"[^a-zA-Z0-9._-]+", "_", self.login_identifier)[:80] or "credential"
            debug_dir = base_dir / f"{timestamp}-{safe_identifier}-{uuid4().hex[:8]}"
            debug_dir.mkdir(parents=True, exist_ok=True)
            self._debug_dir = debug_dir

            metadata = {
                "identifier": self.login_identifier,
                "login_url": LOGIN_URL,
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
            (debug_dir / "metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
            return str(debug_dir)
        except Exception as exc:  # pragma: no cover
            logger.warning("Bonifica Oristanese debug artifact write failed for %s: %s", self.login_identifier, exc)
            return None

    def _list_cookie_names(self) -> list[str]:
        if self._http is None:
            return []
        return sorted({cookie.name for cookie in self._http.cookies.jar})

    @staticmethod
    def _extract_html_title(html_text: str) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return BonificaOristaneseSessionManager._clean_html_fragment(match.group(1), limit=160)

    @staticmethod
    def _extract_html_snippet(html_text: str) -> str:
        interesting_patterns = [
            r"Credenziali non valide",
            r"Codice utente/Email",
            r"Hai dimenticato la password\?",
            r"Sei gi[aà] un consorziato\?",
            r"Non sei un consorziato\?",
        ]
        for pattern in interesting_patterns:
            match = re.search(pattern, html_text, re.IGNORECASE)
            if match:
                return BonificaOristaneseSessionManager._clean_html_fragment(match.group(0), limit=220)
        return BonificaOristaneseSessionManager._clean_html_fragment(html_text, limit=220)

    @staticmethod
    def _clean_html_fragment(fragment: str, limit: int = 220) -> str:
        cleaned = re.sub(r"<[^>]+>", " ", fragment)
        cleaned = html.unescape(cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) > limit:
            return f"{cleaned[:limit].rstrip()}..."
        return cleaned
