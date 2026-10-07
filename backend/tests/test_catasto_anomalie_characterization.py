from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.catasto_phase1 import (
    CatAnomalia,
    CatComune,
    CatImportBatch,
    CatParticella,
    CatUtenzaIrrigua,
)
from app.modules.catasto.routes import anomalie
from app.modules.catasto.services.anomalie_matching import score_comune_candidate
from app.schemas.catasto_phase1 import (
    CatAdeStatusScanRunInput,
    CatAnomaliaCfWizardApplyInput,
    CatAnomaliaComuneWizardApplyInput,
    CatAnomaliaParticellaWizardApplyInput,
)

WIZARDS = {
    "cf": ("VAL-02-cf_invalido", CatAnomaliaCfWizardApplyInput, anomalie.apply_cf_wizard),
    "comune": (
        "VAL-04-comune_invalido",
        CatAnomaliaComuneWizardApplyInput,
        anomalie.apply_comune_wizard,
    ),
    "particella": (
        "VAL-05-particella_assente",
        CatAnomaliaParticellaWizardApplyInput,
        anomalie.apply_particella_wizard,
    ),
}


@pytest.fixture
def database():
    engine = create_engine("sqlite://")
    tables = [
        model.__table__
        for model in (CatImportBatch, CatComune, CatParticella, CatUtenzaIrrigua, CatAnomalia)
    ]
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def wizard_case(database):
    batch = CatImportBatch(filename="characterization.xlsx", tipo="capacitas")
    comune = CatComune(nome_comune="Roma", codice_catastale="H501", cod_comune_capacitas=10)
    parcel = CatParticella(cod_comune_capacitas=10, nome_comune="Roma", foglio="1", particella="2")
    database.add_all([batch, comune, parcel])
    database.flush()
    utenza = CatUtenzaIrrigua(
        import_batch_id=batch.id,
        anno_campagna=2025,
        nome_comune="Roma",
        cod_comune_capacitas=10,
        foglio="1",
        particella="2",
        codice_fiscale="INVALID",
        anomalia_cf_invalido=True,
        anomalia_comune_invalido=True,
        anomalia_particella_assente=True,
    )
    database.add(utenza)
    database.flush()
    anomaly = CatAnomalia(
        utenza_id=utenza.id, tipo="VAL-02-cf_invalido", severita="error", status="aperta"
    )
    database.add(anomaly)
    database.commit()
    return SimpleNamespace(anomaly=anomaly, utenza=utenza, comune=comune, parcel=parcel)


def _wizard_request(kind, case, *, note=None):
    anomaly_type, schema, handler = WIZARDS[kind]
    case.anomaly.tipo = anomaly_type
    values = {
        "cf": {"codice_fiscale": "RSSMRA80A01H501U"},
        "comune": {"comune_id": case.comune.id},
        "particella": {"particella_id": case.parcel.id},
    }
    item = {"anomalia_id": case.anomaly.id, **values[kind], "note_operatore": note}
    return handler, schema(items=[item])


@pytest.mark.parametrize("kind", WIZARDS)
@pytest.mark.parametrize(
    "failure", ["missing_anomaly", "wrong_type", "no_utenza", "missing_utenza"]
)
def test_wizard_rejects_missing_or_incompatible_entities_without_commit(
    database, wizard_case, monkeypatch, kind, failure
):
    case = wizard_case
    handler, payload = _wizard_request(kind, case)
    identifier = case.anomaly.id
    expected = {
        "missing_anomaly": (404, f"Anomalia {identifier} not found"),
        "wrong_type": (
            409,
            f"Anomalia {identifier} is not supported by {kind.upper() if kind == 'cf' else kind} wizard",
        ),
        "no_utenza": (409, f"Anomalia {identifier} has no utenza linked"),
        "missing_utenza": (404, f"Utenza {case.utenza.id} not found"),
    }
    if failure == "missing_anomaly":
        database.delete(case.anomaly)
    if failure == "wrong_type":
        case.anomaly.tipo = "VAL-01-other"
    if failure == "no_utenza":
        case.anomaly.utenza_id = None
    database.commit()
    if failure == "missing_utenza":
        original_get = database.get

        def get_with_missing_utenza(model, identity):
            if model is CatUtenzaIrrigua:
                return None
            return original_get(model, identity)

        monkeypatch.setattr(database, "get", get_with_missing_utenza)
    commits = []
    event.listen(database, "after_commit", lambda session: commits.append(session))

    with pytest.raises(HTTPException) as error:
        handler(payload, db=database, current_user=SimpleNamespace(id=7))

    assert (error.value.status_code, error.value.detail) == expected[failure]
    assert commits == []
    assert case.utenza.codice_fiscale == "INVALID"
    assert case.utenza.anomalia_comune_invalido is True
    assert case.utenza.anomalia_particella_assente is True


