"""Explain differences; distinguish data blockers from explicit accounting review."""

from decimal import Decimal

from app.modules.ruolo.services.campaign_2021_excel import excel_charges, money

GAIA_SOURCES = {"gaia_reminder", "gaia_batch_item"}


def amount(value) -> Decimal | None:
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip()
    try:
        return money(raw.replace(".", "").replace(",", ".") if "," in raw else raw)
    except ValueError:
        return None


def _identity(row, facts) -> list[str]:
    problems = []
    if facts["year"] != "2021":
        problems.append("annualita_incass_discordante")
    for key in ("tax_code", "ruolo_tax_code"):
        if (facts[key] or "").strip().upper() != row["tax_code"]:
            problems.append("identita_discordante")
    for key in ("name", "ruolo_name"):
        if " ".join((facts[key] or "").upper().split()) != " ".join(row["name"].upper().split()):
            problems.append("nominativo_discordante")
    return problems


def _document_problems(h, tax_code) -> list[str]:
    checks = {
        "step_non_liberato": h["recovery"] not in {"non_affidato_verificato", "revocato"}
        or not h["recovery_reference"],
        "notifica_da_verificare": h["notification"]
        not in {"nessuna_evidenza", "tentativo_senza_notifica", "perfezionata"},
        "prova_notifica_assente": h["notification"] == "perfezionata"
        and not (h["evidence"] and h["notified_on"]),
        "invii_non_chiariti": bool(h["attempts"]) and not h["evidence"],
        "storico_discordante": h["year"] != 2021
        or (h["tax_code"] or "").strip().upper() != tax_code.strip().upper(),
    }
    return [key for key, failed in checks.items() if failed]


def _delivery_problems(facts, historical) -> list[str]:
    problems = []
    if facts["step_assigned"] or facts["ambiguous_history"]:
        problems.append("step_o_storico_ambiguo")
    if (facts["last_delivery"] or facts["mailing_delivery"] or facts["pec_documented"]) and not any(
        h["evidence"] for h in historical
    ):
        problems.append("invio_incass_da_riconciliare")
    return problems


def _history(facts) -> tuple[str, list[str]]:
    historical = [h for h in facts["history"] if h["source"] not in GAIA_SOURCES]
    problems = _delivery_problems(facts, historical)
    if not historical:
        problems.append("storico_non_verificato")
    for h in facts["history"]:
        problems.extend(_document_problems(h, facts["ruolo_tax_code"]))
    kind = (
        "sollecito_documentato"
        if any(h["notification"] == "perfezionata" for h in historical)
        else "prima_emissione_non_documentata_come_notificata"
    )
    return ("stato_incerto" if problems else kind), problems


def _accounting_blockers(row, facts, current) -> list[str]:
    blockers = []
    residual = current["importo_residuo"]
    if residual is not None and residual != money(row["amounts"]["residual"]):
        blockers.append("residuo_corrente_discordante")
    if residual is not None and residual <= 0:
        blockers.append("saldo_non_esigibile")
    if (current["importo_annullato"] or 0) > 0 or facts["engine"]["workflow_status"] in {
        "annullato",
        "sospeso",
        "contestato",
    }:
        blockers.append("posizione_bloccata")
    return blockers


def _input_blockers(row, facts, current) -> list[str]:
    checks = {
        "contabilita_incompleta": current["importo_carico"] is None
        or current["importo_residuo"] is None
        or not facts["synced_at"],
        "riscossioni_non_verificate": current["importo_riscosso"] is None,
        "partitario_assente": not facts["partitario_available"],
        "motore_avviso_discordante": facts["engine"]["capacitas_avviso_code"] != row["number"],
        "policy_non_verificata": facts["engine"]["calculation_policy"] != "internal_gaia"
        or not facts["policy"],
    }
    return [key for key, failed in checks.items() if failed]


def _accounting_reviews(row, current) -> list[str]:
    reviews = []
    if money(row["amounts"]["difference"]) != 0:
        reviews.append("differenza_contabile_non_prova_pagamento")
    if (current["importo_rateizzato"] or 0) > 0:
        reviews.append("oneri_rateizzazione_da_riconciliare")
    if row["digital"]:
        reviews.extend(["euribor_3m_6m", "base_360_365", "decorrenza_interessi"])
    return reviews


def _accounting_kind(kind, current):
    residual = current["importo_residuo"]
    if residual is None:
        return "stato_incerto"
    if residual <= 0:
        return "saldato_annullato_esubero"
    if (current["importo_rateizzato"] or 0) > 0:
        return "rateizzazione_con_residuo"
    if (current["importo_riscosso"] or 0) != 0:
        return "parzialmente_saldato"
    return kind


def reconcile(row: dict, facts: dict, params: dict) -> dict:
    blockers = [p for p in row["problems"] if p != "cf_da_revisionare"]
    reviews = [p for p in row["problems"] if p == "cf_da_revisionare"]
    if "match_error" in facts:
        return {
            "kind": "stato_incerto",
            "blockers": sorted(set([*blockers, facts["match_error"]])),
            "reviews": reviews,
            "deltas": {},
            "generable": False,
        }
    kind, history_problems = _history(facts)
    current = {key: amount(value) for key, value in facts["accounting"].items()}
    blockers.extend(
        [
            *_identity(row, facts),
            *_input_blockers(row, facts, current),
            *history_problems,
            *_accounting_blockers(row, facts, current),
        ]
    )
    deltas = _deltas(row, facts, current, params)
    reviews.extend(key for key, value in deltas.items() if value != "0.00")
    reviews.extend(_accounting_reviews(row, current))
    return {
        "kind": _accounting_kind(kind, current),
        "blockers": sorted(set(blockers)),
        "reviews": sorted(set(reviews)),
        "deltas": deltas,
        "generable": not blockers and not reviews,
    }


def _deltas(row, facts, current, params) -> dict[str, str]:
    values = row["amounts"]
    engine = facts["engine"]
    pairs = {
        "carico_excel_incass": (money(values["load"]), current["importo_carico"]),
        "tributi_carico": (money(row["tribute_delta"]), money(0)),
        "maggiorazione_excel_gaia": (
            money(values["surcharge"]),
            amount(engine["surcharge_amount"]),
        ),
        "interessi_excel_gaia": (money(values["interest"]), amount(engine["interest_amount"])),
        "totale_excel_gaia": (money(values["total"]), amount(engine["saldo_amount"])),
    }
    return {
        **{
            key: str(a - b) if b is not None else "non_disponibile" for key, (a, b) in pairs.items()
        },
        "interessi_360_365": str(
            money(values["interest"])
            - money(
                excel_charges(values["residual"], row["digital"], params, basis=365)["interest"]
            )
        ),
    }
