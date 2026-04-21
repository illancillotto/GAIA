"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { ColumnDef } from "@tanstack/react-table";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { DataTable } from "@/components/table/data-table";
import { AlertBanner } from "@/components/ui/alert-banner";
import { MetricCard } from "@/components/ui/metric-card";
import { catastoGetDistrettoKpi, catastoGetImportHistory, catastoListDistretti } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatDistretto, CatDistrettoKpi, CatImportBatch } from "@/types/catasto";

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

function getLatestImportedAnno(history: CatImportBatch[]): number | null {
  const candidates = history
    .filter((b) => b.status === "completed" && typeof b.anno_campagna === "number")
    .map((b) => b.anno_campagna as number);
  if (candidates.length === 0) return null;
  return Math.max(...candidates);
}

type DistrettoRow = CatDistretto & { kpi: CatDistrettoKpi | null };

export default function CatastoDistrettiPage() {
  const router = useRouter();
  const [anno, setAnno] = useState<number>(currentYear());
  const [rows, setRows] = useState<DistrettoRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [annoNotice, setAnnoNotice] = useState<string | null>(null);

  useEffect(() => {
    async function load(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;

      setIsLoading(true);
      try {
        const [distretti, importHistory] = await Promise.all([
          catastoListDistretti(token),
          catastoGetImportHistory(token),
        ]);

        const latestImportedAnno = getLatestImportedAnno(importHistory);
        const nowYear = currentYear();
        if (latestImportedAnno != null && latestImportedAnno !== anno) {
          setAnno(latestImportedAnno);
          setAnnoNotice(
            latestImportedAnno < nowYear
              ? `L'anno corrente (${nowYear}) non risulta ancora caricato. Mostro i dati dell'anno ${latestImportedAnno}.`
              : null,
          );
          return;
        }
        if (latestImportedAnno != null && latestImportedAnno < nowYear) {
          setAnnoNotice(`L'anno corrente (${nowYear}) non risulta ancora caricato. Mostro i dati dell'anno ${latestImportedAnno}.`);
        } else {
          setAnnoNotice(null);
        }

        const kpis = await Promise.all(
          distretti.map(async (d) => {
            try {
              const kpi = await catastoGetDistrettoKpi(token, d.id, anno);
              return { distrettoId: d.id, kpi } as const;
            } catch {
              return { distrettoId: d.id, kpi: null } as const;
            }
          }),
        );
        const kpiIndex = Object.fromEntries(kpis.map((k) => [k.distrettoId, k.kpi]));
        setRows(distretti.map((d) => ({ ...d, kpi: kpiIndex[d.id] ?? null })));
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore caricamento distretti");
      } finally {
        setIsLoading(false);
      }
    }
    void load();
  }, [anno]);

  const totals = useMemo(() => {
    const withKpi = rows.map((r) => r.kpi).filter((kpi): kpi is CatDistrettoKpi => kpi != null);
    return {
      distretti: rows.length,
      supHa: withKpi.reduce((acc, k) => acc + Number(k.superficie_irrigabile_mq || 0) / 10_000, 0),
      importo0648: withKpi.reduce((acc, k) => acc + Number(k.importo_totale_0648 || 0), 0),
      importo0985: withKpi.reduce((acc, k) => acc + Number(k.importo_totale_0985 || 0), 0),
      anomalie: withKpi.reduce((acc, k) => acc + (k.totale_anomalie ?? 0), 0),
    };
  }, [rows]);

  const columns = useMemo<ColumnDef<DistrettoRow>[]>(
    () => [
      {
        header: "N.Distretto",
        accessorKey: "num_distretto",
        cell: ({ row }) => <span className="text-sm font-medium text-gray-900">{row.original.num_distretto}</span>,
      },
      {
        header: "Nome",
        accessorKey: "nome_distretto",
        cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.nome_distretto ?? "—"}</span>,
      },
      {
        header: "Sup.Irrigabile (ha)",
        id: "sup_ha",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">
            {row.original.kpi ? `${formatHaFromMq(row.original.kpi.superficie_irrigabile_mq)} ha` : "—"}
          </span>
        ),
      },
      {
        header: "Importo tot 0648",
        id: "imp_0648",
        cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.kpi ? formatEuro(row.original.kpi.importo_totale_0648) : "—"}</span>,
      },
      {
        header: "Importo tot 0985",
        id: "imp_0985",
        cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.kpi ? formatEuro(row.original.kpi.importo_totale_0985) : "—"}</span>,
      },
      {
        header: "N.Anomalie",
        id: "anom",
        cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.kpi ? row.original.kpi.totale_anomalie : "—"}</span>,
      },
    ],
    [],
  );

  return (
    <CatastoPage
      title="Distretti"
      description="Lista distretti con KPI aggregati per anno campagna."
      breadcrumb="Catasto / Distretti"
      requiredModule="catasto"
    >
      <div className="page-stack">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm text-gray-500">Anno campagna</p>
            <select className="form-control mt-1 w-[160px]" value={String(anno)} onChange={(e) => setAnno(Number(e.target.value))}>
              {[currentYear() + 1, currentYear(), currentYear() - 1, currentYear() - 2].map((y) => (
                <option key={y} value={String(y)}>
                  {y}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loadError ? (
          <AlertBanner variant="danger" title="Errore caricamento">
            {loadError}
          </AlertBanner>
        ) : null}

        {annoNotice ? (
          <AlertBanner variant="warning" title="Anno campagna">
            {annoNotice}
          </AlertBanner>
        ) : null}

        <div className="grid gap-3 md:grid-cols-4">
          <MetricCard label="Distretti" value={isLoading ? "—" : totals.distretti} />
          <MetricCard label="Sup. irrigabile" value={isLoading ? "—" : `${totals.supHa.toFixed(2)} ha`} />
          <MetricCard label="Importo 0648" value={isLoading ? "—" : formatEuro(totals.importo0648)} />
          <MetricCard label="Importo 0985" value={isLoading ? "—" : formatEuro(totals.importo0985)} />
        </div>

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Tabella distretti</p>
              <p className="mt-1 text-sm text-gray-500">Clic su una riga per aprire il dettaglio.</p>
            </div>
            <p className="text-sm text-gray-500">{isLoading ? "Caricamento…" : `${rows.length} righe`}</p>
          </div>

          <div className="mt-4">
            <DataTable
              data={rows}
              columns={columns}
              initialPageSize={12}
              emptyTitle={isLoading ? "Caricamento…" : "Nessun distretto"}
              emptyDescription={isLoading ? "Sto caricando i distretti dal backend." : "Non risultano distretti disponibili."}
              onRowClick={(row) => router.push(`/catasto/distretti/${row.id}`)}
            />
          </div>
        </article>
      </div>
    </CatastoPage>
  );
}
