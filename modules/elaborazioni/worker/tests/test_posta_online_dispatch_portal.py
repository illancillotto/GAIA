from __future__ import annotations

from decimal import Decimal

import pytest

from posta_online_dispatch_portal import (
    PHASE_POSTS,
    allows_request,
    dwr_calls,
    parse_archive_rows,
    parse_draft_rows,
    parse_price,
)

COL = "https://corrispondenza.poste.it/col"
# Trimmed from the real "Verifica e invia" page of the 2026-10-28 test draft to the Consorzio.
REAL_DRAFT_PAGE = """
<table class="table table-striped table-hover table-full" style="" id="col_invio_dett">
<thead><tr><th class="thcenter"><input type="checkbox" id="checkAll"></th>
<th class="ThLeft sortable"><a href="/col/incorso.do?d-2780962-s=1">Identificativo</a></th>
<th>Nome spedizione</th><th>Data creazione</th><th>Stato</th><th>Prezzo</th><th>Anteprima</th>
<th>Modifica</th><th>Elimina</th></tr></thead>
<tbody>
<tr class="odd">
<td><div class="checkbox spacer-xs-0"><label class="checkbox-inline"><span class="custom-checkbox">
<input type="checkbox" id="12269236" value="" onclick="CleanErrorAreaCheckBox('12269236')" name="invioCheck">
</span></label></div></td>
<td style=""><a href="#" onclick="dettaglio('dettaglio.do', '12269236', '')">12269236</a></td>
<td style="">GAIA-PROVA-202610281901</td>
<td style="text-align:left;">28/10/2026 19:01</td>
<td style="">
<!-- Req-522-03 - AGGIUNTA COLONNA PREZZO -->
<div class="spacer-xs-bottom-0"><span class="counter text-basic">Prezzato</span></div>
</td>
<td style="">
        &euro;&nbsp;5,43
</td>
<td style="text-align:left"><a href="#" onclick="MostraAnteprima(800,600,'anteprimaPostaAR.do', 12269236);">
<img height="28px" title="Raccomandata online" alt="anteprima">&nbsp;&nbsp;Raccomandata online</a></td>
<td style="text-align:center"><a href="#" onclick="SubmitDoAction('modifica.do','12269236','')"></a></td>
<td style="text-align:center"><a href="#" onclick="DeleteInvio('12269236')"></a></td></tr></tbody></table>
"""
EMPTY_PAGE = '<table id="col_invio_dett"><tbody><tr><td colspan="9">Nulla da mostrare.</td></tr></tbody></table>'
ARCHIVE_PAGE = """<table class="table" id="col_invio_dett"><thead><tr><th>Identificativo</th></tr></thead><tbody>
<tr><td> <a href="#" onclick="SubmitDoAction('dettaglio.do','11280322','_self');" id="idInvio"> 11280322 </a> </td>
<td>GAIA 020217801062586</td><td>04/04/2025 07:56</td><td> &euro;&nbsp;5,37 </td>
<td><a onclick="SubmitDoAction('cancellaArchivio.do','11280322','_self');"></a></td></tr></tbody></table>"""


def _dwr(*calls: tuple[str, str]) -> str:
    lines = [f"callCount={len(calls)}"]
    for index, (script, method) in enumerate(calls):
        lines += [
            f"c{index}-scriptName={script}",
            f"c{index}-methodName={method}",
            f"c{index}-id=1",
        ]
    return "\n".join(lines)


@pytest.mark.parametrize("phase", ["login", *PHASE_POSTS])
@pytest.mark.parametrize("method", ["GET", "POST"])
def test_invia_payment_and_archive_deletion_are_denied_in_every_phase(phase, method):
    for endpoint in (
        "inserisciInvii.do",
        "paga.do",
        "carrello.do",
        "cancellaArchivio.do",
        "modifica.do",
    ):
        assert allows_request(phase, method, f"{COL}/{endpoint}", "") is False


def test_reads_and_login_traffic_are_allowed():
    assert allows_request("draft", "GET", f"{COL}/home.do", "") is True
    assert allows_request("reconcile", "HEAD", f"{COL}/incorso.do", "") is True
    assert allows_request("login", "POST", "https://idp-business.poste.it/cas/login", "") is True


def test_each_phase_allows_only_the_writes_it_needs():
    assert allows_request("draft", "POST", f"{COL}/invioDestinatari.do", "") is True
    for phase in ("addresses", "reconcile", "delete"):
        assert allows_request(phase, "POST", f"{COL}/invioDestinatari.do", "") is False
    assert allows_request("addresses", "POST", f"{COL}/autocomplete.do", "") is True
    assert allows_request("reconcile", "POST", f"{COL}/autocomplete.do", "") is False
    assert (
        allows_request("reconcile", "POST", f"{COL}/selezionaCheck.do?idSelezionato=1", "") is False
    )
    assert allows_request("unknown", "POST", f"{COL}/incorso.do", "") is False


def test_dwr_calls_are_checked_one_by_one():
    url = f"{COL}/dwr/call/plaincall/batch.dwr"
    assert dwr_calls(_dwr(("UtilHelper", "checkEnabled"))) == [("UtilHelper", "checkEnabled")]
    assert (
        allows_request(
            "draft",
            "POST",
            url,
            _dwr(("UtilHelper", "checkEnabled"), ("DestinatarioForm", "checkGo")),
        )
        is True
    )
    assert (
        allows_request(
            "draft",
            "POST",
            url,
            _dwr(("UtilHelper", "checkEnabled"), ("InviiColHelper", "eliminaInvio")),
        )
        is False
    )
    assert allows_request("delete", "POST", url, _dwr(("InviiColHelper", "eliminaInvio"))) is True
    assert allows_request("delete", "POST", url, _dwr(("InviiColHelper", "eliminaInvii"))) is False
    assert allows_request("draft", "POST", url, "no calls") is False


def test_real_draft_page_is_parsed():
    [row] = parse_draft_rows(REAL_DRAFT_PAGE)
    assert (row.draft_id, row.name, row.status, row.price) == (
        "12269236",
        "GAIA-PROVA-202610281901",
        "PREZZATO",
        Decimal("5.43"),
    )
    assert parse_draft_rows(EMPTY_PAGE) == []
    assert parse_draft_rows("<html>login</html>") == []


def test_archive_rows_and_prices_are_parsed():
    assert parse_archive_rows(ARCHIVE_PAGE) == [("11280322", "GAIA 020217801062586")]
    assert parse_price("€ 1.234,50") == Decimal("1234.50")
    assert parse_price("in lavorazione") is None
