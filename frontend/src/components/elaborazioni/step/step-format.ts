import type { StepLinkStatus, StepSyncJob } from "@/types/step";

const JOB_STATUS_LABELS: Record<string, string> = {
  pending: "In coda",
  processing: "In esecuzione",
  succeeded: "Completato",
  completed_with_errors: "Completato con anomalie",
  failed: "Fallito",
  cancelled: "Annullato",
};

const JOB_MODE_LABELS: Record<string, string> = {
  sync: "Sincronizzazione",
  list_only: "Solo elenco",
  archive_import: "Import archivio",
  relink: "Ricollega al ruolo",
  credential_test: "Test login",
};

export const LINK_STATUS_LABELS: Record<StepLinkStatus, string> = {
  linked: "Collegati",
  not_found: "Avviso non trovato",
  ambiguous: "Ambigui",
  unrecognized: "Riferimento non riconosciuto",
};

export const ACTIVE_JOB_STATUSES = new Set(["pending", "processing"]);

export function formatJobStatus(status: string): string {
  return JOB_STATUS_LABELS[status] ?? status;
}

export function formatJobMode(mode: string): string {
  return JOB_MODE_LABELS[mode] ?? mode;
}

export function jobStatusClassName(status: string): string {
  if (status === "succeeded") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "failed") return "border-red-200 bg-red-50 text-red-700";
  if (status === "cancelled") return "border-gray-200 bg-gray-50 text-gray-600";
  return "border-amber-200 bg-amber-50 text-amber-700";
}

export function formatEuro(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const amount = Number(value);
  if (Number.isNaN(amount)) return String(value);
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(amount);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const [year, month, day] = value.split("-");
  return day && month && year ? `${day}/${month}/${year}` : value;
}

function resultCount(result: Record<string, unknown>, key: string): number | null {
  const value = result[key];
  return typeof value === "number" ? value : null;
}

export function summarizeJob(job: StepSyncJob): string {
  if (job.error_detail) return job.error_detail;
  const result = job.result_json ?? {};
  const progress = (result.progress as Record<string, unknown> | undefined) ?? {};
  if (result.ok === true) return "Login verificato";
  const parts: string[] = [];
  const imported = resultCount(result, "imported") ?? resultCount(progress, "imported");
  const rows = resultCount(result, "list_rows") ?? resultCount(progress, "list_rows");
  const details = resultCount(result, "details") ?? resultCount(progress, "details");
  if (imported !== null) parts.push(`${imported} schede importate`);
  if (rows !== null) parts.push(`${rows} righe elenco`);
  if (details !== null) parts.push(`${details} schede lette`);
  const errors = result.errors;
  if (Array.isArray(errors) && errors.length > 0) parts.push(`${errors.length} errori`);
  return parts.length > 0 ? parts.join(" · ") : "—";
}