@pytest.mark.parametrize("kind", WIZARDS)
def test_wizard_rejects_empty_requests(database, kind):
    _, schema, handler = WIZARDS[kind]
    with pytest.raises(HTTPException) as error:
        handler(schema(items=[]), db=database, current_user=SimpleNamespace(id=7))
    assert (error.value.status_code, error.value.detail) == (422, "No wizard items provided")


@pytest.mark.parametrize("kind", WIZARDS)
def test_duplicate_wizard_request_can_be_rolled_back_without_persisting_first_item(
    database, wizard_case, kind
):
    handler, payload = _wizard_request(kind, wizard_case)
    database.commit()
    payload.items.append(payload.items[0])
    commits = []
    event.listen(database, "after_commit", lambda session: commits.append(session))

    with pytest.raises(HTTPException) as error:
        handler(payload, db=database, current_user=SimpleNamespace(id=7))

    assert (error.value.status_code, error.value.detail) == (
        422,
        "Duplicate anomaly ids are not allowed in wizard apply",
    )
    assert commits == []
    database.rollback()
    assert wizard_case.anomaly.status == "aperta"
    assert wizard_case.utenza.codice_fiscale == "INVALID"
    assert wizard_case.utenza.comune_id is None
    assert wizard_case.utenza.particella_id is None


@pytest.mark.parametrize("kind", ["comune", "particella"])
def test_wizard_rejects_missing_target(database, wizard_case, kind):
    handler, payload = _wizard_request(kind, wizard_case)
    missing_id = uuid4()
    setattr(payload.items[0], f"{kind}_id", missing_id)
    database.commit()
    with pytest.raises(HTTPException) as error:
        handler(payload, db=database, current_user=SimpleNamespace(id=7))
    assert (error.value.status_code, error.value.detail) == (
        404,
        f"{kind.title()} {missing_id} not found",
    )
    assert wizard_case.anomaly.status == "aperta"


def test_particella_wizard_rejects_current_but_unrelated_parcel(database, wizard_case):
    handler, payload = _wizard_request("particella", wizard_case)
    wizard_case.parcel.foglio = "99"
    database.commit()
    with pytest.raises(HTTPException) as error:
        handler(payload, db=database, current_user=SimpleNamespace(id=7))
    assert (error.value.status_code, error.value.detail) == (
        409,
        f"Particella {wizard_case.parcel.id} is not a valid candidate for anomalia {wizard_case.anomaly.id}",
    )
    assert wizard_case.utenza.particella_id is None


