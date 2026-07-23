from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS: dict[str, tuple[str, str]] = {
    "AnagraficaImportPreviewService": ("app.modules.utenze.services.import_service", "AnagraficaImportPreviewService"),
    "AnagraficaNASWarning": ("app.modules.utenze.services.import_service", "AnagraficaNASWarning"),
    "AnagraficaPreviewDocument": ("app.modules.utenze.services.import_service", "AnagraficaPreviewDocument"),
    "AnagraficaPreviewSubject": ("app.modules.utenze.services.import_service", "AnagraficaPreviewSubject"),
    "CsvImportError": ("app.modules.utenze.services.csv_import_service", "CsvImportError"),
    "CsvImportResult": ("app.modules.utenze.services.csv_import_service", "CsvImportResult"),
    "ImportPreviewResult": ("app.modules.utenze.services.import_service", "ImportPreviewResult"),
    "ImportRunResult": ("app.modules.utenze.services.import_service", "ImportRunResult"),
    "ParseResult": ("app.modules.utenze.services.parser_service", "ParseResult"),
    "ResetAnagraficaResult": ("app.modules.utenze.services.import_service", "ResetAnagraficaResult"),
    "SubjectImportRunResult": ("app.modules.utenze.services.import_service", "SubjectImportRunResult"),
    "classify_filename": ("app.modules.utenze.services.classify_service", "classify_filename"),
    "classify_filenames": ("app.modules.utenze.services.classify_service", "classify_filenames"),
    "import_existing_registry_subjects": ("app.modules.utenze.services.import_service", "import_existing_registry_subjects"),
    "import_subject_from_existing_registry": ("app.modules.utenze.services.import_service", "import_subject_from_existing_registry"),
    "import_subjects_from_csv": ("app.modules.utenze.services.csv_import_service", "import_subjects_from_csv"),
    "parse_folder_name": ("app.modules.utenze.services.parser_service", "parse_folder_name"),
    "preview_import": ("app.modules.utenze.services.import_service", "preview_import"),
    "reset_anagrafica_data": ("app.modules.utenze.services.import_service", "reset_anagrafica_data"),
    "run_import": ("app.modules.utenze.services.import_service", "run_import"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
