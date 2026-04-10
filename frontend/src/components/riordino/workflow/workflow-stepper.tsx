"use client";

import { RiordinoStatusBadge } from "@/components/riordino/shared/status-badge";
import { formatRiordinoLabel } from "@/components/riordino/shared/format";
import type { RiordinoPhase } from "@/types/riordino";

export function RiordinoWorkflowStepper({ phase }: { phase: RiordinoPhase }) {
  return (
    <article className="panel-card">
      <div className="flex flex-wrap items-center gap-3">
        <p className="section-title">Workflow fase corrente</p>
        <RiordinoStatusBadge value={phase.status} />
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {phase.steps.map((step) => (
          <div key={step.id} className="rounded-xl border border-gray-100 bg-white px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-600">
                {step.code}
              </span>
              <RiordinoStatusBadge value={step.status} />
              {step.branch ? (
                <span className="text-[11px] text-gray-500">ramo {formatRiordinoLabel(step.branch)}</span>
              ) : null}
            </div>
            <p className="mt-2 text-sm font-medium text-gray-900">{step.title}</p>
            <p className="mt-1 text-xs text-gray-500">
              {step.documents.length} documenti • {step.checklist_items.length} checklist
            </p>
          </div>
        ))}
      </div>
    </article>
  );
}
