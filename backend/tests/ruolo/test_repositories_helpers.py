from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.catasto import CatastoParcel
from app.models.catasto_phase1 import CatUtenzaIrrigua
from app.modules.ruolo import repositories as repo
from app.modules.utenze.models import AnagraficaCompany


class _FakeMappingsResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def mappings(self) -> "_FakeMappingsResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return self._rows


class _FakePostgresDb:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def get_bind(self) -> object:
        return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    def execute(self, *_args, **_kwargs) -> _FakeMappingsResult:
        return _FakeMappingsResult(self._rows)


class _FakeRowsResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class _FakeScalarsResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class _FakeSqliteDb:
    def __init__(self, *, execute_rows: list[object] | None = None, scalar_values: list[object] | None = None) -> None:
        self.execute_rows = execute_rows or []
        self.scalar_values = scalar_values or []

    def get_bind(self) -> object:
        return SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))

    def execute(self, *_args, **_kwargs) -> _FakeRowsResult:
        return _FakeRowsResult(self.execute_rows)

    def scalar(self, *_args, **_kwargs) -> object:
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, *_args, **_kwargs) -> _FakeScalarsResult:
        return _FakeScalarsResult(self.execute_rows)


def test_repository_amount_and_partite_helpers_cover_edge_cases() -> None:
    assert repo._parse_incass_amount(None) == 0.0
    assert repo._parse_incass_amount(Decimal("12.345")) == 12.35
    assert repo._parse_incass_amount("") == 0.0
    assert repo._parse_incass_amount("1.234,56") == 1234.56
    assert repo._parse_incass_amount("1,234.56") == 1234.56
    assert repo._parse_incass_amount("1,5") == 1.5
    assert repo._parse_incass_amount("bad") == 0.0

    assert repo._iter_incass_partite(None) == []
    assert repo._iter_incass_partite([]) == []
    assert repo._iter_incass_partite({}) == []
    assert repo._iter_incass_partite({"partitario": []}) == []
    assert repo._iter_incass_partite({"partitario": {"partite": "bad"}}) == []
    assert repo._iter_incass_partite({"partitario": {"partite": [{"ok": True}, "bad"]}}) == [{"ok": True}]


def test_repository_calculation_classifiers_cover_decision_tree() -> None:
    assert repo._compute_gaia_amount(None, 1) == 0.0
    assert repo._compute_gaia_amount(100, None) == 0.0
    assert repo._compute_gaia_amount(Decimal("100.00"), Decimal("0.10")) == 10.0
    assert repo._normalize_capacitas_check_comune_name("SILI'*ORISTANO") == "ORISTANO"
    assert repo._normalize_capacitas_check_comune_name("San Nicolo D'Arcidano") == "SAN NICOLO ARCIDANO"
    assert repo._normalize_capacitas_check_comune_name(None) == "N/D"

    assert repo._classify_capacitas_mismatch(
        status="only_in_capacitas",
        threshold=0.01,
        ruolo_0648=0,
        ruolo_0985=0,
        gaia_0648=0,
        gaia_0985=0,
        excel_0648=0,
        excel_0985=0,
    ) == "problema_ruolo"
    assert repo._classify_capacitas_mismatch(
        status="only_in_ruolo",
        threshold=0.01,
        ruolo_0648=0,
        ruolo_0985=0,
        gaia_0648=0,
        gaia_0985=0,
        excel_0648=0,
        excel_0985=0,
    ) == "problema_snapshot_excel"
    assert repo._classify_capacitas_mismatch(
        status="matched",
        threshold=0.01,
        ruolo_0648=0,
        ruolo_0985=0,
        gaia_0648=0,
        gaia_0985=0,
        excel_0648=0,
        excel_0985=0,
    ) == "allineato"
    assert repo._classify_capacitas_mismatch(
        status="amount_mismatch",
        threshold=0.01,
        ruolo_0648=50,
        ruolo_0985=0,
        gaia_0648=100,
        gaia_0985=0,
        excel_0648=100,
        excel_0985=0,
    ) == "problema_ruolo"
    assert repo._classify_capacitas_mismatch(
        status="amount_mismatch",
        threshold=0.01,
        ruolo_0648=100,
        ruolo_0985=0,
        gaia_0648=50,
        gaia_0985=0,
        excel_0648=100,
        excel_0985=0,
    ) == "problema_ricalcolo_gaia"
    assert repo._classify_capacitas_mismatch(
        status="amount_mismatch",
        threshold=0.01,
        ruolo_0648=100,
        ruolo_0985=0,
        gaia_0648=100,
        gaia_0985=0,
        excel_0648=50,
        excel_0985=0,
    ) == "problema_snapshot_excel"
    assert repo._classify_capacitas_mismatch(
        status="amount_mismatch",
        threshold=0.01,
        ruolo_0648=100,
        ruolo_0985=0,
        gaia_0648=80,
        gaia_0985=0,
        excel_0648=40,
        excel_0985=0,
    ) == "problema_snapshot_excel"
    assert repo._classify_capacitas_mismatch(
        status="amount_mismatch",
        threshold=0.01,
        ruolo_0648=100,
        ruolo_0985=0,
        gaia_0648=40,
        gaia_0985=0,
        excel_0648=80,
        excel_0985=0,
    ) == "problema_ricalcolo_gaia"
    assert repo._classify_capacitas_mismatch(
        status="amount_mismatch",
        threshold=0.01,
        ruolo_0648=10,
        ruolo_0985=0,
        gaia_0648=0,
        gaia_0985=0,
        excel_0648=20,
        excel_0985=0,
    ) == "problema_snapshot_excel"


