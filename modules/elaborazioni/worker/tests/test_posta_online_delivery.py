import asyncio
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, NumberObject, StreamObject

import posta_online_delivery as delivery

CODE = "123456789012"
REFERENCE = "12345678-1234-1234-1234-123456789012"
HTML = f"""<form name="doAction"><input type="hidden" name="controller" value="archivio.do">
<input type="hidden" name="numrows"><input name="ignored" value="not-hidden"></form>
<table id="destinatario"><tr><td>Raccomandata N.{CODE}</td></tr></table>
<a onclick="MostraAnteprima(800,600,'recuperaRicevutaAccettazione.do',' {REFERENCE}');">
Ricevuta Raccomandata</a>"""


def pdf_bytes(label=CODE):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    content = StreamObject()
    content.set_data(f"BT /F1 12 Tf 10 100 Td ({label}) Tj ET".encode())
    page[NameObject("/Contents")] = content
    page[NameObject("/Rotate")] = NumberObject(0)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_tracking_uses_the_observed_read_endpoint_and_preserves_provider_evidence():
    payload = {"idTracciatura": CODE, "listaMovimenti": [], "stato": "2"}
    http = SimpleNamespace(
        post=AsyncMock(return_value=SimpleNamespace(status_code=200, json=lambda: payload))
    )
    assert asyncio.run(delivery.read_tracking(http, CODE)) == payload
    http.post.assert_awaited_once_with(
        delivery.TRACKING_URL,
        json={"tipoRichiedente": "WEB", "codiceSpedizione": CODE, "periodoRicerca": 1},
    )


@pytest.mark.parametrize(
    "code",
    [
        "123",
        "1234567890123",
        "\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19\uff10\uff11\uff12",
        "../../secret",
    ],
)
def test_invalid_tracking_never_makes_a_request(code):
    http = SimpleNamespace(post=AsyncMock())
    with pytest.raises(ValueError):
        asyncio.run(delivery.read_tracking(http, code))
    http.post.assert_not_called()


@pytest.mark.parametrize(
    "status,payload",
    [
        (403, {}),
        (429, {}),
        (500, {}),
        (302, {}),
        (200, []),
        (200, {"idTracciatura": "other"}),
        (200, {"idTracciatura": CODE}),
    ],
)
def test_unavailable_tracking_is_never_retried_or_reported_as_delivery(status, payload):
    http = SimpleNamespace(
        post=AsyncMock(return_value=SimpleNamespace(status_code=status, json=lambda: payload))
    )
    with pytest.raises(delivery.EvidenceUnavailable):
        asyncio.run(delivery.read_tracking(http, CODE))
    assert http.post.await_count == 1


def test_receipt_form_uses_only_the_observed_acceptance_action_and_checks_identity():
    assert delivery.receipt_form(HTML, CODE) == {
        "controller": "archivio.do",
        "numrows": "",
        "idInvio": REFERENCE,
    }
    assert (
        delivery.receipt_form(HTML.replace("recuperaRicevutaAccettazione", "inserisciInvii"), CODE)
        is None
    )
    assert delivery.receipt_form(HTML.replace("onclick", "data-other"), CODE) is None
    with pytest.raises(delivery.EvidenceUnavailable, match="corrispondente"):
        delivery.receipt_form(HTML, "999999999999")
    with pytest.raises(delivery.EvidenceUnavailable, match="corrispondente"):
        delivery.receipt_form("<html>Login</html>", CODE)
    with pytest.raises(delivery.EvidenceUnavailable, match="assente"):
        delivery.receipt_form(HTML.replace('name="doAction"', 'name="other"'), CODE)
    with pytest.raises(delivery.EvidenceUnavailable, match="ambigua"):
        delivery.receipt_form(
            HTML + HTML.replace(REFERENCE, "abcdefab-1234-1234-1234-123456789012"), CODE
        )


def test_pdf_must_really_contain_the_expected_tracking():
    content = pdf_bytes()
    metadata = delivery.validate_receipt(content, CODE)
    assert metadata["kind"] == "acceptance_receipt"
    assert metadata["pages"] == 1 and metadata["bytes"] == len(content)
    assert len(metadata["sha256"]) == 64
    with pytest.raises(delivery.EvidenceUnavailable, match="Tracking"):
        delivery.validate_receipt(pdf_bytes("unrelated receipt"), CODE)
    for invalid in (b"<html>Login</html>", b"%PDF-" + b"x" * (20 * 1024 * 1024)):
        with pytest.raises(delivery.EvidenceUnavailable, match="PDF"):
            delivery.validate_receipt(invalid, CODE)


def test_empty_pdf_text_cannot_certify_a_receipt():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=200)
    output = BytesIO()
    writer.write(output)
    with pytest.raises(delivery.EvidenceUnavailable, match="Tracking"):
        delivery.validate_receipt(output.getvalue(), CODE)


@pytest.mark.parametrize("other_code", [f"9{CODE}", f"{CODE}9"])
def test_tracking_embedded_in_another_number_cannot_certify_identity(other_code):
    with pytest.raises(delivery.EvidenceUnavailable, match="corrispondente"):
        delivery.receipt_form(HTML.replace(CODE, other_code), CODE)
    with pytest.raises(delivery.EvidenceUnavailable, match="Tracking"):
        delivery.validate_receipt(pdf_bytes(other_code), CODE)


@pytest.mark.parametrize(
    "payload",
    [
        {"id": 2, "tipo": "error", "descrizione": "Specificare una CAPTCHA valido"},
        [],
        ValueError("non JSON"),
    ],
)
def test_tracking_challenge_is_distinguished_from_other_errors(payload):
    from unittest.mock import Mock

    response = SimpleNamespace(status_code=400, json=Mock())
    if isinstance(payload, ValueError):
        response.json.side_effect = payload
    else:
        response.json.return_value = payload
    http = SimpleNamespace(post=AsyncMock(return_value=response))
    expected = (
        delivery.InteractiveCheckRequired
        if isinstance(payload, dict)
        else delivery.EvidenceUnavailable
    )
    with pytest.raises(expected):
        asyncio.run(delivery.read_tracking(http, CODE))
    assert http.post.await_count == 1


def test_receipt_read_is_throttled_and_never_retried():
    content = pdf_bytes()
    response = SimpleNamespace(status=200, body=AsyncMock(return_value=content))
    request = SimpleNamespace(post=AsyncMock(return_value=response))
    client = SimpleNamespace(
        context=SimpleNamespace(request=request), throttle=SimpleNamespace(wait=AsyncMock())
    )
    result = asyncio.run(delivery.read_acceptance_receipt(client, HTML, CODE))
    assert result[0] == content
    client.throttle.wait.assert_awaited_once_with("acceptance-receipt")
    assert request.post.call_args.args == (delivery.RECEIPT_URL,)
    assert request.post.call_args.kwargs["multipart"]["idInvio"] == REFERENCE
    response.status = 403
    with pytest.raises(delivery.EvidenceUnavailable, match="HTTP 403"):
        asyncio.run(delivery.read_acceptance_receipt(client, HTML, CODE))
    assert request.post.await_count == 2
    assert (
        asyncio.run(
            delivery.read_acceptance_receipt(client, HTML.replace("onclick", "unused"), CODE)
        )
        is None
    )
    assert request.post.await_count == 2
