"use client";

import type {
  RuoloCapacitasCalculationDetailResponse,
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

  return (
    <div className="fixed inset-0 z-[85] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
      <div className="flex max-h-[94vh] w-full max-w-[1500px] flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Dettaglio calcolo GAIA</p>
            <h2 className="mt-2 text-2xl font-semibold text-gray-900">{item.ruolo_display_name ?? item.capacitas_display_name ?? item.tax_code}</h2>
            <p className="mt-1 text-sm text-gray-500">
              {item.tax_code} · qui l&apos;utente puo valutare come gestire il caso guardando direttamente formula, righe anomale e scostamenti.
            </p>
          </div>
          <button className="btn-secondary" type="button" onClick={onClose}>
            Chiudi
          </button>
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
                      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-sky-700">GAIA</p>
                      <p className="mt-2 text-lg font-semibold text-gray-900">{formatEuro(summary.gaia_total)}</p>
                      <p className="mt-1 text-xs text-gray-500">Righe anomale {formatEuro(summary.gaia_total_anomalous_rows)}</p>
                    </div>
                    <div className="rounded-2xl border border-[#efe1ef] bg-[#fff7fc] p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-fuchsia-700">Excel</p>
                      <p className="mt-2 text-lg font-semibold text-gray-900">{formatEuro(summary.excel_total)}</p>
                      <p className="mt-1 text-xs text-gray-500">Righe anomale {formatEuro(summary.excel_total_anomalous_rows)}</p>
                    </div>
                  </div>
                </article>

                <article className="rounded-[24px] border border-[#d8dfd3] bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Indicatori del calcolo</p>
                  <div className="mt-4 space-y-4">
                    <div>
                      <p className="text-sm font-medium text-gray-900">Delta Excel meno GAIA</p>
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
                    Ogni riga mostra `mq`, `indice`, `imponibile`, aliquote e il confronto tra importo Excel e ricalcolo GAIA.
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
                  <p className="text-xs text-gray-500">Ordinato per impatto del gap Excel/GAIA.</p>
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50 text-left text-xs uppercase tracking-[0.16em] text-gray-500">
                      <tr>
                        <th className="px-4 py-3">Comune</th>
                        <th className="px-4 py-3">Righe</th>
                        <th className="px-4 py-3">Superficie</th>
                        <th className="px-4 py-3">GAIA</th>
                        <th className="px-4 py-3">Excel</th>
                        <th className="px-4 py-3">Gap Excel/GAIA</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {detail.comuni.map((row) => (
                        <tr key={row.comune_nome}>
                          <td className="px-4 py-3 font-medium text-gray-900">{row.comune_nome}</td>
                          <td className="px-4 py-3 text-gray-700">{row.rows_count} · anomale {row.anomalous_rows_count}</td>
                          <td className="px-4 py-3 text-gray-700">{formatDecimal(row.total_sup_irrigabile_mq, 0)} mq</td>
                          <td className="px-4 py-3 text-gray-700">{formatEuro(row.gaia_total)}</td>
                          <td className="px-4 py-3 text-gray-700">{formatEuro(row.excel_total)}</td>
                          <td className="px-4 py-3 font-semibold text-amber-800">{formatEuro(row.gap_excel_gaia_total)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="rounded-[24px] border border-[#d8dfd3] bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-gray-900">Righe del calcolo</p>
                  <p className="text-xs text-gray-500">Ordinate per impatto assoluto sul gap Excel/GAIA.</p>
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50 text-left text-xs uppercase tracking-[0.16em] text-gray-500">
                      <tr>
                        <th className="px-4 py-3">Riga</th>
                        <th className="px-4 py-3">Base</th>
                        <th className="px-4 py-3">GAIA</th>
                        <th className="px-4 py-3">Excel</th>
                        <th className="px-4 py-3">Gap</th>
                        <th className="px-4 py-3">Segnali</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {detail.rows.map((row, index) => (
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
                          <td className="px-4 py-3 align-top">
                            <span className="text-sm font-semibold text-amber-800">{formatEuro(row.gap_excel_gaia_total)}</span>
                          </td>
                          <td className="px-4 py-3 align-top">
                            <div className="flex flex-wrap gap-2">
                              {row.anomalia_imponibile ? <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-800">Anomalia imponibile</span> : null}
                              {row.anomalia_importi ? <span className="rounded-full border border-fuchsia-200 bg-fuchsia-50 px-2.5 py-1 text-[11px] font-medium text-fuchsia-800">Anomalia importi</span> : null}
                              {!row.anomalia_imponibile && !row.anomalia_importi ? <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-800">Riga pulita</span> : null}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
