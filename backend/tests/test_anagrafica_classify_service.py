from app.modules.anagrafica.services.classify_service import classify_filename


def test_classify_ingiunzione_filename() -> None:
    doc_type, source = classify_filename("INGIUNZIONE-2024.pdf")

    assert doc_type == "ingiunzione"
    assert source == "auto"


def test_classify_notifica_filename() -> None:
    doc_type, source = classify_filename("Relata_notifica_messo.pdf")

    assert doc_type == "notifica"
    assert source == "auto"


def test_classify_pratica_interna_filename() -> None:
    doc_type, source = classify_filename("PE_Prot5620.gif")

    assert doc_type == "pratica_interna"
    assert source == "auto"


def test_classify_altro_when_no_pattern_matches() -> None:
    doc_type, source = classify_filename("foto_documento_generico.png")

    assert doc_type == "altro"
    assert source == "auto"
