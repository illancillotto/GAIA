#!/usr/bin/env python3
"""Generate GAIA data-model documentation and relationship diagrams.

The script reads SQLAlchemy metadata from the backend models and writes
print-oriented documentation under docs/data-model/.
"""

from __future__ import annotations

import csv
import asyncio
import base64
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
OUTPUT_DIR = REPO_ROOT / "docs" / "data-model"
TILED_OUTPUT_DIR = OUTPUT_DIR / "a3-tiled"


@dataclass(frozen=True)
class Domain:
    key: str
    label: str
    color: str
    description: str
    prefixes: tuple[str, ...]
    exact: tuple[str, ...] = ()


DOMAINS: tuple[Domain, ...] = (
    Domain(
        key="accessi",
        label="Accessi e permessi",
        color="#29524a",
        description="Gestisce utenti, ruoli, sezioni abilitate, inviti e accessi applicativi.",
        prefixes=("section", "role_section", "user_section", "permission", "effective_permission", "operator_invitation", "user_presence", "nas_"),
        exact=("application_users",),
    ),
    Domain(
        key="organigramma",
        label="Organigramma",
        color="#52796f",
        description="Rappresenta uffici, revisioni organizzative, assegnazioni e visibilita delle strutture.",
        prefixes=("org_",),
    ),
    Domain(
        key="presenze",
        label="Presenze",
        color="#0077b6",
        description="Raccoglie collaboratori, timbrature, giornaliere, squadre, turni e controlli operativi.",
        prefixes=("presenze_", "organization_team"),
    ),
    Domain(
        key="catasto",
        label="Catasto e GIS catastale",
        color="#8f5e15",
        description="Collega particelle, utenze irrigue, distretti, intestatari, letture e dati cartografici.",
        prefixes=("cat_", "catasto_", "capacitas_"),
    ),
    Domain(
        key="utenze",
        label="Utenze e anagrafiche",
        color="#7b2cbf",
        description="Normalizza persone, aziende, documenti, import anagrafici, ANPR e fonti esterne.",
        prefixes=("ana_", "anpr_", "bonifica_user"),
    ),
    Domain(
        key="ruolo",
        label="Ruolo e incassi",
        color="#b08968",
        description="Tiene traccia di partite, avvisi, particelle collegate e import del ruolo.",
        prefixes=("ruolo_",),
    ),
    Domain(
        key="operazioni",
        label="Operazioni sul campo",
        color="#d00000",
        description="Descrive attivita, squadre, mezzi, segnalazioni, allegati, carburante e sincronizzazioni mobile.",
        prefixes=(
            "activity_",
            "attachment",
            "field_report",
            "fleet_",
            "fuel_",
            "gate_mobile",
            "gps_",
            "internal_case",
            "mobile_sync",
            "operator_",
            "team",
            "vehicle",
            "wc_",
        ),
    ),
    Domain(
        key="riordino",
        label="Riordino fondiario",
        color="#386641",
        description="Gestisce pratiche, fasi, documenti, problemi, task, notifiche, ricorsi e collegamenti catastali.",
        prefixes=("riordino_",),
    ),
    Domain(
        key="network",
        label="Rete e dispositivi",
        color="#023e8a",
        description="Monitora dispositivi, scansioni, firewall, alert, planimetrie e soggetti tracciati.",
        prefixes=("network_", "device_", "floor_plan"),
    ),
    Domain(
        key="gis",
        label="Piattaforma GIS",
        color="#008000",
        description="Gestisce layer GIS, import shapefile, annotazioni, audit, permessi ed esportazioni.",
        prefixes=("gis_",),
    ),
    Domain(
        key="wiki",
        label="Wiki e assistente",
        color="#6c757d",
        description="Conserva conversazioni, richieste, chunk documentali, eventi, metriche e audit degli strumenti.",
        prefixes=("wiki_",),
    ),
    Domain(
        key="inventario",
        label="Inventario e magazzino",
        color="#bc6c25",
        description="Gestisce richieste di magazzino e collegamenti con segnalazioni operative.",
        prefixes=("warehouse_", "storage_"),
    ),
    Domain(
        key="sync",
        label="Sincronizzazioni e audit",
        color="#495057",
        description="Registra job, esecuzioni, snapshot, revisioni e condivisioni trasversali.",
        prefixes=("sync_", "snapshot", "review", "share", "elaborazione_"),
    ),
)

FALLBACK_DOMAIN = Domain(
    key="altro",
    label="Altro",
    color="#adb5bd",
    description="Tabelle di supporto non assegnate a un dominio principale.",
    prefixes=(),
)

BUSINESS_TERMS = {
    "application_users": "Utenti applicativi GAIA: account, ruolo globale e dati di accesso.",
    "org_unit": "Unita organizzative: uffici, aree o strutture interne.",
    "org_assignment": "Assegnazioni delle persone alle unita organizzative.",
    "presenze_daily_records": "Giornate di presenza elaborate per collaboratore.",
    "presenze_daily_punches": "Timbrature giornaliere provenienti dal sistema presenze.",
    "presenze_collaborators": "Collaboratori gestiti nel modulo presenze.",
    "organization_teams": "Squadre operative usate per coordinare personale e supervisori.",
    "cat_particelle": "Particelle catastali normalizzate.",
    "cat_utenze_irrigue": "Utenze irrigue collegate a import, particelle e intestatari.",
    "cat_delivery_points": "Punti di consegna o prelievo georeferenziati.",
    "catasto_meter_readings": "Letture contatori collegate al catasto e ai punti di consegna.",
    "ana_subjects": "Soggetti anagrafici normalizzati: persone o aziende.",
    "ana_persons": "Dati specifici delle persone fisiche.",
    "ana_companies": "Dati specifici delle aziende.",
    "ruolo_partite": "Partite del ruolo importate e collegate a soggetti e particelle.",
    "ruolo_avvisi": "Avvisi o posizioni economiche collegate al ruolo.",
    "field_report": "Segnalazioni dal territorio, con categoria, gravita, posizione e allegati.",
    "operator_activity": "Attivita operative registrate dagli operatori.",
    "vehicle": "Mezzi e veicoli usati nelle operazioni.",
    "wc_operator": "Operatori provenienti o allineati con White Company.",
    "wc_area": "Aree operative White Company.",
    "riordino_practices": "Pratiche principali del riordino fondiario.",
    "riordino_steps": "Passaggi operativi delle pratiche di riordino.",
    "network_devices": "Dispositivi di rete censiti o rilevati.",
    "network_alerts": "Alert prodotti dal monitoraggio rete.",
    "gis_layers": "Layer geografici pubblicati o gestiti dalla piattaforma GIS.",
    "gis_shapefile_imports": "Import shapefile e relativo stato di pubblicazione.",
    "wiki_conversations": "Conversazioni del wiki/assistente.",
    "wiki_requests": "Richieste operative o informative gestite dal wiki.",
    "sync_runs": "Esecuzioni di sincronizzazione o elaborazioni trasversali.",
    "sync_jobs": "Job di sincronizzazione pianificati o tracciati.",
}

