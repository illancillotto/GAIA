from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.services import sister_visura_extractions as runtime


class RecordingSession:
    def __init__(self, existing=None, candidates=None, canonical_owner=None, fail_at=None):
        self.existing = existing
        self.candidates = candidates or []
        self.canonical_owner = canonical_owner
        self.fail_at = fail_at
        self.operations = []
        self.records = []
        self.scalar_count = 0
        self.flush_count = 0

    def scalar(self, statement):
        self.scalar_count += 1
        self.operations.append(("scalar", str(statement), statement.compile().params))
        if self.fail_at == "owner" and self.scalar_count > 1:
            raise RuntimeError("owner lookup failed")
        return self.existing if self.scalar_count == 1 else self.canonical_owner

    def execute(self, statement):
        self.operations.append(("execute", str(statement), statement.compile().params))
        if self.fail_at == "delete" and str(statement).startswith("DELETE"):
            raise RuntimeError("delete failed")
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: self.candidates))

    def add(self, record):
        if record.id is None:
            record.id = UUID(int=40 + len(self.records))
        self.operations.append(("add", type(record).__name__))
        self.records.append(record)

    def flush(self):
        self.flush_count += 1
        self.operations.append(("flush",))
        if self.fail_at == f"flush{self.flush_count}":
            raise RuntimeError("flush failed")


@pytest.fixture
def document():
    return SimpleNamespace(id=UUID(int=1), filepath="visura.pdf")


@pytest.fixture
def parsed():
    return {
        "status": "ready",
        "observed_at": date(2026, 10, 5),
        "comune_nome": "Comune",
        "comune_codice": "A001",
        "parcel": {"foglio": "01", "particella": "002", "subalterno": "A"},
        "owners": [
            {
                "codice_fiscale": " cf001 ",
                "data_nascita": date(1980, 1, 2),
                "nome": "Nome",
                "cognome": "Cognome",
                "denominazione": "Persona",
                "luogo_nascita": "Luogo",
                "diritto": "Proprieta",
                "quota": "1/2",
            }
        ],
        "history_events": [
            {
                "from_date": date(2020, 1, 1),
                "act_date": date(2019, 12, 2),
                "act": "Atto",
                "owner": {
                    "codice_fiscale": "raw cf",
                    "denominazione": "Storico",
                    "diritto": "Usufrutto",
                    "quota": "1/4",
                },
            }
        ],
    }


@pytest.fixture(autouse=True)
def parser_stubs(monkeypatch, parsed):
    monkeypatch.setattr(runtime, "sister_pdf_sha256", lambda _: "current-sha")
    monkeypatch.setattr(runtime, "parse_sister_visura_pdf", lambda _: parsed)


@pytest.mark.parametrize("invalid_history", [False, True])
def test_multiple_children_order_and_partial_history_failure(document, parsed, invalid_history):
    parsed["owners"].append({"nome": "Secondo"})
    parsed["history_events"].append(
        {"act": "Secondo atto", "from_date": "invalid" if invalid_history else "2021-01-01"}
    )
    session = RecordingSession()
    result = runtime.persist_sister_visura(session, document)
    assert result.status == ("failed" if invalid_history else "ready")
    assert [type(record).__name__ for record in session.records] == [
        "CatastoSisterExtraction",
        "CatastoSisterParcel",
        "CatastoSisterOwner",
        "CatastoSisterOwner",
        "CatastoSisterHistoryEvent",
        "CatastoSisterExtraction" if invalid_history else "CatastoSisterHistoryEvent",
    ]
    assert session.records[3].nome == "Secondo"
    assert session.records[4].act_description == "Atto"
    assert session.flush_count == 2
    if invalid_history:
        assert session.records[-1] is result
        assert result.payload_json == {}
        assert "Invalid isoformat" in result.error_message
    else:
        assert session.records[-1].act_description == "Secondo atto"


@pytest.mark.parametrize(
    "sha,version,cached",
    [
        ("current-sha", runtime.PARSER_VERSION, True),
        ("old-sha", runtime.PARSER_VERSION, False),
        ("current-sha", "old-version", False),
    ],
)
def test_cache_and_existing_record_reuse(document, sha, version, cached):
    existing = runtime.CatastoSisterExtraction(
        id=UUID(int=2),
        document_id=document.id,
        pdf_sha256=sha,
        parser_version=version,
        payload_json={"old": True},
        status="failed",
    )
    session = RecordingSession(existing=existing)
    result = runtime.persist_sister_visura(session, document)
    assert result is existing
    assert session.flush_count == (0 if cached else 2)
    assert len(session.operations) == (1 if cached else 11)
    if not cached:
        assert result.pdf_sha256 == "current-sha"
        assert result.parser_version == runtime.PARSER_VERSION
        assert result.error_message is None


