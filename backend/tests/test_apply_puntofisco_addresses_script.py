from __future__ import annotations

import importlib.util
import runpy
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.application_user import (
    ApplicationUser,  # noqa: F401  (registra la FK application_users)
)
from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem
from app.modules.utenze.models import (
    AnagraficaAuditLog,
    AnagraficaCompany,
    AnagraficaPerson,
    AnagraficaPersonSnapshot,
    AnagraficaSubject,
)

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "apply_puntofisco_addresses.py"
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
PERSON_HEADER = [
    "CF_Inviato",
    "Esito",
    "Codice_Fiscale",
    "Com_Residenza",
    "PR",
    "CAP",
    "Indirizzo_Residenza_AdE",
]
COMPANY_HEADER = [
    "CF_Inviato",
    "Esito",
    "Codice_Fiscale",
    "Comune_Sede",
    "PR",
    "CAP",
    "Indirizzo_Sede",
]
ADDRESS = "VIA TUVERI 11 09092 ARBOREA OR"


def _load_script(*, without_backend_path: bool = False):
    backend_root = str(SCRIPT_PATH.parents[1])
    original_path = list(sys.path)
    if without_backend_path:
        sys.path[:] = [entry for entry in sys.path if entry != backend_root]
    spec = importlib.util.spec_from_file_location(
        "apply_puntofisco_addresses_under_test", SCRIPT_PATH
    )
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


def _workbook(tmp_path: Path, persons: list[list[object]], companies: list[list[object]]) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Persone fisiche"
    sheet.append(PERSON_HEADER)
    for row in persons:
        sheet.append(row)
    sheet = workbook.create_sheet("Persone giuridiche")
    sheet.append(COMPANY_HEADER)
    for row in companies:
        sheet.append(row)
    path = tmp_path / "R2.xlsx"
    workbook.save(path)
    return path


def _subject(db, name: str) -> AnagraficaSubject:
    subject = AnagraficaSubject(subject_type="person", source_name_raw=name)
    db.add(subject)
    db.flush()
    return subject


def _person(db, cf: str, **fields) -> uuid.UUID:
    subject = _subject(db, cf)
    db.add(
        AnagraficaPerson(
            subject_id=subject.id, cognome="ROSSI", nome="MARIO", codice_fiscale=cf, **fields
        )
    )
    db.commit()
    return subject.id


def _company(db, piva: str, cf: str | None = None) -> uuid.UUID:
    subject = _subject(db, piva)
    db.add(
        AnagraficaCompany(
            subject_id=subject.id, ragione_sociale="COOP", partita_iva=piva, codice_fiscale=cf
        )
    )
    db.commit()
    return subject.id


def _avviso(db, subject_id: uuid.UUID, address: str | None) -> uuid.UUID:
    avviso = RuoloAvviso(
        import_job_id=uuid.uuid4(),
        codice_cnc=f"01.{uuid.uuid4().hex[:10]}",
        anno_tributario=2025,
        subject_id=subject_id,
        residenza_raw=address,
        domicilio_raw=address,
    )
    db.add(avviso)
    db.commit()
    return avviso.id


def test_read_addresses_skips_replaced_codes_and_incomplete_rows(tmp_path: Path) -> None:
    module = _load_script()
    path = _workbook(
        tmp_path,
        [
            ["aaa", "0000", "aaa", "Arborea", "or", "09092", " via  tuveri 11 "],
            ["OLD", "0001", "NEW", "X", "OR", "09092", "VIA X"],
            ["NEW", "0000", "NEW", "X", "OR", "09092", "VIA X"],
            ["BBB", "0000", "BBB", "X", "OR", "09092", None],
            ["CCC", "0000", "CCC", "PARIGI", None, None, "RUE X 1"],
        ],
        [
            ["P1", "0000", "P1", "ORISTANO", "OR", "09170", "VIA SEDE 1"],
            ["P2", "0008", "P2", None, None, None, None],
        ],
    )

    addresses, skipped = module.read_addresses(path)

    assert addresses == [
        module.Address("person", "AAA", "VIA TUVERI 11", "09092", "ARBOREA", "OR"),
        module.Address("person", "CCC", "RUE X 1", None, "PARIGI", None),
        module.Address("company", "P1", "VIA SEDE 1", "09170", "ORISTANO", "OR"),
    ]
    assert skipped == {"cf_anomalo": 2, "indirizzo_mancante": 1, "esito_0008": 1}
    assert addresses[0].avviso_text == ADDRESS
    assert addresses[0].comune_label == "ARBOREA (OR)"
    assert addresses[1].comune_label == "PARIGI"
    assert module._text(None) is None


