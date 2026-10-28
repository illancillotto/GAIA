import runpy
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import create_engine, inspect, text

from app.core import database
from app.modules.ruolo.payer_assignment_models import RuoloTributiPayerAssignment
from app.modules.ruolo.services import payer_assignments as service
from app.modules.ruolo.services.payer_notice_cell import payer_notice_cell_html
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject
from app.scripts import import_payer_assignments as script

from .test_tributi_api import TestingSessionLocal, auth_headers, client, seed_avviso
from .test_tributi_api import setup_database as setup_database

OWNER = "FLRSST40A01F272X"
OTHER_OWNER = "PNNDRA50A01F272Y"
HEIR = "FLRFRZ68C17F272I"
COMPANY_VAT = "01217890951"
SMALL = '<small style="display:block;white-space:normal;overflow-wrap:anywhere">'


def _person(tax_code: str = HEIR, *, nas: str | None = "/archivio/F/FLORIS FABRIZIO") -> UUID:
    with TestingSessionLocal() as db:
        subject = AnagraficaSubject(source_name_raw="FLORIS FABRIZIO", nas_folder_path=nas)
        db.add(subject)
        db.flush()
        db.add(
            AnagraficaPerson(
                subject_id=subject.id,
                cognome="FLORIS",
                nome="FABRIZIO",
                codice_fiscale=tax_code,
                indirizzo="VIA POLA N 1",
                cap="09030",
                comune_residenza="SARDARA",
            )
        )
        db.commit()
        return subject.id


def _company(*, tax_code: str | None = None) -> UUID:
    with TestingSessionLocal() as db:
        subject = AnagraficaSubject(source_name_raw="SIMACAR S.R.L.")
        db.add(subject)
        db.flush()
        db.add(
            AnagraficaCompany(
                subject_id=subject.id,
                ragione_sociale="SIMACAR S.R.L.",
                partita_iva=COMPANY_VAT,
                codice_fiscale=tax_code,
                sede_legale="VIA ROMA 2",
                comune_sede="ORISTANO",
            )
        )
        db.commit()
        return subject.id


def _put(avviso_id: str, tax_code: str = HEIR, reason: str = "decesso", **extra):
    return client.put(
        f"/ruolo/tributi/avvisi/{avviso_id}/payer",
        headers=auth_headers(),
        json={"payer_tax_code": tax_code, "reason": reason, **extra},
    )


def test_payer_is_set_replaced_with_history_and_removed() -> None:
    _person()
    _company()
    avviso_id = seed_avviso(tax_code=OWNER, nominativo="FLORIS SEBASTIANO")

    assert client.get(
        f"/ruolo/tributi/avvisi/{avviso_id}/payer", headers=auth_headers()
    ).json() == {"active": None, "history": []}
    first = _put(avviso_id, HEIR.lower(), notes="  erede unico  ")
    assert first.status_code == 200, first.text
    active = first.json()["active"]
    assert active["payer_name"] == "FLORIS FABRIZIO"
    assert active["payer_address"] == "VIA POLA N 1 09030 SARDARA"
    assert active["reason_label"] == "Decesso: paga l'erede"
    assert active["notes"] == "erede unico"

    second = _put(avviso_id, COMPANY_VAT, "vendita").json()
    assert second["active"]["payer_name"] == "SIMACAR S.R.L."
    assert second["active"]["payer_address"] == "VIA ROMA 2 ORISTANO"
    assert [row["voided_at"] is None for row in second["history"]] == [True, False]

    removed = client.delete(f"/ruolo/tributi/avvisi/{avviso_id}/payer", headers=auth_headers())
    assert removed.json()["active"] is None and len(removed.json()["history"]) == 2


