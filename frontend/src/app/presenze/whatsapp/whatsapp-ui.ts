export const WHATSAPP_STATUS_OPTIONS = [
  ["", "Tutti gli stati"],
  ["SENT", "Inviati"],
  ["DELIVERED", "Consegnati"],
  ["READ", "Letti"],
  ["FAILED", "Non riusciti"],
  ["SENDING", "Da verificare"],
  ["UNKNOWN", "Esito incerto"],
] as const;

const STATUS_LABELS: Record<string, string> = {
  SENT: "Inviato",
  DELIVERED: "Consegnato",
  READ: "Letto",
  FAILED: "Non riuscito",
  NOT_ON_WHATSAPP: "Numero non WhatsApp",
  SENDING: "Da verificare",
  UNKNOWN: "Esito incerto",
  DRY_RUN: "Simulato",
  CANCELLED: "Annullato",
};

const SKIP_LABELS: Record<string, string> = {
  operator_not_linked: "Utente GAIA non collegato",
  operator_profile_missing: "Profilo operatore assente",
  operator_disabled: "Utente o profilo disattivato",
  opted_out: "Ha risposto STOP",
  phone_missing: "Numero di telefono mancante",
  phone_invalid: "Numero di telefono non valido",
};

export function whatsappStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function whatsappStatusTone(status: string): string {
  if (status === "READ" || status === "DELIVERED") return "bg-emerald-50 text-emerald-700 ring-emerald-200";
  if (status === "SENT" || status === "DRY_RUN") return "bg-sky-50 text-sky-700 ring-sky-200";
  if (status === "SENDING" || status === "UNKNOWN") return "bg-amber-50 text-amber-800 ring-amber-200";
  return "bg-rose-50 text-rose-700 ring-rose-200";
}

export function whatsappSkipLabel(reason: string | null): string {
  return reason ? (SKIP_LABELS[reason] ?? reason) : "Motivo non disponibile";
}

export function formatWhatsAppDateTime(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

export function whatsappSessionLabel(status: string | undefined): string {
  const labels: Record<string, string> = {
    working: "Collegata",
    dry_run: "Modalità prova",
    disabled: "Spenta",
    starting: "In avvio",
    scan_qr_code: "QR da scansionare",
    stopped: "Disconnessa",
    failed: "In errore",
    unavailable: "Non raggiungibile",
    misconfigured: "Configurazione incompleta",
    unsupported: "Provider non supportato",
    invalid_response: "Risposta non valida",
    not_created: "Non configurata",
  };
  return labels[status ?? ""] ?? status ?? "Stato non disponibile";
}
