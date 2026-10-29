"""Payment terms printed from the saved rule, without inventing a notification date."""

FIXED_DEADLINE = "fixed_date"
NOTIFICATION_DEADLINE = "notification_60_days"
DEADLINE_MODES = {FIXED_DEADLINE, NOTIFICATION_DEADLINE}
NOTIFICATION_TERM = "60 giorni dalla data di notifica"
MISSING_BOLLETTINO_DATE = (
    "Per stampare il bollettino impostare una data di scadenza fissa nelle Regole ruolo."
)

PAYMENT_DEADLINE_CSS = """
.front:has(.payment-deadline) { padding-top: 8mm; padding-bottom: 8mm; }
.front:has(.payment-deadline) > :is(.payment-deadline, .note, .portal-access, .notice-footer) {
  margin-top: auto; margin-bottom: 1mm; }
.front:has(.payment-deadline) > .notice-footer { margin-bottom: 0; }
.front:has(.payment-deadline) .body { font-size: 9.2pt; line-height: 1.17; }
.front:has(.payment-deadline) .body { padding: 1.5mm; }
.front:has(.payment-deadline) .kv { row-gap: .3mm; }
.front:has(.payment-deadline) .head-title h1 { font-size: 18.5pt; }
.front:has(.payment-deadline) .head-title p { font-size: 9.2pt; }
.front:has(.payment-deadline) .notice-title { margin: 2mm 0; padding-top: 2mm; padding-bottom: 2mm; }
.front:has(.payment-deadline) .pay-band { margin-top: 2mm; }
.front:has(.payment-deadline) .summary { margin-top: 2mm; }
.front:has(.payment-deadline) .portal-body { padding-top: 1mm; padding-bottom: 1mm; }
.front:has(.payment-deadline) .amount { padding: 2.5mm; }
.front:has(.payment-deadline) .amount .installment-request { font-size: 8.2pt; }
.front:has(.payment-deadline):has(.summary tbody tr:nth-child(4)) .body {
  padding: 1.2mm; font-size: 8.3pt; line-height: 1.05; }
.front:has(.payment-deadline):has(.summary tbody tr:nth-child(4)) .kv { row-gap: .2mm; }
.front:has(.payment-deadline):has(.summary tbody tr:nth-child(4)) .card h2 {
  padding-top: 1.2mm; padding-bottom: 1.2mm; font-size: 9pt; }
.front:has(.payment-deadline):has(.summary tbody tr:nth-child(4)) .card p { margin: 1mm 0; }
.front:has(.payment-deadline):has(.summary tbody tr:nth-child(4)) .recipient { font-size: 10pt; }
.front:has(.payment-deadline):has(.summary tbody tr:nth-child(4)) .amount { padding: 2mm; font-size: 9.2pt; }
.front:has(.payment-deadline):has(.summary tbody tr:nth-child(4)) .amount .installment-request { font-size: 7.8pt; }
.front:has(.payment-deadline):has(.summary tbody tr:nth-child(4)) .instructions p { font-size: 9.2pt; }
.front:has(.payment-deadline):has(.summary tbody tr:nth-child(4)) .summary { font-size: 7.5pt; }
.front:has(.payment-deadline):has(.summary tbody tr:nth-child(4)) .summary td { padding-top: .5mm; padding-bottom: .5mm; }
.front:has(.payment-deadline):has(.summary tbody tr:nth-child(4)) .summary th { padding-top: .75mm; padding-bottom: .75mm; }
.front:has(.payment-deadline):has(.summary tbody tr:nth-child(4)) .rateization-note { font-size: 8.3pt; }
.payment-deadline { margin-top: 2mm; border: 1pt solid #2b5793; border-radius: 2mm;
  padding: 1.5mm 3mm; background: #f2f6fa; break-inside: avoid; }
.payment-deadline p { margin: 0 0 .6mm; font-size: 8.5pt; line-height: 1.18; }
.payment-deadline p:last-child { margin-bottom: 0; }
.payment-deadline .payment-term { font-size: 10.2pt; font-weight: 700; }
.notice-enforcement { display: grid; grid-template-columns: 10mm 1fr; gap: 3mm;
  align-items: start; margin-bottom: 1.5mm; break-inside: avoid; }
.notice-enforcement .attention-icon { color: #c62828; width: 10mm; height: 10mm; display: block; }
.notice-enforcement p { margin: 0; font-size: 8.3pt; line-height: 1.2; text-align: justify; }
"""


