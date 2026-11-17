"""Read tracking and acceptance evidence; neither service authorizes a shipment."""

import hashlib
import re
from io import BytesIO

from bs4 import BeautifulSoup
from pypdf import PdfReader

TRACKING_URL = "https://www.poste.it/online/dovequando/DQ-REST/ricercasemplice"
RECEIPT_URL = "https://corrispondenza.poste.it/col/recuperaRicevutaAccettazione.do"
_PREVIEW = re.compile(
    r"MostraAnteprima\(\s*\d+\s*,\s*\d+\s*,\s*"
    r"'recuperaRicevutaAccettazione\.do'\s*,\s*"
    r"'\s*([0-9a-fA-F-]{36})\s*'\s*\);?"
)


class EvidenceUnavailable(RuntimeError):
    """A missing or refused response must not be interpreted as delivery."""


class InteractiveCheckRequired(EvidenceUnavailable):
    """The provider requires human verification; no automatic retry is allowed."""


def _tracking_failure(response) -> None:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if isinstance(payload, dict) and "captcha" in str(payload.get("descrizione", "")).lower():
        raise InteractiveCheckRequired("Tracking Poste richiede CAPTCHA: recupero sospeso")
    raise EvidenceUnavailable(f"Tracking Poste HTTP {response.status_code}")


def tracking_code(value: str) -> str:
    if not re.fullmatch(r"\d{12}", value, flags=re.ASCII):
        raise ValueError("Tracking raccomandata non valido")
    return value


async def read_tracking(http, code: str) -> dict:
    """Same read-only request made by the Poste shipment webview, without login."""
    code = tracking_code(code)
    response = await http.post(
        TRACKING_URL,
        json={"tipoRichiedente": "WEB", "codiceSpedizione": code, "periodoRicerca": 1},
    )
    if response.status_code != 200:
        _tracking_failure(response)
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("idTracciatura") != code:
        raise EvidenceUnavailable("Tracking restituito da Poste non corrispondente")
    if not isinstance(payload.get("listaMovimenti"), list):
        raise EvidenceUnavailable("Risposta Poste priva dei movimenti della spedizione")
    # Keep the original labels/codes: a generic service status is not proof of delivery.
    return payload


def receipt_form(detail_html: str, code: str) -> dict[str, str] | None:
    soup = BeautifulSoup(detail_html, "html.parser")
    table = soup.find("table", id="destinatario")
    if table is None or not re.search(
        rf"(?<!\d){tracking_code(code)}(?!\d)", table.get_text(" ", strip=True)
    ):
        raise EvidenceUnavailable("Dettaglio Poste non corrispondente al tracking richiesto")
    references = {
        match.group(1)
        for link in soup.find_all("a", onclick=True)
        if (match := _PREVIEW.fullmatch(link["onclick"].strip()))
    }
    if not references:
        return None
    if len(references) != 1:
        raise EvidenceUnavailable("Ricevuta Poste ambigua: revisione richiesta")
    form = soup.find("form", attrs={"name": "doAction"})
    if form is None:
        raise EvidenceUnavailable("Modulo di lettura ricevuta Poste assente")
    fields = {
        field["name"]: field.get("value", "")
        for field in form.find_all("input", attrs={"type": "hidden", "name": True})
    }
    fields["idInvio"] = references.pop()
    return fields


def validate_receipt(content: bytes, code: str) -> dict:
    if not content.startswith(b"%PDF-") or len(content) > 20 * 1024 * 1024:
        raise EvidenceUnavailable("La ricevuta Poste non è un PDF valido entro 20 MiB")
    reader = PdfReader(BytesIO(content))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    if not re.search(rf"(?<!\d){tracking_code(code)}(?!\d)", text):
        raise EvidenceUnavailable("Tracking non verificabile nella ricevuta Poste")
    return {
        "kind": "acceptance_receipt",
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
        "pages": len(reader.pages),
    }


async def read_acceptance_receipt(client, detail_html: str, code: str):
    fields = receipt_form(detail_html, code)
    if fields is None:
        return None
    await client.throttle.wait("acceptance-receipt")
    response = await client.context.request.post(
        RECEIPT_URL,
        multipart=fields,
        headers={"Referer": "https://corrispondenza.poste.it/col/dettaglio.do"},
        timeout=60000,
    )
    if response.status != 200:
        raise EvidenceUnavailable(f"Ricevuta Poste HTTP {response.status}")
    content = await response.body()
    return content, validate_receipt(content, code)
