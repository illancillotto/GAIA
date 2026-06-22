from __future__ import annotations

import builtins
from pathlib import Path
import runpy

from app.models import elaborazioni as elaborazioni_models
from app.modules.elaborazioni import models as elaborazioni_compat_models
from app.modules.elaborazioni import schemas as elaborazioni_compat_schemas
from app.modules.ruolo import enums as ruolo_enums
from app.schemas import elaborazioni as elaborazioni_schemas


def test_catasto_and_elaborazioni_wrapper_modules_reexport_symbols() -> None:
    assert elaborazioni_compat_models.ElaborazioneBatch is elaborazioni_models.ElaborazioneBatch
    assert elaborazioni_compat_models.ElaborazioneCredential is elaborazioni_models.ElaborazioneCredential
    assert elaborazioni_compat_schemas.ElaborazioneBatchResponse is elaborazioni_schemas.ElaborazioneBatchResponse
    assert elaborazioni_compat_schemas.ElaborazioneCredentialResponse is elaborazioni_schemas.ElaborazioneCredentialResponse


def test_catasto_schema_compat_file_executes_from_path() -> None:
    file_path = Path(__file__).resolve().parents[1] / "app/modules/catasto/schemas.py"
    globals_dict = runpy.run_path(str(file_path))
    assert "CatastoBatchResponse" in globals_dict
    assert "CatastoCredentialResponse" in globals_dict


def test_ruolo_enums_expose_expected_values_and_str_behavior() -> None:
    assert ruolo_enums.RuoloImportStatus.PENDING == "pending"
    assert ruolo_enums.RuoloImportStatus.COMPLETED.value == "completed"
    assert str(ruolo_enums.CodiceTributo.MANUTENZIONE) == "0648"
    assert ruolo_enums.CodiceTributo.ISTITUZIONALE.value == "0985"
    assert ruolo_enums.CodiceTributo.IRRIGAZIONE.value == "0668"
    assert ruolo_enums.CatastoParcelSource.RUOLO_IMPORT == "ruolo_import"
    assert ruolo_enums.CatastoParcelSource.SISTER.value == "sister"
    assert ruolo_enums.CatastoParcelSource.CAPACITAS.value == "capacitas"


def test_ruolo_enums_fallback_branch_without_strenum(monkeypatch) -> None:
    file_path = Path(__file__).resolve().parents[1] / "app/modules/ruolo/enums.py"
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "enum" and "StrEnum" in fromlist:
            raise ImportError("forced for test")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    globals_dict = runpy.run_path(str(file_path))

    assert globals_dict["RuoloImportStatus"].FAILED.value == "failed"
