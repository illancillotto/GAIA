from __future__ import annotations

import uuid
from collections import Counter
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import materialize_ruolo_from_incass as _MODULE


class _ScalarResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values

    def first(self) -> object | None:
        return self._values[0] if self._values else None


class _ExecuteResult:
    def __init__(
        self,
        *,
        rows: list[object] | None = None,
        rowcounts: list[int] | None = None,
    ) -> None:
        self._rows = rows or []
        self._rowcounts = rowcounts or [0]
        self._rowcount_index = 0

    @property
    def rowcount(self) -> int:
        index = min(self._rowcount_index, len(self._rowcounts) - 1)
        value = self._rowcounts[index]
        self._rowcount_index += 1
        return value

    def all(self) -> list[object]:
        return self._rows


class _FakeDb:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0
        self.closed = False
        self.execute_results: list[_ExecuteResult] = []
        self.scalar_values: list[object] = []
        self.scalars_values: list[list[object]] = []
        self.get_values: list[object | None] = []

    def add(self, item: object) -> None:
        self.added.append(item)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def flush(self) -> None:
        self.flushes += 1

    def close(self) -> None:
        self.closed = True

    def scalar(self, statement: object) -> object:
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement: object) -> _ScalarResult:
        values = self.scalars_values.pop(0) if self.scalars_values else []
        return _ScalarResult(values)

    def execute(self, statement: object, params: object | None = None) -> _ExecuteResult:
        if self.execute_results:
            return self.execute_results.pop(0)
        return _ExecuteResult()

    def get(self, model: object, object_id: object) -> object | None:
        return self.get_values.pop(0) if self.get_values else None

    def begin_nested(self) -> "_FakeDb":
        return self

    def __enter__(self) -> "_FakeDb":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


def test_to_decimal_preserves_parser_decimal_points_and_parses_italian_amounts() -> None:
    assert _MODULE._to_decimal(None) is None
    assert _MODULE._to_decimal("") is None
    assert _MODULE._to_decimal("bad") is None
    assert _MODULE._to_decimal("18.4994") == Decimal("18.4994")
    assert _MODULE._to_decimal("0.9208") == Decimal("0.9208")
    assert _MODULE._to_decimal("184994") == Decimal("184994")
    assert _MODULE._to_decimal("675,28") == Decimal("675.28")
    assert _MODULE._to_decimal("1.808,94") == Decimal("1808.94")


def test_parse_args_accepts_reparse_replace_and_rejects_invalid_combinations(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "materialize",
            "--from-year",
            "2019",
            "--to-year",
            "2024",
            "--replace-year",
            "--reparse-partitario",
            "--apply",
            "--commit-every",
            "1",
            "--purge-batch-size",
            "2000",
            "--skip-catasto",
        ],
    )

    args = _MODULE.parse_args()

    assert args.from_year == 2019
    assert args.to_year == 2024
    assert args.replace_year is True
    assert args.reparse_partitario is True
    assert args.apply is True
    assert args.commit_every == 1
    assert args.purge_batch_size == 2000
    assert args.skip_catasto is True

    monkeypatch.setattr(
        "sys.argv",
        ["materialize", "--from-year", "2019", "--to-year", "2019", "--purge-only"],
    )
    with pytest.raises(SystemExit):
        _MODULE.parse_args()

    monkeypatch.setattr(
        "sys.argv",
        [
            "materialize",
            "--from-year",
            "2019",
            "--to-year",
            "2019",
            "--replace-year",
            "--purge-only",
            "--rebuild-only",
        ],
    )
    with pytest.raises(SystemExit):
        _MODULE.parse_args()


