"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { DocumentIcon, GridIcon } from "@/components/ui/icons";
import { listSubjectDomandeIrrigue } from "@/lib/catasto-domande-irrigue-subject-api";
import { formatDateTime } from "@/lib/presentation";
import type { CatDomandaIrrigua, CatDomandaIrriguaParticella, CatDomandeIrrigueListResponse } from "@/types/catasto";

type Props = {
  subjectId: string;
  token: string;
  utenzaId?: string | null;
};

type SubjectDomandeIrrigueSummary = {
  domandeCount: number;
  particelleCount: number;
  totalSupIrrMq: number | null;
  totalSupRichiestaMq: number | null;
  totalBonusMq: number | null;
  totalMalusMq: number | null;
  availableYears: number[];
  latestActivityAt: string | null;
};

const SUBJECT_DOMANDE_LIMIT = 120;

export function parseDomandaDecimal(value: string | null | undefined): number | null {
  if (value == null || value === "") return null;
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatDomandaArea(value: string | number | null | undefined): string {
  const parsed = typeof value === "number" ? value : parseDomandaDecimal(value);
  if (parsed == null) return "-";
  return `${parsed.toLocaleString("it-IT", { maximumFractionDigits: 2 })} mq`;
}

export function formatDomandaMoney(value: string | null | undefined): string {
  const parsed = parseDomandaDecimal(value);
  if (parsed == null) return "-";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(parsed);
}

export function domandaStatusClassName(status: string | null): string {
  const normalized = (status ?? "").toLowerCase();
  if (normalized.includes("apert") || normalized.includes("aggiornat")) return "bg-emerald-50 text-emerald-700 ring-emerald-200";
  if (normalized.includes("rettificat")) return "bg-amber-50 text-amber-700 ring-amber-200";
  if (normalized.includes("annull") || normalized.includes("chius")) return "bg-slate-50 text-slate-600 ring-slate-200";
  return "bg-sky-50 text-sky-700 ring-sky-200";
}

export function summarizeSubjectDomandeIrrigue(items: CatDomandaIrrigua[]): SubjectDomandeIrrigueSummary {
  let particelleCount = 0;
  let totalSupIrrMq = 0;
  let totalSupRichiestaMq = 0;
  let totalBonusMq = 0;
  let totalMalusMq = 0;
  let hasSupIrr = false;
  let hasSupRichiesta = false;
  let hasBonus = false;
  let hasMalus = false;
  let latestTimestamp = 0;
  const years = new Set<number>();

  for (const domanda of items) {
    particelleCount += domanda.particelle.length;
    years.add(domanda.anno);

    const supIrr = parseDomandaDecimal(domanda.tot_sup_irr_mq);
    if (supIrr != null) {
      hasSupIrr = true;
      totalSupIrrMq += supIrr;
    }

    const supRichiesta = parseDomandaDecimal(domanda.tot_sup_richiesta_mq);
    if (supRichiesta != null) {
      hasSupRichiesta = true;
      totalSupRichiestaMq += supRichiesta;
    }

    const bonus = parseDomandaDecimal(domanda.tot_sup_bonus_mq);
    if (bonus != null) {
      hasBonus = true;
      totalBonusMq += bonus;
    }

    const malus = parseDomandaDecimal(domanda.tot_sup_malus_mq);
    if (malus != null) {
      hasMalus = true;
      totalMalusMq += malus;
    }

    const activityDate = domanda.data_agg ?? domanda.data_rett ?? domanda.data_ins;
    if (activityDate) {
      const timestamp = new Date(activityDate).getTime();
      if (Number.isFinite(timestamp) && timestamp > latestTimestamp) {
        latestTimestamp = timestamp;
      }
    }
  }

  return {
    domandeCount: items.length,
    particelleCount,
    totalSupIrrMq: hasSupIrr ? totalSupIrrMq : null,
    totalSupRichiestaMq: hasSupRichiesta ? totalSupRichiestaMq : null,
    totalBonusMq: hasBonus ? totalBonusMq : null,
    totalMalusMq: hasMalus ? totalMalusMq : null,
    availableYears: Array.from(years).sort((left, right) => right - left),
    latestActivityAt: latestTimestamp > 0 ? new Date(latestTimestamp).toISOString() : null,
  };
}

function isModuleAccessError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error);
  return message.includes("403") || message.includes("Module access");
}

function normalizeLoadError(error: unknown): string {
  return error instanceof Error ? error.message : "Errore caricamento domande irrigue";
}

export function detailKey(detail: CatDomandaIrriguaParticella): string {
  return [detail.foglio || "-", detail.particella || "-", detail.sub || "-"].join("/");
}

