"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { DocumentIcon } from "@/components/ui/icons";
import { getAvvisiBySubject } from "@/lib/ruolo-api";
import { catastoGetMeterReadingsBySubject, catastoListDistretti } from "@/lib/api/catasto";
import { getUtenzeSubjectPaymentNotices } from "@/lib/api";
import type { CatDistretto, CatMeterReading } from "@/types/catasto";
import type { AnagraficaPaymentNotice } from "@/types/api";
import type { RuoloAvvisoDetailResponse } from "@/types/ruolo";

type Props = {
  subjectId: string;
  token: string;
};

type YearSummary = {
  year: number;
  items: CatMeterReading[];
  totalConsumption: number;
  uniquePoints: number;
  warningCount: number;
  validatedCount: number;
  latestDate: string | null;
  associatedCost: number | null;
  costSource: "tariff_rules" | "ruolo_0985" | "payment_notices" | null;
  tariffCoverage: number;
};

const DISTRETTO_TARIFF_RULES = [
  {
    match: (distretto: CatDistretto | undefined) =>
      Boolean(distretto?.nome_distretto?.toLowerCase().includes("arborea") || distretto?.num_distretto === "25"),
    euroPerMc: 0.012,
    multiplier: 1.24,
    label: "Arborea",
  },
] as const;