def test_repository_postgres_ruolo_loaders_with_fake_db() -> None:
    by_tax, missing_tax = repo._load_ruolo_incass_by_tax(
        _FakePostgresDb(
            [
                {
                    "tax_code": " rssmra80a01h501z ",
                    "display_name": "ROSSI MARIO",
                    "amount_0648": 10,
                    "amount_0985": 5,
                    "amount_0668": 2,
                },
                {
                    "tax_code": "",
                    "display_name": "MISSING",
                    "amount_0648": 1,
                    "amount_0985": 1,
                    "amount_0668": 1,
                },
            ]
        ),
        anno=2025,
    )

    assert missing_tax == 1
    assert by_tax["RSSMRA80A01H501Z"]["amount_0648"] == 10.0
    assert by_tax["RSSMRA80A01H501Z"]["amount_0985"] == 5.0
    assert by_tax["RSSMRA80A01H501Z"]["amount_0668"] == 2.0

    by_comune = repo._load_ruolo_incass_by_comune(
        _FakePostgresDb(
            [
                {"comune_nome": "ORISTANO", "ruolo_0648": 10, "ruolo_0985": 5},
                {"comune_nome": "CABRAS", "ruolo_0648": None, "ruolo_0985": 2},
            ]
        ),
        anno=2025,
    )

    assert by_comune == {
        "ORISTANO": {"comune_nome": "ORISTANO", "ruolo_0648": 10.0, "ruolo_0985": 5.0},
        "CABRAS": {"comune_nome": "CABRAS", "ruolo_0648": 0.0, "ruolo_0985": 2.0},
    }


def test_repository_capacitas_check_skips_matched_and_calculates_anomaly_share(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        repo,
        "_load_ruolo_incass_by_tax",
        lambda _db, *, anno: (
            {
                "MATCHED": {
                    "tax_code": "MATCHED",
                    "display_name": "MATCHED",
                    "amount_0648": 10.0,
                    "amount_0985": 0.0,
                    "amount_0668": 0.0,
                },
                "ANOMALY": {
                    "tax_code": "ANOMALY",
                    "display_name": "ANOMALY",
                    "amount_0648": 10.0,
                    "amount_0985": 0.0,
                    "amount_0668": 0.0,
                },
            },
            0,
        ),
    )
    monkeypatch.setattr(
        repo,
        "_load_capacitas_snapshot_by_tax",
        lambda _db, *, anno: (
            {
                "MATCHED": {
                    "tax_code": "MATCHED",
                    "display_name": "MATCHED",
                    "excel_0648": 10.0,
                    "excel_0985": 0.0,
                    "gaia_0648": 10.0,
                    "gaia_0985": 0.0,
                    "anomalous_rows_count": 0,
                    "clean_rows_count": 1,
                    "excel_total_anomalous_rows": 0.0,
                    "gaia_total_anomalous_rows": 0.0,
                },
                "ANOMALY": {
                    "tax_code": "ANOMALY",
                    "display_name": "ANOMALY",
                    "excel_0648": 30.0,
                    "excel_0985": 0.0,
                    "gaia_0648": 15.0,
                    "gaia_0985": 0.0,
                    "anomalous_rows_count": 1,
                    "clean_rows_count": 0,
                    "excel_total_anomalous_rows": 30.0,
                    "gaia_total_anomalous_rows": 15.0,
                },
            },
            0,
            uuid4(),
        ),
    )

    result = repo.get_capacitas_check(object(), anno=2025)

    assert [item["tax_code"] for item in result["items"]] == ["ANOMALY"]
    assert result["items"][0]["anomaly_driven_case"] is True


def test_repository_sqlite_ruolo_loader_merges_tax_rows_and_missing_codes() -> None:
    rows = [
        SimpleNamespace(codice_fiscale=None, partita_iva=None, display_name="MISSING", raw_detail_json={}),
        SimpleNamespace(
            codice_fiscale="RSSMRA80A01H501Z",
            partita_iva=None,
            display_name=None,
            raw_detail_json={"partitario": {"partite": [{"importo_0648_euro": "1,00"}]}},
        ),
        SimpleNamespace(
            codice_fiscale="RSSMRA80A01H501Z",
            partita_iva=None,
            display_name="ROSSI MARIO",
            raw_detail_json={
                "partitario": {
                    "partite": [
                        {
                            "importo_0648_euro": "2,00",
                            "importo_0985_euro": "3,00",
                            "importo_0668_euro": "4,00",
                        }
                    ]
                }
            },
        ),
    ]

    by_tax, missing_tax = repo._load_ruolo_incass_by_tax(_FakeSqliteDb(execute_rows=rows), anno=2025)

    assert missing_tax == 1
    assert by_tax["RSSMRA80A01H501Z"]["display_name"] == "ROSSI MARIO"
    assert by_tax["RSSMRA80A01H501Z"]["amount_0648"] == 3.0
    assert by_tax["RSSMRA80A01H501Z"]["amount_0985"] == 3.0
    assert by_tax["RSSMRA80A01H501Z"]["amount_0668"] == 4.0


