"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { RefreshIcon } from "@/components/ui/icons";
import { formatRiordinoDate, formatRiordinoLabel } from "@/components/riordino/shared/format";
import type { RiordinoEvent } from "@/types/riordino";

export function RiordinoTimelinePanel({ events }: { events: RiordinoEvent[] }) {
  return (
    <article className="panel-card">
      <p className="section-title">Timeline</p>
      <div className="mt-4 space-y-3">
        {events.length === 0 ? (
          <EmptyState icon={RefreshIcon} title="Nessun evento" description="La timeline della pratica comparira qui con gli eventi di workflow e audit." />
        ) : (
          events.map((event) => (
            <div key={event.id} className="rounded-2xl border border-gray-100 px-4 py-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold text-gray-900">{formatRiordinoLabel(event.event_type)}</p>
                {event.step_id ? <span className="text-xs text-gray-500">step collegato</span> : null}
              </div>
              <p className="mt-1 text-sm text-gray-600">{formatRiordinoDate(event.created_at, true)}</p>
              {event.payload_json ? (
                <pre className="mt-3 overflow-x-auto rounded-xl bg-gray-50 p-3 text-xs text-gray-600">
                  {JSON.stringify(event.payload_json, null, 2)}
                </pre>
              ) : null}
            </div>
          ))
        )}
      </div>
    </article>
  );
}
