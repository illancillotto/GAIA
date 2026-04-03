"use client";

import { cn } from "@/lib/cn";
import type { ElaborazioneBatch, ElaborazioneRequestStatus } from "@/types/api";

type StatusValue = ElaborazioneRequestStatus | ElaborazioneBatch["status"];

const STATUS_CONFIG: Record<StatusValue, { label: string; className: string; dotClassName: string }> = {
  pending: {
    label: "In coda",
    className: "bg-gray-100 text-gray-600",
    dotClassName: "bg-gray-400",
  },
  processing: {
    label: "In lavorazione",
    className: "bg-sky-100 text-sky-700",
    dotClassName: "bg-sky-500",
  },
  awaiting_captcha: {
    label: "Attende CAPTCHA",
    className: "bg-amber-100 text-amber-700",
    dotClassName: "bg-amber-500",
  },
  completed: {
    label: "Completato",
    className: "bg-emerald-100 text-emerald-700",
    dotClassName: "bg-emerald-500",
  },
  failed: {
    label: "Fallito",
    className: "bg-red-100 text-red-700",
    dotClassName: "bg-red-500",
  },
  skipped: {
    label: "Saltato",
    className: "bg-slate-100 text-slate-700",
    dotClassName: "bg-slate-500",
  },
  cancelled: {
    label: "Annullato",
    className: "bg-slate-100 text-slate-700",
    dotClassName: "bg-slate-500",
  },
};

export function ElaborazioneStatusBadge({ status }: { status: StatusValue }) {
  const config = STATUS_CONFIG[status];

  return (
    <span className={cn("inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium", config.className)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dotClassName)} />
      {config.label}
    </span>
  );
}
