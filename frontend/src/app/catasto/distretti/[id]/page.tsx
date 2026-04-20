"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { AlertBanner } from "@/components/ui/alert-banner";
import { MetricCard } from "@/components/ui/metric-card";
import { DataTable } from "@/components/table/data-table";
import type { ColumnDef } from "@tanstack/react-table";
import { AnomaliaStatusBadge } from "@/components/catasto/AnomaliaStatusBadge";
import { AnomaliaStatusPill } from "@/components/catasto/AnomaliaStatusPill";
import { catastoGetDistretto, catastoGetDistrettoKpi, catastoListAnomalie, catastoListParticelle } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnomalia, CatDistretto, CatDistrettoKpi, CatParticella } from "@/types/catasto";

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

type TabKey = "particelle" | "anomalie";

export default function CatastoDistrettoDetailPage() {
  const params = useParams<{ id: string }>();
  const distrettoId = params.id;

  const [anno, setAnno] = useState<number>(currentYear());
  const [tab, setTab] = useState<TabKey>("particelle");
  const [distretto, setDistretto] = useState<CatDistretto | null>(null);
  const [kpi, setKpi] = useState<CatDistrettoKpi | null>(null);
  const [particelle, setParticelle] = useState<CatParticella[]>([]);
  const [anomalie, setAnomalie] = useState<CatAnomalia[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function load(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;

      setIsLoading(true);
      try {
        const [d, k] = await Promise.all([
          catastoGetDistretto(token, distrettoId),
          catastoGetDistrettoKpi(token, distrettoId, anno),
        ]);
        setDistretto(d);
        setKpi(k);
        setLoadError(null);

        if (tab === "particelle") {
          const parts = await catastoListParticelle(token, { distretto: d.num_distretto, limit: 200 });
          setParticelle(parts);
        } else {
          const anoms = await catastoListAnomalie(token, {
            distretto: d.num_distretto,
            anno,
            status: "aperta",
            page: 1,
            pageSize: 200,
          });
          setAnomalie(anoms.items);
        }
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore caricamento distretto");
      } finally {
        setIsLoading(false);
      }
    }
    void load();
  }, [anno, distrettoId, tab]);

  const columns = useMemo<ColumnDef<CatParticella>[]>(
    () => [
      {
        header: "Comune",
        accessorKey: "nome_comune",
        cell: ({ row }) => (
          <div>
            <p className="text-sm font-medium text-gray-900">{row.original.nome_comune ?? row.original.cod_comune_istat}</p>
            <p className="text-xs text-gray-400">ISTAT {row.original.cod_comune_istat}</p>
          </div>
        ),
      },
      {
        header: "Riferimento",
        id: "rif",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">
            Fg.{row.original.foglio} Part.{row.original.particella}
            {row.original.subalterno ? ` Sub.${row.original.subalterno}` : ""}
          </span>
        ),
      },
      {
        header: "Sup. (ha)",
        id: "sup",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">
            {row.original.superficie_mq ? `${formatHaFromMq(row.original.superficie_mq)} ha` : "—"}
          </span>
        ),
      },
      {
        header: "Dettaglio",
        id: "open",
        cell: ({ row }) => (
          <Link className="text-sm font-medium text-[#1D4E35]" href={`/catasto/particelle/${row.original.id}`}>
            Apri
          </Link>
        ),
      },
    ],
    [],
  );

  const anomalieColumns = useMemo<ColumnDef<CatAnomalia>[]>(
    () => [
      { header: "Sev", accessorKey: "severita", cell: ({ row }) => <AnomaliaStatusBadge severita={row.original.severita} /> },
      { header: "Tipo", accessorKey: "tipo", cell: ({ row }) => <span className="text-sm font-medium text-gray-900">{row.original.tipo}</span> },
      { header: "Stato", accessorKey: "status", cell: ({ row }) => <AnomaliaStatusPill status={row.original.status} /> },
      { header: "Descrizione", accessorKey: "descrizione", cell: ({ row }) => <span className="text-sm text-gray-600">{row.original.descrizione ?? "—"}</span> },
    ],
    [],
  );

  return (
    <CatastoPage
      title={`Distretto ${distretto?.num_distretto ?? ""}`.trim()}
      description="Dettaglio distretto con KPI e liste correlate."
      breadcrumb="Catasto / Distretti / Dettaglio"
      requiredModule="catasto"
    >
      <div className="page-stack">
        {loadError ? (
          <AlertBanner variant="danger" title="Errore caricamento">
            {loadError}
          </AlertBanner>
        ) : null}

        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            <p className="text-lg font-semibold text-gray-900">{distretto?.nome_distretto ?? "—"}</p>
            <p className="mt-1 text-sm text-gray-500">
              N. distretto: <span className="font-medium text-gray-800">{distretto?.num_distretto ?? "—"}</span>
            </p>
          </div>
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

        <div className="grid gap-3 md:grid-cols-4">
          <MetricCard label="Particelle" value={isLoading ? "—" : kpi?.totale_particelle ?? "—"} />
          <MetricCard label="Utenze" value={isLoading ? "—" : kpi?.totale_utenze ?? "—"} />
          <MetricCard label="Importo 0648" value={isLoading ? "—" : kpi ? formatEuro(kpi.importo_totale_0648) : "—"} />
          <MetricCard label="Importo 0985" value={isLoading ? "—" : kpi ? formatEuro(kpi.importo_totale_0985) : "—"} />
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={`rounded-xl px-3 py-2 text-sm font-medium transition ${tab === "particelle" ? "bg-[#EAF3E8] text-[#1D4E35]" : "bg-white text-gray-600 hover:bg-gray-50"}`}
            onClick={() => setTab("particelle")}
          >
            Particelle
          </button>
          <button
            type="button"
            className={`rounded-xl px-3 py-2 text-sm font-medium transition ${tab === "anomalie" ? "bg-[#EAF3E8] text-[#1D4E35]" : "bg-white text-gray-600 hover:bg-gray-50"}`}
            onClick={() => setTab("anomalie")}
          >
            Anomalie
          </button>
        </div>

        {tab === "particelle" ? (
          <article className="panel-card">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-gray-900">Particelle (prime 200)</p>
                <p className="mt-1 text-sm text-gray-500">Filtrate per numero distretto.</p>
              </div>
              <p className="text-sm text-gray-500">{isLoading ? "Caricamento…" : `${particelle.length} righe`}</p>
            </div>
            <div className="mt-4">
              <DataTable
                data={particelle}
                columns={columns}
                initialPageSize={12}
                emptyTitle={isLoading ? "Caricamento…" : "Nessuna particella"}
                emptyDescription={isLoading ? "Sto caricando le particelle." : "Non risultano particelle per questo distretto."}
              />
            </div>
          </article>
        ) : (
          <article className="panel-card">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-gray-900">Anomalie aperte (prime 200)</p>
                <p className="mt-1 text-sm text-gray-500">Filtrate per distretto e anno campagna.</p>
              </div>
              <Link className="text-sm font-medium text-[#1D4E35] underline underline-offset-2" href="/catasto/anomalie">
                Vista completa
              </Link>
            </div>
            <div className="mt-4">
              <DataTable
                data={anomalie}
                columns={anomalieColumns}
                initialPageSize={12}
                emptyTitle={isLoading ? "Caricamento…" : "Nessuna anomalia"}
                emptyDescription={isLoading ? "Sto caricando le anomalie." : "Non risultano anomalie aperte per questo distretto/anno."}
              />
            </div>
          </article>
        )}
      </div>
    </CatastoPage>
  );
}
