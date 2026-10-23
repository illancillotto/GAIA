"""Pick the inCASS notice that belongs to one ruolo avviso.

inCASS notices are fetched by year and tax code, so a contribuente with more
avvisi in the same year has several candidates. The inCASS code is the CNC
without the ``01.`` prefix plus a check digit (``01.02021780106733`` ->
``020217801067337``), which identifies the avviso's own notice.
"""

from collections.abc import Mapping, Sequence
from typing import Any

CNC_PREFIX = "01."


def cnc_notice_prefix(codice_cnc: str | None) -> str:
    code = (codice_cnc or "").strip()
    return code.removeprefix(CNC_PREFIX)


def select_incass_notice(
    codice_cnc: str | None,
    preferred_notice_id: str | None,
    candidates: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    """Operator-chosen code first, then the CNC; a lone candidate is kept as before."""
    if preferred_notice_id:
        preferred = [
            notice for notice in candidates if notice["source_notice_id"] == preferred_notice_id
        ]
        if preferred:
            return preferred[0]
    prefix = cnc_notice_prefix(codice_cnc)
    if prefix:
        own = [
            notice for notice in candidates if (notice["source_notice_id"] or "").startswith(prefix)
        ]
        if own:
            return own[0]
    # Several notices and none is this avviso's: attaching another avviso's notice is wrong.
    return candidates[0] if len(candidates) == 1 else None
