from __future__ import annotations

import logging
import re

import json5
from pydantic import BaseModel, ConfigDict, Field

from app.modules.elaborazioni.bonifica_oristanese.parsers import clean_html_text
from app.modules.elaborazioni.capacitas.apps import get_capacitas_app
from app.modules.elaborazioni.capacitas.decoder import decode_response
from app.modules.elaborazioni.capacitas.models import CapacitasAnagrafica
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager

logger = logging.getLogger(__name__)

INVOLTURE_APP = get_capacitas_app("involture")
CERTIFICATO_URL = f"{INVOLTURE_APP.base_url}/pages/rptCertificato.aspx"
DOMANDE_IRRIGAZ_URL = f"{INVOLTURE_APP.base_url}/pages/domandeIrrigaz.aspx"
AJAX_DOMANDE_IRRIGAZ_URL = f"{INVOLTURE_APP.base_url}/pages/ajax/ajaxDomandeIrrigaz.aspx"

_AJAX_HEADERS = {
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}


class CapacitasDomandaIrriguaRow(BaseModel):
    external_row_id: str | None = Field(default=None, alias="ID")
    autorinnovo: str | None = Field(default=None, alias="Autorinnovo")
    stato: str | None = Field(default=None, alias="Stato")
    stato_codice: str | None = Field(default=None, alias="StatoCodice")
    anno: str | None = Field(default=None, alias="Anno")
    cco: str | None = Field(default=None, alias="Cco")
    domanda: str | None = Field(default=None, alias="Domanda")
    data_ins: str | None = Field(default=None, alias="DataIns")
    tipo: str | None = Field(default=None, alias="Tipo")
    tipo_codice: str | None = Field(default=None, alias="TipoCodice")
    tipo_scheda_codice: str | None = Field(default=None, alias="TipoSchedaCodice")
    tipo_scheda: str | None = Field(default=None, alias="TipoScheda")
    pvc: str | None = Field(default=None, alias="Pvc")
    com: str | None = Field(default=None, alias="Com")
    fra: str | None = Field(default=None, alias="Fra")
    ccs: str | None = Field(default=None, alias="Ccs")
    ruolo_irr: str | None = Field(default=None, alias="RuoloIrr")
    tot_sup_cat: str | None = Field(default=None, alias="TotSupCat")
    tot_sup_irr: str | None = Field(default=None, alias="TotSupIrr")
    tot_sup_servita: str | None = Field(default=None, alias="TotSupServita")
    tot_sup_richiesta: str | None = Field(default=None, alias="TotSupRichiesta")
    tot_sup_malus: str | None = Field(default=None, alias="TotSupMalus")
    tot_sup_bonus: str | None = Field(default=None, alias="TotSupBonus")
    data_agg: str | None = Field(default=None, alias="DataAgg")
    data_rett: str | None = Field(default=None, alias="DataRett")
    data_sosp: str | None = Field(default=None, alias="DataSosp")
    data_chius: str | None = Field(default=None, alias="DataChius")
    comune: str | None = Field(default=None, alias="Comune")
    idxana: str | None = Field(default=None, alias="IDXAna")
    note: str | None = Field(default=None, alias="strNote")

    model_config = ConfigDict(populate_by_name=True)


class CapacitasDomandaIrriguaDetailRow(BaseModel):
    domanda_id: str | None = Field(default=None, alias="IDDomanda")
    external_row_id: str | None = Field(default=None, alias="ID")
    localita: str | None = Field(default=None, alias="Localita")
    comizio: str | None = Field(default=None, alias="Comizio")
    foglio: str | None = Field(default=None, alias="Foglio")
    particella: str | None = Field(default=None, alias="Partic")
    sub: str | None = Field(default=None, alias="Sub")
    sup_cat: str | None = Field(default=None, alias="SupCat")
    sup_irr: str | None = Field(default=None, alias="SupIrr")
    coltura: str | None = Field(default=None, alias="Coltura")
    part_pvc: str | None = Field(default=None, alias="PartPvc")
    part_com: str | None = Field(default=None, alias="PartCom")
    part_cco: str | None = Field(default=None, alias="PartCco")
    part_fra: str | None = Field(default=None, alias="PartFra")
    part_ccs: str | None = Field(default=None, alias="PartCcs")
    ruolo_bon: str | None = Field(default=None, alias="RuoloBon")
    ruolo_irr: str | None = Field(default=None, alias="RuoloIrr")
    ruolo_var: str | None = Field(default=None, alias="RuoloVar")
    note: str | None = Field(default=None, alias="Note")

    model_config = ConfigDict(populate_by_name=True)


class CapacitasDomandeIrrigueResult(BaseModel):
    cco: str | None = None
    com: str | None = None
    pvc: str | None = None
    fra: str | None = None
    ccs: str | None = None
    source_row_id: str | None = None
    source_idxana: str | None = None
    source_denominazione: str | None = None
    source_patrimonio: str | None = None
    patrimonio_has_domanda_hint: bool = False
    detail_op: str | None = None
    total_domande: int = 0
    domande: list[CapacitasDomandaIrriguaRow] = Field(default_factory=list)
    details_by_domanda_id: dict[str, list[CapacitasDomandaIrriguaDetailRow]] = Field(default_factory=dict)
    error: str | None = None


