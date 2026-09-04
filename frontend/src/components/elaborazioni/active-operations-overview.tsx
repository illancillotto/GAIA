"use client";

import { AutoSyncMonitorLink } from "@/components/elaborazioni/autosync-monitor-link";
import { ChevronRightIcon, RefreshIcon } from "@/components/ui/icons";
import { collapseRunningOperationsByArea } from "@/lib/elaborazioni-dashboard-overview";
import { formatDateTime } from "@/lib/presentation";

export type DashboardRunningOperation = {
  id: string;
  area: string;
  title: string;
  detail: string;
  startedAt: string | null;
  statusLabel: "In coda" | "In corso" | "In ripresa";
  href: string;
  progress?: {
    completed: number | null;
    total: number | null;
    percent: number | null;
    failed?: number | null;
  };
};

type ActiveOperationsOverviewProps = {
  attentionCount: number;
  isLive: boolean;
  onOpen: (operation: DashboardRunningOperation) => void;
  operations: DashboardRunningOperation[];
};

function boundedPercent(value: number): number {
  return Math.min(100, Math.max(0, value));
}

function operationProgress(operation: DashboardRunningOperation): number | null {
  if (operation.progress?.percent != null) return boundedPercent(operation.progress.percent);
  if (operation.progress?.completed == null || !operation.progress.total) return null;
  return boundedPercent((operation.progress.completed / operation.progress.total) * 100);
}

function OperationRow({ operation, onOpen }: { operation: DashboardRunningOperation; onOpen: (operation: DashboardRunningOperation) => void }) {
  const progress = operationProgress(operation);

  return (
    <article className="grid gap-4 p-4 transition-colors hover:bg-[#f8faf8] md:grid-cols-[minmax(0,1fr),minmax(210px,0.45fr),auto] md:items-center md:px-5">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800">
            <span className="h-2 w-2 animate-pulse rounded-full bg-amber-500" aria-hidden="true" />
            {operation.statusLabel}
          </span>
          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-gray-500">{operation.area}</span>
        </div>
        <h3 className="mt-2 truncate text-base font-semibold text-gray-950">{operation.title}</h3>
        <p className="mt-1 line-clamp-2 text-sm leading-5 text-gray-600">{operation.detail}</p>
      </div>

      <div>
        {progress != null ? (
          <div>
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="font-medium text-gray-700">{operation.progress?.completed ?? "—"} di {operation.progress?.total ?? "—"}</span>
              <span className="font-semibold text-[#1D4E35]">{Math.round(progress)}%</span>
            </div>
            <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-[#dfe9e1]" role="progressbar" aria-label={`Avanzamento ${operation.title}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)}>
              <div className="h-full rounded-full bg-[#24734a] transition-[width] duration-500" style={{ width: `${progress}%` }} />
            </div>
            {operation.progress?.failed ? <p className="mt-1.5 text-xs font-medium text-red-700">{operation.progress.failed} con errore</p> : null}
          </div>
        ) : (
          <div className="rounded-xl bg-gray-50 px-3 py-2 text-sm text-gray-600">
            <span className="block text-xs text-gray-500">Avviata</span>
            <span className="mt-0.5 block font-medium text-gray-900">{formatDateTime(operation.startedAt)}</span>
          </div>
        )}
      </div>

      <button className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-[#bad0c1] bg-white px-4 py-2.5 text-sm font-semibold text-[#1D4E35] transition hover:border-[#1D4E35] hover:bg-[#edf5ef]" onClick={() => onOpen(operation)} type="button">
        Apri monitor
        <ChevronRightIcon className="h-4 w-4" />
      </button>
    </article>
  );
}

function OverflowRow({
  area,
  hiddenCount,
  onOpen,
  sample,
}: {
  area: string;
  hiddenCount: number;
  onOpen: (operation: DashboardRunningOperation) => void;
  sample: DashboardRunningOperation;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 bg-[#f7faf8] px-4 py-3 md:px-5">
      <p className="text-sm text-gray-600">
        Altri {hiddenCount} {area}
      </p>
      <button
        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-[#bad0c1] bg-white px-4 py-2.5 text-sm font-semibold text-[#1D4E35] transition hover:border-[#1D4E35] hover:bg-[#edf5ef]"
        onClick={() => onOpen(sample)}
        type="button"
      >
        Apri monitor
        <ChevronRightIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

export function ActiveOperationsOverview({ attentionCount, isLive, onOpen, operations }: ActiveOperationsOverviewProps) {
  const collapsed = collapseRunningOperationsByArea(operations);

  return (
    <section className="mt-4 overflow-hidden rounded-[24px] border border-[#cfd9d1] bg-white/95 shadow-sm" aria-labelledby="active-operations-title">
      <div className="grid gap-4 border-b border-[#e5ebe6] bg-[linear-gradient(115deg,_#173f2b_0%,_#245b3d_58%,_#e6efe8_58%,_#f6f4eb_100%)] p-5 text-white md:grid-cols-[1fr,auto] md:items-center">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-100">
            <RefreshIcon className={isLive ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            Quadro lavorazioni
          </div>
          <h2 id="active-operations-title" className="mt-2 text-2xl font-semibold tracking-tight">
            {operations.length === 0 ? "Nessuna lavorazione in corso" : `${operations.length} lavorazioni in corso`}
          </h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-emerald-50/90">
            {isLive
              ? "I dati si aggiornano automaticamente. Non serve ricaricare la pagina."
              : "Il quadro si aggiorna quando torni su questa pagina."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 md:max-w-[260px] md:justify-end">
          <AutoSyncMonitorLink />
          <span className="rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold ring-1 ring-white/25">
            {operations.length} attive
          </span>
          <span className={attentionCount > 0 ? "rounded-full bg-amber-300 px-3 py-1.5 text-xs font-semibold text-amber-950" : "rounded-full bg-emerald-100 px-3 py-1.5 text-xs font-semibold text-emerald-900"}>
            {attentionCount > 0 ? `${attentionCount} da controllare` : "Nessun problema"}
          </span>
        </div>
      </div>

      {operations.length === 0 ? (
        <div className="p-6 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-[#1D4E35]">
            <RefreshIcon className="h-5 w-5" />
          </div>
          <p className="mt-3 text-base font-semibold text-gray-900">Tutto tranquillo</p>
          <p className="mt-1 text-sm text-gray-600">Non ci sono batch, import o sincronizzazioni da seguire.</p>
        </div>
      ) : (
        <div className="divide-y divide-gray-100">
          {collapsed.items.map((operation) => <OperationRow key={operation.id} operation={operation} onOpen={onOpen} />)}
          {collapsed.hiddenByArea.map((hidden) => (
            <OverflowRow
              area={hidden.area}
              hiddenCount={hidden.hiddenCount}
              key={hidden.area}
              onOpen={onOpen}
              sample={hidden.sample}
            />
          ))}
        </div>
      )}
    </section>
  );
}
