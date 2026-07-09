"use client";

import { useMemo, useState } from "react";
import * as XLSX from "xlsx";

import type { CatIndiceGroupSummary, CatIndiceOverview } from "@/types/catasto";

const INDEX_COLORS: Record<string, string> = {
  alta_pressione: "#14532d",
  bassa_pressione: "#1d4ed8",
  canaletta: "#ea580c",
  non_classificato: "#64748b",
};

const DISTRETTI_INDICE_FILTER_ALL = "__all__";

const DISTRETTO_CODE_ALIASES: Record<string, string> = {
  "291": "29a",
  "292": "29b",
  "293": "29c",
};

export type DistrettoSortKey =
  | "indice"
  | "num"
  | "nome"
  | "haRiferimento"
  | "particelle"
  | "aRuolo"
  | "conAnagrafica"
  | "supIrrigata"
  | "importoRuolo"
  | "importoRuoloManutenzione"
  | "importoRuoloIrrigazione"
  | "importoRuoloIstituzionale";

export type SortDirection = "asc" | "desc";

export type DistrettoSortState = {
  key: DistrettoSortKey;
  direction: SortDirection;
};

export type DistrettoTableRow = {
  indiceKey: string;
  indiceLabel: string;
  num: string;
  nome: string;
  haRiferimento: number | null;
  particelle: number;
  aRuolo: number;
  conAnagrafica: number;
  supIrrigata: number;
  importoRuolo: number;
  importoRuoloManutenzione: number;
  importoRuoloIrrigazione: number;
  importoRuoloIstituzionale: number;
};

type DistrettoTableTotals = Omit<DistrettoTableRow, "indiceKey" | "indiceLabel" | "num" | "nome" | "haRiferimento"> & {
  haRiferimento: number;
};

type DistrettiExcelRow = {
  Indice: string;
  "N°": string;
  Nome: string;
  "Ha riferimento": number | null;
  Particelle: number;
  "A ruolo": number;
  "Con anagrafica": number;
  "Sup. irrigata (ha)": number;
  "Importo ruolo (EUR)": number;
  "0648 Manut. (EUR)": number;
  "0668 Irrig. (EUR)": number;
  "0985 Ist. (EUR)": number;
};

export function normalizeDistrettoCode(code: string): string {
  const trimmed = code.trim().toLowerCase();
  const aliased = DISTRETTO_CODE_ALIASES[trimmed] ?? trimmed;
  return aliased.length === 1 && aliased >= "0" && aliased <= "9" ? `0${aliased}` : aliased;
}

export function distrettoSortValue(code: string): [number, number, string] {
  const normalized = normalizeDistrettoCode(code);
  const numeric = normalized.match(/^(\d+)([a-z]*)$/);
  if (numeric) {
    return [0, Number(numeric[1]), numeric[2]];
  }
  if (normalized.startsWith("fd")) {
    return [1, 0, normalized];
  }
  return [2, 0, normalized];
}

export function compareNullableNumber(left: number | null, right: number | null): number {
  if (left == null && right == null) return 0;
  if (left == null) return 1;
  if (right == null) return -1;
  return left - right;
}

export function compareDistrettoRows(left: DistrettoTableRow, right: DistrettoTableRow, sort: DistrettoSortState): number {
  let result = 0;
  switch (sort.key) {
    case "indice":
      result = left.indiceLabel.localeCompare(right.indiceLabel, "it", { numeric: true, sensitivity: "base" });
      break;
    case "num": {
      const [lg, ln, ls] = distrettoSortValue(left.num);
      const [rg, rn, rs] = distrettoSortValue(right.num);
      result = lg - rg || ln - rn || ls.localeCompare(rs, "it", { numeric: true, sensitivity: "base" });
      break;
    }
    case "nome":
      result = left.nome.localeCompare(right.nome, "it", { numeric: true, sensitivity: "base" });
      break;
    case "haRiferimento":
      result = compareNullableNumber(left.haRiferimento, right.haRiferimento);
      break;
    case "particelle":
      result = left.particelle - right.particelle;
      break;
    case "aRuolo":
      result = left.aRuolo - right.aRuolo;
      break;
    case "conAnagrafica":
      result = left.conAnagrafica - right.conAnagrafica;
      break;
    case "supIrrigata":
      result = left.supIrrigata - right.supIrrigata;
      break;
    case "importoRuolo":
      result = left.importoRuolo - right.importoRuolo;
      break;
    case "importoRuoloManutenzione":
      result = left.importoRuoloManutenzione - right.importoRuoloManutenzione;
      break;
    case "importoRuoloIrrigazione":
      result = left.importoRuoloIrrigazione - right.importoRuoloIrrigazione;
      break;
    case "importoRuoloIstituzionale":
      result = left.importoRuoloIstituzionale - right.importoRuoloIstituzionale;
      break;
  }
  if (result === 0) {
    const [lg, ln, ls] = distrettoSortValue(left.num);
    const [rg, rn, rs] = distrettoSortValue(right.num);
    result = lg - rg || ln - rn || ls.localeCompare(rs, "it", { numeric: true, sensitivity: "base" });
  }
  return sort.direction === "asc" ? result : -result;
}

