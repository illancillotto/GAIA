"use client";

import { useMemo, useState } from "react";

import { ParticellaDetailDialog } from "@/components/catasto/anagrafica/ParticellaDetailDialog";
import type { CatAnagraficaMatch } from "@/types/catasto";
import type { ParticellaGisSummary } from "@/types/gis";

interface SelectionPanelProps {
  particelle: ParticellaGisSummary[];
  truncated: boolean;
  nTotale: number;
}

export default function SelectionPanel({ particelle, truncated, nTotale }: SelectionPanelProps) {
  const [selected, setSelected] = useState<ParticellaGisSummary | null>(null);
  const match = useMemo<CatAnagraficaMatch | null>(() => {
    if (!selected) return null;
    return {
      particella_id: selected.id,
      unit_id: null,
      comune_id: null,
      comune: selected.nome_comune ?? null,
      cod_comune_capacitas: selected.cod_comune_capacitas ?? null,
      codice_catastale: selected.codice_catastale ?? null,
      foglio: selected.foglio ?? "",
      particella: selected.particella ?? "",
      subalterno: selected.subalterno ?? null,
      num_distretto: selected.num_distretto ?? null,
      nome_distretto: selected.nome_distretto ?? null,
      superficie_mq: selected.superficie_mq != null ? String(selected.superficie_mq) : null,
      superficie_grafica_mq: selected.superficie_grafica_mq != null ? String(selected.superficie_grafica_mq) : null,
      presente_in_catasto_consorzio: false,
      utenza_latest: null,
      cert_com: null,
      cert_pvc: null,
      cert_fra: null,
      cert_ccs: null,
      stato_ruolo: null,
      stato_cnc: null,
      intestatari: [],
      anomalie_count: 0,
      anomalie_top: [],
      note: null,
    };
  }, [selected]);

  if (particelle.length === 0) return null;

  return (
    <>
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
              {particella.utenza_cf || particella.utenza_denominazione ? (
                <div className="truncate text-gray-400">
                  {particella.utenza_cf ? <span className="font-mono">{particella.utenza_cf}</span> : null}
                  {particella.utenza_cf && particella.utenza_denominazione ? <span className="px-1">·</span> : null}
                  {particella.utenza_denominazione ? <span>{particella.utenza_denominazione}</span> : null}
                </div>
              ) : null}
              </div>
              <div className="ml-3 flex items-center gap-2">
                {particella.ha_anomalie ? <span className="h-2 w-2 rounded-full bg-red-400" title="Anomalie aperte" /> : null}
                <button
                  type="button"
                  onClick={() => setSelected(particella)}
                  className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
                >
                  Apri
                </button>
                <a
                  href={`/catasto/particelle/${particella.id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-medium text-gray-500 hover:text-gray-700"
                >
                  Apri in pagina
                </a>
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

      <ParticellaDetailDialog open={selected !== null} match={match} onClose={() => setSelected(null)} />
    </>
  );
}