class CapacitasDomandeIrrigueBatchResult(BaseModel):
    source_total: int
    checked_records: int
    records_with_domande: int
    items: list[CapacitasDomandeIrrigueResult]


class DomandeIrrigueScraper:
    def __init__(self, session_manager: CapacitasSessionManager) -> None:
        self._manager = session_manager

    async def fetch_domande_irrigue(
        self,
        *,
        cco: str,
        com: str,
        pvc: str,
        fra: str,
        ccs: str,
        bc: str = "",
        include_details: bool = False,
    ) -> CapacitasDomandeIrrigueResult:
        await self._open_certificato_context(cco=cco, com=com, pvc=pvc, fra=fra, ccs=ccs, bc=bc)
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.get(
            DOMANDE_IRRIGAZ_URL,
            params={"BC": bc, "token": token, "app": "involture", "tenant": ""},
            headers={"Referer": _certificato_referer(token=token, cco=cco, com=com, pvc=pvc, fra=fra, ccs=ccs, bc=bc)},
        )
        response.raise_for_status()
        result = parse_domande_irrigue_html(response.text)
        result.cco = result.cco or cco
        result.com = result.com or com
        result.pvc = result.pvc or pvc
        result.fra = result.fra or fra
        result.ccs = result.ccs or ccs
        if include_details:
            await self._append_details(result, response.url)
        return result

    async def fetch_domanda_details(
        self,
        *,
        domanda_id: str,
        op: str = "detail-090",
        referer: object | None = None,
    ) -> list[CapacitasDomandaIrriguaDetailRow]:
        http = self._manager.get_http_client()
        response = await http.get(
            AJAX_DOMANDE_IRRIGAZ_URL,
            params={"op": op, "IDDomanda": domanda_id},
            headers={**_AJAX_HEADERS, "Referer": str(referer or DOMANDE_IRRIGAZ_URL)},
        )
        response.raise_for_status()
        payload = response.text.strip()
        try:
            decoded = decode_response(payload)
        except ValueError:
            decoded = payload
        return parse_domanda_irrigua_detail_rows(decoded)

    async def fetch_for_anagrafica_rows(
        self,
        rows: list[CapacitasAnagrafica],
        *,
        include_details: bool = False,
        continue_on_error: bool = True,
    ) -> CapacitasDomandeIrrigueBatchResult:
        items: list[CapacitasDomandeIrrigueResult] = []
        for row in rows:
            base = result_from_anagrafica_row(row)
            if not (row.cco and row.com and row.pvc and row.fraz):
                base.error = "Contesto Capacitas incompleto: richiesti CCO, COM, PVC e Fraz."
                items.append(base)
                if not continue_on_error:
                    raise RuntimeError(base.error)
                continue
            try:
                fetched = await self.fetch_domande_irrigue(
                    cco=row.cco,
                    com=row.com,
                    pvc=row.pvc,
                    fra=row.fraz,
                    ccs=row.sche or "00000",
                    include_details=include_details,
                )
                items.append(_merge_source_context(fetched, base))
            except Exception as exc:
                base.error = str(exc)
                items.append(base)
                if not continue_on_error:
                    raise
        return CapacitasDomandeIrrigueBatchResult(
            source_total=len(rows),
            checked_records=len(items),
            records_with_domande=sum(1 for item in items if item.total_domande > 0),
            items=items,
        )

    async def _append_details(self, result: CapacitasDomandeIrrigueResult, referer: object) -> None:
        detail_op = result.detail_op or "detail-090"
        for domanda in result.domande:
            if domanda.external_row_id:
                result.details_by_domanda_id[domanda.external_row_id] = await self.fetch_domanda_details(
                    domanda_id=domanda.external_row_id,
                    op=detail_op,
                    referer=referer,
                )

    async def _open_certificato_context(
        self,
        *,
        cco: str,
        com: str,
        pvc: str,
        fra: str,
        ccs: str,
        bc: str = "",
    ) -> None:
        http = self._manager.get_http_client()
        token = self._manager.get_token()
        response = await http.get(
            CERTIFICATO_URL,
            params={"CCO": cco, "COM": com, "PVC": pvc, "FRA": fra, "CCS": ccs, "BC": bc, "token": token, "app": "involture", "tenant": ""},
        )
        response.raise_for_status()


