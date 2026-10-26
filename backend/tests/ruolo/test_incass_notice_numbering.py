from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import create_engine, inspect, select, text

from app.modules.ruolo.models import RuoloAvviso, RuoloTributiReminderBatchItem
from app.modules.ruolo.services import incass_notice_numbering as numbering
from app.modules.ruolo.services.notice_drafts import retain_draft_number
from app.modules.ruolo.tributi_policy_repository import upsert_calculation_policy

from .test_tributi_api import TestingSessionLocal, auth_headers, client, seed_avviso
from .test_tributi_api import setup_database as setup_database

TAX_CODE = "RSSMRA80A01H501Z"
OTHER_TAX_CODE = "BNCLGU80A01H501Y"


def _policy(year: int, **extra) -> dict:
    response = client.post(
        "/ruolo/tributi/calculation-policies",
        headers=auth_headers(),
        json={"name": f"Regola {year}", "year_from": year, "year_to": year, **extra},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _avviso(
    number: str, *, tax_code: str = TAX_CODE, anno: int = 2024, amount: float = 100.0
) -> str:
    avviso_id = seed_avviso(amount=amount, anno=anno, tax_code=tax_code)
    with TestingSessionLocal() as db:
        db.get(RuoloAvviso, UUID(avviso_id)).codice_cnc = number
        db.commit()
    return avviso_id


def _batch(monkeypatch: pytest.MonkeyPatch, years: list[int], tax_codes: list[str]):
    payloads: list[tuple[dict, Path]] = []

    def fake_pdf(payload: dict, *, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4 test")
        payloads.append((payload, output_path))

    monkeypatch.setattr(
        "app.modules.ruolo.tributi_repositories.generate_batch_reminder_pdf", fake_pdf
    )
    response = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=auth_headers(),
        json={
            "title": "inCASS",
            "codice_fiscale": tax_codes,
            "filters": {"years": years, "preview_only": True},
            "template_path": "/tmp/template.docx",
        },
    )
    return response, payloads


def test_rule_stores_the_notice_number_source_and_rejects_unknown_values() -> None:
    assert _policy(2024)["notice_number_source"] == "gaia"
    assert _policy(2021, notice_number_source="incass")["notice_number_source"] == "incass"
    with (
        TestingSessionLocal() as db,
        pytest.raises(ValueError, match="Numerazione avviso non valida"),
    ):
        upsert_calculation_policy(
            db,
            name="X",
            year_from=2030,
            year_to=2030,
            bonario_due_date=None,
            surcharge_rate_percent=0,
            surcharge_from=None,
            interest_rate_percent=0,
            interest_from=None,
            interest_start_mode="fixed_date",
            is_active=True,
            notes=None,
            updated_by=None,
            notice_number_source="altro",
        )


# 2021 is a STEP year by default in tests: 2024/2025 are GAIA-managed and not drafts.
def test_incass_rule_prints_one_notice_per_avviso_with_its_inCASS_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _policy(
        2024, notice_number_source="incass", bollettino_esercizio="2024", bollettino_causale="801"
    )
    _policy(2025, bollettino_causale="801", bollettino_esercizio="2626")
    _avviso("123456789012345", amount=100.0)
    _avviso("123456789054321", amount=50.0)
    seed_avviso(amount=30.0, anno=2025, tax_code=TAX_CODE)
    seed_avviso(amount=70.0, anno=2025, tax_code=OTHER_TAX_CODE, nominativo="BIANCHI LUIGI")

    response, payloads = _batch(monkeypatch, [2024, 2025], [TAX_CODE, OTHER_TAX_CODE])

    assert response.status_code == 200, response.text
    assert response.json()["items_total"] == 4
    by_number = {payload["notice_number"]: (payload, path) for payload, path in payloads}
    for number, amount in (("123456789012345", "100.00 EUR"), ("123456789054321", "50.00 EUR")):
        payload, path = by_number.pop(number)
        assert payload["bollettino_causale"] == number
        assert payload["bollettino_esercizio"] == "2024"
        assert payload["notice_progressive"] is None
        assert payload["years"] == [2024] and payload["saldo_amount"] == amount
        assert number in path.name
    rest = [payload for payload, _ in by_number.values()]
    assert {payload["codice_fiscale"] for payload in rest} == {TAX_CODE, OTHER_TAX_CODE}
    assert all(
        payload["notice_number"].startswith("1") and payload["bollettino_causale"] == "801"
        for payload in rest
    )
    assert all(payload["years"] == [2025] for payload in rest)
    with TestingSessionLocal() as db:
        items = db.scalars(select(RuoloTributiReminderBatchItem)).all()
        assert sum(item.notice_number_id is None for item in items) == 2


def test_incass_rule_refuses_an_avviso_without_its_inCASS_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _policy(2024, notice_number_source="incass")
    seed_avviso(amount=100.0, anno=2024, tax_code=TAX_CODE)

    response, payloads = _batch(monkeypatch, [2024], [TAX_CODE])

    assert response.status_code >= 400
    assert "Numero avviso inCASS mancante" in response.text
    assert payloads == []


def test_helpers_without_a_GAIA_reservation() -> None:
    assert numbering.incass_payload_overrides({}) == {}
    with TestingSessionLocal() as db:
        assert numbering.notice_reservation(db, None) is None
    item = SimpleNamespace(status="draft", notice_number_id=None)
    retain_draft_number(None, item)
    candidate = {"codice_fiscale": TAX_CODE, "years": [2021]}
    assert numbering.notice_filename(candidate) == f"{TAX_CODE}_avviso_sollecito_2021.pdf"
    candidate[numbering.INCASS_NOTICE_KEY] = "020217801062586"
    assert (
        numbering.notice_filename(candidate)
        == f"{TAX_CODE}_avviso_sollecito_2021_020217801062586.pdf"
    )


def test_migration_defaults_existing_rules_to_gaia_numbers_and_can_be_reverted() -> None:
    versions = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    migration = load_python_file(str(versions), "20261026_1600_tributi_notice_number_source.py")
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE ruolo_tributi_calculation_policies (id INTEGER PRIMARY KEY)")
        )
        connection.execute(text("INSERT INTO ruolo_tributi_calculation_policies VALUES (1)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        assert (
            connection.execute(
                text("SELECT notice_number_source FROM ruolo_tributi_calculation_policies")
            ).scalar()
            == "gaia"
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert [
            column["name"]
            for column in inspect(connection).get_columns("ruolo_tributi_calculation_policies")
        ] == ["id"]
    engine.dispose()