export function contextLabel(domanda: CatDomandaIrrigua): string {
  return [domanda.cco, domanda.com, domanda.pvc, domanda.fra, domanda.ccs].filter(Boolean).join(" / ") || "-";
}

export function yearsLabel(years: number[]): string {
  return years.length === 0 ? "N/D" : years.join(", ");
}

export function UtenzeDomandeIrrigueSection({ subjectId, token, utenzaId = null }: Props) {
  const [payload, setPayload] = useState<CatDomandeIrrigueListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [catastoAccessMissing, setCatastoAccessMissing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setCatastoAccessMissing(false);
    setPayload(null);

    listSubjectDomandeIrrigue(token, subjectId, { utenzaId, limit: SUBJECT_DOMANDE_LIMIT, offset: 0 })
      .then((response) => {
        /* v8 ignore next -- evita setState dopo un cambio rapido di soggetto o unmount. */
        if (cancelled) return;
        setPayload(response);
      })
      .catch((loadError: unknown) => {
        /* v8 ignore next -- evita setState dopo un cambio rapido di soggetto o unmount. */
        if (cancelled) return;
        if (isModuleAccessError(loadError)) {
          setCatastoAccessMissing(true);
          return;
        }
        setError(normalizeLoadError(loadError));
      })
      .finally(() => {
        /* v8 ignore next -- evita setState dopo un cambio rapido di soggetto o unmount. */
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [subjectId, token, utenzaId]);

  if (loading) {
    return (
      <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-panel">
        <p className="text-sm text-gray-500">{utenzaId ? "Caricamento domande irrigue dell'utenza..." : "Caricamento domande irrigue del soggetto..."}</p>
      </section>
    );
  }

  if (catastoAccessMissing) {
    return (
      <section className="rounded-[28px] border border-amber-200 bg-amber-50 p-5 text-sm text-amber-800 shadow-panel">
        Il modulo Catasto non e accessibile con l&apos;utente corrente: le domande irrigue non sono disponibili.
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-[28px] border border-red-200 bg-red-50 p-5 text-sm text-red-700 shadow-panel">
        {error}
      </section>
    );
  }

  const items = payload?.items ?? [];
  if (items.length === 0) {
    return (
      <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-panel">
        <p className="text-sm text-gray-500">
          {utenzaId
            ? "Nessuna domanda irrigua importata risulta collegata a questa utenza."
            : "Nessuna domanda irrigua importata risulta collegata a questo soggetto."}
        </p>
      </section>
    );
  }

  const summary = summarizeSubjectDomandeIrrigue(items);
  const shownLimitWarning = payload != null && payload.total > items.length;

  return (
    <section className="space-y-4">
      <ModuleWorkspaceHero
        compact
        badge={
          <>
            <DocumentIcon className="h-3.5 w-3.5" />
            Domande irrigue
          </>
        }
        title={utenzaId ? "Domande irrigue Capacitas dell'utenza" : "Domande irrigue Capacitas"}
        description={
          utenzaId
            ? "Domande collegate alla specifica utenza consortile tramite matching Capacitas. Le righe particella riportano colture, superfici e contesto CCO/COM/PVC/FRA/CCS importato."
            : "Domande collegate al soggetto GAIA tramite matching Capacitas. Le righe particella riportano colture, superfici e contesto CCO/COM/PVC/FRA/CCS importato."
        }
        actions={
          <>
            <ModuleWorkspaceNoticeCard compact title="Superficie irrigata" description={formatDomandaArea(summary.totalSupIrrMq)} tone="success" />
            <ModuleWorkspaceNoticeCard compact title="Ultima attivita" description={summary.latestActivityAt ? formatDateTime(summary.latestActivityAt) : "-"} tone="warning" />
          </>
        }
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <ModuleWorkspaceMiniStat compact eyebrow="Domande" value={summary.domandeCount} description={`Annualita: ${yearsLabel(summary.availableYears)}`} />
          <ModuleWorkspaceMiniStat compact eyebrow="Particelle dichiarate" value={summary.particelleCount} description="Righe dettaglio importate da domandeIrrigaz.aspx" tone="success" />
          <ModuleWorkspaceMiniStat compact eyebrow="Superficie richiesta" value={formatDomandaArea(summary.totalSupRichiestaMq)} description="Totale richiesto sulle testate domanda" tone="success" />
          <ModuleWorkspaceMiniStat compact eyebrow="Bonus / Malus" value={`${formatDomandaArea(summary.totalBonusMq)} / ${formatDomandaArea(summary.totalMalusMq)}`} description="Superfici rettifica salvate da Capacitas" tone="warning" />
        </div>
      </ModuleWorkspaceHero>

      {shownLimitWarning ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Visualizzate {items.length} domande su {payload.total}. Apri il registro Catasto per una consultazione paginata completa.
        </div>
      ) : null}

      <div className="space-y-3">
        {items.map((domanda) => (
          <article key={domanda.id} className="overflow-hidden rounded-[24px] border border-[#e4ebe2] bg-white shadow-sm">
            <div className="flex flex-col gap-3 border-b border-[#edf1eb] bg-[#fbfcfa] p-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-[#eef3ec] px-3 py-1 text-xs font-semibold text-[#1D4E35]">{domanda.anno}</span>
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${domandaStatusClassName(domanda.stato)}`}>
                    {domanda.stato || "Stato non indicato"}
                  </span>
                  {domanda.autorinnovo ? <span className="rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700">Autorinnovo</span> : null}
                </div>
                <h3 className="mt-3 text-lg font-semibold text-gray-950">Domanda {domanda.domanda_numero || domanda.external_id || domanda.id}</h3>
                <p className="mt-1 text-sm text-gray-500">
                  {domanda.tipo || "Tipo non indicato"} / {domanda.comune || "Comune non indicato"} / Contesto {contextLabel(domanda)}
                </p>
              </div>
              <div className="grid gap-2 text-sm sm:grid-cols-3 lg:min-w-[420px]">
                <div className="rounded-2xl border border-gray-100 bg-white px-3 py-2">
                  <p className="text-xs uppercase tracking-widest text-gray-400">Sup. irrigata</p>
                  <p className="mt-1 font-semibold text-gray-900">{formatDomandaArea(domanda.tot_sup_irr_mq)}</p>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-white px-3 py-2">
                  <p className="text-xs uppercase tracking-widest text-gray-400">Ruolo irr.</p>
                  <p className="mt-1 font-semibold text-gray-900">{formatDomandaMoney(domanda.ruolo_irr)}</p>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-white px-3 py-2">
                  <p className="text-xs uppercase tracking-widest text-gray-400">Aggiornata</p>
                  <p className="mt-1 font-semibold text-gray-900">{formatDateTime(domanda.data_agg ?? domanda.data_rett ?? domanda.data_ins)}</p>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-100 text-sm">
                <thead className="bg-white text-left text-xs uppercase tracking-wider text-gray-400">
                  <tr>
                    <th className="px-4 py-3">Particella</th>
                    <th className="px-4 py-3">Coltura</th>
                    <th className="px-4 py-3">Sup. catastale</th>
                    <th className="px-4 py-3">Sup. irrigata</th>
                    <th className="px-4 py-3">Ruolo irr.</th>
                    <th className="px-4 py-3">Contesto riga</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {domanda.particelle.length === 0 ? (
                    <tr>
                      <td className="px-4 py-4 text-sm text-gray-500" colSpan={6}>
                        Nessun dettaglio particella importato per questa domanda.
                      </td>
                    </tr>
                  ) : (
                    domanda.particelle.slice(0, 8).map((detail) => (
                      <tr key={detail.id} className="align-top">
                        <td className="px-4 py-3 font-medium text-gray-900">{detailKey(detail)}</td>
                        <td className="px-4 py-3 text-gray-700">{detail.coltura || "-"}</td>
                        <td className="px-4 py-3 text-gray-700">{formatDomandaArea(detail.sup_cat_mq)}</td>
                        <td className="px-4 py-3 text-gray-700">{formatDomandaArea(detail.sup_irr_mq)}</td>
                        <td className="px-4 py-3 text-gray-700">{formatDomandaMoney(detail.ruolo_irr)}</td>
                        <td className="px-4 py-3 text-gray-500">
                          {[detail.part_cco, detail.part_com, detail.part_pvc, detail.part_fra, detail.part_ccs].filter(Boolean).join(" / ") || "-"}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {domanda.particelle.length > 8 ? (
              <div className="border-t border-gray-100 px-4 py-3 text-sm text-gray-500">
                Mostrate 8 particelle su {domanda.particelle.length}. Usa il registro Catasto per il dettaglio completo.
              </div>
            ) : null}
          </article>
        ))}
      </div>

      <div className="flex justify-end">
        <Link className="inline-flex items-center gap-2 rounded-xl border border-[#d9e8df] bg-white px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50" href="/catasto/domande-irrigue">
          <GridIcon className="h-4 w-4" />
          Apri registro domande
        </Link>
      </div>
    </section>
  );
}