WORD_LABELS = {
    "audit": "audit",
    "config": "configurazione",
    "credentials": "credenziali",
    "credential": "credenziale",
    "documents": "documenti",
    "document": "documento",
    "events": "eventi",
    "event": "evento",
    "history": "storico",
    "import": "importazione",
    "imports": "importazioni",
    "jobs": "job",
    "job": "job",
    "metrics": "metriche",
    "metric": "metrica",
    "permissions": "permessi",
    "permission": "permesso",
    "requests": "richieste",
    "request": "richiesta",
    "runs": "esecuzioni",
    "run": "esecuzione",
    "snapshots": "snapshot",
    "snapshot": "snapshot",
    "sync": "sincronizzazione",
}


def main() -> int:
    os.environ.setdefault("DATABASE_URL", "sqlite:///./gaia-docs-introspection.db")
    sys.path.insert(0, str(BACKEND_ROOT))

    from app.db import base as _base  # noqa: F401
    from app.core.database import Base

    metadata = Base.metadata
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TILED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tables = dict(sorted(metadata.tables.items(), key=lambda item: item[0]))
    domains_by_table = {name: classify_table(name) for name in tables}
    incoming = incoming_foreign_keys(tables)

    write_relationships_csv(tables, domains_by_table)
    write_relationships_guide(tables, domains_by_table, incoming)
    write_table_dictionary(tables, domains_by_table, incoming)
    write_domain_diagrams(tables, domains_by_table)
    write_a3_print_packs()
    write_a0_poster(tables, domains_by_table)
    write_readme(tables, domains_by_table)

    return 0


def classify_table(table_name: str) -> Domain:
    for domain in DOMAINS:
        if table_name in domain.exact or table_name.startswith(domain.prefixes):
            return domain
    return FALLBACK_DOMAIN


def incoming_foreign_keys(tables: dict) -> dict[str, list[tuple[str, str, str]]]:
    result: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for table in tables.values():
        for fk in sorted(table.foreign_keys, key=lambda item: item.parent.name):
            result[fk.column.table.name].append((table.name, fk.parent.name, fk.column.name))
    return result


def write_relationships_csv(tables: dict, domains_by_table: dict[str, Domain]) -> None:
    path = OUTPUT_DIR / "gaia_data_model_relationships.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "from_domain",
                "from_table",
                "from_column",
                "to_domain",
                "to_table",
                "to_column",
                "business_label",
            ]
        )
        for table in tables.values():
            for fk in sorted(table.foreign_keys, key=lambda item: (item.parent.name, item.column.table.name)):
                writer.writerow(
                    [
                        domains_by_table[table.name].label,
                        table.name,
                        fk.parent.name,
                        domains_by_table[fk.column.table.name].label,
                        fk.column.table.name,
                        fk.column.name,
                        relationship_label(table.name, fk.parent.name, fk.column.table.name),
                    ]
                )


def write_relationships_guide(tables: dict, domains_by_table: dict[str, Domain], incoming: dict[str, list[tuple[str, str, str]]]) -> None:
    html_path = OUTPUT_DIR / "GAIA_TABLE_RELATIONSHIPS_GUIDE.html"
    pdf_path = OUTPUT_DIR / "GAIA_TABLE_RELATIONSHIPS_GUIDE.pdf"
    html_path.write_text(build_relationships_guide_html(tables, domains_by_table, incoming), encoding="utf-8")
    render_pdf(
        html_path,
        pdf_path,
        paper_width=11.69,
        paper_height=8.27,
        fallback_landscape=True,
    )


