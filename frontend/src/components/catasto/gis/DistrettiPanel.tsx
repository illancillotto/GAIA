import type { ReactNode } from "react";

import type { CatDistretto } from "@/types/catasto";

export type DistrettiPanelProps = {
  isDark: boolean;
  selectedDistretto: CatDistretto | null;
  distrettiOpen: boolean;
  onToggleOpen: () => void;
  distrettoColorMap: Record<string, string>;
  showParticelleFill: boolean;
  onToggleParticelleFill: () => void;
  distrettiSearch: string;
  onSearchChange: (value: string) => void;
  onClearSearch: () => void;
  distrettiLoading: boolean;
  distretti: CatDistretto[];
  filteredDistretti: CatDistretto[];
  distrettoLayer: string;
  onSelectDistretto: (distretto: CatDistretto) => void;
  onClearDistretto: () => void;
};

type DistrettiThemeProps = { isDark: boolean };

type SelectedDistrettoCardProps = DistrettiThemeProps & {
  selectedDistretto: CatDistretto;
  distrettoColorMap: Record<string, string>;
  showParticelleFill: boolean;
  onToggleParticelleFill: () => void;
  onClearDistretto: () => void;
};

type DistrettiSearchBoxProps = DistrettiThemeProps & {
  distrettiSearch: string;
  onSearchChange: (value: string) => void;
  onClearSearch: () => void;
};

type DistrettiListProps = DistrettiThemeProps & {
  distrettiLoading: boolean;
  distretti: CatDistretto[];
  filteredDistretti: CatDistretto[];
  distrettiSearch: string;
  distrettoLayer: string;
  distrettoColorMap: Record<string, string>;
  onSelectDistretto: (distretto: CatDistretto) => void;
};

type DistrettoListItemProps = DistrettiThemeProps & {
  distretto: CatDistretto;
  isSelected: boolean;
  color: string;
  onSelect: () => void;
};

type DistrettiHeaderProps = DistrettiThemeProps & {
  selectedDistretto: CatDistretto | null;
  distrettiOpen: boolean;
  onToggleOpen: () => void;
};

type DistrettiPanelBodyProps = DistrettiPanelProps & {
  selectedDistretto: CatDistretto | null;
};

const DARK_SELECTED_CARD = "border-white/15 bg-white/10";
const LIGHT_SELECTED_CARD = "border-white bg-white/80";
const DARK_MUTED_TEXT = "text-white/55";
const LIGHT_MUTED_TEXT = "text-gray-500";
const FILL_ON_CLASS = "border-indigo-200 bg-indigo-50 text-indigo-700";
const FILL_OFF_DARK_CLASS = "border-white/15 bg-white/10 text-white/70 hover:bg-white/15";
const FILL_OFF_LIGHT_CLASS = "border-gray-200 bg-white text-gray-600 hover:bg-gray-50";

function fillButtonClass(isDark: boolean, showParticelleFill: boolean): string {
  if (showParticelleFill) return FILL_ON_CLASS;
  return isDark ? FILL_OFF_DARK_CLASS : FILL_OFF_LIGHT_CLASS;
}

function distrettoRowClass(isDark: boolean, isSelected: boolean): string {
  if (isSelected) return "border-emerald-300 bg-white shadow-sm ring-1 ring-emerald-100";
  return isDark ? "border-white/10 bg-white/5 hover:bg-white/10" : "border-white/70 bg-white/70 hover:border-emerald-200 hover:bg-white";
}