export function buildDistrettoTableRows(groups: CatIndiceGroupSummary[]): DistrettoTableRow[] {
  const rows: DistrettoTableRow[] = [];
  for (const group of groups) {
    const analyticsByKey = new Map(group.distretti_analytics.map((entry) => [entry.key, entry]));
    for (const distretto of group.distretti) {
      const analytics = analyticsByKey.get(normalizeDistrettoCode(distretto.num_distretto));
      rows.push({
        indiceKey: group.indice_key,
        indiceLabel: group.indice_label,
        num: distretto.num_distretto.toLowerCase().startsWith("fd") ? distretto.num_distretto.toUpperCase() : distretto.num_distretto,
        nome: distretto.nome_distretto ?? "—",
        haRiferimento: distretto.hectares_reference != null ? Number(distretto.hectares_reference) : null,
        particelle: analytics?.particelle_count ?? 0,
        aRuolo: analytics?.ruolo_particelle_count ?? 0,
        conAnagrafica: analytics?.particelle_con_anagrafica_count ?? 0,
        supIrrigata: Number(analytics?.superficie_irrigata_ha ?? 0),
        importoRuolo: Number(analytics?.importo_ruolo ?? 0),
        importoRuoloManutenzione: Number(analytics?.importo_ruolo_manutenzione ?? 0),
        importoRuoloIrrigazione: Number(analytics?.importo_ruolo_irrigazione ?? 0),
        importoRuoloIstituzionale: Number(analytics?.importo_ruolo_istituzionale ?? 0),
      });
    }
  }
  return rows.sort((left, right) => {
    const [lg, ln, ls] = distrettoSortValue(left.num);
    const [rg, rn, rs] = distrettoSortValue(right.num);
    return lg - rg || ln - rn || ls.localeCompare(rs);
  });
}

export function filterAndSortDistrettoRows(
  rows: DistrettoTableRow[],
  indiceFilter: string,
  sort: DistrettoSortState,
): DistrettoTableRow[] {
  const filteredRows =
    indiceFilter === DISTRETTI_INDICE_FILTER_ALL ? rows : rows.filter((row) => row.indiceKey === indiceFilter);
  return [...filteredRows].sort((left, right) => compareDistrettoRows(left, right, sort));
}

export function summarizeDistrettoRows(rows: DistrettoTableRow[]): DistrettoTableTotals {
  return rows.reduce(
    (acc, row) => ({
      haRiferimento: acc.haRiferimento + (row.haRiferimento ?? 0),
      particelle: acc.particelle + row.particelle,
      aRuolo: acc.aRuolo + row.aRuolo,
      conAnagrafica: acc.conAnagrafica + row.conAnagrafica,
      supIrrigata: acc.supIrrigata + row.supIrrigata,
      importoRuolo: acc.importoRuolo + row.importoRuolo,
      importoRuoloManutenzione: acc.importoRuoloManutenzione + row.importoRuoloManutenzione,
      importoRuoloIrrigazione: acc.importoRuoloIrrigazione + row.importoRuoloIrrigazione,
      importoRuoloIstituzionale: acc.importoRuoloIstituzionale + row.importoRuoloIstituzionale,
    }),
    {
      haRiferimento: 0,
      particelle: 0,
      aRuolo: 0,
      conAnagrafica: 0,
      supIrrigata: 0,
      importoRuolo: 0,
      importoRuoloManutenzione: 0,
      importoRuoloIrrigazione: 0,
      importoRuoloIstituzionale: 0,
    },
  );
}

