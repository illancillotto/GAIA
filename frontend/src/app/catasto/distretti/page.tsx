"use client";

import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { DistrettoGisPreview } from "@/components/catasto/distretti/distretto-gis-preview";
import { CatastoWorkspaceModal } from "@/components/catasto/workspace-modal";
import { DataTable } from "@/components/table/data-table";
import { AlertBanner } from "@/components/ui/alert-banner";
import { MetricCard } from "@/components/ui/metric-card";
import { catastoGetDistrettoKpi, catastoGetImportHistory, catastoListDistretti } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatDistretto, CatDistrettoKpi, CatImportBatch } from "@/types/catasto";

const DISTRETTO_COLORS = [
  "#2E7D32",
  "#1565C0",
  "#EF6C00",
  "#6A1B9A",
  "#00838F",
  "#C2185B",
  "#9E9D24",
  "#5D4037",
  "#1976D2",
  "#F9A825",
  "#455A64",
  "#AD1457",
];

const CHART_COLORS = DISTRETTO_COLORS;
const OPERATIONS_PRIMARY_COLORS = ["#14532d", "#166534", "#047857", "#0f766e", "#0369a1", "#1d4ed8"];
const OPERATIONS_ALERT_COLORS = ["#f97316", "#ea580c", "#ef4444", "#dc2626", "#fb7185", "#f43f5e"];
const VALUE_0648_COLORS = ["#1d4e35", "#2E7D32", "#1565C0", "#6A1B9A", "#00838F"];
const VALUE_0985_COLORS = ["#8cb39d", "#9fbda9", "#9bb8c7", "#b4a7c8", "#9dc7c3"];

function formatEuro(value: string | number): string {
  const amount = typeof value === "number" ? value : Number(value);
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(Number.isFinite(amount) ? amount : 0);
}

function formatHaFromMq(value: string | number): string {
  const mq = typeof value === "number" ? value : Number(value);
  const ha = (Number.isFinite(mq) ? mq : 0) / 10_000;
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(ha);
}

function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat("it-IT", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function asNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value ?? 0);
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

function ratio(value: number, total: number): number {
  if (!Number.isFinite(value) || !Number.isFinite(total) || total <= 0) return 0;
  return Math.round((value / total) * 100);
}

function priorityTone(anomalie: number): "default" | "warning" | "danger" {
  if (anomalie >= 25) return "danger";
  if (anomalie > 0) return "warning";
  return "default";
}

type DistrettoRow = CatDistretto & {
  kpi: CatDistrettoKpi | null;
  superficieHa: number;
  importoTotale: number;
  priorityScore: number;
};

function DistrettoKpiCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string;
  subtitle: string;
}) {
  return (
    <article className="rounded-[1.5rem] border border-white/70 bg-white/90 p-5 shadow-[0_18px_40px_rgba(15,23,42,0.08)] backdrop-blur">
      <p className="text-[0.7rem] font-semibold uppercase tracking-[0.22em] text-[#5f7d68]">{title}</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{subtitle}</p>
    </article>
  );
}

