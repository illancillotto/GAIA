from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import asyncio
import base64
import json
import zlib

import pytest

from app.modules.elaborazioni.capacitas.apps.incass.client import (
    CapacitasInCassSessionExpiredError,
    InCassClient,
)
from app.modules.elaborazioni.capacitas.apps.incass.parsers import (
    _is_same_parcel,
    _looks_like_partitario_separator,
    _parse_combined_row_tokens,
    _parse_detail_row_tokens,
    _parse_incass_domanda_surface_ha,
    _parse_partitario_header_spec,
    _parse_particella_row_by_columns,
    _parse_summary_row_tokens,
    parse_incass_partitario_dialog,
)
from app.modules.elaborazioni.capacitas.models import (
    CapacitasInCassMailingContactRow,
    CapacitasInCassMailingReceiptParent,
    CapacitasInCassMailingShipmentRow,
    CapacitasObjManDocument,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "incass"


class _FakeResponse:
    def __init__(
        self,
        text: str = "",
        *,
        url: str = "https://incass3.servizicapacitas.com/pages/test.aspx",
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.text = text
        self.url = url
        self.content = content if content is not None else text.encode("utf-8")
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        return None


class _FakeHttp:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict | None]] = []
        self.gets: list[tuple[str, dict | None]] = []

    async def get(self, url: str, params: dict | None = None, **_kwargs) -> _FakeResponse:
        self.gets.append((url, params))
        if url.endswith("/download/html-avviso.pdf"):
            return _FakeResponse(
                "<html>download</html>",
                url=url,
                content=b"<html>download</html>",
                headers={"content-type": "text/html; charset=utf-8"},
            )
        if url.endswith("/download/avviso.pdf"):
            return _FakeResponse(
                "",
                url=url,
                content=b"%PDF-avviso",
                headers={"content-type": "application/pdf"},
            )
        if "ricercaAvvisi.aspx" in url:
            return _FakeResponse("ricercaavvisi", url=url)
        if "dettaglioAvviso.aspx" in url:
            return _FakeResponse('<html><a href="/download/avviso.pdf">PDF</a></html>', url=url)
        if "mailingListOpMass.aspx" in url:
            return _FakeResponse("mailinglistopmass", url=url)
        if "objman.servizicapacitas.com" in url:
            return _FakeResponse("<html>objman</html>", url=url)
        return _FakeResponse("", url=url)

    async def post(self, url: str, data: dict | None = None, headers: dict | None = None) -> _FakeResponse:
        self.posts.append((url, data))
        op = (data or {}).get("op")
        if "ajaxRicerca.aspx" in url:
            return _FakeResponse(
                _capacitas_encoded_payload(
                    {
                        "rows": [
                            {
                                "Avviso": "020250001",
                                "Anno": "2025",
                                "Denominaz": "ROSSI MARIO",
                                "CodFisc": "RSSMRA80A01H501U",
                                "Carico": "10,00",
                                "Differenza": "10,00",
                            }
                        ]
                    }
                ),
                url=url,
            )
        if "dlgPartitarioKUI.aspx" in url:
            return _FakeResponse(PARTITARIO_SAMPLE_HTML, url=url)
        if op == "get-rubrica-soggetti":
            return _json_response(url, {"results": [{"strID": "sub-1", "strDenominaz": "ROSSI MARIO", "strCodFisc": "RSSMRA80A01H501U"}], "total": 1})
        if op == "get-rubrica-recapiti":
            return _json_response(url, {"results": [{"strID": "rec-1", "strEmail": "mario.rossi@examplepec.it", "strTipo": "PEC"}], "total": 1})
        if op == "registro-PEC":
            return _json_response(
                url,
                {
                    "results": [
                        {
                            "strID": "sped-1",
                            "intStato": 36,
                            "strAvviso": "020250001",
                            "strDestinatario": "mario.rossi@examplepec.it",
                            "strOggetto": "Emissione avviso",
                            "strAccount": "R2025-ML",
                            "intCodiceInvio": 0,
                        }
                    ],
                    "total": 1,
                },
            )
        if op == "get-ricevute-pec":
            return _json_response(url, [{"IDParent": "parent-1", "Gruppo": "CONSEGNA", "Account": "R2025-ML", "Data": "17/12/2021 20:01:58"}])
        if op == "OTP":
            return _json_response(url, [{"OTP": "otp-1", "PIN": "pin-1", "CONS": "090"}])
        if op == "get-metadata":
            return _json_response(
                url,
                {
                    "results": [
                        {
                            "strID": "obj-1",
                            "strMetadataIDParent": "parent-1",
                            "strMetadataFileName": "1637.eml",
                            "strMetadataGroup": "CONSEGNA",
                            "intMetadataFileSize": 12,
                        }
                    ],
                    "total": 1,
                },
            )
        if op == "scarica-documento":
            return _FakeResponse("", url=url, content=b"eml-bytes")
        if "dlgObjMan.aspx" in url:
            return _FakeResponse(
                """
                dlgobjman
                <script>
                var mstrObjManUrl = "https://objman.servizicapacitas.com/pages/allegati.aspx";
                var mstrIDApp = "app-1";
                var mstrIDUtente = "user-1";
                var mstrTitolo = "inCass";
                </script>
                """,
                url=url,
            )
        return _FakeResponse("", url=url)


def _json_response(url: str, payload: object) -> _FakeResponse:
    return _FakeResponse(json.dumps(payload), url=url)


def _capacitas_encoded_payload(payload: object) -> str:
    compressor = zlib.compressobj(wbits=-15)
    compressed = compressor.compress(json.dumps(payload).encode("utf-8")) + compressor.flush()
    return "SZ" + base64.b64encode(compressed).decode("ascii").rstrip("=")


