from __future__ import annotations

from app.modules.elaborazioni.capacitas.apps.involture.domande_irrigue import DomandeIrrigueScraper

FULL_CYCLE = "full-v1"
RECENT_PREFIX = "recent-v1:"


def sync_cycle_key(state, day: str) -> str:
    completed = state.completed_cycle_key or ""
    if completed == FULL_CYCLE or completed.startswith(RECENT_PREFIX):
        return RECENT_PREFIX + day
    if state.cycle_key != FULL_CYCLE and state.pending_job_id is None:
        state.cursor = None
    return FULL_CYCLE


def refresh_years(state, year: int) -> list[int] | None:
    completed = state.completed_cycle_key or ""
    if completed == FULL_CYCLE or completed.startswith(RECENT_PREFIX):
        return [year - 1, year]
    return None


class RecentDomandeIrrigueScraper(DomandeIrrigueScraper):
    def __init__(self, manager, years: list[int]) -> None:
        super().__init__(manager)
        self._years = set(years)

    def _filter(self, result) -> None:
        selected = []
        for domanda in result.domande:
            year = str(domanda.anno or "").strip()
            if len(year) != 4 or not year.isascii() or not year.isdigit():
                raise ValueError(f"Anno domanda irrigua non valido: {domanda.anno!r}")
            if int(year) in self._years:
                selected.append(domanda)
        result.domande = selected
        result.total_domande = len(selected)

    async def fetch_domande_irrigue(self, **kwargs):
        result = await super().fetch_domande_irrigue(**kwargs)
        self._filter(result)
        return result

    async def _append_details(self, result, referer) -> None:
        self._filter(result)
        await super()._append_details(result, referer)


def limit_scraper(scraper, payload):
    years = (payload or {}).get("refresh_years")
    if years is None:
        return scraper
    if (
        not isinstance(years, list)
        or len(years) != 2
        or any(type(year) is not int or not 1000 <= year <= 9999 for year in years)
        or years[1] != years[0] + 1
    ):
        raise ValueError("refresh_years deve contenere due anni consecutivi")
    return RecentDomandeIrrigueScraper(scraper._manager, years)
