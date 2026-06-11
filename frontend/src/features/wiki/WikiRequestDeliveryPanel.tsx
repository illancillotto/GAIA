"use client";

type DeliveryStatusValue = "discovery" | "planned" | "in_progress" | "released" | "wont_do";

type Props = {
  externalTicketKey: string | null;
  externalTicketUrl: string | null;
  deliveryStatus: string | null;
  draftExternalTicketKey: string;
  draftExternalTicketUrl: string;
  draftDeliveryStatus: DeliveryStatusValue;
  draftDeliveryNotes: string;
  deliveryStatusOptions: Array<{ value: DeliveryStatusValue; label: string }>;
  onExternalTicketKeyChange: (value: string) => void;
  onExternalTicketUrlChange: (value: string) => void;
  onDeliveryStatusChange: (value: DeliveryStatusValue) => void;
  onDeliveryNotesChange: (value: string) => void;
};

export function WikiRequestDeliveryPanel({
  externalTicketKey,
  externalTicketUrl,
  deliveryStatus,
  draftExternalTicketKey,
  draftExternalTicketUrl,
  draftDeliveryStatus,
  draftDeliveryNotes,
  deliveryStatusOptions,
  onExternalTicketKeyChange,
  onExternalTicketUrlChange,
  onDeliveryStatusChange,
  onDeliveryNotesChange,
}: Props) {
  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Ticket esterno</p>
          <p className="mt-2 break-words">{externalTicketKey || "n/d"}</p>
        </div>
        <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700 md:col-span-2">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">URL ticket</p>
          {externalTicketUrl ? (
            <a href={externalTicketUrl} target="_blank" rel="noreferrer" className="mt-2 block break-all text-[#1D4E35] underline underline-offset-2">
              {externalTicketUrl}
            </a>
          ) : (
            <p className="mt-2 break-all">n/d</p>
          )}
        </div>
        <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Delivery</p>
          <p className="mt-2 break-words">{deliveryStatus || "n/d"}</p>
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] p-4">
        <div className="mb-3">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Delivery</p>
          <p className="mt-1 text-sm text-gray-500">Collega la richiesta a un ticket esterno e tieni traccia dello stato di consegna.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Ticket key</span>
            <input
              value={draftExternalTicketKey}
              onChange={(event) => onExternalTicketKeyChange(event.target.value)}
              placeholder="GAIA-123"
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            />
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Delivery status</span>
            <select
              value={draftDeliveryStatus}
              onChange={(event) => onDeliveryStatusChange(event.target.value as DeliveryStatusValue)}
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            >
              {deliveryStatusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="mt-4 block space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Ticket URL</span>
          <input
            value={draftExternalTicketUrl}
            onChange={(event) => onExternalTicketUrlChange(event.target.value)}
            placeholder="https://tracker.example.com/browse/GAIA-123"
            className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
          />
        </label>
        <label className="mt-4 block space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Note delivery</span>
          <textarea
            value={draftDeliveryNotes}
            onChange={(event) => onDeliveryNotesChange(event.target.value)}
            rows={4}
            placeholder="Link con delivery reale, milestone, branch, note di rilascio o motivazione del no-go."
            className="w-full rounded-2xl border border-gray-200 px-3 py-3 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
          />
        </label>
      </div>
    </>
  );
}
