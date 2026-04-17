"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, CalendarIcon, DocumentIcon, FolderIcon, LockIcon, SearchIcon } from "@/components/ui/icons";
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
        const sortedItems = [...r.items].sort((left, right) => right.anno_tributario - left.anno_tributario);
        setStatsAnni(sortedItems);
        if (sortedItems.length > 0) setSelectedAnno(sortedItems[0].anno_tributario);
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

  const selectedStats = useMemo(
    () => statsAnni.find((item) => item.anno_tributario === selectedAnno) ?? null,
    [statsAnni, selectedAnno],
  );

  const totalEuro = useMemo(
    () => statsAnni.reduce((sum, item) => sum + (item.totale_euro ?? 0), 0),
    [statsAnni],
  );

  const topComune = useMemo(() => {
    if (statsComuni.length === 0) {
      return null;
    }
    return [...statsComuni].sort((left, right) => (right.totale_euro ?? 0) - (left.totale_euro ?? 0))[0];
  }, [statsComuni]);

  return (
    <RuoloModulePage
      title="Statistiche Ruolo"
      description="Riepilogo importi per anno e comune."
      breadcrumb="Statistiche"
      requiredSection="ruolo.stats"
    >
      <div className="space-y-8">
        {loading ? (
          <p className="text-sm text-gray-400">Caricamento...</p>
        ) : (
          <>
            <ModuleWorkspaceHero
              badge={
                <>
                  <LockIcon className="h-3.5 w-3.5" />
                  Analytics Ruolo
                </>
              }
              title="Vista aggregata per annualità e comuni."
              description="Analizza volume avvisi, collegamenti anagrafici e distribuzione economica del ruolo consortile. Seleziona un anno per leggere subito il peso dei comuni e le eventuali aree da approfondire."
              actions={
                <>
                  <ModuleWorkspaceNoticeCard
                    title={selectedStats ? `Anno in focus: ${selectedStats.anno_tributario}` : "Nessun anno selezionato"}
                    description={
                      selectedStats
                        ? `${selectedStats.total_avvisi} avvisi e totale ${formatEuro(selectedStats.totale_euro)} nell'annualità selezionata.`
                        : "Carica dati Ruolo per abilitare l'analisi storica."
                    }
                    tone={selectedStats ? "info" : "warning"}
                  />
                  <ModuleWorkspaceNoticeCard
                    title={topComune ? `Comune leader: ${topComune.comune_nome}` : "Nessun dettaglio per comune"}
                    description={
                      topComune
                        ? `${topComune.num_avvisi} avvisi e totale ${formatEuro(topComune.totale_euro)} nell'anno selezionato.`
                        : "La distribuzione per comune apparirà quando selezioni un anno con dati disponibili."
                    }
                    tone={topComune ? "success" : "neutral"}
                  />
                </>
              }
            >
              <ModuleWorkspaceKpiRow>
                <ModuleWorkspaceKpiTile
                  label="Annualità"
                  value={statsAnni.length}
                  hint="Anni tributari disponibili"
                />
                <ModuleWorkspaceKpiTile
                  label="Anno selezionato"
                  value={selectedAnno ?? "—"}
                  hint={selectedStats ? `${selectedStats.total_avvisi} avvisi` : "Nessun dataset"}
                />
                <ModuleWorkspaceKpiTile
                  label="Totale storico"
                  value={formatEuro(totalEuro)}
                  hint="Somma di tutte le annualità"
                />
                <ModuleWorkspaceKpiTile
                  label="Comuni analizzati"
                  value={statsComuni.length}
                  hint={selectedAnno ? `Breakdown ${selectedAnno}` : "Seleziona un anno"}
                  variant={statsComuni.length > 0 ? "emerald" : "default"}
                />
              </ModuleWorkspaceKpiRow>
            </ModuleWorkspaceHero>

            <section className="grid gap-4 xl:grid-cols-[1.05fr,0.95fr]">
              <article className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
                <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
                  <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                    <CalendarIcon className="h-3.5 w-3.5" />
                    Selettore annualità
                  </p>
                  <p className="mt-3 text-lg font-semibold text-gray-900">Scegli il perimetro temporale da analizzare.</p>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                    Ogni card mostra sintesi economica e qualità del collegamento anagrafico per l&apos;anno tributario corrispondente.
                  </p>
                </div>
                <div className="p-6">
                  {statsAnni.length === 0 ? (
                    <EmptyState
                      icon={DocumentIcon}
                      title="Nessuna statistica disponibile"
                      description="Importa il primo file Ruolo per abilitare l'analisi per anno e per comune."
                    />
                  ) : (
                    <div className="grid gap-4 sm:grid-cols-2">
                      {statsAnni.map((s) => {
                        const isSelected = selectedAnno === s.anno_tributario;
                        return (
                          <button
                            key={s.anno_tributario}
                            type="button"
                            onClick={() => setSelectedAnno(s.anno_tributario)}
                            className={`rounded-2xl border p-5 text-left transition ${
                              isSelected
                                ? "border-[#8CB39D] bg-[#f3f8f5] shadow-sm"
                                : "border-[#e3e9e0] bg-[#fbfcfb] hover:border-[#c8d8cc]"
                            }`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Anno</p>
                                <p className="mt-2 text-2xl font-semibold text-gray-900">{s.anno_tributario}</p>
                              </div>
                              <span className="rounded-full border border-white bg-white px-3 py-1 text-xs font-medium text-[#1D4E35]">
                                {isSelected ? "Selezionato" : "Apri dettaglio"}
                              </span>
                            </div>
                            <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
                              <div>
                                <p className="text-gray-500">Avvisi</p>
                                <p className="mt-1 font-semibold text-gray-900">{s.total_avvisi}</p>
                              </div>
                              <div>
                                <p className="text-gray-500">Totale €</p>
                                <p className="mt-1 font-semibold text-gray-900">{formatEuro(s.totale_euro)}</p>
                              </div>
                              <div>
                                <p className="text-gray-500">Collegati</p>
                                <p className="mt-1 font-semibold text-emerald-700">{s.avvisi_collegati}</p>
                              </div>
                              <div>
                                <p className="text-gray-500">Orfani</p>
                                <p className={`mt-1 font-semibold ${s.avvisi_non_collegati > 0 ? "text-amber-700" : "text-gray-900"}`}>
                                  {s.avvisi_non_collegati}
                                </p>
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </article>

              <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
                <div>
                  <p className="inline-flex items-center gap-2 rounded-full bg-[#eef3ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                    <FolderIcon className="h-3.5 w-3.5" />
                    Sintesi anno selezionato
                  </p>
                  <p className="mt-3 text-lg font-semibold text-gray-900">Indicatori rapidi del focus corrente.</p>
                  <p className="mt-2 text-sm leading-6 text-gray-600">
                    Le mini-stat aiutano a leggere subito concentrazione economica, qualità dei link e peso dei tributi sull&apos;annualità scelta.
                  </p>
                </div>
                <div className="mt-6 grid gap-3">
                  <ModuleWorkspaceMiniStat
                    eyebrow="Avvisi anno"
                    value={selectedStats?.total_avvisi ?? "—"}
                    description={selectedStats ? `${selectedStats.anno_tributario} è l'anno attualmente selezionato.` : "Seleziona un anno per attivare il dettaglio."}
                    compact
                  />
                  <ModuleWorkspaceMiniStat
                    eyebrow="Non collegati"
                    value={selectedStats?.avvisi_non_collegati ?? "—"}
                    description={selectedStats ? `${selectedStats.avvisi_collegati} risultano già collegati all'anagrafica.` : "Il dato apparirà dopo la selezione dell'annualità."}
                    tone={selectedStats && selectedStats.avvisi_non_collegati > 0 ? "warning" : "success"}
                    compact
                  />
                  <ModuleWorkspaceMiniStat
                    eyebrow="Tributo 0648"
                    value={formatEuro(selectedStats?.totale_0648 ?? null)}
                    description="Quota manutenzione complessiva dell'anno selezionato."
                    compact
                  />
                  <ModuleWorkspaceMiniStat
                    eyebrow="Tributo 0985 + 0668"
                    value={formatEuro((selectedStats?.totale_0985 ?? 0) + (selectedStats?.totale_0668 ?? 0))}
                    description="Somma irrigazione e sistemazione idraulica del focus corrente."
                    compact
                  />
                </div>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Link
                    href={selectedAnno ? `/ruolo/avvisi?anno=${selectedAnno}` : "/ruolo/avvisi"}
                    className="rounded-xl border border-[#d6e5db] bg-white px-4 py-2 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                  >
                    Apri avvisi dell&apos;anno
                  </Link>
                </div>
              </article>
            </section>

            <section className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
              <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
                <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                  <SearchIcon className="h-3.5 w-3.5" />
                  Ripartizione per comune
                </p>
                <p className="mt-3 text-lg font-semibold text-gray-900">
                  {selectedAnno != null ? `Distribuzione economica per comune — ${selectedAnno}` : "Distribuzione economica per comune"}
                </p>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                  Leggi il peso relativo dei comuni e individua rapidamente le aree con maggior numero di avvisi o importi più elevati.
                </p>
              </div>
              <div className="p-6">
                {selectedAnno == null ? (
                  <EmptyState
                    icon={CalendarIcon}
                    title="Seleziona un anno"
                    description="La distribuzione per comune si attiva dopo aver selezionato un'annualità dal pannello superiore."
                  />
                ) : loadingComuni ? (
                  <p className="text-sm text-gray-400">Caricamento...</p>
                ) : statsComuni.length === 0 ? (
                  <EmptyState
                    icon={AlertTriangleIcon}
                    title="Nessun dato per comune"
                    description="L'anno selezionato non ha ancora una ripartizione comunale disponibile."
                  />
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {statsComuni
                      .slice()
                      .sort((left, right) => (right.totale_euro ?? 0) - (left.totale_euro ?? 0))
                      .map((c) => (
                        <div key={c.comune_nome} className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-5">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Comune</p>
                              <p className="mt-2 text-lg font-semibold text-gray-900">{c.comune_nome}</p>
                            </div>
                            <span className="rounded-full border border-white bg-white px-3 py-1 text-xs font-medium text-gray-600">
                              {c.num_avvisi} avvisi
                            </span>
                          </div>
                          <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
                            <div>
                              <dt className="text-gray-500">0648</dt>
                              <dd className="mt-1 font-semibold text-gray-900">{formatEuro(c.totale_0648)}</dd>
                            </div>
                            <div>
                              <dt className="text-gray-500">0985</dt>
                              <dd className="mt-1 font-semibold text-gray-900">{formatEuro(c.totale_0985)}</dd>
                            </div>
                            <div>
                              <dt className="text-gray-500">0668</dt>
                              <dd className="mt-1 font-semibold text-gray-900">{formatEuro(c.totale_0668)}</dd>
                            </div>
                            <div>
                              <dt className="text-gray-500">Totale €</dt>
                              <dd className="mt-1 font-semibold text-gray-900">{formatEuro(c.totale_euro)}</dd>
                            </div>
                          </dl>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </RuoloModulePage>
  );
}