class _FakeSessionManager:
    def __init__(self) -> None:
        self.http = _FakeHttp()
        self.closed = False
        self.logged_in = False
        self.activated_apps: list[str] = []
        self.keepalive_apps: list[str] = []

    def get_http_client(self) -> _FakeHttp:
        return self.http

    def get_token(self) -> str:
        return "token-1"

    async def close(self) -> None:
        self.closed = True

    async def login(self) -> None:
        self.logged_in = True

    async def activate_app(self, app: str) -> None:
        self.activated_apps.append(app)

    async def start_keepalive(self, app: str) -> None:
        self.keepalive_apps.append(app)


def _load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


PARTITARIO_SAMPLE_HTML = """\
<html>
  <body>
    <div class="kdlg-content">
      ================================================================================
      <br />ELENCO DELLE PARTITE SOGGETTE A CONTRIBUTO
      <br />================================================================================
      <br />Partita 000000402/00000 beni in comune di ARBOREA
      <br />Contribuente: Laore Sardegna                               C.F. 03122560927
      <br />Anno Trib Descrizione                                              Ruolo
      <br />2025 0648 Beni in ARBOREA - Contributo Opere Irrigue              17.288,12 euro
      <br />2025 0985 Beni in ARBOREA - Consorzio Quote Ordinarie             12.346,56 euro
      <br />Dom. Dis. Fog. Part.  Sub Sup.Cata.  Sup.Irr. Colt.     Manut.   Irrig.     Ist.
      <br />33    1    80          2.536                       9,26              6,61
      <br />26    2    10         10.880                      39,71             28,36
      <br />================================================================================
    </div>
  </body>
</html>
"""

PARTITARIO_WRAPPED_ROW_HTML = """\
<div id="divPart" style="font-family: Monospace;">
================================================================================<br />
ELENCO DELLE PARTITE SOGGETTE A CONTRIBUTO<br />
================================================================================<br />
Partita 0A0287663/00000 beni in comune di ZEDDIANI<br />
Contribuente: Porcu Giovanni                               C.F. PRCGNN65M02D947W<br />
Co-intestato con: Porcu Pier Antonio<br />
Anno Trib Descrizione                                              Ruolo<br />
2025 0648 Beni in ZEDDIANI - Contributo Opere Irrigue              771,18 euro<br />
2025 0668 Beni in ZEDDIANI - Contributo utenza                      70,00 euro<br />
2025 0985 Beni in ZEDDIANI - Consorzio Quote Ordinarie             550,75 euro<br />
Dom. Dis. Fog. Part.  Sub Sup.Cata.  Sup.Irr. Colt.     Manut.   Irrig.     Ist.<br />
7    6  1323          2.491                       9,09              6,49<br />
7    6  1325          2.334                       8,52              6,08<br />
7    6  1326            187                       0,68              0,49<br />
7    6  1327             51                       0,19              0,13<br />
7    6  1342          9.170                      33,47             23,91<br />
7    6  1346         10.947                      39,96             28,54<br />
7    6  1349        186.086                     679,26            485,11<br />
1598  7    6  1349        186.086     1.000 FRUTTETO             4,07<br />
Legenda:========================================================================<br />
</div>
"""

PARTITARIO_LARGE_CASE_HTML = """\
<div id="divPart" style="font-family: Monospace;">
================================================================================<br />
ELENCO DELLE PARTITE SOGGETTE A CONTRIBUTO<br />
================================================================================<br />
Partita 0A1616640/00000 beni in comune di ARBOREA<br />
Contribuente: Societa Ferraresi                               C.F. 00050540384<br />
Anno Trib Descrizione                                              Ruolo<br />
2025 0648 Beni in ARBOREA - Contributo Opere Irrigue              73.744,37 euro<br />
2025 0985 Beni in ARBOREA - Consorzio Quote Ordinarie             12.346,56 euro<br />
Dom. Dis. Fog. Part.  Sub Sup.Cata.  Sup.Irr. Colt.     Manut.   Irrig.     Ist.<br />
26 8 62 409.115 1.493,38 1.066,52<br />
6441 26 8 62 409.115 265.000 MEDICA 1 1.727,51<br />
5891 26 16 100 9.135 2.600 OLIVO 1 7,42<br />
Legenda:========================================================================<br />
</div>
"""

PARTITARIO_CONSUMPTION_BLOCK_HTML = """\
<div id="divPart" style="font-family: Monospace;">
================================================================================<br />
ELENCO DELLE PARTITE SOGGETTE A CONTRIBUTO<br />
================================================================================<br />
Partita 0A2468143/00000 beni in comune di TERRALBA<br />
Contribuente: Serra Claudio                               C.F. SRRCLD68P09G113D<br />
Anno Trib Descrizione                                              Ruolo<br />
2025 0648 Beni in TERRALBA - Contributo Opere Irrigue               30,00 euro<br />
2025 0668 Beni in TERRALBA - Contributo utenza                     364,99 euro<br />
2025 0985 Beni in TERRALBA - Consorzio Quote Ordinarie              20,00 euro<br />
Dom. Dis. Fog. Part.  Sub Sup.Cata.  Sup.Irr. Colt.     Manut.   Irrig.     Ist.<br />
28 8 1458 693 2,53 1,81<br />
28 8 1462 870 3,18 2,27<br />
Consumi da contatore: 30.416,000 mc Imposta: 364,99 euro (Tributo 0668)<br />
Anno Domanda Distretto Sup.Domanda Contatore Seriale Tessera Consumo (mc)<br />
2025 4381 28 671390 8.458,000<br />
2025 4382 28 678490 4.289,000<br />
2025 5892 28 680360 570,000<br />
2025 5893 28 680460 17.099,000<br />
Legenda:========================================================================<br />
</div>
"""