@pytest.mark.parametrize("kind", WIZARDS)
@pytest.mark.parametrize("note", [None, "   ", "  Verificato  "])
def test_wizard_success_commits_once_and_only_closes_related_open_anomalies(
    database, wizard_case, kind, note
):
    handler, payload = _wizard_request(kind, wizard_case, note=note)
    unrelated = CatAnomalia(
        utenza_id=wizard_case.utenza.id, tipo="VAL-01-other", severita="info", status="aperta"
    )
    closed = CatAnomalia(
        utenza_id=wizard_case.utenza.id,
        tipo=wizard_case.anomaly.tipo,
        severita="error",
        status="chiusa",
        note_operatore="Preesistente",
    )
    database.add_all([unrelated, closed])
    database.commit()
    commits = []
    event.listen(database, "after_commit", lambda session: commits.append(session))

    result = handler(payload, db=database, current_user=SimpleNamespace(id=7))

    assert result.model_dump() == {"applied_count": 1, "updated_utenze": 1, "closed_anomalies": 1}
    assert len(commits) == 1
    defaults = {
        "cf": "Correzione CF tramite wizard anomalie",
        "comune": "Correzione comune tramite wizard anomalie",
        "particella": "Collegamento particella tramite wizard anomalie",
    }
    assert wizard_case.anomaly.note_operatore == (
        "Verificato" if note and note.strip() else defaults[kind]
    )
    assert wizard_case.anomaly.assigned_to == 7
    assert wizard_case.anomaly.status == "chiusa"
    assert unrelated.status == "aperta"
    assert closed.note_operatore == "Preesistente"


@pytest.mark.parametrize(
    ("source_code", "name", "legacy", "source_name", "expected"),
    [
        (None, "Roma", None, "", 0),
        (10, "Roma", None, "roma", 16),
        (20, "Roma", "Lazio", "lazio", 13),
        (30, "Roma", "Lazio", "roma", 14),
        (99, "Roma", "Lazio", "roma", 8),
        (None, "Roma", "Lazio", "rom", 4),
        (None, "Roma", "Lazio", "romacapitale", 4),
        (None, "Roma", "Lazio", "laz", 3),
        (None, "Roma", "Lazio", "laziomeridionale", 3),
        (None, "Roma", "Lazio", "milano", 0),
        (None, "Roma", None, "milano", 0),
        (None, "", None, "milano", 4),
        (None, "Roma", "Roma", "roma", 8),
        (None, "Roma Capitale", "Roma", "roma", 7),
    ],
)
def test_comune_score_preserves_code_weights_name_precedence_and_empty_name_fallback(
    source_code, name, legacy, source_name, expected
):
    row = CatComune(
        nome_comune=name,
        nome_comune_legacy=legacy,
        cod_comune_capacitas=10,
        codice_comune_formato_numerico=20,
        codice_comune_numerico_2017_2025=30,
    )
    assert score_comune_candidate(row, source_code, source_name) == expected


def test_comune_score_accumulates_all_matching_code_namespaces():
    row = CatComune(
        nome_comune=" Roma ",
        nome_comune_legacy="Roma",
        cod_comune_capacitas=10,
        codice_comune_formato_numerico=10,
        codice_comune_numerico_2017_2025=10,
    )
    assert score_comune_candidate(row, 10, "roma") == 28


def test_comune_candidates_keep_score_name_code_order_and_serialized_fields(database):
    rows = [
        CatComune(
            nome_comune="Roma",
            codice_catastale="H501",
            cod_comune_capacitas=3,
            codice_comune_formato_numerico=20,
            nome_comune_legacy="Urbe",
            sigla_provincia="RM",
        ),
        CatComune(
            nome_comune="Roma",
            codice_catastale="H502",
            cod_comune_capacitas=2,
            codice_comune_formato_numerico=20,
        ),
        CatComune(nome_comune="Milano", codice_catastale="F205", cod_comune_capacitas=20),
        CatComune(nome_comune="Torino", codice_catastale="L219", cod_comune_capacitas=99),
    ]
    database.add_all(rows)
    database.commit()
    candidates = anomalie._build_comune_candidates(
        database, CatAnomalia(dati_json={"cod_istat": 20}), CatUtenzaIrrigua(nome_comune="Roma")
    )
    assert [candidate.id for candidate in candidates] == [rows[1].id, rows[0].id, rows[2].id]
    assert [candidate.match_score for candidate in candidates] == [14, 14, 8]
    assert candidates[1].model_dump() == {
        "id": rows[0].id,
        "nome_comune": "Roma",
        "nome_comune_legacy": "Urbe",
        "codice_catastale": "H501",
        "cod_comune_capacitas": 3,
        "codice_comune_formato_numerico": 20,
        "codice_comune_numerico_2017_2025": None,
        "sigla_provincia": "RM",
        "match_score": 14,
    }