def test_configure_database_url_for_host_handles_env_file_and_fallback(monkeypatch, tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql://user:pass@postgres:5432/gaia\n", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(_MODULE, "REPO_ROOT", tmp_path)

    class FakePath:
        def __init__(self, value: str) -> None:
            self.value = value

        def exists(self) -> bool:
            return False

    monkeypatch.setattr(_MODULE, "Path", FakePath)

    _MODULE._configure_database_url_for_host()

    assert "127.0.0.1:5434" in str(_MODULE.os.environ["DATABASE_URL"])


def test_import_bootstrap_fallback_backend_path_and_no_database_url(monkeypatch, tmp_path) -> None:
    fake_project = tmp_path / "project"
    fake_backend = fake_project / "backend"
    (fake_backend / "app").mkdir(parents=True)
    fake_script = fake_project / "other" / "scripts" / "materialize_ruolo_from_incass.py"
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text("", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    source = Path(_MODULE.__file__).read_text(encoding="utf-8").splitlines()
    bootstrap_source = "\n".join(source[:52])
    namespace = {"__file__": str(fake_script), "__name__": "materialize_bootstrap_probe"}

    exec(compile(bootstrap_source, _MODULE.__file__, "exec"), namespace)

    assert namespace["BACKEND_ROOT"] == fake_backend
    assert namespace["REPO_ROOT"] == fake_project
    assert str(fake_backend) in namespace["sys"].path


def test_configure_database_url_for_host_keeps_non_postgres_and_ignores_invalid(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(_MODULE, "REPO_ROOT", Path("/tmp/gaia-env-file-that-does-not-exist"))
    _MODULE._configure_database_url_for_host()
    assert "DATABASE_URL" not in _MODULE.os.environ

    monkeypatch.setenv("DATABASE_URL", "not a url")
    _MODULE._configure_database_url_for_host()
    assert _MODULE.os.environ["DATABASE_URL"] == "not a url"

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5433/gaia")
    _MODULE._configure_database_url_for_host()
    assert _MODULE.os.environ["DATABASE_URL"] == "postgresql://user:pass@localhost:5433/gaia"


def test_configure_database_url_for_host_keeps_postgres_inside_docker(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@postgres:5432/gaia")

    class FakePath:
        def __init__(self, value: str) -> None:
            self.value = value

        def exists(self) -> bool:
            return self.value == "/.dockerenv"

    monkeypatch.setattr(_MODULE, "Path", FakePath)

    _MODULE._configure_database_url_for_host()

    assert _MODULE.os.environ["DATABASE_URL"] == "postgresql://user:pass@postgres:5432/gaia"


def test_extract_partite_uses_stored_payload_unless_reparse_is_forced(monkeypatch) -> None:
    stored_partita = {"codice_partita": "stored"}
    reparsed_partita = {"codice_partita": "reparsed"}

    def fake_parse(source: str, *, avviso: str) -> SimpleNamespace:
        assert source == "<pre>raw partitario</pre>"
        assert avviso == "0123"
        parsed_model = SimpleNamespace(model_dump=lambda mode: reparsed_partita)
        return SimpleNamespace(partite=[parsed_model])

    monkeypatch.setattr(_MODULE, "parse_incass_partitario_dialog", fake_parse)
    payload = {
        "partitario": {
            "avviso": "0123",
            "raw_html": "<pre>raw partitario</pre>",
            "partite": [stored_partita],
        }
    }

    assert _MODULE._extract_partite(payload) == [stored_partita]
    assert _MODULE._extract_partite(payload, force_reparse=True) == [reparsed_partita]


def test_extract_partite_falls_back_to_stored_payload_when_reparse_has_no_partite(monkeypatch) -> None:
    stored_partita = {"codice_partita": "stored"}
    monkeypatch.setattr(
        _MODULE,
        "parse_incass_partitario_dialog",
        lambda source, *, avviso: SimpleNamespace(partite=[]),
    )

    payload = {
        "partitario": {
            "raw_html": "<pre>raw partitario</pre>",
            "partite": [stored_partita],
        }
    }

    assert _MODULE._extract_partite(payload, force_reparse=True) == [stored_partita]


def test_extract_partite_handles_payload_variants(monkeypatch) -> None:
    parsed_partita = {"codice_partita": "parsed"}
    monkeypatch.setattr(
        _MODULE,
        "parse_incass_partitario_dialog",
        lambda source, *, avviso: SimpleNamespace(
            partite=[SimpleNamespace(model_dump=lambda mode: parsed_partita)]
        ),
    )

    assert _MODULE._extract_partite({"partitario": {"info_text": "raw"}}) == [parsed_partita]
    assert _MODULE._extract_partite({"partite": [{"ok": True}, "bad"]}) == [{"ok": True}]
    assert _MODULE._extract_partite({"partitario": {"partite": "bad"}}) == []
    assert _MODULE._extract_partite({}) == []


def test_normalizers_and_numeric_guards_cover_historical_parser_cleanup() -> None:
    stats: Counter[str] = Counter()

    assert _MODULE._normalize_comune(" SILI`*ORISTANO ; extra ") == "SILI"
    assert _MODULE._normalize_numeric_token(" Fog. 0012 ") == "12"
    assert _MODULE._normalize_numeric_token("foglio") == ""
    assert _MODULE._normalize_subalterno(" a ") == "A"
    assert _MODULE._clip("abcdef", 3) == "abc"
    assert _MODULE._sum_decimals([None, Decimal("1.25"), Decimal("2.75")]) == Decimal("4.00")
    assert _MODULE._sup_ha_from_are(Decimal("125")) == Decimal("1.25")
    assert _MODULE._coerce_decimal(Decimal("100000000"), _MODULE.MAX_NUMERIC_10_2, stats, "amount") is None
    assert stats["sanitized_amount_out_of_range"] == 1
    assert _MODULE._normalize_spaces(None) == ""
    assert _MODULE._normalize_partita_code(" abc  123 ") == "ABC 123"
    assert _MODULE._normalize_comune(None) == ""
    assert _MODULE._clip(None, 3) is None
    assert _MODULE._coerce_decimal(None, _MODULE.MAX_NUMERIC_10_2, stats, "none") is None
    assert _MODULE._coerce_decimal(Decimal("12.34"), _MODULE.MAX_NUMERIC_10_2, stats, "ok") == 12.34
    assert _MODULE._notice_to_codice_cnc("1") == "1"
    assert _MODULE._notice_to_codice_cnc("12345") == "01.1234"


def test_ensure_import_job_creates_only_when_apply_is_true() -> None:
    db = _FakeDb()
    existing_id = uuid.uuid4()
    db.scalars_values = [[SimpleNamespace(id=existing_id)]]

    assert _MODULE._ensure_import_job(db, 2024, apply=True) == existing_id
    assert db.added == []

    new_id = _MODULE._ensure_import_job(_FakeDb(), 2024, apply=False)
    assert isinstance(new_id, uuid.UUID)

    db_apply = _FakeDb()
    created_id = _MODULE._ensure_import_job(db_apply, 2024, apply=True)
    assert isinstance(created_id, uuid.UUID)
    assert db_apply.added[0].filename == "incass_backfill_2024"
    assert db_apply.added[0].params_json["source"] == "ana_payment_notices"


def test_collect_and_purge_year_use_state_and_batch_deletes(monkeypatch) -> None:
    db = _FakeDb()
    db.scalar_values = [2, 3, 4, 1]

    assert _MODULE._collect_year_state(db, 2024) == {
        "avvisi": 2,
        "partite": 3,
        "particelle": 4,
        "jobs": 1,
    }

    monkeypatch.setattr(
        _MODULE,
        "_collect_year_state",
        lambda db, anno: {"avvisi": 2, "partite": 3, "particelle": 5, "jobs": 1},
    )
    dry_state = _MODULE._purge_year(_FakeDb(), 2024, apply=False, batch_size=2)
    assert dry_state["particelle"] == 5

    purge_db = _FakeDb()
    purge_db.execute_results = [
        _ExecuteResult(rowcounts=[2]),
        _ExecuteResult(rowcounts=[2]),
        _ExecuteResult(rowcounts=[1]),
        _ExecuteResult(rowcounts=[0]),
        _ExecuteResult(),
        _ExecuteResult(),
        _ExecuteResult(),
    ]

    state = _MODULE._purge_year(purge_db, 2024, apply=True, batch_size=2)

    assert state["particelle"] == 5
    assert purge_db.commits == 3
    assert purge_db.flushes == 1


def test_load_maps_and_notice_iteration(monkeypatch) -> None:
    avviso_id = uuid.uuid4()
    partita_id = uuid.uuid4()
    avviso = SimpleNamespace(id=avviso_id, codice_cnc="01.1")
    partita = SimpleNamespace(
        id=partita_id,
        avviso_id=avviso_id,
        codice_partita=" p1 ",
        comune_nome=" SILI`*ORISTANO ",
    )
    db = _FakeDb()
    db.scalars_values = [[avviso], [SimpleNamespace(source_notice_id="n1")]]
    db.execute_results = [
        _ExecuteResult(rows=[(partita, avviso)]),
        _ExecuteResult(rows=[(partita_id, " 001 ", " P-002 ", " a ")]),
    ]

    assert _MODULE._load_notice_map(db, 2024) == {"01.1": avviso}
    assert _MODULE._load_partita_map(db, 2024)[(str(avviso_id), "P1", "SILI")] is partita
    assert _MODULE._load_existing_parcel_keys(db, 2024) == {
        _MODULE.ExistingParcelKey(str(partita_id), "1", "2", "A")
    }

    notices = _MODULE._iter_notices(db, 2024, max_notices=1)
    assert notices[0].source_notice_id == "n1"


def test_ensure_ruolo_avviso_builds_materialized_notice_without_db_write() -> None:
    stats: Counter[str] = Counter()
    notice = SimpleNamespace(
        source_notice_id="02019000012345",
        subject_id=uuid.uuid4(),
        codice_fiscale="RSSMRA80A01H501U",
        partita_iva=None,
        display_name="Mario Rossi",
        source_internal_id="UTENZA-12345678901234567890123456789012345",
        indirizzo="Via Roma 1",
        cap="09170",
        citta="Oristano",
        provincia="OR",
    )

    avviso = _MODULE._ensure_ruolo_avviso(
        SimpleNamespace(add=lambda item: None),
        anno=2019,
        notice=notice,
        partite=[
            {
                "importo_0648_euro": "1.000,50",
                "importo_0985_euro": "2.50",
                "importo_0668_euro": "3",
            }
        ],
        import_job_id=uuid.uuid4(),
        notice_map={},
        stats=stats,
        apply=False,
    )

    assert avviso.codice_cnc == "01.0201900001234"
    assert avviso.importo_totale_0648 == 1000.5
    assert avviso.importo_totale_0985 == 2.5
    assert avviso.importo_totale_0668 == 3.0
    assert avviso.importo_totale_euro == 1006.0
    assert avviso.domicilio_raw == "Via Roma 1 09170 Oristano OR"
    assert avviso.codice_utenza == "UTENZA-12345678901234567890123"
    assert stats["created_avvisi"] == 1


def test_ensure_ruolo_avviso_adds_new_notice_when_apply_is_true() -> None:
    db = _FakeDb()
    notice = SimpleNamespace(
        source_notice_id="02019000012345",
        subject_id=uuid.uuid4(),
        codice_fiscale=None,
        partita_iva="12345678901",
        display_name="Societa Agricola",
        source_internal_id=None,
        indirizzo=None,
        cap=None,
        citta=None,
        provincia=None,
    )

    avviso = _MODULE._ensure_ruolo_avviso(
        db,
        anno=2019,
        notice=notice,
        partite=[],
        import_job_id=uuid.uuid4(),
        notice_map={},
        stats=Counter(),
        apply=True,
    )

    assert db.added == [avviso]
    assert avviso.codice_fiscale_raw == "12345678901"


def test_ensure_ruolo_avviso_updates_sparse_existing_notice() -> None:
    stats: Counter[str] = Counter()
    existing = SimpleNamespace(
        subject_id=None,
        nominativo_raw="",
        codice_fiscale_raw="",
    )
    notice = SimpleNamespace(
        source_notice_id="02019000012345",
        subject_id=uuid.uuid4(),
        codice_fiscale="RSSMRA80A01H501U",
        partita_iva=None,
        display_name="Mario Rossi",
        source_internal_id=None,
        indirizzo=None,
        cap=None,
        citta=None,
        provincia=None,
    )

    avviso = _MODULE._ensure_ruolo_avviso(
        _FakeDb(),
        anno=2019,
        notice=notice,
        partite=[],
        import_job_id=uuid.uuid4(),
        notice_map={"01.0201900001234": existing},
        stats=stats,
        apply=True,
    )

    assert avviso is existing
    assert existing.subject_id == notice.subject_id
    assert existing.nominativo_raw == "Mario Rossi"
    assert existing.codice_fiscale_raw == "RSSMRA80A01H501U"
    assert stats["updated_avvisi"] == 1


def test_ensure_ruolo_partita_creates_and_rejects_invalid_keys(monkeypatch) -> None:
    monkeypatch.setattr(_MODULE, "_resolve_comune_codice_for_ruolo", lambda db, comune: "G113")
    stats: Counter[str] = Counter()
    avviso = SimpleNamespace(id=uuid.uuid4())
    db = _FakeDb()

    partita = _MODULE._ensure_ruolo_partita(
        db,
        avviso=avviso,
        partita_payload={
            "codice_partita": " p123 ",
            "comune_nome": "SILI`*ORISTANO",
            "contribuente_cf": "RSSMRA80A01H501U",
            "co_intestati_raw": "CO",
            "importo_0648_euro": "1,20",
            "importo_0985_euro": "2,30",
            "importo_0668_euro": "3,40",
        },
        partite_map={},
        stats=stats,
        apply=True,
    )

    assert partita is not None
    assert partita.codice_partita == "P123"
    assert partita.comune_nome == "SILI"
    assert partita.comune_codice == "G113"
    assert partita.importo_0648 == 1.2
    assert db.added == [partita]
    assert db.flushes == 1

    partite_map = {(str(avviso.id), "P123", "SILI"): partita}
    assert (
        _MODULE._ensure_ruolo_partita(
            db,
            avviso=avviso,
            partita_payload={"codice_partita": "p123", "comune_nome": "SILI"},
            partite_map=partite_map,
            stats=stats,
            apply=True,
        )
        is partita
    )

    assert (
        _MODULE._ensure_ruolo_partita(
            db,
            avviso=avviso,
            partita_payload={"codice_partita": "", "comune_nome": ""},
            partite_map={},
            stats=stats,
            apply=False,
        )
        is None
    )
    assert stats["partite_invalid_key"] == 1


def test_ensure_ruolo_particella_counts_duplicates_and_skip_catasto_without_db_write() -> None:
    stats: Counter[str] = Counter()
    existing_keys: set[object] = set()
    partita = SimpleNamespace(id=uuid.uuid4(), comune_nome="ORISTANO")
    payload = {
        "domanda_irrigua": "D1",
        "distretto": "001",
        "foglio": " Fog. 0007 ",
        "particella": " Part. 0042 ",
        "subalterno": " a ",
        "sup_catastale_are": "125",
        "sup_irrigata_ha": "1.25",
        "coltura": "SEMINATIVO",
        "importo_manut_euro": "10,50",
        "importo_irrig_euro": "20,25",
        "importo_ist_euro": "1",
    }

    _MODULE._ensure_ruolo_particella(
        SimpleNamespace(add=lambda item: None),
        anno=2024,
        partita=partita,
        particella_payload=payload,
        existing_keys=existing_keys,
        stats=stats,
        apply=False,
        skip_catasto=True,
    )
    _MODULE._ensure_ruolo_particella(
        SimpleNamespace(add=lambda item: None),
        anno=2024,
        partita=partita,
        particella_payload=payload,
        existing_keys=existing_keys,
        stats=stats,
        apply=False,
        skip_catasto=True,
    )

    assert stats["created_particelle"] == 1
    assert stats["existing_particelle"] == 1
    assert stats["particella_catasto_skipped"] == 1
    assert stats["match_status_unmatched"] == 1
    assert stats["match_reason_catasto_skipped"] == 1


def test_ensure_ruolo_particella_adds_row_with_catasto_match(monkeypatch) -> None:
    parcel_id = uuid.uuid4()
    cat_particella_id = uuid.uuid4()
    monkeypatch.setattr(_MODULE, "_upsert_catasto_parcel", lambda *args, **kwargs: parcel_id)
    monkeypatch.setattr(
        _MODULE,
        "resolve_cat_particella_match",
        lambda *args, **kwargs: (cat_particella_id, "matched", "exact_no_sub", None),
    )
    monkeypatch.setattr(
        _MODULE,
        "_resolve_section_hint_for_ruolo_comune",
        lambda comune: "E",
    )
    db = _FakeDb()
    db.get_values = [SimpleNamespace(comune_codice="G113", foglio="7", particella="42", subalterno=None)]
    stats: Counter[str] = Counter()

    _MODULE._ensure_ruolo_particella(
        db,
        anno=2024,
        partita=SimpleNamespace(id=uuid.uuid4(), comune_nome="SILI"),
        particella_payload={
            "domanda_irrigua": "D1",
            "distretto": "DISTRETTO-LUNGO",
            "foglio": "7",
            "particella": "42",
            "subalterno": "",
            "sup_catastale_are": "125",
            "sup_irrigata_ha": "1.25",
            "coltura": "SEMINATIVO-LUNGO-CHE-VIENE-TAGLIATO-OLTRE-CINQUANTA-CARATTERI",
            "importo_manut_euro": "10,50",
            "importo_irrig_euro": "20,25",
            "importo_ist_euro": "1",
        },
        existing_keys=set(),
        stats=stats,
        apply=True,
        skip_catasto=False,
    )

    created = db.added[0]
    assert created.catasto_parcel_id == parcel_id
    assert created.cat_particella_id == cat_particella_id
    assert created.cat_particella_match_status == "matched"
    assert created.cat_particella_match_confidence == "exact_no_sub"
    assert created.distretto == "DISTRETTO-"
    assert created.sup_catastale_ha == 1.25
    assert stats["created_particelle"] == 1
    assert stats["match_status_matched"] == 1


def test_ensure_ruolo_particella_counts_match_resolution_errors(monkeypatch) -> None:
    monkeypatch.setattr(_MODULE, "_upsert_catasto_parcel", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError()))
    stats: Counter[str] = Counter()

    _MODULE._ensure_ruolo_particella(
        _FakeDb(),
        anno=2024,
        partita=SimpleNamespace(id=uuid.uuid4(), comune_nome="ORISTANO"),
        particella_payload={"foglio": "7", "particella": "42"},
        existing_keys=set(),
        stats=stats,
        apply=False,
        skip_catasto=False,
    )

    assert stats["particella_match_resolution_errors"] == 1
    assert stats["match_reason_catasto_parcel_not_resolved"] == 1


def test_ensure_ruolo_particella_rejects_invalid_cadastral_keys() -> None:
    stats: Counter[str] = Counter()

    _MODULE._ensure_ruolo_particella(
        SimpleNamespace(add=lambda item: None),
        anno=2024,
        partita=SimpleNamespace(id=uuid.uuid4(), comune_nome="ORISTANO"),
        particella_payload={"foglio": "FOGLIO", "particella": ""},
        existing_keys=set(),
        stats=stats,
        apply=False,
        skip_catasto=True,
    )

    assert stats["particelle_invalid_key"] == 1
    assert stats["created_particelle"] == 0


def test_flush_job_stats_updates_existing_job() -> None:
    job = SimpleNamespace(total_partite=0, records_imported=0, records_skipped=0, records_errors=0)
    db = _FakeDb()
    db.get_values = [job, None]

    _MODULE._flush_job_stats(
        db,
        uuid.uuid4(),
        Counter(
            {
                "partite_scanned": 3,
                "created_avvisi": 2,
                "created_partite": 3,
                "created_particelle": 4,
                "existing_particelle": 1,
                "notice_errors": 5,
            }
        ),
    )
    _MODULE._flush_job_stats(db, uuid.uuid4(), Counter())

    assert job.total_partite == 3
    assert job.records_imported == 9
    assert job.records_skipped == 1
    assert job.records_errors == 5


def test_process_year_dry_run_replace_uses_empty_maps_and_rolls_back(monkeypatch) -> None:
    calls: list[str] = []
    notice = SimpleNamespace(
        source_notice_id="02024000000001",
        subject_id=uuid.uuid4(),
        codice_fiscale="RSSMRA80A01H501U",
        partita_iva=None,
        display_name="Mario Rossi",
        source_internal_id=None,
        indirizzo=None,
        cap=None,
        citta=None,
        provincia=None,
        raw_detail_json={"partite": [{"codice_partita": "", "comune_nome": ""}]},
    )
    db = _FakeDb()
    monkeypatch.setattr(
        _MODULE,
        "_purge_year",
        lambda db, anno, apply, batch_size: {"avvisi": 1, "partite": 2, "particelle": 3, "jobs": 4},
    )
    monkeypatch.setattr(_MODULE, "_iter_notices", lambda db, anno, max_notices: [notice])
    monkeypatch.setattr(_MODULE, "_ensure_import_job", lambda db, anno, apply: uuid.uuid4())
    monkeypatch.setattr(_MODULE, "_load_notice_map", lambda db, anno: calls.append("notice_map") or {})
    monkeypatch.setattr(_MODULE, "_load_partita_map", lambda db, anno: calls.append("partita_map") or {})
    monkeypatch.setattr(_MODULE, "_load_existing_parcel_keys", lambda db, anno: calls.append("keys") or set())

    stats = _MODULE.process_year(
        db,
        2024,
        apply=False,
        replace_year=True,
        purge_only=False,
        rebuild_only=False,
        max_notices=None,
        commit_every=250,
        purge_batch_size=2000,
        skip_catasto=True,
    )

    assert stats["purged_particelle"] == 3
    assert stats["partite_invalid_key"] == 1
    assert db.rollbacks == 1
    assert calls == []


def test_process_year_apply_commits_and_recovers_after_notice_error(monkeypatch) -> None:
    good_notice = SimpleNamespace(
        raw_detail_json={
            "partite": [
                {
                    "codice_partita": "P1",
                    "comune_nome": "ORISTANO",
                    "particelle": ["skip", {"foglio": "1", "particella": "2"}],
                }
            ]
        }
    )
    bad_notice = SimpleNamespace(raw_detail_json={"partite": [{"codice_partita": "P2", "comune_nome": "ORISTANO"}]})
    no_payload = SimpleNamespace(raw_detail_json="bad")
    no_partite = SimpleNamespace(raw_detail_json={"partite": []})
    db = _FakeDb()
    job_id = uuid.uuid4()
    monkeypatch.setattr(_MODULE, "_purge_year", lambda *args, **kwargs: {"avvisi": 0, "partite": 0, "particelle": 0, "jobs": 0})
    monkeypatch.setattr(_MODULE, "_iter_notices", lambda *args, **kwargs: [good_notice, bad_notice, no_payload, no_partite])
    monkeypatch.setattr(_MODULE, "_load_notice_map", lambda *args, **kwargs: {})
    monkeypatch.setattr(_MODULE, "_load_partita_map", lambda *args, **kwargs: {})
    monkeypatch.setattr(_MODULE, "_load_existing_parcel_keys", lambda *args, **kwargs: set())
    monkeypatch.setattr(_MODULE, "_ensure_import_job", lambda *args, **kwargs: job_id)
    monkeypatch.setattr(_MODULE, "_flush_job_stats", lambda *args, **kwargs: None)
    monkeypatch.setattr(_MODULE, "_ensure_ruolo_avviso", lambda *args, **kwargs: SimpleNamespace(id=uuid.uuid4()))

    def fake_partita(*args, **kwargs):
        payload = kwargs["partita_payload"]
        if payload["codice_partita"] == "P2":
            raise RuntimeError("boom")
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(_MODULE, "_ensure_ruolo_partita", fake_partita)
    particella_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        _MODULE,
        "_ensure_ruolo_particella",
        lambda *args, **kwargs: particella_calls.append(kwargs["particella_payload"]),
    )

    stats = _MODULE.process_year(
        db,
        2024,
        apply=True,
        replace_year=True,
        purge_only=False,
        rebuild_only=False,
        max_notices=None,
        commit_every=1,
        purge_batch_size=2000,
        skip_catasto=True,
    )

    assert stats["notices_processed"] == 1
    assert stats["notice_errors"] == 1
    assert stats["notices_without_payload_dict"] == 1
    assert stats["notices_without_partite"] == 1
    assert stats["particelle_scanned"] == 1
    assert particella_calls == [{"foglio": "1", "particella": "2"}]
    assert db.rollbacks == 1
    assert db.commits >= 2


def test_process_year_prints_periodic_progress(monkeypatch, capsys) -> None:
    notices = [
        SimpleNamespace(raw_detail_json={"partite": [{"codice_partita": "P", "comune_nome": "ORISTANO"}]})
        for _ in range(250)
    ]
    monkeypatch.setattr(_MODULE, "_iter_notices", lambda *args, **kwargs: notices)
    monkeypatch.setattr(_MODULE, "_load_notice_map", lambda *args, **kwargs: {})
    monkeypatch.setattr(_MODULE, "_load_partita_map", lambda *args, **kwargs: {})
    monkeypatch.setattr(_MODULE, "_load_existing_parcel_keys", lambda *args, **kwargs: set())
    monkeypatch.setattr(_MODULE, "_ensure_import_job", lambda *args, **kwargs: uuid.uuid4())
    monkeypatch.setattr(_MODULE, "_flush_job_stats", lambda *args, **kwargs: None)
    monkeypatch.setattr(_MODULE, "_ensure_ruolo_avviso", lambda *args, **kwargs: SimpleNamespace(id=uuid.uuid4()))
    monkeypatch.setattr(_MODULE, "_ensure_ruolo_partita", lambda *args, **kwargs: SimpleNamespace(id=uuid.uuid4()))

    _MODULE.process_year(
        _FakeDb(),
        2024,
        apply=True,
        replace_year=False,
        purge_only=False,
        rebuild_only=False,
        max_notices=None,
        commit_every=250,
        purge_batch_size=2000,
        skip_catasto=True,
    )

    assert "[rebuild] anno=2024 processed=250/250" in capsys.readouterr().out


def test_process_year_purge_only_and_rebuild_only_paths(monkeypatch) -> None:
    db = _FakeDb()
    monkeypatch.setattr(
        _MODULE,
        "_purge_year",
        lambda *args, **kwargs: {"avvisi": 1, "partite": 1, "particelle": 1, "jobs": 1},
    )

    stats = _MODULE.process_year(
        db,
        2024,
        apply=False,
        replace_year=True,
        purge_only=True,
        rebuild_only=False,
        max_notices=None,
        commit_every=0,
        purge_batch_size=2000,
        skip_catasto=True,
    )
    assert stats["purged_avvisi"] == 1
    assert db.rollbacks == 1

    monkeypatch.setattr(_MODULE, "_iter_notices", lambda *args, **kwargs: [])
    monkeypatch.setattr(_MODULE, "_load_notice_map", lambda *args, **kwargs: {})
    monkeypatch.setattr(_MODULE, "_load_partita_map", lambda *args, **kwargs: {})
    monkeypatch.setattr(_MODULE, "_load_existing_parcel_keys", lambda *args, **kwargs: set())
    monkeypatch.setattr(_MODULE, "_ensure_import_job", lambda *args, **kwargs: uuid.uuid4())
    stats = _MODULE.process_year(
        db,
        2024,
        apply=False,
        replace_year=True,
        purge_only=False,
        rebuild_only=True,
        max_notices=None,
        commit_every=0,
        purge_batch_size=2000,
        skip_catasto=True,
    )
    assert stats["notices_total"] == 0


def test_main_processes_year_range_and_closes_session(monkeypatch, capsys) -> None:
    db = _FakeDb()
    monkeypatch.setattr(
        _MODULE,
        "parse_args",
        lambda: SimpleNamespace(
            from_year=2023,
            to_year=2024,
            apply=False,
            replace_year=True,
            purge_only=False,
            rebuild_only=False,
            max_notices=None,
            commit_every=1,
            purge_batch_size=2000,
            skip_catasto=True,
            reparse_partitario=True,
        ),
    )
    monkeypatch.setattr(_MODULE, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        _MODULE,
        "process_year",
        lambda *args, **kwargs: Counter(
            {
                "notices_total": 1,
                "notices_processed": 1,
                "purged_avvisi": 2,
                "purged_partite": 3,
                "purged_particelle": 4,
                "purged_jobs": 5,
                "notices_without_partite": 6,
                "notices_without_payload_dict": 7,
                "created_avvisi": 8,
                "created_partite": 9,
                "created_particelle": 10,
                "existing_particelle": 11,
                "notice_errors": 12,
            }
        ),
    )

    _MODULE.main()

    output = capsys.readouterr().out
    assert "anno=2023 notices=1 processed=1" in output
    assert "anno=2024 notices=1 processed=1" in output
    assert db.closed is True


def test_main_guard_invokes_main() -> None:
    called: list[bool] = []
    guard_source = "\n" * 808 + 'if __name__ == "__main__":\n    main()\n'

    exec(
        compile(guard_source, _MODULE.__file__, "exec"),
        {"__name__": "__main__", "main": lambda: called.append(True)},
    )

    assert called == [True]
