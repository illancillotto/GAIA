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
  return (
    <section className="rounded-3xl border border-[#d9dfd4] bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Governance richieste</p>
          <h2 className="mt-1 text-xl font-semibold text-gray-900">{supportOnly ? "Inbox supporto Wiki" : "Richieste registrate dal Wiki"}</h2>
          <p className="mt-1 text-sm text-gray-500">
            {supportOnly
              ? "Coda operativa su supporto, anomalie, accesso e problemi dati generati dal Wiki."
              : "Le richieste vengono generate dai fallback `found=false` del widget e della pagina Wiki."}
          </p>
        </div>
        <div className="grid gap-3 md:grid-cols-8">
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Cerca per testo, autore o note"
            className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
          />
          <select
            value={statusFilter}
            onChange={(event) => onStatusChange(event.target.value)}
            className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            value={categoryFilter}
            onChange={(event) => onCategoryChange(event.target.value)}
            className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
          >
            {categoryOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            value={priorityFilter}
            onChange={(event) => onPriorityChange(event.target.value)}
            className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
          >
            {priorityOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            value={requestTypeFilter}
            onChange={(event) => onRequestTypeChange(event.target.value)}
            className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
          >
            {requestTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            value={severityFilter}
            onChange={(event) => onSeverityChange(event.target.value)}
            className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
          >
            {severityOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            value={deliveryFilter}
            onChange={(event) => onDeliveryChange(event.target.value)}
            className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
          >
            {deliveryOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            value={ticketFilter}
            onChange={(event) => onTicketChange(event.target.value)}
            className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
          >
            {ticketOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </section>
  );
}
