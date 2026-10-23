from app.modules.ruolo.services import tributi_reminder_service as reminder_service
from app.modules.ruolo.services.partitario_dialog import (
    is_empty_partitario_dialog,
    usable_partitario_text,
)

EMPTY_DIALOG_HTML = """<html><head><script type="text/javascript">
    var mstrAvvisoDlgPartitarioKUI = "020217801062586";
    $(function () { $("#btnScaricaPartitarioDlgPartitarioKUI").click(function (e) { }); });
</script></head><body><form>
<div id="boxContentDlgPartitarioKUI"><div id="divPart"><div id="fine"></div></div></div>
<button type="button">Chiudi</button><button type="button">Scarica</button>
</form></body></html>"""

PARTITARIO_HTML = (
    "<div>================================================================================<br>"
    "                     ELENCO DELLE PARTITE SOGGETTE A CONTRIBUTO<br>"
    "================================================================================<br>"
    "Partita 000000347/00000 beni in comune di ARBOREA<br>Chiudi<br>Scarica</div>"
)


def test_empty_incass_dialogs_are_recognised() -> None:
    assert is_empty_partitario_dialog(EMPTY_DIALOG_HTML)
    assert is_empty_partitario_dialog("Chiudi Scarica")
    assert is_empty_partitario_dialog("<div>&nbsp;</div>")
    assert not is_empty_partitario_dialog(PARTITARIO_HTML)
    assert not is_empty_partitario_dialog("Partita senza intestazione")
    assert usable_partitario_text(EMPTY_DIALOG_HTML) is None
    assert usable_partitario_text(PARTITARIO_HTML) == PARTITARIO_HTML


def test_notice_prints_only_avvisi_with_real_partite() -> None:
    payload = {
        "avvisi": [
            {"partitario": {"raw_html": PARTITARIO_HTML, "info_text": "ignored"}},
            {"partitario": {"raw_html": EMPTY_DIALOG_HTML, "info_text": "var x;\nChiudi\nScarica"}},
        ]
    }
    assert reminder_service._stored_partitario_lines(payload) == [
        "================================================================================",
        "                     ELENCO DELLE PARTITE SOGGETTE A CONTRIBUTO",
        "================================================================================",
        "Partita 000000347/00000 beni in comune di ARBOREA",
    ]
