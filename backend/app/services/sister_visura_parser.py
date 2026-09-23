from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

PARSER_VERSION = "sister-visura-v2"
_PARCEL_RE = re.compile(
    r"Foglio\s*:?\s*(?P<foglio>[^\s]+)\s+Particella\s*:?\s*(?P<particella>[^\s]+)"
    r"(?:\s+Subalterno:\s*(?P<sub>[^\s]+))?",
    re.I,
)
_COMUNE_RE = re.compile(r"Comune di\s+(?P<nome>.+?)\s+\((?:Codice:)?(?P<codice>[A-Z0-9]+)\)", re.I)
_OWNER_RE = re.compile(
    r"(?:^|\s)\d*\s*(?P<name>.+?)\s+nat[oa]\s+a\s+(?P<place>.+?)\s+"
    r"\(.*?\)\s+il\s+(?P<date>\d{2}/\d{2}/\d{4})",
    re.I,
)
_CF_RE = re.compile(r"^[A-Z0-9]{11,16}\*?$", re.I)
_RIGHT_RE = re.compile(r"\(\d+\)\s*(?P<right>.+?)\s+(?P<share>\d+\/\d+)", re.I)
_OWNER_HEADER_RE = re.compile(r"^\d+\.\s+(?P<name>.+?)(?:\s+\(CF\s+(?P<cf>[A-Z0-9]{11,16})\*?\))?$", re.I)
_HISTORY_DATE_RE = re.compile(r"^dal\s+(?P<date>\d{2}/\d{2}/\d{4})$", re.I)
_ACT_DATE_RE = re.compile(r"(?P<date>\d{2}/\d{2}/\d{4})")
_RELATED_PARCEL_RE = re.compile(
    r"Foglio\s*:?\s*(?P<foglio>[^\s]+)\s+Particella\s*:?\s*(?P<particella>[^\s]+)", re.I
)


def extract_sister_pdf_text(path: str | Path) -> str:
    from pypdf import PdfReader

    return "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        return None


def _owner_name_parts(value: str) -> tuple[str | None, str | None, str | None]:
    name = re.sub(r"\s+", " ", value.strip())
    parts = name.split(" ")
    if len(parts) < 2:
        return name or None, None, None
    return name, parts[0], " ".join(parts[1:])


def _parse_owner_header(line: str) -> dict[str, Any] | None:
    line = re.sub(r"\s+\d+\.\s+(?=(?:Atto|Compravendita|Dichiarazione)\b).*$", "", line, flags=re.I)
    match = _OWNER_HEADER_RE.match(line)
    if not match:
        return None
    if match.group("name").casefold().startswith(("atto ", "compravendita ", "dichiarazione ")):
        return None
    display, surname, given = _owner_name_parts(match.group("name"))
    return {
        "denominazione": display,
        "cognome": surname,
        "nome": given,
        "codice_fiscale": match.group("cf").upper() if match.group("cf") else None,
    }


def _parse_current_owners(lines: list[str], start: int) -> list[dict[str, Any]]:
    owners: list[dict[str, Any]] = []
    pending: dict[str, Any] | None = None
    for line in lines[start:]:
        if line.casefold().startswith("dati identificativi") or line.casefold().startswith("storia degli"):
            break
        header = _parse_owner_header(line)
        if header:
            pending = header
            owners.append(pending)
            continue
        if pending is None:
            continue
        cf_match = re.search(r"\(CF\s+([A-Z0-9]{11,16})\*?\)", line, re.I)
        if cf_match:
            pending["codice_fiscale"] = cf_match.group(1).upper()
        right_match = re.search(r"Diritto di:\s*(.+?)(?:\s+per\s+(\d+\/\d+))?$", line, re.I)
        if right_match:
            pending["diritto"] = right_match.group(1).strip()
            pending["quota"] = right_match.group(2)
    return owners


def _parse_history_events(lines: list[str], start: int) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    events: list[dict[str, Any]] = []
    related: list[dict[str, str]] = []
    current: dict[str, Any] | None = None
    pending_owner: dict[str, Any] | None = None
    in_related = False
    for line in lines[start:]:
        if line.casefold().startswith("dati identificativi:") and "immobile attuale" in line.casefold():
            in_related = False
        if "sono stati inoltre variati/soppressi" in line.casefold():
            in_related = True
        if in_related:
            match = _RELATED_PARCEL_RE.search(line)
            if match and match.group("particella") not in {"/", "*"}:
                related.append({"foglio": match.group("foglio"), "particella": match.group("particella")})
        date_match = _HISTORY_DATE_RE.match(line)
        if date_match:
            current = {"from_date": _parse_date(date_match.group("date")), "owner": pending_owner or {}}
            pending_owner = None
            events.append(current)
            continue
        owner = _parse_owner_header(line)
        if owner:
            if current is None:
                pending_owner = owner
            elif current["from_date"] is None:
                pending_owner = owner
            else:
                current["owner"] = owner
            continue
        if current is None:
            if pending_owner is not None:
                cf_match = re.search(r"\(CF\s+([A-Z0-9]{11,16})\*?\)", line, re.I)
                if cf_match:
                    pending_owner["codice_fiscale"] = cf_match.group(1).upper()
            continue
        cf_match = re.search(r"\(CF\s+([A-Z0-9]{11,16})\*?\)", line, re.I)
        if cf_match:
            current["owner"]["codice_fiscale"] = cf_match.group(1).upper()
        right_match = re.search(r"Diritto di:\s*(.+?)(?:\s+per\s+(\d+\/\d+))?$", line, re.I)
        if right_match:
            current["owner"]["diritto"] = right_match.group(1).strip()
            current["owner"]["quota"] = right_match.group(2)
        if "atto amministrativo" in line.casefold() or "compravendita" in line.casefold():
            current["act"] = line.strip()
        act_date = _ACT_DATE_RE.search(line)
        if act_date and "act_date" not in current:
            current["act_date"] = _parse_date(act_date.group("date"))
    return events, related