def write_table_dictionary(tables: dict, domains_by_table: dict[str, Domain], incoming: dict[str, list[tuple[str, str, str]]]) -> None:
    path = OUTPUT_DIR / "GAIA_DATA_MODEL_DICTIONARY.md"
    lines: list[str] = []
    lines.append("# GAIA - Dizionario dati e relazioni")
    lines.append("")
    lines.append("Documento generato dai modelli SQLAlchemy del backend. E pensato per spiegare le tabelle in modo semplice, non per sostituire le migrazioni o il codice.")
    lines.append("")
    lines.append(f"- Tabelle rilevate: `{len(tables)}`")
    lines.append(f"- Relazioni foreign key rilevate: `{sum(len(table.foreign_keys) for table in tables.values())}`")
    lines.append("- Fonte: `backend/app/db/base.py` e modelli importati dalla metadata SQLAlchemy")
    lines.append("")

    for domain in (*DOMAINS, FALLBACK_DOMAIN):
        domain_tables = [name for name in tables if domains_by_table[name].key == domain.key]
        if not domain_tables:
            continue
        lines.append(f"## {domain.label}")
        lines.append("")
        lines.append(domain.description)
        lines.append("")
        lines.append("| Tabella | Spiegazione semplice | Chiave primaria | Colonne principali | Collegamenti in uscita | Collegamenti in entrata |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for table_name in domain_tables:
            table = tables[table_name]
            pk = ", ".join(column.name for column in table.primary_key.columns) or "-"
            fk_text = compact_html_list(
                [format_fk(fk) for fk in sorted(table.foreign_keys, key=lambda item: item.parent.name)]
            )
            incoming_text = compact_html_list(
                [format_incoming_fk(item) for item in sorted(incoming.get(table_name, []))]
            )
            lines.append(
                "| "
                + " | ".join(
                    [
                        code(table_name),
                        escape_md(describe_table(table_name)),
                        escape_md(pk),
                        escape_md(", ".join(important_columns(table)) or "-"),
                        fk_text,
                        incoming_text,
                    ]
                )
                + " |"
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_domain_diagrams(tables: dict, domains_by_table: dict[str, Domain]) -> None:
    for domain in DOMAINS:
        domain_tables = [name for name in tables if domains_by_table[name].key == domain.key]
        if not domain_tables:
            continue
        dot = build_domain_dot(domain, domain_tables, tables, domains_by_table)
        dot_path = OUTPUT_DIR / f"gaia_erd_{domain.key}.dot"
        svg_path = OUTPUT_DIR / f"gaia_erd_{domain.key}.svg"
        dot_path.write_text(dot, encoding="utf-8")
        render_dot(dot_path, svg_path)


def write_a0_poster(tables: dict, domains_by_table: dict[str, Domain]) -> None:
    dot_path = OUTPUT_DIR / "gaia_data_model_a0_map.dot"
    svg_path = OUTPUT_DIR / "gaia_data_model_a0_map.svg"
    dot_path.write_text(build_a0_domain_dot(tables, domains_by_table), encoding="utf-8")
    render_dot(dot_path, svg_path)

    svg = svg_path.read_text(encoding="utf-8") if svg_path.exists() else ""
    html_path = OUTPUT_DIR / "GAIA_DATA_MODEL_A0_POSTER.html"
    html_path.write_text(build_a0_html(svg, tables, domains_by_table), encoding="utf-8")
    render_pdf(
        html_path,
        OUTPUT_DIR / "GAIA_DATA_MODEL_A0_POSTER.pdf",
        paper_width=46.811,
        paper_height=33.11,
        fallback_landscape=True,
    )


def write_a3_print_packs() -> None:
    metrics = []
    for domain in DOMAINS:
        result = write_a3_print_pack(
            domain.key,
            domain.label,
            write_fit=domain.key == "catasto",
            write_legacy_catasto_alias=domain.key == "catasto",
        )
        if result:
            metrics.append(result)
    write_a3_print_check(metrics)


def write_a3_print_pack(
    domain_key: str,
    domain_label: str,
    *,
    write_fit: bool = False,
    write_legacy_catasto_alias: bool = False,
) -> dict[str, str | float] | None:
    svg_path = OUTPUT_DIR / f"gaia_erd_{domain_key}.svg"
    if not svg_path.exists():
        return None

    raw_svg = svg_path.read_text(encoding="utf-8")
    inline_svg = sanitize_inline_svg(raw_svg)
    viewbox = read_svg_viewbox(raw_svg)
    if viewbox is None:
        return None

    width, height = viewbox
    title = f"GAIA ERD {domain_label}"
    fit_html_path = OUTPUT_DIR / f"gaia_erd_{domain_key}_A3_fit.html"
    fit_pdf_path = OUTPUT_DIR / f"gaia_erd_{domain_key}_A3_fit.pdf"
    borders_html_path = OUTPUT_DIR / f"gaia_erd_{domain_key}_A3_borders.html"
    borders_pdf_path = OUTPUT_DIR / f"gaia_erd_{domain_key}_A3_borders.pdf"
    four_up_html_path = TILED_OUTPUT_DIR / f"gaia_erd_{domain_key}_A3_4up.html"
    four_up_pdf_path = TILED_OUTPUT_DIR / f"gaia_erd_{domain_key}_A3_4up.pdf"

    if write_fit:
        fit_html_path.write_text(build_a3_fit_html(title, inline_svg), encoding="utf-8")
        render_pdf(
            fit_html_path,
            fit_pdf_path,
            paper_width=11.69,
            paper_height=16.54,
            fallback_landscape=False,
        )

    borders_html = build_a3_borders_html(title, inline_svg, width, height)
    borders_html_path.write_text(borders_html, encoding="utf-8")
    render_pdf(
        borders_html_path,
        borders_pdf_path,
        paper_width=11.69,
        paper_height=16.54,
        fallback_landscape=False,
    )

    if write_legacy_catasto_alias:
        legacy_html_path = OUTPUT_DIR / f"gaia_erd_{domain_key}_A3_page1_borders.html"
        legacy_pdf_path = OUTPUT_DIR / f"gaia_erd_{domain_key}_A3_page1_borders.pdf"
        legacy_html_path.write_text(borders_html, encoding="utf-8")
        render_pdf(
            legacy_html_path,
            legacy_pdf_path,
            paper_width=11.69,
            paper_height=16.54,
            fallback_landscape=False,
        )
        four_up_html_path.write_text(build_a3_4up_html(title, inline_svg, width, height), encoding="utf-8")
        render_pdf(
            four_up_html_path,
            four_up_pdf_path,
            paper_width=11.69,
            paper_height=16.54,
            fallback_landscape=False,
        )

    natural_height_mm = 281.0 * (height / width)
    limiter = "altezza" if natural_height_mm > 388.0 else "larghezza"
    scale_percent = min(100.0, 388.0 / natural_height_mm * 100.0) if natural_height_mm else 0.0
    return {
        "domain_key": domain_key,
        "domain_label": domain_label,
        "width": width,
        "height": height,
        "ratio": height / width if width else 0.0,
        "natural_height_mm": natural_height_mm,
        "limiter": limiter,
        "scale_percent": scale_percent,
        "html": borders_html_path.name,
        "pdf": borders_pdf_path.name,
    }


def write_a3_print_check(metrics: list[dict[str, str | float]]) -> None:
    path = OUTPUT_DIR / "GAIA_ERD_A3_PRINT_CHECK.md"
    lines = [
        "# GAIA - Verifica stampa A3 diagrammi ERD",
        "",
        "Report generato dagli SVG ERD. Tutti i PDF A3 con bordi contengono il diagramma intero, senza ritagli.",
        "",
        "| Dominio | SVG viewBox | Rapporto H/W | Altezza naturale su 281 mm | Limite in A3 | Scala indicativa | PDF A3 | HTML A3 |",
        "| --- | ---: | ---: | ---: | --- | ---: | --- | --- |",
    ]
    for item in metrics:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["domain_label"]),
                    f'{float(item["width"]):.0f} x {float(item["height"]):.0f}',
                    f'{float(item["ratio"]):.2f}',
                    f'{float(item["natural_height_mm"]):.0f} mm',
                    str(item["limiter"]),
                    f'{float(item["scale_percent"]):.0f}%',
                    f'[{item["pdf"]}]({item["pdf"]})',
                    f'[{item["html"]}]({item["html"]})',
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Nota: quando il limite e `altezza`, il diagramma e molto verticale e su A3 risulta piu piccolo. In quel caso la soluzione migliore e rigenerare il layout Graphviz in modo piu compatto/orizzontale, non ritagliare il PDF.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(tables: dict, domains_by_table: dict[str, Domain]) -> None:
    path = OUTPUT_DIR / "README.md"
    domain_rows = []
    for domain in (*DOMAINS, FALLBACK_DOMAIN):
        count = sum(1 for item in domains_by_table.values() if item.key == domain.key)
        if count:
            domain_rows.append(f"| {domain.label} | {count} | {domain.description} |")

    diagram_links = []
    a3_links = []
    for domain in DOMAINS:
        if any(item.key == domain.key for item in domains_by_table.values()):
            diagram_links.append(f"- [{domain.label}](gaia_erd_{domain.key}.svg)")
            a3_links.append(f"- [{domain.label} A3 con bordi](gaia_erd_{domain.key}_A3_borders.pdf)")

    content = f"""# GAIA - Data model per stampa e condivisione

Questa cartella contiene una vista divulgativa del modello dati GAIA.
I file sono generati con `scripts/generate_data_model_docs.py` leggendo la metadata SQLAlchemy del backend.

## File principali

- [Poster A0 HTML](GAIA_DATA_MODEL_A0_POSTER.html): versione pensata per stampa A0 orizzontale.
- [Poster A0 PDF](GAIA_DATA_MODEL_A0_POSTER.pdf): esportazione pronta per stampa, se Chrome/Chromium era disponibile durante la generazione.
- [Guida relazioni HTML](GAIA_TABLE_RELATIONSHIPS_GUIDE.html): nomi tabella, chiavi primarie e collegamenti spiegati in modo semplice.
- [Guida relazioni PDF](GAIA_TABLE_RELATIONSHIPS_GUIDE.pdf): versione A4 orizzontale multipagina della guida relazioni.
- [Catasto ERD A3 completo](gaia_erd_catasto_A3_fit.pdf): diagramma Catasto completo adattato su una pagina A3.
- [Catasto ERD A3 completo con bordi](gaia_erd_catasto_A3_borders.pdf): diagramma Catasto intero adattato su A3 con bordi di riferimento.
- [Catasto ERD poster 4 A3](a3-tiled/gaia_erd_catasto_A3_4up.pdf): diagramma Catasto ingrandito e diviso in 4 fogli A3.
- [Verifica stampa A3 ERD](GAIA_ERD_A3_PRINT_CHECK.md): controllo dimensioni SVG e leggibilita indicativa su A3.
- [Mappa A0 SVG](gaia_data_model_a0_map.svg): mappa macro tra domini funzionali.
- [Dizionario dati](GAIA_DATA_MODEL_DICTIONARY.md): descrizioni semplici, chiavi e collegamenti per ogni tabella.
- [Relazioni CSV](gaia_data_model_relationships.csv): elenco completo delle foreign key.

## Domini rilevati

| Dominio | Tabelle | Cosa racconta |
| --- | ---: | --- |
{chr(10).join(domain_rows)}

## Diagrammi di dettaglio

{chr(10).join(diagram_links)}

## PDF A3 con bordi

{chr(10).join(a3_links)}

## Rigenerazione

```bash
PYTHONPATH=backend python scripts/generate_data_model_docs.py
```

Il generatore usa `dot` se disponibile per produrre SVG. Se `dot` non e installato, restano comunque disponibili i file `.dot`, il CSV e il dizionario Markdown.
Se Chrome o Chromium e disponibile, viene generato anche il PDF A0.
"""
    path.write_text(content, encoding="utf-8")


def build_relationships_guide_html(tables: dict, domains_by_table: dict[str, Domain], incoming: dict[str, list[tuple[str, str, str]]]) -> str:
    total_fk = sum(len(table.foreign_keys) for table in tables.values())
    domain_sections = []
    for domain in (*DOMAINS, FALLBACK_DOMAIN):
        domain_tables = [name for name in tables if domains_by_table[name].key == domain.key]
        if not domain_tables:
            continue
        rows = []
        for table_name in domain_tables:
            table = tables[table_name]
            outgoing_count = len(table.foreign_keys)
            incoming_count = len(incoming.get(table_name, []))
            rows.append(
                "<tr>"
                f"<td><code>{html.escape(table_name)}</code></td>"
                f"<td>{html.escape(describe_table(table_name))}</td>"
                f"<td>{html.escape(primary_key_text(table))}</td>"
                f"<td>{html.escape(primary_key_explanation(table))}</td>"
                f"<td>{outgoing_count} uscite / {incoming_count} entrate</td>"
                "</tr>"
            )
        domain_sections.append(
            f"""
            <section class="domain">
              <h2 style="--accent:{domain.color}">{html.escape(domain.label)}</h2>
              <p>{html.escape(domain.description)}</p>
              <table>
                <thead>
                  <tr>
                    <th>Nome tabella</th>
                    <th>Cosa contiene</th>
                    <th>Chiave primaria</th>
                    <th>Spiegazione semplice della chiave</th>
                    <th>Collegamenti</th>
                  </tr>
                </thead>
                <tbody>{''.join(rows)}</tbody>
              </table>
            </section>
            """
        )

    relationship_rows = []
    for table in tables.values():
        for fk in sorted(table.foreign_keys, key=lambda item: (item.parent.name, item.column.table.name)):
            relationship_rows.append(
                "<tr>"
                f"<td>{html.escape(domains_by_table[table.name].label)}</td>"
                f"<td><code>{html.escape(table.name)}</code></td>"
                f"<td><code>{html.escape(fk.parent.name)}</code></td>"
                f"<td>{html.escape(domains_by_table[fk.column.table.name].label)}</td>"
                f"<td><code>{html.escape(fk.column.table.name)}</code></td>"
                f"<td><code>{html.escape(fk.column.name)}</code></td>"
                f"<td>{html.escape(simple_relationship_text(table.name, fk.parent.name, fk.column.table.name, fk.column.name))}</td>"
                "</tr>"
            )

    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>GAIA - Guida relazioni tra tabelle</title>
  <style>
    @page {{ size: A4 landscape; margin: 10mm; }}
    :root {{
      --ink: #17212b;
      --muted: #5d6875;
      --paper: #fbfaf6;
      --line: #d9d2c3;
      --header: #233d4d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: "DejaVu Sans", Verdana, sans-serif;
      font-size: 9.4pt;
      line-height: 1.35;
    }}
    header {{
      padding: 12mm 14mm 7mm;
      color: white;
      background:
        radial-gradient(circle at 15% 10%, rgba(255,255,255,0.22), transparent 26%),
        linear-gradient(120deg, #233d4d, #52796f);
    }}
    h1 {{
      margin: 0 0 4mm;
      font-size: 24pt;
      letter-spacing: -0.5pt;
    }}
    header p {{
      max-width: 220mm;
      margin: 0;
      font-size: 10.5pt;
    }}
    .stats {{
      display: flex;
      gap: 5mm;
      margin-top: 7mm;
    }}
    .stat {{
      min-width: 32mm;
      padding: 3mm 4mm;
      border: 0.3mm solid rgba(255,255,255,0.45);
      border-radius: 3mm;
      background: rgba(255,255,255,0.12);
    }}
    .stat strong {{
      display: block;
      font-size: 18pt;
      line-height: 1;
    }}
    main {{
      padding: 9mm 12mm 14mm;
    }}
    .guide-note {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 5mm;
      margin-bottom: 8mm;
    }}
    .note {{
      border: 0.3mm solid var(--line);
      border-radius: 3mm;
      background: white;
      padding: 4mm;
    }}
    .note strong {{
      color: var(--header);
    }}
    h2 {{
      break-after: avoid;
      margin: 9mm 0 3mm;
      padding-left: 3mm;
      border-left: 2mm solid var(--accent, #52796f);
      font-size: 15pt;
    }}
    p {{
      color: var(--muted);
      margin: 0 0 3mm;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 0 0 6mm;
      background: white;
      break-inside: auto;
    }}
    thead {{
      display: table-header-group;
    }}
    tr {{
      break-inside: avoid;
    }}
    th, td {{
      border: 0.25mm solid var(--line);
      padding: 2mm 2.2mm;
      vertical-align: top;
    }}
    th {{
      background: #edf2f4;
      color: #233d4d;
      text-align: left;
      font-size: 8.6pt;
      text-transform: uppercase;
      letter-spacing: 0.35pt;
    }}
    code {{
      font-family: "DejaVu Sans Mono", Consolas, monospace;
      font-size: 8.6pt;
      color: #1b4965;
      word-break: break-word;
    }}
    .relationships h2 {{
      margin-top: 12mm;
    }}
    .relationships table {{
      font-size: 8.5pt;
    }}
    .relationships th, .relationships td {{
      padding: 1.6mm 1.8mm;
    }}
    .page-break {{
      break-before: page;
    }}
  </style>
</head>
<body>
  <header>
    <h1>GAIA - Relazioni tra tabelle e chiavi primarie</h1>
    <p>Guida per leggere il modello dati senza entrare nel codice: ogni riga mostra il nome reale della tabella, il dato che conserva, la sua chiave primaria e i collegamenti verso altre tabelle.</p>
    <div class="stats">
      <div class="stat"><strong>{len(tables)}</strong>tabelle</div>
      <div class="stat"><strong>{total_fk}</strong>relazioni</div>
      <div class="stat"><strong>{len(DOMAINS)}</strong>domini principali</div>
    </div>
  </header>
  <main>
    <section class="guide-note">
      <div class="note"><strong>Tabella:</strong> e un contenitore di dati omogenei, per esempio utenti, particelle, presenze o segnalazioni.</div>
      <div class="note"><strong>Chiave primaria:</strong> e il codice interno che identifica una riga in modo univoco. Di solito si chiama <code>id</code>.</div>
      <div class="note"><strong>Relazione:</strong> una colonna di una tabella punta alla chiave di un'altra tabella, cosi GAIA sa collegare i dati.</div>
    </section>
    {''.join(domain_sections)}
    <section class="relationships page-break">
      <h2>Elenco completo delle relazioni</h2>
      <p>Ogni riga indica una foreign key: la colonna nella tabella di partenza conserva il riferimento alla tabella di destinazione.</p>
      <table>
        <thead>
          <tr>
            <th>Dominio origine</th>
            <th>Tabella origine</th>
            <th>Colonna che collega</th>
            <th>Dominio destinazione</th>
            <th>Tabella destinazione</th>
            <th>Chiave destinazione</th>
            <th>Significato semplice</th>
          </tr>
        </thead>
        <tbody>{''.join(relationship_rows)}</tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def build_a3_fit_html(title: str, inline_svg: str) -> str:
    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)} - A3 completo</title>
  <style>
    @page {{ size: A3 portrait; margin: 0; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: #f7f3ea;
      color: #17212b;
      font-family: "DejaVu Sans", Verdana, sans-serif;
    }}
    .page {{
      width: 297mm;
      height: 420mm;
      padding: 8mm;
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: 4mm;
      overflow: hidden;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 8mm;
      align-items: end;
      border-bottom: 0.35mm solid #d7c9ae;
      padding-bottom: 3mm;
    }}
    h1 {{
      margin: 0;
      font-size: 15pt;
      letter-spacing: -0.2pt;
    }}
    .hint {{
      margin: 0;
      color: #5c6770;
      font-size: 8.5pt;
      text-align: right;
    }}
    .canvas {{
      min-height: 0;
      border: 0.3mm solid #d7c9ae;
      background: white;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }}
    .canvas svg {{
      max-width: 100%;
      max-height: 100%;
      width: auto;
      height: auto;
    }}
    footer {{
      color: #5c6770;
      font-size: 8pt;
      display: flex;
      justify-content: space-between;
    }}
  </style>