def test_comune_candidates_apply_alphabetic_500_row_limit_before_scoring(database):
    database.add_all(
        [
            CatComune(
                nome_comune=f"Comune {index:03}",
                codice_catastale=f"{index:04}",
                cod_comune_capacitas=index,
            )
            for index in range(500)
        ]
    )
    database.add(CatComune(nome_comune="ZZZ", codice_catastale="ZZZZ", cod_comune_capacitas=999))
    database.commit()
    assert (
        anomalie._build_comune_candidates(
            database, CatAnomalia(dati_json={"cod_istat": 999}), CatUtenzaIrrigua(nome_comune="ZZZ")
        )
        == []
    )


@pytest.mark.parametrize("payload", [None, {}, {"cod_istat": None}, {"cod_istat": "invalid"}])
def test_source_code_falls_back_to_utenza_and_normalization_preserves_empty(payload):
    assert (
        anomalie._extract_source_comune_code(
            CatAnomalia(dati_json=payload), CatUtenzaIrrigua(cod_comune_capacitas=10)
        )
        == 10
    )
    assert anomalie._normalize_lookup_text(None) == ""
    assert anomalie._normalize_lookup_text(" Róma - 1 ") == "rma1"


@pytest.mark.parametrize("comune_name", [None, " roma "])
def test_particella_candidates_fall_back_to_name_or_allow_any_comune(database, comune_name):
    parcels = [
        CatParticella(cod_comune_capacitas=10, nome_comune="Roma", foglio="1", particella="2"),
        CatParticella(
            cod_comune_capacitas=20,
            nome_comune="Roma",
            foglio="1",
            particella="2",
            sezione_catastale="B",
            subalterno="3",
        ),
        CatParticella(cod_comune_capacitas=30, nome_comune="Milano", foglio="1", particella="2"),
    ]
    database.add_all(parcels)
    database.commit()
    utenza = CatUtenzaIrrigua(nome_comune=comune_name, foglio="1", particella="2")

    candidates = anomalie._build_particella_candidates(database, utenza)

    assert [candidate.match_score for candidate in candidates] == (
        [6, 6, 0] if comune_name is None else [6, 0]
    )
    assert candidates[-1].id == parcels[1].id
    assert all(not candidate.ha_anagrafica for candidate in candidates)
    utenza.foglio = "99"
    assert anomalie._build_particella_candidates(database, utenza) == []


def test_summary_promotes_severity_and_fills_initially_empty_label(database):
    database.add_all(
        [
            CatAnomalia(tipo="", severita="info", descrizione=""),
            CatAnomalia(tipo="", severita="warning", descrizione="Nuova descrizione"),
        ]
    )
    database.commit()

    result = anomalie.anomalie_summary(
        status_filter=None, severita=None, anno=None, distretto=None, db=database, _=None
    )

    assert result.model_dump() == {
        "total": 2,
        "buckets": [{"tipo": "", "label": "Nuova descrizione", "severita": "warning", "count": 2}],
    }


@pytest.mark.parametrize(("limit", "expected_limit"), [(None, None), (0, 1), (-5, 1), (3, 3)])
@pytest.mark.parametrize("reasons", [None, [], ["missing_particella"]])
def test_ade_run_preserves_service_arguments_and_response(
    database, monkeypatch, limit, expected_limit, reasons
):
    calls = []
    batch_id = uuid4()

    def create_batch(session, **kwargs):
        calls.append((session, kwargs))
        return {"batch_id": batch_id, "created": 3, "skipped": 1}

    monkeypatch.setattr(anomalie, "create_ade_status_scan_batch", create_batch)
    result = anomalie.run_ade_status_scan(
        CatAdeStatusScanRunInput(limit=limit, match_reasons=reasons),
        db=database,
        current_user=SimpleNamespace(id=7),
    )
    assert calls == [
        (database, {"user_id": 7, "limit": expected_limit, "match_reasons": reasons or None})
    ]
    assert result.model_dump() == {"batch_id": batch_id, "created": 3, "skipped": 1}
