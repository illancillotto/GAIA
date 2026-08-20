from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlparse

from sister_exceptions import SisterRequestCorrelationError


_REMOTE_ID_KEYS = {
    "id",
    "idrichiesta",
    "idrich",
    "richiesta",
    "progrichiesta",
    "progressivo",
    "protocollo",
    "requestid",
}


@dataclass(frozen=True, slots=True)
class SisterRemoteRequestRow:
    index: int
    key: str
    remote_id: str | None
    state: str
    text: str
    hrefs: tuple[str, ...]
    download_href: str | None
    delete_href: str | None


@dataclass(frozen=True, slots=True)
class SisterRequestCorrelation:
    local_request_id: str
    baseline_keys: frozenset[str]
    expected_tokens: tuple[str, ...]
    remote_id: str | None = None

    def with_remote_id(self, remote_id: str | None) -> "SisterRequestCorrelation":
        return replace(self, remote_id=remote_id or self.remote_id)


def normalize_portal_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    ascii_value = decomposed.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", " ", ascii_value.upper()).strip()


def expected_request_tokens(request: object) -> tuple[str, ...]:
    values = [
        getattr(request, "subject_id", None),
        getattr(request, "comune", None),
        getattr(request, "foglio", None),
        getattr(request, "particella", None),
        getattr(request, "subalterno", None),
    ]
    normalized = [normalize_portal_text(str(value)) for value in values if value not in (None, "")]
    return tuple(value for value in normalized if len(value) >= 2)


def build_correlation(request: object, rows: list[SisterRemoteRequestRow]) -> SisterRequestCorrelation:
    return SisterRequestCorrelation(
        local_request_id=str(getattr(request, "id")),
        baseline_keys=frozenset(row.key for row in rows),
        expected_tokens=expected_request_tokens(request),
    )


def parse_remote_rows(payload: list[dict[str, object]]) -> list[SisterRemoteRequestRow]:
    rows: list[SisterRemoteRequestRow] = []
    for index, item in enumerate(payload):
        text = str(item.get("text") or "").strip()
        hrefs = tuple(str(href) for href in item.get("hrefs", []) if href)
        values = tuple(str(value) for value in item.get("values", []) if value)
        if not text and not hrefs and not values:
            continue
        remote_id = extract_remote_id((*hrefs, *values))
        normalized = normalize_portal_text(text)
        state = _classify_state(normalized)
        download_href = _find_href(hrefs, ("checkrichiesta", "salva", "download", "dettaglio"))
        delete_href = _find_href(hrefs, ("elimina", "delete", "cancella"))
        key = remote_id or _stable_row_key(normalized, hrefs, values)
        rows.append(
            SisterRemoteRequestRow(
                index=index,
                key=key,
                remote_id=remote_id,
                state=state,
                text=text,
                hrefs=hrefs,
                download_href=download_href,
                delete_href=delete_href,
            )
        )
    return rows


def extract_remote_id(values: tuple[str, ...]) -> str | None:
    for value in values:
        parsed = urlparse(value)
        for key, candidate in parse_qsl(parsed.query, keep_blank_values=False):
            if normalize_portal_text(key).replace(" ", "").lower() in _REMOTE_ID_KEYS and candidate:
                return candidate.strip()
        match = re.search(
            r"(?:idRichiesta|idRich|progRichiesta|protocollo|requestId)[=/:'\"\s]+([A-Za-z0-9._-]+)",
            value,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)
    return None


def correlate_remote_row(
    rows: list[SisterRemoteRequestRow],
    correlation: SisterRequestCorrelation,
) -> SisterRemoteRequestRow | None:
    if correlation.remote_id:
        matches = [row for row in rows if row.remote_id == correlation.remote_id]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise SisterRequestCorrelationError(
                f"Identificativo SISTER duplicato per richiesta {correlation.local_request_id}"
            )

    new_rows = [row for row in rows if row.key not in correlation.baseline_keys]
    if not new_rows:
        return None
    if len(new_rows) == 1:
        return new_rows[0]

    token_matches = [row for row in new_rows if _matches_expected_tokens(row, correlation.expected_tokens)]
    if len(token_matches) == 1:
        return token_matches[0]
    raise SisterRequestCorrelationError(
        f"Correlazione SISTER ambigua per richiesta {correlation.local_request_id}: {len(new_rows)} nuove righe"
    )


def _classify_state(normalized_text: str) -> str:
    if "NON EVADIBIL" in normalized_text:
        return "non_evadibile"
    if "ESPLETAT" in normalized_text or "PRONT" in normalized_text:
        return "ready"
    if "IN LAVORAZIONE" in normalized_text or "DA ESPLETARE" in normalized_text or "IN ATTESA" in normalized_text:
        return "pending"
    return "unknown"


def _find_href(hrefs: tuple[str, ...], markers: tuple[str, ...]) -> str | None:
    for href in hrefs:
        lowered = href.lower()
        if any(marker in lowered for marker in markers):
            return href
    return None


def _stable_row_key(normalized_text: str, hrefs: tuple[str, ...], values: tuple[str, ...]) -> str:
    stable_text = re.sub(r"\b(?:NON EVADIBILE|ESPLETATA|ESPLETATE|PRONTA|IN LAVORAZIONE|IN ATTESA)\b", "", normalized_text)
    payload = "|".join((stable_text, *sorted(hrefs), *sorted(values)))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _matches_expected_tokens(row: SisterRemoteRequestRow, expected_tokens: tuple[str, ...]) -> bool:
    if not expected_tokens:
        return False
    normalized_row = normalize_portal_text(row.text)
    meaningful = [token for token in expected_tokens if len(token) >= 3]
    required = meaningful or list(expected_tokens)
    return all(token in normalized_row for token in required)
