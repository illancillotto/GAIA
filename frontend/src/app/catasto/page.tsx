"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { CatastoWorkspaceModal } from "@/components/catasto/workspace-modal";
import { AlertBanner } from "@/components/ui/alert-banner";
import { RefreshIcon } from "@/components/ui/icons";
import { catastoGetDashboardSummary } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatDashboardDistrettoSummary, CatDashboardSummary } from "@/types/catasto";

function currentYear(): number {
  return new Date().getFullYear();
}

function formatNumber(value: number | null | undefined): string {
  return new Intl.NumberFormat("it-IT").format(Number.isFinite(value) ? Number(value) : 0);
}

function formatEuro(value: number | null | undefined): string {
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(
    Number.isFinite(value) ? Number(value) : 0,
  );
}

function formatHa(valueMq: number | null | undefined): string {
  const ha = (Number.isFinite(valueMq) ? Number(valueMq) : 0) / 10_000;
  return new Intl.NumberFormat("it-IT", { maximumFractionDigits: 1 }).format(ha);
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function percent(part: number, total: number): number {
  if (!Number.isFinite(part) || !Number.isFinite(total) || total <= 0) return 0;
  return Math.round((part / total) * 100);
}

function statusTone(summary: CatDashboardSummary | null): "success" | "warning" | "danger" | "default" {
  if (!summary) return "default";
  if (summary.imports.processing_batch > 0) return "warning";
  if (summary.imports.failed_batch > 0 || summary.anomalie.error > 0) return "danger";
  if (summary.imports.latest_completed) return "success";
  return "default";
}

function StatCard({
  label,
  value,
  sub,
  tone = "default",
}: {
  label: string;
  value: string | number;
  sub: string;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  const toneClass = {
    default: "border-slate-200 bg-white text-slate-900",
    success: "border-emerald-200 bg-emerald-50 text-emerald-950",
    warning: "border-amber-200 bg-amber-50 text-amber-950",
    danger: "border-rose-200 bg-rose-50 text-rose-950",
  }[tone];

  return (
    <article className={`rounded-[1.35rem] border p-4 shadow-sm ${toneClass}`}>
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{sub}</p>
    </article>
  );
}

function ProgressRow({ label, value, total, tone = "emerald" }: { label: string; value: number; total: number; tone?: "emerald" | "amber" | "rose" | "blue" }) {
  const width = percent(value, total);
  const barClass = {
    emerald: "bg-emerald-500",
    amber: "bg-amber-500",
    rose: "bg-rose-500",
    blue: "bg-blue-500",
  }[tone];
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="text-slate-500">
          {formatNumber(value)} · {width}%
        </span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${barClass}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

export default function CatastoDashboardPage() {
  const [anno, setAnno] = useState<number | null>(null);
  const [summary, setSummary] = useState<CatDashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedDistretto, setSelectedDistretto] = useState<CatDashboardDistrettoSummary | null>(null);

  useEffect(() => {
    async function load(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;

      setIsLoading(true);
      try {
        const payload = await catastoGetDashboardSummary(token, { anno: anno ?? undefined });
        setSummary(payload);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore caricamento dashboard Catasto");
      } finally {
        setIsLoading(false);
      }
    }

    void load();
  }, [anno]);

  const yearOptions = useMemo(() => {
    const values = [summary?.imports.latest_imported_anno, summary?.anno, currentYear(), currentYear() - 1, currentYear() - 2]
      .filter((value): value is number => typeof value === "number")
      .sort((a, b) => b - a);
    return Array.from(new Set(values));
  }, [summary]);

  const sortedDistretti = useMemo(() => {
    return [...(summary?.distretti ?? [])].sort((a, b) => {
      const scoreA = a.anomalie_error * 1000 + a.totale_anomalie_aperte * 10 + a.totale_particelle;
      const scoreB = b.anomalie_error * 1000 + b.totale_anomalie_aperte * 10 + b.totale_particelle;
      return scoreB - scoreA;
    });
  }, [summary]);

  const activeYear = summary?.anno ?? anno;
  const tone = statusTone(summary);
  const statusLabel = tone === "success" ? "Operativo" : tone === "warning" ? "Import in corso" : tone === "danger" ? "Da verificare" : "In attesa dati";

  return (
    <CatastoPage
      title="GAIA Catasto"
      description="Dashboard operativa Catasto con copertura dati, ruolo, anomalie, distretti e stato import."
      breadcrumb="Catasto / Dashboard"
      requiredModule="catasto"
    >
      <div className="page-stack">
        <section className="overflow-hidden rounded-[2rem] border border-emerald-100 bg-[#f5faf7] shadow-sm">
          <div className="relative p-6 md:p-7">
            <div className="absolute right-0 top-0 h-48 w-48 rounded-full bg-emerald-200/35 blur-3xl" />
            <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-3xl">
                <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                  Catasto consortile
                  <span className={`rounded-full px-2 py-0.5 normal-case tracking-normal ${tone === "danger" ? "bg-rose-100 text-rose-700" : tone === "warning" ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700"}`}>
                    {statusLabel}
                  </span>
                </div>
                <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">Cruscotto dati catastali</h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                  Controllo unico su import, particelle, distretti, ruolo e anomalie. I valori arrivano da un aggregato backend dedicato, non da somme stimate lato frontend.
                </p>
              </div>

              <div className="flex flex-wrap items-end gap-3">
                <label className="block">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Anno campagna</span>
                  <select
                    className="form-control mt-1 w-[170px] bg-white"
                    value={activeYear != null ? String(activeYear) : ""}
                    onChange={(event) => setAnno(event.target.value ? Number(event.target.value) : null)}
                  >
                    <option value="">Ultimo caricato</option>
                    {yearOptions.map((year) => (
                      <option key={year} value={String(year)}>
                        {year}
                      </option>
                    ))}
                  </select>
                </label>
                <Link className="btn-secondary bg-white" href="/catasto/gis">
                  Apri GIS
                </Link>
                <Link className="btn-primary" href="/catasto/import">
                  <RefreshIcon className="h-4 w-4" />
                  Import dati
                </Link>
              </div>
            </div>
          </div>
        </section>

        {loadError ? (
          <AlertBanner variant="danger" title="Errore caricamento">
            {loadError}
          </AlertBanner>
        ) : null}

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Particelle correnti"
            value={isLoading ? "—" : formatNumber(summary?.particelle.totale_correnti)}
            sub={`${formatNumber(summary?.particelle.con_geometria)} con geometria`}
            tone="success"
          />
          <StatCard
            label="Utenze ruolo"
            value={isLoading ? "—" : formatNumber(summary?.utenze.totale_utenze)}
            sub={`Anno ${activeYear ?? "—"} · ${formatNumber(summary?.utenze.particelle_collegate)} particelle`}
          />
          <StatCard
            label="Importi 0648+0985"
            value={isLoading ? "—" : formatEuro(summary?.utenze.importo_totale)}
            sub={`${formatHa(summary?.utenze.superficie_irrigabile_mq)} ha irrigabili`}
          />
          <StatCard
            label="Anomalie aperte"
            value={isLoading ? "—" : formatNumber(summary?.anomalie.aperte)}
            sub={`${formatNumber(summary?.anomalie.error)} error · ${formatNumber(summary?.anomalie.warning)} warning`}
            tone={(summary?.anomalie.error ?? 0) > 0 ? "danger" : (summary?.anomalie.warning ?? 0) > 0 ? "warning" : "success"}
          />
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <article className="panel-card">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Copertura dati</p>
                <h2 className="mt-1 text-xl font-semibold text-slate-950">Particelle e collegamenti</h2>
              </div>
              <Link className="text-sm font-medium text-[#1D4E35] underline underline-offset-2" href="/catasto/particelle">
                Apri particelle
              </Link>
            </div>
            <div className="mt-5 space-y-5">
              <ProgressRow label="Con geometria GIS" value={summary?.particelle.con_geometria ?? 0} total={summary?.particelle.totale_correnti ?? 0} tone="emerald" />
              <ProgressRow label="Associate a distretto" value={summary?.particelle.in_distretto ?? 0} total={summary?.particelle.totale_correnti ?? 0} tone="blue" />
              <ProgressRow label="Collegate al ruolo" value={summary?.utenze.particelle_collegate ?? 0} total={summary?.particelle.totale_correnti ?? 0} tone="amber" />
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Fuori distretto</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{formatNumber(summary?.particelle.fuori_distretto)}</p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Senza distretto</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{formatNumber(summary?.particelle.senza_distretto)}</p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Senza geometria</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{formatNumber(summary?.particelle.senza_geometria)}</p>
              </div>
            </div>
          </article>

          <article className="panel-card">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.16em] text-rose-700">Qualità dati</p>
                <h2 className="mt-1 text-xl font-semibold text-slate-950">Cose da correggere</h2>
              </div>
              <Link className="text-sm font-medium text-[#1D4E35] underline underline-offset-2" href="/catasto/anomalie">
                Apri anomalie
              </Link>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <StatCard label="CF mancanti" value={formatNumber(summary?.utenze.cf_mancante)} sub="Righe ruolo con anomalia" tone={(summary?.utenze.cf_mancante ?? 0) > 0 ? "warning" : "success"} />
              <StatCard label="CF invalidi" value={formatNumber(summary?.utenze.cf_invalido)} sub="Validazione formale" tone={(summary?.utenze.cf_invalido ?? 0) > 0 ? "danger" : "success"} />
              <StatCard label="Senza titolare" value={formatNumber(summary?.utenze.utenze_senza_titolare)} sub="Utenze senza intestatari" tone={(summary?.utenze.utenze_senza_titolare ?? 0) > 0 ? "warning" : "success"} />
              <StatCard label="Righe anomale" value={formatNumber(summary?.utenze.righe_con_anomalie)} sub="Almeno una anomalia import" tone={(summary?.utenze.righe_con_anomalie ?? 0) > 0 ? "warning" : "success"} />
            </div>
            <div className="mt-5 space-y-2">
              {(summary?.anomalie.by_tipo ?? []).slice(0, 5).map((item) => (
                <div key={item.key} className="flex items-center justify-between rounded-2xl border border-slate-100 bg-white px-4 py-3 text-sm">
                  <span className="font-medium text-slate-700">{item.label}</span>
                  <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700">{formatNumber(item.count)}</span>
                </div>
              ))}
              {!isLoading && (summary?.anomalie.by_tipo.length ?? 0) === 0 ? (
                <p className="rounded-2xl border border-dashed border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">Nessuna anomalia aperta per l&apos;anno selezionato.</p>
              ) : null}
            </div>
          </article>
        </div>

        <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
          <article className="panel-card">
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">Stato import</p>
            <h2 className="mt-1 text-xl font-semibold text-slate-950">Freschezza del dato</h2>
            <div className="mt-5 space-y-3">
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Ultimo completato</p>
                <p className="mt-2 font-semibold text-slate-900">{summary?.imports.latest_completed?.filename ?? "—"}</p>
                <p className="mt-1 text-sm text-slate-500">{formatDate(summary?.imports.latest_completed?.completed_at)} · anno {summary?.imports.latest_completed?.anno_campagna ?? "—"}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <StatCard label="Completati" value={formatNumber(summary?.imports.completed_batch)} sub="Batch import" tone="success" />
                <StatCard label="In corso" value={formatNumber(summary?.imports.processing_batch)} sub="Da monitorare" tone={(summary?.imports.processing_batch ?? 0) > 0 ? "warning" : "default"} />
                <StatCard label="Falliti" value={formatNumber(summary?.imports.failed_batch)} sub="Richiedono verifica" tone={(summary?.imports.failed_batch ?? 0) > 0 ? "danger" : "default"} />
              </div>
            </div>
          </article>

          <article className="panel-card overflow-hidden">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Distretti</p>
                <h2 className="mt-1 text-xl font-semibold text-slate-950">Priorità operative</h2>
                <p className="mt-1 text-sm text-slate-500">Ordinati per errori, anomalie e volume particelle.</p>
              </div>
              <Link className="text-sm font-medium text-[#1D4E35] underline underline-offset-2" href="/catasto/distretti">
                Lista completa
              </Link>
            </div>
            <div className="mt-5 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-[0.14em] text-slate-400">
                  <tr>
                    <th className="pb-3 pr-4 font-semibold">Distretto</th>
                    <th className="pb-3 pr-4 font-semibold">Particelle</th>
                    <th className="pb-3 pr-4 font-semibold">Utenze</th>
                    <th className="pb-3 pr-4 font-semibold">Anomalie</th>
                    <th className="pb-3 pr-4 font-semibold">Importo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {sortedDistretti.slice(0, 10).map((distretto) => (
                    <tr
                      key={distretto.distretto_id}
                      className="cursor-pointer transition hover:bg-emerald-50/70"
                      onClick={() => setSelectedDistretto(distretto)}
                    >
                      <td className="py-3 pr-4">
                        <p className="font-semibold text-slate-900">Distretto {distretto.num_distretto}</p>
                        <p className="max-w-[220px] truncate text-xs text-slate-500">{distretto.nome_distretto ?? "—"}</p>
                      </td>
                      <td className="py-3 pr-4 text-slate-700">{formatNumber(distretto.totale_particelle)}</td>
                      <td className="py-3 pr-4 text-slate-700">{formatNumber(distretto.totale_utenze)}</td>
                      <td className="py-3 pr-4">
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${distretto.anomalie_error > 0 ? "bg-rose-50 text-rose-700" : distretto.totale_anomalie_aperte > 0 ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"}`}>
                          {formatNumber(distretto.totale_anomalie_aperte)}
                        </span>
                      </td>
                      <td className="py-3 pr-4 font-medium text-slate-900">{formatEuro(distretto.importo_totale)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>
        </div>

        <CatastoWorkspaceModal
          open={selectedDistretto != null}
          href={selectedDistretto ? `/catasto/distretti/${selectedDistretto.distretto_id}` : null}
          title={selectedDistretto ? `Distretto ${selectedDistretto.num_distretto}` : "Dettaglio distretto"}
          description={selectedDistretto?.nome_distretto ?? "Dettaglio distretto aperto dalla dashboard Catasto."}
          onClose={() => setSelectedDistretto(null)}
        />
      </div>
    </CatastoPage>
  );
}