def test_apply_addresses_updates_registry_and_notices_with_audit() -> None:
    module = _load_script()
    tuveri = module.Address("person", "AAA", "VIA TUVERI 11", "09092", "ARBOREA", "OR")
    with TestingSessionLocal() as db:
        person_id = _person(
            db, "AAA", indirizzo="VIA Vecchia 1", cap="09170", comune_residenza="ORISTANO (OR)"
        )
        old_avviso = _avviso(db, person_id, "VIA VECCHIA 1 09170 ORISTANO OR")
        aligned_avviso = _avviso(db, person_id, ADDRESS)
        company_id = _company(db, "P1", cf="CFP1")
        aligned_id = _person(
            db, "BBB", indirizzo="VIA TUVERI 11", cap="09092", comune_residenza="ARBOREA (OR)"
        )
        notices_only_id = _person(
            db, "CCC", indirizzo="VIA TUVERI 11", cap="09092", comune_residenza="ARBOREA (OR)"
        )
        _avviso(db, notices_only_id, None)
        addresses = [
            tuveri,
            module.Address("person", "AAA", "VIA DOPPIA 2", "09092", "ARBOREA", "OR"),
            module.Address("company", "CFP1", "VIA SEDE 1", "09170", "ORISTANO", "OR"),
            module.Address("person", "BBB", "VIA TUVERI 11", "09092", "ARBOREA", "OR"),
            module.Address("person", "CCC", "VIA TUVERI 11", "09092", "ARBOREA", "OR"),
            module.Address("person", "ZZZ", "VIA X", None, "X", None),
        ]

        outcomes = module.apply_addresses(db, addresses, source="test", dry_run=False)

        assert [(o.cf, o.esito, o.avvisi) for o in outcomes] == [
            ("AAA", "aggiornato", 1),
            ("CFP1", "aggiornato", 0),
            ("BBB", "gia_allineato", 0),
            ("CCC", "solo_avvisi", 1),
            ("ZZZ", "non_in_gaia", 0),
        ]
        assert outcomes[0].prima == "VIA Vecchia 1 09170 ORISTANO (OR)"
        assert outcomes[0].dopo == "VIA TUVERI 11 09092 ARBOREA (OR)"
        person = db.get(AnagraficaPerson, person_id)
        assert (person.indirizzo, person.cap, person.comune_residenza) == (
            "VIA TUVERI 11",
            "09092",
            "ARBOREA (OR)",
        )
        company = db.get(AnagraficaCompany, company_id)
        assert (company.sede_legale, company.cap, company.comune_sede) == (
            "VIA SEDE 1",
            "09170",
            "ORISTANO (OR)",
        )
        avviso = db.get(RuoloAvviso, old_avviso)
        assert (avviso.residenza_raw, avviso.domicilio_raw) == (ADDRESS, ADDRESS)
        snapshot = db.scalars(select(AnagraficaPersonSnapshot)).one()
        assert (snapshot.subject_id, snapshot.indirizzo, snapshot.source_system) == (
            person_id,
            "VIA Vecchia 1",
            "puntofisco",
        )
        audits = {a.subject_id: a.diff_json for a in db.scalars(select(AnagraficaAuditLog))}
        assert set(audits) == {person_id, company_id, notices_only_id}
        assert audits[person_id]["avvisi_before"] == [
            [str(old_avviso), "VIA VECCHIA 1 09170 ORISTANO OR", "VIA VECCHIA 1 09170 ORISTANO OR"]
        ]
        assert audits[person_id]["before"]["indirizzo"] == "VIA Vecchia 1"
        assert audits[person_id]["source"] == "test"
        assert db.get(AnagraficaPerson, aligned_id).indirizzo == "VIA TUVERI 11"
        assert db.get(RuoloAvviso, aligned_avviso).residenza_raw == ADDRESS


def test_apply_addresses_dry_run_writes_nothing() -> None:
    module = _load_script()
    with TestingSessionLocal() as db:
        person_id = _person(db, "AAA", indirizzo="VIA VECCHIA 1")
        avviso_id = _avviso(db, person_id, "VIA VECCHIA 1")

        outcomes = module.apply_addresses(
            db,
            [module.Address("person", "AAA", "VIA TUVERI 11", "09092", "ARBOREA", "OR")],
            source="test",
            dry_run=True,
        )

        assert [(o.esito, o.avvisi) for o in outcomes] == [("aggiornato", 1)]
        assert db.get(AnagraficaPerson, person_id).indirizzo == "VIA VECCHIA 1"
        assert db.get(RuoloAvviso, avviso_id).residenza_raw == "VIA VECCHIA 1"
        assert db.scalars(select(AnagraficaAuditLog)).all() == []


