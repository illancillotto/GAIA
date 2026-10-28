import type { PosteDispatchJobKind } from "@/types/ruolo-poste-dispatch";

export const STATUS_LABELS: Record<string, string> = {
  address_pending: "Indirizzo da verificare",
  address_review: "Indirizzo da rivedere",
  address_ok: "Pronto per la bozza",
  draft_creating: "Creazione bozza in corso",
  draft_created: "Bozza in lavorazione Poste",
  draft_priced: "Bozza prezzata",
  draft_uncertain: "Esito bozza da verificare",
  draft_error: "Bozza non creata",
  draft_missing: "Bozza scaduta o eliminata",
  cancel_requested: "Eliminazione richiesta",
  cancelled: "Annullato",
  sent: "Spedito",
};

export const STATUS_TONES: Record<string, string> = {
  address_review: "bg-amber-50 text-amber-900",
  draft_uncertain: "bg-amber-50 text-amber-900",
  draft_error: "bg-rose-50 text-rose-800",
  draft_missing: "bg-rose-50 text-rose-800",
  draft_priced: "bg-sky-50 text-sky-900",
  sent: "bg-emerald-50 text-emerald-800",
};

export const JOB_ACTIONS: { kind: PosteDispatchJobKind; label: string; hint: string }[] = [
  { kind: "addresses", label: "Verifica indirizzi", hint: "Confronta gli indirizzi con lo stradario Poste" },
  { kind: "drafts", label: "Crea bozze su Poste", hint: "Carica PDF e destinatari in Verifica e invia" },
  { kind: "reconcile", label: "Controlla Poste", hint: "Aggiorna prezzi e registra le raccomandate spedite" },
  { kind: "delete", label: "Elimina bozze annullate", hint: "Toglie da Poste le bozze annullate in GAIA" },
];

export const JOB_LABELS: Record<string, string> = {
  poste_dispatch_addresses: "Verifica indirizzi",
  poste_dispatch_drafts: "Creazione bozze",
  poste_dispatch_reconcile: "Controllo Poste",
  poste_dispatch_delete: "Eliminazione bozze",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function euro(value: number | null): string {
  return value === null ? "-" : new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

export function dateTime(value: string | null): string {
  return value ? new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "-";
}

export function countsSummary(counts: Record<string, number>): string {
  const parts = Object.entries(counts).map(([status, count]) => `${count} ${statusLabel(status).toLowerCase()}`);
  return parts.length ? parts.join(" · ") : "Nessun avviso";
}

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
