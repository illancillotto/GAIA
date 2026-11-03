from __future__ import annotations

import datetime as dt
import importlib.util
import runpy
import sys
import uuid
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.application_user import (
    ApplicationUser,  # noqa: F401  (registra la FK application_users)
)
from app.modules.utenze.models import AnagraficaAuditLog, AnagraficaPerson, AnagraficaSubject

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "apply_puntofisco_deaths.py"
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
HEADER = ["CF_Inviato", "Esito", "Codice_Fiscale", "Cognome", "STATO", "Data_Decesso"]


def _load_script(*, without_backend_path: bool = False):
    backend_root = str(SCRIPT_PATH.parents[1])
    original_path = list(sys.path)
    if without_backend_path:
        sys.path[:] = [entry for entry in sys.path if entry != backend_root]
    spec = importlib.util.spec_from_file_location("apply_puntofisco_deaths_under_test", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original_path
    return module


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _workbook(tmp_path: Path, rows: list[list[object]]) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Persone fisiche"
    sheet.append(HEADER)
    for row in rows:
        sheet.append(row)
    path = tmp_path / "R2.xlsx"
    workbook.save(path)
    return path


def _person(
    db, cf: str, *, data_decesso: dt.date | None = None, stato_anpr: str | None = None
) -> uuid.UUID:
    subject = AnagraficaSubject(subject_type="person", source_name_raw=cf)
    db.add(subject)
    db.flush()
    db.add(
        AnagraficaPerson(
            subject_id=subject.id,
            cognome="ROSSI",
            nome="MARIO",
            codice_fiscale=cf,
            data_decesso=data_decesso,
            stato_anpr=stato_anpr,
        )
    )
    db.commit()
    return subject.id


def test_read_death_records_keeps_only_dated_deaths(tmp_path: Path) -> None:
    module = _load_script()
    path = _workbook(
        tmp_path,
        [
            ["aaa", "0000", "AAA", "X", "DECEDUTO", dt.datetime(2023, 9, 28)],
            ["BBB", "0000", "BBB", "X", "Vivente", None],
            [
                "CCC",
                "0000",
                "CCC",
                "X",
                "Decesso presunto per limiti di età",
                dt.datetime(1001, 1, 1),
            ],
            ["DDD", "0000", "DDD", "X", "DECEDUTO", None],
            ["EEE", "0000", "EEE", "X", "DECEDUTO", dt.date(2020, 1, 2)],
        ],
    )

    records, skipped = module.read_death_records(path)

    assert records == [
        module.DeathRecord("AAA", "AAA", dt.date(2023, 9, 28)),
        module.DeathRecord("EEE", "EEE", dt.date(2020, 1, 2)),
    ]
    assert skipped == {"decesso_presunto": 1, "data_decesso_mancante": 1}
    assert module._as_date("28092023") is None
    assert module._as_date(dt.date(2020, 1, 2)) == dt.date(2020, 1, 2)


def test_apply_deaths_updates_only_missing_dates_and_audits() -> None:
    module = _load_script()
    with TestingSessionLocal() as db:
        new_id = _person(db, "NEW")
        old_cf_id = _person(db, "OLD", stato_anpr="deceased")
        new_cf_id = _person(db, "OLDNEW")
        _person(db, "SAME", data_decesso=dt.date(2024, 1, 1), stato_anpr="deceased")
        _person(db, "DIFF", data_decesso=dt.date(2024, 1, 2), stato_anpr="deceased")
        _person(db, "ALIVE", stato_anpr="alive")
        records = [
            module.DeathRecord("NEW", "NEW", dt.date(2023, 9, 28)),
            module.DeathRecord("OLD", "OLDNEW", dt.date(2022, 5, 1)),
            module.DeathRecord("OLDNEW", "OLDNEW", dt.date(2022, 5, 1)),
            module.DeathRecord("SAME", "SAME", dt.date(2024, 1, 1)),
            module.DeathRecord("DIFF", "DIFF", dt.date(2024, 1, 1)),
            module.DeathRecord("ALIVE", "ALIVE", dt.date(2024, 1, 1)),
            module.DeathRecord("MISSING", "MISSING", dt.date(2024, 1, 1)),
        ]

        outcomes = module.apply_deaths(db, records, source="test", dry_run=False)

        assert {
            (o.subject_id, o.esito)
            for o in outcomes
            if o.subject_id in {str(old_cf_id), str(new_cf_id)}
        } == {
            (str(old_cf_id), "data_aggiunta"),
            (str(new_cf_id), "decesso_registrato"),
        }
        assert [o.esito for o in outcomes if o.cf_ade != "OLDNEW"] == [
            "decesso_registrato",
            "gia_allineato",
            "conflitto_data",
            "conflitto_anpr_vivo",
            "non_in_gaia",
        ]
        updated = db.get(AnagraficaPerson, new_id)
        assert updated.data_decesso == dt.date(2023, 9, 28)
        assert updated.stato_anpr == "deceased"
        assert db.get(AnagraficaPerson, old_cf_id).data_decesso == dt.date(2022, 5, 1)
        audits = db.scalars(select(AnagraficaAuditLog)).all()
        assert {a.subject_id for a in audits} == {new_id, old_cf_id, new_cf_id}
        assert all(
            a.action == "puntofisco_death_update" and a.diff_json["source"] == "test"
            for a in audits
        )


def test_apply_deaths_dry_run_writes_nothing() -> None:
    module = _load_script()
    with TestingSessionLocal() as db:
        subject_id = _person(db, "NEW")

        outcomes = module.apply_deaths(
            db,
            [module.DeathRecord("NEW", "NEW", dt.date(2023, 9, 28))],
            source="test",
            dry_run=True,
        )

        assert [o.esito for o in outcomes] == ["decesso_registrato"]
        assert db.get(AnagraficaPerson, subject_id).data_decesso is None
        assert db.scalars(select(AnagraficaAuditLog)).all() == []


def test_main_writes_report(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _load_script(without_backend_path=True)
    with TestingSessionLocal() as db:
        _person(db, "NEW")
    path = _workbook(
        tmp_path,
        [
            ["NEW", "0000", "NEW", "X", "DECEDUTO", dt.datetime(2023, 9, 28)],
            ["OLD", "0000", "OLD", "X", "DECEDUTO", None],
        ],
    )
    report = tmp_path / "report.csv"
    monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)

    assert module.main([str(path), "--report", str(report), "--apply"]) == 0

    out = capsys.readouterr().out
    assert "decesso_registrato: 1" in out
    assert "scartati_data_decesso_mancante: 1" in out
    assert report.read_text(encoding="utf-8").splitlines()[1].startswith("NEW,")
    with TestingSessionLocal() as db:
        assert db.scalars(select(AnagraficaPerson)).one().stato_anpr == "deceased"


def test_script_entrypoint_shows_help(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH), "--help"])
    try:
        runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0
    assert "PuntoFisco" in capsys.readouterr().out
