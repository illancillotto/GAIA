from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from pypdf import PdfReader, PdfWriter
from sqlalchemy import create_engine, inspect, text

from app.modules.ruolo import tributi_policy_repository as policies
from app.modules.ruolo.services import bollettino_v2 as layout
from app.modules.ruolo.services import notice_html_pdf as printer
from app.modules.ruolo.services import tributi_reminder_service as service
from app.modules.ruolo.tributi_policy_schemas import RuoloTributiCalculationPolicyUpsertRequest

from .test_tributi_api import TestingSessionLocal, auth_headers, client
from .test_tributi_api import setup_database as setup_database


@pytest.fixture
def payload() -> dict:
    return {
        "display_name": "ROSSI MARIO",
        "codice_fiscale": "RSSMRA80A01H501Z",
        "notice_number": "12026242500001",
        "notice_emission_year": 2026,
        "years": [2024, 2025],
        "saldo_amount": "210.00 EUR",
        "due_date": "2026-11-30",
        "bollettino_version": "v2",
        "bollettino_causale": "025",
        "template_path": service.GAIA_PROPOSAL_TEMPLATE_KEY,
        "avvisi": [{"anno_tributario": 2025, "residenza_raw": "VIA ROMA 1 09170 ORISTANO (OR)"}],
    }


def test_policy_persists_version_and_uses_the_latest_annuality() -> None:
    headers = auth_headers()
    first = client.post(
        "/ruolo/tributi/calculation-policies",
        headers=headers,
        json={"name": "2024", "year_from": 2024, "year_to": 2024, "bollettino_version": "v2"},
    )
    assert first.status_code == 200 and first.json()["bollettino_version"] == "v2"
    latest = client.post(
        "/ruolo/tributi/calculation-policies",
        headers=headers,
        json={"name": "2025", "year_from": 2025, "year_to": 2025},
    )
    assert latest.status_code == 200 and latest.json()["bollettino_version"] == "v1"
    with TestingSessionLocal() as db:
        assert policies.notice_print_policy_payload(db, [2024])["bollettino_version"] == "v2"
        assert policies.notice_print_policy_payload(db, [2024, 2025])["bollettino_version"] == "v1"
    updated = client.put(
        f"/ruolo/tributi/calculation-policies/{latest.json()['id']}",
        headers=headers,
        json={"name": "2025", "year_from": 2025, "year_to": 2025, "bollettino_version": "v2"},
    )
    assert updated.status_code == 200 and updated.json()["bollettino_version"] == "v2"
    listed = client.get("/ruolo/tributi/calculation-policies", headers=headers).json()["items"]
    assert [item["bollettino_version"] for item in listed] == ["v2", "v2"]
    with TestingSessionLocal() as db:
        assert policies.notice_print_policy_payload(db, [2024, 2025])["bollettino_version"] == "v2"


def test_unknown_layout_is_rejected_by_api_and_repository() -> None:
    response = client.post(
        "/ruolo/tributi/calculation-policies",
        headers=auth_headers(),
        json={"name": "Unknown", "bollettino_version": "v3"},
    )
    assert response.status_code == 422
    with TestingSessionLocal() as db, pytest.raises(ValueError, match="Versione bollettino"):
        policies.upsert_calculation_policy(
            db,
            **{
                **RuoloTributiCalculationPolicyUpsertRequest(name="Unknown").model_dump(),
                "bollettino_version": "v3",
            },
            updated_by=None,
        )


def test_v2_prints_live_fields_and_preserves_the_original_static_artwork(payload) -> None:
    fields = service._batch_template_field_values(payload)
    rendered = service._gaia_proposal_html(payload, include_main=False, include_partitario=False)
    assert "@page bollettino { size: 595pt 841pt; margin: 0; }" in rendered
    assert 'class="poste-v2"' in rendered
    assert "ROSSI MARIO" in rendered and "VIA ROMA 1" in rendered
    assert "09170 ORISTANO OR" in rendered
    assert "Scadenza:30/11/2026 - Rata Unica" in rendered
    assert "Esercizio: 2626 Causale: 025" in rendered
    assert "causale: A 12026242500001 CF RSSMRA80A01H501Z" in rendered
    assert "18012026242500001985120010072148261000000221553896" in rendered
    assert fields["Complessivo"] == "221,55"
    assert 'textLength="121.446' in rendered
    assert "data:image/svg+xml;base64," in rendered
    # V2 uses the specimen's authorization, independently of the v1 authorization configuration.
    assert "AUT.DB/SISB/XXXXX" not in rendered
    legacy = service._gaia_proposal_html({**payload, "bollettino_version": "v1"})
    assert 'class="poste-v2"' not in legacy and "AUT.DB/SISB/XXXXX" in legacy


