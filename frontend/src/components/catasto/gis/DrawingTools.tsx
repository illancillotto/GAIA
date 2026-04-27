"use client";

interface DrawingToolsProps {
  onDrawPolygon: () => void;
  onClearDrawing: () => void;
  isLoading: boolean;
  hasSelection: boolean;
  nParticelle?: number;
}

export default function DrawingTools({
  onDrawPolygon,
  onClearDrawing,
  isLoading,
  hasSelection,
  nParticelle,
}: DrawingToolsProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-gray-200 bg-white p-2 shadow-sm">
      <button
        type="button"
        onClick={onDrawPolygon}
        className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-sm font-medium text-indigo-700 transition-colors hover:bg-indigo-100"
      >
        Disegna area
      </button>

      {hasSelection ? (
        <button
          type="button"
          onClick={onClearDrawing}
          className="rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-100"
        >
          Cancella selezione
        </button>
      ) : null}

      <div className="px-1 text-sm text-gray-600">
        {isLoading ? (
          <span>Analisi in corso...</span>
        ) : hasSelection && nParticelle != null ? (
          <span className="font-medium text-indigo-700">
            {nParticelle.toLocaleString("it-IT")} particelle selezionate
          </span>
        ) : (
          <span className="text-gray-400">Disegna un&apos;area nel GIS</span>
        )}
      </div>
    </div>
  );
}
