"use client";

interface DrawingToolsProps {
  onDrawPolygon: () => void;
  onClearDrawing: () => void;
  isLoading: boolean;
  hasSelection: boolean;
  nParticelle?: number;
  orientation?: "horizontal" | "vertical";
}

export default function DrawingTools({
  onDrawPolygon,
  onClearDrawing,
  isLoading,
  hasSelection,
  nParticelle,
  orientation = "horizontal",
}: DrawingToolsProps) {
  const isVertical = orientation === "vertical";
  
  const content = (
    <>
      <button
        type="button"
        onClick={onDrawPolygon}
        className={`group relative flex items-center justify-center gap-2 overflow-hidden rounded-xl border border-indigo-200 bg-white px-4 py-2 text-sm font-semibold text-indigo-700 shadow-sm transition-all hover:border-indigo-300 hover:bg-indigo-50 hover:shadow active:scale-[0.98] ${isVertical ? "w-full" : ""}`}
      >
        <svg className="h-4 w-4 text-indigo-500 transition-transform group-hover:scale-110" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.042 21.672L13.684 16.6m0 0l-2.51 2.225.569-9.47 5.227 7.917-3.286-.672zm-7.518-.267A8.25 8.25 0 1120.25 10.5M8.288 14.212A5.25 5.25 0 1117.25 10.5" />
        </svg>
        Disegna area
      </button>

      {hasSelection ? (
        <button
          type="button"
          onClick={onClearDrawing}
          className={`group flex items-center justify-center gap-2 rounded-xl border border-rose-200 bg-white px-4 py-2 text-sm font-semibold text-rose-700 shadow-sm transition-all hover:border-rose-300 hover:bg-rose-50 hover:shadow active:scale-[0.98] ${isVertical ? "w-full" : ""}`}
        >
          <svg className="h-4 w-4 text-rose-500 transition-transform group-hover:rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          Cancella selezione
        </button>
      ) : null}

      <div className={`flex items-center gap-2 px-1 text-sm ${isVertical ? "w-full justify-center pt-1" : ""}`}>
        {isLoading ? (
          <div className="flex items-center gap-2 text-indigo-600">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span className="font-medium">Analisi in corso...</span>
          </div>
        ) : hasSelection && nParticelle != null ? (
          <span className="flex items-center gap-1.5 font-medium text-emerald-600">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            </span>
            {nParticelle.toLocaleString("it-IT")} particelle selezionate
          </span>
        ) : (
          <span className="text-gray-400">Disegna un&apos;area nel GIS</span>
        )}
      </div>
    </>
  );

  if (isVertical) {
    return <div className="flex flex-col items-stretch gap-3">{content}</div>;
  }

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-gray-200 bg-white p-2 shadow-sm">
      {content}
    </div>
  );
}
