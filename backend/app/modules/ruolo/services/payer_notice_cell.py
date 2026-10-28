"""Summary-table avviso cell of a reminder addressed to a payer other than the taxpayer."""

import html

from app.modules.ruolo.services.notice_number_cell import notice_numbers_html


def payer_notice_cell_html(numbers: str, payer: dict | None) -> str:
    """A reassigned avviso also names its registered taxpayer and why the payer owes it."""
    cell = notice_numbers_html(numbers)
    if not payer:
        return cell
    role = f"<br>dovuto come {html.escape(payer['role'])}" if payer.get("role") else ""
    return (
        f'{cell}<small style="display:block;white-space:normal;overflow-wrap:anywhere">'
        f"intestato a<br>{html.escape(payer['intestatario'])}{role}</small>"
    )
