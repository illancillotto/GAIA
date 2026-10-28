"""Saved notification terms, old-rule compatibility and the printed legal/payment blocks."""

from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import create_engine, inspect, select, text

from app.modules.ruolo.models import RuoloTributiReminderBatchItem
from app.modules.ruolo.services import notice_payment_deadline as deadline
from app.modules.ruolo.services import tributi_reminder_service as renderer
from app.modules.ruolo.tributi_policy_repository import notice_print_policy_payload
from app.services.elaborazioni_credentials import get_credential_fernet

from .test_notice_presentation import _payload
from .test_tributi_api import TestingSessionLocal, auth_headers, client, seed_avviso
from .test_tributi_api import setup_database as setup_database


def _policy(year, **options):
    response = client.post(
        "/ruolo/tributi/calculation-policies",
        headers=auth_headers(),
        json={"name": f"Regola {year}", "year_from": year, "year_to": year, **options},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_rule_defaults_to_fixed_date_and_preserves_slip_date_alongside_notification_mode():
    old = _policy(2024, payment_due_date="2026-11-30")
    assert old["payment_deadline_mode"] == "fixed_date"
    assert old["payment_due_date"] == "2026-11-30"
    updated = client.put(
        f"/ruolo/tributi/calculation-policies/{old['id']}",
        headers=auth_headers(),
        json={
            "name": "Regola 2024",
            "year_from": 2024,
            "year_to": 2024,
            "payment_deadline_mode": "notification_60_days",
            "payment_due_date": "2026-11-30",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["payment_deadline_mode"] == "notification_60_days"
    assert updated.json()["payment_due_date"] == "2026-11-30"
    listed = client.get("/ruolo/tributi/calculation-policies", headers=auth_headers()).json()[
        "items"
    ]
    assert listed[0]["payment_deadline_mode"] == "notification_60_days"
    with TestingSessionLocal() as db:
        saved = notice_print_policy_payload(db, [2024])
        assert saved["payment_deadline_mode"] == "notification_60_days"
        assert saved["due_date"] == "2026-11-30"
    _policy(2025, payment_due_date="2026-12-10")
    with TestingSessionLocal() as db:
        multi = notice_print_policy_payload(db, [2024, 2025])
        assert multi["due_date"] == "2026-12-10" and "payment_deadline_mode" not in multi
    assert saved["payment_deadline_mode"] == "notification_60_days"


def test_invalid_mode_is_rejected_by_api_and_domain_validation():
    response = client.post(
        "/ruolo/tributi/calculation-policies",
        headers=auth_headers(),
        json={"name": "Invalid", "payment_deadline_mode": "60"},
    )
    assert response.status_code == 422
    with pytest.raises(ValueError, match="Modalità scadenza pagamento non valida"):
        deadline.apply_payment_deadline(
            SimpleNamespace(), SimpleNamespace(payment_deadline_mode="60")
        )


def test_notification_slip_requires_a_fixed_date_but_notice_without_slip_does_not():
    response = client.post(
        "/ruolo/tributi/calculation-policies",
        headers=auth_headers(),
        json={"name": "Data obbligatoria", "payment_deadline_mode": "notification_60_days"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == deadline.MISSING_BOLLETTINO_DATE
    saved = _policy(2021, payment_deadline_mode="notification_60_days", print_bollettino=False)
    assert saved["payment_due_date"] is None
    with TestingSessionLocal() as db:
        snapshot = notice_print_policy_payload(db, [2021])
        assert snapshot["print_bollettino"] is False
        assert snapshot["payment_deadline_mode"] == "notification_60_days"
        assert "due_date" not in snapshot
        from app.modules.ruolo.tributi_policy_model import RuoloTributiCalculationPolicy

        old = db.get(RuoloTributiCalculationPolicy, UUID(saved["id"]))
        old.print_bollettino = True
        db.flush()
        with pytest.raises(ValueError, match="Regole ruolo"):
            notice_print_policy_payload(db, [2021])


@pytest.mark.parametrize("version", ["v1", "v2"])
@pytest.mark.parametrize("key,date", [("due_date", "2026-11-30"), ("deadline", "30.11.2026")])
def test_both_slip_coupons_print_the_calendar_date_and_single_installment(version, key, date):
    payload = {
        **_payload([2021]),
        "payment_deadline_mode": "notification_60_days",
        "bollettino_version": version,
    }
    payload.pop("due_date")
    payload[key] = date
    rendered = renderer._gaia_proposal_html(payload, include_main=False, include_partitario=False)
    assert rendered.count("30/11/2026 - Rata Unica") == 2
    assert "60 giorni dalla data di notifica" not in rendered
    assert renderer._batch_template_field_values(payload)["Scadenza"] == deadline.NOTIFICATION_TERM
    payload.pop(key)
    with pytest.raises(ValueError, match="Regole ruolo"):
        renderer._gaia_proposal_html(payload, include_main=False, include_partitario=False)
    # Historical snapshots can still render their notice when no slip is requested.
    assert "PER CONSULTARE" in renderer._gaia_proposal_html(payload, include_bollettino=False)


def test_batch_generation_snapshots_relative_term_and_the_newest_rule_wins(monkeypatch):
    _policy(2024, payment_deadline_mode="notification_60_days", payment_due_date="2026-11-30")
    latest = _policy(
        2025, payment_deadline_mode="notification_60_days", payment_due_date="2026-12-10"
    )
    seed_avviso(anno=2024)
    seed_avviso(anno=2025)
    payloads = []

    def fake_pdf(payload, *, output_path):
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
            "title": "Termine di notifica",
            "codice_fiscale": ["RSSMRA80A01H501Z"],
            "filters": {"years": [2024, 2025], "preview_only": True},
            "template_path": "__gaia_proposal__",
        },
    )
    assert response.status_code == 200, response.text
    assert len(payloads) == 1
    assert payloads[0]["payment_deadline_mode"] == "notification_60_days"
    assert payloads[0]["due_date"] == "2026-12-10"
    updated = client.put(
        f"/ruolo/tributi/calculation-policies/{latest['id']}",
        headers=auth_headers(),
        json={
            "name": "Regola 2025",
            "year_from": 2025,
            "year_to": 2025,
            "payment_deadline_mode": "fixed_date",
            "payment_due_date": "2026-12-10",
        },
    )
    assert updated.status_code == 200, updated.text
    with TestingSessionLocal() as db:
        snapshot = db.scalars(select(RuoloTributiReminderBatchItem)).one().payload_json
        assert snapshot["payment_deadline_mode"] == "notification_60_days"
        assert snapshot["due_date"] == "2026-12-10"
        assert notice_print_policy_payload(db, [2024, 2025])["due_date"] == "2026-12-10"


def test_notification_term_overrides_old_dates_and_does_not_call_fixed_date_formatter():
    payload = {
        "payment_deadline_mode": "notification_60_days",
        "due_date": "2026-11-30",
        "deadline": "2026-12-01",
        "generated_at": "2026-10-27T10:00:00Z",
    }

    def unavailable(_payload):
        raise AssertionError("A notification term cannot be derived from the print date")

    assert deadline.payment_deadline_text(payload, unavailable) == deadline.NOTIFICATION_TERM
    fields = renderer._batch_template_field_values({**_payload([2021]), **payload})
    assert fields["Scadenza"] == deadline.NOTIFICATION_TERM
    assert fields["Pagamento_entro"] == "entro 60 giorni dalla data di notifica"
    fixed = renderer._batch_template_field_values({**_payload([2021]), "due_date": "2026-11-30"})
    assert fixed["Pagamento_entro"] == "entro il 30/11/2026"
    assert deadline.payment_deadline_html({}) == ""
    assert deadline.notice_enforcement_html({}) == ""


def test_notification_blocks_are_ordered_and_amount_is_only_in_payment_summary():
    payload = {**_payload([2021]), "payment_deadline_mode": "notification_60_days"}
    front = (
        renderer._gaia_proposal_html(payload, include_bollettino=False)
        .split('<section class="page front">')[1]
        .split("</section>")[0]
    )
    assert "Pagamento entro 60 giorni dalla data di notifica" in front
    term_block = front.split('<div class="payment-deadline">')[1].split("</div>")[0]
    assert "221,55" not in term_block and "Totale da pagare" not in term_block
    assert '<div class="euro">€. 221,55</div>' in front
    assert "La scadenza che cade nelle giornate di sabato o festive" in front
    assert "In caso di pagamento oltre i 60 giorni" in front
    assert front.index('class="payment-deadline"') < front.index('class="portal-access"')
    assert (
        front.index('class="portal-access"')
        < front.index("Per maggiori chiarimenti")
        < front.index("È possibile consultare il sito")
        < front.index('class="notice-enforcement"')
        < front.index('class="notice-services"')
    )
    assert "Il presente avviso ha valore di intimazione" in front
    assert (
        "il Consorzio di Bonifica dell'Oristanese tramite l'agente di riscossione attiverà" in front
    )
    assert '<svg class="attention-icon"' in front
    assert '<div class="attention-icon"' not in front
    assert "Agente della riscossione" not in front
    assert "entro il 30/11/2026 e comunque entro 60 giorni dalla data di notifica" in front


@pytest.mark.parametrize("mode", ["fixed_date", "notification_60_days"])
@pytest.mark.parametrize(
    "dates,expected",
    [
        ({"due_date": "2026-11-30"}, "entro il 30/11/2026 e comunque entro "),
        ({"deadline": "30.11.2026"}, "entro il 30/11/2026 e comunque entro "),
        ({}, "entro "),
    ],
)
def test_2021_amount_box_combines_only_an_explicit_date_with_notification_term(
    mode, dates, expected
):
    payload = {**_payload([2021]), "payment_deadline_mode": mode}
    payload.pop("due_date")
    payload.update(dates)
    fields = renderer._batch_template_field_values(payload)
    phrase = expected + deadline.NOTIFICATION_TERM
    assert (
        deadline.front_payment_due_phrase(payload, [2021], renderer._gaia_bollettino_due_date)
        == phrase
    )
    front = (
        renderer._gaia_proposal_html(payload, include_bollettino=False)
        .split('<div class="amount">')[1]
        .split('<div class="instructions">')[0]
    )
    assert phrase in front
    # The shared DOCX fields retain the relative term independently of the slip date.
    if mode == "notification_60_days":
        assert fields["Scadenza"] == deadline.NOTIFICATION_TERM
    assert (
        deadline.front_payment_due_phrase(
            {"payment_deadline_mode": "fixed_date", "due_date": "2026-11-30"},
            [2024, 2025],
            renderer._gaia_bollettino_due_date,
        )
        == "entro il 30/11/2026"
    )


@pytest.mark.parametrize(
    "years,access_count", [([2021], 1), ([2024, 2025], 0), ([2021, 2022, 2023, 2024, 2025], 1)]
)
def test_notification_notice_keeps_payment_instructions_and_attention_block_on_page_one(
    years, access_count, tmp_path
):
    import pymupdf
    import zxingcpp
    from PIL import Image

    payload = {**_payload(years), "payment_deadline_mode": "notification_60_days"}
    payload["taxpayer_portal_access"] = [
        {
            "account_code": f"000000{index}",
            "pin_encrypted": get_credential_fernet().encrypt(f"001234{index}".encode()).decode(),
        }
        for index in range(access_count)
    ]
    path = tmp_path / "notification.pdf"
    renderer.generate_batch_reminder_pdf(payload, output_path=path)
    with pymupdf.open(path) as document:
        assert len(document) == 4
        first = document[0]
        assert "Comunicazioni per il Contribuente" in document[1].get_text()
        normalized = " ".join(first.get_text().split())
        assert "Pagamento entro 60 giorni dalla data di notifica" in normalized
        assert "Totale da pagare" not in normalized
        assert "€. 221,55" in normalized
        assert "Il presente avviso ha valore di intimazione" in normalized
        assert ("30/11/2026" in normalized) == (years == [2021])
        term_end = first.search_for("In caso di pagamento oltre i 60 giorni")[0].y1
        information = first.search_for("Per maggiori chiarimenti")[0]
        assert normalized.index("Per maggiori chiarimenti") < normalized.index(
            "È possibile consultare"
        )
        information_end = first.search_for("istituzionale dell\u2019Ente.")[-1].y1
        portal = first.search_for("PER CONSULTARE LA PROPRIA POSIZIONE")[0]
        access_text = (
            f"001234{access_count - 1}" if access_count else "Per ottenere i dati di accesso"
        )
        access_end = first.search_for(access_text)[0].y1
        attention = first.search_for("Il presente avviso")[0]
        gaps = [portal.y0 - term_end, information.y0 - access_end, attention.y0 - information_end]
        assert min(gaps) > 0
        # The available space is shared between blocks, rather than left above the footer.
        assert max(gaps) - min(gaps) < 12
        qr = next(
            item for item in first.get_image_info() if item["bbox"][1] > first.rect.height / 2
        )
        raster = first.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=pymupdf.Rect(qr["bbox"]))
        image = Image.frombytes("RGB", (raster.width, raster.height), raster.samples)
        assert [code.text for code in zxingcpp.read_barcodes(image)] == [
            "https://whatsapp.com/channel/0029Vb9tZLzDJ6H3keAt9h24"
        ]
        assert first.search_for("Il presente avviso")[0].y1 < qr["bbox"][1]
        assert max(word[3] for word in first.get_text("words")) < first.rect.height
        slip = " ".join(document[-1].get_text().split())
        assert slip.count("30/11/2026 - Rata Unica") == 2
        assert "60 giorni dalla data di notifica" not in slip


def test_notification_deadline_migration_preserves_old_rules_and_roundtrips():
    revision = load_python_file(
        str(Path(__file__).parents[2] / "alembic" / "versions"),
        "20261027_1300_notice_notification_deadline.py",
    )
    engine = create_engine("sqlite://")
    with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
        connection.execute(
            text(
                "CREATE TABLE ruolo_tributi_calculation_policies (id integer PRIMARY KEY, payment_due_date DATE)"
            )
        )
        connection.execute(
            text("INSERT INTO ruolo_tributi_calculation_policies VALUES (1, '2026-11-30')")
        )
        revision.upgrade()
        assert connection.execute(
            text(
                "SELECT payment_deadline_mode, payment_due_date FROM ruolo_tributi_calculation_policies"
            )
        ).one() == ("fixed_date", "2026-11-30")
        revision.downgrade()
        assert {
            c["name"] for c in inspect(connection).get_columns("ruolo_tributi_calculation_policies")
        } == {"id", "payment_due_date"}
    engine.dispose()