def _audited(db, subject_id: uuid.UUID) -> None:
    db.add(
        AnagraficaAuditLog(subject_id=subject_id, action="puntofisco_address_update", diff_json={})
    )
    db.add(AnagraficaAuditLog(subject_id=subject_id, action="altro", diff_json={}))
    db.commit()


def _item(cf: str, name: str | None = "ROSSI MARIO"):
    return SimpleNamespace(
        id=uuid.uuid4(), codice_fiscale=cf, display_name=name, generated_document_path="old.pdf"
    )


def _regeneration_setup(module, monkeypatch, items, failures):
    calls = []

    def fake_regenerate(db, item, mode, *, actor_id, reason):
        calls.append((item.codice_fiscale, mode, actor_id, reason))
        if item.codice_fiscale in failures:
            raise failures[item.codice_fiscale]
        item.generated_document_path = "new.pdf"

    monkeypatch.setattr(
        module.regeneration, "regeneration_targets", lambda db, batch_id: (items, 3)
    )
    monkeypatch.setattr(module.regeneration, "regenerate_batch_item", fake_regenerate)
    return calls


def test_regenerate_pdfs_only_for_updated_subjects(monkeypatch) -> None:
    module = _load_script()
    with TestingSessionLocal() as db:
        _audited(db, _person(db, "AAA"))
        _audited(db, _person(db, "SKIP"))
        _audited(db, _person(db, "FAIL"))
        _audited(db, _person(db, "SENT"))
        _audited(db, _company(db, "P1", cf="CFP1"))
        _person(db, "OTHER")
        sent = _item("SENT")
        db.add(
            PosteDispatchItem(
                lot_id=uuid.uuid4(),
                batch_item_id=sent.id,
                notice_number="N1",
                shipment_name="S1",
                active_key="N1",
                recipient={},
                artifact_sha256="x",
                artifact_size=1,
            )
        )
        db.commit()
        items = [
            _item("aaa "),
            _item("CFP1", None),
            _item("OTHER"),
            sent,
            _item("SKIP"),
            _item("FAIL"),
        ]
        calls = _regeneration_setup(
            module,
            monkeypatch,
            items,
            {
                "SKIP": module.regeneration.RegenerationSkipped("posizione cambiata"),
                "FAIL": module.regeneration.RegenerationFailed("render"),
            },
        )

        outcomes = module.regenerate_pdfs(db, actor_id=7, dry_run=False)

        assert [(o.cf, o.esito, o.prima, o.dopo) for o in outcomes] == [
            ("aaa ", "rigenerato", "ROSSI MARIO", "new.pdf"),
            ("CFP1", "rigenerato", "", "new.pdf"),
            ("SENT", "in_spedizione", "ROSSI MARIO", ""),
            ("SKIP", "saltato", "ROSSI MARIO", "posizione cambiata"),
            ("FAIL", "errore", "ROSSI MARIO", "render"),
        ]
        assert {call[1:] for call in calls} == {("recompute", 7, module.REGENERATION_REASON)}

        calls.clear()
        dry = module.regenerate_pdfs(db, actor_id=None, dry_run=True)
        assert [o.esito for o in dry] == [
            "da_rigenerare",
            "da_rigenerare",
            "in_spedizione",
            "da_rigenerare",
            "da_rigenerare",
        ]
        assert calls == []


def test_main_addresses_and_regenerate(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _load_script(without_backend_path=True)
    with TestingSessionLocal() as db:
        _person(db, "AAA", indirizzo="VIA VECCHIA 1")
    path = _workbook(
        tmp_path,
        [
            ["AAA", "0000", "AAA", "ARBOREA", "OR", "09092", "VIA TUVERI 11"],
            ["BBB", "0000", "BBB", "ARBOREA", "OR", "09092", None],
        ],
        [],
    )
    report = tmp_path / "report.csv"
    monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)

    assert module.main(["addresses", str(path), "--report", str(report), "--apply"]) == 0

    out = capsys.readouterr().out
    assert "aggiornato: 1" in out
    assert "scartati_indirizzo_mancante: 1" in out
    assert report.read_text(encoding="utf-8").splitlines()[1].startswith("AAA,")
    with TestingSessionLocal() as db:
        assert db.scalars(select(AnagraficaPerson)).one().indirizzo == "VIA TUVERI 11"

    _regeneration_setup(module, monkeypatch, [_item("AAA")], {})
    assert module.main(["regenerate", "--report", str(report), "--apply", "--actor-id", "7"]) == 0
    assert "rigenerato: 1" in capsys.readouterr().out
    try:
        module.main(["regenerate", "--report", str(report), "--apply"])
    except SystemExit as exc:
        assert exc.code == 2
    assert "--actor-id" in capsys.readouterr().err


def test_script_entrypoint_shows_help(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH), "--help"])
    try:
        runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0
    assert "PuntoFisco" in capsys.readouterr().out
