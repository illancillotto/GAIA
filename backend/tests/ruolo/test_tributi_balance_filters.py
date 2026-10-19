from datetime import UTC, datetime

import pytest

from .test_tributi_api import auth_headers, client, seed_avviso
from .test_tributi_api import setup_database as setup_database


@pytest.mark.parametrize(
    ("manager_key", "year", "other_year", "outside_year"),
    [
        ("agenzia_entrate", 2017, 2016, 2018),
        ("step", 2018, 2021, 2022),
        ("gaia", 2022, 2024, 2021),
    ],
)
def test_outstanding_filters_combine_manager_year_and_effective_balance(
    manager_key: str, year: int, other_year: int, outside_year: int
) -> None:
    headers = auth_headers()
    unpaid = seed_avviso(anno=year)
    partial = seed_avviso(anno=year)
    paid = seed_avviso(anno=year)
    overpaid = seed_avviso(anno=year)
    review = seed_avviso(anno=year, amount=None)
    other = seed_avviso(anno=other_year)
    seed_avviso(anno=outside_year)
    for avviso_id, amount in [(partial, 40), (paid, 100), (overpaid, 120)]:
        response = client.post(
            f"/ruolo/tributi/avvisi/{avviso_id}/payments",
            headers=headers,
            json={"amount": amount, "paid_at": datetime.now(UTC).isoformat()},
        )
        assert response.status_code == 200

    params = {"manager_key": manager_key, "anno": year, "open_only": "true"}
    response = client.get("/ruolo/tributi/avvisi", params=params, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert {item["id"]: item["payment_status"] for item in payload["items"]} == {
        unpaid: "unpaid",
        partial: "partial",
        review: "to_review",
    }
    assert next(item["saldo_amount"] for item in payload["items"] if item["id"] == partial) == 60
    summary = client.get("/ruolo/tributi/summary", params=params, headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total_count"] == 3
    assert summary.json()["total_amount"] == 200

    params.pop("anno")
    period = client.get("/ruolo/tributi/avvisi", params=params, headers=headers)
    assert period.status_code == 200
    assert {item["id"] for item in period.json()["items"]} == {unpaid, partial, review, other}
    period_summary = client.get("/ruolo/tributi/summary", params=params, headers=headers)
    assert period_summary.status_code == 200
    assert period_summary.json()["total_count"] == 4

    params.update({"anno": year, "open_only": "false"})
    history = client.get("/ruolo/tributi/avvisi", params=params, headers=headers)
    assert history.status_code == 200
    assert {item["id"] for item in history.json()["items"]} == {
        unpaid,
        partial,
        paid,
        overpaid,
        review,
    }