export function buildDistrettiExcelRows(rows: DistrettoTableRow[], totals: DistrettoTableTotals): DistrettiExcelRow[] {
  const sheetRows = rows.map((row) => ({
    Indice: row.indiceLabel,
    "N°": row.num,
    Nome: row.nome,
    "Ha riferimento": row.haRiferimento,
    Particelle: row.particelle,
    "A ruolo": row.aRuolo,
    "Con anagrafica": row.conAnagrafica,
    "Sup. irrigata (ha)": Number(row.supIrrigata.toFixed(4)),
    "Importo ruolo (EUR)": Number(row.importoRuolo.toFixed(2)),
    "0648 Manut. (EUR)": Number(row.importoRuoloManutenzione.toFixed(2)),
    "0668 Irrig. (EUR)": Number(row.importoRuoloIrrigazione.toFixed(2)),
    "0985 Ist. (EUR)": Number(row.importoRuoloIstituzionale.toFixed(2)),
  }));
  sheetRows.push({
    Indice: "TOTALE",
    "N°": "",
    Nome: "",
    "Ha riferimento": totals.haRiferimento,
    Particelle: totals.particelle,
    "A ruolo": totals.aRuolo,
    "Con anagrafica": totals.conAnagrafica,
    "Sup. irrigata (ha)": Number(totals.supIrrigata.toFixed(4)),
    "Importo ruolo (EUR)": Number(totals.importoRuolo.toFixed(2)),
    "0648 Manut. (EUR)": Number(totals.importoRuoloManutenzione.toFixed(2)),
    "0668 Irrig. (EUR)": Number(totals.importoRuoloIrrigazione.toFixed(2)),
    "0985 Ist. (EUR)": Number(totals.importoRuoloIstituzionale.toFixed(2)),
  });
  return sheetRows;
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

function formatInteger(value: number): string {
  return new Intl.NumberFormat("it-IT").format(value);
}

function formatHa(value: number): string {
  return new Intl.NumberFormat("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value);
}

function formatEuro(value: number): string {
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(value);
}

function SortableHeader({
  label,
  sortKey,
  currentSort,
  align = "left",
  onSort,
}: {
  label: string;
  sortKey: DistrettoSortKey;
  currentSort: DistrettoSortState;
  align?: "left" | "right";
  onSort: (key: DistrettoSortKey) => void;
}) {
  const isActive = currentSort.key === sortKey;
  const nextDirection = isActive && currentSort.direction === "asc" ? "discendente" : "ascendente";
  return (
    <th className={align === "right" ? "px-3 py-3 text-right" : "px-3 py-3 text-left"} aria-sort={isActive ? (currentSort.direction === "asc" ? "ascending" : "descending") : "none"}>
      <button
        type="button"
        className={`inline-flex items-center gap-1.5 rounded-full px-2 py-1 transition hover:bg-white/80 hover:text-[#1d4e35] focus:outline-none focus:ring-2 focus:ring-[#1d4e35]/25 ${
          align === "right" ? "justify-end" : "justify-start"
        } ${isActive ? "bg-white text-[#1d4e35] shadow-sm" : ""}`}
        onClick={() => onSort(sortKey)}
        aria-label={`Ordina ${label} in modo ${nextDirection}`}
      >
        <span>{label}</span>
        <span className={`flex flex-col text-[8px] leading-[0.7] ${isActive ? "text-[#1d4e35]" : "text-[#8aa395]"}`} aria-hidden="true">
          <span className={isActive && currentSort.direction === "asc" ? "opacity-100" : "opacity-35"}>▲</span>
          <span className={isActive && currentSort.direction === "desc" ? "opacity-100" : "opacity-35"}>▼</span>
        </span>
      </button>
    </th>
  );
}

function getNextSort(current: DistrettoSortState, sortKey: DistrettoSortKey): DistrettoSortState {
  return {
    key: sortKey,
    direction: current.key === sortKey && current.direction === "asc" ? "desc" : "asc",
  };
}

export function DistrettiIndiciTable({
  overview,
  isLoading,
}: {
  overview: CatIndiceOverview | null;
  isLoading: boolean;
}) {
  const [indiceFilter, setIndiceFilter] = useState(DISTRETTI_INDICE_FILTER_ALL);
  const [sort, setSort] = useState<DistrettoSortState>({ key: "num", direction: "asc" });

  const indiceOptions = useMemo(
    () =>
      (overview?.items ?? []).map((item) => ({
        key: item.indice_key,
        label: item.indice_label,
      })),
    [overview],
  );

  const allRows = useMemo(() => buildDistrettoTableRows(overview?.items ?? []), [overview]);
  const rows = useMemo(() => filterAndSortDistrettoRows(allRows, indiceFilter, sort), [allRows, indiceFilter, sort]);
  const totals = useMemo(() => summarizeDistrettoRows(rows), [rows]);

  function handleSort(sortKey: DistrettoSortKey): void {
    setSort((current) => getNextSort(current, sortKey));
  }

  function exportExcel(): void {
    const anno = overview?.anno_riferimento ?? "nd";
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(buildDistrettiExcelRows(rows, totals)), `Distretti ${anno}`);
    const output = XLSX.write(workbook, { type: "array", bookType: "xlsx" });
    triggerDownload(
      new Blob([output], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
      `distretti-indici-${anno}.xlsx`,
    );
  }

  return (
    <article className="panel-card">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7d68]">Quadro distretti</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">Tutti i distretti con indice, superfici e importi ruolo</h2>
          <p className="mt-2 text-sm text-slate-500">
            La tabella replica il quadro ufficiale dei distretti (indice · numero · nome) arricchito con i dati ruolo {overview?.anno_riferimento ?? "—"} per distretto.
          </p>
        </div>
        <div className="flex max-w-full flex-col items-stretch gap-3 sm:items-end">
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#5f7d68]">Filtra per indice</p>
            <div
              className="rounded-[1.75rem] border border-[#d7e4da] bg-[#f7fbf8] p-1.5 shadow-sm"
              role="radiogroup"
              aria-label="Filtra per indice"
            >
              <div className="flex max-w-full flex-wrap gap-1">
                <button
                  type="button"
                  role="radio"
                  aria-checked={indiceFilter === DISTRETTI_INDICE_FILTER_ALL}
                  className={
                    indiceFilter === DISTRETTI_INDICE_FILTER_ALL
                      ? "rounded-full bg-[#1d4e35] px-3.5 py-2 text-xs font-semibold text-white shadow-sm"
                      : "rounded-full px-3.5 py-2 text-xs font-semibold text-[#5f7d68] transition hover:bg-white hover:text-[#1d4e35]"
                  }
                  onClick={() => setIndiceFilter(DISTRETTI_INDICE_FILTER_ALL)}
                >
                  Tutti
                </button>
                {indiceOptions.map((item) => {
                  const isSelected = indiceFilter === item.key;
                  return (
                    <button
                      key={item.key}
                      type="button"
                      role="radio"
                      aria-checked={isSelected}
                      className={
                        isSelected
                          ? "rounded-full bg-white px-3.5 py-2 text-xs font-semibold text-[#1d4e35] shadow-sm ring-1 ring-[#1d4e35]/15"
                          : "rounded-full px-3.5 py-2 text-xs font-semibold text-[#5f7d68] transition hover:bg-white hover:text-[#1d4e35]"
                      }
                      onClick={() => setIndiceFilter(item.key)}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
          <button
            type="button"
            className="rounded-full border border-[#1d4e35] bg-[#1d4e35] px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#163c29] disabled:cursor-not-allowed disabled:opacity-50"
            disabled={rows.length === 0}
            onClick={exportExcel}
          >
            Scarica Excel
          </button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <span className="rounded-full bg-[#eef6f0] px-3 py-1 font-semibold text-[#1d4e35]">
          {formatInteger(rows.length)} distretti visibili
        </span>
        <span>
          Ordine: <span className="font-semibold text-slate-700">{sort.direction === "asc" ? "crescente" : "decrescente"}</span>
        </span>
      </div>

      <div className="mt-6 overflow-x-auto rounded-3xl border border-[#d7e4da]">
        {isLoading ? (
          <div className="bg-gray-50 px-4 py-5 text-sm text-gray-500">Caricamento quadro distretti...</div>
        ) : rows.length === 0 ? (
          <div className="bg-gray-50 px-4 py-5 text-sm text-gray-500">Nessun distretto disponibile.</div>
        ) : (
          <table className="w-full min-w-[1120px] text-sm">
            <thead>
              <tr className="bg-[#f7fbf8] text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-[#5f7d68]">
                <SortableHeader label="Indice" sortKey="indice" currentSort={sort} onSort={handleSort} />
                <SortableHeader label="N°" sortKey="num" currentSort={sort} onSort={handleSort} />
                <SortableHeader label="Nome" sortKey="nome" currentSort={sort} onSort={handleSort} />
                <SortableHeader label="Ha riferimento" sortKey="haRiferimento" currentSort={sort} align="right" onSort={handleSort} />
                <SortableHeader label="Particelle" sortKey="particelle" currentSort={sort} align="right" onSort={handleSort} />
                <SortableHeader label="A ruolo" sortKey="aRuolo" currentSort={sort} align="right" onSort={handleSort} />
                <SortableHeader label="Con anagrafica" sortKey="conAnagrafica" currentSort={sort} align="right" onSort={handleSort} />
                <SortableHeader label="Sup. irrigata (ha)" sortKey="supIrrigata" currentSort={sort} align="right" onSort={handleSort} />
                <SortableHeader label="Importo ruolo" sortKey="importoRuolo" currentSort={sort} align="right" onSort={handleSort} />
                <SortableHeader label="0648 Manut." sortKey="importoRuoloManutenzione" currentSort={sort} align="right" onSort={handleSort} />
                <SortableHeader label="0668 Irrig." sortKey="importoRuoloIrrigazione" currentSort={sort} align="right" onSort={handleSort} />
                <SortableHeader label="0985 Ist." sortKey="importoRuoloIstituzionale" currentSort={sort} align="right" onSort={handleSort} />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.indiceKey}-${row.num}`} className="border-t border-[#eef4ef] bg-white">
                  <td className="px-4 py-2.5">
                    <span className="inline-flex items-center gap-2 text-sm text-slate-800">
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: INDEX_COLORS[row.indiceKey] ?? INDEX_COLORS.non_classificato }}
                      />
                      {row.indiceLabel}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 font-semibold text-slate-900">{row.num}</td>
                  <td className="px-3 py-2.5 text-slate-800">{row.nome}</td>
                  <td className="px-3 py-2.5 text-right text-slate-700">{row.haRiferimento != null ? formatHa(row.haRiferimento) : "—"}</td>
                  <td className="px-3 py-2.5 text-right text-slate-700">{formatInteger(row.particelle)}</td>
                  <td className="px-3 py-2.5 text-right text-slate-700">{formatInteger(row.aRuolo)}</td>
                  <td className="px-3 py-2.5 text-right text-slate-700">{formatInteger(row.conAnagrafica)}</td>
                  <td className="px-3 py-2.5 text-right text-slate-700">{formatHa(row.supIrrigata)}</td>
                  <td className="px-4 py-2.5 text-right font-semibold text-[#1d4e35]">{formatEuro(row.importoRuolo)}</td>
                  <td className="px-3 py-2.5 text-right text-slate-700">{formatEuro(row.importoRuoloManutenzione)}</td>
                  <td className="px-3 py-2.5 text-right text-slate-700">{formatEuro(row.importoRuoloIrrigazione)}</td>
                  <td className="px-4 py-2.5 text-right text-slate-700">{formatEuro(row.importoRuoloIstituzionale)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-[#d7e4da] bg-[#f7fbf8] font-semibold text-slate-900">
                <td className="px-4 py-3" colSpan={3}>
                  Totale ({formatInteger(rows.length)} distretti)
                </td>
                <td className="px-3 py-3 text-right">{formatHa(totals.haRiferimento)}</td>
                <td className="px-3 py-3 text-right">{formatInteger(totals.particelle)}</td>
                <td className="px-3 py-3 text-right">{formatInteger(totals.aRuolo)}</td>
                <td className="px-3 py-3 text-right">{formatInteger(totals.conAnagrafica)}</td>
                <td className="px-3 py-3 text-right">{formatHa(totals.supIrrigata)}</td>
                <td className="px-4 py-3 text-right text-[#1d4e35]">{formatEuro(totals.importoRuolo)}</td>
                <td className="px-3 py-3 text-right">{formatEuro(totals.importoRuoloManutenzione)}</td>
                <td className="px-3 py-3 text-right">{formatEuro(totals.importoRuoloIrrigazione)}</td>
                <td className="px-4 py-3 text-right">{formatEuro(totals.importoRuoloIstituzionale)}</td>
              </tr>
            </tfoot>
          </table>
        )}
      </div>
    </article>
  );
}