def test_repository_capacitas_snapshot_helpers_handle_missing_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo, "active_capacitas_batch_id", lambda _db, _anno: None)

    assert repo._load_capacitas_snapshot_by_tax(_FakeSqliteDb(), anno=2025) == ({}, 0, None)
    assert repo._load_capacitas_snapshot_by_comune(_FakeSqliteDb(), anno=2025) == ({}, None)
    assert repo.get_capacitas_calculation_detail(_FakeSqliteDb(), anno=2025, tax_code="") is None
    assert repo.get_capacitas_calculation_detail(_FakeSqliteDb(), anno=2025, tax_code="RSSMRA80A01H501Z") is None


def test_repository_capacitas_snapshot_by_tax_merges_rows_and_missing_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    active_batch_id = uuid4()
    monkeypatch.setattr(repo, "active_capacitas_batch_id", lambda _db, _anno: active_batch_id)
    rows = [
        SimpleNamespace(
            codice_fiscale=None,
            denominazione="MISSING",
            importo_0648=Decimal("1"),
            importo_0985=Decimal("1"),
            imponibile_sf=Decimal("10"),
            aliquota_0648=Decimal("0.1"),
            aliquota_0985=Decimal("0.1"),
            anomalia_imponibile=False,
            anomalia_importi=False,
        ),
        SimpleNamespace(
            codice_fiscale="RSSMRA80A01H501Z",
            denominazione=None,
            importo_0648=None,
            importo_0985=Decimal("2"),
            imponibile_sf=None,
            aliquota_0648=Decimal("0.1"),
            aliquota_0985=None,
            anomalia_imponibile=True,
            anomalia_importi=False,
        ),
        SimpleNamespace(
            codice_fiscale="RSSMRA80A01H501Z",
            denominazione="ROSSI MARIO",
            importo_0648=Decimal("3"),
            importo_0985=Decimal("4"),
            imponibile_sf=Decimal("100"),
            aliquota_0648=Decimal("0.1"),
            aliquota_0985=Decimal("0.2"),
            anomalia_imponibile=False,
            anomalia_importi=False,
        ),
    ]

    snapshot, missing_tax, returned_batch_id = repo._load_capacitas_snapshot_by_tax(
        _FakeSqliteDb(execute_rows=rows),
        anno=2025,
    )

    assert missing_tax == 1
    assert returned_batch_id == active_batch_id
    assert snapshot["RSSMRA80A01H501Z"]["display_name"] == "ROSSI MARIO"
    assert snapshot["RSSMRA80A01H501Z"]["excel_0648"] == 3.0
    assert snapshot["RSSMRA80A01H501Z"]["excel_0985"] == 6.0
    assert snapshot["RSSMRA80A01H501Z"]["gaia_0648"] == 10.0
    assert snapshot["RSSMRA80A01H501Z"]["gaia_0985"] == 20.0
    assert snapshot["RSSMRA80A01H501Z"]["anomalous_rows_count"] == 1
    assert snapshot["RSSMRA80A01H501Z"]["clean_rows_count"] == 1


def test_repository_list_and_history_filters_build_queries() -> None:
    parcel_id = uuid4()
    parcel = CatastoParcel(
        id=parcel_id,
        comune_codice="A357",
        comune_nome="ARBOREA",
        foglio="1",
        particella="2",
        subalterno="A",
        valid_from=2025,
        source="ruolo_import",
    )
    fake_db = _FakeSqliteDb(execute_rows=[parcel], scalar_values=[1])

    jobs, total = repo.list_jobs(fake_db, anno=2025)
    assert jobs == [parcel]
    assert total == 1
    assert repo.search_particelle(
        fake_db,
        foglio="1",
        particella="2",
        comune="Arborea",
        unmatched_only=True,
    ) == ([parcel], 0)
    assert repo.get_catasto_parcel_history(
        fake_db,
        comune_codice="A357",
        foglio="1",
        particella="2",
        subalterno="A",
    ) == [parcel]


def test_repository_subject_display_name_uses_company_fallback() -> None:
    company = AnagraficaCompany(
        subject_id=uuid4(),
        ragione_sociale="AZIENDA AGRICOLA SRL",
        partita_iva="01234567890",
    )

    class FakeDb:
        def __init__(self) -> None:
            self.values = [None, None, None, company]

        def scalar(self, _statement):
            return self.values.pop(0)

    db = FakeDb()

    assert repo._get_subject_display_name(db, None) is None
    assert repo._get_subject_display_name(db, uuid4()) is None
    assert repo._get_subject_display_name(db, company.subject_id) == "AZIENDA AGRICOLA SRL"
