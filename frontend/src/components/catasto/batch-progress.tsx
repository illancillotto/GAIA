"use client";

import type { CatastoBatch } from "@/types/api";

type BatchProgressProps = {
  batch: CatastoBatch;
};

export function BatchProgress({ batch }: BatchProgressProps) {
  const processed = batch.completed_items + batch.failed_items + batch.skipped_items;
  const percentage = batch.total_items > 0 ? Math.round((processed / batch.total_items) * 100) : 0;

  return (
    <article className="panel-card">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="section-title">Avanzamento batch</p>
          <p className="section-copy">{batch.current_operation ?? "In attesa del worker Catasto"}</p>
        </div>
        <div className="text-sm font-medium text-gray-700">
          {processed}/{batch.total_items} · {percentage}%
        </div>
      </div>
      <div className="mt-4 h-3 overflow-hidden rounded-full bg-gray-100">
        <div className="h-full rounded-full bg-[#1D4E35] transition-all" style={{ width: `${percentage}%` }} />
      </div>
      <div className="mt-4 grid gap-3 text-sm text-gray-600 md:grid-cols-4">
        <div>Completate: <span className="font-medium text-emerald-700">{batch.completed_items}</span></div>
        <div>Fallite: <span className="font-medium text-red-700">{batch.failed_items}</span></div>
        <div>Saltate: <span className="font-medium text-slate-700">{batch.skipped_items}</span></div>
        <div>Stato batch: <span className="font-medium text-gray-900">{batch.status}</span></div>
      </div>
    </article>
  );
}
