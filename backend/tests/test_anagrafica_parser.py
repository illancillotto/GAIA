from app.modules.anagrafica.services.parser_service import parse_folder_name


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
