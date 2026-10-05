import pytest

from app.modules.utenze.services.parser_service import parse_folder_name


def test_parse_person_folder_name() -> None:
    result = parse_folder_name("Obinu_Santina_BNOSTN34L64I743F")

    assert result.subject_type == "person"
    assert result.cognome == "Obinu"
    assert result.nome == "Santina"
    assert result.codice_fiscale == "BNOSTN34L64I743F"
    assert result.requires_review is False


def test_parse_company_folder_name() -> None:
    result = parse_folder_name("Olati_Srl_14542661005")

    assert result.subject_type == "company"
    assert result.ragione_sociale == "Olati Srl"
    assert result.partita_iva == "14542661005"
    assert result.requires_review is False


def test_parse_partial_piva_company_with_review() -> None:
    result = parse_folder_name("3M_Societa_Agricola_Semplice_0123806095")

    assert result.subject_type == "company"
    assert result.ragione_sociale == "3M Societa Agricola Semplice"
    assert result.partita_iva == "0123806095"
    assert result.requires_review is True
    assert "partita_iva_length_anomaly" in result.warnings


def test_parse_special_folder_as_unknown() -> None:
    result = parse_folder_name("TELERILEVAMENTO")

    assert result.subject_type == "unknown"
    assert result.requires_review is True
    assert "special_folder_candidate" in result.warnings


def test_parse_numeric_only_folder_as_unknown() -> None:
    result = parse_folder_name("00710430950")

    assert result.subject_type == "unknown"
    assert result.partita_iva == "00710430950"
    assert result.requires_review is True


@pytest.mark.parametrize(
    ("folder_name", "is_person", "is_company"),
    [
        ("Obinu_Santina_BNOSTN34L64I743F", True, False),
        ("Olati_Srl_14542661005", False, True),
        ("TELERILEVAMENTO", False, False),
    ],
)
def test_result_subject_type_properties(
    folder_name: str, is_person: bool, is_company: bool
) -> None:
    result = parse_folder_name(folder_name)

    assert result.is_person is is_person
    assert result.is_company is is_company


@pytest.mark.parametrize("folder_name", ["", " \t\n", "___", " _ \t_ \n_"])
def test_parse_empty_folder_name_requires_review(folder_name: str) -> None:
    result = parse_folder_name(folder_name)

    assert result.source_name_raw == folder_name
    assert result.subject_type == "unknown"
    assert result.requires_review is True
    assert result.confidence == 0.0
    assert result.warnings == ["empty_folder_name"]


@pytest.mark.parametrize(
    "folder_name",
    ["BNOSTN34L64I743F", "Obinu_BNOSTN34L64I743F", "Obinu_ _BNOSTN34L64I743F"],
)
def test_parse_incomplete_person_name_requires_review(folder_name: str) -> None:
    result = parse_folder_name(folder_name)

    assert result.source_name_raw == folder_name
    assert result.subject_type == "unknown"
    assert result.codice_fiscale == "BNOSTN34L64I743F"
    assert result.cognome is None
    assert result.nome is None
    assert result.requires_review is True
    assert result.confidence == 0.2
    assert result.warnings == ["person_name_incomplete"]


@pytest.mark.parametrize("folder_name", ["documenti", "Documenti_Archivio", "ARCHIVIO_DOC"])
def test_parse_unclassified_non_special_folder_name(folder_name: str) -> None:
    result = parse_folder_name(folder_name)

    assert result.source_name_raw == folder_name
    assert result.subject_type == "unknown"
    assert result.requires_review is True
    assert result.confidence == 0.1
    assert result.warnings == ["unclassified_folder_name"]


@pytest.mark.parametrize(
    ("folder_name", "expected_name"),
    [
        ("Obinu_Santina_BNOSTN34L64I743F", "Santina"),
        (" _Obinu_ _Santina_ _BNOSTN34L64I743F_ ", "Santina"),
        ("Obinu_\tSantina\nMaria_BNOSTN34L64I743F", "Santina Maria"),
        ("Obinu_Santina_Maria_BNOSTN34L64I743F", "Santina Maria"),
    ],
)
def test_parse_complete_person_name_preserves_nonempty_name(
    folder_name: str, expected_name: str
) -> None:
    result = parse_folder_name(folder_name)

    assert result.source_name_raw == folder_name
    assert result.subject_type == "person"
    assert result.cognome == "Obinu"
    assert result.nome == expected_name
    assert result.codice_fiscale == "BNOSTN34L64I743F"
    assert result.requires_review is False
    assert result.confidence == 0.98
    assert result.warnings == []
