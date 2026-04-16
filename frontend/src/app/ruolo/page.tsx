"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { RuoloModulePage } from "@/components/ruolo/module-page";
import { getStoredAccessToken } from "@/lib/auth";
import { getRuoloStats, listImportJobs } from "@/lib/ruolo-api";
import type { RuoloStatsByAnnoResponse, RuoloImportJobResponse } from "@/types/ruolo";

function formatEuro(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    running: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-700"}`}>
      {status}
    </span>
  );
}

export default function RuoloDashboardPage() {
  const [token, setToken] = useState<string | null>(null);
  const [stats, setStats] = useState<RuoloStatsByAnnoResponse[]>([]);
  const [recentJobs, setRecentJobs] = useState<RuoloImportJobResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    Promise.all([
      getRuoloStats(token),
      listImportJobs(token, undefined, 1, 5),
    ])
      .then(([statsData, jobsData]) => {
        setStats(statsData.items);
        setRecentJobs(jobsData.items);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <RuoloModulePage
      title="GAIA Ruolo"
      description="Dashboard del modulo ruolo consortile."
      requiredSection="ruolo.dashboard"
    >
      <div className="space-y-8">
        <div>
          <h2 className="mb-1 text-xl font-semibold text-gray-800">Dashboard Ruolo</h2>
          <p className="text-sm text-gray-500">
            Panoramica degli avvisi consortili per anno tributario.
          </p>
        </div>

        {loading ? (
          <p className="text-sm text-gray-400">Caricamento...</p>
        ) : (
          <>
            {/* Stats by year */}
            <div>
              <h3 className="mb-3 text-sm font-medium uppercase tracking-wider text-gray-400">Riepilogo per anno</h3>
              {stats.length === 0 ? (
                <div className="rounded-xl border border-dashed border-gray-200 p-8 text-center">
                  <p className="text-sm text-gray-400">Nessun dato importato.</p>
                  <Link href="/ruolo/import" className="mt-2 inline-block text-sm font-medium text-[#1D4E35] hover:underline">
                    Importa il primo file Ruolo →
                  </Link>
                </div>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {stats.map((s) => (
                    <div key={s.anno_tributario} className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
                      <div className="mb-3 flex items-center justify-between">
                        <span className="text-lg font-bold text-gray-800">{s.anno_tributario}</span>
                        <Link
                          href={`/ruolo/avvisi?anno=${s.anno_tributario}`}
                          className="text-xs text-[#1D4E35] hover:underline"
                        >
                          Vedi avvisi →
                        </Link>
                      </div>
                      <dl className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <dt className="text-gray-400">Avvisi totali</dt>
                          <dd className="font-semibold text-gray-800">{s.total_avvisi}</dd>
                        </div>
                        <div>
                          <dt className="text-gray-400">Collegati</dt>
                          <dd className="font-semibold text-green-700">{s.avvisi_collegati}</dd>
                        </div>
                        <div>
                          <dt className="text-gray-400">Non collegati</dt>
                          <dd className={`font-semibold ${s.avvisi_non_collegati > 0 ? "text-orange-600" : "text-gray-800"}`}>
                            {s.avvisi_non_collegati}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-gray-400">Totale (€)</dt>
                          <dd className="font-semibold text-gray-800">{formatEuro(s.totale_euro)}</dd>
                        </div>
                      </dl>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Quick actions */}
            <div className="grid gap-4 sm:grid-cols-3">
              <Link
                href="/ruolo/avvisi"
                className="flex flex-col gap-1 rounded-xl border border-gray-100 bg-white p-5 shadow-sm transition hover:border-[#8CB39D] hover:shadow"
              >
                <span className="text-sm font-semibold text-gray-800">Avvisi</span>
                <span className="text-xs text-gray-400">Sfoglia e filtra gli avvisi consortili</span>
              </Link>
              <Link
                href="/ruolo/stats"
                className="flex flex-col gap-1 rounded-xl border border-gray-100 bg-white p-5 shadow-sm transition hover:border-[#8CB39D] hover:shadow"
              >
                <span className="text-sm font-semibold text-gray-800">Statistiche</span>
                <span className="text-xs text-gray-400">Ripartizione per comune e anno</span>
              </Link>
              <Link
                href="/ruolo/import"
                className="flex flex-col gap-1 rounded-xl border border-gray-100 bg-white p-5 shadow-sm transition hover:border-[#8CB39D] hover:shadow"
              >
                <span className="text-sm font-semibold text-gray-800">Import</span>
                <span className="text-xs text-gray-400">Carica un nuovo file Ruolo (.dmp / PDF)</span>
              </Link>
            </div>

            {/* Recent jobs */}
            {recentJobs.length > 0 && (
              <div>
                <h3 className="mb-3 text-sm font-medium uppercase tracking-wider text-gray-400">Import recenti</h3>
                <div className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                        <th className="px-4 py-3">Anno</th>
                        <th className="px-4 py-3">File</th>
                        <th className="px-4 py-3">Stato</th>
                        <th className="px-4 py-3">Importati</th>
                        <th className="px-4 py-3">Avviato</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {recentJobs.map((job) => (
                        <tr key={job.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-800">{job.anno_tributario}</td>
                          <td className="max-w-[180px] truncate px-4 py-3 text-gray-500">{job.filename ?? "—"}</td>
                          <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
                          <td className="px-4 py-3 text-gray-700">{job.records_imported ?? "—"}</td>
                          <td className="px-4 py-3 text-gray-400">
                            {new Date(job.started_at).toLocaleDateString("it-IT")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </RuoloModulePage>
  );
}