PARTITARIO_MIXED_SUMMARY_AND_DOMANDA_HTML = """\
<div id="divPart" style="font-family: Monospace;">
================================================================================<br />
ELENCO DELLE PARTITE SOGGETTE A CONTRIBUTO<br />
================================================================================<br />
Partita 000000402/00000 beni in comune di ARBOREA<br />
Contribuente: Laore Sardegna                               C.F. 03122560927<br />
Anno Trib Descrizione                                              Ruolo<br />
2025 0648 Beni in ARBOREA - Contributo Opere Irrigue              17.288,12 euro<br />
2025 0985 Beni in ARBOREA - Consorzio Quote Ordinarie             12.346,56 euro<br />
Dom. Dis. Fog. Part.  Sub Sup.Cata.  Sup.Irr. Colt.     Manut.   Irrig.     Ist.<br />
33    1    80          2.536                       9,26              6,61<br />
26    2    19        838.570                   3.061,00          2.186,06<br />
Partita 000000072/00000 beni in comune di SIAMAGGIORE<br />
Contribuente: Laore Sardegna                               C.F. 03122560927<br />
Anno Trib Descrizione                                              Ruolo<br />
2025 0648 Beni in SIAMAGGIORE - Contributo Opere Irrigue           66,56 euro<br />
2025 0668 Beni in SIAMAGGIORE - Contributo utenza                  70,00 euro<br />
2025 0985 Beni in SIAMAGGIORE - Consorzio Quote Ordinarie          47,53 euro<br />
Dom. Dis. Fog. Part.  Sub Sup.Cata.  Sup.Irr. Colt.     Manut.   Irrig.     Ist.<br />
3431 15 9 467 5.303 1.330 FRUTTETO 5,42<br />
3431 15 9 470 2.242 470 FRUTTETO 1,91<br />
Legenda:========================================================================<br />
</div>
"""


def test_parse_incass_partitario_dialog_extracts_partite_and_particelle() -> None:
    result = parse_incass_partitario_dialog(PARTITARIO_SAMPLE_HTML, avviso="020250007976220")

    assert result is not None
    assert result.avviso == "020250007976220"
    assert len(result.partite) == 1

    partita = result.partite[0]
    assert partita.codice_partita == "000000402/00000"
    assert partita.comune_nome == "ARBOREA"
    assert partita.contribuente == "Laore Sardegna"
    assert partita.contribuente_cf == "03122560927"
    assert partita.importo_0648_euro == "17.288,12"
    assert partita.importo_0985_euro == "12.346,56"
    assert len(partita.particelle) == 2
    assert partita.particelle[0].foglio == "1"
    assert partita.particelle[0].particella == "80"
    assert partita.particelle[0].distretto == "33"
    assert partita.particelle[0].sup_catastale_are == "2536"


def test_incass_mailing_models_parse_kendo_and_objman_payloads() -> None:
    contact = CapacitasInCassMailingContactRow.model_validate(
        {
            "strID": "rec-1",
            "strIDRubricaSoggetti": "sub-1",
            "strEmail": "utente@examplepec.it",
            "strTipo": "PEC",
            "dtDataIns": "/Date(1638188210000)/",
            "intAttivo": 1,
        }
    )
    shipment = CapacitasInCassMailingShipmentRow.model_validate(
        {
            "strID": "ship-1",
            "intStato": 36,
            "strAvviso": "02025000289160",
            "strOggetto": "Emissione avviso",
            "dtDataEvento": "/Date(1778147103000)/",
        }
    )
    document = CapacitasObjManDocument.model_validate(
        {
            "strID": "obj-1",
            "strMetadataIDParent": "parent-1",
            "strMetadataFileName": "1637.eml",
            "dtMetadataFileDateCreation": "/Date(1640260065000)/",
            "dtMetadataFileDateLastUpdate": "/Date(-62135596800000)/",
            "intMetadataFileSize": 479182,
        }
    )

    assert contact.inserted_at is not None
    assert contact.inserted_at.year == 2021
    assert shipment.event_at is not None
    assert shipment.status_code == 36
    assert document.created_at is not None
    assert document.updated_at is None
    assert document.filename == "1637.eml"


def test_incass_client_fetches_mailing_list_shipments_and_objman_documents() -> None:
    manager = _FakeSessionManager()
    client = InCassClient(manager)  # type: ignore[arg-type]

    async def scenario() -> None:
        await client.warmup_mailing_list_page()
        subjects = await client.search_mailing_subjects("RSSMRA80A01H501U")
        contacts = await client.fetch_mailing_contacts("sub-1")
        shipments = await client.fetch_mailing_shipments("mario.rossi@examplepec.it")
        parents = await client.fetch_mailing_receipt_parents(shipments[0])
        documents = await client.fetch_objman_documents(parents[0])
        content = await client.download_objman_document(documents[0])

        assert subjects[0].external_id == "sub-1"
        assert contacts[0].email == "mario.rossi@examplepec.it"
        assert shipments[0].status_label == "Accettazione, Consegna"
        assert parents[0].parent_id == "parent-1"
        assert documents[0].object_id == "obj-1"
        assert content == b"eml-bytes"
        receipt_post = next(data for _, data in manager.http.posts if (data or {}).get("op") == "get-ricevute-pec")
        assert receipt_post["codiceInvio"] == "0"
        assert any(
            "idParent=parent-1" in url and "otp=otp-1" in url and "cons=090" in url
            for url, _ in manager.http.gets
        )

    asyncio.run(scenario())


