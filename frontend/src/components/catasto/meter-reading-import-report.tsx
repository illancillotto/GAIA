"use client";

import { useMemo, useState } from "react";

import type { CatMeterReadingImportPreview, CatMeterReadingImportPreviewItem } from "@/types/catasto";

export type MeterReadingImportReportItem = {
  filename: string;
  preview: CatMeterReadingImportPreview;
};

function readStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function ValidationStatusBadge({ status }: { status: string }) {
  const tone =
    status === "error"
      ? "bg-rose-100 text-rose-800"
      : status === "warning"
        ? "bg-amber-100 text-amber-800"
        : "bg-emerald-100 text-emerald-800";
  const label = status === "error" ? "Errore" : status === "warning" ? "Warning" : "Valida";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${tone}`}>{label}</span>;
}

function MeterReadingImportIssuesModal({
  item,
  onClose,
}: {
  item: MeterReadingImportReportItem;
  onClose: () => void;
}) {
  const issueRows = useMemo(
    () => item.preview.items.filter((row) => row.validation_status !== "valid" || row.validation_messages.length > 0),
    [item],
  );

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
      <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Dettaglio validazione</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-900">{item.filename}</h2>
            <p className="mt-1 text-sm text-slate-500">
              {item.preview.distretto_numero ? `Distretto D${item.preview.distretto_numero}` : "Distretto non dedotto"}
              {item.preview.distretto_nome ? ` · ${item.preview.distretto_nome}` : ""}
              {item.preview.anno ? ` · Anno ${item.preview.anno}` : ""}
            </p>
          </div>
          <button className="btn-secondary" type="button" onClick={onClose}>
            Chiudi
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5">
          {!item.preview.distretto_id ? (
            <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              Il distretto non e stato dedotto dal nome file. Rinomina il file con il codice o con il nome del distretto.
            </div>
          ) : null}

          {issueRows.length === 0 ? (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
              Nessun warning o errore su questo file.
            </div>
          ) : (
            <div className="space-y-3">
              {issueRows.map((row) => (
                <div key={`${item.filename}-${row.row_number}`} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                  {(() => {
                    const sharedSubjects = readStringArray(row.data?.shared_meter_subject_labels);
                    const taxCodes = readStringArray(row.data?.tax_code_candidates);

                    return (
                      <>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        Riga {row.row_number}
                        {row.punto_consegna ? ` · ${row.punto_consegna}` : ""}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {row.subject_display_name ?? row.codice_fiscale_normalizzato ?? row.codice_fiscale ?? "Soggetto non risolto"}
                      </p>
                    </div>
                    <ValidationStatusBadge status={row.validation_status} />
                  </div>
                  {sharedSubjects.length > 0 ? (
                    <div className="mt-3 rounded-xl border border-sky-200 bg-sky-50 px-3 py-3 text-sm text-sky-900">
                      <p className="font-semibold">Soggetti candidati</p>
                      <p className="mt-1">{sharedSubjects.join(", ")}</p>
                      {taxCodes.length > 0 ? <p className="mt-1 text-xs text-sky-800">CF/P.IVA rilevati: {taxCodes.join(" · ")}</p> : null}
                    </div>
                  ) : null}
                  <div className="mt-3 space-y-2">
                    {row.validation_messages.map((message, index) => (
                      <div
                        key={`${row.row_number}-${message.code}-${index}`}
                        className={`rounded-xl px-3 py-2 text-sm ${
                          message.level === "error"
                            ? "bg-rose-100 text-rose-900"
                            : message.level === "warning"
                              ? "bg-amber-100 text-amber-900"
                              : "bg-slate-100 text-slate-800"
                        }`}
                      >
                        <span className="font-semibold">{message.code}</span>
                        {message.field ? ` · ${message.field}` : ""}
                        {`: ${message.message}`}
                      </div>
                    ))}
                  </div>
                      </>
                    );
                  })()}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function fileHasIssues(preview: CatMeterReadingImportPreview): boolean {
  return !preview.distretto_id || preview.righe_con_warning > 0 || preview.righe_con_errori > 0;
}

export function MeterReadingImportReport({ previews }: { previews: MeterReadingImportReportItem[] }) {
  const [selectedItem, setSelectedItem] = useState<MeterReadingImportReportItem | null>(null);

  if (previews.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 bg-white px-4 py-5 text-sm text-slate-500">
        Nessuna anteprima disponibile.
      </div>
    );
  }

  return (
    <>
      <div className="space-y-4">
        {previews.map((item) => {
          const { filename, preview } = item;
          const hasIssues = fileHasIssues(preview);
          return (
            <div key={filename} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="section-title">Report validazione</p>
                  <p className="section-copy">
                    {filename} · {preview.distretto_numero ? `D${preview.distretto_numero}` : "Distretto non dedotto"}
                    {preview.distretto_nome ? ` · ${preview.distretto_nome}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-sm text-slate-500">Anno {preview.anno ?? "—"}</div>
                  {hasIssues ? (
                    <button className="btn-secondary" type="button" onClick={() => setSelectedItem(item)}>
                      Vedi errori
                    </button>
                  ) : null}
                </div>
              </div>

              {!preview.distretto_id ? (
                <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
                  Distretto non dedotto dal nome file. Apri il dettaglio per vedere il problema e i controlli bloccanti.
                </div>
              ) : null}

              <div className="mt-4 grid gap-3 md:grid-cols-4">
                <div className="rounded-xl bg-slate-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Righe</p>
                  <p className="mt-2 text-2xl font-semibold text-slate-900">{preview.totale_righe}</p>
                </div>
                <div className="rounded-xl bg-emerald-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Valide</p>
                  <p className="mt-2 text-2xl font-semibold text-emerald-900">{preview.righe_valide}</p>
                </div>
                <div className="rounded-xl bg-amber-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Warning</p>
                  <p className="mt-2 text-2xl font-semibold text-amber-900">{preview.righe_con_warning}</p>
                </div>
                <div className="rounded-xl bg-rose-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-rose-700">Errori</p>
                  <p className="mt-2 text-2xl font-semibold text-rose-900">{preview.righe_con_errori}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {selectedItem ? <MeterReadingImportIssuesModal item={selectedItem} onClose={() => setSelectedItem(null)} /> : null}
    </>
  );
}
