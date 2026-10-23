import type { Dispatch, SetStateAction } from "react";

export type PaymentStatusFilterState = [string, Dispatch<SetStateAction<string>>];

const PAYMENT_STATUS_SHORTCUTS: Array<{ value: string; label: string }> = [
  { value: "", label: "Tutti gli stati" },
  { value: "unpaid", label: "Non pagati" },
  { value: "partial", label: "Pagamenti parziali" },
];

type TributiPaymentFiltersProps = {
  openOnly: boolean;
  onOpenOnlyChange: (openOnly: boolean) => void;
  paymentStatusFilter: PaymentStatusFilterState;
};

export function TributiPaymentFilters({ openOnly, onOpenOnlyChange, paymentStatusFilter }: TributiPaymentFiltersProps) {
  const [paymentStatus, onPaymentStatusChange] = paymentStatusFilter;
  return (
    <>
      <div className="grid gap-1">
        <label className="flex items-center gap-2 rounded-xl border border-[#e3e9e0] bg-[#fbfcfb] px-4 py-3 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={openOnly}
            onChange={(event) => {
              onOpenOnlyChange(event.target.checked);
              if (event.target.checked && !isOutstandingStatus(paymentStatus)) onPaymentStatusChange("");
            }}
            aria-describedby="tributi-saldo-hint"
          />
          Solo non pagati (anche parziali)
        </label>
        <span id="tributi-saldo-hint" className="text-xs text-gray-500">
          Esclude i saldati; restano visibili le posizioni con saldo da verificare.
        </span>
      </div>
      <div role="group" aria-label="Stato pagamento" className="flex flex-wrap gap-2 pb-5">
        {PAYMENT_STATUS_SHORTCUTS.map((shortcut) => {
          const selected = paymentStatus === shortcut.value;
          return (
            <button
              key={shortcut.value || "all"}
              type="button"
              aria-pressed={selected}
              onClick={() => onPaymentStatusChange(shortcut.value)}
              className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${
                selected
                  ? "border-[#1D4E35] bg-[#1D4E35] text-white shadow-sm"
                  : "border-[#d8dfd3] bg-white text-gray-700 hover:border-[#8CB39D] hover:bg-[#f4faf6]"
              }`}
            >
              {shortcut.label}
            </button>
          );
        })}
      </div>
    </>
  );
}

function isOutstandingStatus(paymentStatus: string): boolean {
  return paymentStatus === "unpaid" || paymentStatus === "partial";
}
