import type { RuoloTributiYearManagerResponse } from "@/types/ruolo";

import { TributiPaymentFilters, type PaymentStatusFilterState } from "./payment-filters";

type TributiListFiltersProps = {
  managers: RuoloTributiYearManagerResponse[];
  managerKey: string;
  onManagerChange: (managerKey: string) => void;
  anno: string;
  openOnly: boolean;
  onAnnoChange: (anno: string) => void;
  onOpenOnlyChange: (openOnly: boolean) => void;
  paymentStatusFilter: PaymentStatusFilterState;
};

export function TributiListFilters({
  managers,
  managerKey,
  onManagerChange,
  anno,
  openOnly,
  onAnnoChange,
  onOpenOnlyChange,
  paymentStatusFilter,
}: TributiListFiltersProps) {
  return (
    <>
      <AnnualityManagerQuickFilters
        managers={managers}
        selectedManagerKey={managerKey}
        onSelect={(nextManagerKey) => {
          onManagerChange(nextManagerKey);
          onAnnoChange("");
        }}
      />
      <div className="mt-4 flex flex-wrap items-end gap-4">
        <AnnualityYearFilter managerKey={managerKey} anno={anno} onAnnoChange={onAnnoChange} />
        <TributiPaymentFilters openOnly={openOnly} onOpenOnlyChange={onOpenOnlyChange} paymentStatusFilter={paymentStatusFilter} />
      </div>
    </>
  );
}

function AnnualityYearFilter({ managerKey, anno, onAnnoChange }: Pick<TributiListFiltersProps, "managerKey" | "anno" | "onAnnoChange">) {
  return (
    <div className="grid gap-1 text-sm font-medium text-gray-700">
      {managerKey === "gaia" && (
        <div role="group" aria-label="Anni Consorzio/GAIA" className="mb-2 flex flex-wrap gap-2">
          {["", "2022", "2023", "2024", "2025"].map((year) => (
            <button
              key={year}
              type="button"
              aria-pressed={anno === year}
              onClick={() => onAnnoChange(year)}
              className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${getAnnualityManagerFilterClassName("gaia", anno === year)}`}
            >
              {year || "Tutti gli anni"}
            </button>
          ))}
        </div>
      )}
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
        Vuoto: tutti gli anni del periodo selezionato.
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

function getAnnualityManagerFilterClassName(managerKey: string, selected: boolean): string {
  const palettes: Record<string, { selected: string; idle: string }> = {
    agenzia_entrate: {
      selected: "border-red-700 bg-red-700 text-white shadow-sm",
      idle: "border-red-200 bg-red-50 text-red-800 hover:border-red-300 hover:bg-red-100",
    },
    step: {
      selected: "border-orange-600 bg-orange-600 text-white shadow-sm",
      idle: "border-orange-200 bg-orange-50 text-orange-800 hover:border-orange-300 hover:bg-orange-100",
    },
    gaia: {
      selected: "border-yellow-500 bg-yellow-400 text-yellow-950 shadow-sm",
      idle: "border-yellow-200 bg-yellow-50 text-yellow-900 hover:border-yellow-300 hover:bg-yellow-100",
    },
  };
  const palette = palettes[managerKey] ?? {
    selected: "border-[#1D4E35] bg-[#1D4E35] text-white shadow-sm",
    idle: "border-[#d8dfd3] bg-white text-gray-700 hover:border-[#8CB39D] hover:bg-[#f4faf6]",
  };
  return selected ? palette.selected : palette.idle;
}

function AnnualityManagerQuickFilters({
  managers,
  selectedManagerKey,
  onSelect,
}: {
  managers: RuoloTributiYearManagerResponse[];
  selectedManagerKey: string;
  onSelect: (managerKey: string) => void;
}) {
  const activeManagers = [...managers]
    .filter((manager) => manager.is_active)
    .sort((first, second) => managerYearStart(first) - managerYearStart(second));
  if (activeManagers.length === 0) {
    return (
      <div className="mt-4 rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-800">
        Regole annualita non disponibili: il filtro predefinito resta Consorzio/GAIA.
      </div>
    );
  }

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {activeManagers.map((manager) => {
        const selected = selectedManagerKey === manager.manager_key;
        return (
          <button
            key={manager.id}
            type="button"
            onClick={() => onSelect(manager.manager_key)}
            className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${getAnnualityManagerFilterClassName(manager.manager_key, selected)}`}
            aria-pressed={selected}
          >
            {formatYearRange(manager)} · {manager.manager_label}
          </button>
        );
      })}
    </div>
  );
}
