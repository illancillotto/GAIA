"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { SearchIcon } from "@/components/ui/icons";
import type { WikiRequest } from "@/types/api";

type WikiRequestsListProps = {
  filteredItems: WikiRequest[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (requestId: string) => void;
  formatDateTime: (value: string) => string;
  statusBadgeClasses: (status: WikiRequest["status"]) => string;
  statusLabel: (status: WikiRequest["status"]) => string;
  requestTypeLabel: (requestType: WikiRequest["request_type"]) => string;
  priorityBadgeClasses: (priority: WikiRequest["priority"]) => string;
  priorityLabel: (priority: WikiRequest["priority"]) => string;
  severityBadgeClasses: (severity: WikiRequest["severity"]) => string;
  severityLabel: (severity: WikiRequest["severity"]) => string;
};

export function WikiRequestsList({
  filteredItems,
  loading,
  selectedId,
  onSelect,
  formatDateTime,
  statusBadgeClasses,
  statusLabel,
  requestTypeLabel,
  priorityBadgeClasses,
  priorityLabel,
  severityBadgeClasses,
  severityLabel,
}: WikiRequestsListProps) {
  return (
    <article className="rounded-3xl border border-[#d9dfd4] bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-gray-100 pb-3">
        <div>
          <p className="text-sm font-semibold text-gray-900">Coda richieste</p>
          <p className="text-xs text-gray-500">{filteredItems.length} elementi nel filtro corrente.</p>
        </div>
      </div>
      <div className="mt-4 space-y-3">
        {loading ? (
          <p className="text-sm text-gray-500">Caricamento richieste...</p>
        ) : filteredItems.length === 0 ? (
          <EmptyState icon={SearchIcon} title="Nessuna richiesta trovata" description="Prova a modificare i filtri o la ricerca." />
        ) : (
          filteredItems.map((item) => {
            const isSelected = item.id === selectedId;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelect(item.id)}
                className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                  isSelected
                    ? "border-[#1D4E35] bg-[#eef6ef] shadow-sm"
                    : "border-gray-200 bg-white hover:border-[#bfd0c3] hover:bg-[#f8fbf8]"
                }`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadgeClasses(item.status)}`}>
                    {statusLabel(item.status)}
                  </span>
                  <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600">
                    {requestTypeLabel(item.request_type)}
                  </span>
                  <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${priorityBadgeClasses(item.priority)}`}>
                    {priorityLabel(item.priority)}
                  </span>
                  <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${severityBadgeClasses(item.severity)}`}>
                    {severityLabel(item.severity)}
                  </span>
                  <span className="text-xs text-gray-400">{formatDateTime(item.created_at)}</span>
                </div>
                <p className="mt-2 line-clamp-2 text-sm font-medium text-gray-900">{item.user_question}</p>
                <p className="mt-2 text-xs text-gray-500">
                  Creata da <span className="font-medium text-gray-700">{item.created_by ?? "n/d"}</span>
                  {item.assigned_to_name ? (
                    <>
                      {" · "}Assegnata a <span className="font-medium text-gray-700">{item.assigned_to_name}</span>
                    </>
                  ) : null}
                </p>
              </button>
            );
          })
        )}
      </div>
    </article>
  );
}