function SelectedDistrettoCard({
  isDark,
  selectedDistretto,
  distrettoColorMap,
  showParticelleFill,
  onToggleParticelleFill,
  onClearDistretto,
}: SelectedDistrettoCardProps) {
  const cardClass = isDark ? DARK_SELECTED_CARD : LIGHT_SELECTED_CARD;
  const mutedText = isDark ? DARK_MUTED_TEXT : LIGHT_MUTED_TEXT;
  return (
    <div className={`mt-3 rounded-xl border px-3 py-2 ${cardClass}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="h-3 w-3 shrink-0 rounded-full ring-2 ring-white"
              style={{ backgroundColor: distrettoColorMap[selectedDistretto.num_distretto] ?? "#1D4E35" }}
            />
            <p className={`truncate text-sm font-semibold ${isDark ? "text-white" : "text-gray-900"}`}>
              Distretto {selectedDistretto.num_distretto}
            </p>
          </div>
          <p className={`mt-0.5 truncate text-[11px] ${mutedText}`}>
            {selectedDistretto.nome_distretto ?? "Senza nome"}
          </p>
        </div>
        <button
          type="button"
          onClick={onClearDistretto}
          className={`rounded-full px-2.5 py-1 text-[11px] font-semibold transition ${isDark ? "bg-white/10 text-white/70 hover:bg-white/15" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
        >
          Tutti
        </button>
      </div>
      <button
        type="button"
        onClick={onToggleParticelleFill}
        className={`mt-2 w-full rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${fillButtonClass(isDark, showParticelleFill)}`}
      >
        {showParticelleFill ? "Nascondi riempimento particelle" : "Mostra riempimento particelle"}
      </button>
    </div>
  );
}

function DistrettiSearchBox({ isDark, distrettiSearch, onSearchChange, onClearSearch }: DistrettiSearchBoxProps) {
  return (
    <div className={`flex items-center gap-2 rounded-xl border px-2.5 py-2 ${isDark ? "border-white/15 bg-white/5" : "border-white bg-white/85"}`}>
      <span className={`material-symbols-outlined text-[16px] ${isDark ? "text-white/45" : "text-emerald-600"}`}>search</span>
      <input
        id={`distretti-search-${isDark ? "dark" : "light"}`}
        type="search"
        value={distrettiSearch}
        onChange={(event) => onSearchChange(event.target.value)}
        placeholder="Cerca per numero o nome"
        className={`min-w-0 flex-1 bg-transparent text-xs outline-none placeholder:text-current/45 ${isDark ? "text-white" : "text-gray-800"}`}
      />
      {distrettiSearch ? (
        <button
          type="button"
          onClick={onClearSearch}
          className={`rounded-full p-0.5 transition ${isDark ? "text-white/45 hover:bg-white/10 hover:text-white/75" : "text-gray-400 hover:bg-gray-100 hover:text-gray-600"}`}
          aria-label="Pulisci filtro distretti"
        >
          <span className="material-symbols-outlined text-[15px]">close</span>
        </button>
      ) : null}
    </div>
  );
}

function EmptyDistrettiState({ isDark, children }: DistrettiThemeProps & { children: ReactNode }) {
  return (
    <div className={`rounded-xl border border-dashed px-3 py-4 text-center text-xs ${isDark ? "border-white/15 text-white/50" : "border-emerald-100 text-gray-500"}`}>
      {children}
    </div>
  );
}

function DistrettoListItem({ isDark, distretto, isSelected, color, onSelect }: DistrettoListItemProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`flex w-full items-center gap-2 rounded-xl border px-3 py-2 text-left transition ${distrettoRowClass(isDark, isSelected)}`}
    >
      <span className="h-3 w-3 shrink-0 rounded-full ring-2 ring-white" style={{ backgroundColor: color }} />
      <span className="min-w-0 flex-1">
        <span className={`block truncate text-xs font-semibold ${isDark ? "text-white" : "text-gray-900"}`}>
          Distretto {distretto.num_distretto}
        </span>
        <span className={`block truncate text-[10px] ${isDark ? "text-white/45" : "text-gray-500"}`}>
          {distretto.nome_distretto ?? "Senza nome"}
        </span>
      </span>
      {isSelected ? (
        <span className="material-symbols-outlined text-[16px] text-emerald-600">check_circle</span>
      ) : null}
    </button>
  );
}

function DistrettiList({
  isDark,
  distrettiLoading,
  distretti,
  filteredDistretti,
  distrettiSearch,
  distrettoLayer,
  distrettoColorMap,
  onSelectDistretto,
}: DistrettiListProps) {
  if (distrettiLoading) return <EmptyDistrettiState isDark={isDark}>Caricamento distretti...</EmptyDistrettiState>;
  if (distretti.length === 0) return <EmptyDistrettiState isDark={isDark}>Nessun distretto disponibile.</EmptyDistrettiState>;
  if (filteredDistretti.length === 0) {
    return <EmptyDistrettiState isDark={isDark}>Nessun distretto trovato per “{distrettiSearch.trim()}”.</EmptyDistrettiState>;
  }

  return filteredDistretti.map((distretto) => {
    const isSelected = distretto.num_distretto === distrettoLayer.trim();
    const color = distrettoColorMap[distretto.num_distretto] ?? "#1D4E35";
    return (
      <DistrettoListItem
        key={distretto.id}
        isDark={isDark}
        distretto={distretto}
        isSelected={isSelected}
        color={color}
        onSelect={() => onSelectDistretto(distretto)}
      />
    );
  });
}

function DistrettiHeader({ isDark, selectedDistretto, distrettiOpen, onToggleOpen }: DistrettiHeaderProps) {
  return (
    <button type="button" onClick={onToggleOpen} className="flex w-full items-center justify-between gap-3 text-left">
      <div>
        <p className={`text-[10px] font-semibold uppercase tracking-widest ${isDark ? "text-emerald-200" : "text-emerald-700"}`}>Distretti irrigui</p>
        <p className={`mt-1 text-xs ${isDark ? "text-white/60" : "text-gray-500"}`}>
          {selectedDistretto
            ? `Filtro attivo: distretto ${selectedDistretto.num_distretto}`
            : "Seleziona un distretto per centrare la mappa e isolare il perimetro."}
        </p>
      </div>
      <span className={`material-symbols-outlined text-[20px] transition ${distrettiOpen ? "rotate-180" : ""} ${isDark ? "text-white/60" : "text-emerald-700"}`}>
        expand_more
      </span>
    </button>
  );
}

function DistrettiPanelBody(props: DistrettiPanelBodyProps) {
  if (!props.distrettiOpen) return null;
  return (
    <div className="mt-3">
      <label className="sr-only" htmlFor={`distretti-search-${props.isDark ? "dark" : "light"}`}>Cerca distretto</label>
      <DistrettiSearchBox {...props} />
      <div className="mt-2 max-h-56 space-y-1.5 overflow-y-auto pr-1">
        <DistrettiList {...props} />
      </div>
    </div>
  );
}

export default function DistrettiPanel(props: DistrettiPanelProps) {
  const panelClass = props.isDark ? "border-white/15 bg-white/10" : "border-emerald-100 bg-emerald-50/30";
  return (
    <div className={`rounded-2xl border p-3 ${panelClass}`}>
      <DistrettiHeader {...props} />
      {props.selectedDistretto ? <SelectedDistrettoCard {...props} selectedDistretto={props.selectedDistretto} /> : null}
      <DistrettiPanelBody {...props} />
    </div>
  );
}
