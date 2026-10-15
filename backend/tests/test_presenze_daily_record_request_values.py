"""Characterization of the request-field resolution in the daily record serializers.

Both ``_serialize_daily_record`` (detail/API) and ``_serialize_daily_record_matrix``
(matrix and GATE giornaliere snapshot) resolve ``request_type``,
``request_description``, ``request_status`` and ``request_authorized_by`` the
same way: the stored column wins when truthy, otherwise the value is derived
from ``raw_payload_json`` only when it is a dict, otherwise ``None``.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PRESENZE_CONTRACT_KIND_OPERAIO,
    PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO,
    PresenzeCollaborator,
    PresenzeDailyRecord,
)
from app.modules.presenze.router.helpers import daily_records

REQUEST_KEYS = (
    "request_type",
    "request_description",
    "request_status",
    "request_authorized_by",
)

PAYLOAD_WITH_REQUEST = {
    "detail_requests": [
        {
            "Tipo": "Ferie",
            "Descrizione": "Ferie annuali",
            "Stato": "Approvata",
            "Autorizzato da": "ROSSI MARIO",
        }
    ]
}

RESOLVED_FROM_PAYLOAD = {
    "request_type": "Ferie",
    "request_description": "Ferie annuali",
    "request_status": "Approvata",
    "request_authorized_by": "ROSSI MARIO",
}

STORED_VALUES = {
    "request_type": "Permesso",
    "request_description": "Permesso retribuito",
    "request_status": "In attesa",
    "request_authorized_by": "BIANCHI LUCA",
}

NONE_VALUES = dict.fromkeys(REQUEST_KEYS)


def _serialize_detail(db: Session, record: PresenzeDailyRecord):
    return daily_records._serialize_daily_record(db, record, punches=[])


def _serialize_matrix(_db: Session, record: PresenzeDailyRecord):
    return daily_records._serialize_daily_record_matrix(record)


SERIALIZERS = pytest.mark.parametrize(
    "serialize",
    [_serialize_detail, _serialize_matrix],
    ids=["detail", "matrix"],
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            ApplicationUser.__table__,
            *(
                table
                for name, table in Base.metadata.tables.items()
                if name.startswith("presenze_")
            ),
        ],
    )
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with session_factory() as session:
        yield session
    engine.dispose()


def _persist_record(
    db: Session, *, raw_payload_json, work_date: date = date(2026, 6, 3), **request_values
):
    collaborator = PresenzeCollaborator(
        employee_code="117", company_code="53", name="DESCHINO GIANNI"
    )
    db.add(collaborator)
    db.flush()
    record = PresenzeDailyRecord(
        collaborator_id=collaborator.id,
        work_date=work_date,
        raw_payload_json=raw_payload_json,
        **request_values,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _request_values(serialized) -> dict[str, str | None]:
    return {key: getattr(serialized, key) for key in REQUEST_KEYS}


@SERIALIZERS
def test_a_stored_request_values_win_over_dict_payload(db, serialize) -> None:
    record = _persist_record(db, raw_payload_json=PAYLOAD_WITH_REQUEST, **STORED_VALUES)

    assert _request_values(serialize(db, record)) == STORED_VALUES


@SERIALIZERS
def test_b_missing_stored_values_resolve_from_dict_payload(db, serialize) -> None:
    record = _persist_record(db, raw_payload_json=PAYLOAD_WITH_REQUEST)

    assert _request_values(serialize(db, record)) == RESOLVED_FROM_PAYLOAD


@SERIALIZERS
def test_c_empty_stored_values_are_falsy_and_resolve_from_dict_payload(db, serialize) -> None:
    record = _persist_record(
        db, raw_payload_json=PAYLOAD_WITH_REQUEST, **dict.fromkeys(REQUEST_KEYS, "")
    )

    assert _request_values(serialize(db, record)) == RESOLVED_FROM_PAYLOAD


@SERIALIZERS
@pytest.mark.parametrize("raw_payload_json", [None, ["Ferie"]], ids=["none", "list"])
def test_d_empty_stored_values_with_non_dict_payload_become_none(
    db, serialize, raw_payload_json
) -> None:
    record = _persist_record(
        db, raw_payload_json=raw_payload_json, **dict.fromkeys(REQUEST_KEYS, "")
    )

    assert _request_values(serialize(db, record)) == NONE_VALUES


@SERIALIZERS
def test_e_dict_payload_without_requests_resolves_to_none(db, serialize) -> None:
    record = _persist_record(db, raw_payload_json={"detail_requests": [{}]})

    assert _request_values(serialize(db, record)) == NONE_VALUES


@SERIALIZERS
def test_f_request_keys_override_record_columns_in_place(db, serialize, monkeypatch) -> None:
    captured: list[dict[str, object]] = []

    class _RecordingResponse:
        @staticmethod
        def model_validate(value):
            captured.append(value)
            return value

    monkeypatch.setattr(daily_records, "PresenzeDailyRecordResponse", _RecordingResponse)
    record = _persist_record(db, raw_payload_json=PAYLOAD_WITH_REQUEST, request_type="Permesso")

    serialize(db, record)

    record_keys = list(record.__dict__)
    keys = list(captured[0])
    assert set(REQUEST_KEYS) <= set(record_keys)
    assert keys[: len(record_keys)] == record_keys
    assert {key: captured[0][key] for key in REQUEST_KEYS} == {
        **RESOLVED_FROM_PAYLOAD,
        "request_type": "Permesso",
    }


@SERIALIZERS
def test_g_each_field_resolves_independently(db, serialize) -> None:
    record = _persist_record(
        db,
        raw_payload_json=PAYLOAD_WITH_REQUEST,
        request_type=None,
        request_description="Descrizione salvata",
        request_status="",
        request_authorized_by="VERDI ANNA",
    )

    assert _request_values(serialize(db, record)) == {
        "request_type": "Ferie",
        "request_description": "Descrizione salvata",
        "request_status": "Approvata",
        "request_authorized_by": "VERDI ANNA",
    }


def test_detail_and_matrix_serializers_agree_on_request_values(db) -> None:
    record = _persist_record(db, raw_payload_json=PAYLOAD_WITH_REQUEST, request_status="Respinta")

    detail = _request_values(_serialize_detail(db, record))
    matrix = _request_values(_serialize_matrix(db, record))

    assert detail == matrix == {**RESOLVED_FROM_PAYLOAD, "request_status": "Respinta"}


def test_catasto_saturday_without_work_or_absence_coverage_is_not_counted(db) -> None:
    collaborator = PresenzeCollaborator(
        employee_code="118",
        company_code="53",
        name="OPERAIO CATASTO",
        contract_kind=PRESENZE_CONTRACT_KIND_OPERAIO,
        operai_group=PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO,
    )
    db.add(collaborator)
    db.flush()
    saturday = PresenzeDailyRecord(
        id=uuid.uuid4(),
        collaborator_id=collaborator.id,
        work_date=date(2026, 6, 6),
        resolved_absence_cause="Malattia",
        justified_minutes=420,
        absence_minutes=420,
    )
    db.add(saturday)
    db.commit()

    counts = daily_records._build_catasto_saturday_coverage_counts(
        db, [saturday], {collaborator.id: collaborator}
    )

    assert counts == {(collaborator.id, 2026, 6): 0}


def _install_request_resolvers(monkeypatch, make_resolver) -> None:
    """Replace the four request resolvers wherever the serializers look them up."""
    resolvers = {key: make_resolver(key) for key in REQUEST_KEYS}
    for key, resolver in resolvers.items():
        monkeypatch.setattr(daily_records, f"resolve_{key}", resolver)
    if hasattr(daily_records, "_REQUEST_FIELD_RESOLVERS"):
        monkeypatch.setattr(
            daily_records,
            "_REQUEST_FIELD_RESOLVERS",
            tuple((key, resolvers[key]) for key in REQUEST_KEYS),
        )


def _raising_resolver(key: str):
    def resolver(_raw_payload):
        raise AssertionError(f"resolver for {key} must not be called")

    return resolver


@SERIALIZERS
def test_h_truthy_stored_values_never_call_the_resolvers(db, serialize, monkeypatch) -> None:
    record = _persist_record(db, raw_payload_json=PAYLOAD_WITH_REQUEST, **STORED_VALUES)
    _install_request_resolvers(monkeypatch, _raising_resolver)

    assert _request_values(serialize(db, record)) == STORED_VALUES


@SERIALIZERS
@pytest.mark.parametrize("raw_payload_json", [None, ["Ferie"]], ids=["none", "list"])
def test_i_non_dict_payload_never_calls_the_resolvers(
    db, serialize, monkeypatch, raw_payload_json
) -> None:
    record = _persist_record(
        db, raw_payload_json=raw_payload_json, **dict.fromkeys(REQUEST_KEYS, "")
    )
    _install_request_resolvers(monkeypatch, _raising_resolver)

    assert _request_values(serialize(db, record)) == NONE_VALUES


@SERIALIZERS
def test_j_resolvers_run_once_per_falsy_field_with_dict_payload(db, serialize, monkeypatch) -> None:
    calls: list[str] = []

    def recording_resolver(key: str):
        def resolver(raw_payload):
            assert raw_payload == PAYLOAD_WITH_REQUEST
            calls.append(key)
            return f"resolved-{key}"

        return resolver

    record = _persist_record(
        db,
        raw_payload_json=PAYLOAD_WITH_REQUEST,
        request_type="Permesso",
        request_description="",
        request_status=None,
        request_authorized_by="VERDI ANNA",
    )
    _install_request_resolvers(monkeypatch, recording_resolver)

    assert _request_values(serialize(db, record)) == {
        "request_type": "Permesso",
        "request_description": "resolved-request_description",
        "request_status": "resolved-request_status",
        "request_authorized_by": "VERDI ANNA",
    }
    assert calls == ["request_description", "request_status"]