def apply_payment_deadline(policy, command) -> None:
    if command.payment_deadline_mode not in DEADLINE_MODES:
        raise ValueError("Modalità scadenza pagamento non valida")
    if (
        command.payment_deadline_mode == NOTIFICATION_DEADLINE
        and command.print_bollettino
        and command.payment_due_date is None
    ):
        raise ValueError(MISSING_BOLLETTINO_DATE)
    policy.payment_deadline_mode = command.payment_deadline_mode
    policy.payment_due_date = command.payment_due_date


def payment_deadline_payload(policy, *, require_date=False) -> dict:
    if policy is None:
        return {}
    payload = {"due_date": policy.payment_due_date.isoformat()} if policy.payment_due_date else {}
    if policy.payment_deadline_mode == NOTIFICATION_DEADLINE:
        if require_date and policy.payment_due_date is None:
            raise ValueError(MISSING_BOLLETTINO_DATE)
        payload["payment_deadline_mode"] = NOTIFICATION_DEADLINE
    return payload


def payment_deadline_text(payload, fixed_date_formatter) -> str:
    if payload.get("payment_deadline_mode") == NOTIFICATION_DEADLINE:
        return NOTIFICATION_TERM
    return fixed_date_formatter(payload)


def bollettino_deadline_date(payload, fixed_date_formatter) -> str:
    """A notification term cannot replace the slip's mandatory calendar date."""
    if not (payload.get("due_date") or payload.get("deadline")) and (
        payload.get("payment_deadline_mode") == NOTIFICATION_DEADLINE
    ):
        raise ValueError(MISSING_BOLLETTINO_DATE)
    return fixed_date_formatter(payload)


def payment_due_phrase(payload, deadline: str) -> str:
    prefix = (
        "entro " if payload.get("payment_deadline_mode") == NOTIFICATION_DEADLINE else "entro il "
    )
    return prefix + deadline


def front_payment_due_phrase(payload, years, fixed_date_formatter) -> str:
    """The 2021 payment box always retains the notification term beside any saved date."""
    if years != [2021]:
        return payment_due_phrase(payload, payment_deadline_text(payload, fixed_date_formatter))
    if payload.get("due_date") or payload.get("deadline"):
        return f"scadenza il {fixed_date_formatter(payload)} e comunque entro {NOTIFICATION_TERM}"
    return f"entro {NOTIFICATION_TERM}"


def payment_deadline_fields(payload, fixed_date_formatter) -> dict[str, str]:
    deadline = payment_deadline_text(payload, fixed_date_formatter)
    return {"Scadenza": deadline, "Pagamento_entro": payment_due_phrase(payload, deadline)}


def payment_deadline_html(payload) -> str:
    if payload.get("payment_deadline_mode") != NOTIFICATION_DEADLINE:
        return ""
    return f"""<div class="payment-deadline">
  <p class="payment-term">Pagamento entro {NOTIFICATION_TERM}</p>
  <p>La scadenza che cade nelle giornate di sabato o festive è spostata al primo giorno lavorativo successivo.</p>
  <p>In caso di pagamento oltre i 60 giorni, alla somma dovuta saranno aggiunti gli interessi di mora.</p>
</div>"""


def notice_enforcement_html(payload) -> str:
    if payload.get("payment_deadline_mode") != NOTIFICATION_DEADLINE:
        return ""
    return """<div class="notice-enforcement">
  <svg class="attention-icon" viewBox="0 0 40 40" aria-hidden="true">
    <path d="M20 3 L38 36 H2 Z" fill="#fff5f5" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
    <path d="M20 14 V24" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
    <circle cx="20" cy="30" r="1.8" fill="currentColor"/>
  </svg>
  <p><strong>Il presente avviso ha valore di intimazione ad adempiere l'obbligo</strong> risultante dai ruoli in esso contenuti entro il termine di 60 giorni dalla data di notifica. Nelle ipotesi in cui il ruolo emesso sia ripartito in più rate, l'intimazione produce effetti relativamente a tutte le rate. <strong>In caso di mancato pagamento,</strong> il Consorzio di Bonifica dell'Oristanese tramite l'agente di riscossione attiverà le procedure di riscossione coattiva previste dalla legge. Tali procedure possono comportare, nei casi e con le modalità previsti dalla legge, l'acquisizione presso terzi di notizie sul reddito e sul patrimonio dei debitori, il fermo amministrativo di beni mobili registrati (veicoli, natanti, aeromobili), l'iscrizione di ipoteca sugli immobili e l'esecuzione forzata di beni immobili, mobili e crediti (stipendio, emolumenti, parcelle, fatture, titoli, somme disponibili sui conti correnti e depositi).</p>
</div>"""