def parse_sister_visura_text(text: str) -> dict[str, Any]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    joined = "\n".join(lines)
    comune_match = _COMUNE_RE.search(joined)
    parcel_match = _PARCEL_RE.search(joined)
    observed_match = re.search(r"Situazione degli atti informatizzati al\s+(\d{2}/\d{2}/\d{4})", joined, re.I)
    result: dict[str, Any] = {
        "parser_version": PARSER_VERSION,
        "source": "sister_pdf",
        "document_type": (
            "storica"
            if "visura storica" in joined.casefold()
            else "attuale"
            if "visura attuale" in joined.casefold()
            else "unknown"
        ),
        "observed_at": _parse_date(observed_match.group(1) if observed_match else None),
        "comune_nome": comune_match.group("nome").strip() if comune_match else None,
        "comune_codice": comune_match.group("codice").strip() if comune_match else None,
        "parcel": {
            "foglio": parcel_match.group("foglio").strip() if parcel_match else None,
            "particella": parcel_match.group("particella").strip() if parcel_match else None,
            "subalterno": parcel_match.group("sub").strip() if parcel_match and parcel_match.group("sub") else None,
        },
        "owners": [],
        "history_events": [],
        "related_parcels": [],
        "raw_lines": lines,
    }
    owners_started = False
    pending_owner: dict[str, Any] | None = None
    owner_start: int | None = None
    history_start: int | None = None
    for index, line in enumerate(lines):
        if line.casefold().startswith("intestati catastali") or line.casefold() in {"intestato", "intestati"}:
            owner_start = index + 1
        if line.casefold().startswith("storia degli intestati"):
            history_start = index + 1
        if line.casefold() in {"intestato", "intestati"} or line.startswith("INTESTAT"):
            owners_started = True
            continue
        if not owners_started:
            continue
        if line.casefold().startswith("situazione degli intestati"):
            break
        owner_match = _OWNER_RE.search(line)
        if owner_match:
            display, surname, given = _owner_name_parts(owner_match.group("name"))
            pending_owner = {
                "denominazione": display,
                "cognome": surname,
                "nome": given,
                "luogo_nascita": owner_match.group("place").strip(),
                "data_nascita": _parse_date(owner_match.group("date")),
            }
            remainder = line[owner_match.end() :]
            cf_match = re.search(r"\b([A-Z0-9]{11,16})\*?\b", remainder, re.I)
            if cf_match:
                pending_owner["codice_fiscale"] = cf_match.group(1).upper()
            right_match = _RIGHT_RE.search(remainder)
            if right_match:
                pending_owner["diritto"] = right_match.group("right").strip()
                pending_owner["quota"] = right_match.group("share")
            result["owners"].append(pending_owner)
            continue
        if pending_owner is not None and _CF_RE.match(line):
            pending_owner["codice_fiscale"] = line.rstrip("*").upper()
            continue
        if pending_owner is not None:
            right_match = _RIGHT_RE.match(line)
            if right_match:
                pending_owner["diritto"] = right_match.group("right").strip()
                pending_owner["quota"] = right_match.group("share")
    if owner_start is not None:
        structured_owners = _parse_current_owners(lines, owner_start)
        if structured_owners:
            result["owners"] = structured_owners
    if history_start is not None:
        result["history_events"], _ = _parse_history_events(lines, history_start)
        _, result["related_parcels"] = _parse_history_events(lines, 0)
    result["status"] = (
        "completed"
        if result["comune_codice"] and result["parcel"]["foglio"] and result["parcel"]["particella"]
        else "review_required"
    )
    return result


def parse_sister_visura_pdf(path: str | Path) -> dict[str, Any]:
    return parse_sister_visura_text(extract_sister_pdf_text(path))


def sister_pdf_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["PARSER_VERSION", "parse_sister_visura_pdf", "parse_sister_visura_text", "sister_pdf_sha256"]
