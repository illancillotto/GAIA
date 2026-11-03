"""Explicit accounting bridge in the existing annual PDF table, only for approved 2021 inputs."""

import html

from app.modules.ruolo.services.notice_summary import notice_summary_html


def accounting_rows(snapshot: dict | None, columns: int) -> str:
    if snapshot is None:
        return ""
    labels = (
        ("load", "Carico (emesso)"),
        ("residual", "Residuo contabile"),
        ("difference", "Differenza contabile F-J (non equivale a incasso)"),
        ("total", "Totale approvato prima delle spese"),
    )
    return "".join(
        f'<tr><td colspan="{columns - 1}">{label}</td><td>{html.escape(str(snapshot[key]).replace(".", ","))}</td></tr>'
        for key, label in labels
    )


def campaign_summary_html(rows, notification, payer, snapshot: dict | None) -> str:
    summary = notice_summary_html(rows, notification, payer)
    if snapshot is None:
        return summary
    marker = "<tr><td>Spese Notifica</td>"
    if summary.count(marker) != 1:
        raise ValueError("Riepilogo contabile non riconosciuto")
    return summary.replace(marker, accounting_rows(snapshot, summary.count("<th>")) + marker, 1)
