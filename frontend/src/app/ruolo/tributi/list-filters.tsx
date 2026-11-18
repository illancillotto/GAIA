import type { RuoloTributiYearManagerResponse } from "@/types/ruolo";

import { TributiPaymentFilters, type PaymentStatusFilterState } from "./payment-filters";

type TributiListFiltersProps = {
  anno: string;
  openOnly: boolean;
  onAnnoChange: (anno: string) => void;
  onOpenOnlyChange: (openOnly: boolean) => void;
  paymentStatusFilter: PaymentStatusFilterState;
};

export function TributiListFilters({
  anno,
  openOnly,
  onAnnoChange,
  onOpenOnlyChange,
  paymentStatusFilter,
}: TributiListFiltersProps) {
  return (
    <div className="mt-4 flex flex-wrap items-end gap-4">
      <AnnualityYearFilter anno={anno} onAnnoChange={onAnnoChange} />
      <TributiPaymentFilters openOnly={openOnly} onOpenOnlyChange={onOpenOnlyChange} paymentStatusFilter={paymentStatusFilter} />
    </div>
  );
}

function AnnualityYearFilter({ anno, onAnnoChange }: Pick<TributiListFiltersProps, "anno" | "onAnnoChange">) {
  return (
    <div className="grid gap-1 text-sm font-medium text-gray-700">
      <label htmlFor="tributi-anno">Anno tributario</label>
      <input
        id="tributi-anno"
        type="text"
        inputMode="numeric"
        maxLength={4}
        pattern="[0-9]{4}"
        placeholder="Anno completo"
        value={anno}
        onChange={(event) => onAnnoChange(event.target.value.replace(/\D/g, "").slice(0, 4))}
        aria-describedby="tributi-anno-hint"
        className="w-44 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm outline-none"
      />
      <span id="tributi-anno-hint" className="text-xs font-normal text-gray-500">
        Vuoto: tutti gli anni, indipendentemente dalla tipologia.
      </span>
    </div>
  );
}

export function formatYearRange(manager: Pick<RuoloTributiYearManagerResponse, "year_from" | "year_to">): string {
  if (manager.year_from == null && manager.year_to == null) return "Tutte le annualita";
  if (manager.year_from == null) return `Fino al ${manager.year_to}`;
  if (manager.year_to == null) return `Dal ${manager.year_from}`;
  if (manager.year_from === manager.year_to) return String(manager.year_from);
  return `${manager.year_from}-${manager.year_to}`;
}

export function managerYearStart(manager: Pick<RuoloTributiYearManagerResponse, "year_from">): number {
  if (manager.year_from == null) return Number.NEGATIVE_INFINITY;
  return manager.year_from;
}
