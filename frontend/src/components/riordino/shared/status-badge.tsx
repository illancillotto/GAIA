"use client";

import { cn } from "@/lib/cn";
import { formatRiordinoLabel } from "@/components/riordino/shared/format";

const tones: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  open: "bg-sky-50 text-sky-700",
  in_progress: "bg-sky-50 text-sky-700",
  in_review: "bg-indigo-50 text-indigo-700",
  completed: "bg-emerald-50 text-emerald-700",
  done: "bg-emerald-50 text-emerald-700",
  skipped: "bg-gray-100 text-gray-500 line-through",
  blocked: "bg-amber-50 text-amber-800",
  archived: "bg-gray-200 text-gray-700",
  not_started: "bg-gray-100 text-gray-600",
  phase_1: "bg-lime-50 text-lime-800",
  phase_2: "bg-cyan-50 text-cyan-800",
  low: "bg-gray-100 text-gray-700",
  medium: "bg-amber-50 text-amber-800",
  high: "bg-orange-50 text-orange-800",
  blocking: "bg-red-50 text-red-700",
  resolved_accepted: "bg-emerald-50 text-emerald-700",
  resolved_rejected: "bg-rose-50 text-rose-700",
  under_review: "bg-violet-50 text-violet-700",
  withdrawn: "bg-slate-100 text-slate-700",
};

const labels: Record<string, string> = {
  draft: "Bozza",
  open: "Aperta",
  in_progress: "In corso",
  in_review: "In revisione",
  completed: "Completata",
  done: "Completato",
  skipped: "Saltato",
  blocked: "Bloccato",
  archived: "Archiviata",
  not_started: "Non avviata",
  phase_1: "Fase 1",
  phase_2: "Fase 2",
  low: "Bassa",
  medium: "Media",
  high: "Alta",
  blocking: "Bloccante",
  resolved_accepted: "Accolto",
  resolved_rejected: "Respinto",
  under_review: "In esame",
  withdrawn: "Ritirato",
};

function getDeadlineTone(dueAt: string | null | undefined): string | null {
  if (!dueAt) {
    return null;
  }

  const target = new Date(dueAt).getTime();
  if (Number.isNaN(target)) {
    return null;
  }

  const days = (target - Date.now()) / (1000 * 60 * 60 * 24);
  if (days < 0) {
    return "bg-red-50 text-red-700";
  }
  if (days <= 7) {
    return "bg-red-50 text-red-700";
  }
  if (days <= 30) {
    return "bg-amber-50 text-amber-800";
  }
  return null;
}

export function RiordinoStatusBadge({
  value,
  dueAt,
}: {
  value: string;
  dueAt?: string | null;
}) {
  const deadlineTone = getDeadlineTone(dueAt);

  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2.5 py-1 text-xs font-medium",
        deadlineTone ?? tones[value] ?? "bg-gray-100 text-gray-700",
      )}
      title={dueAt ? `Scadenza: ${dueAt}` : undefined}
    >
      {labels[value] ?? formatRiordinoLabel(value)}
    </span>
  );
}