def test_incass_client_fetches_notices_detail_and_partitario() -> None:
    manager = _FakeSessionManager()
    client = InCassClient(manager)  # type: ignore[arg-type]

    async def scenario() -> None:
        await client.refresh_session()
        await client.warmup_search_page()
        result = await client.search_notices("rssmra80a01h501u")
        detail = await client.fetch_notice_detail("020250001")
        pdf_bytes = await client.download_notice_pdf(detail.pdf_links[0].url, referer=detail.detail_url)
        html_bytes = await client.download_notice_pdf("https://incass3.servizicapacitas.com/download/html-avviso.pdf")
        partitario = await client.fetch_notice_partitario("020250001")

        assert manager.closed is True
        assert manager.logged_in is True
        assert manager.activated_apps == ["incass"]
        assert manager.keepalive_apps == ["incass"]
        assert result.total == 1
        assert result.rows[0].avviso == "020250001"
        assert detail.pdf_links[0].filename == "avviso.pdf"
        assert pdf_bytes == b"%PDF-avviso"
        assert html_bytes == b"<html>download</html>"
        assert partitario is not None
        assert partitario.avviso == "020250001"

    asyncio.run(scenario())


def test_incass_client_handles_empty_and_nested_payload_branches() -> None:
    assert InCassClient._decode_ajax_payload("") == {}
    assert InCassClient._ajax_result_rows({"results": None}) == []
    assert InCassClient._ajax_result_rows({"results": "bad"}) == []
    assert InCassClient._ajax_result_rows({"results": [{"ok": True}]}) == [{"ok": True}]
    assert InCassClient._ajax_result_rows([{"ok": True}]) == [{"ok": True}]
    assert InCassClient._ajax_result_rows("bad") == []
    assert InCassClient._extract_js_string_vars('var mstrIDApp = "app-1";') == {"mstrIDApp": "app-1"}
    shipment = CapacitasInCassMailingShipmentRow(status_code=0)
    assert InCassClient._normalize_mailing_shipment(shipment).status_label == "Nessuna ricevuta rilevata"
    complex_status = CapacitasInCassMailingShipmentRow(status_code=27)
    assert InCassClient._normalize_mailing_shipment(complex_status).status_label == (
        "Avviso di non accettazione, Anomalia messaggio, "
        "Mancata consegna per superamento tempo massimo, Avviso di mancata consegna"
    )

    client = InCassClient(_FakeSessionManager())  # type: ignore[arg-type]

    async def scenario() -> None:
        assert await client.fetch_mailing_receipt_parents(CapacitasInCassMailingShipmentRow()) == []
        assert await client.fetch_objman_documents(CapacitasObjManDocument(object_id="obj-0")) == []

    asyncio.run(scenario())


def test_incass_client_handles_nested_receipt_payload_and_objman_missing_rows() -> None:
    class BranchHttp(_FakeHttp):
        async def post(self, url: str, data: dict | None = None, headers: dict | None = None) -> _FakeResponse:
            op = (data or {}).get("op")
            if op == "get-ricevute-pec":
                return _json_response(url, json.dumps([{"IDParent": "parent-2", "Gruppo": "ACCETTAZIONE"}]))
            if op == "OTP":
                return _json_response(url, {"results": [{"OTP": "otp-2", "PIN": "pin-2", "CONS": "090"}]})
            if op == "get-metadata":
                return _json_response(url, {"results": [{}, {"strID": "obj-2", "strMetadataFileName": "ok.eml"}]})
            if "dlgObjMan.aspx" in url:
                return _FakeResponse(
                    """
                    dlgobjman
                    <script>
                    var mstrObjManUrl = "https://objman.servizicapacitas.com/pages/allegati.aspx";
                    var mstrIDApp = "app-2";
                    var mstrIDUtente = "user-2";
                    var mstrTitolo = "inCass";
                    </script>
                    """,
                    url=url,
                )
            return await super().post(url, data=data, headers=headers)

    class BranchManager(_FakeSessionManager):
        def __init__(self) -> None:
            self.http = BranchHttp()

    client = InCassClient(BranchManager())  # type: ignore[arg-type]

    async def scenario() -> None:
        parents = await client.fetch_mailing_receipt_parents(
            CapacitasInCassMailingShipmentRow(external_id="sped-2")
        )
        documents = await client.fetch_objman_documents(parents[0])
        assert parents[0].parent_id == "parent-2"
        assert len(documents) == 1
        assert documents[0].object_id == "obj-2"

    asyncio.run(scenario())


def test_incass_client_objman_dialog_fallbacks() -> None:
    class MissingOtpHttp(_FakeHttp):
        async def post(self, url: str, data: dict | None = None, headers: dict | None = None) -> _FakeResponse:
            op = (data or {}).get("op")
            if op == "OTP":
                return _json_response(url, {"results": []})
            return await super().post(url, data=data, headers=headers)

    class MissingUrlHttp(_FakeHttp):
        async def post(self, url: str, data: dict | None = None, headers: dict | None = None) -> _FakeResponse:
            if "dlgObjMan.aspx" in url:
                return _FakeResponse("dlgobjman without objman url", url=url)
            return await super().post(url, data=data, headers=headers)

    class MissingOtpManager(_FakeSessionManager):
        def __init__(self) -> None:
            self.http = MissingOtpHttp()

    class MissingUrlManager(_FakeSessionManager):
        def __init__(self) -> None:
            self.http = MissingUrlHttp()

    client = InCassClient(MissingOtpManager())  # type: ignore[arg-type]
    missing_url_client = InCassClient(MissingUrlManager())  # type: ignore[arg-type]

    async def scenario() -> None:
        assert await client.fetch_objman_documents(CapacitasObjManDocument(object_id="obj-0")) == []
        assert await client._fetch_objman_otp() is None
        parent = CapacitasInCassMailingReceiptParent(parent_id="parent-0", group="CONSEGNA")
        assert await client.fetch_objman_documents(parent) == []
        assert await missing_url_client.fetch_objman_documents(parent) == []

    asyncio.run(scenario())