</head>
<body>
  <section class="page">
    <header>
      <h1>{html.escape(title)} - vista completa A3</h1>
      <p class="hint">Tutto il diagramma in una sola pagina. Per maggiore leggibilita usa anche la versione a tasselli.</p>
    </header>
    <main class="canvas">{inline_svg}</main>
    <footer>
      <span>Fonte: metadata SQLAlchemy GAIA</span>
      <span>Formato: A3 verticale</span>
    </footer>
  </section>
</body>
</html>
"""


def build_a3_borders_html(title: str, inline_svg: str, viewbox_width: float, viewbox_height: float) -> str:
    content_width_mm = 281.0
    content_height_mm = 388.0
    diagram_height_mm = content_width_mm * (viewbox_height / viewbox_width)

    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)} - A3 completo con bordi</title>
  <style>
    @page {{ size: A3 portrait; margin: 0; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: #f7f3ea;
      color: #17212b;
      font-family: "DejaVu Sans", Verdana, sans-serif;
    }}
    .page {{
      width: 297mm;
      height: 420mm;
      padding: 8mm;
      display: grid;
      grid-template-rows: auto {content_height_mm:.2f}mm auto;
      gap: 3mm;
      overflow: hidden;
      border: 1.2mm solid #233d4d;
      background:
        linear-gradient(#f7f3ea, #f7f3ea) padding-box,
        repeating-linear-gradient(45deg, #233d4d 0 2mm, #d7c9ae 2mm 4mm) border-box;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      border-bottom: 0.5mm solid #233d4d;
      padding-bottom: 2mm;
    }}
    h1 {{
      margin: 0;
      font-size: 14pt;
      letter-spacing: -0.2pt;
    }}
    header p {{
      margin: 0;
      color: #5c6770;
      font-size: 9pt;
    }}
    .viewport {{
      width: {content_width_mm:.2f}mm;
      height: {content_height_mm:.2f}mm;
      background: white;
      border: 0.7mm solid #233d4d;
      outline: 0.35mm dashed #b08968;
      outline-offset: -4mm;
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }}
    .viewport::before,
    .viewport::after {{
      content: "";
      position: absolute;
      z-index: 2;
      pointer-events: none;
    }}
    .viewport::before {{
      inset: 6mm;
      border: 0.25mm dotted #52796f;
    }}
    .viewport::after {{
      left: 0;
      right: 0;
      top: 50%;
      border-top: 0.2mm dashed rgba(35, 61, 77, 0.45);
    }}
    .diagram {{
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .diagram svg {{
      display: block;
      max-width: calc(100% - 10mm);
      max-height: calc(100% - 10mm);
      width: auto;
      height: auto;
    }}
    footer {{
      display: flex;
      justify-content: space-between;
      color: #5c6770;
      font-size: 8pt;
      border-top: 0.35mm solid #d7c9ae;
      padding-top: 1.5mm;
    }}
  </style>
</head>
<body>
  <section class="page">
    <header>
      <h1>{html.escape(title)} - A3 completo con bordi</h1>
      <p>Diagramma intero adattato alla pagina</p>
    </header>
    <main class="viewport">
      <div class="diagram">{inline_svg}</div>
    </main>
    <footer>
      <span>Area stampabile con bordo: {content_width_mm:.0f} x {content_height_mm:.0f} mm</span>
      <span>Altezza naturale alla larghezza piena: {diagram_height_mm:.0f} mm</span>
    </footer>
  </section>
</body>
</html>
"""


