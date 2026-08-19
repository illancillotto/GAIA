export type DeliveryPointQuickFilter = "all" | "with_meter" | "without_meter";

type DeliveryPointQuickFilterOption = {
  id: DeliveryPointQuickFilter;
  label: string;
  dot: string;
};

type DeliveryPointThemeProps = {
  isDark: boolean;
};

const DELIVERY_POINT_QUICK_FILTERS: DeliveryPointQuickFilterOption[] = [
  { id: "all", label: "Tutti", dot: "bg-teal-400" },
  { id: "with_meter", label: "Con contatore", dot: "bg-emerald-500" },
  { id: "without_meter", label: "Senza contatore", dot: "bg-amber-500" },
];

export type DeliveryPointQuickFiltersProps = DeliveryPointThemeProps & {
  selectedFilter: DeliveryPointQuickFilter;
  onFilterChange: (filter: DeliveryPointQuickFilter) => void;
  onRefreshCache: () => void;
  cacheRefreshing: boolean;
  cacheMessage: string | null;
};

function deliveryPointSelectedClass(filter: DeliveryPointQuickFilter) {
  if (filter === "with_meter") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700 shadow-sm";
  }
  if (filter === "without_meter") {
    return "border-amber-200 bg-amber-50 text-amber-700 shadow-sm";
  }
  return "border-teal-200 bg-teal-50 text-teal-700 shadow-sm";
}

function deliveryPointUnselectedClass(isDark: boolean) {
  return isDark
    ? "border-white/10 bg-white/5 text-white/60 hover:bg-white/10"
    : "border-gray-200 bg-white text-gray-500 hover:border-teal-100 hover:text-teal-700";
}

function DeliveryPointFilterButton({
  isDark,
  option,
  selected,
  onFilterChange,
}: DeliveryPointThemeProps & {
  option: DeliveryPointQuickFilterOption;
  selected: boolean;
  onFilterChange: (filter: DeliveryPointQuickFilter) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onFilterChange(option.id)}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold transition ${
        selected ? deliveryPointSelectedClass(option.id) : deliveryPointUnselectedClass(isDark)
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${selected ? option.dot : isDark ? "bg-white/35" : "bg-gray-300"}`} />
      {option.label}
    </button>
  );
}

function DeliveryPointFilterButtons({
  isDark,
  selectedFilter,
  onFilterChange,
}: DeliveryPointThemeProps & {
  selectedFilter: DeliveryPointQuickFilter;
  onFilterChange: (filter: DeliveryPointQuickFilter) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {DELIVERY_POINT_QUICK_FILTERS.map((option) => (
        <DeliveryPointFilterButton
          key={option.id}
          isDark={isDark}
          option={option}
          selected={selectedFilter === option.id}
          onFilterChange={onFilterChange}
        />
      ))}
    </div>
  );
}

function CacheRefreshPanel({
  isDark,
  cacheRefreshing,
  cacheMessage,
  onRefreshCache,
}: DeliveryPointThemeProps & {
  cacheRefreshing: boolean;
  cacheMessage: string | null;
  onRefreshCache: () => void;
}) {
  return (
    <div className={`mt-3 rounded-xl border px-3 py-2 ${isDark ? "border-white/10 bg-white/5" : "border-teal-100 bg-teal-50/70"}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className={`text-[10px] font-semibold uppercase tracking-widest ${isDark ? "text-white/45" : "text-teal-700"}`}>
            Cache tile GIS
          </p>
          <p className={`mt-0.5 text-[11px] ${isDark ? "text-white/55" : "text-slate-500"}`}>
            Forza nuove tile per punti, canali, particelle e distretti.
          </p>
        </div>
        <button
          type="button"
          onClick={() => onRefreshCache()}
          disabled={cacheRefreshing}
          className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold transition ${
            isDark
              ? "border-white/15 bg-white/10 text-white/75 hover:bg-white/15 disabled:opacity-50"
              : "border-teal-200 bg-white text-teal-700 shadow-sm hover:bg-teal-50 disabled:opacity-50"
          }`}
        >
          {cacheRefreshing ? "Aggiorno..." : "Aggiorna cache"}
        </button>
      </div>
      {cacheMessage ? (
        <p className={`mt-2 text-[11px] font-medium ${isDark ? "text-emerald-200" : "text-emerald-700"}`}>
          {cacheMessage}
        </p>
      ) : null}
    </div>
  );
}

export default function DeliveryPointQuickFilters({
  isDark,
  selectedFilter,
  onFilterChange,
  onRefreshCache,
  cacheRefreshing,
  cacheMessage,
}: DeliveryPointQuickFiltersProps) {
  return (
    <div className={`mt-2 rounded-2xl border px-2.5 py-2 ${isDark ? "border-white/15 bg-white/5" : "border-teal-100 bg-white/70"}`}>
      <p className={`mb-2 text-[10px] font-semibold uppercase tracking-widest ${isDark ? "text-white/50" : "text-teal-600"}`}>
        Filtro punti di consegna
      </p>
      <DeliveryPointFilterButtons isDark={isDark} selectedFilter={selectedFilter} onFilterChange={onFilterChange} />
      <CacheRefreshPanel
        isDark={isDark}
        cacheRefreshing={cacheRefreshing}
        cacheMessage={cacheMessage}
        onRefreshCache={onRefreshCache}
      />
    </div>
  );
}
