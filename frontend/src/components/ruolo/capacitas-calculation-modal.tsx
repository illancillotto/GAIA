"use client";

import { useState } from "react";

import type {
  RuoloCapacitasCalculationDetailResponse,
  RuoloCapacitasCalculationRowResponse,
  RuoloCapacitasCheckItemResponse,
} from "@/types/ruolo";

function formatEuro(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function formatDecimal(value: number | null, maximumFractionDigits = 2): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { maximumFractionDigits }).format(value);
}

function formatText(value: string | number | null | undefined): string {
  if (value == null || value === "") return "—";
  return String(value);
}

function getExcelRowSignals(row: RuoloCapacitasCalculationRowResponse): string[] {
  return [
    row.anomalia_superficie ? "Superficie" : null,
    row.anomalia_cf_invalido ? "CF invalido" : null,
    row.anomalia_cf_mancante ? "CF mancante" : null,
    row.anomalia_comune_invalido ? "Comune" : null,
    row.anomalia_particella_assente ? "Particella assente" : null,
    row.anomalia_imponibile ? "Imponibile" : null,
    row.anomalia_importi ? "Importi" : null,
  ].filter((value): value is string => value != null);
}

type RowGapKey =
  | "excel_gaia_lordo"
  | "ruolo_gaia_lordo"
  | "ruolo_excel_lordo";

type RowGapEntry = {
  key: RowGapKey;
  label: string;
  value: number | null;
};

function getRowGapEntries(row: RuoloCapacitasCalculationRowResponse): RowGapEntry[] {
  return [
    { key: "excel_gaia_lordo", label: "Excel/GAIA", value: row.gap_excel_gaia_total },
    { key: "ruolo_gaia_lordo", label: "Ruolo/GAIA", value: row.ruolo_match_found ? row.delta_ruolo_gaia_total : null },
    { key: "ruolo_excel_lordo", label: "Ruolo/Excel", value: row.ruolo_match_found ? row.delta_ruolo_excel_total : null },
  ];
}

function getLargestRowGap(row: RuoloCapacitasCalculationRowResponse): RowGapEntry | null {
  const largest = getRowGapEntries(row).reduce<RowGapEntry | null>((current, entry) => {
    if (entry.value == null) return current;
    if (current == null) return entry;
    return Math.abs(entry.value) > Math.abs(current.value ?? 0) ? entry : current;
  }, null);

  if (largest == null || largest.value == null || Math.abs(largest.value) < 0.01) return null;
  return largest;
}

function getRowGapClassName(key: RowGapKey, largestGap: RowGapEntry | null, defaultClassName: string): string {
  if (largestGap?.key !== key) return defaultClassName;
  return "rounded-lg border border-red-200 bg-red-50 px-2 py-1 font-semibold text-red-800";
}

function getRuoloMatchDescription(row: RuoloCapacitasCalculationRowResponse): string {
  if (!row.ruolo_match_found) return "Nessun match ruolo";
  if (row.ruolo_match_level === "without_sub") return "Match ruolo unico senza sub nello snapshot";
  return "Match ruolo esatto";
}

function getAmountRatio(numerator: number, denominator: number): number | null {
  if (denominator <= 0) return null;
  return numerator / denominator;
}

type Props = {
  open: boolean;
  item: RuoloCapacitasCheckItemResponse | null;
  detail: RuoloCapacitasCalculationDetailResponse | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
};

