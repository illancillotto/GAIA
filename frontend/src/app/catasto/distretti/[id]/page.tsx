"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { AlertBanner } from "@/components/ui/alert-banner";
import { MetricCard } from "@/components/ui/metric-card";
import { DataTable } from "@/components/table/data-table";
import type { ColumnDef } from "@tanstack/react-table";
import { AnomaliaStatusBadge } from "@/components/catasto/AnomaliaStatusBadge";
import { AnomaliaStatusPill } from "@/components/catasto/AnomaliaStatusPill";
import {
  catastoGetDistretto,
  catastoGetDistrettoKpi,
  catastoGetImportHistory,
  catastoListAnomalie,
  catastoListParticelle,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnomalia, CatDistretto, CatDistrettoKpi, CatImportBatch, CatParticella } from "@/types/catasto";

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

type TabKey = "particelle" | "anomalie";

export default function CatastoDistrettoDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const distrettoId = params.id;
  const isEmbedded = searchParams.get("embedded") === "1";

  const [anno, setAnno] = useState<number>(currentYear());
  const [tab, setTab] = useState<TabKey>("particelle");
  const [distretto, setDistretto] = useState<CatDistretto | null>(null);
  const [kpi, setKpi] = useState<CatDistrettoKpi | null>(null);
  const [particelle, setParticelle] = useState<CatParticella[]>([]);
  const [anomalie, setAnomalie] = useState<CatAnomalia[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [annoNotice, setAnnoNotice] = useState<string | null>(null);

  useEffect(() => {
    async function load(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;

      setIsLoading(true);
      try {
        const importHistory = await catastoGetImportHistory(token);
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

  const particelleColumns = useMemo<ColumnDef<CatParticella>[]>(
    () => [
      {
        header: "Comune",
        accessorKey: "nome_comune",
        cell: ({ row }) => (
          <div>
            <p className="text-sm font-medium text-gray-900">{row.original.nome_comune ?? row.original.cod_comune_capacitas}</p>
            <p className="text-xs text-gray-400">Codice Capacitas {row.original.cod_comune_capacitas}</p>
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
        header: "Sup. catastale (ha)",
        id: "supCatastale",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">
            {row.original.superficie_mq ? `${formatHaFromMq(row.original.superficie_mq)} ha` : "—"}
          </span>
        ),
      },
      {
        header: "Sup. grafica (ha)",
        id: "supGrafica",
        cell: ({ row }) => (
          <span className="text-sm text-gray-700">
            {row.original.superficie_grafica_mq ? `${formatHaFromMq(row.original.superficie_grafica_mq)} ha` : "—"}
          </span>
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

  function triggerDownload(content: BlobPart, mimeType: string, filename: string): void {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function exportCurrentCsv(): void {
    if (!distretto) return;
    const filename = `distretto-${distretto.num_distretto}-${tab}-${anno}.csv`;
    const rows = tab === "particelle"
      ? [
          ["Comune", "Codice Capacitas", "Foglio", "Particella", "Subalterno", "Superficie catastale mq", "Superficie grafica mq", "Distretto"],
          ...particelle.map((item) => [
            item.nome_comune ?? "",
            String(item.cod_comune_capacitas ?? ""),
            item.foglio ?? "",
            item.particella ?? "",
            item.subalterno ?? "",
            String(item.superficie_mq ?? ""),
            String(item.superficie_grafica_mq ?? ""),
            String(item.num_distretto ?? ""),
          ]),
        ]
      : [
          ["Severita", "Tipo", "Stato", "Descrizione"],
          ...anomalie.map((item) => [
            item.severita ?? "",
            item.tipo ?? "",
            item.status ?? "",
            item.descrizione ?? "",
          ]),
        ];
    const content = rows
      .map((row) => row.map((value) => `"${String(value).replaceAll("\"", "\"\"")}"`).join(";"))
      .join("\n");
    triggerDownload(content, "text/csv;charset=utf-8", filename);
  }

  function exportCurrentXls(): void {
    if (!distretto) return;
    const filename = `distretto-${distretto.num_distretto}-${tab}-${anno}.xls`;
    const headers = tab === "particelle"
      ? ["Comune", "Codice Capacitas", "Foglio", "Particella", "Subalterno", "Superficie catastale mq", "Superficie grafica mq", "Distretto"]
      : ["Severita", "Tipo", "Stato", "Descrizione"];
    const rows = tab === "particelle"
      ? particelle.map((item) => [
          item.nome_comune ?? "",
          String(item.cod_comune_capacitas ?? ""),
          item.foglio ?? "",
          item.particella ?? "",
          item.subalterno ?? "",
          String(item.superficie_mq ?? ""),
          String(item.superficie_grafica_mq ?? ""),
          String(item.num_distretto ?? ""),
        ])
      : anomalie.map((item) => [
          item.severita ?? "",
          item.tipo ?? "",
          item.status ?? "",
          item.descrizione ?? "",
        ]);
    const table = `
      <table>
        <thead><tr>${headers.map((header) => `<th>${header}</th>`).join("")}</tr></thead>
        <tbody>${rows.map((row) => `<tr>${row.map((value) => `<td>${String(value)}</td>`).join("")}</tr>`).join("")}</tbody>
      </table>
    `;
    triggerDownload(`\ufeff${table}`, "application/vnd.ms-excel;charset=utf-8", filename);
  }

  function exportCurrentPdf(): void {
    if (!distretto) return;
    const headers = tab === "particelle" ? ["Comune", "Riferimento", "Sup. catastale (ha)", "Sup. grafica (ha)"] : ["Sev", "Tipo", "Stato", "Descrizione"];
    const rows = tab === "particelle"
      ? particelle.map((item) => [
          item.nome_comune ?? "—",
          `Fg.${item.foglio} Part.${item.particella}${item.subalterno ? ` Sub.${item.subalterno}` : ""}`,
          item.superficie_mq ? `${formatHaFromMq(item.superficie_mq)} ha` : "—",
          item.superficie_grafica_mq ? `${formatHaFromMq(item.superficie_grafica_mq)} ha` : "—",
        ])
      : anomalie.map((item) => [
          item.severita ?? "—",
          item.tipo ?? "—",
          item.status ?? "—",
          item.descrizione ?? "—",
        ]);
    const popup = window.open("", "_blank", "width=1200,height=800");
    if (!popup) return;
    popup.document.write(`
      <html>
        <head>
          <title>Distretto ${distretto.num_distretto}</title>
          <style>
            body { font-family: Arial, sans-serif; padding: 24px; color: #111827; }
            h1 { font-size: 20px; margin-bottom: 4px; }
            p { color: #6b7280; margin-bottom: 16px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid #d1d5db; padding: 8px; text-align: left; font-size: 12px; vertical-align: top; }
            th { background: #f3f4f6; }
          </style>
        </head>
        <body>
          <h1>Distretto ${distretto.num_distretto}</h1>
          <p>${distretto.nome_distretto ?? ""} · ${tab} · anno ${anno}</p>
          <table>
            <thead><tr>${headers.map((header) => `<th>${header}</th>`).join("")}</tr></thead>
            <tbody>${rows.map((row) => `<tr>${row.map((value) => `<td>${String(value)}</td>`).join("")}</tr>`).join("")}</tbody>
          </table>
        </body>
      </html>
    `);
    popup.document.close();
    popup.focus();
    popup.print();
  }

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

        {annoNotice ? (
          <AlertBanner variant="warning" title="Anno campagna">
            {annoNotice}
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

        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gray-100 bg-white px-4 py-3">
          <p className="text-sm text-gray-500">
            Export vista corrente: <span className="font-medium text-gray-800">{tab === "particelle" ? "Particelle" : "Anomalie"}</span>
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={exportCurrentCsv}>Esporta CSV</button>
            <button type="button" className="btn-secondary" onClick={exportCurrentXls}>Esporta XLS</button>
            <button type="button" className="btn-secondary" onClick={exportCurrentPdf}>Esporta PDF</button>
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
                columns={particelleColumns}
                initialPageSize={12}
                onRowClick={(row) => {
                  router.push(isEmbedded ? `/catasto/particelle/${row.id}?embedded=1` : `/catasto/particelle/${row.id}`);
                }}
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
