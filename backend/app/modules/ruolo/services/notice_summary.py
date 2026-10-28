"""Printed annual summary, omitting interest only when every displayed amount is zero."""

import html
from decimal import Decimal

from app.modules.ruolo.services.payer_notice_cell import payer_notice_cell_html

_COLUMNS = (
    ("Anno_Ruolo", "Ruolo", "role"),
    ("Rif_Ruolo", "Numero avviso", "notice"),
    ("M_648", "0648 Opere irrigue", "opere"),
    ("M_668", "0668 Utenza", "utenza"),
    ("M_985", "0985 Quota istituzionale", "quota"),
    ("Magg_Applicate", "Magg.", "magg"),
    ("Interessi", "Interessi", "interessi"),
    ("Riscosso", "Somme versate", "versate"),
    ("Altre_Spese", "Altre spese", "spese"),
)


def _cell(row: dict[str, str], key: str, payer: dict | None) -> str:
    if key == "Rif_Ruolo":
        return f'<td class="notice-number">{payer_notice_cell_html(row[key], payer)}</td>'
    return f"<td>{html.escape(row.get(key, '0,00'))}</td>"


def notice_summary_html(rows: list[dict[str, str]], notification: str, payer: dict | None) -> str:
    has_interest = any(
        Decimal(row["Interessi"].replace(".", "").replace(",", ".")) != 0 for row in rows
    )
    columns = [column for column in _COLUMNS if column[0] != "Interessi" or has_interest]
    colgroup = "".join(f'<col class="{style}">' for _, _, style in columns)
    headings = "".join(f"<th>{title}</th>" for _, title, _ in columns)
    body = "".join(
        "<tr>" + "".join(_cell(row, key, payer) for key, _, _ in columns) + "</tr>" for row in rows
    )
    return (
        f'<table class="summary"><colgroup>{colgroup}</colgroup>'
        f"<thead><tr>{headings}</tr></thead><tbody>{body}"
        f'<tr><td>Spese Notifica</td><td colspan="{len(columns) - 2}"></td>'
        f"<td>{html.escape(notification)}</td></tr></tbody></table>"
    )