def test_incass_client_validates_expired_session_and_error_redirects() -> None:
    with pytest.raises(CapacitasInCassSessionExpiredError):
        InCassClient._ensure_valid_app_response(
            _FakeResponse('name="txtUsername"', url="https://sso.servizicapacitas.com/pages/login.aspx"),
            expected_marker="ajaxricerca",
        )
    with pytest.raises(RuntimeError, match="errore.aspx"):
        InCassClient._ensure_valid_app_response(
            _FakeResponse("", url="https://incass3.servizicapacitas.com/pages/errore.aspx"),
            expected_marker="ajaxricerca",
        )
    with pytest.raises(CapacitasInCassSessionExpiredError, match="URL finale inatteso"):
        InCassClient._ensure_valid_app_response(
            _FakeResponse("", url="https://incass3.servizicapacitas.com/pages/login.aspx"),
            expected_marker="ajaxricerca",
        )


def test_parse_incass_partitario_dialog_merges_wrapped_parcel_row() -> None:
    result = parse_incass_partitario_dialog(PARTITARIO_WRAPPED_ROW_HTML, avviso="020250028766300000")

    assert result is not None
    assert len(result.partite) == 1

    partita = result.partite[0]
    assert partita.codice_partita == "0A0287663/00000"
    assert len(partita.particelle) == 7

    last_row = partita.particelle[-1]
    assert last_row.domanda_irrigua == "1598"
    assert last_row.distretto == "7"
    assert last_row.foglio == "6"
    assert last_row.particella == "1349"
    assert last_row.sup_catastale_are == "186086"
    assert last_row.sup_irrigata_ha == "0.1"
    assert last_row.coltura == "FRUTTETO"
    assert last_row.importo_manut_euro == "679.26"
    assert last_row.importo_irrig_euro == "4.07"
    assert last_row.importo_ist_euro == "485.11"


def test_parse_incass_partitario_dialog_merges_large_case_split_row_and_parses_domanda_rows() -> None:
    result = parse_incass_partitario_dialog(PARTITARIO_LARGE_CASE_HTML, avviso="020250001616640")

    assert result is not None
    assert len(result.partite) == 1

    partita = result.partite[0]
    assert len(partita.particelle) == 2

    merged_row = partita.particelle[0]
    assert merged_row.domanda_irrigua == "6441"
    assert merged_row.distretto == "26"
    assert merged_row.foglio == "8"
    assert merged_row.particella == "62"
    assert merged_row.sup_catastale_are == "409115"
    assert merged_row.sup_irrigata_ha == "26.5"
    assert merged_row.coltura == "MEDICA"
    assert merged_row.importo_manut_euro == "1493.38"
    assert merged_row.importo_irrig_euro == "1727.51"
    assert merged_row.importo_ist_euro == "1066.52"

    standalone_row = partita.particelle[1]
    assert standalone_row.domanda_irrigua == "5891"
    assert standalone_row.distretto == "26"
    assert standalone_row.foglio == "16"
    assert standalone_row.particella == "100"
    assert standalone_row.sup_catastale_are == "9135"
    assert standalone_row.sup_irrigata_ha == "0.26"
    assert standalone_row.coltura == "OLIVO"
    assert standalone_row.importo_manut_euro is None
    assert standalone_row.importo_irrig_euro == "7.42"
    assert standalone_row.importo_ist_euro is None


def test_parse_incass_partitario_dialog_ignores_0668_consumption_block_rows() -> None:
    result = parse_incass_partitario_dialog(PARTITARIO_CONSUMPTION_BLOCK_HTML, avviso="020250024681430")

    assert result is not None
    assert len(result.partite) == 1

    partita = result.partite[0]
    assert len(partita.particelle) == 2
    assert [row.particella for row in partita.particelle] == ["1458", "1462"]
    assert all(row.foglio != "2025" for row in partita.particelle)


def test_parse_incass_partitario_dialog_keeps_summary_rows_without_fake_sup_irr() -> None:
    result = parse_incass_partitario_dialog(PARTITARIO_MIXED_SUMMARY_AND_DOMANDA_HTML, avviso="020250007976220")

    assert result is not None
    assert len(result.partite) == 2

    arborea = result.partite[0]
    assert arborea.comune_nome == "ARBOREA"
    assert len(arborea.particelle) == 2
    assert arborea.particelle[0].particella == "80"
    assert arborea.particelle[0].sup_catastale_are == "2536"
    assert arborea.particelle[0].sup_irrigata_ha is None
    assert arborea.particelle[0].importo_manut_euro == "9.26"
    assert arborea.particelle[0].importo_ist_euro == "6.61"
    assert arborea.particelle[1].particella == "19"
    assert arborea.particelle[1].sup_catastale_are == "838570"
    assert arborea.particelle[1].sup_irrigata_ha is None
    assert arborea.particelle[1].importo_manut_euro == "3061.00"
    assert arborea.particelle[1].importo_ist_euro == "2186.06"

    siamaggiore = result.partite[1]
    assert siamaggiore.comune_nome == "SIAMAGGIORE"
    assert len(siamaggiore.particelle) == 2
    assert siamaggiore.particelle[0].domanda_irrigua == "3431"
    assert siamaggiore.particelle[0].sup_catastale_are == "5303"
    assert siamaggiore.particelle[0].sup_irrigata_ha == "0.133"
    assert siamaggiore.particelle[0].coltura == "FRUTTETO"
    assert siamaggiore.particelle[1].sup_catastale_are == "2242"
    assert siamaggiore.particelle[1].sup_irrigata_ha == "0.047"


def test_parse_incass_partitario_dialog_skips_consumption_rows_for_any_year() -> None:
    html = PARTITARIO_CONSUMPTION_BLOCK_HTML.replace("2025 4381", "2026 4381").replace(
        "2025 4382", "2026 4382"
    ).replace("2025 5892", "2027 5892").replace("2025 5893", "2027 5893")
    result = parse_incass_partitario_dialog(html, avviso="020250024681430")

    assert result is not None
    partita = result.partite[0]
    assert [row.particella for row in partita.particelle] == ["1458", "1462"]
    assert all(row.foglio not in ("2025", "2026", "2027") for row in partita.particelle)


