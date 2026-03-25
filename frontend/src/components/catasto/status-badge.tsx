"use client";

import { cn } from "@/lib/cn";
import type { CatastoBatch, CatastoRequestStatus } from "@/types/api";

type StatusValue = CatastoRequestStatus | CatastoBatch["status"];

const STATUS_CONFIG: Record<StatusValue, { label: string; className: string; dotClassName: string }> = {
  pending: {
    label: "Pending",
    className: "bg-gray-100 text-gray-600",
    dotClassName: "bg-gray-400",
  },
  processing: {
    label: "Processing",
    className: "bg-sky-100 text-sky-700",
    dotClassName: "bg-sky-500",
  },
  awaiting_captcha: {
    label: "CAPTCHA",
    className: "bg-amber-100 text-amber-700",
    dotClassName: "bg-amber-500",
  },
  completed: {
    label: "Completed",
    className: "bg-emerald-100 text-emerald-700",
    dotClassName: "bg-emerald-500",
  },
  failed: {
    label: "Failed",
    className: "bg-red-100 text-red-700",
    dotClassName: "bg-red-500",
  },
  skipped: {
    label: "Skipped",
    className: "bg-slate-100 text-slate-700",
    dotClassName: "bg-slate-500",
  },
  cancelled: {
    label: "Cancelled",
    className: "bg-slate-100 text-slate-700",
    dotClassName: "bg-slate-500",
  },
};

export function CatastoStatusBadge({ status }: { status: StatusValue }) {
  const config = STATUS_CONFIG[status];

  return (
    <span className={cn("inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium", config.className)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dotClassName)} />
      {config.label}
    </span>
  );
}
