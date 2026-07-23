from pypdf import PdfWriter

from app.modules.utenze.services.content_classification_service import (
    _compact_text,
    _excerpt_around,
    classify_document_content_file,
    classify_document_content_text,
)


def test_classify_content_text_for_all_operational_categories() -> None:
    cases = [
        ("Ingiunzione per riscossione coattiva.", "legal_action", "Azioni legali"),
        ("Relata di notifica consegnata dal messo notificatore.", "notification", "Notifiche e relate"),
        ("Ricevuta di avvenuta consegna PEC ObjMan.", "delivery_proof", "Prove invio e PEC"),
        ("Avviso di pagamento inCASS con IUV 123 e importo da pagare.", "debt_payment", "Pagamenti e debito"),
        ("Domanda di utenza irrigua DUI annuale.", "irrigation_application", "Domande utenza irrigua"),
        ("Visura catastale Agenzia delle Entrate foglio particella.", "cadastral", "Visure e catasto"),
        ("Contratto e convenzione tra le parti.", "contract", "Contratti e convenzioni"),
        ("Protocollo pratica interna prot. 123.", "internal_practice", "Pratiche interne"),
    ]

    for text, category, label in cases:
        content = classify_document_content_text(text)
        assert content.status == "classified"
        assert content.category == category
        assert content.label == label
        assert content.confidence == 0.82
        assert content.excerpt


def test_irrigation_application_wins_over_plain_pec_mentions() -> None:
    content = classify_document_content_text(
        "Consorzio di Bonifica dell'Oristanese protocollo.cbo@pec.it. "
        "Oggetto: verifica domanda utenza irrigua 2024 per annullamento DUI. "
        "Il consorzio utilizza i dati relativi all'indirizzo di posta elettronica certificata PEC per le comunicazioni."
    )

    assert content.status == "classified"
    assert content.category == "irrigation_application"
    assert content.label == "Domande utenza irrigua"
    assert content.reason == "contenuto con riferimenti a domanda utenza irrigua/DUI"


def test_delivery_proof_requires_receipt_or_delivery_context() -> None:
    content = classify_document_content_text(
        "Ricevuta di avvenuta consegna PEC relativa alla comunicazione inviata dal gestore."
    )

    assert content.status == "classified"
    assert content.category == "delivery_proof"


def test_classify_content_text_empty() -> None:
    content = classify_document_content_text(" \n\t ")

    assert content.status == "empty"
    assert content.category is None
    assert content.error == "Testo documento assente o non estraibile"


def test_classify_content_text_unclassified() -> None:
    content = classify_document_content_text("Documento generico senza indicatori operativi riconosciuti.")

    assert content.status == "unclassified"
    assert content.category == "other"
    assert content.label == "Altro da classificare"
    assert content.confidence == 0.25


def test_text_helpers_compact_and_excerpt_boundaries() -> None:
    assert _compact_text("a\x00  b\n c") == "a b c"
    assert _excerpt_around("PEC test", 0, 3) == "PEC test"
    assert _excerpt_around("x" * 120 + "PEC" + "y" * 220, 120, 123).startswith("...")


def test_classify_content_file_eml(tmp_path) -> None:
    path = tmp_path / "ricevuta.eml"
    path.write_text(
        "Subject: Ricevuta di avvenuta consegna PEC\n"
        "From: gestore@example.test\n"
        "To: consorzio@example.test\n"
        "\n"
        "Posta elettronica certificata consegnata.",
        encoding="utf-8",
    )

    content = classify_document_content_file(path)

    assert content.status == "classified"
    assert content.category == "delivery_proof"
    assert content.source == "eml_text"


def test_classify_content_file_plain_text(tmp_path) -> None:
    path = tmp_path / "ricevuta.txt"
    path.write_text("Ricevuta di avvenuta consegna PEC.", encoding="utf-8")

    content = classify_document_content_file(path)

    assert content.status == "classified"
    assert content.category == "delivery_proof"
    assert content.source == "plain_text"


def test_classify_content_file_pdf_empty(tmp_path) -> None:
    path = tmp_path / "vuoto.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as handle:
        writer.write(handle)

    content = classify_document_content_file(path)

    assert content.status == "empty"
    assert content.source == "pdf_text"


def test_classify_content_file_unsupported(tmp_path) -> None:
    path = tmp_path / "foto.png"
    path.write_bytes(b"not an image")

    content = classify_document_content_file(path)

    assert content.status == "unsupported"
    assert content.category is None
    assert content.error == "Formato documento non supportato per classificazione contenutistica"