export function RuoloCapacitasCalculationModal({
  open,
  item,
  detail,
  loading,
  error,
  onClose,
}: Props) {
  const [excelPreviewOpen, setExcelPreviewOpen] = useState(false);

  if (!open || !item) return null;

  const summary = detail?.summary ?? null;
  const anomalyGap = summary
    ? Number((summary.excel_total_anomalous_rows - summary.gaia_total_anomalous_rows).toFixed(2))
    : 0;
  const cleanGap = summary
    ? Number((summary.excel_total_clean_rows - summary.gaia_total_clean_rows).toFixed(2))
    : 0;
  const anomalyGapShare = summary && Math.abs(summary.gap_excel_gaia_total) > 0
    ? Math.round((Math.abs(anomalyGap) / Math.abs(summary.gap_excel_gaia_total)) * 1000) / 10
    : 0;
  const cleanRowsAligned = Math.abs(cleanGap) <= 1;
  const anomalyDrivenCase = anomalyGapShare >= 95 && summary != null && summary.anomalous_rows_count > 0;
  const excelRows = detail?.rows ?? [];
  const sourceFilename = summary?.source_filename ?? excelRows.find((row) => row.source_filename)?.source_filename ?? null;

  return (
    <div className="fixed inset-0 z-[85] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
      <div className="flex max-h-[94vh] w-full max-w-[1500px] flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Dettaglio calcolo GAIA</p>
            <h2 className="mt-2 text-2xl font-semibold text-gray-900">{item.ruolo_display_name ?? item.capacitas_display_name ?? item.tax_code}</h2>
            <p className="mt-1 text-sm text-gray-500">
              {item.tax_code} · confronto tra calcolo GAIA, Excel Capacitas e valori ruolo/live sulle particelle del batch attivo.
              {summary?.capacitas_avviso_code ? ` Avviso CapaciTas ${summary.capacitas_avviso_code}.` : ""}
            </p>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            {detail && summary?.capacitas_url ? (
              <a
                className="rounded-xl border border-fuchsia-200 bg-fuchsia-50 px-4 py-2 text-sm font-medium text-fuchsia-800 transition hover:bg-white"
                href={summary.capacitas_url}
                target="_blank"
                rel="noreferrer"
              >
                Apri avviso CapaciTas
              </a>
            ) : null}
            {detail && summary ? (
              <button
                className="rounded-xl border border-[#d6e5db] bg-[#f3f8f5] px-4 py-2 text-sm font-medium text-[#1D4E35] transition hover:bg-white"
                type="button"
                onClick={() => setExcelPreviewOpen(true)}
              >
                Visualizza righe Excel
              </button>
            ) : null}
            <button className="btn-secondary" type="button" onClick={onClose}>
              Chiudi
            </button>
          </div>
        </div>

        <div className="overflow-y-auto bg-[#f4f7f5] px-6 py-6">
          {loading ? (
            <div className="rounded-2xl border border-gray-200 bg-white px-5 py-4 text-sm text-gray-500 shadow-sm">
              Caricamento dettaglio calcolo.
            </div>
          ) : error ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
              {error}
            </div>
          ) : !detail || !summary ? (
            <div className="rounded-2xl border border-gray-200 bg-white px-5 py-4 text-sm text-gray-500 shadow-sm">
              Nessun dettaglio disponibile.
            </div>
          ) : (
            <div className="space-y-6">
              <section className="grid gap-4 xl:grid-cols-[1.15fr,0.85fr]">
                <article className="rounded-[24px] border border-[#d8dfd3] bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Lettura operativa</p>
                  <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-2xl border border-[#e5ece6] bg-[#f9fbf9] p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500">Righe totali</p>
                      <p className="mt-2 text-lg font-semibold text-gray-900">{formatDecimal(summary.rows_count, 0)}</p>
                      <p className="mt-1 text-xs text-gray-500">Anomale {formatDecimal(summary.anomalous_rows_count, 0)} · Pulite {formatDecimal(summary.clean_rows_count, 0)}</p>
                    </div>
                    <div className="rounded-2xl border border-[#e5ece6] bg-[#f9fbf9] p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500">Superficie</p>
                      <p className="mt-2 text-lg font-semibold text-gray-900">{formatDecimal(summary.total_sup_irrigabile_mq, 0)} mq</p>
                      <p className="mt-1 text-xs text-gray-500">Imponibile totale {formatDecimal(summary.total_imponibile_sf)}</p>
                    </div>
                    <div className="rounded-2xl border border-[#dbe7f4] bg-[#f7fbff] p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-sky-700">Calcolo GAIA</p>
                      <p className="mt-2 text-lg font-semibold text-gray-900">{formatEuro(summary.gaia_total)}</p>
                      <p className="mt-1 text-xs text-gray-500">Righe anomale {formatEuro(summary.gaia_total_anomalous_rows)}</p>
                    </div>
                    <div className="rounded-2xl border border-[#efe1ef] bg-[#fff7fc] p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-fuchsia-700">Excel Capacitas</p>
                      <p className="mt-2 text-lg font-semibold text-gray-900">{formatEuro(summary.excel_total)}</p>
                      <p className="mt-1 text-xs text-gray-500">Righe anomale {formatEuro(summary.excel_total_anomalous_rows)}</p>
                    </div>
                  </div>
                </article>

                <article className="rounded-[24px] border border-[#d8dfd3] bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Indicatori del calcolo</p>
                  <div className="mt-4 space-y-4">
                    <div>
                      <p className="text-sm font-medium text-gray-900">Delta Excel Capacitas meno calcolo GAIA</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">{formatEuro(summary.gap_excel_gaia_total)}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">Indici spese fisse osservati</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {summary.distinct_ind_spese_fisse.map((value) => (
                          <span key={value} className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs font-medium text-gray-700">
                            {formatDecimal(value, 4)}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">Valori imponibile/mq osservati</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {summary.distinct_imponibile_per_mq.map((value) => (
                          <span key={value} className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs font-medium text-gray-700">
                            {formatDecimal(value, 4)}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className={`rounded-2xl border px-4 py-3 ${anomalyDrivenCase ? "border-amber-200 bg-amber-50" : "border-gray-200 bg-gray-50"}`}>
                      <p className="text-sm font-medium text-gray-900">Esito operativo</p>
                      <p className="mt-1 text-sm text-gray-700">
                        {anomalyDrivenCase
                          ? `${formatDecimal(anomalyGapShare, 1)}% del gap Excel/GAIA arriva da righe gia marcate anomale.`
                          : `Le righe anomale spiegano ${formatDecimal(anomalyGapShare, 1)}% del gap Excel/GAIA.`}
                      </p>
                      <p className="mt-1 text-xs text-gray-600">
                        Gap righe anomale {formatEuro(anomalyGap)} · gap righe pulite {formatEuro(cleanGap)}.
                        {cleanRowsAligned ? " Le righe pulite risultano sostanzialmente allineate." : " Anche alcune righe pulite meritano verifica."}
                      </p>
                    </div>
                  </div>
                </article>
              </section>

              <section className="grid gap-4 xl:grid-cols-3">
                <article className="rounded-[24px] border border-amber-200 bg-[#fffaf4] p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">Valutazione</p>
                  <p className="mt-2 text-sm text-gray-700">
                    Le righe anomale sono quelle da valutare per prime. Se le righe pulite hanno GAIA ed Excel allineati, il salto nasce quasi certamente da poche particelle.
                  </p>
                </article>
                <article className="rounded-[24px] border border-sky-200 bg-[#f7fbff] p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">Calcolo</p>
                  <p className="mt-2 text-sm text-gray-700">
                    Ogni riga mostra `mq`, `indice`, `imponibile`, aliquote e il confronto tra importo Excel Capacitas, calcolo GAIA e ruolo particellare.
                  </p>
                </article>
                <article className="rounded-[24px] border border-fuchsia-200 bg-[#fff7fc] p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fuchsia-700">Decisione utente</p>
                  <p className="mt-2 text-sm text-gray-700">
                    Questa vista non decide il caso: rende evidente quali righe e quali comuni meritano rivalutazione manuale.
                  </p>
                </article>
              </section>

              <section className="rounded-[24px] border border-[#d8dfd3] bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-gray-900">Breakdown per comune</p>
                  <p className="text-xs text-gray-500">Ordinato per impatto del gap Excel Capacitas/GAIA.</p>
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-[1180px] divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50 text-left text-xs uppercase tracking-[0.16em] text-gray-500">
                      <tr>
                        <th className="px-4 py-3">Comune</th>
                        <th className="px-4 py-3">Righe</th>
                        <th className="px-4 py-3">Superficie</th>
                        <th className="px-4 py-3">Calcolo GAIA</th>
                        <th className="px-4 py-3">Excel Capacitas</th>
                        <th className="px-4 py-3">Ruolo Capacitas live</th>
                        <th className="px-4 py-3">Gap</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {detail.comuni.map((row) => (
                        <tr key={row.comune_nome}>
                          <td className="px-4 py-3 font-medium text-gray-900">{row.comune_nome}</td>
                          <td className="px-4 py-3 text-gray-700">{row.rows_count} · anomale {row.anomalous_rows_count}</td>
                          <td className="px-4 py-3 text-gray-700">{formatDecimal(row.total_sup_irrigabile_mq, 0)} mq</td>
                          <td className="px-4 py-3 text-xs text-sky-900">
                            <p>0648: <span className="font-semibold">{formatEuro(row.gaia_0648)}</span></p>
                            <p>0985: <span className="font-semibold">{formatEuro(row.gaia_0985)}</span></p>
                            <p>Totale: <span className="font-semibold">{formatEuro(row.gaia_total)}</span></p>
                          </td>
                          <td className="px-4 py-3 text-xs text-fuchsia-900">
                            <p>0648: <span className="font-semibold">{formatEuro(row.excel_0648)}</span></p>
                            <p>0985: <span className="font-semibold">{formatEuro(row.excel_0985)}</span></p>
                            <p>Totale: <span className="font-semibold">{formatEuro(row.excel_total)}</span></p>
                          </td>
                          <td className="px-4 py-3 text-xs text-[#183325]">
                            {row.ruolo_matched_rows_count > 0 ? (
                              <>
                                <p>0648: <span className="font-semibold">{formatEuro(row.ruolo_0648)}</span></p>
                                <p>0985: <span className="font-semibold">{formatEuro(row.ruolo_0985)}</span></p>
                                <p>Totale: <span className="font-semibold">{formatEuro(row.ruolo_total)}</span></p>
                                <p className="mt-1 text-gray-500">{row.ruolo_matched_rows_count}/{row.rows_count} righe abbinate al ruolo</p>
                              </>
                            ) : (
                              <span className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-[11px] font-medium text-gray-600">
                                Nessun match ruolo
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-xs">
                            <p className="font-semibold text-amber-800">Excel/GAIA {formatEuro(row.gap_excel_gaia_total)}</p>
                            {row.ruolo_matched_rows_count > 0 ? (
                              <>
                                <p className="mt-1 font-semibold text-[#183325]">Ruolo/GAIA {formatEuro(row.delta_ruolo_gaia_total)}</p>
                                <p className="mt-1 text-gray-500">Ruolo/Excel {formatEuro(row.delta_ruolo_excel_total)}</p>
                              </>
                            ) : (
                              <p className="mt-1 text-gray-500">Ruolo non disponibile per il comune.</p>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="rounded-[24px] border border-[#d8dfd3] bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-gray-900">Righe del calcolo</p>
                  <p className="text-xs text-gray-500">Ordinate per impatto assoluto sul gap Excel Capacitas/GAIA.</p>
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-[1500px] divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50 text-left text-xs uppercase tracking-[0.16em] text-gray-500">
                      <tr>
                        <th className="px-4 py-3">Riga</th>
                        <th className="px-4 py-3">Base</th>
                        <th className="px-4 py-3">Calcolo GAIA</th>
                        <th className="px-4 py-3">Excel Capacitas</th>
                        <th className="px-4 py-3">Ruolo Capacitas live</th>
                        <th className="px-4 py-3">Gap</th>
                        <th className="px-4 py-3">Segnali</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {detail.rows.map((row, index) => {
                        const largestGap = getLargestRowGap(row);
                        const gaiaRoleRatio = getAmountRatio(row.gaia_total, row.ruolo_total);
                        const excelRoleRatio = getAmountRatio(row.excel_total, row.ruolo_total);
                        return (
                        <tr key={`${row.comune_nome}-${row.foglio}-${row.particella}-${row.subalterno}-${index}`}>
                          <td className="px-4 py-3 align-top">
                            <p className="font-medium text-gray-900">{row.comune_nome ?? "N/D"}</p>
                            <p className="text-xs text-gray-500">
                              Fg {row.foglio ?? "—"} · Part {row.particella ?? "—"}{row.subalterno ? `/${row.subalterno}` : ""}
                            </p>
                          </td>
                          <td className="px-4 py-3 align-top text-xs text-gray-700">
                            <p>Sup: <span className="font-semibold">{formatDecimal(row.sup_irrigabile_mq, 0)} mq</span></p>
                            <p>Indice: <span className="font-semibold">{formatDecimal(row.ind_spese_fisse, 4)}</span></p>
                            <p>Imponibile: <span className="font-semibold">{formatDecimal(row.imponibile_sf)}</span></p>
                            <p>Imp./mq: <span className="font-semibold">{formatDecimal(row.imponibile_per_mq, 4)}</span></p>
                          </td>
                          <td className="px-4 py-3 align-top text-xs text-sky-900">
                            <p>0648: <span className="font-semibold">{formatEuro(row.gaia_0648)}</span></p>
                            <p>0985: <span className="font-semibold">{formatEuro(row.gaia_0985)}</span></p>
                            <p>Totale: <span className="font-semibold">{formatEuro(row.gaia_total)}</span></p>
                            <p>Aliquote: <span className="font-semibold">{formatDecimal(row.aliquota_0648, 6)} / {formatDecimal(row.aliquota_0985, 6)}</span></p>
                          </td>
                          <td className="px-4 py-3 align-top text-xs text-gray-800">
                            <p>0648: <span className="font-semibold">{formatEuro(row.excel_0648)}</span></p>
                            <p>0985: <span className="font-semibold">{formatEuro(row.excel_0985)}</span></p>
                            <p>Totale: <span className="font-semibold">{formatEuro(row.excel_total)}</span></p>
                          </td>
                          <td className="px-4 py-3 align-top text-xs text-[#183325]">
                            {row.ruolo_match_found ? (
                              <>
                                <p>0648: <span className="font-semibold">{formatEuro(row.ruolo_0648)}</span></p>
                                <p>0985: <span className="font-semibold">{formatEuro(row.ruolo_0985)}</span></p>
                                <p>Totale: <span className="font-semibold">{formatEuro(row.ruolo_total)}</span></p>
                                <p className="mt-1 text-gray-500">
                                  {row.ruolo_partite_count} match ruolo
                                  {row.ruolo_comuni.length > 0 ? ` · ${row.ruolo_comuni.join(", ")}` : ""}
                                </p>
                                {row.ruolo_match_level === "without_sub" ? (
                                  <p className="mt-1 text-amber-700">Match unico senza subalterno nello snapshot.</p>
                                ) : null}
                              </>
                            ) : (
                              <span className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-[11px] font-medium text-gray-600">
                                Nessun match ruolo
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 align-top">
                            <p className={getRowGapClassName("excel_gaia_lordo", largestGap, "text-sm font-semibold text-amber-800")}>Excel/GAIA {formatEuro(row.gap_excel_gaia_total)}</p>
                            {row.ruolo_match_found ? (
                              <>
                                <p className={getRowGapClassName("ruolo_gaia_lordo", largestGap, "mt-1 text-xs font-semibold text-[#183325]")}>
                                  Ruolo/GAIA {formatEuro(row.delta_ruolo_gaia_total)}
                                </p>
                                <p className={getRowGapClassName("ruolo_excel_lordo", largestGap, "mt-1 text-xs text-gray-500")}>
                                  Ruolo/Excel {formatEuro(row.delta_ruolo_excel_total)}
                                </p>
                              </>
                            ) : (
                              <p className="mt-1 text-xs text-gray-500">Ruolo non disponibile.</p>
                            )}
                          </td>
                          <td className="px-4 py-3 align-top">
                            <div className="flex flex-wrap gap-2">
                              {row.anomalia_imponibile ? <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-800">Anomalia imponibile</span> : null}
                              {row.anomalia_importi ? <span className="rounded-full border border-fuchsia-200 bg-fuchsia-50 px-2.5 py-1 text-[11px] font-medium text-fuchsia-800">Anomalia importi</span> : null}
                              {!row.anomalia_imponibile && !row.anomalia_importi ? <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-800">Riga pulita</span> : null}
                            </div>
                            <div className="mt-3 space-y-1 rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 text-[11px] leading-5 text-gray-600">
                              {largestGap ? (
                                <p>
                                  Gap max: <span className="font-semibold text-red-800">{largestGap.label} {formatEuro(largestGap.value)}</span>
                                </p>
                              ) : (
                                <p>Gap max: <span className="font-semibold text-emerald-800">nessuno scostamento rilevante</span></p>
                              )}
                              <p>
                                Riga Excel: <span className="font-semibold">{formatText(row.source_row_number)}</span> · CCO: <span className="font-semibold">{formatText(row.cco)}</span>
                              </p>
                              <p>
                                {getRuoloMatchDescription(row)}
                                {row.ruolo_partite_count > 0 ? ` · ${row.ruolo_partite_count} match` : ""}
                              </p>
                              {excelRoleRatio != null ? (
                                <p>
                                  Moltiplicatore Excel/Ruolo: <span className="font-semibold">{formatDecimal(excelRoleRatio, 4)}x</span>
                                </p>
                              ) : null}
                              {gaiaRoleRatio != null ? (
                                <p>
                                  Moltiplicatore GAIA/Ruolo: <span className="font-semibold">{formatDecimal(gaiaRoleRatio, 4)}x</span>
                                </p>
                              ) : null}
                              <p>
                                Distretto: <span className="font-semibold">{formatText(row.num_distretto)}</span>{row.nome_distretto_loc ? ` · ${row.nome_distretto_loc}` : ""}
                              </p>
                            </div>
                          </td>
                        </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          )}
        </div>
      </div>
      {excelPreviewOpen && detail && summary ? (
        <div className="fixed inset-0 z-[95] flex items-center justify-center bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
          <div className="flex max-h-[92vh] w-full max-w-[1600px] flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_100px_rgba(15,23,42,0.32)]">
            <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-fuchsia-700">Anteprima Excel Capacitas</p>
                <h3 className="mt-2 text-2xl font-semibold text-gray-900">{summary.display_name ?? item.tax_code}</h3>
                <p className="mt-1 text-sm text-gray-500">
                  {sourceFilename ? `File: ${sourceFilename}. ` : ""}
                  Righe filtrate sul CF/P.IVA {summary.tax_code}; i numeri riga sono ricostruiti sull&apos;ordine del batch importato.
                </p>
              </div>
              <button className="btn-secondary" type="button" onClick={() => setExcelPreviewOpen(false)}>
                Chiudi anteprima
              </button>
            </div>
            <div className="overflow-y-auto bg-[#f7f3f6] px-6 py-6">
              <div className="rounded-[24px] border border-fuchsia-100 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-900">Righe sorgente Capacitas</p>
                    <p className="mt-1 text-xs text-gray-500">
                      Vista compatta del contenuto importato dall&apos;Excel, con importi originali e segnali di anomalia.
                    </p>
                  </div>
                  <div className="rounded-full border border-fuchsia-100 bg-fuchsia-50 px-3 py-1 text-xs font-semibold text-fuchsia-800">
                    {excelRows.length} righe
                  </div>
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-[1450px] divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50 text-left text-xs uppercase tracking-[0.14em] text-gray-500">
                      <tr>
                        <th className="px-4 py-3">Riga Excel</th>
                        <th className="px-4 py-3">Codici</th>
                        <th className="px-4 py-3">Comune / distretto</th>
                        <th className="px-4 py-3">Catasto</th>
                        <th className="px-4 py-3">Superfici</th>
                        <th className="px-4 py-3">Calcolo Excel</th>
                        <th className="px-4 py-3">Importi Excel</th>
                        <th className="px-4 py-3">Segnali</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {excelRows.map((row, index) => {
                        const signals = getExcelRowSignals(row);
                        return (
                          <tr key={`${row.source_row_number ?? index}-${row.comune_nome}-${row.foglio}-${row.particella}`}>
                            <td className="px-4 py-3 align-top">
                              <p className="font-semibold text-gray-900">{formatText(row.source_row_number)}</p>
                              <p className="mt-1 text-xs text-gray-500">{formatText(row.source_filename)}</p>
                            </td>
                            <td className="px-4 py-3 align-top text-xs text-gray-700">
                              <p>CCO: <span className="font-semibold">{formatText(row.cco)}</span></p>
                              <p>CF raw: <span className="font-semibold">{formatText(row.codice_fiscale_raw ?? summary.tax_code)}</span></p>
                              <p>Prov: <span className="font-semibold">{formatText(row.cod_provincia)}</span></p>
                              <p>Comune cap.: <span className="font-semibold">{formatText(row.cod_comune_capacitas)}</span></p>
                              <p>Frazione: <span className="font-semibold">{formatText(row.cod_frazione)}</span></p>
                            </td>
                            <td className="px-4 py-3 align-top text-xs text-gray-700">
                              <p className="font-semibold text-gray-900">{formatText(row.comune_nome)}</p>
                              <p>Distretto: <span className="font-semibold">{formatText(row.num_distretto)}</span></p>
                              <p>{formatText(row.nome_distretto_loc)}</p>
                            </td>
                            <td className="px-4 py-3 align-top text-xs text-gray-700">
                              <p>Sez: <span className="font-semibold">{formatText(row.sezione_catastale)}</span></p>
                              <p>Fg: <span className="font-semibold">{formatText(row.foglio)}</span></p>
                              <p>Part: <span className="font-semibold">{formatText(row.particella)}</span></p>
                              <p>Sub: <span className="font-semibold">{formatText(row.subalterno)}</span></p>
                            </td>
                            <td className="px-4 py-3 align-top text-xs text-gray-700">
                              <p>Catastale: <span className="font-semibold">{formatDecimal(row.sup_catastale_mq, 0)} mq</span></p>
                              <p>Irrigabile: <span className="font-semibold">{formatDecimal(row.sup_irrigabile_mq, 0)} mq</span></p>
                            </td>
                            <td className="px-4 py-3 align-top text-xs text-gray-700">
                              <p>Indice SF: <span className="font-semibold">{formatDecimal(row.ind_spese_fisse, 4)}</span></p>
                              <p>Imponibile: <span className="font-semibold">{formatDecimal(row.imponibile_sf)}</span></p>
                              <p>Aliq. 0648: <span className="font-semibold">{formatDecimal(row.aliquota_0648, 6)}</span></p>
                              <p>Aliq. 0985: <span className="font-semibold">{formatDecimal(row.aliquota_0985, 6)}</span></p>
                              <p>Esente 0648: <span className="font-semibold">{row.esente_0648 ? "Si" : "No"}</span></p>
                            </td>
                            <td className="px-4 py-3 align-top text-xs text-gray-800">
                              <p>0648: <span className="font-semibold">{formatEuro(row.excel_0648)}</span></p>
                              <p>0985: <span className="font-semibold">{formatEuro(row.excel_0985)}</span></p>
                              <p>Totale: <span className="font-semibold">{formatEuro(row.excel_total)}</span></p>
                            </td>
                            <td className="px-4 py-3 align-top">
                              <div className="flex flex-wrap gap-2">
                                {signals.length > 0 ? signals.map((signal) => (
                                  <span key={signal} className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-800">
                                    {signal}
                                  </span>
                                )) : (
                                  <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-800">
                                    Riga pulita
                                  </span>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