function DistrettoPriorityPill({ anomalie }: { anomalie: number }) {
  const tone = priorityTone(anomalie);
  const className = {
    default: "bg-emerald-50 text-emerald-700 border-emerald-100",
    warning: "bg-amber-50 text-amber-700 border-amber-100",
    danger: "bg-rose-50 text-rose-700 border-rose-100",
  }[tone];
  const label = tone === "danger" ? "Alta" : tone === "warning" ? "Media" : "Stabile";
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${className}`}>{label}</span>;
}

function renderDistrettoTick(props: {
  x?: number | string;
  y?: number | string;
  payload?: { value?: string };
}) {
  const { x = 0, y = 0, payload } = props;
  const xPos = typeof x === "number" ? x : Number(x);
  const yPos = typeof y === "number" ? y : Number(y);
  const raw = String(payload?.value ?? "");
  const [short, ...restParts] = raw.split(" · ");
  const rest = restParts.join(" · ");

  return (
    <g transform={`translate(${xPos},${yPos})`}>
      <text textAnchor="middle" fill="#475569">
        <tspan x={0} dy="0" className="fill-slate-700 text-[11px] font-semibold">
          {short}
        </tspan>
        {rest ? (
          <tspan x={0} dy="14" className="fill-slate-400 text-[10px]">
            {rest.length > 18 ? `${rest.slice(0, 18)}…` : rest}
          </tspan>
        ) : null}
      </text>
    </g>
  );
}

function StatusProgressRow({
  label,
  value,
  total,
  tone,
}: {
  label: string;
  value: number;
  total: number;
  tone: "emerald" | "amber" | "slate";
}) {
  const percent = ratio(value, total);
  const toneClass = {
    emerald: "bg-emerald-500",
    amber: "bg-amber-500",
    slate: "bg-slate-400",
  }[tone];

  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="text-slate-500">
          {value} · {percent}%
        </span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${toneClass}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

export default function CatastoDistrettiPage() {
  const [anno, setAnno] = useState<number>(currentYear());
  const [rows, setRows] = useState<DistrettoRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [annoNotice, setAnnoNotice] = useState<string | null>(null);
  const [selectedDistretto, setSelectedDistretto] = useState<DistrettoRow | null>(null);

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
        const relevantDistretti = distretti.filter((distretto) => distretto.num_distretto !== "FD");

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
          relevantDistretti.map(async (d) => {
            try {
              const kpi = await catastoGetDistrettoKpi(token, d.id, anno);
              return { distrettoId: d.id, kpi } as const;
            } catch {
              return { distrettoId: d.id, kpi: null } as const;
            }
          }),
        );
        const kpiIndex = Object.fromEntries(kpis.map((k) => [k.distrettoId, k.kpi]));
        setRows(
          relevantDistretti.map((d) => {
            const kpi = kpiIndex[d.id] ?? null;
            const superficieHa = kpi ? Number(kpi.superficie_irrigabile_mq || 0) / 10_000 : 0;
            const importoTotale = kpi ? Number(kpi.importo_totale_0648 || 0) + Number(kpi.importo_totale_0985 || 0) : 0;
            const priorityScore = kpi
              ? (kpi.anomalie_error ?? 0) * 1000 + (kpi.totale_anomalie ?? 0) * 25 + (kpi.totale_utenze ?? 0)
              : 0;
            return { ...d, kpi, superficieHa, importoTotale, priorityScore };
          }),
        );
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
    const activeRows = rows.filter((row) => row.attivo);
    const withKpi = rows.filter((row) => row.kpi != null);
    const anomaliesTotal = withKpi.reduce((acc, row) => acc + (row.kpi?.totale_anomalie ?? 0), 0);
    const errorsTotal = withKpi.reduce((acc, row) => acc + (row.kpi?.anomalie_error ?? 0), 0);
    return {
      distretti: rows.length,
      attivi: activeRows.length,
      supHa: withKpi.reduce((acc, row) => acc + row.superficieHa, 0),
      importo0648: withKpi.reduce((acc, row) => acc + Number(row.kpi?.importo_totale_0648 || 0), 0),
      importo0985: withKpi.reduce((acc, row) => acc + Number(row.kpi?.importo_totale_0985 || 0), 0),
      totaleUtenze: withKpi.reduce((acc, row) => acc + (row.kpi?.totale_utenze ?? 0), 0),
      totaleParticelle: withKpi.reduce((acc, row) => acc + (row.kpi?.totale_particelle ?? 0), 0),
      anomalie: anomaliesTotal,
      anomalieError: errorsTotal,
      quotaError: ratio(errorsTotal, anomaliesTotal),
    };
  }, [rows]);

  const rankedRows = useMemo(() => [...rows].sort((a, b) => b.priorityScore - a.priorityScore), [rows]);

  const topOperationalData = useMemo(
    () =>
      rankedRows
        .filter((row) => row.kpi != null)
        .slice(0, 6)
        .map((row) => ({
          name: `D${row.num_distretto} · ${row.nome_distretto ?? "Senza nome"}`,
          fullName: `Distretto ${row.num_distretto}${row.nome_distretto ? ` · ${row.nome_distretto}` : ""}`,
          anomalie: row.kpi?.totale_anomalie ?? 0,
          errori: row.kpi?.anomalie_error ?? 0,
          utenze: row.kpi?.totale_utenze ?? 0,
        })),
    [rankedRows],
  );

  const economicData = useMemo(
    () =>
      [...rows]
        .filter((row) => row.kpi != null)
        .sort((a, b) => b.importoTotale - a.importoTotale)
        .slice(0, 5)
        .map((row) => ({
          name: `D${row.num_distretto} · ${row.nome_distretto ?? "Senza nome"}`,
          fullName: `Distretto ${row.num_distretto}${row.nome_distretto ? ` · ${row.nome_distretto}` : ""}`,
          importo0648: Number(row.kpi?.importo_totale_0648 || 0),
          importo0985: Number(row.kpi?.importo_totale_0985 || 0),
        })),
    [rows],
  );

  const statusBreakdown = useMemo(() => {
    const withKpi = rows.filter((row) => row.kpi != null).length;
    const stabili = rows.filter((row) => row.kpi != null && (row.kpi?.totale_anomalie ?? 0) === 0).length;
    const conAnomalie = rows.filter((row) => row.kpi != null && (row.kpi?.totale_anomalie ?? 0) > 0).length;
    const senzaKpi = rows.filter((row) => row.kpi == null).length;
    return { withKpi, stabili, conAnomalie, senzaKpi };
  }, [rows]);

  const spotlightRows = useMemo(
    () => rankedRows.filter((row) => row.kpi != null).slice(0, 3),
    [rankedRows],
  );

  const columns = useMemo<ColumnDef<DistrettoRow>[]>(
    () => [
      {
        header: "Distretto",
        id: "distretto",
        accessorFn: (row) => row.num_distretto,
        cell: ({ row }) => (
          <div>
            <p className="text-sm font-semibold text-slate-950">Distretto {row.original.num_distretto}</p>
            <p className="mt-0.5 text-xs text-slate-500">{row.original.nome_distretto ?? "Nome non disponibile"}</p>
          </div>
        ),
      },
      {
        header: "Priorità",
        id: "priority",
        accessorFn: (row) => row.priorityScore,
        cell: ({ row }) => <DistrettoPriorityPill anomalie={row.original.kpi?.totale_anomalie ?? 0} />,
      },
      {
        header: "Copertura",
        id: "coverage",
        accessorFn: (row) => row.superficieHa,
        cell: ({ row }) => (
          <div className="min-w-[120px]">
            <p className="text-sm font-medium text-slate-800">{row.original.kpi ? `${formatHaFromMq(row.original.kpi.superficie_irrigabile_mq)} ha` : "—"}</p>
            <p className="text-xs text-slate-500">{row.original.kpi ? `${row.original.kpi.totale_particelle} particelle` : "Nessun indicatore"}</p>
          </div>
        ),
      },
      {
        header: "Utenze",
        id: "utenze",
        accessorFn: (row) => row.kpi?.totale_utenze ?? -1,
        cell: ({ row }) => <span className="text-sm text-slate-700">{row.original.kpi ? row.original.kpi.totale_utenze : "—"}</span>,
      },
      {
        header: "Anomalie",
        id: "anomalie",
        accessorFn: (row) => row.kpi?.totale_anomalie ?? -1,
        cell: ({ row }) => {
          const total = row.original.kpi?.totale_anomalie ?? 0;
          const errors = row.original.kpi?.anomalie_error ?? 0;
          return row.original.kpi ? (
            <div className="min-w-[120px]">
              <p className="text-sm font-medium text-slate-800">{total}</p>
              <p className="text-xs text-slate-500">{errors} errori</p>
            </div>
          ) : (
            <span className="text-sm text-slate-400">—</span>
          );
        },
      },
      {
        header: "Valore",
        id: "valore",
        accessorFn: (row) => row.importoTotale,
        cell: ({ row }) => (
          <div className="min-w-[140px]">
            <p className="text-sm font-medium text-slate-900">{row.original.kpi ? formatEuro(row.original.importoTotale) : "—"}</p>
            <p className="text-xs text-slate-500">
              {row.original.kpi ? `0648 ${formatEuro(row.original.kpi.importo_totale_0648)}` : "Nessun importo"}
            </p>
          </div>
        ),
      },
    ],
    [],
  );

  return (
    <CatastoPage
      title="Distretti"
      description="Vista operativa dei distretti catastali con priorità, carico anomalie e peso economico per anno campagna."
      breadcrumb="Catasto / Distretti"
      requiredModule="catasto"
    >
      <div className="page-stack">
        <section className="overflow-hidden rounded-[2rem] border border-[#d8efe1] bg-[radial-gradient(circle_at_top_left,_rgba(34,197,94,0.18),_transparent_36%),linear-gradient(135deg,#f7fcf8_0%,#eef7f2_52%,#fdfdfb_100%)] shadow-[0_20px_60px_rgba(15,23,42,0.08)]">
          <div className="flex flex-col gap-6 p-6 md:p-7 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#b9dfc8] bg-white/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[#1d4e35]">
                Distretto intelligence
                <span className="rounded-full bg-[#e3f4e8] px-2 py-0.5 text-[11px] normal-case tracking-normal text-[#2d6b47]">
                  {isLoading ? "aggiornamento" : `anno ${anno}`}
                </span>
              </div>
              <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">Cruscotto distretti più leggibile e operativo</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                Riepilogo immediato di copertura, valore economico e aree da seguire prima. La classifica combina errori, anomalie e volume utenze.
              </p>
            </div>

            <div className="flex flex-wrap items-end gap-3">
              <label className="block">
                <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Anno campagna</span>
                <select className="form-control mt-1 w-[170px] bg-white" value={String(anno)} onChange={(e) => setAnno(Number(e.target.value))}>
                  {[currentYear() + 1, currentYear(), currentYear() - 1, currentYear() - 2].map((y) => (
                    <option key={y} value={String(y)}>
                      {y}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
        </section>

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

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <DistrettoKpiCard title="Distretti attivi" value={isLoading ? "—" : `${totals.attivi}/${totals.distretti}`} subtitle="Perimetro operativo disponibile" />
          <DistrettoKpiCard title="Superficie irrigabile" value={isLoading ? "—" : `${totals.supHa.toFixed(1)} ha`} subtitle={`${formatCompactNumber(totals.totaleParticelle)} particelle censite`} />
          <DistrettoKpiCard title="Valore economico" value={isLoading ? "—" : formatEuro(totals.importo0648 + totals.importo0985)} subtitle={`0648 ${formatEuro(totals.importo0648)} · 0985 ${formatEuro(totals.importo0985)}`} />
          <DistrettoKpiCard title="Pressione anomalie" value={isLoading ? "—" : String(totals.anomalie)} subtitle={`${totals.anomalieError} errori · ${totals.quotaError}% quota error`} />
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <article className="overflow-hidden rounded-[1.75rem] border border-[#e7efe8] bg-white shadow-[0_16px_45px_rgba(15,23,42,0.07)]">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <p className="text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-[#5f7d68]">Focus operativo</p>
                <h2 className="mt-1 text-xl font-semibold text-slate-950">Distretti da guardare per primi</h2>
              </div>
              <p className="text-sm text-slate-500">Ranking combinato su errori, anomalie e volume</p>
            </div>
            <div className="space-y-3 px-6 py-5">
              {spotlightRows.map((row, index) => (
                <button
                  key={row.id}
                  type="button"
                  onClick={() => setSelectedDistretto(row)}
                  className="flex w-full items-center justify-between gap-4 rounded-[1.35rem] border border-slate-100 bg-slate-50 px-4 py-4 text-left transition hover:border-[#b9dfc8] hover:bg-[#f5faf7]"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[#1d4e35] text-sm font-semibold text-white">
                      {index + 1}
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-base font-semibold text-slate-950">Distretto {row.num_distretto}</p>
                        <DistrettoPriorityPill anomalie={row.kpi?.totale_anomalie ?? 0} />
                      </div>
                      <p className="mt-1 text-sm text-slate-500">{row.nome_distretto ?? "Nome non disponibile"}</p>
                      <p className="mt-2 text-sm text-slate-600">
                        {row.kpi?.totale_anomalie ?? 0} anomalie · {row.kpi?.anomalie_error ?? 0} errori · {row.kpi?.totale_utenze ?? 0} utenze
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-slate-900">{formatEuro(row.importoTotale)}</p>
                    <p className="mt-1 text-xs text-slate-500">{formatHaFromMq(row.kpi?.superficie_irrigabile_mq ?? 0)} ha</p>
                  </div>
                </button>
              ))}
              {!isLoading && spotlightRows.length === 0 ? (
                <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">Nessun distretto con indicatori disponibili per l&apos;anno selezionato.</p>
              ) : null}
            </div>
          </article>

          <article className="overflow-hidden rounded-[1.75rem] border border-[#e7efe8] bg-white shadow-[0_16px_45px_rgba(15,23,42,0.07)]">
            <div className="border-b border-slate-100 px-6 py-5">
              <p className="text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-[#5f7d68]">Bilanciamento</p>
              <h2 className="mt-1 text-xl font-semibold text-slate-950">Stato del parco distretti</h2>
            </div>
            <div className="grid gap-4 px-6 py-5 sm:grid-cols-2">
              <MetricCard label="Utenze totali" value={isLoading ? "—" : totals.totaleUtenze} sub="Somma indicatori caricati" />
              <MetricCard label="Errori aperti" value={isLoading ? "—" : totals.anomalieError} sub="Parte più urgente delle anomalie" variant={totals.anomalieError > 0 ? "danger" : "success"} />
              <div className="sm:col-span-2 rounded-[1.25rem] border border-slate-100 bg-slate-50 p-4">
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl bg-white p-4 shadow-sm">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Copertura indicatori</p>
                    <p className="mt-2 text-2xl font-semibold text-slate-900">{statusBreakdown.withKpi}/{rows.length}</p>
                    <p className="mt-1 text-xs text-slate-500">distretti con indicatori caricati</p>
                  </div>
                  <div className="rounded-2xl bg-white p-4 shadow-sm">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Stabili</p>
                    <p className="mt-2 text-2xl font-semibold text-emerald-700">{statusBreakdown.stabili}</p>
                    <p className="mt-1 text-xs text-slate-500">nessuna anomalia aperta</p>
                  </div>
                  <div className="rounded-2xl bg-white p-4 shadow-sm">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Da seguire</p>
                    <p className="mt-2 text-2xl font-semibold text-amber-700">{statusBreakdown.conAnomalie}</p>
                    <p className="mt-1 text-xs text-slate-500">almeno una anomalia aperta</p>
                  </div>
                </div>

                <div className="mt-5 space-y-4">
                  <StatusProgressRow label="Distretti con indicatori" value={statusBreakdown.withKpi} total={rows.length} tone="slate" />
                  <StatusProgressRow label="Distretti stabili" value={statusBreakdown.stabili} total={rows.length} tone="emerald" />
                  <StatusProgressRow label="Distretti con anomalie" value={statusBreakdown.conAnomalie} total={rows.length} tone="amber" />
                  {statusBreakdown.senzaKpi > 0 ? (
                    <StatusProgressRow label="Distretti senza indicatori" value={statusBreakdown.senzaKpi} total={rows.length} tone="slate" />
                  ) : null}
                </div>
              </div>
            </div>
          </article>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <article className="overflow-hidden rounded-[1.75rem] border border-[#e7efe8] bg-white shadow-[0_16px_45px_rgba(15,23,42,0.07)]">
            <div className="border-b border-slate-100 px-6 py-5">
              <p className="text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-[#5f7d68]">Chart anomalie</p>
              <h2 className="mt-1 text-xl font-semibold text-slate-950">Top distretti per carico operativo</h2>
            </div>
            <div className="h-[320px] bg-[linear-gradient(180deg,#f8fbf9_0%,#ffffff_55%)] px-4 py-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topOperationalData} margin={{ top: 8, right: 12, left: 4, bottom: 28 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#dfe7e2" />
                  <XAxis dataKey="name" tickLine={false} axisLine={false} interval={0} height={44} tick={renderDistrettoTick} />
                  <YAxis tickLine={false} axisLine={false} />
                  <Tooltip
                    labelFormatter={(_, payload) => {
                      const item = payload?.[0]?.payload as { fullName?: string } | undefined;
                      return item?.fullName ?? "";
                    }}
                  />
                  <Bar dataKey="anomalie" name="Anomalie" radius={[8, 8, 0, 0]}>
                    {topOperationalData.map((entry, index) => (
                      <Cell key={`${entry.name}-anomalie`} fill={OPERATIONS_PRIMARY_COLORS[index % OPERATIONS_PRIMARY_COLORS.length]} />
                    ))}
                  </Bar>
                  <Bar dataKey="errori" name="Errori" radius={[8, 8, 0, 0]}>
                    {topOperationalData.map((entry, index) => (
                      <Cell key={`${entry.name}-errori`} fill={OPERATIONS_ALERT_COLORS[index % OPERATIONS_ALERT_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="overflow-hidden rounded-[1.75rem] border border-[#e7efe8] bg-white shadow-[0_16px_45px_rgba(15,23,42,0.07)]">
            <div className="border-b border-slate-100 px-6 py-5">
              <p className="text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-[#5f7d68]">Chart valore</p>
              <h2 className="mt-1 text-xl font-semibold text-slate-950">Dove si concentra il valore economico</h2>
            </div>
            <div className="h-[320px] bg-[linear-gradient(180deg,#f8fbf9_0%,#ffffff_55%)] px-4 py-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={economicData} margin={{ top: 8, right: 12, left: 4, bottom: 28 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#dfe7e2" />
                  <XAxis dataKey="name" tickLine={false} axisLine={false} interval={0} height={44} tick={renderDistrettoTick} />
                  <YAxis tickLine={false} axisLine={false} tickFormatter={(value) => formatCompactNumber(Number(value))} />
                  <Tooltip
                    labelFormatter={(_, payload) => {
                      const item = payload?.[0]?.payload as { fullName?: string } | undefined;
                      return item?.fullName ?? "";
                    }}
                    formatter={(value) => formatEuro(asNumber(value))}
                  />
                  <Bar dataKey="importo0648" name="Importo 0648" radius={[8, 8, 0, 0]}>
                    {economicData.map((entry, index) => (
                      <Cell key={`${entry.name}-0648`} fill={VALUE_0648_COLORS[index % VALUE_0648_COLORS.length]} />
                    ))}
                  </Bar>
                  <Bar dataKey="importo0985" name="Importo 0985" radius={[8, 8, 0, 0]}>
                    {economicData.map((entry, index) => (
                      <Cell key={`${entry.name}-0985`} fill={VALUE_0985_COLORS[index % VALUE_0985_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </article>
        </div>

        <article className="rounded-[1.75rem] border border-[#e7efe8] bg-white shadow-[0_16px_45px_rgba(15,23,42,0.07)]">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
            <div>
              <p className="text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-[#5f7d68]">Lista completa</p>
              <h2 className="mt-1 text-xl font-semibold text-slate-950">Tabella distretti</h2>
              <p className="mt-1 text-sm text-slate-500">Click sulla riga per aprire il dettaglio operativo del distretto.</p>
            </div>
            <p className="text-sm text-slate-500">{isLoading ? "Caricamento…" : `${rows.length} distretti`}</p>
          </div>

          <div className="px-6 py-5">
            <DataTable
              data={rankedRows}
              columns={columns}
              initialPageSize={12}
              emptyTitle={isLoading ? "Caricamento…" : "Nessun distretto"}
              emptyDescription={isLoading ? "Sto caricando i distretti dal backend." : "Non risultano distretti disponibili."}
              onRowClick={(row) => setSelectedDistretto(row)}
              initialSorting={[{ id: "priority", desc: true }]}
            />
          </div>
        </article>

        <CatastoWorkspaceModal
          open={selectedDistretto != null}
          href={selectedDistretto ? `/catasto/distretti/${selectedDistretto.id}` : null}
          title={selectedDistretto ? `Distretto ${selectedDistretto.num_distretto}` : "Dettaglio distretto"}
          description={selectedDistretto?.nome_distretto ?? "Dettaglio distretto aperto dalla lista distretti."}
          onClose={() => setSelectedDistretto(null)}
        >
          {selectedDistretto ? (
            <DistrettoGisPreview distretto={selectedDistretto} kpi={selectedDistretto.kpi} />
          ) : null}
        </CatastoWorkspaceModal>
      </div>
    </CatastoPage>
  );
}
