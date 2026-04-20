"use client";

import { cn } from "@/lib/cn";
import type { CatAnomaliaStatus } from "@/types/catasto";

const STATUS_STYLE: Record<string, { label: string; className: string }> = {
  aperta: { label: "Aperta", className: "bg-sky-50 text-sky-700" },
  chiusa: { label: "Chiusa", className: "bg-emerald-50 text-emerald-700" },
  ignora: { label: "Ignorata", className: "bg-gray-100 text-gray-600" },
};

export function AnomaliaStatusPill({ status }: { status: CatAnomaliaStatus }) {
  const config = STATUS_STYLE[status] ?? { label: status, className: "bg-gray-100 text-gray-600" };
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium", config.className)}>
      {config.label}
    </span>
  );
}