def test_persistence_record_values_and_operation_order(document, parsed):
    canonical_parcel = SimpleNamespace(
        id=UUID(int=3), codice_catastale="a001", nome_comune="Comune"
    )
    session = RecordingSession(
        candidates=[canonical_parcel], canonical_owner=SimpleNamespace(id=UUID(int=4))
    )
    result = runtime.persist_sister_visura(session, document)
    assert result.status == "ready"
    assert result.observed_at == date(2026, 10, 5)
    assert result.payload_json["owners"][0]["data_nascita"] == "1980-01-02"
    assert parsed["owners"][0]["data_nascita"] == date(1980, 1, 2)
    assert [operation[0] for operation in session.operations] == [
        "scalar",
        "add",
        "flush",
        "execute",
        "execute",
        "execute",
        "add",
        "flush",
        "scalar",
        "add",
        "add",
    ]
    assert session.operations[3][1].startswith("DELETE FROM catasto_sister_parcels")
    assert session.operations[4][1].startswith("DELETE FROM catasto_sister_history_events")
    parcel, owner, history = session.records[1:]
    assert parcel.cat_particella_id == canonical_parcel.id
    assert (parcel.foglio, parcel.particella, parcel.subalterno) == ("01", "002", "A")
    assert owner.cat_intestatario_id == UUID(int=4)
    assert owner.codice_fiscale == "CF001"
    assert owner.data_nascita == date(1980, 1, 2)
    assert (owner.nome, owner.cognome, owner.quota, owner.diritto) == (
        "Nome",
        "Cognome",
        "1/2",
        "Proprieta",
    )
    assert owner.payload_json == result.payload_json["owners"][0]
    assert history.from_date == date(2020, 1, 1)
    assert history.act_date == date(2019, 12, 2)
    assert history.codice_fiscale == "raw cf"
    assert history.act_description == "Atto"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"parcel": {}},
        {"parcel": {"foglio": "1"}},
        {"parcel": {"particella": "2"}},
        {"owners": [{"codice_fiscale": "   "}], "history_events": [{}]},
        {"owners": [{"codice_fiscale": "UNKNOWN"}], "history_events": [{"owner": {}}]},
    ],
)
def test_empty_fields_and_missing_canonical_records(monkeypatch, document, payload):
    monkeypatch.setattr(runtime, "parse_sister_visura_pdf", lambda _: payload)
    session = RecordingSession()
    result = runtime.persist_sister_visura(session, document)
    assert result.status == "review_required"
    assert result.observed_at is None
    assert session.records[1].cat_particella_id is None
    for owner in session.records[2:]:
        if isinstance(owner, runtime.CatastoSisterOwner):
            assert owner.cat_intestatario_id is None
            assert owner.data_nascita is None


@pytest.mark.parametrize(
    "code,name,candidates,expected",
    [
        ("a001", "unused", [("A001", "Comune")], 0),
        ("", "comune", [("X", "Comune")], 0),
        ("missing", "comune", [(None, "Comune")], 0),
        ("", "", [(None, None)], None),
        ("a001", "comune", [("A001", "Comune"), ("a001", "Comune")], None),
        ("", "missing", [(None, None)], None),
        (" A001 ", "Other", [("a001", "Comune"), ("X", "Other")], 0),
        ("A001", "Other", [("A001", "Comune"), ("a001", "Comune"), ("X", "Other")], None),
        ("missing", "Comune", [("X", "Comune"), ("Y", "COMUNE")], None),
        ("A001", "", [(" A001 ", "Comune")], None),
        ("", " Comune ", [(None, "COMUNE")], 0),
        ("", "Comune", [(None, " Comune ")], None),
        (0, 0, [(None, None)], None),
        (12, "", [("12", None)], 0),
    ],
)
def test_canonical_parcel_matching(code, name, candidates, expected):
    candidates = [
        SimpleNamespace(codice_catastale=code_value, nome_comune=name_value)
        for code_value, name_value in candidates
    ]
    session = RecordingSession(candidates=candidates)
    result = runtime._resolve_particella(
        session,
        {"comune_codice": code, "comune_nome": name, "parcel": {"foglio": "1", "particella": "2"}},
    )
    assert result is (candidates[expected] if expected is not None else None)


@pytest.mark.parametrize("fail_at", ["parse", "flush1", "flush2", "delete", "owner", "birth"])
@pytest.mark.parametrize("existing_record", [False, True])
def test_failure_state_preserves_partial_writes_and_existing_identity(
    monkeypatch, document, parsed, fail_at, existing_record
):
    existing = (
        runtime.CatastoSisterExtraction(
            id=UUID(int=2),
            document_id=document.id,
            pdf_sha256="old-sha",
            parser_version="old-version",
            payload_json={"old": True},
            status="ready",
        )
        if existing_record
        else None
    )
    session = RecordingSession(existing=existing, fail_at=fail_at)
    if fail_at == "parse":

        def fail_parser(_):
            raise RuntimeError("parse failed")

        monkeypatch.setattr(runtime, "parse_sister_visura_pdf", fail_parser)
    if fail_at == "birth":
        parsed["owners"][0]["data_nascita"] = "invalid"
    result = runtime.persist_sister_visura(session, document)
    if existing_record:
        assert result is existing
    assert result.status == "failed"
    assert result.payload_json == {}
    assert result.error_message
    assert session.records[-1] is result
    if fail_at in {"owner", "birth", "flush2"}:
        assert any(isinstance(record, runtime.CatastoSisterParcel) for record in session.records)


def test_sha_failure_propagates_before_try(monkeypatch, document):
    def fail_sha(_):
        raise RuntimeError("sha failed")

    monkeypatch.setattr(runtime, "sister_pdf_sha256", fail_sha)
    session = RecordingSession()
    with pytest.raises(RuntimeError, match="sha failed"):
        runtime.persist_sister_visura(session, document)
    assert not session.records


def test_recursive_jsonable_preserves_non_json_container():
    unchanged = (date(2026, 1, 1),)
    result = runtime._jsonable({1: [date(2026, 1, 2), {"tuple": unchanged}]})
    assert result["1"][0] == "2026-01-02"
    assert result["1"][1]["tuple"] is unchanged