def test_real_fixture_pau_domanda_rows_assign_amounts_to_irrig() -> None:
    result = parse_incass_partitario_dialog(_load_fixture("partitario_pau.html"), avviso="T")

    assert result is not None
    assert len(result.partite) == 1
    rows = result.partite[0].particelle
    assert len(rows) == 16

    # La classe coltura "1" di "MAIS 1 I" non deve diventare un importo,
    # e l'unico importo delle righe domanda va nella colonna Irrig. (0668).
    assert all(row.importo_manut_euro is None for row in rows)
    assert all(row.importo_ist_euro is None for row in rows)
    assert all(row.coltura == "MAIS" for row in rows)
    irrig_total = sum(Decimal(row.importo_irrig_euro) for row in rows if row.importo_irrig_euro)
    assert irrig_total == Decimal("50.73")

    # La riga "40 28 9 1308 1 MAIS 1 I" (senza importi) non deve produrre
    # la particella fantasma foglio=28/particella=9.
    assert not any(row.foglio == "28" and row.particella == "9" for row in rows)
    row_1308 = next(row for row in rows if row.particella == "1308")
    assert row_1308.foglio == "9"
    assert row_1308.sup_catastale_are == "1"
    assert row_1308.importo_irrig_euro is None

    # Il blocco consumi in coda non deve generare particelle.
    assert not any(row.foglio == "2025" for row in rows)


def test_real_fixture_ferraresi_merges_summary_and_multi_coltura_details() -> None:
    result = parse_incass_partitario_dialog(_load_fixture("partitario_ferraresi.html"), avviso="T")

    assert result is not None
    rows = [row for partita in result.partite for row in partita.particelle]
    assert len(rows) == 118
    assert not any(row.importo_manut_euro == "1" for row in rows)

    # Stessa particella con più colture: ogni riga domanda resta distinta
    # e porta il proprio importo irriguo.
    fog16_part2 = [row for row in rows if row.foglio == "16" and row.particella == "2"]
    assert sorted(row.coltura for row in fog16_part2) == ["MAIS", "SOIA", "SORGO"]
    assert all(row.importo_irrig_euro is not None for row in fog16_part2)

    # Riconciliazione contabile: somma Manut. == totale 0648 e somma Ist. == totale
    # 0985 dichiarati in testa alla partita.
    for partita in result.partite:
        manut_total = sum(
            Decimal(row.importo_manut_euro) for row in partita.particelle if row.importo_manut_euro
        )
        ist_total = sum(
            Decimal(row.importo_ist_euro) for row in partita.particelle if row.importo_ist_euro
        )
        if partita.importo_0648_euro:
            expected_0648 = Decimal(partita.importo_0648_euro.replace(".", "").replace(",", "."))
            assert abs(manut_total - expected_0648) <= Decimal("0.05")
        if partita.importo_0985_euro:
            expected_0985 = Decimal(partita.importo_0985_euro.replace(".", "").replace(",", "."))
            assert abs(ist_total - expected_0985) <= Decimal("0.05")


def test_real_fixture_marrubiu_keeps_non_numeric_particella() -> None:
    result = parse_incass_partitario_dialog(_load_fixture("partitario_marrubiu.html"), avviso="T")

    assert result is not None
    rows = [row for partita in result.partite for row in partita.particelle]
    assert len(rows) == 729
    acque = [row for row in rows if row.particella == "acque"]
    assert len(acque) == 1
    assert acque[0].foglio == "6"
    assert acque[0].importo_manut_euro == "2.37"
    assert acque[0].importo_ist_euro == "1.69"


def test_real_fixture_consumption_only_partite_have_no_particelle() -> None:
    for name in ("partitario_angheleddu.html", "partitario_sanna.html"):
        result = parse_incass_partitario_dialog(_load_fixture(name), avviso="T")
        assert result is not None
        assert all(not partita.particelle for partita in result.partite), name


def test_token_fallback_parses_legacy_merged_and_combined_lines() -> None:
    # info_text storici a DB possono contenere righe già fuse dal parser
    # precedente, in due forme: riordinata a 10 token (manut/irrig/ist in coda)
    # e concatenata riepilogo+domanda. Entrambe devono produrre la stessa
    # particella fusa.
    legacy_text = "\n".join(
        [
            "Partita 0A0287663/00000 beni in comune di ZEDDIANI",
            "Contribuente: Porcu Giovanni C.F. PRCGNN65M02D947W",
            "2025 0648 Beni in ZEDDIANI - Contributo Opere Irrigue 771,18 euro",
            "Dom. Dis. Fog. Part. Sub Sup.Cata. Sup.Irr. Colt. Manut. Irrig. Ist.",
            "1598 7 6 1349 186.086 1.000 FRUTTETO 679,26 4,07 485,11",
            "7 6 1350 2.491 9,09 6,49 1599 7 6 1350 2.491 1.000 FRUTTETO 4,07",
        ]
    )
    result = parse_incass_partitario_dialog(legacy_text, avviso="T")

    assert result is not None
    rows = result.partite[0].particelle
    assert len(rows) == 2

    merged_10_tokens = rows[0]
    assert merged_10_tokens.particella == "1349"
    assert merged_10_tokens.importo_manut_euro == "679.26"
    assert merged_10_tokens.importo_irrig_euro == "4.07"
    assert merged_10_tokens.importo_ist_euro == "485.11"

    combined = rows[1]
    assert combined.particella == "1350"
    assert combined.domanda_irrigua == "1599"
    assert combined.coltura == "FRUTTETO"
    assert combined.importo_manut_euro == "9.09"
    assert combined.importo_irrig_euro == "4.07"
    assert combined.importo_ist_euro == "6.49"


