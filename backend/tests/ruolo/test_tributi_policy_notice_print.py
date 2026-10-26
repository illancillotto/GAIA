from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import create_engine, inspect, text

from app.modules.ruolo import tributi_repositories as tributi_repo
from app.modules.ruolo.services import tributi_reminder_service as service

from .test_tributi_api import TestingSessionLocal, auth_headers, client
from .test_tributi_api import setup_database as setup_database


def _create_policy(year: int, **extra) -> dict:
    response = client.post(
        "/ruolo/tributi/calculation-policies",
        headers=auth_headers(),
        json={"name": f"Regola {year}", "year_from": year, "year_to": year, **extra},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_policy_stores_slip_choice_and_notice_payment_date() -> None:
    default = _create_policy(2024)
    assert default["print_bollettino"] is True and default["payment_due_date"] is None
    custom = _create_policy(
        2025,
        print_bollettino=False,
        payment_due_date="2026-11-30",
        bonario_due_date="2026-05-07",
        bollettino_causale="801",
    )
    assert custom["print_bollettino"] is False
    assert custom["payment_due_date"] == "2026-11-30"
    assert custom["bonario_due_date"] == "2026-05-07"

    with TestingSessionLocal() as db:
        assert tributi_repo._notice_print_policy_payload(db, [2025]) == {
            "print_bollettino": False,
            "bollettino_causale": "801",
            "bollettino_version": "v1",
            "due_date": "2026-11-30",
        }
        # One year without the slip removes it from the whole multi-year notice.
        assert (
            tributi_repo._notice_print_policy_payload(db, [2025, 2024])["print_bollettino"] is False
        )
        assert tributi_repo._notice_print_policy_payload(db, [2024, 2030]) == {
            "print_bollettino": True
        }
        assert tributi_repo._notice_print_policy_payload(db, [2030]) == {"print_bollettino": True}

    updated = client.put(
        f"/ruolo/tributi/calculation-policies/{custom['id']}",
        headers=auth_headers(),
        json={"name": "Regola 2025", "year_from": 2025, "year_to": 2025, "print_bollettino": True},
    )
    assert updated.status_code == 200
    assert updated.json()["print_bollettino"] is True and updated.json()["payment_due_date"] is None


def test_notice_payment_date_drives_amount_box_and_slip_due_date() -> None:
    payload = {"due_date": "2026-11-30", "generated_at": "2026-10-23T08:00:00+00:00"}
    assert service._gaia_bollettino_due_date(payload) == "30/11/2026"


def test_pdf_omits_the_slip_page_when_the_rule_excludes_it(tmp_path, monkeypatch) -> None:
    rendered: list[tuple[str, str]] = []

    def fake_render(html_text, *, chromium_binary, working_dir, stem):
        rendered.append((stem, html_text))
        return Path(working_dir) / f"{stem}.pdf"

    merged: list[list[str]] = []
    monkeypatch.setattr(service, "_find_chromium_binary", lambda: "/usr/bin/chromium")
    monkeypatch.setattr(service, "_chromium_accessible_temp_parent", lambda _binary: None)
    monkeypatch.setattr(service, "_render_gaia_html_to_pdf", fake_render)
    monkeypatch.setattr(
        service, "_gaia_proposal_html", lambda payload, **flags: repr(sorted(flags))
    )
    monkeypatch.setattr(
        service,
        "_merge_pdf_files",
        lambda paths, *, output_path: merged.append([Path(path).stem for path in paths]),
    )

    output = tmp_path / "avviso.pdf"
    service._generate_gaia_proposal_pdf({"print_bollettino": False}, output_path=output)
    service._generate_gaia_proposal_pdf({}, output_path=output)

    assert merged == [
        ["avviso_main", "avviso_partitario"],
        ["avviso_main", "avviso_partitario", "avviso_bollettino"],
    ]
    assert rendered[-1] == ("avviso_bollettino", "['include_main', 'include_partitario']")


def test_policy_notice_print_migration_keeps_existing_rules_with_slip() -> None:
    versions = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    revision = load_python_file(str(versions), "20261023_0900_tributi_policy_notice_print.py")
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE ruolo_tributi_calculation_policies (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
        )
        connection.execute(
            text("INSERT INTO ruolo_tributi_calculation_policies VALUES (1, 'Esistente')")
        )
        with Operations.context(MigrationContext.configure(connection)):
            revision.upgrade()
        assert connection.execute(
            text(
                "SELECT print_bollettino, payment_due_date FROM ruolo_tributi_calculation_policies"
            )
        ).one() == (1, None)
        with Operations.context(MigrationContext.configure(connection)):
            revision.downgrade()
        assert {
            column["name"]
            for column in inspect(connection).get_columns("ruolo_tributi_calculation_policies")
        } == {"id", "name"}
    engine.dispose()
