"use client";

import { useMemo, useState, type ReactNode } from "react";
import * as XLSX from "xlsx";

import { catastoGetIndiciRuoloEsclusi } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatIndiceRuoloExcludedParticella, CatIndiceRuoloReconciliation } from "@/types/catasto";

function formatInteger(value: number): string {
  return new Intl.NumberFormat("it-IT").format(value);
}

function formatHa(value: string): string {
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(Number(value));
}

function formatEuro(value: string): string {
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(Number(value));
}

function formatPercent(value: string | null): string {
  if (value == null) {
    return "—";
  }
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(Number(value)) + "%";
}

function percentOf(part: string, total: string): string {
  const totalNumber = Number(total);
  if (totalNumber <= 0) {
    return "—";
  }
  return formatPercent(String((Number(part) / totalNumber) * 100));
}

function ReconciliationMetric({
  label,
  value,
  sub,
  action,
  tone = "neutral",
}: {
  label: string;
  value: string;
  sub: string;
  action?: ReactNode;
  tone?: "good" | "warning" | "neutral";
}) {
  const toneClass =
    tone === "good"
      ? "border-[#b9d8c3] bg-[#f2faf4] text-[#14532d]"
      : tone === "warning"
        ? "border-[#f3d7a2] bg-[#fff8e9] text-[#8a4f00]"
        : "border-[#d7e4da] bg-white text-slate-900";
  return (
    <div className={`rounded-3xl border p-4 shadow-sm ${toneClass}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] opacity-75">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
      <p className="mt-1 text-xs opacity-75">{sub}</p>
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function buildExcludedExcelRows(rows: CatIndiceRuoloExcludedParticella[]) {
  return rows.map((row) => ({
    Motivo: row.reason_label,
    Comune: row.comune_nome ?? "",
    Foglio: row.foglio,
    Particella: row.particella,
    Subalterno: row.subalterno ?? "",
    "Righe ruolo": row.righe_ruolo_count,
    "Superficie irrigata (ha)": Number(Number(row.superficie_irrigata_ha).toFixed(4)),
    "Importo ruolo (EUR)": Number(Number(row.importo_ruolo).toFixed(2)),
    "0648 Manut. (EUR)": Number(Number(row.importo_ruolo_manutenzione).toFixed(2)),
    "0668 Irrig. (EUR)": Number(Number(row.importo_ruolo_irrigazione).toFixed(2)),
    "0985 Ist. (EUR)": Number(Number(row.importo_ruolo_istituzionale).toFixed(2)),
    "Catasto corrente": row.catasto_is_current == null ? "" : row.catasto_is_current ? "si" : "no",
    "Distretto catasto": row.catasto_num_distretto ?? "",
    "ID cat_particella": row.cat_particella_id ?? "",
    Avvisi: row.avvisi.join(", "),
    Nominativi: row.nominativi.join(", "),
    Partite: row.partite.join(", "),
  }));
}

export function RuoloReconciliationCard({
  reconciliation,
  anno,
}: {
  reconciliation: CatIndiceRuoloReconciliation | null | undefined;
  anno: number | null | undefined;
}) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [excludedRows, setExcludedRows] = useState<CatIndiceRuoloExcludedParticella[] | null>(null);
  const [isLoadingExcludedRows, setIsLoadingExcludedRows] = useState(false);
  const [excludedRowsError, setExcludedRowsError] = useState<string | null>(null);
  const visibleExcludedRows = useMemo(() => excludedRows ?? [], [excludedRows]);

  if (!reconciliation) {
    return null;
  }

  const excludedPercent = percentOf(reconciliation.importo_ruolo_escluso, reconciliation.importo_ruolo_totale);

  async function openExcludedRowsModal(): Promise<void> {
    setIsModalOpen(true);
    if (excludedRows != null || isLoadingExcludedRows) {
      return;
    }
    const token = getStoredAccessToken();
    if (!token) {
      setExcludedRowsError("Sessione non disponibile: effettua nuovamente l'accesso.");
      return;
    }
    setIsLoadingExcludedRows(true);
    setExcludedRowsError(null);
    try {
      const response = await catastoGetIndiciRuoloEsclusi(token, anno ?? undefined);
      setExcludedRows(response.items);
    } catch (error) {
      setExcludedRowsError(error instanceof Error ? error.message : "Errore caricamento particelle escluse.");
    } finally {
      setIsLoadingExcludedRows(false);
    }
  }

  function exportExcludedRows(): void {
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(buildExcludedExcelRows(visibleExcludedRows)), `Esclusi ${anno ?? "nd"}`);
    const output = XLSX.write(workbook, { type: "array", bookType: "xlsx" });
    triggerDownload(
      new Blob([output], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
      `particelle-ruolo-escluse-indici-${anno ?? "nd"}.xlsx`,
    );
  }

  return (
    <article className="overflow-hidden rounded-[2rem] border border-[#c9ddcf] bg-gradient-to-br from-[#f6fbf7] via-white to-[#fff8ea] shadow-sm">
      <div className="border-b border-[#dbe8df] bg-white/70 px-5 py-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Riconciliazione ruolo</p>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-slate-950">Perché il totale ruolo non coincide sempre con gli indici</h2>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
              Gli indici continuano a usare solo il catasto corrente Agenzia Entrate con distretto valorizzato. La riconciliazione parte invece
              da <span className="font-semibold text-slate-800">ruolo_particelle</span>: le righe senza aggancio territoriale affidabile restano fuori
              dai totali per Alta/Bassa/Canaletta e sono mostrate qui come differenza spiegata, non come attribuzione territoriale.
            </p>
          </div>
          <span className="rounded-full border border-[#d7e4da] bg-white px-4 py-2 text-xs font-semibold text-[#1d4e35]">
            Anno ruolo {anno ?? "—"}
          </span>
        </div>
      </div>

      <div className="grid gap-3 p-5 md:grid-cols-4">
        <ReconciliationMetric
          label="Incluso negli indici"
          value={formatEuro(reconciliation.importo_ruolo_incluso)}
          sub={`${formatInteger(reconciliation.particelle_ruolo_incluse_count)} particelle ruolo · ${formatPercent(reconciliation.coverage_percent)} del totale`}
          tone="good"
        />
        <ReconciliationMetric
          label="Escluso dagli indici"
          value={formatEuro(reconciliation.importo_ruolo_escluso)}
          sub={`${formatInteger(reconciliation.particelle_ruolo_escluse_count)} particelle ruolo · ${excludedPercent} del totale`}
          tone="warning"
          action={
            <button
              type="button"
              className="rounded-full border border-[#8a4f00]/30 bg-white px-3 py-1.5 text-xs font-semibold text-[#8a4f00] shadow-sm transition hover:border-[#8a4f00] hover:bg-[#fff3d6] disabled:cursor-not-allowed disabled:opacity-50"
              disabled={reconciliation.particelle_ruolo_escluse_count === 0}
              onClick={() => void openExcludedRowsModal()}
            >
              Visualizza ed esporta
            </button>
          }
        />
        <ReconciliationMetric
          label="Totale ruolo particellare"
          value={formatEuro(reconciliation.importo_ruolo_totale)}
          sub={`${formatInteger(reconciliation.righe_ruolo_totali_count)} righe ruolo da ruolo_particelle`}
        />
        <ReconciliationMetric
          label="Superficie esclusa"
          value={`${formatHa(reconciliation.superficie_irrigata_esclusa_ha)} ha`}
          sub="Ettari ruolo non attribuiti a un indice operativo"
        />
      </div>

      <div className="grid gap-4 border-t border-[#dbe8df] p-5 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-3xl border border-[#d7e4da] bg-white p-4">
          <p className="text-sm font-semibold text-slate-900">Regola di lettura</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Il dato principale resta il quadro per indice, perché è agganciato a particelle correnti e distretti del catasto AE. La differenza
            nasce quando il ruolo contiene particelle non più risolvibili nel catasto corrente, oppure particelle presenti ma prive di distretto.
          </p>
          <div className="mt-4 rounded-2xl bg-[#f7fbf8] p-3 text-xs leading-5 text-slate-600">
            Importi esclusi: manutenzione {formatEuro(reconciliation.importo_ruolo_escluso_manutenzione)} · irrigazione{" "}
            {formatEuro(reconciliation.importo_ruolo_escluso_irrigazione)} · istituzionale{" "}
            {formatEuro(reconciliation.importo_ruolo_escluso_istituzionale)}.
          </div>
        </div>

        <div className="rounded-3xl border border-[#d7e4da] bg-white p-4">
          <p className="text-sm font-semibold text-slate-900">Motivi della differenza</p>
          {reconciliation.reasons.length === 0 ? (
            <p className="mt-3 rounded-2xl border border-dashed border-[#d7e4da] bg-[#f7fbf8] px-4 py-6 text-sm text-slate-500">
              Nessuna riga ruolo esclusa dagli indici.
            </p>
          ) : (
            <div className="mt-3 space-y-3">
              {reconciliation.reasons.map((reason) => (
                <div key={reason.key} className="rounded-2xl border border-[#eef4ef] bg-[#fbfdfb] p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{reason.label}</p>
                      <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-500">{reason.description}</p>
                    </div>
                    <p className="text-right text-sm font-semibold text-[#8a4f00]">{formatEuro(reason.importo_ruolo)}</p>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold text-slate-600">
                    <span className="rounded-full bg-white px-2.5 py-1 ring-1 ring-[#d7e4da]">
                      {formatInteger(reason.particelle_ruolo_distinte_count)} particelle ruolo
                    </span>
                    <span className="rounded-full bg-white px-2.5 py-1 ring-1 ring-[#d7e4da]">
                      {formatInteger(reason.righe_ruolo_count)} righe
                    </span>
                    <span className="rounded-full bg-white px-2.5 py-1 ring-1 ring-[#d7e4da]">
                      {formatHa(reason.superficie_irrigata_ha)} ha
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {isModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4" role="dialog" aria-modal="true" aria-labelledby="ruolo-esclusi-title">
          <div className="flex max-h-[88vh] w-full max-w-7xl flex-col overflow-hidden rounded-[2rem] border border-[#d7e4da] bg-white shadow-2xl">
            <div className="border-b border-[#dbe8df] bg-[#f7fbf8] px-5 py-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#8a4f00]">Particelle escluse dagli indici</p>
                  <h3 id="ruolo-esclusi-title" className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
                    Elenco particelle ruolo fuori dal quadro indici
                  </h3>
                  <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
                    Sono particelle del ruolo {anno ?? "—"} non attribuite agli indici perché non collegate al catasto corrente, non correnti,
                    oppure prive di distretto. Gli importi sono aggregati per particella ruolo distinta.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <a
                    className="rounded-full border border-[#8a4f00] bg-[#fff8e9] px-4 py-2 text-sm font-semibold text-[#8a4f00] shadow-sm transition hover:bg-[#fff0cc]"
                    href={`/catasto/indici/anomalie-ruolo${anno != null ? `?anno=${anno}` : ""}`}
                  >
                    Apri gestione anomalie
                  </a>
                  <button
                    type="button"
                    className="rounded-full border border-[#1d4e35] bg-[#1d4e35] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#163c29] disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={visibleExcludedRows.length === 0}
                    onClick={exportExcludedRows}
                  >
                    Esporta Excel
                  </button>
                  <button
                    type="button"
                    className="rounded-full border border-[#d7e4da] bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
                    onClick={() => setIsModalOpen(false)}
                  >
                    Chiudi
                  </button>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-600">
                <span className="rounded-full bg-white px-3 py-1 font-semibold text-[#1d4e35] ring-1 ring-[#d7e4da]">
                  {formatInteger(visibleExcludedRows.length)} particelle caricate
                </span>
                <span className="rounded-full bg-white px-3 py-1 font-semibold text-[#8a4f00] ring-1 ring-[#f3d7a2]">
                  Attese da riconciliazione: {formatInteger(reconciliation.particelle_ruolo_escluse_count)}
                </span>
              </div>
            </div>
            <div className="min-h-0 flex-1 overflow-auto p-5">
              {isLoadingExcludedRows ? (
                <div className="rounded-3xl border border-dashed border-[#d7e4da] bg-[#f7fbf8] px-5 py-10 text-center text-sm text-slate-500">
                  Caricamento particelle escluse...
                </div>
              ) : excludedRowsError ? (
                <div className="rounded-3xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">{excludedRowsError}</div>
              ) : visibleExcludedRows.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-[#d7e4da] bg-[#f7fbf8] px-5 py-10 text-center text-sm text-slate-500">
                  Nessuna particella esclusa disponibile.
                </div>
              ) : (
                <table className="w-full min-w-[1320px] text-sm">
                  <thead>
                    <tr className="bg-[#f7fbf8] text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-[#5f7d68]">
                      <th className="px-3 py-3">Motivo</th>
                      <th className="px-3 py-3">Comune</th>
                      <th className="px-3 py-3">Foglio</th>
                      <th className="px-3 py-3">Particella</th>
                      <th className="px-3 py-3">Sub</th>
                      <th className="px-3 py-3 text-right">Righe</th>
                      <th className="px-3 py-3 text-right">Ha irrig.</th>
                      <th className="px-3 py-3 text-right">Importo</th>
                      <th className="px-3 py-3 text-right">0648</th>
                      <th className="px-3 py-3 text-right">0668</th>
                      <th className="px-3 py-3 text-right">0985</th>
                      <th className="px-3 py-3">Avvisi</th>
                      <th className="px-3 py-3">Nominativi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleExcludedRows.map((row) => (
                      <tr key={row.key} className="border-t border-[#eef4ef] bg-white align-top">
                        <td className="px-3 py-2.5">
                          <span className="rounded-full bg-[#fff8e9] px-2.5 py-1 text-[11px] font-semibold text-[#8a4f00]">{row.reason_label}</span>
                        </td>
                        <td className="px-3 py-2.5 text-slate-800">{row.comune_nome ?? "—"}</td>
                        <td className="px-3 py-2.5 font-mono text-slate-700">{row.foglio}</td>
                        <td className="px-3 py-2.5 font-mono text-slate-700">{row.particella}</td>
                        <td className="px-3 py-2.5 font-mono text-slate-700">{row.subalterno || "—"}</td>
                        <td className="px-3 py-2.5 text-right tabular-nums">{formatInteger(row.righe_ruolo_count)}</td>
                        <td className="px-3 py-2.5 text-right tabular-nums">{formatHa(row.superficie_irrigata_ha)}</td>
                        <td className="px-3 py-2.5 text-right font-semibold tabular-nums text-[#1d4e35]">{formatEuro(row.importo_ruolo)}</td>
                        <td className="px-3 py-2.5 text-right tabular-nums">{formatEuro(row.importo_ruolo_manutenzione)}</td>
                        <td className="px-3 py-2.5 text-right tabular-nums">{formatEuro(row.importo_ruolo_irrigazione)}</td>
                        <td className="px-3 py-2.5 text-right tabular-nums">{formatEuro(row.importo_ruolo_istituzionale)}</td>
                        <td className="max-w-[180px] px-3 py-2.5 text-xs text-slate-600">{row.avvisi.join(", ") || "—"}</td>
                        <td className="max-w-[260px] px-3 py-2.5 text-xs text-slate-600">{row.nominativi.join(", ") || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </article>
  );
}
