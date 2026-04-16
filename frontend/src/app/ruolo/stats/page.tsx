"use client";

import { useEffect, useState } from "react";

import { RuoloModulePage } from "@/components/ruolo/module-page";
import { getStoredAccessToken } from "@/lib/auth";
import { getRuoloStats, getRuoloStatsComuni } from "@/lib/ruolo-api";
import type { RuoloStatsByAnnoResponse, RuoloStatsComuneItem } from "@/types/ruolo";

function formatEuro(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

export default function RuoloStatsPage() {
  const [token, setToken] = useState<string | null>(null);
  const [statsAnni, setStatsAnni] = useState<RuoloStatsByAnnoResponse[]>([]);
  const [selectedAnno, setSelectedAnno] = useState<number | null>(null);
  const [statsComuni, setStatsComuni] = useState<RuoloStatsComuneItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingComuni, setLoadingComuni] = useState(false);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    getRuoloStats(token)
      .then((r) => {
        setStatsAnni(r.items);
        if (r.items.length > 0) setSelectedAnno(r.items[0].anno_tributario);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    if (!token || selectedAnno == null) return;
    setLoadingComuni(true);
    getRuoloStatsComuni(token, selectedAnno)
      .then((r) => setStatsComuni(r.items))
      .catch(console.error)
      .finally(() => setLoadingComuni(false));
  }, [token, selectedAnno]);

  return (
    <RuoloModulePage
      title="Statistiche Ruolo"
      description="Riepilogo importi per anno e comune."
      breadcrumb="Statistiche"
      requiredSection="ruolo.stats"
    >
      <div className="space-y-8">
        <div>
          <h2 className="mb-1 text-xl font-semibold text-gray-800">Statistiche Ruolo</h2>
          <p className="text-sm text-gray-500">Aggregati per anno tributario e comune.</p>
        </div>

        {loading ? (
          <p className="text-sm text-gray-400">Caricamento...</p>
        ) : (
          <>
            {/* Per-anno summary */}
            <div>
              <h3 className="mb-3 text-sm font-medium uppercase tracking-wider text-gray-400">Per anno</h3>
              {statsAnni.length === 0 ? (
                <p className="text-sm text-gray-400">Nessun dato disponibile.</p>
              ) : (
                <div className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                        <th className="px-4 py-3">Anno</th>
                        <th className="px-4 py-3">Avvisi</th>
                        <th className="px-4 py-3">Collegati</th>
                        <th className="px-4 py-3">Orfani</th>
                        <th className="px-4 py-3 text-right">Tot. 0648</th>
                        <th className="px-4 py-3 text-right">Tot. 0985</th>
                        <th className="px-4 py-3 text-right">Tot. 0668</th>
                        <th className="px-4 py-3 text-right">Totale €</th>
                        <th className="px-4 py-3" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {statsAnni.map((s) => (
                        <tr
                          key={s.anno_tributario}
                          className={`cursor-pointer hover:bg-gray-50 ${selectedAnno === s.anno_tributario ? "bg-[#EAF3E8]" : ""}`}
                          onClick={() => setSelectedAnno(s.anno_tributario)}
                        >
                          <td className="px-4 py-3 font-medium text-gray-800">{s.anno_tributario}</td>
                          <td className="px-4 py-3 text-gray-700">{s.total_avvisi}</td>
                          <td className="px-4 py-3 text-green-700">{s.avvisi_collegati}</td>
                          <td className={`px-4 py-3 ${s.avvisi_non_collegati > 0 ? "text-orange-600" : "text-gray-400"}`}>
                            {s.avvisi_non_collegati}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-700">{formatEuro(s.totale_0648)}</td>
                          <td className="px-4 py-3 text-right text-gray-700">{formatEuro(s.totale_0985)}</td>
                          <td className="px-4 py-3 text-right text-gray-700">{formatEuro(s.totale_0668)}</td>
                          <td className="px-4 py-3 text-right font-semibold text-gray-800">{formatEuro(s.totale_euro)}</td>
                          <td className="px-4 py-3 text-xs text-[#1D4E35]">
                            {selectedAnno === s.anno_tributario ? "▲ selezionato" : "Seleziona →"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Per-comune breakdown */}
            {selectedAnno != null && (
              <div>
                <h3 className="mb-3 text-sm font-medium uppercase tracking-wider text-gray-400">
                  Per comune — anno {selectedAnno}
                </h3>
                {loadingComuni ? (
                  <p className="text-sm text-gray-400">Caricamento...</p>
                ) : statsComuni.length === 0 ? (
                  <p className="text-sm text-gray-400">Nessun dato per questo anno.</p>
                ) : (
                  <div className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-100 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                          <th className="px-4 py-3">Comune</th>
                          <th className="px-4 py-3">Avvisi</th>
                          <th className="px-4 py-3 text-right">Manut. 0648</th>
                          <th className="px-4 py-3 text-right">Irrig. 0985</th>
                          <th className="px-4 py-3 text-right">Sist. 0668</th>
                          <th className="px-4 py-3 text-right">Totale €</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {statsComuni.map((c) => (
                          <tr key={c.comune_nome} className="hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium text-gray-800">{c.comune_nome}</td>
                            <td className="px-4 py-3 text-gray-600">{c.num_avvisi}</td>
                            <td className="px-4 py-3 text-right text-gray-700">{formatEuro(c.totale_0648)}</td>
                            <td className="px-4 py-3 text-right text-gray-700">{formatEuro(c.totale_0985)}</td>
                            <td className="px-4 py-3 text-right text-gray-700">{formatEuro(c.totale_0668)}</td>
                            <td className="px-4 py-3 text-right font-semibold text-gray-800">{formatEuro(c.totale_euro)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </RuoloModulePage>
  );
}
