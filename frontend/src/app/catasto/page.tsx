"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { KpiCard } from "@/components/catasto/KpiCard";
import { AlertBanner } from "@/components/ui/alert-banner";
import { RefreshIcon } from "@/components/ui/icons";
import {
  catastoGetImportHistory,
  catastoListAnomalie,
  catastoListDistretti,
  catastoGetDistrettoKpi,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatDistretto, CatDistrettoKpi } from "@/types/catasto";

function formatEuro(value: string | number): string {
  const amount = typeof value === "number" ? value : Number(value);
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(Number.isFinite(amount) ? amount : 0);
}

function formatHaFromMq(value: string | number): string {
  const mq = typeof value === "number" ? value : Number(value);
  const ha = (Number.isFinite(mq) ? mq : 0) / 10_000;
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(ha);
}

function currentYear(): number {
  return new Date().getFullYear();
}

export default function CatastoDashboardPage() {
  const [anno, setAnno] = useState<number>(currentYear());
  const [distretti, setDistretti] = useState<CatDistretto[]>([]);
  const [kpiByDistrettoId, setKpiByDistrettoId] = useState<Record<string, CatDistrettoKpi>>({});
  const [lastImportAt, setLastImportAt] = useState<string | null>(null);
  const [openErrorAnomalie, setOpenErrorAnomalie] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function load(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;

      setIsLoading(true);
      try {
        const [distrettiList, importHistory, anomalies] = await Promise.all([
          catastoListDistretti(token),
          catastoGetImportHistory(token),
          catastoListAnomalie(token, { severita: "error", status: "aperta", page: 1, pageSize: 1 }),
        ]);

        setDistretti(distrettiList);
        setOpenErrorAnomalie(anomalies.total);
        const mostRecent = importHistory.find((b) => b.status === "completed") ?? importHistory[0];
        setLastImportAt(mostRecent?.completed_at ?? mostRecent?.created_at ?? null);

        const kpis = await Promise.all(
          distrettiList.map(async (d) => {
            const kpi = await catastoGetDistrettoKpi(token, d.id, anno);
            return [d.id, kpi] as const;
          }),
        );
        setKpiByDistrettoId(Object.fromEntries(kpis));
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore caricamento Catasto");
      } finally {
        setIsLoading(false);
      }
    }

    void load();
  }, [anno]);

  const distrettiAttivi = useMemo(() => distretti.filter((d) => d.attivo).length, [distretti]);
  const totaleParticelle = useMemo(
    () => Object.values(kpiByDistrettoId).reduce((acc, kpi) => acc + (kpi.totale_particelle ?? 0), 0),
    [kpiByDistrettoId],
  );

  return (
    <CatastoPage
      title="GAIA Catasto"
      description="Dashboard Catasto Fase 1: distretti, particelle, anomalie e import Capacitas."
      breadcrumb="Catasto / Dashboard"
      requiredModule="catasto"
    >
      <div className="page-stack">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm text-gray-500">Anno campagna</p>
            <select
              className="form-control mt-1 w-[160px]"
              value={String(anno)}
              onChange={(event) => setAnno(Number(event.target.value))}
            >
              {[currentYear() + 1, currentYear(), currentYear() - 1, currentYear() - 2].map((y) => (
                <option key={y} value={String(y)}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link className="btn-secondary" href="/catasto/anomalie">
              Vedi anomalie
            </Link>
            <Link className="btn-primary" href="/catasto/import">
              <RefreshIcon className="h-4 w-4" />
              Import Capacitas
            </Link>
          </div>
        </div>

        {loadError ? (
          <AlertBanner variant="danger" title="Errore caricamento">
            {loadError}
          </AlertBanner>
        ) : null}

        <div className="grid gap-3 md:grid-cols-4">
          <KpiCard label="Particelle (stima)" value={isLoading ? "—" : totaleParticelle} sub={`Somma KPI distretti · anno ${anno}`} />
          <KpiCard label="Distretti attivi" value={isLoading ? "—" : distrettiAttivi} sub="Anagrafica distretti" />
          <KpiCard
            label="Anomalie error aperte"
            value={isLoading ? "—" : openErrorAnomalie}
            sub="Severità=error · status=aperta"
            variant={openErrorAnomalie > 0 ? "danger" : "success"}
          />
          <KpiCard label="Ultimo import" value={lastImportAt ? new Date(lastImportAt).toLocaleDateString("it-IT") : "—"} sub="Da storico import" />
        </div>

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Distretti</p>
              <p className="mt-1 text-sm text-gray-500">KPI aggregati (superficie in ha, importi in €).</p>
            </div>
            <Link className="text-sm font-medium text-[#1D4E35] underline underline-offset-2" href="/catasto/distretti">
              Apri lista completa
            </Link>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {isLoading && distretti.length === 0 ? (
              <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento distretti…</div>
            ) : (
              distretti.slice(0, 9).map((d) => {
                const kpi = kpiByDistrettoId[d.id];
                return (
                  <Link
                    key={d.id}
                    href={`/catasto/distretti/${d.id}`}
                    className="rounded-2xl border border-gray-100 bg-white p-4 transition hover:border-[#c8d8ce] hover:shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-gray-900">
                          Distretto {d.num_distretto}
                        </p>
                        <p className="mt-1 line-clamp-2 text-xs text-gray-500">{d.nome_distretto ?? "—"}</p>
                      </div>
                      <span className={`rounded-full px-2 py-1 text-xs font-medium ${d.attivo ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>
                        {d.attivo ? "Attivo" : "Inattivo"}
                      </span>
                    </div>

                    {kpi ? (
                      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-600">
                        <div>
                          <p className="text-[10px] uppercase tracking-wide text-gray-400">Sup. irrigabile</p>
                          <p className="mt-0.5 font-medium text-gray-800">{formatHaFromMq(kpi.superficie_irrigabile_mq)} ha</p>
                        </div>
                        <div>
                          <p className="text-[10px] uppercase tracking-wide text-gray-400">Anomalie</p>
                          <p className="mt-0.5 font-medium text-gray-800">
                            {kpi.totale_anomalie}{" "}
                            <span className="text-red-700">({kpi.anomalie_error} err)</span>
                          </p>
                        </div>
                        <div>
                          <p className="text-[10px] uppercase tracking-wide text-gray-400">Importo 0648</p>
                          <p className="mt-0.5 font-medium text-gray-800">{formatEuro(kpi.importo_totale_0648)}</p>
                        </div>
                        <div>
                          <p className="text-[10px] uppercase tracking-wide text-gray-400">Importo 0985</p>
                          <p className="mt-0.5 font-medium text-gray-800">{formatEuro(kpi.importo_totale_0985)}</p>
                        </div>
                      </div>
                    ) : (
                      <p className="mt-3 text-xs text-gray-400">KPI non disponibili.</p>
                    )}
                  </Link>
                );
              })
            )}
          </div>
        </article>
      </div>
    </CatastoPage>
  );
}
