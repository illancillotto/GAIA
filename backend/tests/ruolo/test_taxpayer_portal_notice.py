"""Generation API snapshots the actual recipient's access, including reassigned payers."""

from pathlib import Path

import pytest

from app.modules.ruolo.services.taxpayer_portal_access import printable_portal_access
from app.modules.ruolo.services.taxpayer_portal_import import PortalAccessRow, import_access_rows

from .test_payer_assignments import HEIR, OTHER_OWNER, OWNER, _person, _put
from .test_tributi_api import TestingSessionLocal, auth_headers, client, seed_avviso
from .test_tributi_api import setup_database as setup_database


@pytest.mark.parametrize("ambiguous_payer", [False, True])
def test_generated_snapshots_use_payer_account_or_fallback_for_missing_or_ambiguous_cf(
    monkeypatch, ambiguous_payer
):
    _person()
    client.post(
        "/ruolo/tributi/calculation-policies",
        headers=auth_headers(),
        json={"name": "Regola 2024", "year_from": 2024, "year_to": 2024},
    )
    inherited = seed_avviso(tax_code=OWNER)
    seed_avviso(tax_code=OWNER)
    seed_avviso(tax_code=OTHER_OWNER)
    assert _put(inherited).status_code == 200
    with TestingSessionLocal() as db:
        import_access_rows(
            db,
            [
                PortalAccessRow(OWNER, "0000001", "0011111"),
                PortalAccessRow(HEIR, "0000002", "0022222"),
                *([PortalAccessRow(HEIR, "0000003", "0033333")] if ambiguous_payer else []),
            ],
            "a" * 64,
        )
        db.commit()
    payloads = []

    def fake_pdf(payload, *, output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4 test")
        payloads.append(payload)

    monkeypatch.setattr(
        "app.modules.ruolo.tributi_repositories.generate_batch_reminder_pdf", fake_pdf
    )
    response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=auth_headers(),
        json={
            "title": "Accessi portale",
            "codice_fiscale": [OWNER, OTHER_OWNER],
            "filters": {"years": [2024], "preview_only": True},
            "template_path": "__gaia_proposal__",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["items_total"] == 3
    by_recipient = {payload["codice_fiscale"]: payload for payload in payloads}
    assert printable_portal_access(by_recipient[OWNER]) == [("0000001", "0011111")]
    assert printable_portal_access(by_recipient[HEIR]) == (
        [] if ambiguous_payer else [("0000002", "0022222")]
    )
    assert printable_portal_access(by_recipient[OTHER_OWNER]) == []
    assert all(
        "0011111" not in str(payload) and "0022222" not in str(payload) for payload in payloads
    )


@pytest.mark.parametrize("tax_codes", [[], [OWNER]])
def test_no_candidates_means_no_portal_snapshot_or_generation(tax_codes):
    from app.modules.ruolo.services.notice_candidates import batch_candidates

    with TestingSessionLocal() as db:
        assert batch_candidates(db, [], tax_codes) == []
