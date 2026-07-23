from __future__ import annotations

import html
import re
from urllib.parse import quote, urlencode, urljoin

from app.modules.elaborazioni.capacitas.apps import get_capacitas_app
from app.modules.elaborazioni.capacitas.decoder import decode_response
from app.modules.elaborazioni.capacitas.models import (
    CapacitasInCassMailingContactRow,
    CapacitasInCassMailingReceiptParent,
    CapacitasInCassMailingShipmentRow,
    CapacitasInCassMailingSubjectRow,
    CapacitasInCassNoticeDetail,
    CapacitasInCassPartitarioDetail,
    CapacitasInCassSearchResult,
    CapacitasObjManDocument,
)
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.modules.elaborazioni.capacitas.apps.incass.parsers import (
    parse_incass_notice_detail,
    parse_incass_partitario_dialog,
    parse_incass_search_result,
)

INCASS_APP = get_capacitas_app("incass")
AJAX_RICERCA_URL = f"{INCASS_APP.base_url}/pages/ajax/ajaxRicerca.aspx"
RICERCA_AVVISI_URL = f"{INCASS_APP.base_url}/pages/ricercaAvvisi.aspx"
DETTAGLIO_AVVISO_URL = f"{INCASS_APP.base_url}/pages/dettaglioAvviso.aspx"
DLG_PARTITARIO_URL = f"{INCASS_APP.base_url}/pages/dialog/dlgPartitarioKUI.aspx"
MAILING_LIST_URL = f"{INCASS_APP.base_url}/pages/mailingListOpMass.aspx"
AJAX_OPERAZIONI_MASSIVE_URL = f"{INCASS_APP.base_url}/pages/ajax/ajaxOperazioniMassive.aspx"
AJAX_MAILING_LIST_URL = f"{INCASS_APP.base_url}/pages/ajax/ajaxMailingList.aspx"
DLG_SPEDIZIONI_URL = f"{INCASS_APP.base_url}/pages/dialog/dlgSpedizioni.aspx"
DLG_OBJMAN_URL = f"{INCASS_APP.base_url}/pages/dialog/dlgObjMan.aspx"
AJAX_MISC_URL = f"{INCASS_APP.base_url}/pages/ajax/ajaxMisc.aspx"
OBJMAN_BASE_URL = "https://objman.servizicapacitas.com"
OBJMAN_XHR_ALLEGATI_URL = f"{OBJMAN_BASE_URL}/pages/ajax/xhrAllegati.ashx"
OBJMAN_DOWNLOAD_URL = f"{OBJMAN_BASE_URL}/pages/download.aspx"

_AJAX_HEADERS = {
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}

_OBJMAN_URL_RE = re.compile(r"https://objman\.servizicapacitas\.com/[^'\"<>\s]+", re.IGNORECASE)
_KENDO_FIRST_PAGE = {"take": "1000", "skip": "0", "page": "1", "pageSize": "1000"}


class CapacitasInCassSessionExpiredError(RuntimeError):
    pass


