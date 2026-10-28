"""HTML for the "Comunicazioni per il Contribuente" page of the GAIA notice.

The legal page text comes from the default DOCX template, which was written for the
2022-2023 roles. The paragraphs that depend on the role year (emission/approval
resolutions, installment and enforced-collection resolution, contribution minimums,
budget year) are rebuilt here from the years included in the notice.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any

TRIBUTE_INFO_LABEL = "Informazioni sul tributo."
# Installment plan tiers (delibera di approvazione del ruolo), lowest amount first.
INSTALLMENT_TIERS: tuple[tuple[str, str], ...] = (
    ("inferiore a 100,00 €", "nessuna dilazione"),
    ("da 100,00 a 300,00 €", "2"),
    ("da 300,01 a 500,00 €", "4"),
    ("da 500,01 a 1.000,00 €", "6"),
    ("da 1.000,00 a 5.000,00 €", "12"),
    ("oltre 5.000,00 €", "18"),
)
_INSTALLMENT_LIST_PATTERN = re.compile(r"<ul>\n<li>n\. 18 rate per gli importi.*?</ul>", re.S)
_CELL_STYLE = "border: .5pt solid #8797ad; padding: .45mm .8mm; text-align: center;"
_HEAD_STYLE = (
    f"{_CELL_STYLE} background: #f0f4f9; font-weight: 700; text-align: left; white-space: nowrap;"
)
# Runs in Chromium before print-to-pdf: picks the largest line height (1.05-1.8) that keeps the
# text and the signature on page 2; if even 1.05 overflows, shrinks the font (down to 70%).
_FIT_SCRIPT = """(function () {
  var box = document.currentScript.previousElementSibling;
  var copy = box.parentElement;
  var page = copy.closest("section");
  var style = getComputedStyle(page);
  var safety = 2 * 96 / 25.4;
  function fits(lineHeight, fontSize) {
    box.style.lineHeight = String(lineHeight);
    box.style.fontSize = fontSize + "%";
    var limit = page.getBoundingClientRect().top + parseFloat(style.minHeight)
      - parseFloat(style.paddingBottom) - safety;
    return copy.getBoundingClientRect().bottom <= limit;
  }
  function largest(low, high, test) {
    for (var step = 0; step < 14; step++) {
      var mid = (low + high) / 2;
      if (test(mid)) { low = mid; } else { high = mid; }
    }
    return low;
  }
  if (fits(1.05, 100)) {
    fits(largest(1.05, 1.8, function (value) { return fits(value, 100); }), 100);
  } else {
    fits(1.05, largest(70, 100, function (value) { return fits(1.05, value); }));
  }
})();"""
# Typographic apostrophe used by the template text (RUF001 flags it as a literal).
APOS = "\N{RIGHT SINGLE QUOTATION MARK}"
EXISTING_INSTALLMENT_PLAN_NOTE = (
    "Qualora le somme oggetto della presente comunicazione siano già comprese in un piano di "
    "rateizzazione sottoscritto e non integralmente saldato, la presente comunicazione non "
    "sostituisce il piano né modifica le decorrenze applicabili ai fini del calcolo degli "
    "interessi. Restano ferme le conseguenze dell\N{RIGHT SINGLE QUOTATION MARK}eventuale "
    "mancato rispetto del piano, secondo le condizioni sottoscritte e il regolamento vigente. "
    "La determinazione dell\N{RIGHT SINGLE QUOTATION MARK}importo residuo dovuto tiene conto "
    "dei versamenti già effettuati."
)
_EXISTING_INSTALLMENT_PLAN_HTML = (
    f'<p class="existing-installment-plan">{EXISTING_INSTALLMENT_PLAN_NOTE}</p>'
)


@dataclass(frozen=True)
class RoleYearResolutions:
    year: int
    emission: str
    emission_albo_date: str
    approval: str
    approval_albo_date: str
    notes: tuple[str, ...] = ()


REFUND_2017_NOTE = (
    "Il presente avviso potrebbe contenere, se presente, una quota di rimborso relativo ai "
    "tributi esercizio 2017 disposto con delibera del CdA n. 42/2020."
)

# Sources: template DOCX (2023) and the notices actually issued for 2021, 2022, 2024, 2025.
ROLE_YEAR_RESOLUTIONS: dict[int, RoleYearResolutions] = {
    2021: RoleYearResolutions(
        year=2021,
        emission="89/2022",
        emission_albo_date="03.08.2022",
        approval="106/2022",
        approval_albo_date="19.09.2022",
        notes=(REFUND_2017_NOTE,),
    ),
    2022: RoleYearResolutions(
        year=2022,
        emission="116/2023",
        emission_albo_date="30.08.2023",
        approval="131/2023",
        approval_albo_date="16.10.2023",
        notes=(REFUND_2017_NOTE,),
    ),
    2023: RoleYearResolutions(
        year=2023,
        emission="52/2024",
        emission_albo_date="05.04.2024",
        approval="58/2024",
        approval_albo_date="19.04.2024",
    ),
    2024: RoleYearResolutions(
        year=2024,
        emission="6/2025",
        emission_albo_date="28.01.2025",
        approval="19/2025",
        approval_albo_date="21.02.2025",
    ),
    2025: RoleYearResolutions(
        year=2025,
        emission="5/2026",
        emission_albo_date="15.01.2026",
        approval="23/2026",
        approval_albo_date="20.02.2026",
    ),
}

# (pattern, replacement builder) for the year-dependent fragments of the template paragraphs.
_INSTALLMENT_PATTERN = re.compile(r"\(Delib\. CdA n\.\s?[\d/]+\)")
_BUDGET_PATTERN = re.compile(r"in base al bilancio [^,]+,")
_MINIMUMS_PATTERN = re.compile(
    r"(confermati con delibera del CdD n\.\s?14/2020 e delibera CdA n\.)\s?[\d/]+"
)
_ENFORCEMENT_PATTERN = re.compile(r"giusta Delibera del CdA n\.\s?[\d/]+")


class MissingRoleYearResolutionsError(ValueError):
    pass


def resolutions_for_years(years: list[int]) -> list[RoleYearResolutions]:
    missing = [year for year in years if year not in ROLE_YEAR_RESOLUTIONS]
    if not years or missing:
        label = ", ".join(str(year) for year in missing) or "nessun anno"
        raise MissingRoleYearResolutionsError(
            f"Delibere ruolo non configurate per: {label}. Aggiornare ROLE_YEAR_RESOLUTIONS."
        )
    return [ROLE_YEAR_RESOLUTIONS[year] for year in sorted(set(years))]


def apply_role_year_resolutions(
    blocks: list[dict[str, Any]], years: list[int]
) -> list[dict[str, Any]]:
    resolutions = resolutions_for_years(years)
    latest = resolutions[-1]
    replacements = (
        (_INSTALLMENT_PATTERN, f"(Delib. CdA n. {latest.approval})"),
        (
            _BUDGET_PATTERN,
            f"in base al bilancio {_join_human(str(item.year) for item in resolutions)},",
        ),
        (_MINIMUMS_PATTERN, rf"\g<1> {latest.emission}"),
        (_ENFORCEMENT_PATTERN, f"giusta Delibera del CdA n. {latest.approval}"),
    )
    hits = dict.fromkeys(range(len(replacements)), 0)
    tribute_info_hits = 0
    adapted: list[dict[str, Any]] = []
    for block in blocks:
        text = str(block["text"])
        if text.startswith(TRIBUTE_INFO_LABEL):
            tribute_info_hits += 1
            adapted.extend(_tribute_info_blocks(resolutions))
            continue
        for index, (pattern, replacement) in enumerate(replacements):
            text, count = pattern.subn(replacement, text)
            hits[index] += count
        adapted.append({**block, "text": text})
    if tribute_info_hits != 1 or any(count != 1 for count in hits.values()):
        raise MissingRoleYearResolutionsError(
            "Il template delle Comunicazioni per il Contribuente non contiene i paragrafi attesi per le delibere."
        )
    return adapted


def _tribute_info_blocks(resolutions: list[RoleYearResolutions]) -> list[dict[str, Any]]:
    years_label = _join_human(str(item.year) for item in resolutions)
    scope = (
        f"per l{APOS}anno {years_label}" if len(resolutions) == 1 else f"per gli anni {years_label}"
    )
    clauses = [_resolution_clause(item, first=index == 0) for index, item in enumerate(resolutions)]
    if len(resolutions) > 1:
        clauses = [
            f"{clause} per l{APOS}anno {item.year}"
            for clause, item in zip(clauses, resolutions, strict=True)
        ]
    text = (
        f"{TRIBUTE_INFO_LABEL} L{APOS}\N{LEFT DOUBLE QUOTATION MARK}Avviso di Pagamento\N{RIGHT DOUBLE QUOTATION MARK} si riferisce ai tributi istituzionali, manutenzione opere irrigue "
        f"e utenza irrigua, emessi in acconto in attesa dell{APOS}approvazione del Rendiconto di gestione. "
        f"L{APOS}emissione dei ruoli {scope} è stata disposta {_join_human(clauses)}."
    )
    notes = dict.fromkeys(note for item in resolutions for note in item.notes)
    note_blocks = [{"text": note, "list": False} for note in notes]
    return [{"text": text, "list": False}, *note_blocks]


def _resolution_clause(item: RoleYearResolutions, *, first: bool) -> str:
    board = "Consiglio di Amministrazione (di seguito CdA)" if first else "CdA"
    return (
        f"con delibera {board} n. {item.emission}, pubblicata all'albo in data {item.emission_albo_date} "
        f"e approvata con Delibera CdA n. {item.approval} pubblicata all{APOS}albo in data {item.approval_albo_date}"
    )


def _join_human(values: Any) -> str:
    items = list(values)
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} e {items[-1]}"


def legal_page_html(
    blocks: list[dict[str, Any]], field_values: dict[str, str], years: list[int]
) -> str:
    if blocks:
        content = _gaia_legal_blocks_html(apply_role_year_resolutions(blocks, years), field_values)
        return _fit_legal_page(_installment_table(content))
    return _gaia_fallback_legal_html(field_values)


def _fit_legal_page(content: str) -> str:
    return f'<div class="legal-fit">{content}</div><script>{_FIT_SCRIPT}</script>'


def _installment_table(content: str) -> str:
    rows = (
        ("Importo dell'avviso", [amount for amount, _ in INSTALLMENT_TIERS]),
        ("Numero massimo di rate", [f"<strong>{rate}</strong>" for _, rate in INSTALLMENT_TIERS]),
    )
    table = "".join(
        f'<tr><th scope="row" style="{_HEAD_STYLE}">{html.escape(label)}</th>'
        + "".join(f'<td style="{_CELL_STYLE}">{cell}</td>' for cell in cells)
        + "</tr>"
        for label, cells in rows
    )
    replaced, count = _INSTALLMENT_LIST_PATTERN.subn(
        f'<table class="legal-installments" style="width: 100%; border-collapse: collapse; '
        f'margin: -.4mm 0 .8mm;">{table}</table>{_EXISTING_INSTALLMENT_PLAN_HTML}',
        content,
    )
    if count != 1:
        raise MissingRoleYearResolutionsError(
            "Il template delle Comunicazioni per il Contribuente non contiene le fasce di dilazione attese."
        )
    return replaced


def _gaia_legal_blocks_html(blocks: list[dict[str, Any]], field_values: dict[str, str]) -> str:
    chunks: list[str] = []
    in_list = False
    for block in blocks:
        text = _replace_legal_placeholders(str(block["text"]), field_values)
        if block["list"]:
            if not in_list:
                chunks.append("<ul>")
                in_list = True
            chunks.append(f"<li>{html.escape(text)}</li>")
            continue
        if in_list:
            chunks.append("</ul>")
            in_list = False
        chunks.append(_gaia_legal_paragraph_html(text))
    if in_list:
        chunks.append("</ul>")
    return "\n".join(chunks)


def _replace_legal_placeholders(text: str, field_values: dict[str, str]) -> str:
    for field_name, value in field_values.items():
        text = text.replace(f"«{field_name}»", value)
    return text


def _gaia_legal_paragraph_html(text: str) -> str:
    labels = (
        "Informazioni di carattere generale.",
        "Informazioni sul tributo.",
        "Scadenza del Pagamento:",
        "Determinazione del Contributo.",
        "Detraibilità del contributo.",
        "Modalità di ricorso al presente avviso di pagamento.",
        "Richiesta di Voltura / Variazione:",
        "Informazione sulla riscossione mediante Avvisi di Pagamento:",
        "AVVERTENZA IMPORTANTE:",
    )
    for label in labels:
        if text.startswith(label):
            return f"<p><strong>{html.escape(label)}</strong>{html.escape(text[len(label) :])}</p>"
    return f"<p>{html.escape(text)}</p>"


def _gaia_fallback_legal_html(field_values: dict[str, str]) -> str:
    tax_code = html.escape(field_values["CodFiscale"])
    notice_number = html.escape(field_values["Avviso_n"])
    return f"""
    <p><strong>Informazioni di carattere generale.</strong> Il Consorzio di Bonifica dell'Oristanese è un Ente Pubblico ex art. 59 R.D. 215/1933 e art. 14 L.R. 06/2008. Il contributo consortile costituisce la quota dovuta da ciascun consorziato per le spese di manutenzione e gestione delle opere di bonifica, nonché per le spese di funzionamento dell'Ente. Sono tenuti al pagamento i proprietari di terreni ricadenti nel perimetro consortile e serviti dalla rete consortile di distribuzione dell'acqua ad uso irriguo. I contributi di bonifica sono oneri reali sulla proprietà, sono esigibili con le norme per l'esazione dei tributi e seguono il regime di riscossione delle imposte. Il contributo consortile è annuale e le volture producono effetti a partire dal ruolo dell'anno successivo.</p>
    <p><strong>Informazioni sul tributo.</strong> L'Avviso di Pagamento si riferisce ai tributi istituzionali, manutenzione opere irrigue e utenza irrigua, emessi in acconto in attesa dell'approvazione del Rendiconto di gestione. L'emissione dei ruoli è disposta dagli atti deliberativi dell'Ente pubblicati all'albo.</p>
    <p>Dilazione del pagamento. Il contribuente può richiedere, direttamente presso gli uffici dell'Ente, una dilazione del pagamento del presente AVVISO fino a:</p><ul><li>n. 18 rate per gli importi superiori ai 5.000,00 euro; n. 12 rate per gli importi da 1.000,00 euro a 5.000,00 euro;</li><li>n. 6 rate per gli importi da 500,01 euro a 1.000,00 euro; n. 4 rate per gli importi da 300,01 euro a 500,00 euro;</li><li>n. 2 rate per gli importi da 100,00 euro a 300,00 euro; non sono previste dilazioni per importi inferiori a 100,00 euro;</li></ul>
    {_EXISTING_INSTALLMENT_PLAN_HTML}<p><strong>Scadenza del Pagamento:</strong> Si ricorda che in caso di mancato pagamento nel termine indicato, verranno attivate le procedure previste dal D.P.R. n. 602/1973 e successive modificazioni con conseguente aggravio delle spese per la riscossione coattiva.</p>
    <p>Il pagamento potrà essere effettuato anche mediante bonifico bancario al Conto Corrente:<br>Intestato a: CONSORZIO DI BONIFICA DELL'ORISTANESE - RISCOSSIONE QUOTE ASSOCIATIVE<br>Iban: IT15L0760117400001007214826 - Causale: indicare codice fiscale {tax_code} e numero dell'avviso di pagamento {notice_number}</p>
    <p><strong>Determinazione del Contributo.</strong> Il tributo istituzionale è dovuto per le spese di funzionamento dell'Ente (cod. 0985). Il tributo per la manutenzione opere irrigue (cod. 0648) è dovuto per le spese di manutenzione ordinaria delle opere irrigue. Il contributo utenza (cod. 0668) è dovuto da coloro che hanno utilizzato la risorsa idrica ed è commisurato ai criteri del Piano di Classifica e Riparto.</p>
    <p><strong>Detraibilità del contributo.</strong> I contributi del Consorzio hanno natura tributaria. Il contributo istituzionale e il contributo opere irrigue sono deducibili dal reddito lordo da denunciare ai fini fiscali; il contributo utenza non è invece deducibile.</p>
    <p><strong>Modalità di ricorso al presente avviso di pagamento.</strong></p><ul><li>Direttamente al Consorzio di Bonifica dell'Oristanese mediante raccomandata A/R da inviarsi alla sede legale: Via Cagliari 170, 09170 ORISTANO, ovvero mediante PEC all'indirizzo protocollo.cbo@pec.it.</li></ul>
    <p><strong>Richiesta di Voltura / Variazione:</strong> Il contribuente potrà segnalare al Consorzio qualsiasi correzione di dati anagrafici e/o di trasferimento della proprietà mediante invio di apposita comunicazione:</p><ul><li>Via posta all'indirizzo del Consorzio: 09170 Oristano - Via Cagliari, 170</li><li>Via e-mail a uno dei seguenti indirizzi: catasto@bonificaoristanese.it, tributi.cbo@pec.it;</li></ul>
    <p><strong>Informazione sulla riscossione mediante Avvisi di Pagamento:</strong> La riscossione ordinaria dei contributi di bonifica iscritti a ruolo viene fatta precedere da una fase di riscossione volontaria realizzata mediante avvisi di pagamento, consentendo al contribuente di evitare i diritti di notifica altrimenti dovuti all'Agente della Riscossione.</p>
    <p class="warning"><strong>AVVERTENZA IMPORTANTE:</strong> IL MANCATO PAGAMENTO DEL PRESENTE AVVISO, NON GIUSTIFICA IL MANCATO O TARDIVO VERSAMENTO DEL TRIBUTO DOVUTO. PERTANTO, È OBBLIGO DEL CONTRIBUENTE ATTIVARSI PER ADEMPIERE AL PAGAMENTO DEL DOVUTO ALLA SCADENZA PREFISSATA. <em>Tale omissione comporta il conseguente avvio della RISCOSSIONE COATTIVA del credito tributario in oggetto.</em></p>
    <p>Il responsabile del procedimento è il Direttore Generale del Consorzio, Dott. Maurizio Scanu.</p>
    """
