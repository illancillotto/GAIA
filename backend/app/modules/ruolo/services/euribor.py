from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO
from urllib.parse import urlencode
from urllib.request import urlopen


ECB_EURIBOR_6M_DATA_URL = "https://data-api.ecb.europa.eu/service/data/FM/M.U2.EUR.RT.MM.EURIBOR6MD_.HSTA"
ECB_EURIBOR_6M_VERIFY_URL = "https://data.ecb.europa.eu/data/datasets/FM/FM.M.U2.EUR.RT.MM.EURIBOR6MD_.HSTA"


@dataclass(frozen=True)
class EuriborRate:
    year: int
    rate_percent: Decimal
    reference_period: str
    source_url: str
    verification_url: str
    fetched_at: datetime
    observations_count: int


def ecb_euribor_6m_csv_url(*, year: int) -> str:
    query = urlencode({"format": "csvdata", "startPeriod": f"{year}-01", "endPeriod": f"{year}-12"})
    return f"{ECB_EURIBOR_6M_DATA_URL}?{query}"


def fetch_euribor_6m_average(*, year: int) -> EuriborRate:
    if year < 1994 or year > datetime.now(timezone.utc).year:
        raise ValueError("Anno Euribor non supportato")

    source_url = ecb_euribor_6m_csv_url(year=year)
    with urlopen(source_url, timeout=20) as response:
        payload = response.read().decode("utf-8-sig")

    observations = _parse_ecb_euribor_csv(payload, year=year)
    if not observations:
        raise ValueError(f"Nessun dato Euribor 6 mesi disponibile per {year}")

    average = (sum(observations, Decimal("0")) / Decimal(len(observations))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return EuriborRate(
        year=year,
        rate_percent=average,
        reference_period=f"{year}",
        source_url=source_url,
        verification_url=ECB_EURIBOR_6M_VERIFY_URL,
        fetched_at=datetime.now(timezone.utc),
        observations_count=len(observations),
    )


def _parse_ecb_euribor_csv(payload: str, *, year: int) -> list[Decimal]:
    reader = csv.DictReader(StringIO(payload))
    observations: list[Decimal] = []
    for row in reader:
        period = (row.get("TIME_PERIOD") or "").strip()
        value = (row.get("OBS_VALUE") or "").strip()
        if not period.startswith(f"{year}-") or not value:
            continue
        observations.append(Decimal(value))
    return observations
