"use client";

type Option = {
  value: string;
  label: string;
};

type Props = {
  supportOnly: boolean;
  query: string;
  statusFilter: string;
  categoryFilter: string;
  priorityFilter: string;
  requestTypeFilter: string;
  severityFilter: string;
  deliveryFilter: string;
  ticketFilter: string;
  statusOptions: Option[];
  categoryOptions: Option[];
  priorityOptions: Option[];
  requestTypeOptions: Option[];
  severityOptions: Option[];
  deliveryOptions: Option[];
  ticketOptions: Option[];
  onQueryChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onCategoryChange: (value: string) => void;
  onPriorityChange: (value: string) => void;
  onRequestTypeChange: (value: string) => void;
  onSeverityChange: (value: string) => void;
  onDeliveryChange: (value: string) => void;
  onTicketChange: (value: string) => void;
};

export function WikiRequestsFilters({
  supportOnly,
  query,
  statusFilter,
  categoryFilter,
  priorityFilter,
  requestTypeFilter,
  severityFilter,
  deliveryFilter,
  ticketFilter,
  statusOptions,
  categoryOptions,
  priorityOptions,
  requestTypeOptions,
  severityOptions,
  deliveryOptions,
  ticketOptions,
  onQueryChange,
  onStatusChange,
  onCategoryChange,
  onPriorityChange,
  onRequestTypeChange,
  onSeverityChange,
  onDeliveryChange,
  onTicketChange,
}: Props) {
  const activeFilters = [
    statusFilter !== "all" ? `Stato: ${statusOptions.find((option) => option.value === statusFilter)?.label ?? statusFilter}` : null,
    categoryFilter !== "all" ? `Categoria: ${categoryOptions.find((option) => option.value === categoryFilter)?.label ?? categoryFilter}` : null,
    requestTypeFilter !== "all" ? `Tipo: ${requestTypeOptions.find((option) => option.value === requestTypeFilter)?.label ?? requestTypeFilter}` : null,
    priorityFilter !== "all" ? `Priorita: ${priorityOptions.find((option) => option.value === priorityFilter)?.label ?? priorityFilter}` : null,
    severityFilter !== "all" ? `Severita: ${severityOptions.find((option) => option.value === severityFilter)?.label ?? severityFilter}` : null,
    deliveryFilter !== "all" ? `Delivery: ${deliveryOptions.find((option) => option.value === deliveryFilter)?.label ?? deliveryFilter}` : null,
    ticketFilter !== "all" ? `Ticket: ${ticketOptions.find((option) => option.value === ticketFilter)?.label ?? ticketFilter}` : null,
    query.trim() ? `Ricerca: ${query.trim()}` : null,
  ].filter(Boolean) as string[];

  return (
    <section className="overflow-hidden rounded-[32px] border border-[#d9dfd4] bg-[radial-gradient(circle_at_top_left,_rgba(235,243,236,0.9),_rgba(255,255,255,0.98)_58%)] p-5 shadow-sm">
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#7a897f]">Governance richieste</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-gray-900">{supportOnly ? "Inbox supporto Wiki" : "Richieste registrate dal Wiki"}</h2>
            <p className="mt-2 text-sm leading-6 text-gray-600">
            {supportOnly
              ? "Coda operativa su supporto, anomalie, accesso e problemi dati generati dal Wiki. Usa questa vista per leggere il backlog come una console di triage."
              : "Le richieste vengono generate dai fallback `found=false` del widget e della pagina Wiki."}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3 xl:w-[27rem]">
            <div className="rounded-[24px] border border-white/80 bg-white/80 px-4 py-3 shadow-sm">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#87948c]">Vista</p>
              <p className="mt-2 text-sm font-semibold text-[#223d30]">{supportOnly ? "Supporto operativo" : "Backlog completo"}</p>
            </div>
            <div className="rounded-[24px] border border-white/80 bg-white/80 px-4 py-3 shadow-sm">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#87948c]">Filtri attivi</p>
              <p className="mt-2 text-sm font-semibold text-[#223d30]">{activeFilters.length}</p>
            </div>
            <div className="rounded-[24px] border border-white/80 bg-white/80 px-4 py-3 shadow-sm">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#87948c]">Focus</p>
              <p className="mt-2 text-sm font-semibold text-[#223d30]">{supportOnly ? "Triage e carico" : "Governance e deduplica"}</p>
            </div>
          </div>
        </div>

        {activeFilters.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {activeFilters.map((filter) => (
              <span key={filter} className="rounded-full border border-[#d7e3d9] bg-white/85 px-3 py-1 text-xs font-medium text-[#315744] shadow-sm">
                {filter}
              </span>
            ))}
          </div>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,2fr)]">
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Ricerca</span>
            <input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Cerca per testo, autore, modulo, ticket o note"
              className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Stato</span>
              <select
                value={statusFilter}
                onChange={(event) => onStatusChange(event.target.value)}
                className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              >
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Categoria</span>
              <select
                value={categoryFilter}
                onChange={(event) => onCategoryChange(event.target.value)}
                className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              >
                {categoryOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Priorita</span>
              <select
                value={priorityFilter}
                onChange={(event) => onPriorityChange(event.target.value)}
                className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              >
                {priorityOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Tipo</span>
              <select
                value={requestTypeFilter}
                onChange={(event) => onRequestTypeChange(event.target.value)}
                className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              >
                {requestTypeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Severita</span>
              <select
                value={severityFilter}
                onChange={(event) => onSeverityChange(event.target.value)}
                className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              >
                {severityOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Delivery</span>
              <select
                value={deliveryFilter}
                onChange={(event) => onDeliveryChange(event.target.value)}
                className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              >
                {deliveryOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Ticket</span>
              <select
                value={ticketFilter}
                onChange={(event) => onTicketChange(event.target.value)}
                className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              >
                {ticketOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </div>
    </section>
  );
}
