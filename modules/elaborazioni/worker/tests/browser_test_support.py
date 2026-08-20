from __future__ import annotations

from pathlib import Path
from typing import Any

from browser_session import BrowserSession, BrowserSessionConfig


class ScriptedLocator:
    def __init__(
        self,
        *,
        count: int = 1,
        visible: bool = True,
        text: str = "",
        payload: Any = None,
    ) -> None:
        self._count = count
        self.visible = visible
        self.text = text
        self.attrs: dict[str, str | None] = {}
        self.box: dict[str, float] | None = None
        self.payload = payload
        self.error: Exception | None = None
        self.clicks = 0
        self.checks = 0
        self.fills: list[str] = []
        self.children: dict[str, ScriptedLocator] = {}
        self.items: list[ScriptedLocator] = []

    @property
    def first(self) -> "ScriptedLocator":
        return self

    def nth(self, index: int) -> "ScriptedLocator":
        return self.items[index] if self.items else self

    def locator(self, selector: str) -> "ScriptedLocator":
        return self.children.get(selector, ScriptedLocator(count=0))

    def _raise(self) -> None:
        if self.error is not None:
            raise self.error

    async def count(self) -> int:
        self._raise()
        return self._count

    async def is_visible(self) -> bool:
        self._raise()
        return self.visible

    async def inner_text(self, timeout: int | None = None) -> str:
        self._raise()
        return self.text

    async def click(self, timeout: int | None = None) -> None:
        self._raise()
        self.clicks += 1

    async def check(self, timeout: int | None = None) -> None:
        self._raise()
        self.checks += 1

    async def fill(self, value: str, timeout: int | None = None) -> None:
        self._raise()
        self.fills.append(value)

    async def wait_for(self, timeout: int | None = None) -> None:
        self._raise()

    async def get_attribute(self, name: str, timeout: int | None = None) -> str | None:
        self._raise()
        return self.attrs.get(name)

    async def bounding_box(self) -> dict[str, float] | None:
        self._raise()
        return self.box

    async def screenshot(self, **_kwargs: Any) -> bytes:
        self._raise()
        return self.payload if isinstance(self.payload, bytes) else b"image"

    async def evaluate_all(self, _script: str) -> Any:
        self._raise()
        return self.payload if self.payload is not None else []


class ScriptedPage:
    def __init__(self, *, url: str = "about:blank", title: str = "", body: str = "") -> None:
        self.url = url
        self.title_text = title
        self.body = body
        self.locators: dict[str, ScriptedLocator] = {}
        self.roles: dict[tuple[str, str], ScriptedLocator] = {}
        self.gotos: list[str] = []
        self.clicks: list[str] = []
        self.fills: list[tuple[str, str]] = []
        self.types: list[tuple[str, str]] = []
        self.selects: list[tuple[str, str | None, str | None]] = []
        self.checks: list[str] = []
        self.wait_states: list[str] = []
        self.wait_selector_error: Exception | None = None
        self.evaluate_results: list[Any] = []
        self.evaluate_error: Exception | None = None
        self.screenshot_error: Exception | None = None
        self.content_error: Exception | None = None
        self.title_error: Exception | None = None
        self.body_error: Exception | None = None
        self.closed = False
        self.paused = False
        self.events: list[tuple[str, Any]] = []
        self.default_timeout: int | None = None

    def locator(self, selector: str) -> ScriptedLocator:
        if selector == "body":
            locator = ScriptedLocator(text=self.body)
            locator.error = self.body_error
            return locator
        return self.locators.get(selector, ScriptedLocator(count=0))

    def get_by_role(self, role: str, name: str) -> ScriptedLocator:
        return self.roles.get((role, name), ScriptedLocator(count=0))

    async def title(self) -> str:
        if self.title_error is not None:
            raise self.title_error
        return self.title_text

    async def goto(self, url: str, wait_until: str | None = None) -> None:
        self.gotos.append(url)
        self.url = url

    async def click(self, selector: str) -> None:
        self.clicks.append(selector)

    async def fill(self, selector: str, value: str) -> None:
        self.fills.append((selector, value))

    async def type(self, selector: str, value: str, delay: int | None = None) -> None:
        self.types.append((selector, value))

    async def select_option(
        self,
        selector: str,
        *,
        value: str | None = None,
        label: str | None = None,
    ) -> None:
        self.selects.append((selector, value, label))

    async def check(self, selector: str) -> None:
        self.checks.append(selector)

    async def wait_for_selector(self, _selector: str, timeout: int | None = None) -> None:
        if self.wait_selector_error is not None:
            raise self.wait_selector_error

    async def wait_for_load_state(self, state: str, timeout: int | None = None) -> None:
        self.wait_states.append(state)

    async def wait_for_timeout(self, timeout: int) -> None:
        self.wait_states.append(str(timeout))

    async def evaluate(self, _script: str, arg: Any = None) -> Any:
        if self.evaluate_error is not None:
            raise self.evaluate_error
        return self.evaluate_results.pop(0) if self.evaluate_results else None

    async def screenshot(self, **kwargs: Any) -> None:
        if self.screenshot_error is not None:
            raise self.screenshot_error
        path = kwargs.get("path")
        if path:
            Path(path).write_bytes(b"png")

    async def content(self) -> str:
        if self.content_error is not None:
            raise self.content_error
        return "<html>test</html>"

    async def pause(self) -> None:
        self.paused = True

    async def close(self) -> None:
        self.closed = True

    def on(self, event: str, callback: Any) -> None:
        self.events.append((event, callback))

    def set_default_timeout(self, timeout: int) -> None:
        self.default_timeout = timeout


async def noop_async(*_args: Any, **_kwargs: Any) -> None:
    return None


async def true_async(*_args: Any, **_kwargs: Any) -> bool:
    return True


async def false_async(*_args: Any, **_kwargs: Any) -> bool:
    return False


def make_session(page: ScriptedPage | None = None, *, debug_path: Path | None = None) -> BrowserSession:
    session = BrowserSession(BrowserSessionConfig(debug_artifacts_path=debug_path))
    session._page = page or ScriptedPage()
    session._trace_state = noop_async
    return session