def parse_domande_irrigue_html(html: str) -> CapacitasDomandeIrrigueResult:
    rows = [_normalize_domanda_row(row) for row in _extract_load_data_grid_rows(html, grid_id="grdRis")]
    return CapacitasDomandeIrrigueResult(
        cco=_extract_optional_from_url_or_html(html, "CCO"),
        com=_extract_optional_from_url_or_html(html, "COM"),
        pvc=_extract_optional_from_url_or_html(html, "PVC"),
        fra=_extract_optional_from_url_or_html(html, "FRA"),
        ccs=_extract_optional_from_url_or_html(html, "CCS"),
        detail_op=_extract_detail_op(html),
        total_domande=len(rows),
        domande=rows,
    )


def parse_domanda_irrigua_detail_rows(payload: str | list | dict) -> list[CapacitasDomandaIrriguaDetailRow]:
    return [_normalize_detail_row(row) for row in _coerce_payload_rows(payload)]


def result_from_anagrafica_row(row: CapacitasAnagrafica) -> CapacitasDomandeIrrigueResult:
    return CapacitasDomandeIrrigueResult(
        cco=row.cco,
        com=row.com,
        pvc=row.pvc,
        fra=row.fraz,
        ccs=row.sche or "00000",
        source_row_id=row.id,
        source_idxana=row.id_ana,
        source_denominazione=row.denominazione,
        source_patrimonio=row.patrimonio,
        patrimonio_has_domanda_hint=patrimonio_has_domanda_hint(row.patrimonio),
    )


def patrimonio_has_domanda_hint(patrimonio: str | None) -> bool:
    return (patrimonio or "").strip().upper().endswith("D")


def _merge_source_context(
    result: CapacitasDomandeIrrigueResult,
    source: CapacitasDomandeIrrigueResult,
) -> CapacitasDomandeIrrigueResult:
    result.source_row_id = source.source_row_id
    result.source_idxana = source.source_idxana
    result.source_denominazione = source.source_denominazione
    result.source_patrimonio = source.source_patrimonio
    result.patrimonio_has_domanda_hint = source.patrimonio_has_domanda_hint
    return result


def _normalize_domanda_row(row: dict) -> CapacitasDomandaIrriguaRow:
    item = CapacitasDomandaIrriguaRow.model_validate(row)
    item.external_row_id = _strip_value(item.external_row_id)
    item.cco = _strip_value(item.cco)
    item.com = _strip_value(item.com)
    item.pvc = _strip_value(item.pvc)
    item.fra = _strip_value(item.fra)
    item.ccs = _strip_value(item.ccs)
    item.domanda = _strip_value(item.domanda)
    return item


def _normalize_detail_row(row: dict) -> CapacitasDomandaIrriguaDetailRow:
    item = CapacitasDomandaIrriguaDetailRow.model_validate(row)
    item.domanda_id = _strip_value(item.domanda_id)
    item.external_row_id = _strip_value(item.external_row_id)
    item.foglio = _strip_value(item.foglio)
    item.particella = _strip_value(item.particella)
    item.sub = _strip_value(item.sub)
    return item


def _extract_load_data_grid_rows(html: str, *, grid_id: str) -> list[dict]:
    match = re.search(
        rf'loadDataGridV2\(\s*jQuery\(["\']#{re.escape(grid_id)}["\']\)\s*,\s*'
        r'("(?:(?:\\.)|[^"\\])*"|\'(?:(?:\\.)|[^\'\\])*\')\s*(?:,\s*false)?\)',
        html,
        flags=re.DOTALL,
    )
    if not match:
        return []
    decoded = _decode_js_string_literal(match.group(1))
    return _parse_jsish_payload(decoded)


def _decode_js_string_literal(value: str) -> str:
    try:
        decoded = json5.loads(value)
        if isinstance(decoded, str):
            return decoded
    except Exception:
        logger.debug("Domande irrigue: fallback decode string literal", exc_info=True)
    return value[1:-1].encode("utf-8").decode("unicode_escape")


def _parse_jsish_payload(payload: str) -> list[dict]:
    cleaned = payload.strip().lstrip("\ufeff")
    if not cleaned:
        return []
    parsed = json5.loads(cleaned)
    if isinstance(parsed, dict):
        return [parsed]
    return [row for row in parsed if isinstance(row, dict)]


def _coerce_payload_rows(payload: str | list | dict) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        rows = payload.get("rows", payload.get("Rows"))
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
        return [payload]
    return _parse_jsish_payload(payload)


def _extract_detail_op(html: str) -> str | None:
    match = re.search(r'strOp\s*=\s*["\'](detail-\d{3})["\']', html)
    return match.group(1) if match else None


def _extract_optional_from_url_or_html(html: str, param: str) -> str | None:
    match = re.search(rf"(?:[?&]|&amp;){param}=([^&\"']+)", html)
    return match.group(1) if match else None


def _certificato_referer(*, token: str, cco: str, com: str, pvc: str, fra: str, ccs: str, bc: str) -> str:
    return (
        f"{CERTIFICATO_URL}?CCO={cco}&COM={com}&PVC={pvc}&FRA={fra}&CCS={ccs}"
        f"&BC={bc}&token={token}&app=involture&tenant="
    )


def _strip_value(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = clean_html_text(value)
    return stripped or None