def test_v2_handles_missing_causale_city_and_long_names_without_truncation(payload) -> None:
    fields = service._batch_template_field_values(payload)
    fields.update(
        Denominazione="AZIENDA AGRICOLA " * 3,
        INDIRIZZO="  VIA A < B  ",
        CAP="",
        CITTA="-",
        PROVINCIA="",
    )
    rendered = layout.bollettino_v2_html(
        fields,
        payload,
        barcode_renderer=service._gaia_bollettino_code128_svg,
        causale="",
    )
    assert "AZIENDA AGRICOLA AZIENDA AGRICOLA AZIENDA AGRICOLA" in rendered
    assert "Causale:" not in rendered
    assert 'font-size="7.' in rendered
    assert rendered.count(">VIA A &lt; B</text>") == 2
    assert rendered.count('y="442.5"') == 2 and rendered.count("></text>") == 2
    fields["Denominazione"] = "A" * 200
    rendered = layout.bollettino_v2_html(
        fields,
        payload,
        barcode_renderer=service._gaia_bollettino_code128_svg,
        causale="",
    )
    assert (
        rendered.count(f'font-size="6.0{"3"}') == 2 and rendered.count(f">{'A' * 60}…</text>") == 2
    )


@pytest.mark.parametrize(
    ("name", "printed"),
    [
        (
            "Societa Agricola F.lli Sotgiu Donatello E Maria Irene Soc. Semplice",
            "Soc. Agr. F.lli Sotgiu Donatello E Maria Irene S.S.",
        ),
        (
            "SOCIETÀ COOPERATIVA AGRICOLA FRATELLI ROSSI E BIANCHI DI ORISTANO SANTA GIUSTA",
            "Soc. Coop. AGRICOLA F.lli ROSSI E BIANCHI DI ORISTANO SANTA…",
        ),
        (
            "Cooperativa dei Fratelli Rossi a responsabilita limitata del Campidano di Oristano",
            "Coop. dei F.lli Rossi a responsabilita limitata del Campidan…",
        ),
        (
            "Rossi e Bianchi Societa' a responsabilita' limitata - Campidano di Oristano",
            "Rossi e Bianchi S.r.l. - Campidano di Oristano",
        ),
        ("Mario Rossi Societa Agricola", "Mario Rossi Societa Agricola"),
    ],
)
def test_v2_shortens_legal_forms_only_when_the_name_does_not_fit(name, printed) -> None:
    assert layout._fit(name, 230) == printed
    assert len(printed) <= 61


def test_pdf_pipeline_selects_only_the_slip_and_restores_exact_page_size(
    payload, tmp_path, monkeypatch
):
    printed = []

    def print_pdf(args, **_kwargs):
        html_path = Path(args[-1].removeprefix("file://"))
        content = html_path.read_text()
        printed.append(content)
        output = Path(
            next(arg.split("=", 1)[1] for arg in args if arg.startswith("--print-to-pdf="))
        )
        writer = PdfWriter()
        writer.add_blank_page(width=594.96, height=840.96)
        writer.write(output)

    monkeypatch.setattr(service, "_find_chromium_binary", lambda: "/usr/bin/chromium")
    monkeypatch.setattr(service, "_chromium_accessible_temp_parent", lambda _binary: None)
    monkeypatch.setattr(printer.subprocess, "run", print_pdf)
    output = tmp_path / "avviso.pdf"
    service.generate_batch_reminder_pdf(payload, output_path=output)
    pages = PdfReader(output).pages
    assert len(pages) == 3 and len(printed) == 3
    assert [float(v) for v in pages[0].mediabox] == [0, 0, 594.96, 840.96]
    assert [float(v) for v in pages[-1].mediabox] == [0, 0, 595, 841]
    assert [float(v) for v in pages[-1].cropbox] == [0, 0, 595, 841]
    assert all('class="poste-v2"' not in content for content in printed[:2])
    service.generate_batch_reminder_pdf({**payload, "print_bollettino": False}, output_path=output)
    assert len(PdfReader(output).pages) == 2
    assert 'class="poste-v2"' not in printed[-1]
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=841)
    writer.add_blank_page(width=595, height=841)
    writer.write(output)
    with pytest.raises(RuntimeError, match="una sola pagina"):
        printer._restore_poste_page_box(output)


def test_migration_defaults_existing_rules_to_v1_and_can_be_reverted() -> None:
    versions = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    migration = load_python_file(str(versions), "20261026_0900_tributi_bollettino_version.py")
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
                text("SELECT bollettino_version FROM ruolo_tributi_calculation_policies")
            ).scalar()
            == "v1"
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert [
            column["name"]
            for column in inspect(connection).get_columns("ruolo_tributi_calculation_policies")
        ] == ["id"]
    engine.dispose()
