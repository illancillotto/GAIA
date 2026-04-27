"use client";

import Link from "next/link";

import type { ParticellaGisSummary } from "@/types/gis";

interface SelectionPanelProps {
  particelle: ParticellaGisSummary[];
  truncated: boolean;
  nTotale: number;
}

export default function SelectionPanel({ particelle, truncated, nTotale }: SelectionPanelProps) {
  if (particelle.length === 0) return null;

  return (
    <div className="max-h-72 overflow-y-auto border-t border-gray-100">
      <div className="flex justify-between bg-gray-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        <span>Particelle</span>
        <span>
          {particelle.length.toLocaleString("it-IT")} / {nTotale.toLocaleString("it-IT")}
        </span>
      </div>
      <div className="divide-y divide-gray-50">
        {particelle.map((particella) => (
          <div key={particella.id} className="flex items-center justify-between px-4 py-2 hover:bg-gray-50">
            <div className="min-w-0 text-xs">
              <div className="truncate font-mono font-medium text-gray-800">
                {particella.cfm || `${particella.codice_catastale ?? ""}-${particella.foglio}/${particella.particella}`}
              </div>
              <div className="truncate text-gray-400">
                {(particella.superficie_mq ?? particella.superficie_grafica_mq)?.toLocaleString("it-IT") ?? "-"} mq -{" "}
                {particella.num_distretto || "-"}
              </div>
            </div>
            <div className="ml-3 flex items-center gap-2">
              {particella.ha_anomalie ? <span className="h-2 w-2 rounded-full bg-red-400" title="Anomalie aperte" /> : null}
              <Link href={`/catasto/particelle/${particella.id}`} className="text-xs font-medium text-indigo-600 hover:text-indigo-800">
                Apri
              </Link>
            </div>
          </div>
        ))}
      </div>
      {truncated ? (
        <div className="bg-amber-50 px-4 py-2 text-center text-xs text-amber-700">
          Preview limitata a 200 risultati. Usa l&apos;export per scaricare la lista completa.
        </div>
      ) : null}
    </div>
  );
}