def test_token_fallback_parses_subalterno_rows() -> None:
    collapsed_text = "\n".join(
        [
            "Partita 000000795/00000 beni in comune di TERRALBA",
            "Contribuente: Esempio C.F. 00587060955",
            "Dom. Dis. Fog. Part. Sub Sup.Cata. Sup.Irr. Colt. Manut. Irrig. Ist.",
            "28 20 12 c 15 0,05 0,04",
            "40 28 9 392 b 510 510 MAIS 1 I 3,32",
        ]
    )
    result = parse_incass_partitario_dialog(collapsed_text, avviso="T")

    assert result is not None
    rows = result.partite[0].particelle
    assert len(rows) == 2
    assert rows[0].subalterno == "c"
    assert rows[0].importo_manut_euro == "0.05"
    assert rows[0].importo_ist_euro == "0.04"
    assert rows[1].subalterno == "b"
    assert rows[1].importo_irrig_euro == "3.32"
    assert rows[1].importo_manut_euro is None


def test_garbage_rows_inside_table_are_skipped() -> None:
    collapsed_text = "\n".join(
        [
            "Partita 000000001/00000 beni in comune di ARBOREA",
            "Dom. Dis. Fog. Part. Sub Sup.Cata. Sup.Irr. Colt. Manut. Irrig. Ist.",
            "nota a margine non tabellare",
            "12 34",
            "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15",
            "33 1 80 2.536 9,26 6,61",
        ]
    )
    result = parse_incass_partitario_dialog(collapsed_text, avviso="T")

    assert result is not None
    rows = result.partite[0].particelle
    assert [row.particella for row in rows] == ["80"]


def test_parse_incass_partitario_dialog_handles_degenerate_inputs() -> None:
    assert parse_incass_partitario_dialog("", avviso="T") is None
    assert parse_incass_partitario_dialog("<div><br /></div>", avviso="T") is None

    # Testo senza alcuna partita: niente particelle ma info_text conservato.
    result = parse_incass_partitario_dialog("solo testo libero", avviso="T")
    assert result is not None
    assert result.partite == []
    assert result.info_text == "solo testo libero"


_CANONICAL_HEADER = (
    "Dom. Dis. Fog. Part.  Sub Sup.Cata.  Sup.Irr. Colt.     Manut.   Irrig.     Ist."
)


def _build_aligned_row(values: dict[str, str]) -> str:
    # Costruisce una riga monospace con i valori allineati a destra sul bordo
    # del titolo colonna (Colt. allineato a sinistra), come nella modale reale.
    spec = _parse_partitario_header_spec(_CANONICAL_HEADER)
    assert spec is not None
    row = [" "] * 90
    for name, start, end in spec:
        value = values.get(name)
        if value is None:
            continue
        offset = start if name == "Colt." else end - len(value)
        row[offset:offset + len(value)] = value
    return "".join(row).rstrip()


def test_header_spec_rejects_collapsed_or_unknown_headers() -> None:
    assert _parse_partitario_header_spec(_CANONICAL_HEADER) is not None
    # Header collassato: gli offset non sono affidabili.
    assert _parse_partitario_header_spec(" ".join(_CANONICAL_HEADER.split())) is None
    # Header con colonne diverse da quelle note.
    assert _parse_partitario_header_spec("Fog. Part.  Sup.Cata.  Altro") is None


def test_column_parser_guard_clauses_reject_malformed_rows() -> None:
    spec = _parse_partitario_header_spec(_CANONICAL_HEADER)
    assert spec is not None

    base_summary = {"Dis.": "31", "Fog.": "6", "Part.": "650", "Sup.Cata.": "650",
                    "Manut.": "2,37", "Ist.": "1,69"}
    base_detail = {"Dom.": "40", "Dis.": "28", "Fog.": "9", "Part.": "392",
                   "Sup.Cata.": "510", "Sup.Irr.": "510", "Colt.": "MAIS 1 I",
                   "Irrig.": "3,32"}
    assert _parse_particella_row_by_columns(_build_aligned_row(base_summary), spec) is not None
    assert _parse_particella_row_by_columns(_build_aligned_row(base_detail), spec) is not None

    rejected = [
        # token numerico fuori allineamento rispetto a ogni colonna
        " " * 55 + "99999999",
        # Dom. non numerico
        _build_aligned_row({**base_detail, "Dom.": "4a"}),
        # Dis. mancante / non numerico
        _build_aligned_row({k: v for k, v in base_summary.items() if k != "Dis."}),
        _build_aligned_row({**base_summary, "Dis.": "3x"}),
        # Fog. non numerico
        _build_aligned_row({**base_summary, "Fog.": "6y"}),
        # Part. non alfanumerica
        _build_aligned_row({**base_summary, "Part.": "2.536"}),
        # Sub non valido
        _build_aligned_row({**base_detail, "Sub": "9z"}),
        # Sup.Cata. mancante o malformata
        _build_aligned_row({k: v for k, v in base_summary.items() if k != "Sup.Cata."}),
        _build_aligned_row({**base_summary, "Sup.Cata.": "2,53"}),
        # Sup.Irr. malformata
        _build_aligned_row({**base_detail, "Sup.Irr.": "2,53"}),
        # importo malformato
        _build_aligned_row({**base_summary, "Manut.": "abc"}),
        # riga riepilogo con coltura/Irrig. (incoerente)
        _build_aligned_row({**base_summary, "Colt.": "MAIS"}),
        _build_aligned_row({**base_summary, "Irrig.": "1,00"}),
        # riga riepilogo senza uno dei due importi
        _build_aligned_row({k: v for k, v in base_summary.items() if k != "Ist."}),
        # riga domanda senza coltura o con Manut./Ist. (incoerente)
        _build_aligned_row({k: v for k, v in base_detail.items() if k != "Colt."}),
        _build_aligned_row({**base_detail, "Manut.": "1,00"}),
        # due token nella stessa colonna numerica
        "1 2 3 4 5 6",
    ]
    for raw in rejected:
        assert _parse_particella_row_by_columns(raw, spec) is None, raw


