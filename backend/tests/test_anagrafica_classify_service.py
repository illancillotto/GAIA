from app.modules.utenze.services.classify_service import classify_filename, derive_document_smart_classification


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


def test_derive_smart_category_from_saved_doc_type() -> None:
    smart = derive_document_smart_classification(
        filename="documento_generico.pdf",
        doc_type="ingiunzione",
        classification_source="manual",
    )

    assert smart.category == "legal_action"
    assert smart.priority == 100
    assert smart.confidence == 1.0


def test_derive_smart_category_for_incass_payment_notice_filename() -> None:
    smart = derive_document_smart_classification(
        filename="avviso_pagamento_incass_2026.pdf",
        doc_type="altro",
        classification_source="auto",
    )

    assert smart.category == "debt_payment"
    assert smart.label == "Pagamenti e debito"


def test_derive_smart_category_for_pec_receipt_filename() -> None:
    smart = derive_document_smart_classification(
        filename="ricevuta_consegna_objman.eml",
        doc_type="altro",
        classification_source="auto",
        extension=".eml",
    )

    assert smart.category == "delivery_proof"
    assert smart.priority > 70


def test_derive_smart_category_for_cadastral_visura_filename() -> None:
    smart = derive_document_smart_classification(
        filename="visura_catastale_2026.pdf",
        doc_type="altro",
        classification_source="auto",
    )

    assert smart.category == "cadastral"


def test_derive_smart_category_for_irrigation_application_filename() -> None:
    smart = derive_document_smart_classification(
        filename="P_U_8209_24_Rif31-Verifica_domanda_utenza_irrigua_2024.pdf",
        doc_type="altro",
        classification_source="auto",
    )

    assert smart.category == "irrigation_application"
    assert smart.label == "Domande utenza irrigua"


def test_derive_smart_category_for_dui_folder_like_filename() -> None:
    smart = derive_document_smart_classification(
        filename="Dui2025",
        doc_type="altro",
        classification_source="auto",
    )

    assert smart.category == "irrigation_application"


def test_derive_smart_category_for_dui_cancellation_filename() -> None:
    smart = derive_document_smart_classification(
        filename="P_U_1571_25_DEIAS_DAVIDE_P_E_7655_annull_DUI.pdf",
        doc_type="altro",
        classification_source="auto",
    )

    assert smart.category == "irrigation_application"
