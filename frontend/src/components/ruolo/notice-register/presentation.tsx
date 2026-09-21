import type { ReactNode } from "react";

export const NOTIFICATIONS = {
  da_verificare: "Da verificare", nessuna_evidenza: "Nessuna evidenza", invio_in_corso: "Invio in corso",
  tentativo_senza_notifica: "Tentativo senza notifica", perfezionata: "Perfezionata",
};
export const RECOVERIES = {
  da_verificare: "Da verificare", non_affidato_verificato: "Non affidato (verificato)",
  affidato: "Affidato", revocato: "Revocato", chiuso: "Chiuso",
};
const ANOMALIES: Record<string, string> = {
  posizioni_assenti: "Posizioni assenti", collegamenti_mancanti: "Collegamenti mancanti",
  collegamenti_discordanti: "Collegamenti discordanti", notifica_da_verificare: "Notifica da verificare",
  step_da_verificare: "STEP da verificare",
};
export const inputClass = "w-full rounded-xl border border-[#d8dfd3] bg-white px-3 py-2 text-sm text-gray-900";
export const panelClass = "min-w-0 rounded-2xl border border-[#d8dfd3] bg-white p-4 sm:p-6";

export function AnomalyLabels({ values }: { values: string[] }) {
  return <ul className="flex flex-wrap gap-2">{values.map((key) => <li key={key} className="rounded-lg bg-amber-50 px-2 py-1 text-xs text-amber-900">{ANOMALIES[key] ?? key}</li>)}</ul>;
}

export function ReadState({ loading, error }: { loading: boolean; error?: string }) {
  if (loading) return <p role="status">Caricamento registro...</p>;
  if (error) return <p role="alert" className="rounded-xl bg-rose-50 p-3 text-rose-800">{error}</p>;
  return null;
}

export function Pagination({ page, total, pageSize, onPage }: { page: number; total: number; pageSize: number; onPage: (page: number) => void }) {
  return <nav aria-label="Paginazione" className="flex flex-wrap items-center gap-3 py-3 text-sm">
    <button className="btn-secondary" disabled={page === 1} onClick={() => onPage(page - 1)}>Precedente</button>
    <span>Pagina {page} | {total} risultati</span>
    <button className="btn-secondary" disabled={page * pageSize >= total} onClick={() => onPage(page + 1)}>Successiva</button>
  </nav>;
}

export function JsonDetails({ title, value }: { title: string; value: unknown }) {
  return <details className="min-w-0 rounded-xl bg-[#f7faf7] p-3"><summary className="cursor-pointer text-sm font-medium">{title}</summary>
    <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-all text-xs">{JSON.stringify(value, null, 2)}</pre>
  </details>;
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="grid gap-1 text-sm font-medium text-gray-700">{label}{children}</label>;
}
