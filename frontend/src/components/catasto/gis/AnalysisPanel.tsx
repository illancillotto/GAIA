"use client";

import type { GisSelectResult } from "@/types/gis";

interface AnalysisPanelProps {
  result: GisSelectResult | null;
  isLoading: boolean;
  onExport: (format: "geojson" | "csv") => void;
}

function formatNumber(value: number, digits = 1): string {
  return value.toLocaleString("it-IT", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export default function AnalysisPanel({ result, isLoading, onExport }: AnalysisPanelProps) {
  if (isLoading) {
    return (
      <div className="space-y-3 p-4">
        <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200" />
        <div className="grid grid-cols-2 gap-2">
          <div className="h-20 animate-pulse rounded-lg bg-gray-100" />
          <div className="h-20 animate-pulse rounded-lg bg-gray-100" />
        </div>
        <div className="h-28 animate-pulse rounded-lg bg-gray-100" />
      </div>
    );
  }

  if (!result) {
    return (
      <div className="p-6 text-center text-sm text-gray-400">
        Disegna un&apos;area nel GIS per avviare l&apos;analisi spaziale.
      </div>
    );
  }

  return (
    <div className="space-y-4 overflow-y-auto p-4">
      <section>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Selezione attiva</h3>
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg bg-indigo-50 p-3">
            <div className="text-xl font-semibold text-indigo-700">{result.n_particelle.toLocaleString("it-IT")}</div>
            <div className="text-xs text-indigo-500">Particelle</div>
          </div>
          <div className="rounded-lg bg-emerald-50 p-3">
            <div className="text-xl font-semibold text-emerald-700">{formatNumber(result.superficie_ha)}</div>
            <div className="text-xs text-emerald-500">Ettari totali</div>
          </div>
        </div>
        {result.truncated ? (
          <div className="mt-2 rounded bg-amber-50 px-2 py-1 text-xs text-amber-700">
            Preview limitata a 200 particelle. I totali includono tutta l&apos;area.
          </div>
        ) : null}
      </section>

      {result.per_foglio.length > 0 ? (
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Per foglio</h3>
          <div className="overflow-hidden rounded-lg border border-gray-100 text-xs">
            <table className="w-full">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="px-2 py-1 text-left font-medium">Foglio</th>
                  <th className="px-2 py-1 text-right font-medium">N.</th>
                  <th className="px-2 py-1 text-right font-medium">Ha</th>
                </tr>
              </thead>
              <tbody>
                {result.per_foglio.slice(0, 8).map((item) => (
                  <tr key={item.foglio} className="border-t border-gray-50">
                    <td className="px-2 py-1 font-mono">{item.foglio}</td>
                    <td className="px-2 py-1 text-right">{item.n_particelle.toLocaleString("it-IT")}</td>
                    <td className="px-2 py-1 text-right">{formatNumber(item.superficie_ha)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {result.per_foglio.length > 8 ? (
            <p className="mt-1 text-center text-xs text-gray-400">Altri {result.per_foglio.length - 8} fogli non mostrati.</p>
          ) : null}
        </section>
      ) : null}

      {result.per_distretto.length > 0 ? (
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Per distretto</h3>
          <div className="space-y-1 text-xs">
            {result.per_distretto.map((item) => (
              <div key={item.num_distretto} className="flex items-center justify-between rounded bg-gray-50 px-2 py-1.5">
                <span>
                  <span className="font-mono font-medium">{item.num_distretto}</span>
                  {item.nome_distretto ? <span className="ml-1 text-gray-400">{item.nome_distretto}</span> : null}
                </span>
                <span className="text-gray-600">
                  {item.n_particelle.toLocaleString("it-IT")} part. - {formatNumber(item.superficie_ha)} ha
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="border-t border-gray-100 pt-3">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Esporta selezione</h3>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onExport("csv")}
            className="flex-1 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
          >
            CSV
          </button>
          <button
            type="button"
            onClick={() => onExport("geojson")}
            className="flex-1 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
          >
            GeoJSON
          </button>
        </div>
      </section>
    </div>
  );
}