def test_payer_read_and_write_permissions_preserve_the_current_assignment() -> None:
    _person()
    avviso_id = seed_avviso(tax_code=OWNER)
    path = f"/ruolo/tributi/avvisi/{avviso_id}/payer"
    assert client.get(path).status_code == 401
    assert _put(avviso_id).status_code == 200
    viewer = auth_headers("ruolo-tributi-viewer")
    assert client.get(path, headers=viewer).json()["active"]["payer_tax_code"] == HEIR
    for method, payload in (
        ("PUT", {"payer_tax_code": HEIR, "reason": "vendita"}),
        ("DELETE", None),
    ):
        response = client.request(method, path, headers=viewer, json=payload)
        assert response.status_code == 403
    current = client.get(path, headers=auth_headers()).json()
    assert current["active"]["reason"] == "decesso"
    assert len(current["history"]) == 1


def test_payer_must_exist_differ_from_the_taxpayer_and_target_a_real_avviso() -> None:
    _person()
    avviso_id = seed_avviso(tax_code=HEIR)

    missing = _put(avviso_id, "MRENRC69M15L321N")
    assert missing.status_code == 422
    assert "non e presente in anagrafica" in missing.json()["detail"]
    same = _put(avviso_id, HEIR)
    assert same.status_code == 422 and "gia l'intestatario" in same.json()["detail"]
    assert _put(str(uuid4())).status_code == 404
    assert (
        client.get(f"/ruolo/tributi/avvisi/{uuid4()}/payer", headers=auth_headers()).status_code
        == 404
    )
    assert _put(avviso_id, reason="altro").status_code == 422
    with TestingSessionLocal() as db, pytest.raises(ValueError, match="Motivo non valido"):
        service.assign(
            db,
            avviso_id=UUID(avviso_id),
            payer_tax_code=HEIR,
            reason="altro",
            notes=None,
            user_id=None,
        )


def test_payers_without_registry_data_are_ignored() -> None:
    company_id = _company(tax_code="90000000001")
    avviso_id = UUID(seed_avviso(tax_code=OWNER))
    with TestingSessionLocal() as db:
        bare = AnagraficaSubject(source_name_raw="SENZA DATI")
        db.add(bare)
        db.flush()
        assert service.load_payer(db, uuid4()) is None
        assert service.load_payer(db, bare.id) is None
        assert service.load_payer(db, company_id).tax_code == "90000000001"
        assert service.find_subject_by_tax_code(db, COMPANY_VAT) == company_id
        assert service.payer_tax_code(db, uuid4()) is None
        assert service.active_payers(db, []) == {}
        db.add(
            RuoloTributiPayerAssignment(
                avviso_id=avviso_id, payer_subject_id=bare.id, reason="ufficio"
            )
        )
        db.flush()
        assert service.active_payers(db, [avviso_id]) == {}
        candidates = [{"avvisi": [{"id": avviso_id}]}]
        assert service.reassign_candidates(db, candidates) is candidates


def test_reminders_of_reassigned_avvisi_go_to_the_payer(monkeypatch: pytest.MonkeyPatch) -> None:
    _person()
    client.post(
        "/ruolo/tributi/calculation-policies",
        headers=auth_headers(),
        json={"name": "Regola 2024", "year_from": 2024, "year_to": 2024},
    )
    inherited = seed_avviso(amount=100.0, tax_code=OWNER, nominativo="FLORIS SEBASTIANO")
    seed_avviso(amount=50.0, tax_code=OWNER, nominativo="FLORIS SEBASTIANO")
    bought = seed_avviso(amount=70.0, tax_code=OTHER_OWNER, nominativo="PINNA DARIO")
    assert _put(inherited).status_code == 200
    assert _put(bought, reason="ufficio").status_code == 200
    payloads: list[dict] = []

    def fake_pdf(payload: dict, *, output_path: Path) -> None:
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
            "title": "Eredi",
            "codice_fiscale": [OWNER, OTHER_OWNER],
            "filters": {"years": [2024], "preview_only": True},
            "template_path": "/tmp/template.docx",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["items_total"] == 3
    by_owner = {
        (
            payload["codice_fiscale"],
            payload.get("payer_assignment", {}).get("codice_fiscale"),
        ): payload
        for payload in payloads
    }
    own = by_owner[(OWNER, None)]
    assert own["saldo_amount"] == "50.00 EUR" and own["display_name"] == "FLORIS SEBASTIANO"
    heir = by_owner[(HEIR, OWNER)]
    assert heir["display_name"] == "FLORIS FABRIZIO" and heir["saldo_amount"] == "100.00 EUR"
    assert heir["avvisi"][0]["residenza_raw"] == "VIA POLA N 1 09030 SARDARA"
    assert heir["payer_assignment"] == {
        "intestatario": "FLORIS SEBASTIANO",
        "codice_fiscale": OWNER,
        "reason": "decesso",
        "role": "erede",
    }
    assert by_owner[(HEIR, OTHER_OWNER)]["payer_assignment"]["role"] is None