function parseNumeric(value: string | number | null | undefined): number | null {
  if (value == null || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const normalized = Number(String(value).replace(/\./g, "").replace(",", "."));
  return Number.isFinite(normalized) ? normalized : null;
}

function formatEuro(value: number | null): string {
  if (value == null) return "-";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(value);
}

function formatConsumption(value: number | null): string {
  if (value == null) return "-";
  return `${new Intl.NumberFormat("it-IT", { maximumFractionDigits: 0 }).format(value)} mc`;
}

function readingConsumption(item: CatMeterReading): number | null {
  const explicitConsumption = parseNumeric(item.consumo_effettivo_mc ?? item.consumo_mc);
  if (explicitConsumption != null) {
    return explicitConsumption;
  }
  const start = parseNumeric(item.lettura_iniziale);
  const end = parseNumeric(item.lettura_finale);
  if (start == null || end == null || end < start) {
    return null;
  }
  return end - start;
}

function formatPerCubicMeter(cost: number | null, consumption: number): string {
  if (cost == null || consumption <= 0) return "-";
  return `${new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(cost / consumption)}/mc`;
}

function buildRoleCostByYear(avvisi: RuoloAvvisoDetailResponse[]): Map<number, number> {
  const yearly = new Map<number, number>();
  for (const item of avvisi) {
    const amount = item.importo_totale_0985;
    if (item.anno_tributario == null || amount == null) continue;
    yearly.set(item.anno_tributario, (yearly.get(item.anno_tributario) ?? 0) + amount);
  }
  return yearly;
}

function buildNoticeCostByYear(notices: AnagraficaPaymentNotice[]): Map<number, number> {
  const yearly = new Map<number, number>();
  for (const item of notices) {
    const year = Number(item.anno);
    const amount = parseNumeric(item.importo_carico);
    if (!Number.isFinite(year) || amount == null) continue;
    yearly.set(year, (yearly.get(year) ?? 0) + amount);
  }
  return yearly;
}

function buildYearSummaries(
  readings: CatMeterReading[],
  ruoloCosts: Map<number, number>,
  noticeCosts: Map<number, number>,
  distrettiById: Map<string, CatDistretto>,
): YearSummary[] {
  const buckets = new Map<number, CatMeterReading[]>();
  for (const item of readings) {
    if (item.record_kind !== "meter_reading") continue;
    const year = Number(item.anno);
    if (!Number.isFinite(year)) continue;
    const bucket = buckets.get(year) ?? [];
    bucket.push(item);
    buckets.set(year, bucket);
  }

  return Array.from(buckets.entries())
    .map(([year, items]) => {
      const sortedItems = [...items].sort((left, right) => {
        const leftDate = left.data_lettura ? new Date(left.data_lettura).getTime() : 0;
        const rightDate = right.data_lettura ? new Date(right.data_lettura).getTime() : 0;
        if (leftDate !== rightDate) return rightDate - leftDate;
        return left.punto_consegna.localeCompare(right.punto_consegna, "it");
      });
      const uniquePoints = new Set(sortedItems.map((item) => `${item.punto_consegna}::${item.matricola ?? ""}`)).size;
      const totalConsumption = sortedItems.reduce((sum, item) => sum + (readingConsumption(item) ?? 0), 0);
      const warningCount = sortedItems.filter((item) => item.validation_status === "warning").length;
      const validatedCount = sortedItems.filter((item) =>
        item.manual_audits.some((audit) => {
          const newValues = audit.new_values && !Array.isArray(audit.new_values) ? audit.new_values : null;
          return newValues?.validation_status === "valid";
        }),
      ).length;
      const latestDate = sortedItems.find((item) => item.data_lettura)?.data_lettura ?? null;
      let tariffCost = 0;
      let tariffCoverage = 0;
      for (const reading of sortedItems) {
        const consumption = readingConsumption(reading);
        if (consumption == null || consumption <= 0) continue;
        const distretto = reading.distretto_id ? distrettiById.get(reading.distretto_id) : undefined;
        const rule = DISTRETTO_TARIFF_RULES.find((candidate) => candidate.match(distretto));
        if (!rule) continue;
        tariffCost += consumption * rule.euroPerMc * rule.multiplier;
        tariffCoverage += 1;
      }
      const ruoloCost = ruoloCosts.get(year) ?? null;
      const noticeCost = noticeCosts.get(year) ?? null;
      const tariffRuleCost = tariffCoverage > 0 ? tariffCost : null;
      const costSource: YearSummary["costSource"] =
        tariffRuleCost != null
          ? "tariff_rules"
          : ruoloCost != null
            ? "ruolo_0985"
            : noticeCost != null
              ? "payment_notices"
              : null;

      return {
        year,
        items: sortedItems,
        totalConsumption,
        uniquePoints,
        warningCount,
        validatedCount,
        latestDate,
        associatedCost: tariffRuleCost ?? ruoloCost ?? noticeCost,
        costSource,
        tariffCoverage,
      };
    })
    .sort((left, right) => right.year - left.year);
}

function statusTone(item: CatMeterReading): string {
  if (item.validation_status === "error") return "bg-rose-50 text-rose-700";
  if (item.validation_status === "warning") return "bg-amber-50 text-amber-700";
  return "bg-emerald-50 text-emerald-700";
}

function statusLabel(item: CatMeterReading): string {
  if (item.validation_status === "error") return "Errore";
  if (item.validation_status === "warning") return "Warning";
  return "Valida";
}

export function UtenzeMeterReadingsSection({ subjectId, token }: Props) {
  const [readings, setReadings] = useState<CatMeterReading[]>([]);
  const [distretti, setDistretti] = useState<CatDistretto[]>([]);
  const [paymentNotices, setPaymentNotices] = useState<AnagraficaPaymentNotice[]>([]);
  const [ruoloAvvisi, setRuoloAvvisi] = useState<RuoloAvvisoDetailResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ruoloAccessMissing, setRuoloAccessMissing] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      setRuoloAccessMissing(false);

      try {
        const [readingsResult, noticesResult, ruoloResult, distrettiResult] = await Promise.allSettled([
          catastoGetMeterReadingsBySubject(token, subjectId),
          getUtenzeSubjectPaymentNotices(token, subjectId),
          getAvvisiBySubject(token, subjectId),
          catastoListDistretti(token),
        ]);

        if (cancelled) return;

        if (readingsResult.status === "fulfilled") {
          setReadings(readingsResult.value);
        } else {
          throw readingsResult.reason;
        }

        if (noticesResult.status === "fulfilled") {
          setPaymentNotices(noticesResult.value);
        } else {
          setPaymentNotices([]);
        }

        if (ruoloResult.status === "fulfilled") {
          setRuoloAvvisi(ruoloResult.value);
        } else {
          const message = ruoloResult.reason instanceof Error ? ruoloResult.reason.message : String(ruoloResult.reason);
          if (message.includes("403") || message.includes("Module access")) {
            setRuoloAccessMissing(true);
            setRuoloAvvisi([]);
          } else {
            throw ruoloResult.reason;
          }
        }

        if (distrettiResult.status === "fulfilled") {
          setDistretti(distrettiResult.value);
        } else {
          setDistretti([]);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Errore caricamento letture contatori soggetto");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [subjectId, token]);

  const distrettiById = useMemo(() => new Map(distretti.map((item) => [item.id, item])), [distretti]);

  const yearSummaries = useMemo(
    () => buildYearSummaries(readings, buildRoleCostByYear(ruoloAvvisi), buildNoticeCostByYear(paymentNotices), distrettiById),
    [readings, ruoloAvvisi, paymentNotices, distrettiById],
  );

  if (loading) {
    return (
      <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-panel">
        <p className="text-sm text-gray-500">Caricamento letture contatori del soggetto...</p>
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

  if (yearSummaries.length === 0) {
    return (
      <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-panel">
        <p className="text-sm text-gray-500">Nessuna lettura contatore collegata a questo soggetto.</p>
      </section>
    );
  }

  const latestYear = yearSummaries[0];
  const totalYears = yearSummaries.length;
  const totalReadings = yearSummaries.reduce((sum, item) => sum + item.items.length, 0);
  const totalWarnings = yearSummaries.reduce((sum, item) => sum + item.warningCount, 0);

  return (
    <section className="space-y-4">
      <ModuleWorkspaceHero
        compact
        badge={
          <>
            <DocumentIcon className="h-3.5 w-3.5" />
            Letture
          </>
        }
        title={`Ultimo anno disponibile: ${latestYear.year}`}
        description="Cruscotto storico annuale delle letture contatori collegate al soggetto, con consumo aggregato e costo economico associato quando disponibile."
        actions={
          <>
            <ModuleWorkspaceNoticeCard
              compact
              title={`Consumo ${latestYear.year}`}
              description={formatConsumption(latestYear.totalConsumption)}
              tone="success"
            />
            <ModuleWorkspaceNoticeCard
              compact
              title={`Costo associato ${latestYear.year}`}
              description={formatEuro(latestYear.associatedCost)}
              tone="warning"
            />
          </>
        }
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <ModuleWorkspaceMiniStat
            compact
            eyebrow="Ultimo anno"
            value={formatConsumption(latestYear.totalConsumption)}
            description={`${latestYear.uniquePoints} punti/contatori su ${latestYear.items.length} letture`}
            tone="success"
          />
          <ModuleWorkspaceMiniStat
            compact
            eyebrow="Costo ultimo anno"
            value={formatEuro(latestYear.associatedCost)}
            description={
              latestYear.costSource === "tariff_rules"
                ? `Tariffa distrettuale stimata - medio ${formatPerCubicMeter(latestYear.associatedCost, latestYear.totalConsumption)}`
                : latestYear.costSource === "ruolo_0985"
                ? `Voce Ruolo 0985 - medio ${formatPerCubicMeter(latestYear.associatedCost, latestYear.totalConsumption)}`
                : latestYear.costSource === "payment_notices"
                  ? `Fallback carico avvisi - medio ${formatPerCubicMeter(latestYear.associatedCost, latestYear.totalConsumption)}`
                  : "Nessun costo economico disponibile"
            }
            tone="warning"
          />
          <ModuleWorkspaceMiniStat
            compact
            eyebrow="Anni storici"
            value={totalYears}
            description={`${totalReadings} letture collegate nello storico`}
          />
          <ModuleWorkspaceMiniStat
            compact
            eyebrow="Warning aperti"
            value={totalWarnings}
            description="Somma delle letture ancora in warning nello storico disponibile"
            tone={totalWarnings > 0 ? "warning" : "default"}
          />
        </div>
      </ModuleWorkspaceHero>

      {ruoloAccessMissing ? (
        <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Il modulo Ruolo non e accessibile con l&apos;utente corrente: il costo associato usa il fallback dagli avvisi di pagamento quando presente.
        </div>
      ) : null}

      <div className="space-y-3">
        {yearSummaries.map((summary) => (
          <article key={summary.year} className="rounded-[24px] border border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] px-4 py-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-lg font-semibold text-gray-900">{summary.year}</p>
                  {summary.year === latestYear.year ? (
                    <span className="rounded-full bg-[#eef3ec] px-2.5 py-1 text-xs font-medium text-[#1D4E35]">Anno piu recente</span>
                  ) : null}
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  {summary.latestDate ? `Ultima lettura ${summary.latestDate}` : "Data ultima lettura non disponibile"}
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Costo associato</p>
                <p className="mt-1 text-sm font-semibold text-gray-900">{formatEuro(summary.associatedCost)}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {summary.costSource === "tariff_rules"
                    ? `Fonte tariffa distrettuale (${summary.tariffCoverage}/${summary.items.length} letture)`
                    : summary.costSource === "ruolo_0985"
                    ? "Fonte Ruolo 0985"
                    : summary.costSource === "payment_notices"
                      ? "Fallback avvisi pagamento"
                      : "Nessuna fonte economica"}
                </p>
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-4">
              <ModuleWorkspaceMiniStat compact eyebrow="Consumo" value={formatConsumption(summary.totalConsumption)} description="Totale annuo delle letture contatore." tone="success" />
              <ModuleWorkspaceMiniStat compact eyebrow="Punti/contatori" value={summary.uniquePoints} description={`${summary.items.length} letture registrate nell'anno.`} />
              <ModuleWorkspaceMiniStat compact eyebrow="Warning" value={summary.warningCount} description="Letture ancora da confermare o correggere." tone={summary.warningCount > 0 ? "warning" : "default"} />
              <ModuleWorkspaceMiniStat compact eyebrow="Validate manualmente" value={summary.validatedCount} description={`Medio ${formatPerCubicMeter(summary.associatedCost, summary.totalConsumption)}`} />
            </div>

            <div className="mt-4 space-y-3">
              {summary.items.map((item) => (
                <div key={item.id} className="rounded-2xl border border-gray-100 bg-white px-4 py-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate text-sm font-semibold text-gray-900">{item.punto_consegna}</p>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusTone(item)}`}>{statusLabel(item)}</span>
                        {item.manual_audits.some((audit) => {
                          const newValues = audit.new_values && !Array.isArray(audit.new_values) ? audit.new_values : null;
                          return newValues?.validation_status === "valid";
                        }) ? (
                          <span className="rounded-full bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-700">Validata manualmente</span>
                        ) : null}
                      </div>
                      <p className="mt-1 text-xs text-gray-500">
                        Matricola {item.matricola || "-"} - {item.data_lettura || "Data non disponibile"} - {item.tariffa || "Tariffa non disponibile"}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Consumo</p>
                      <p className="mt-1 text-sm font-semibold text-gray-900">{formatConsumption(readingConsumption(item))}</p>
                    </div>
                  </div>
                  {(item.intervento_da_eseguire || item.validation_messages.length > 0) ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.intervento_da_eseguire ? (
                        <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">Intervento: {item.intervento_da_eseguire}</span>
                      ) : null}
                      {item.validation_messages
                        .filter((message) => message.level === "warning")
                        .slice(0, 2)
                        .map((message) => (
                          <span key={`${item.id}-${message.code}`} className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700">
                            {message.message}
                          </span>
                        ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>

      <div className="flex justify-end">
        <Link className="btn-secondary" href="/catasto/letture-contatori">
          Apri registro completo Catasto
        </Link>
      </div>
    </section>
  );
}
