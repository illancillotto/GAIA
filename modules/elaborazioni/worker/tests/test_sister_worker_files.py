from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4


WORKER_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = next(path / "backend" for path in WORKER_ROOT.parents if (path / "backend").exists())
for path in (WORKER_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from sister_worker_files import (
    build_document_path,
    build_request_artifact_dir,
    document_values,
    immobile_filename,
    normalize_legacy_immobile_documents,
)


def _request(**overrides):
    values = {
        "id": uuid4(),
        "user_id": 7,
        "batch_id": uuid4(),
        "execution_token": uuid4(),
        "search_mode": "immobile",
        "comune": "Santa Giusta",
        "foglio": "16",
        "particella": "281",
        "subalterno": None,
        "catasto": "terreni",
        "tipo_visura": "storica",
        "subject_kind": None,
        "subject_id": None,
        "request_type": None,
        "intestazione": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_document_names_do_not_expose_sister_username(tmp_path: Path) -> None:
    request = _request()
    path = build_document_path(tmp_path, "CSCVNT85R07G113V", request)

    assert build_request_artifact_dir(tmp_path, request.batch_id, request.id) == (
        tmp_path / "requests" / str(request.batch_id) / str(request.id)
    )
    assert path.name == "SANTA_GIUSTA_16_281.pdf"
    assert "CSCVNT85R07G113V" not in str(path)
    assert document_values(request, "CSCVNT85R07G113V", path, 10, "hash")["codice_fiscale"] is None


def test_subject_document_keeps_subject_identifier_and_subalterno_is_distinct(tmp_path: Path) -> None:
    immobile = _request(subalterno="3")
    subject = _request(
        search_mode="soggetto",
        subject_kind="PF",
        subject_id="RSSMRA80A01H501U",
        request_type="storica",
    )

    assert immobile_filename(immobile) == "SANTA_GIUSTA_16_281_3.pdf"
    path = build_document_path(tmp_path, "OPERATOR", subject)
    assert path.name == "PF_RSSMRA80A01H501U_STORICA.pdf"
    assert document_values(subject, "OPERATOR", path, 10, "hash")["codice_fiscale"] == subject.subject_id


class _FakeDb:
    def __init__(self, rows):
        self.rows = rows
        self.commits = 0

    def execute(self, _statement):
        return SimpleNamespace(all=lambda: self.rows)

    def commit(self) -> None:
        self.commits += 1


def test_cleanup_renames_file_and_clears_operator_identifier(tmp_path: Path) -> None:
    source = tmp_path / "CSCVNT85R07G113V_SANTA_GIUSTA_16_281.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    document = SimpleNamespace(
        filename=source.name,
        filepath=str(source),
        codice_fiscale="CSCVNT85R07G113V",
    )
    db = _FakeDb([(document, _request())])

    result = normalize_legacy_immobile_documents(db)

    target = tmp_path / "SANTA_GIUSTA_16_281.pdf"
    assert (result.scanned, result.updated, result.renamed, result.missing, result.conflicts) == (1, 1, 1, 0, 0)
    assert target.read_bytes() == b"%PDF-1.4\n"
    assert not source.exists()
    assert document.filename == target.name
    assert document.filepath == str(target)
    assert document.codice_fiscale is None
    assert db.commits == 1


def test_cleanup_dry_run_missing_and_unchanged_paths(tmp_path: Path) -> None:
    request = _request()
    canonical = tmp_path / immobile_filename(request)
    canonical.write_bytes(b"%PDF-1.4\n")
    unchanged = SimpleNamespace(filename=canonical.name, filepath=str(canonical), codice_fiscale=None)
    missing_path = tmp_path / "OPERATOR_16_281.pdf"
    missing = SimpleNamespace(filename=missing_path.name, filepath=str(missing_path), codice_fiscale="OPERATOR")
    legacy_path = tmp_path / "SECOND_OPERATOR_16_281.pdf"
    legacy_path.write_bytes(b"%PDF-1.4\n")
    legacy = SimpleNamespace(filename=legacy_path.name, filepath=str(legacy_path), codice_fiscale="SECOND_OPERATOR")
    legacy_request = _request(comune="Oristano")
    db = _FakeDb([(unchanged, request), (missing, request), (legacy, legacy_request)])

    result = normalize_legacy_immobile_documents(db, dry_run=True)

    assert (result.scanned, result.updated, result.renamed, result.missing, result.conflicts) == (3, 2, 1, 0, 0)
    assert missing.filename == missing_path.name
    assert legacy_path.exists()
    assert not (tmp_path / "ORISTANO_16_281.pdf").exists()
    assert db.commits == 0


def test_cleanup_updates_missing_metadata_and_skips_file_conflicts(tmp_path: Path) -> None:
    missing_path = tmp_path / "OPERATOR_16_281.pdf"
    missing = SimpleNamespace(filename=missing_path.name, filepath=str(missing_path), codice_fiscale="OPERATOR")
    missing_request = _request(comune="Marrubiu")

    source = tmp_path / "SECOND_OPERATOR_16_281.pdf"
    target = tmp_path / "SANTA_GIUSTA_16_281.pdf"
    source.write_bytes(b"source")
    target.write_bytes(b"target")
    conflict = SimpleNamespace(filename=source.name, filepath=str(source), codice_fiscale="SECOND_OPERATOR")
    db = _FakeDb([(missing, missing_request), (conflict, _request())])

    result = normalize_legacy_immobile_documents(db)

    assert (result.scanned, result.updated, result.renamed, result.missing, result.conflicts) == (2, 1, 0, 1, 1)
    assert missing.filename == "MARRUBIU_16_281.pdf"
    assert missing.filepath == str(tmp_path / "MARRUBIU_16_281.pdf")
    assert missing.codice_fiscale is None
    assert conflict.filename == source.name
    assert db.commits == 1