def build_a3_4up_html(title: str, inline_svg: str, viewbox_width: float, viewbox_height: float) -> str:
    tile_width_mm = 281.0
    tile_height_mm = 388.0
    poster_width_mm = tile_width_mm * 2
    poster_height_mm = tile_height_mm * 2
    diagram_height_by_poster = poster_height_mm
    diagram_width_by_poster = diagram_height_by_poster * (viewbox_width / viewbox_height)
    if diagram_width_by_poster > poster_width_mm:
        diagram_width_mm = poster_width_mm
        diagram_height_mm = diagram_width_mm * (viewbox_height / viewbox_width)
    else:
        diagram_width_mm = diagram_width_by_poster
        diagram_height_mm = diagram_height_by_poster
    diagram_left_mm = (poster_width_mm - diagram_width_mm) / 2
    diagram_top_mm = (poster_height_mm - diagram_height_mm) / 2

    pages = []
    labels = {
        (0, 0): ("1/4", "alto sinistra"),
        (1, 0): ("2/4", "alto destra"),
        (0, 1): ("3/4", "basso sinistra"),
        (1, 1): ("4/4", "basso destra"),
    }
    for row in range(2):
        for col in range(2):
            label, position = labels[(col, row)]
            pages.append(
                f"""
                <section class="page">
                  <header>
                    <h1>{html.escape(title)} - poster 4 A3</h1>
                    <p>Foglio {label} - {position}</p>
                  </header>
                  <main class="viewport">
                    <div class="poster" style="transform: translate(-{col * tile_width_mm:.2f}mm, -{row * tile_height_mm:.2f}mm);">
                      <div class="diagram">{inline_svg}</div>
                    </div>
                    <div class="tile-label">{label}</div>
                  </main>
                  <footer>
                    <span>Assembla in griglia 2 x 2</span>
                    <span>{position}</span>
                  </footer>
                </section>
                """
            )

    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)} - poster 4 A3</title>
  <style>
    @page {{ size: A3 portrait; margin: 0; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: #f7f3ea;
      color: #17212b;
      font-family: "DejaVu Sans", Verdana, sans-serif;
    }}
    .page {{
      width: 297mm;
      height: 420mm;
      padding: 8mm;
      display: grid;
      grid-template-rows: auto {tile_height_mm:.2f}mm auto;
      gap: 3mm;
      break-after: page;
      overflow: hidden;
      border: 1.2mm solid #233d4d;
      background:
        linear-gradient(#f7f3ea, #f7f3ea) padding-box,
        repeating-linear-gradient(45deg, #233d4d 0 2mm, #d7c9ae 2mm 4mm) border-box;
    }}
    .page:last-child {{
      break-after: auto;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      border-bottom: 0.5mm solid #233d4d;
      padding-bottom: 2mm;
    }}
    h1 {{
      margin: 0;
      font-size: 14pt;
      letter-spacing: -0.2pt;
    }}
    header p {{
      margin: 0;
      color: #5c6770;
      font-size: 9pt;
    }}
    .viewport {{
      width: {tile_width_mm:.2f}mm;
      height: {tile_height_mm:.2f}mm;
      overflow: hidden;
      background: white;
      border: 0.7mm solid #233d4d;
      outline: 0.35mm dashed #b08968;
      outline-offset: -4mm;
      position: relative;
    }}
    .poster {{
      position: absolute;
      left: 0;
      top: 0;
      width: {poster_width_mm:.2f}mm;
      height: {poster_height_mm:.2f}mm;
      transform-origin: top left;
      background: white;
    }}
    .poster::before {{
      content: "";
      position: absolute;
      inset: 0;
      border-right: 0.35mm dashed rgba(35, 61, 77, 0.55);
      border-bottom: 0.35mm dashed rgba(35, 61, 77, 0.55);
      width: {tile_width_mm:.2f}mm;
      height: {tile_height_mm:.2f}mm;
      pointer-events: none;
      z-index: 3;
    }}
    .poster::after {{
      content: "";
      position: absolute;
      left: {tile_width_mm:.2f}mm;
      top: 0;
      width: {tile_width_mm:.2f}mm;
      height: {tile_height_mm:.2f}mm;
      border-bottom: 0.35mm dashed rgba(35, 61, 77, 0.55);
      pointer-events: none;
      z-index: 3;
    }}
    .diagram {{
      position: absolute;
      left: {diagram_left_mm:.2f}mm;
      top: {diagram_top_mm:.2f}mm;
      width: {diagram_width_mm:.2f}mm;
      height: {diagram_height_mm:.2f}mm;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .diagram svg {{
      display: block;
      width: {diagram_width_mm:.2f}mm;
      height: auto;
    }}
    .tile-label {{
      position: absolute;
      right: 5mm;
      top: 5mm;
      z-index: 5;
      padding: 1.5mm 2.5mm;
      border: 0.3mm solid #233d4d;
      border-radius: 2mm;
      background: rgba(247, 243, 234, 0.88);
      color: #233d4d;
      font-weight: 700;
      font-size: 10pt;
    }}
    footer {{
      display: flex;
      justify-content: space-between;
      color: #5c6770;
      font-size: 8pt;
      border-top: 0.35mm solid #d7c9ae;
      padding-top: 1.5mm;
    }}
  </style>
</head>
<body>
  {''.join(pages)}
</body>
</html>
"""


def sanitize_inline_svg(raw_svg: str) -> str:
    svg = re.sub(r"<\?xml[^>]*>\s*", "", raw_svg, count=1)
    svg = re.sub(r"<!DOCTYPE[^>]*(?:\[[\s\S]*?\]\s*)?>\s*", "", svg, count=1)
    return svg.strip()


def read_svg_viewbox(raw_svg: str) -> tuple[float, float] | None:
    match = re.search(r'viewBox="[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)"', raw_svg)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def build_a0_domain_dot(tables: dict, domains_by_table: dict[str, Domain]) -> str:
    domain_counts = Counter(domain.key for domain in domains_by_table.values())
    fk_counts = Counter()
    for table in tables.values():
        source_domain = domains_by_table[table.name]
        for fk in table.foreign_keys:
            target_domain = domains_by_table[fk.column.table.name]
            if source_domain.key != target_domain.key:
                fk_counts[(source_domain.key, target_domain.key)] += 1

    lines = [
        "digraph GAIADataModelA0 {",
        '  graph [rankdir=LR, splines=true, overlap=false, bgcolor="transparent", pad="0.35", nodesep="0.65", ranksep="1.2"];',
        '  node [shape=plain, fontname="DejaVu Sans"];',
        '  edge [fontname="DejaVu Sans", fontsize=13, color="#495057", arrowsize=0.7];',
    ]

    for domain in DOMAINS:
        if domain_counts[domain.key] == 0:
            continue
        label = html_table_label(
            title=domain.label,
            subtitle=f"{domain_counts[domain.key]} tabelle",
            body=domain.description,
            color=domain.color,
        )
        lines.append(f'  "{domain.key}" [label=<{label}>];')

    for (source, target), count in sorted(fk_counts.items(), key=lambda item: (-item[1], item[0])):
        if count < 2:
            continue
        lines.append(f'  "{source}" -> "{target}" [label="{count} collegamenti", penwidth="{min(5, 1 + count / 5):.1f}"];')

    lines.append("}")
    return "\n".join(lines) + "\n"


def build_domain_dot(domain: Domain, domain_tables: list[str], tables: dict, domains_by_table: dict[str, Domain]) -> str:
    external_tables: set[str] = set()
    edges: list[tuple[str, str, str]] = []
    domain_set = set(domain_tables)
    for table_name in domain_tables:
        table = tables[table_name]
        for fk in table.foreign_keys:
            target = fk.column.table.name
            edges.append((table_name, target, fk.parent.name))
            if target not in domain_set:
                external_tables.add(target)
        for other in tables.values():
            if other.name in domain_set:
                continue
            for fk in other.foreign_keys:
                if fk.column.table.name == table_name:
                    external_tables.add(other.name)
                    edges.append((other.name, table_name, fk.parent.name))

    lines = [
        f"digraph GAIAERD_{domain.key} {{",
        '  graph [rankdir=LR, splines=true, overlap=false, bgcolor="transparent", pad="0.25", nodesep="0.45", ranksep="0.9"];',
        '  node [shape=plain, fontname="DejaVu Sans"];',
        '  edge [fontname="DejaVu Sans", fontsize=10, color="#495057", arrowsize=0.6];',
    ]

    for table_name in domain_tables:
        label = table_label(tables[table_name], domain.color, describe_table(table_name))
        lines.append(f'  "{table_name}" [label=<{label}>];')
    for table_name in sorted(external_tables):
        if table_name not in tables:
            continue
        external_domain = domains_by_table[table_name]
        label = table_label(tables[table_name], "#e9ecef", f"Riferimento esterno: {external_domain.label}", text_color="#343a40")
        lines.append(f'  "{table_name}" [label=<{label}>];')

    seen_edges = set()
    for source, target, column in sorted(edges):
        edge_key = (source, target, column)
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        lines.append(f'  "{source}" -> "{target}" [label="{escape_dot(column)}"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


def build_a0_html(svg: str, tables: dict, domains_by_table: dict[str, Domain]) -> str:
    domain_cards = []
    for domain in DOMAINS:
        count = sum(1 for item in domains_by_table.values() if item.key == domain.key)
        if not count:
            continue
        domain_cards.append(
            f"""
            <section class="card" style="--accent:{domain.color}">
              <h3>{html.escape(domain.label)}</h3>
              <p><strong>{count}</strong> tabelle</p>
              <p>{html.escape(domain.description)}</p>
            </section>
            """
        )

    total_fk = sum(len(table.foreign_keys) for table in tables.values())
    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>GAIA - Mappa dati A0</title>
  <style>
    @page {{ size: 1189mm 841mm; margin: 0; }}
    :root {{
      --ink: #182026;
      --muted: #5c6770;
      --paper: #f8f4ec;
      --line: #d7c9ae;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }}
    .poster {{
      width: 1189mm;
      height: 841mm;
      padding: 24mm;
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: 18mm;
      background:
        radial-gradient(circle at 10% 10%, rgba(0, 119, 182, 0.12), transparent 26%),
        radial-gradient(circle at 92% 18%, rgba(143, 94, 21, 0.14), transparent 30%),
        linear-gradient(135deg, #fbf7ef 0%, #f1eadb 100%);
      overflow: hidden;
    }}
    header {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 20mm;
      align-items: end;
      border-bottom: 1.2mm solid var(--line);
      padding-bottom: 8mm;
    }}
    h1 {{
      font-size: 34mm;
      line-height: 0.92;
      margin: 0;
      letter-spacing: -1.5mm;
    }}
    .subtitle {{
      max-width: 330mm;
      color: var(--muted);
      font-size: 8mm;
      line-height: 1.25;
      margin: 6mm 0 0;
    }}
    .stats {{
      display: flex;
      gap: 8mm;
      font-family: "DejaVu Sans", sans-serif;
    }}
    .stat {{
      min-width: 50mm;
      padding: 5mm 7mm;
      border: 0.6mm solid var(--line);
      border-radius: 5mm;
      background: rgba(255,255,255,0.55);
      text-align: center;
    }}
    .stat strong {{
      display: block;
      font-size: 15mm;
      line-height: 1;
    }}
    .stat span {{
      font-size: 4mm;
      text-transform: uppercase;
      letter-spacing: 0.8mm;
      color: var(--muted);
    }}
    main {{
      display: grid;
      grid-template-columns: 1fr 310mm;
      gap: 16mm;
      min-height: 0;
    }}
    .map {{
      padding: 8mm;
      border-radius: 8mm;
      border: 0.8mm solid var(--line);
      background: rgba(255,255,255,0.45);
      overflow: hidden;
    }}
    .map svg {{
      width: 100%;
      height: 100%;
    }}
    aside {{
      display: grid;
      grid-template-rows: auto 1fr;
      gap: 8mm;
    }}
    h2 {{
      font-size: 12mm;
      margin: 0;
      font-family: "DejaVu Sans", sans-serif;
    }}
    .cards {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 5mm;
      align-content: start;
    }}
    .card {{
      min-height: 39mm;
      padding: 5mm;
      border-left: 2.3mm solid var(--accent);
      background: rgba(255,255,255,0.68);
      border-radius: 4mm;
      box-shadow: 0 1mm 4mm rgba(36, 29, 20, 0.08);
    }}
    .card h3 {{
      margin: 0 0 2mm;
      font-family: "DejaVu Sans", sans-serif;
      font-size: 5mm;
    }}
    .card p {{
      margin: 0 0 1.8mm;
      font-size: 3.6mm;
      line-height: 1.18;
    }}
    footer {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 10mm;
      font-family: "DejaVu Sans", sans-serif;
      color: var(--muted);
      font-size: 4.2mm;
      border-top: 0.8mm solid var(--line);
      padding-top: 7mm;
    }}
    footer strong {{ color: var(--ink); }}
  </style>
</head>
<body>
  <article class="poster">
    <header>
      <div>
        <h1>Come GAIA organizza i dati</h1>
        <p class="subtitle">Mappa divulgativa delle aree dati e dei collegamenti tra moduli. Le frecce indicano dipendenze tra domini: per esempio una segnalazione puo riferirsi a un utente, un mezzo, una squadra o una particella.</p>
      </div>
      <div class="stats">
        <div class="stat"><strong>{len(tables)}</strong><span>tabelle</span></div>
        <div class="stat"><strong>{total_fk}</strong><span>relazioni</span></div>
        <div class="stat"><strong>{len(DOMAINS)}</strong><span>domini</span></div>
      </div>
    </header>
    <main>
      <section class="map" aria-label="Mappa relazioni GAIA">
        {svg}
      </section>
      <aside>
        <h2>Legenda dei domini</h2>
        <div class="cards">
          {''.join(domain_cards)}
        </div>
      </aside>
    </main>
    <footer>
      <p><strong>Come leggerla:</strong> ogni blocco e un insieme di tabelle; lo spessore delle frecce cresce quando aumentano i collegamenti.</p>
      <p><strong>Dettaglio operativo:</strong> usa il dizionario dati e i diagrammi per dominio nella stessa cartella.</p>
      <p><strong>Formato:</strong> pagina A0 orizzontale, pensata per stampa o condivisione in PDF.</p>
    </footer>
  </article>
</body>
</html>
"""


def describe_table(table_name: str) -> str:
    if table_name in BUSINESS_TERMS:
        return BUSINESS_TERMS[table_name]
    parts = table_name.split("_")
    translated = [WORD_LABELS.get(part, part) for part in parts]
    if any(part in parts for part in ("audit", "metric", "metrics", "log", "logs")):
        prefix = "Registra"
    elif any(part in parts for part in ("config", "credentials", "credential")):
        prefix = "Configura"
    elif any(part in parts for part in ("job", "jobs", "sync", "import", "imports", "run", "runs")):
        prefix = "Traccia"
    elif any(part in parts for part in ("document", "documents", "attachment", "attachments")):
        prefix = "Conserva"
    else:
        prefix = "Contiene"
    return f"{prefix} dati relativi a {' '.join(translated)}."


def relationship_label(source_table: str, source_column: str, target_table: str) -> str:
    clean_column = source_column.removesuffix("_id")
    return f"{source_table}.{source_column} collega a {target_table} ({clean_column})"


def simple_relationship_text(source_table: str, source_column: str, target_table: str, target_column: str) -> str:
    clean_column = source_column.removesuffix("_id").replace("_", " ")
    if target_column == "id":
        return f"Ogni valore in {source_column} identifica una riga della tabella {target_table}."
    return f"La tabella {source_table} usa {source_column} per collegarsi a {target_table}.{target_column} ({clean_column})."


def primary_key_text(table) -> str:
    columns = [column.name for column in table.primary_key.columns]
    return ", ".join(columns) if columns else "nessuna chiave primaria dichiarata"


def primary_key_explanation(table) -> str:
    columns = [column.name for column in table.primary_key.columns]
    if not columns:
        return "La tabella non dichiara una chiave primaria nella metadata letta dal generatore."
    if columns == ["id"]:
        return "Codice interno univoco della riga."
    if len(columns) == 1:
        return f"Il campo {columns[0]} identifica ogni riga in modo univoco."
    return "La riga e identificata dalla combinazione di questi campi: " + ", ".join(columns) + "."


def important_columns(table) -> list[str]:
    pk_names = {column.name for column in table.primary_key.columns}
    fk_names = {fk.parent.name for fk in table.foreign_keys}
    preferred = []
    for column in table.columns:
        if column.name in pk_names or column.name in fk_names:
            continue
        if column.name in {"created_at", "updated_at", "deleted_at"}:
            continue
        preferred.append(column.name)
    return preferred[:8]


def format_fk(fk) -> str:
    return f"{code(fk.parent.name)} -> {code(fk.column.table.name)}.{code(fk.column.name)}"


def format_incoming_fk(item: tuple[str, str, str]) -> str:
    source_table, source_column, target_column = item
    return f"{code(source_table)}.{code(source_column)} -> {code(target_column)}"


def compact_html_list(values: list[str], limit: int = 8) -> str:
    if not values:
        return "-"
    shown = values[:limit]
    if len(values) > limit:
        shown.append(f"+ {len(values) - limit} altri collegamenti nel CSV completo")
    return "<br>".join(shown)


def table_label(table, color: str, description: str, text_color: str = "#ffffff") -> str:
    pk_names = {column.name for column in table.primary_key.columns}
    rows = []
    for column in list(table.columns)[:10]:
        marker = "PK" if column.name in pk_names else ("FK" if any(fk.parent.name == column.name for fk in table.foreign_keys) else " ")
        rows.append(
            f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="9">{html.escape(marker)}</FONT></TD>'
            f'<TD ALIGN="LEFT"><FONT POINT-SIZE="10">{html.escape(column.name)}</FONT></TD></TR>'
        )
    if len(table.columns) > 10:
        rows.append(f'<TR><TD></TD><TD ALIGN="LEFT"><FONT POINT-SIZE="9">+ {len(table.columns) - 10} colonne</FONT></TD></TR>')
    return f"""
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5" COLOR="#ced4da">
  <TR><TD BGCOLOR="{color}" COLSPAN="2"><FONT COLOR="{text_color}" POINT-SIZE="14"><B>{html.escape(table.name)}</B></FONT></TD></TR>
  <TR><TD COLSPAN="2" BGCOLOR="#f8f9fa"><FONT POINT-SIZE="9">{html.escape(textwrap.shorten(description, width=82, placeholder='...'))}</FONT></TD></TR>
  {''.join(rows)}
</TABLE>
"""


def html_table_label(title: str, subtitle: str, body: str, color: str) -> str:
    return f"""
<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="9">
  <TR><TD BGCOLOR="{color}"><FONT COLOR="#ffffff" POINT-SIZE="23"><B>{html.escape(title)}</B></FONT></TD></TR>
  <TR><TD BGCOLOR="#ffffff"><FONT POINT-SIZE="16"><B>{html.escape(subtitle)}</B></FONT></TD></TR>
  <TR><TD BGCOLOR="#ffffff"><FONT POINT-SIZE="13">{html.escape(textwrap.shorten(body, width=72, placeholder='...'))}</FONT></TD></TR>
</TABLE>
"""


def render_dot(dot_path: Path, svg_path: Path) -> None:
    try:
        subprocess.run(
            ["dot", "-Tsvg", str(dot_path), "-o", str(svg_path)],
            check=True,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"warning: could not render {dot_path.name}: {exc}", file=sys.stderr)


def render_pdf(
    html_path: Path,
    pdf_path: Path,
    *,
    paper_width: float,
    paper_height: float,
    fallback_landscape: bool,
) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not chrome:
        return
    try:
        render_pdf_with_devtools(
            chrome,
            html_path,
            pdf_path,
            paper_width=paper_width,
            paper_height=paper_height,
            landscape=fallback_landscape,
        )
        return
    except Exception as exc:
        print(f"warning: DevTools PDF render failed for {pdf_path.name}: {exc}", file=sys.stderr)

    try:
        subprocess.run(
            [
                chrome,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}",
                html_path.as_uri(),
            ],
            check=True,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"warning: could not render {pdf_path.name}: {exc}", file=sys.stderr)


def render_pdf_with_devtools(
    chrome: str,
    html_path: Path,
    pdf_path: Path,
    *,
    paper_width: float,
    paper_height: float,
    landscape: bool,
) -> None:
    port = free_tcp_port()
    user_data_dir = tempfile.mkdtemp(prefix="gaia-chrome-")
    process = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "about:blank",
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for_devtools(port)
        asyncio.run(
            print_pdf_cdp(
                port,
                html_path,
                pdf_path,
                paper_width=paper_width,
                paper_height=paper_height,
                landscape=landscape,
            )
        )
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        shutil.rmtree(user_data_dir, ignore_errors=True)


def free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_devtools(port: int) -> None:
    deadline = time.monotonic() + 10
    url = f"http://127.0.0.1:{port}/json/version"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.15)
    raise RuntimeError("Chrome DevTools endpoint did not start")


async def print_pdf_cdp(
    port: int,
    html_path: Path,
    pdf_path: Path,
    *,
    paper_width: float,
    paper_height: float,
    landscape: bool,
) -> None:
    import websockets

    target_url = html_path.as_uri()
    create_url = f"http://127.0.0.1:{port}/json/new?{urllib.parse.quote(target_url, safe=':/')}"
    request = urllib.request.Request(create_url, method="PUT")
    with urllib.request.urlopen(request, timeout=5) as response:
        target = json.loads(response.read().decode("utf-8"))

    websocket_url = target["webSocketDebuggerUrl"]
    message_id = 0

    async with websockets.connect(websocket_url, max_size=32 * 1024 * 1024) as ws:
        async def call(method: str, params: dict | None = None) -> dict:
            nonlocal message_id
            message_id += 1
            await ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
            while True:
                message = json.loads(await ws.recv())
                if message.get("id") == message_id:
                    if "error" in message:
                        raise RuntimeError(message["error"])
                    return message.get("result", {})

        await call("Page.enable")
        await call("Runtime.enable")
        await call("Emulation.setEmulatedMedia", {"media": "print"})
        await wait_until_page_ready(call)
        result = await call(
            "Page.printToPDF",
            {
                "landscape": landscape,
                "displayHeaderFooter": False,
                "printBackground": True,
                "preferCSSPageSize": True,
                "paperWidth": paper_width,
                "paperHeight": paper_height,
                "marginTop": 0,
                "marginBottom": 0,
                "marginLeft": 0,
                "marginRight": 0,
                "scale": 1,
            },
        )

    pdf_path.write_bytes(base64.b64decode(result["data"]))


async def wait_until_page_ready(call) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        result = await call("Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True})
        if result.get("result", {}).get("value") == "complete":
            await asyncio.sleep(0.4)
            return
        await asyncio.sleep(0.15)
    raise RuntimeError("page did not finish loading")


def code(value: str) -> str:
    return f"`{escape_md(value)}`"


def escape_md(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


if __name__ == "__main__":
    raise SystemExit(main())