def test_token_parser_guard_clauses() -> None:
    # summary: numero token errato, dis/fog non numerici, sub non valido,
    # Sup.Cata. o importi non in formato atteso
    assert _parse_summary_row_tokens(["7", "6", "1323", "9,09", "6,49"]) is None
    assert _parse_summary_row_tokens(["a", "6", "1323", "2.491", "9,09", "6,49"]) is None
    assert _parse_summary_row_tokens(["7", "6", "1323", "12", "2.491", "9,09", "6,49"]) is None
    assert _parse_summary_row_tokens(["7", "6", "1323", "2,491", "9,09", "6,49"]) is None
    assert _parse_summary_row_tokens(["7", "6", "1323", "2.491", "1.000", "6,49"]) is None
    # detail: Sup.Cata. mancante, coltura mancante o senza lettere, importi in eccesso
    assert _parse_detail_row_tokens(["1", "2", "3", "4", "x9z"]) is None
    assert _parse_detail_row_tokens(["1", "2", "3", "4", "500", "600"]) is None
    assert _parse_detail_row_tokens(["1", "2", "3", "4", "500", "600", "123"]) is None
    # token lungo non-importo dopo la coltura
    assert _parse_detail_row_tokens(["1", "2", "3", "4", "500", "600", "MAIS", "GARBAGE"]) is None
    assert _parse_detail_row_tokens(
        ["1", "2", "3", "4", "500", "600", "MAIS", "1,00", "2,00", "3,00", "4,00"]
    ) is None
    # detail legacy con due importi -> manut/ist
    legacy = _parse_detail_row_tokens(
        ["1598", "7", "6", "1349", "186.086", "1.000", "FRUTTETO", "679,26", "485,11"]
    )
    assert legacy is not None
    assert str(legacy.importo_manut) == "679.26"
    assert legacy.importo_irrig is None
    assert str(legacy.importo_ist) == "485.11"
    # combined: parcelle non coerenti tra riepilogo e domanda
    assert _parse_combined_row_tokens(
        "7 6 1350 2.491 9,09 6,49 1599 7 6 9999 2.491 1.000 FRUTTETO 4,07".split()
    ) is None
    assert _parse_combined_row_tokens(
        "7 6 1350 2.491 9,09 6,49 1599 7 6 1350 9.999 1.000 FRUTTETO 4,07".split()
    ) is None
    # combined con subalterno: il riepilogo valido è quello a 7 token
    combined_sub = _parse_combined_row_tokens(
        "7 6 1350 b 2.491 9,09 6,49 1599 7 6 1350 2.491 1.000 FRUTTETO 4,07".split()
    )
    assert combined_sub is not None
    assert combined_sub.subalterno == "b"
    assert str(combined_sub.importo_manut) == "9.09"
    # combined dove la parte domanda non parsa in nessuno dei due split
    assert _parse_combined_row_tokens(
        "7 6 1350 2.491 9,09 6,49 x y z w k j h g".split()
    ) is None


def test_misc_guard_clauses() -> None:
    spec = _parse_partitario_header_spec(_CANONICAL_HEADER)
    assert spec is not None
    assert _parse_particella_row_by_columns("", spec) is None
    assert _looks_like_partitario_separator("") is True
    assert _looks_like_partitario_separator("=====") is True
    assert _looks_like_partitario_separator("testo") is False


def test_is_same_parcel_guards() -> None:
    summary = _parse_summary_row_tokens(["7", "6", "1350", "b", "2.491", "9,09", "6,49"])
    detail = _parse_detail_row_tokens(
        ["1599", "7", "6", "1350", "c", "2.491", "1.000", "FRUTTETO", "4,07"]
    )
    assert summary is not None and detail is not None
    # subalterni diversi
    assert _is_same_parcel(summary, detail) is False
    # distretto diverso
    other = _parse_summary_row_tokens(["8", "6", "1350", "2.491", "9,09", "6,49"])
    assert other is not None
    assert _is_same_parcel(other, detail) is False


def test_domanda_surface_ha_edge_cases() -> None:
    assert _parse_incass_domanda_surface_ha("") is None
    assert _parse_incass_domanda_surface_ha("   ") is None
    assert _parse_incass_domanda_surface_ha("12a") is None
    # valore già decimale: mantenuto senza conversione mq->ha
    assert str(_parse_incass_domanda_surface_ha("2,53")) == "2.53"
    assert str(_parse_incass_domanda_surface_ha("1.000")) == "0.1"


def test_collapsed_info_text_fallback_matches_column_parsing() -> None:
    # Il ripopolamento da DB può ripartire dall'info_text storico, che ha il
    # whitespace collassato: il fallback a token deve dare lo stesso risultato
    # del parse posizionale sull'HTML originale.
    raw = _load_fixture("partitario_pau.html")
    column_result = parse_incass_partitario_dialog(raw, avviso="T")
    assert column_result is not None

    collapsed = column_result.info_text
    assert collapsed is not None
    fallback_result = parse_incass_partitario_dialog(collapsed, avviso="T")
    assert fallback_result is not None

    def rows_key(result):
        return [
            (
                row.domanda_irrigua, row.distretto, row.foglio, row.particella,
                row.subalterno, row.sup_catastale_are, row.sup_irrigata_ha,
                row.coltura, row.importo_manut_euro, row.importo_irrig_euro,
                row.importo_ist_euro,
            )
            for partita in result.partite
            for row in partita.particelle
        ]

    assert rows_key(fallback_result) == rows_key(column_result)
