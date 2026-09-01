import type { Dispatch, SetStateAction } from "react";

import type { GisMapOverlayLayer, GisSavedSelectionSummary } from "@/types/gis";

type ArchiveListProps = {
  isDark: boolean;
  savedSelections: GisSavedSelectionSummary[];
  loadedSavedSelectionIds: Set<string>;
  loadedSavedSelectionLayerMap: Map<string, GisMapOverlayLayer>;
  savedSelectionFills: Record<string, boolean>;
  savedSelectionOpacities: Record<string, number>;
  savedBusy: boolean;
  onRefresh: () => void | Promise<void>;
  onDraftColorChange: Dispatch<SetStateAction<GisSavedSelectionSummary[]>>;
  onCommitColor: (selectionId: string, color: string) => void | Promise<void>;
  onDelete: (selectionId: string) => void | Promise<void>;
  onFillChange: (selectionId: string, showFill: boolean) => void | Promise<void>;
  onOpacityChange: (selectionId: string, opacity: number) => void | Promise<void>;
  onLoad: (selectionId: string) => void | Promise<void>;
  onRemoveLoaded: (selectionId: string) => void | Promise<void>;
};

type ArchiveSelectionCardProps = {
  selection: GisSavedSelectionSummary;
  loaded: boolean;
  loadedLayer: GisMapOverlayLayer | undefined;
  draftShowFill: boolean | undefined;
  draftOpacity: number | undefined;
  savedBusy: boolean;
  onDraftColorChange: Dispatch<SetStateAction<GisSavedSelectionSummary[]>>;
  onCommitColor: (selectionId: string, color: string) => void | Promise<void>;
  onDelete: (selectionId: string) => void | Promise<void>;
  onFillChange: (selectionId: string, showFill: boolean) => void | Promise<void>;
  onOpacityChange: (selectionId: string, opacity: number) => void | Promise<void>;
  onLoad: (selectionId: string) => void | Promise<void>;
  onRemoveLoaded: (selectionId: string) => void | Promise<void>;
};

function ArchiveHeader({ isDark, savedBusy, onRefresh }: Pick<ArchiveListProps, "isDark" | "savedBusy" | "onRefresh">) {
  return (
    <div className="mb-2 flex items-center justify-between">
      <p className={`text-[10px] font-semibold uppercase tracking-widest ${isDark ? "text-white/50" : "text-gray-400"}`}>Archivio layer salvati</p>
      <button
        type="button"
        onClick={onRefresh}
        disabled={savedBusy}
        className={`text-[11px] font-medium ${isDark ? "text-indigo-300 hover:text-indigo-200" : "text-indigo-600 hover:text-indigo-800"} disabled:opacity-50`}
      >
        Aggiorna
      </button>
    </div>
  );
}

function ArchiveEmptyState({ isDark }: Pick<ArchiveListProps, "isDark">) {
  return (
    <div className={`rounded-xl border border-dashed px-3 py-4 text-center text-xs ${isDark ? "border-white/20 bg-white/5 text-white/50" : "border-gray-200 bg-gray-50 text-gray-400"}`}>
      Nessuna selezione salvata.
    </div>
  );
}

function SelectionSummary({
  selection,
  onDraftColorChange,
  onCommitColor,
}: Pick<ArchiveSelectionCardProps, "selection" | "onDraftColorChange" | "onCommitColor">) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={selection.color}
          onChange={(e) => onDraftColorChange((ss) => ss.map((s) => s.id === selection.id ? { ...s, color: e.target.value } : s))}
          onBlur={(e) => onCommitColor(selection.id, e.target.value.toUpperCase())}
          className="h-5 w-5 cursor-pointer rounded-full border-0 bg-transparent p-0"
          title="Modifica colore"
        />
        <p className="truncate text-sm font-semibold text-gray-800">{selection.name}</p>
      </div>
      <p className="mt-0.5 text-[11px] text-gray-400">
        {selection.n_particelle.toLocaleString("it-IT")} particelle · {selection.n_with_geometry.toLocaleString("it-IT")} in mappa
      </p>
    </div>
  );
}

function FillButton({
  selectionId,
  showFill,
  onFillChange,
}: {
  selectionId: string;
  showFill: boolean;
  onFillChange: (selectionId: string, showFill: boolean) => void | Promise<void>;
}) {
  return (
    <button
      type="button"
      onClick={() => onFillChange(selectionId, !showFill)}
      className={`mb-2 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium transition-all ${
        showFill
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : "border-gray-200 bg-white text-gray-500 hover:border-emerald-100 hover:text-emerald-700"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full transition-colors ${showFill ? "bg-emerald-400" : "bg-gray-300"}`} />
      Riempimento
    </button>
  );
}

