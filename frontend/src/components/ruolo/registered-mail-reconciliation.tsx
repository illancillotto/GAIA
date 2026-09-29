"use client";

import { useCallback, useEffect, useState } from "react";

import { getRegisteredMailCampaignPreview } from "@/lib/registered-mail-api";
import type { RegisteredMailCampaignItem, RegisteredMailCampaignPreview } from "@/types/registered-mail-campaign";
import { parseOperatorRows, workbookEvidence, type OperatorWorkbook } from "./registered-mail-workbook";
import { RegisteredMailReviewDetail } from "./registered-mail-review-detail";

const CAMPAIGN_CUTOFF = "2026-09-29T00:00:00+02:00";
const PAGE_SIZE = 20;

function classificationLabel(value: string): string {
  return ({ proposed_pair: "Coppia da verificare", extend_single_link: "Estensione da verificare", incomplete: "Avvisi incompleti", ambiguous: "Ambigua", already_registered: "Gia nel Registro", review_required: "Verifica necessaria" } as Record<string, string>)[value] ?? value;
}

function ReconciliationHeader({ workbook, loading, error, onFile }: {
  workbook: OperatorWorkbook | null;
  loading: boolean;
  error: string | null;
  onFile: (file: File) => void;
}) {
  return <div className="border-b border-[#edf1eb] bg-[#f3f7ef] p-6">
    <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#1D4E35]">Campagna storica 2022-2023</p>
    <h2 className="mt-2 text-xl font-semibold">Riconciliazione assistita</h2>
    <p className="mt-1 max-w-3xl text-sm text-gray-600">Carica il foglio degli operatori: resta nel browser. Ogni associazione richiede conferma individuale.</p>
    <label className="mt-4 inline-flex cursor-pointer items-center gap-3 rounded-xl border border-[#9db3a3] bg-white px-4 py-3 text-sm font-semibold text-[#1D4E35]">
      <span>{loading ? "Lettura in corso..." : "Seleziona Excel operatori"}</span>
      <input accept=".xlsx" className="sr-only" disabled={loading} onChange={(event) => { const file = event.target.files?.[0]; if (file) onFile(file); }} type="file" />
    </label>
    {workbook ? <p className="mt-2 text-xs text-gray-600">{workbook.name} - {workbook.rows.length} righe operative - SHA-256 {workbook.sha256.slice(0, 12)}...</p> : null}
    {error ? <p className="mt-2 text-sm text-red-700" role="alert">{error}</p> : null}
  </div>;
}

function ReconciliationFilters({ counts, total, filter, onFilter }: {
  counts: Record<string, number>;
  total: number;
  filter: string;
  onFilter: (value: string) => void;
}) {
  return <div className="flex flex-wrap gap-2">
    {["proposed_pair", "extend_single_link", "incomplete", "ambiguous", "review_required", "already_registered", "all"].map((value) =>
      <button className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${filter === value ? "border-[#1D4E35] bg-[#1D4E35] text-white" : "border-gray-200 text-gray-600"}`} key={value} onClick={() => onFilter(value)} type="button">
        {value === "all" ? "Tutte" : classificationLabel(value)} {value === "all" ? total : counts[value] ?? 0}
      </button>)}
  </div>;
}

function ReconciliationRows({ items, workbook, selected, onSelect, token, onSaved }: {
  items: RegisteredMailCampaignItem[];
  workbook: OperatorWorkbook | null;
  selected: string | null;
  onSelect: (mailId: string | null) => void;
  token: string;
  onSaved: () => void;
}) {
  return <div className="mt-4 divide-y divide-gray-100 border-y border-gray-100">
    {items.map((item) => <div key={item.mail_id}>
      <button aria-expanded={selected === item.mail_id} className="flex w-full flex-wrap items-center justify-between gap-2 py-3 text-left" onClick={() => onSelect(selected === item.mail_id ? null : item.mail_id)} type="button">
        <span><strong>{item.recipient_name ?? "Destinatario non letto"}</strong> <span className="text-xs text-gray-500">- invio {item.source_shipment_id}</span></span>
        <span className="text-xs font-semibold text-[#1D4E35]">{workbook && workbookEvidence(item, workbook.rows) ? "Riga Excel trovata" : "Da verificare"} - {classificationLabel(item.classification)}</span>
      </button>
      {selected === item.mail_id ? <RegisteredMailReviewDetail item={item} key={item.mail_id} onSaved={onSaved} token={token} workbook={workbook} /> : null}
    </div>)}
  </div>;
}


export function RegisteredMailReconciliation({ token, canEdit }: { token: string; canEdit: boolean }) {
  const [preview, setPreview] = useState<RegisteredMailCampaignPreview | null>(null);
  const [workbook, setWorkbook] = useState<OperatorWorkbook | null>(null);
  const [filter, setFilter] = useState("proposed_pair");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadPreview = useCallback(async (): Promise<void> => {
    try {
      setPreview(await getRegisteredMailCampaignPreview(token, CAMPAIGN_CUTOFF));
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Anteprima non disponibile");
    }
  }, [token]);

  useEffect(() => { if (canEdit) void loadPreview(); }, [canEdit, loadPreview]);

  async function loadWorkbook(file: File): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const bytes = await file.arrayBuffer();
      const xlsx = await import("xlsx");
      const book = xlsx.read(bytes, { type: "array" });
      const sheet = book.Sheets.Dati;
      if (!sheet) throw new Error("Il foglio Dati non e presente");
      const rows = parseOperatorRows(xlsx.utils.sheet_to_json<unknown[]>(sheet, { header: 1, raw: false }));
      if (!rows.length) throw new Error("Nessuna riga operativa 2022/2023 trovata");
      const digest = await crypto.subtle.digest("SHA-256", bytes);
      const sha256 = Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, "0")).join("");
      setWorkbook({ sha256, name: file.name, rows });
    } catch (cause) {
      setWorkbook(null);
      setError(cause instanceof Error ? cause.message : "Impossibile leggere il file Excel");
    } finally {
      setLoading(false);
    }
  }

  if (!canEdit) return null;
  const items = (preview?.items ?? []).filter((item) => filter === "all" || item.classification === filter);
  const visible = items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  return <section className="mb-6 overflow-hidden rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
    <ReconciliationHeader error={error} loading={loading} onFile={(file) => void loadWorkbook(file)} workbook={workbook} />
    <div className="p-6">
      <ReconciliationFilters counts={preview?.counts ?? {}} filter={filter} onFilter={(value) => { setFilter(value); setPage(0); setSelected(null); }} total={preview?.total ?? 0} />
      {!preview ? <p className="mt-4 text-sm text-gray-500">Caricamento anteprima...</p> : null}
      <ReconciliationRows items={visible} onSaved={() => void loadPreview()} onSelect={setSelected} selected={selected} token={token} workbook={workbook} />
      <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
        <span>{visible.length} di {items.length} mostrati - pagina {page + 1}</span>
        <div className="flex gap-2"><button className="btn-secondary" disabled={page === 0} onClick={() => setPage(page - 1)} type="button">Precedente</button><button className="btn-secondary" disabled={(page + 1) * PAGE_SIZE >= items.length} onClick={() => setPage(page + 1)} type="button">Successiva</button></div>
      </div>
    </div>
  </section>;
}
