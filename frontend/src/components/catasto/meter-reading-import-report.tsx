"use client";

import type { CatMeterReadingImportPreview } from "@/types/catasto";

export function MeterReadingImportReport({ preview }: { preview: CatMeterReadingImportPreview | null }) {
  if (!preview) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 bg-white px-4 py-5 text-sm text-slate-500">
        Nessuna anteprima disponibile.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="section-title">Report validazione</p>
          <p className="section-copy">
            {preview.filename} · {preview.distretto_numero ? `D${preview.distretto_numero}` : "Distretto non dedotto"}
            {preview.distretto_nome ? ` · ${preview.distretto_nome}` : ""}
          </p>
        </div>
        <div className="text-sm text-slate-500">Anno {preview.anno ?? "—"}</div>
      </div>

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
}