class InCassClient:
    def __init__(self, session_manager: CapacitasSessionManager) -> None:
        self._manager = session_manager

    async def refresh_session(self) -> None:
        await self._manager.close()
        await self._manager.login()
        await self._manager.activate_app("incass")
        await self._manager.start_keepalive("incass")

    async def warmup_search_page(self) -> None:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.get(
            RICERCA_AVVISI_URL,
            params={"token": token, "app": "incass", "tenant": ""},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="ricercaavvisi")

    async def warmup_mailing_list_page(self) -> None:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.get(
            MAILING_LIST_URL,
            params={"token": token, "app": "incass", "tenant": ""},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="mailinglistopmass")

    async def search_notices(self, identifier: str) -> CapacitasInCassSearchResult:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        payload = {
            "op": "avvisi",
            "isExport": "false",
            "tipoDenominaz": quote("", safe=""),
            "denominaz": quote("", safe=""),
            "tipoNum": quote("avviso", safe=""),
            "avviso": quote("", safe=""),
            "codFisc": quote(identifier.strip().upper(), safe=""),
            "anno": quote("", safe=""),
            "lista": quote("", safe=""),
            "importoDa": quote("", safe=""),
            "importoA": quote("", safe=""),
            "pagamenti": quote("Tutti gli avvisi", safe=""),
            "sgravio": quote("Tutti gli avvisi", safe=""),
            "tipoPagamento": quote("Tutti", safe=""),
            "postalizzazione": quote("Tutti", safe=""),
            "gruppoEtichette": quote("", safe=""),
            "etichetta": quote("", safe=""),
            "valoreEtichetta": quote("", safe=""),
        }
        response = await http.post(
            AJAX_RICERCA_URL,
            data=payload,
            headers={**_AJAX_HEADERS, "Referer": f"{RICERCA_AVVISI_URL}?token={token}&app=incass&tenant="},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="ajaxricerca")
        decoded = decode_response(response.text.strip())
        return parse_incass_search_result(decoded, base_url=INCASS_APP.base_url)

    async def fetch_notice_detail(self, avviso: str) -> CapacitasInCassNoticeDetail:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.get(
            DETTAGLIO_AVVISO_URL,
            params={"avviso": avviso, "token": token, "app": "incass", "tenant": ""},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="dettaglioavviso")
        detail_url = str(response.url)
        return parse_incass_notice_detail(response.text, detail_url=detail_url, base_url=INCASS_APP.base_url, avviso=avviso)

    async def fetch_notice_partitario(self, avviso: str) -> CapacitasInCassPartitarioDetail | None:
        http = self._manager.get_http_client()
        response = await http.post(
            DLG_PARTITARIO_URL,
            data={"idDlg": "dlg-vis-part-kui", "avviso": avviso},
            headers={**_AJAX_HEADERS, "Referer": f"{DETTAGLIO_AVVISO_URL}?avviso={avviso}"},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="dlgpartitariokui")
        return parse_incass_partitario_dialog(response.text, avviso=avviso)

    async def download_notice_pdf(self, url: str, *, referer: str | None = None) -> bytes:
        http = self._manager.get_http_client()
        response = await http.get(
            url,
            headers={
                "Accept": "application/pdf,application/octet-stream,*/*",
                "Referer": referer or RICERCA_AVVISI_URL,
            },
        )
        response.raise_for_status()
        headers = getattr(response, "headers", {}) or {}
        content_type = str(headers.get("content-type", "")).lower()
        if "text/html" in content_type:
            self._ensure_valid_app_response(response, expected_marker="download")
        return response.content

    async def search_mailing_subjects(self, identifier: str) -> list[CapacitasInCassMailingSubjectRow]:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.post(
            AJAX_OPERAZIONI_MASSIVE_URL,
            data={
                "op": "get-rubrica-soggetti",
                "denominaz": quote("", safe=""),
                "cf": quote(identifier.strip().upper(), safe=""),
                "email": quote("", safe=""),
                "esitoUltimoInvio": quote("", safe=""),
                **_KENDO_FIRST_PAGE,
            },
            headers={**_AJAX_HEADERS, "Referer": f"{MAILING_LIST_URL}?token={token}&app=incass&tenant="},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="ajaxoperazionimassive")
        payload = self._decode_ajax_payload(response.text)
        rows = self._ajax_result_rows(payload)
        return [
            CapacitasInCassMailingSubjectRow.model_validate(row)
            for row in rows
            if isinstance(row, dict)
        ]

    async def fetch_mailing_contacts(self, subject_external_id: str) -> list[CapacitasInCassMailingContactRow]:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.post(
            AJAX_OPERAZIONI_MASSIVE_URL,
            data={
                "op": "get-rubrica-recapiti",
                "IDRubricaSoggetti": quote(subject_external_id, safe=""),
                **_KENDO_FIRST_PAGE,
            },
            headers={**_AJAX_HEADERS, "Referer": f"{MAILING_LIST_URL}?token={token}&app=incass&tenant="},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="ajaxoperazionimassive")
        payload = self._decode_ajax_payload(response.text)
        rows = self._ajax_result_rows(payload)
        return [
            CapacitasInCassMailingContactRow.model_validate(row)
            for row in rows
            if isinstance(row, dict)
        ]

    async def fetch_mailing_shipments(self, email: str) -> list[CapacitasInCassMailingShipmentRow]:
        http = self._manager.get_http_client()
        response = await http.post(
            AJAX_MAILING_LIST_URL,
            data={
                "op": "registro-PEC",
                "avviso": quote("", safe=""),
                "da": quote("", safe=""),
                "a": quote("", safe=""),
                "avvisoFiltro": quote("", safe=""),
                "cf": quote("", safe=""),
                "destinatario": quote(email.strip(), safe=""),
                "stato": quote("", safe=""),
                **_KENDO_FIRST_PAGE,
            },
            headers={**_AJAX_HEADERS, "Referer": DLG_SPEDIZIONI_URL},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="ajaxmailinglist")
        payload = self._decode_ajax_payload(response.text)
        rows = self._ajax_result_rows(payload)
        return [
            self._normalize_mailing_shipment(CapacitasInCassMailingShipmentRow.model_validate(row))
            for row in rows
            if isinstance(row, dict)
        ]

    async def fetch_mailing_receipt_parents(
        self,
        shipment: CapacitasInCassMailingShipmentRow,
    ) -> list[CapacitasInCassMailingReceiptParent]:
        if not shipment.external_id:
            return []
        http = self._manager.get_http_client()
        response = await http.post(
            AJAX_MAILING_LIST_URL,
            data={
                "op": "get-ricevute-pec",
                "id": quote(shipment.external_id, safe=""),
                "avviso": quote(shipment.avviso or "", safe=""),
                "dest": quote(shipment.recipient or "", safe=""),
                "oggetto": quote(shipment.subject or "", safe=""),
                "account": quote(shipment.campaign or "", safe=""),
                "codiceInvio": "" if shipment.send_code is None else str(shipment.send_code),
            },
            headers={**_AJAX_HEADERS, "Referer": DLG_SPEDIZIONI_URL},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="ajaxmailinglist")
        payload = self._decode_ajax_payload(response.text)
        if isinstance(payload, str):
            payload = self._decode_ajax_payload(payload)
        rows = payload if isinstance(payload, list) else []
        return [
            CapacitasInCassMailingReceiptParent.model_validate(row)
            for row in rows
            if isinstance(row, dict) and row.get("IDParent")
        ]

    async def fetch_objman_documents(
        self,
        receipt_parent: CapacitasInCassMailingReceiptParent,
    ) -> list[CapacitasObjManDocument]:
        if not receipt_parent.parent_id:
            return []
        http = self._manager.get_http_client()
        objman_url = await self._open_objman_dialog(receipt_parent)
        if objman_url is None:
            return []
        headers = {
            **_AJAX_HEADERS,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": objman_url,
        }
        response = await http.post(
            OBJMAN_XHR_ALLEGATI_URL,
            data={
                "op": "get-metadata",
                "IDRoot": receipt_parent.parent_id,
                "IDSubParent": receipt_parent.parent_id,
            },
            headers=headers,
        )
        response.raise_for_status()
        payload = self._decode_ajax_payload(response.text)
        rows = self._ajax_result_rows(payload)
        documents: list[CapacitasObjManDocument] = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("strID"):
                continue
            documents.append(CapacitasObjManDocument.model_validate({**row, "raw_json": row}))
        return documents

    async def download_objman_document(self, document: CapacitasObjManDocument, *, referer: str | None = None) -> bytes:
        http = self._manager.get_http_client()
        response = await http.post(
            OBJMAN_DOWNLOAD_URL,
            data={"op": "scarica-documento", "IDObj": document.object_id},
            headers={
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": referer or OBJMAN_BASE_URL,
            },
        )
        response.raise_for_status()
        return response.content

    async def _open_objman_dialog(self, receipt_parent: CapacitasInCassMailingReceiptParent) -> str | None:
        http = self._manager.get_http_client()
        response = await http.post(
            DLG_OBJMAN_URL,
            data={
                "IDDlg": "dlgObjManCodex",
                "idsParent": receipt_parent.parent_id,
                "gruppi": receipt_parent.group or "",
                "accounts": receipt_parent.account or "",
                "date": receipt_parent.date or "",
            },
            headers={**_AJAX_HEADERS, "Referer": DLG_SPEDIZIONI_URL},
        )
        response.raise_for_status()
        self._ensure_valid_app_response(response, expected_marker="dlgobjman")
        body = html.unescape(response.text or "")
        match = _OBJMAN_URL_RE.search(body)
        if match is None:
            return None
        objman_url = urljoin(OBJMAN_BASE_URL, match.group(0))
        if "idParent=" not in objman_url:
            dialog_vars = self._extract_js_string_vars(body)
            otp_payload = await self._fetch_objman_otp()
            if not otp_payload:
                return None
            objman_url = (
                f"{objman_url}?"
                + urlencode(
                    {
                        "idParent": receipt_parent.parent_id,
                        "idUser": dialog_vars.get("mstrIDUtente", ""),
                        "idApp": dialog_vars.get("mstrIDApp", ""),
                        "group": receipt_parent.group or "",
                        "title": dialog_vars.get("mstrTitolo", "inCass"),
                        "otp": otp_payload.get("OTP", ""),
                        "pin": otp_payload.get("PIN", ""),
                        "cons": otp_payload.get("CONS", ""),
                    }
                )
            )
        objman_response = await http.get(objman_url)
        objman_response.raise_for_status()
        return str(objman_response.url)

    @staticmethod
    def _decode_ajax_payload(text: str) -> object:
        cleaned = (text or "").strip()
        if not cleaned:
            return {}
        try:
            return decode_response(cleaned)
        except Exception:
            import json

            return json.loads(cleaned)

    @staticmethod
    def _ajax_result_rows(payload: object) -> list[object]:
        if isinstance(payload, dict):
            rows = payload.get("results")
        elif isinstance(payload, list):
            rows = payload
        else:
            rows = []
        return rows if isinstance(rows, list) else []

    @staticmethod
    def _extract_js_string_vars(text: str) -> dict[str, str]:
        return dict(re.findall(r'var\s+(mstr[A-Za-z0-9_]+)\s*=\s*"([^"]*)"', text or ""))

    async def _fetch_objman_otp(self) -> dict[str, str] | None:
        http = self._manager.get_http_client()
        response = await http.post(AJAX_MISC_URL, data={"op": "OTP"}, headers={**_AJAX_HEADERS, "Referer": DLG_OBJMAN_URL})
        response.raise_for_status()
        payload = self._decode_ajax_payload(response.text)
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            return {str(key): str(value) for key, value in payload[0].items()}
        if isinstance(payload, dict):
            rows = self._ajax_result_rows(payload)
            if rows and isinstance(rows[0], dict):
                return {str(key): str(value) for key, value in rows[0].items()}
        return None

    @staticmethod
    def _normalize_mailing_shipment(shipment: CapacitasInCassMailingShipmentRow) -> CapacitasInCassMailingShipmentRow:
        labels = []
        status = shipment.status_code or 0
        if status == 0:
            labels.append("Nessuna ricevuta rilevata")
        if status & 1:
            labels.append("Avviso di non accettazione")
        if status & 2:
            labels.append("Anomalia messaggio")
        if status & 4:
            labels.append("Accettazione")
        if status & 8:
            labels.append("Mancata consegna per superamento tempo massimo")
        if status & 16:
            labels.append("Avviso di mancata consegna")
        if status & 32:
            labels.append("Consegna")
        shipment.status_label = ", ".join(labels) if labels else None
        return shipment

    @staticmethod
    def _ensure_valid_app_response(response, *, expected_marker: str) -> None:
        final_url = str(response.url).lower()
        body = html.unescape(response.text or "").lower()
        if "sso.servizicapacitas.com/pages/login.aspx" in final_url or "name=\"txtusername\"" in body:
            raise CapacitasInCassSessionExpiredError("Sessione inCass scaduta: il portale ha rediretto sulla login SSO.")
        if "/pages/errore.aspx" in final_url:
            raise RuntimeError(f"inCass ha rediretto su errore.aspx durante la chiamata {expected_marker}.")
        if expected_marker not in final_url and "/pages/login.aspx" in final_url:
            raise CapacitasInCassSessionExpiredError(
                f"Sessione inCass non valida durante la chiamata {expected_marker}: URL finale inatteso {final_url}."
            )