def test_summary_cell_names_the_registered_taxpayer() -> None:
    assert payer_notice_cell_html("1, 2", None) == "1<br>2"
    assert payer_notice_cell_html("1", {"intestatario": "A & B", "role": "erede"}) == (
        "1" + SMALL + "intestato a<br>A &amp; B<br>dovuto come erede</small>"
    )
    assert payer_notice_cell_html("1", {"intestatario": "A", "role": None}) == (
        "1" + SMALL + "intestato a<br>A</small>"
    )


def test_import_script_links_new_payers_and_reports_the_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _person()
    first = seed_avviso(tax_code=OWNER)
    second = seed_avviso(tax_code=OTHER_OWNER)
    csv_path = tmp_path / "pagatori.csv"
    csv_path.write_text(
        "avviso_id;avviso;cf_pagatore;motivo;note\n"
        f"{first};020210004298300;{HEIR};ufficio;Excel ufficio\n"
        f"{second};020210000566810;SCNTRS40B43F840Y;ufficio;\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(script, "SessionLocal", TestingSessionLocal)

    script.main([str(csv_path)])
    assert "DRY RUN" in capsys.readouterr().out
    with TestingSessionLocal() as db:
        assert service.payer_tax_code(db, UUID(first)) is None

    script.main([str(csv_path), "--apply"])
    out = capsys.readouterr().out
    assert f"020210004298300: collegato a {HEIR}" in out
    assert "020210000566810: SALTATO" in out and "APPLIED" in out
    script.main([str(csv_path), "--apply"])
    assert "020210004298300: gia collegato" in capsys.readouterr().out


def test_migration_creates_and_drops_the_assignment_table() -> None:
    versions = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    migration = load_python_file(str(versions), "20261027_0900_tributi_payer_assignments.py")
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for table, key in (
            ("ruolo_avvisi", "id CHAR(32)"),
            ("ana_subjects", "id CHAR(32)"),
            ("application_users", "id INTEGER"),
        ):
            connection.execute(text(f"CREATE TABLE {table} ({key} PRIMARY KEY)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        assert "ruolo_tributi_payer_assignments" in inspect(connection).get_table_names()
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert "ruolo_tributi_payer_assignments" not in inspect(connection).get_table_names()
    engine.dispose()


def test_import_command_entry_point_is_a_dry_run_by_default(tmp_path, monkeypatch, capsys):
    _person()
    avviso_id = seed_avviso(tax_code=OWNER)
    csv_path = tmp_path / "pagatori.csv"
    csv_path.write_text(
        f"avviso_id;avviso;cf_pagatore;motivo;note\n{avviso_id};AVVISO-TEST;{HEIR};ufficio;\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(database, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(sys, "argv", [script.__file__, str(csv_path)])
    runpy.run_path(script.__file__, run_name="__main__")
    assert "DRY RUN: nessuna modifica salvata" in capsys.readouterr().out
    with TestingSessionLocal() as db:
        assert service.payer_tax_code(db, UUID(avviso_id)) is None
