from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

from pypdf import PdfReader


def extract_pdf_text(path: str | Path) -> str:
    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def parse_historical_visura_pdf(path: str | Path) -> dict[str, object]:
    return parse_historical_visura_text(extract_pdf_text(path))


def parse_historical_visura_text(text: str) -> dict[str, object]:
    normalized = _normalize_text(text)
    upper = normalized.upper()
    requested = _parse_requested_parcel(normalized)
    suppression = _parse_suppression(normalized)
    originated = _parse_originated_or_varied_parcels(normalized)
    first_variation = _parse_first_variation(normalized)
    events = _parse_events(normalized)

    classification = "current"
    if suppression["is_suppressed"]:
        classification = "suppressed"
    elif "NON RISULTANO DATI" in upper or "NESSUN IMMOBILE" in upper:
        classification = "not_found"
    elif not events and not requested:
        classification = "unknown"

    return {
        "source": "ade_historical_synthetic_pdf",
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "classification": classification,
        "requested": requested,
        "suppression": suppression,
        "originated_or_varied_parcels": originated,
        "first_variation": first_variation,
        "events": events,
        "raw_text_excerpt": normalized[:4000],
    }


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\xa0", " ")).strip()


def _parse_requested_parcel(text: str) -> dict[str, str | None]:
    comune_match = re.search(
        r"Comune di\s+(.+?)\s+\((?:Codice:)?([A-Z0-9]+)\)(?:\s+\([A-Z]{2}\))?",
        text,
        re.IGNORECASE,
    )
    sezione_match = re.search(r"Sezione\s+(.+?)\s+\(Provincia", text, re.IGNORECASE)
    parcel_match = re.search(
        r"Foglio[: ]+\s*([A-Z0-9]+)\s+Particella[: ]+\s*([A-Z0-9]+)(?:\s+Sub(?:alterno)?[: ]+\s*([A-Z0-9]+))?",
        text,
        re.IGNORECASE,
    )
    return {
        "comune": comune_match.group(1).strip() if comune_match else None,
        "codice": comune_match.group(2).strip() if comune_match else None,
        "sezione": sezione_match.group(1).strip() if sezione_match else None,
        "foglio": parcel_match.group(1).strip() if parcel_match else None,
        "particella": parcel_match.group(2).strip() if parcel_match else None,
        "subalterno": parcel_match.group(3).strip() if parcel_match and parcel_match.group(3) else None,
    }


def _parse_suppression(text: str) -> dict[str, object]:
    match = re.search(
        r"(?:Numero di mappa soppresso dal|soppressione del)\s+(\d{2}/\d{2}/\d{4})",
        text,
        re.IGNORECASE,
    )
    act_matches = list(re.finditer(
        r"(FRAZIONAMENTO|VARIAZIONE|TIPO MAPPALE|FUSIONE|DIVISIONE).{0,180}?\(n\.\s*([^)]+)\)",
        text,
        re.IGNORECASE | re.DOTALL,
    ))
    act_match = _best_act_match(act_matches)
    act_type = act_match.group(1).upper() if act_match else None
    if act_type == "VARIAZIONE" and re.search(r"TIPO\s+MAPPALE", act_match.group(0), re.IGNORECASE):
        act_type = "TIPO MAPPALE"
    return {
        "is_suppressed": match is not None or " SOPPRESSO " in f" {text.upper()} ",
        "suppressed_from": match.group(1) if match else None,
        "act_type": act_type,
        "act_reference": act_match.group(2).strip() if act_match else None,
    }


def _best_act_match(matches: list[re.Match[str]]) -> re.Match[str] | None:
    if not matches:
        return None
    for match in reversed(matches):
        if match.group(1).upper() != "VARIAZIONE":
            return match
    return matches[-1]


def _parse_first_variation(text: str) -> dict[str, list[dict[str, str | None]]]:
    return {
        "suppressed_parcels": _parse_parcels_after(text, "Nella variazione sono stati soppressi i seguenti immobili"),
        "varied_parcels": _parse_parcels_after(text, "Sono stati inoltre variati i seguenti immobili"),
    }


def _parse_events(text: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    pattern = re.compile(
        r"Situazione dell'unità immobiliare\s+(?P<label>.*?)(?=\n| N\.)",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(text))
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else min(len(text), start + 2500)
        block = text[start:end]
        derivation = re.search(
            r"(FRAZIONAMENTO|VARIAZIONE D'UFFICIO|VARIAZIONE|IMPIANTO MECCANOGRAFICO|TIPO MAPPALE|FUSIONE|DIVISIONE).{0,240}?(?:\n|$)",
            block,
            re.IGNORECASE | re.DOTALL,
        )
        events.append(
            {
                "label": re.sub(r"\s+", " ", match.group("label")).strip(),
                "date": _first_date(match.group("label")) or _first_date(block),
                "derivation": re.sub(r"\s+", " ", derivation.group(0)).strip() if derivation else None,
                "suppressed_parcels": _parse_parcels_after(block, "Nella variazione sono stati soppressi i seguenti immobili"),
                "varied_parcels": _parse_parcels_after(block, "Sono stati inoltre variati i seguenti immobili"),
            }
        )
    return events


def _parse_originated_or_varied_parcels(text: str) -> list[dict[str, str | None]]:
    markers = [
        "La soppressione ha originato e/o variato i seguenti immobili",
        "costituito i seguenti immobili",
        "costituiti i seguenti immobili",
        "costituite le seguenti particelle",
        "costituito le seguenti particelle",
    ]
    parcels: list[dict[str, str | None]] = []
    seen: set[tuple[str | None, str | None, str | None]] = set()
    for marker in markers:
        for parcel in _parse_parcels_after(text, marker):
            key = (parcel.get("foglio"), parcel.get("particella"), parcel.get("subalterno"))
            if key in seen:
                continue
            seen.add(key)
            parcels.append(parcel)
    return parcels


def _parse_parcels_after(text: str, marker: str) -> list[dict[str, str | None]]:
    marker_index = text.lower().find(marker.lower())
    if marker_index < 0:
        return []
    window = text[marker_index + len(marker): marker_index + len(marker) + 500]
    stop = re.search(
        r"\n\s*\n|Situazione|L'intestazione|DATI DERIVANTI|Sono stati inoltre variati|soppresso i seguenti|soppressi i seguenti",
        window,
        re.IGNORECASE,
    )
    if stop:
        window = window[: stop.start()]
    parcels: list[dict[str, str | None]] = []
    for match in re.finditer(
        r"Foglio[: ]\s*([A-Z0-9]+)\s+Particella[: ]\s*([A-Z0-9]+)(?:\s+Sub[: ]\s*([A-Z0-9]+))?",
        window,
        re.IGNORECASE,
    ):
        parcels.append(
            {
                "foglio": match.group(1).strip(),
                "particella": match.group(2).strip(),
                "subalterno": match.group(3).strip() if match.group(3) else None,
            }
        )
    return parcels


def _first_date(text: str) -> str | None:
    match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", text)
    return match.group(1) if match else None
