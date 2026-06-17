"use client";

import { useEffect, useMemo, useState } from "react";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import {
  formatRuoloCapacitasDiagnosis,
  getRuoloCapacitasDiagnosisBadgeClassName,
} from "@/components/ruolo/capacitas-check-details";
import { RuoloCapacitasCalculationModal } from "@/components/ruolo/capacitas-calculation-modal";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, CalendarIcon, LockIcon, SearchIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import {
  buildRuoloGaiaCalculationExportUrl,
  getRuoloCapacitasCalculationDetail,
  getRuoloGaiaCalculation,
  getRuoloStats,
} from "@/lib/ruolo-api";
import type {
  RuoloCapacitasCalculationDetailResponse,
  RuoloCapacitasCheckItemResponse,
  RuoloGaiaCalculationItemResponse,
  RuoloGaiaCalculationResponse,
  RuoloStatsByAnnoResponse,
} from "@/types/ruolo";

function formatEuro(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function formatInteger(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT").format(value);
}

function toCalculationModalItem(item: RuoloGaiaCalculationItemResponse): RuoloCapacitasCheckItemResponse {
  return {
    tax_code: item.tax_code,
    ruolo_display_name: item.ruolo_display_name,
    capacitas_display_name: item.display_name,
    status: item.status,
    diagnosis: item.diagnosis,
    ruolo_0648: item.ruolo_0648,
    gaia_0648: item.gaia_0648,
    excel_0648: item.excel_0648,
    delta_0648: item.ruolo_0648 - item.gaia_0648,
    delta_gaia_excel_0648: item.gaia_0648 - item.excel_0648,
    ruolo_0985: item.ruolo_0985,
    gaia_0985: item.gaia_0985,
    excel_0985: item.excel_0985,
    delta_0985: item.ruolo_0985 - item.gaia_0985,
    delta_gaia_excel_0985: item.gaia_0985 - item.excel_0985,
    ruolo_totale_confrontabile: item.ruolo_totale_confrontabile,
    gaia_totale_confrontabile: item.gaia_total,
    excel_totale_confrontabile: item.excel_total,
    delta_totale_confrontabile: item.delta_ruolo_gaia_totale,
    delta_gaia_excel_totale_confrontabile: item.gaia_total - item.excel_total,
    anomalous_rows_count: item.anomalous_rows_count,
    clean_rows_count: item.clean_rows_count,
    anomaly_gap_share: item.anomaly_gap_share,
    anomaly_driven_case: item.anomaly_driven_case,
  };
}

export default function RuoloGaiaCalculationPage() {
  const [token, setToken] = useState<string | null>(null);
  const [stats, setStats] = useState<RuoloStatsByAnnoResponse[]>([]);
  const [selectedAnno, setSelectedAnno] = useState<number | null>(null);
  const [calculation, setCalculation] = useState<RuoloGaiaCalculationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingCalculation, setLoadingCalculation] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [taxCodeFilter, setTaxCodeFilter] = useState("");
  const [onlyAnomalous, setOnlyAnomalous] = useState(false);
  const [selectedItem, setSelectedItem] = useState<RuoloCapacitasCheckItemResponse | null>(null);
  const [detail, setDetail] = useState<RuoloCapacitasCalculationDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    getRuoloStats(token)
      .then((response) => {
        const items = [...response.items].sort((left, right) => right.anno_tributario - left.anno_tributario);
        setStats(items);
        setSelectedAnno(items[0]?.anno_tributario ?? null);
      })
      .catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento annualita"))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    if (!token || selectedAnno == null) return;
    setLoadingCalculation(true);
    setError(null);
    getRuoloGaiaCalculation(token, selectedAnno, {
      limit: 200,
      taxCode: taxCodeFilter.trim() || undefined,
      anomalousOnly: onlyAnomalous,
    })
      .then((gaiaData) => {
        setCalculation(gaiaData);
      })
      .catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento calcolo GAIA"))
      .finally(() => setLoadingCalculation(false));
  }, [token, selectedAnno, taxCodeFilter, onlyAnomalous]);

  const availableYears = useMemo(
    () => [...stats].sort((left, right) => right.anno_tributario - left.anno_tributario),
    [stats],
  );
  const unifiedRows = useMemo(() => calculation?.items ?? [], [calculation]);
  const exportUrl = useMemo(() => {
    if (selectedAnno == null || !token) return null;
    const baseUrl = buildRuoloGaiaCalculationExportUrl(selectedAnno, {
      limit: 100000,
      taxCode: taxCodeFilter.trim() || undefined,
      anomalousOnly: onlyAnomalous,
    });
    return `${baseUrl}&token=${token}`;
  }, [onlyAnomalous, selectedAnno, taxCodeFilter, token]);

  async function openCalculationDetail(item: RuoloGaiaCalculationItemResponse): Promise<void> {
    if (!token || selectedAnno == null) return;
    setSelectedItem(toCalculationModalItem(item));
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      const response = await getRuoloCapacitasCalculationDetail(token, selectedAnno, item.tax_code);
      setDetail(response);
    } catch (loadError) {
      setDetailError(loadError instanceof Error ? loadError.message : "Errore caricamento dettaglio calcolo");
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <RuoloModulePage
      title="Calcolo ruolo GAIA"
      description="Calcolo atteso GAIA su batch Capacitas attivo, separato dal confronto col ruolo pubblicato."
      breadcrumb="Calcolo ruolo GAIA"
      requiredSection="ruolo.stats"
      topbarActions={
        exportUrl ? (
          <a
            href={exportUrl}
            className="rounded-xl border border-[#d6e5db] bg-white px-4 py-2 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
            download={`ruolo_calcolo_gaia_${selectedAnno}.csv`}
          >
            Esporta CSV
          </a>
        ) : undefined
      }
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
                  Motore di calcolo
                </>
              }
              title="Calcolo atteso GAIA su base Capacitas attiva."
              description="Questa vista mostra il calcolo 0648 e 0985 derivato da imponibile e aliquote del batch Capacitas attivo, separato dal ruolo pubblicato e dallo snapshot Excel."
              actions={
                <>
                  <ModuleWorkspaceNoticeCard
                    title={selectedAnno != null ? `Annualita: ${selectedAnno}` : "Nessuna annualita"}
                    description="Il dataset e costruito solo dal batch Capacitas attivo dell'anno selezionato."
                    tone={selectedAnno != null ? "info" : "warning"}
                  />
                  <ModuleWorkspaceNoticeCard
                    title={calculation ? `${formatInteger(calculation.summary.positions)} posizioni calcolate` : "Calcolo in caricamento"}
                    description={calculation ? `${formatInteger(calculation.summary.anomaly_driven_positions)} casi guidati da anomalie. ${formatInteger(calculation.summary.mismatch_positions)} mismatch verso il ruolo.` : "Il motore carichera posizioni, totali e breakdown anomali."}
                    tone={(calculation?.summary.anomaly_driven_positions ?? 0) > 0 ? "warning" : "success"}
                  />
                </>
              }
            >
              <ModuleWorkspaceKpiRow>
                <ModuleWorkspaceKpiTile label="GAIA totale" value={formatEuro(calculation?.summary.gaia_totale_confrontabile ?? null)} hint="Somma attesa 0648 + 0985" />
                <ModuleWorkspaceKpiTile label="Ruolo totale" value={formatEuro(calculation?.summary.ruolo_totale_confrontabile ?? null)} hint="Somma pubblicata lato ruolo su 0648 + 0985" />
                <ModuleWorkspaceKpiTile label="Excel totale" value={formatEuro(calculation?.summary.excel_totale_confrontabile ?? null)} hint="Snapshot importato dal batch attivo" />
                <ModuleWorkspaceKpiTile label="Gap Excel/GAIA" value={formatEuro(calculation?.summary.gap_excel_gaia_totale ?? null)} hint="Excel meno calcolo GAIA" variant={(calculation?.summary.gap_excel_gaia_totale ?? 0) !== 0 ? "amber" : "default"} />
                <ModuleWorkspaceKpiTile label="Gap ruolo/GAIA" value={formatEuro(calculation?.summary.delta_ruolo_gaia_totale ?? null)} hint="Ruolo meno calcolo GAIA" variant={(calculation?.summary.delta_ruolo_gaia_totale ?? 0) !== 0 ? "amber" : "default"} />
                <ModuleWorkspaceKpiTile label="Superficie" value={calculation ? `${formatInteger(Math.round(calculation.summary.total_sup_irrigabile_mq))} mq` : "—"} hint="Somma superfici irrigabili del batch attivo" />
              </ModuleWorkspaceKpiRow>
            </ModuleWorkspaceHero>

            <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
              <div className="grid gap-4 lg:grid-cols-[220px,1fr,auto]">
                <label>
                  <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Anno tributario</span>
                  <select
                    value={selectedAnno ?? ""}
                    onChange={(event) => setSelectedAnno(event.target.value ? Number(event.target.value) : null)}
                    className="w-full rounded-xl border border-[#d8dfd3] bg-white px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                  >
                    {availableYears.map((item) => (
                      <option key={item.anno_tributario} value={item.anno_tributario}>
                        {item.anno_tributario}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">CF / P.IVA</span>
                  <input
                    value={taxCodeFilter}
                    onChange={(event) => setTaxCodeFilter(event.target.value)}
                    placeholder="Filtra per codice fiscale o partita IVA"
                    className="w-full rounded-xl border border-[#d8dfd3] bg-white px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                  />
                </label>
                <label className="inline-flex items-center gap-2 self-end rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900">
                  <input
                    type="checkbox"
                    checked={onlyAnomalous}
                    onChange={(event) => setOnlyAnomalous(event.target.checked)}
                    className="h-4 w-4 rounded border-amber-300 text-amber-700 focus:ring-amber-500"
                  />
                  Solo guidati da anomalie
                </label>
              </div>
            </section>

            {loadingCalculation ? (
              <p className="text-sm text-gray-400">Caricamento calcolo GAIA...</p>
            ) : error ? (
              <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
            ) : !calculation || unifiedRows.length === 0 ? (
              <EmptyState
                icon={CalendarIcon}
                title="Nessun risultato"
                description={onlyAnomalous ? "Nessuna posizione guidata da anomalie per i filtri correnti." : "Non risultano posizioni calcolabili per l'anno o i filtri selezionati."}
              />
            ) : (
              <>
                <section className="grid gap-4 xl:grid-cols-4">
                  <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
                    <p className="section-title">Posizioni</p>
                    <p className="section-copy">{formatInteger(calculation.summary.positions)} soggetti con chiave fiscale valida nel batch attivo.</p>
                  </article>
                  <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
                    <p className="section-title">Posizioni anomale</p>
                    <p className="section-copy">{formatInteger(calculation.summary.anomalous_positions)} soggetti con almeno una riga anomala.</p>
                  </article>
                  <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
                    <p className="section-title">Guidati da anomalie</p>
                    <p className="section-copy">{formatInteger(calculation.summary.anomaly_driven_positions)} casi in cui almeno il 95% del gap nasce da righe anomale.</p>
                  </article>
                  <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
                    <p className="section-title">Chiavi mancanti</p>
                    <p className="section-copy">{formatInteger(calculation.summary.positions_missing_tax_code)} righe escluse dall&apos;aggregazione per assenza di CF/P.IVA utile.</p>
                  </article>
                </section>

                <section className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
                  <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
                    <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                      <SearchIcon className="h-3.5 w-3.5" />
                      Calcolo per soggetto
                    </p>
                    <p className="mt-3 text-lg font-semibold text-gray-900">Calcolo atteso GAIA confrontato con ruolo pubblicato ed Excel.</p>
                  </div>
                  <div className="overflow-x-auto p-6">
                    <table className="min-w-full divide-y divide-gray-200 text-sm">
                      <thead className="bg-gray-50 text-left text-xs uppercase tracking-[0.16em] text-gray-500">
                        <tr>
                          <th className="px-4 py-3">Soggetto</th>
                          <th className="px-4 py-3">Copertura</th>
                          <th className="px-4 py-3">Ruolo</th>
                          <th className="px-4 py-3">GAIA</th>
                          <th className="px-4 py-3">Excel</th>
                          <th className="px-4 py-3">Diagnosi</th>
                          <th className="px-4 py-3">Gap</th>
                          <th className="px-4 py-3">Segnale</th>
                          <th className="px-4 py-3">Azioni</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {unifiedRows.map((item) => (
                          <tr key={item.tax_code}>
                            <td className="px-4 py-3 align-top">
                              <p className="font-medium text-gray-900">{item.display_name ?? item.tax_code}</p>
                              <p className="text-xs text-gray-500">{item.tax_code}</p>
                            </td>
                            <td className="px-4 py-3 align-top text-xs text-gray-700">
                              <p>{item.rows_count} righe · {item.comuni_count} comuni</p>
                              <p>Anomale {item.anomalous_rows_count} · Pulite {item.clean_rows_count}</p>
                              <p>Sup. {formatInteger(Math.round(item.total_sup_irrigabile_mq))} mq</p>
                            </td>
                            <td className="px-4 py-3 align-top text-xs text-[#183325]">
                              <p>0648: <span className="font-semibold">{formatEuro(item.ruolo_0648)}</span></p>
                              <p>0985: <span className="font-semibold">{formatEuro(item.ruolo_0985)}</span></p>
                              <p>Totale: <span className="font-semibold">{formatEuro(item.ruolo_totale_confrontabile)}</span></p>
                            </td>
                            <td className="px-4 py-3 align-top text-xs text-sky-900">
                              <p>0648: <span className="font-semibold">{formatEuro(item.gaia_0648)}</span></p>
                              <p>0985: <span className="font-semibold">{formatEuro(item.gaia_0985)}</span></p>
                              <p>Totale: <span className="font-semibold">{formatEuro(item.gaia_total)}</span></p>
                            </td>
                            <td className="px-4 py-3 align-top text-xs text-gray-800">
                              <p>0648: <span className="font-semibold">{formatEuro(item.excel_0648)}</span></p>
                              <p>0985: <span className="font-semibold">{formatEuro(item.excel_0985)}</span></p>
                              <p>Totale: <span className="font-semibold">{formatEuro(item.excel_total)}</span></p>
                            </td>
                            <td className="px-4 py-3 align-top">
                              <div className="space-y-2">
                                <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${getRuoloCapacitasDiagnosisBadgeClassName(item.diagnosis)}`}>
                                  {formatRuoloCapacitasDiagnosis(item.diagnosis)}
                                </span>
                                <p className="text-xs text-gray-500">{item.status}</p>
                              </div>
                            </td>
                            <td className="px-4 py-3 align-top">
                              <p className="font-semibold text-amber-800">Excel/GAIA {formatEuro(item.gap_excel_gaia_total)}</p>
                              <p className="mt-1 text-xs text-gray-500">Ruolo/GAIA {formatEuro(item.delta_ruolo_gaia_totale)}</p>
                            </td>
                            <td className="px-4 py-3 align-top">
                              {item.anomaly_driven_case ? (
                                <div className="space-y-2">
                                  <span className="inline-flex rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800">
                                    Guidato da anomalie
                                  </span>
                                  <p className="text-xs text-gray-500">
                                    {item.anomalous_rows_count} righe anomale spiegano il {item.anomaly_gap_share.toLocaleString("it-IT", { maximumFractionDigits: 1 })}% del gap.
                                  </p>
                                </div>
                              ) : (
                                <p className="text-xs text-gray-500">
                                  {item.anomalous_rows_count > 0
                                    ? `${item.anomalous_rows_count} righe anomale, copertura gap ${item.anomaly_gap_share.toLocaleString("it-IT", { maximumFractionDigits: 1 })}%.`
                                    : "Nessun segnale anomalo prevalente."}
                                </p>
                              )}
                            </td>
                            <td className="px-4 py-3 align-top">
                              <button
                                type="button"
                                onClick={() => void openCalculationDetail(item)}
                                className="rounded-lg border border-fuchsia-200 bg-fuchsia-50 px-3 py-1.5 text-xs font-medium text-fuchsia-800 transition hover:bg-fuchsia-100"
                              >
                                Apri calcolo
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </>
            )}
          </>
        )}
      </div>

      <RuoloCapacitasCalculationModal
        open={selectedItem != null}
        item={selectedItem}
        detail={detail}
        loading={detailLoading}
        error={detailError}
        onClose={() => {
          setSelectedItem(null);
          setDetail(null);
          setDetailError(null);
          setDetailLoading(false);
        }}
      />
    </RuoloModulePage>
  );
}