function OpacitySlider({
  selectionId,
  opacity,
  onOpacityChange,
}: {
  selectionId: string;
  opacity: number;
  onOpacityChange: (selectionId: string, opacity: number) => void | Promise<void>;
}) {
  const opacityPercent = Math.round(opacity * 100);
  return (
    <>
      <div className="mb-1 flex items-center justify-between text-[11px]">
        <span className="font-medium text-gray-600">Opacità</span>
        <span className="font-semibold text-gray-700">{opacityPercent}%</span>
      </div>
      <input
        type="range"
        min="5"
        max="100"
        step="5"
        value={opacityPercent}
        onChange={(e) => onOpacityChange(selectionId, Number(e.target.value) / 100)}
        className="w-full accent-emerald-600"
      />
    </>
  );
}

function ArchiveDisplayControls({
  selection,
  showFill,
  opacity,
  onFillChange,
  onOpacityChange,
}: Pick<ArchiveSelectionCardProps, "selection" | "onFillChange" | "onOpacityChange"> & { showFill: boolean; opacity: number }) {
  return (
    <div className="mt-2 rounded-lg border border-gray-100 bg-gray-50/70 px-2.5 py-2">
      <FillButton selectionId={selection.id} showFill={showFill} onFillChange={onFillChange} />
      <OpacitySlider selectionId={selection.id} opacity={opacity} onOpacityChange={onOpacityChange} />
    </div>
  );
}

function ArchiveActions({
  selectionId,
  loaded,
  savedBusy,
  onLoad,
  onRemoveLoaded,
}: {
  selectionId: string;
  loaded: boolean;
  savedBusy: boolean;
  onLoad: (selectionId: string) => void | Promise<void>;
  onRemoveLoaded: (selectionId: string) => void | Promise<void>;
}) {
  return (
    <div className="mt-2 grid grid-cols-2 gap-2">
      <button
        type="button"
        onClick={() => onLoad(selectionId)}
        disabled={savedBusy}
        className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-indigo-50 hover:text-indigo-700 disabled:text-gray-300"
      >
        {loaded ? "Porta in primo piano" : "Aggiungi in mappa"}
      </button>
      <button
        type="button"
        onClick={() => onRemoveLoaded(selectionId)}
        disabled={!loaded}
        className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 disabled:text-gray-300"
      >
        Rimuovi
      </button>
    </div>
  );
}

function ArchiveSelectionCard({
  selection,
  loaded,
  loadedLayer,
  draftShowFill,
  draftOpacity,
  savedBusy,
  onDraftColorChange,
  onCommitColor,
  onDelete,
  onFillChange,
  onOpacityChange,
  onLoad,
  onRemoveLoaded,
}: ArchiveSelectionCardProps) {
  const showFill = loadedLayer?.showFill ?? draftShowFill ?? true;
  const opacity = loadedLayer?.opacity ?? draftOpacity ?? 0.55;

  return (
    <div className={`rounded-xl border bg-white p-2 shadow-sm ${loaded ? "border-emerald-200 ring-1 ring-emerald-100" : "border-gray-100"}`}>
      <div className="flex items-start justify-between gap-2">
        <SelectionSummary selection={selection} onDraftColorChange={onDraftColorChange} onCommitColor={onCommitColor} />
        <button
          type="button"
          onClick={() => onDelete(selection.id)}
          disabled={savedBusy}
          className="text-[11px] font-medium text-gray-400 hover:text-red-600 disabled:text-gray-300"
        >
          Elimina
        </button>
      </div>
      <ArchiveDisplayControls selection={selection} showFill={showFill} opacity={opacity} onFillChange={onFillChange} onOpacityChange={onOpacityChange} />
      <ArchiveActions selectionId={selection.id} loaded={loaded} savedBusy={savedBusy} onLoad={onLoad} onRemoveLoaded={onRemoveLoaded} />
    </div>
  );
}

export default function ArchiveList(props: ArchiveListProps) {
  return (
    <>
      <ArchiveHeader isDark={props.isDark} savedBusy={props.savedBusy} onRefresh={props.onRefresh} />
      <div className="max-h-44 space-y-2 overflow-y-auto pr-1">
        {props.savedSelections.length === 0 ? (
          <ArchiveEmptyState isDark={props.isDark} />
        ) : (
          props.savedSelections.map((selection) => (
            <ArchiveSelectionCard
              key={selection.id}
              selection={selection}
              loaded={props.loadedSavedSelectionIds.has(selection.id)}
              loadedLayer={props.loadedSavedSelectionLayerMap.get(selection.id)}
              draftShowFill={props.savedSelectionFills[selection.id]}
              draftOpacity={props.savedSelectionOpacities[selection.id]}
              savedBusy={props.savedBusy}
              onDraftColorChange={props.onDraftColorChange}
              onCommitColor={props.onCommitColor}
              onDelete={props.onDelete}
              onFillChange={props.onFillChange}
              onOpacityChange={props.onOpacityChange}
              onLoad={props.onLoad}
              onRemoveLoaded={props.onRemoveLoaded}
            />
          ))
        )}
      </div>
    </>
  );
}
