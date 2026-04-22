"use client";

import * as XLSX from "xlsx";
import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/table/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertBanner } from "@/components/ui/alert-banner";
import { DocumentIcon, RefreshIcon } from "@/components/ui/icons";
import { catastoBulkSearchAnagrafica } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnagraficaBulkRowInput, CatAnagraficaBulkRowResult } from "@/types/catasto";

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function normHeader(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_")
    .replace(/[^\w]/g, "_");
}

function pickColumn(headers: string[], aliases: string[]): string | null {
  const set = new Set(headers);
  for (const a of aliases) {
    if (set.has(a)) return a;
  }
  return null;
}

function formatHaFromMq(value: unknown): string {
  if (value == null) return "—";
  const mq = typeof value === "number" ? value : Number(value);
  const ha = (Number.isFinite(mq) ? mq : 0) / 10_000;
  return `${new Intl.NumberFormat("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(ha)} ha`;
}

type BulkSummary = {
  total: number;
  found: number;
  notFound: number;
  multiple: number;
  invalid: number;
  error: number;
};

function buildSummary(results: CatAnagraficaBulkRowResult[]): BulkSummary {
  const s: BulkSummary = { total: results.length, found: 0, notFound: 0, multiple: 0, invalid: 0, error: 0 };
  for (const r of results) {
    if (r.esito === "FOUND") s.found += 1;
    else if (r.esito === "NOT_FOUND") s.notFound += 1;
    else if (r.esito === "MULTIPLE_MATCHES") s.multiple += 1;
    else if (r.esito === "INVALID_ROW") s.invalid += 1;
    else if (r.esito === "ERROR") s.error += 1;
  }
  return s;
}

async function readFileToRows(file: File): Promise<{ rows: CatAnagraficaBulkRowInput[]; skipped: number }> {
  const ext = file.name.toLowerCase().split(".").pop() ?? "";

  const toJsonRows = (worksheet: XLSX.WorkSheet): Record<string, unknown>[] => {
    return XLSX.utils.sheet_to_json<Record<string, unknown>>(worksheet, { defval: null, raw: false });
  };

  let workbook: XLSX.WorkBook;
  if (ext === "csv") {
    const text = await file.text();
    workbook = XLSX.read(text, { type: "string" });
  } else {
    const buf = await file.arrayBuffer();
    workbook = XLSX.read(buf, { type: "array" });
  }

  const firstSheetName = workbook.SheetNames[0];
  if (!firstSheetName) {
    return { rows: [], skipped: 0 };
  }
  const sheet = workbook.Sheets[firstSheetName];
  const data = toJsonRows(sheet);
  if (data.length === 0) {
    return { rows: [], skipped: 0 };
  }

  const headers = Object.keys(data[0] ?? {}).map(normHeader);
  const headerMap = new Map<string, string>();
  for (const rawKey of Object.keys(data[0] ?? {})) {
    headerMap.set(normHeader(rawKey), rawKey);
  }

  const comuneKey = pickColumn(headers, ["comune", "codice_comune", "nome_comune"]);
  const foglioKey = pickColumn(headers, ["foglio"]);
  const particellaKey = pickColumn(headers, ["particella", "mappale"]);

  if (!foglioKey || !particellaKey) {
    throw new Error("Colonne minime mancanti. Richieste: foglio, particella (opzionale: comune).");
  }

  let skipped = 0;
  const rows: CatAnagraficaBulkRowInput[] = [];
  for (let i = 0; i < data.length; i += 1) {
    const record = data[i] ?? {};
    const comuneRaw = comuneKey ? record[headerMap.get(comuneKey) ?? comuneKey] : null;
    const foglioRaw = record[headerMap.get(foglioKey) ?? foglioKey];
    const particellaRaw = record[headerMap.get(particellaKey) ?? particellaKey];

    const comune = comuneRaw != null ? String(comuneRaw).trim() : "";
    const foglio = foglioRaw != null ? String(foglioRaw).trim() : "";
    const particella = particellaRaw != null ? String(particellaRaw).trim() : "";

    if (!comune && !foglio && !particella) {
      skipped += 1;
      continue;
    }

    rows.push({
      row_index: i + 2,
      comune: comune || null,
      foglio: foglio || null,
      particella: particella || null,
    });
  }
  return { rows, skipped };
}

export function AnagraficaBulkPanel() {
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [parsedRows, setParsedRows] = useState<CatAnagraficaBulkRowInput[]>([]);
  const [skippedRows, setSkippedRows] = useState(0);
  const [results, setResults] = useState<CatAnagraficaBulkRowResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const summary = useMemo(() => buildSummary(results), [results]);

  const columns = useMemo<ColumnDef<CatAnagraficaBulkRowResult>[]>(
    () => [
      { header: "Riga", accessorKey: "row_index", cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.row_index}</span> },
      {
        header: "Input",
        id: "input",
        cell: ({ row }) => (
          <div className="text-sm text-gray-700">
            <p className="font-medium">{row.original.comune_input ?? "—"}</p>
            <p className="text-xs text-gray-500">
              Fg.{row.original.foglio_input ?? "—"} Part.{row.original.particella_input ?? "—"}
            </p>
          </div>
        ),
      },
      {
        header: "Esito",
        accessorKey: "esito",
        cell: ({ row }) => (
          <span
            className={[
              "rounded-full px-2 py-1 text-xs font-medium",
              row.original.esito === "FOUND"
                ? "bg-emerald-50 text-emerald-700"
                : row.original.esito === "NOT_FOUND"
                  ? "bg-gray-100 text-gray-700"
                  : row.original.esito === "MULTIPLE_MATCHES"
                    ? "bg-amber-50 text-amber-700"
                    : row.original.esito === "INVALID_ROW"
                      ? "bg-amber-50 text-amber-800"
                      : "bg-red-50 text-red-700",
            ].join(" ")}
          >
            {row.original.esito}
          </span>
        ),
      },
      { header: "Messaggio", accessorKey: "message", cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.message}</span> },
      {
        header: "Dettaglio",
        id: "detail",
        cell: ({ row }) => {
          const m = row.original.match;
          if (!m) return <span className="text-sm text-gray-400">—</span>;
          return (
            <div className="text-sm text-gray-700">
              <p className="font-medium">{m.comune ?? m.cod_comune_capacitas ?? "—"}</p>
              <p className="text-xs text-gray-500">
                Distretto: {m.num_distretto ?? "—"} · Sup: {formatHaFromMq(m.utenza_latest?.sup_irrigabile_mq ?? m.superficie_mq)}
              </p>
            </div>
          );
        },
      },
    ],
    [],
  );

  async function parseSelectedFile(file: File): Promise<void> {
    setError(null);
    setBusy(true);
    try {
      const parsed = await readFileToRows(file);
      if (parsed.rows.length === 0) {
        throw new Error("File vuoto o senza righe valide.");
      }
      setParsedRows(parsed.rows);
      setSkippedRows(parsed.skipped);
      setResults([]);
    } catch (e) {
      setParsedRows([]);
      setSkippedRows(0);
      setResults([]);
      setError(e instanceof Error ? e.message : "Errore parsing file");
    } finally {
      setBusy(false);
    }
  }

  async function runBulkSearch(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    if (parsedRows.length === 0) {
      setError("Carica un file e verifica che contenga righe valide.");
      return;
    }
    setBusy(true);
    try {
      const response = await catastoBulkSearchAnagrafica(token, { rows: parsedRows });
      setResults(response.results);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore elaborazione massiva");
    } finally {
      setBusy(false);
    }
  }

  function exportCsv(): void {
    if (results.length === 0) return;
    const flat = results.map((r) => {
      const m = r.match;
      const u = m?.utenza_latest;
      const intest = (m?.intestatari ?? [])
        .map((i) => (i.denominazione ?? i.ragione_sociale ?? [i.cognome, i.nome].filter(Boolean).join(" ")) || "")
        .filter(Boolean);
      return {
        row_index: r.row_index,
        comune_input: r.comune_input ?? "",
        foglio_input: r.foglio_input ?? "",
        particella_input: r.particella_input ?? "",
        esito: r.esito,
        message: r.message,
        particella_id: r.particella_id ?? "",
        intestatari: intest.join(" | "),
        utenza_id: u?.id ?? "",
        utenza_anno: u?.anno_campagna ?? "",
        utenza_distretto: u?.num_distretto ?? "",
        utenza_sup_irrigabile_mq: u?.sup_irrigabile_mq ?? "",
        anomalie_count: m?.anomalie_count ?? "",
        dettaglio_particella_url: r.particella_id ? `/catasto/particelle/${r.particella_id}` : "",
      };
    });
    const sheet = XLSX.utils.json_to_sheet(flat);
    const csv = XLSX.utils.sheet_to_csv(sheet);
    triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), "catasto-anagrafica-export.csv");
  }

  function exportXlsx(): void {
    if (results.length === 0) return;
    const flat = results.map((r) => {
      const m = r.match;
      const u = m?.utenza_latest;
      const intest = (m?.intestatari ?? [])
        .map((i) => (i.denominazione ?? i.ragione_sociale ?? [i.cognome, i.nome].filter(Boolean).join(" ")) || "")
        .filter(Boolean);
      return {
        row_index: r.row_index,
        comune_input: r.comune_input ?? "",
        foglio_input: r.foglio_input ?? "",
        particella_input: r.particella_input ?? "",
        esito: r.esito,
        message: r.message,
        particella_id: r.particella_id ?? "",
        intestatari: intest.join(" | "),
        utenza_id: u?.id ?? "",
        utenza_anno: u?.anno_campagna ?? "",
        utenza_distretto: u?.num_distretto ?? "",
        utenza_sup_irrigabile_mq: u?.sup_irrigabile_mq ?? "",
        anomalie_count: m?.anomalie_count ?? "",
        dettaglio_particella_url: r.particella_id ? `/catasto/particelle/${r.particella_id}` : "",
      };
    });

    const wb = XLSX.utils.book_new();
    const sheetResults = XLSX.utils.json_to_sheet(flat);
    XLSX.utils.book_append_sheet(wb, sheetResults, "risultati");

    const sheetSummary = XLSX.utils.json_to_sheet([
      { key: "totale_righe", value: summary.total },
      { key: "trovate", value: summary.found },
      { key: "non_trovate", value: summary.notFound },
      { key: "multiple", value: summary.multiple },
      { key: "righe_invalide", value: summary.invalid },
      { key: "errori", value: summary.error },
      { key: "righe_saltate_vuote", value: skippedRows },
    ]);
    XLSX.utils.book_append_sheet(wb, sheetSummary, "summary");

    const out = XLSX.write(wb, { type: "array", bookType: "xlsx" });
    triggerDownload(new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), "catasto-anagrafica-export.xlsx");
  }

  return (
    <div className="page-stack">
      {error ? (
        <AlertBanner variant="danger" title="Errore">
          {error}
        </AlertBanner>
      ) : null}

      <article className="panel-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-gray-900">Upload file</p>
            <p className="mt-1 text-sm text-gray-500">
              Carica un file <span className="font-medium">.xlsx</span> o <span className="font-medium">.csv</span> con colonne: comune (opz.), foglio, particella.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary"
              disabled={busy || parsedRows.length === 0}
              onClick={() => {
                setSourceFile(null);
                setParsedRows([]);
                setSkippedRows(0);
                setResults([]);
                setError(null);
              }}
            >
              Reset
            </button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept=".xlsx,.csv"
            aria-label="File ricerca anagrafica"
            disabled={busy}
            onChange={(e) => {
              const file = e.target.files?.[0] ?? null;
              if (!file) return;
              setSourceFile(file);
              void parseSelectedFile(file);
            }}
          />
          <p className="text-sm text-gray-500">
            {sourceFile ? (
              <>
                <span className="font-medium text-gray-800">{sourceFile.name}</span> · {parsedRows.length} righe pronte
                {skippedRows ? <span className="text-gray-400"> · {skippedRows} vuote saltate</span> : null}
              </>
            ) : (
              "Nessun file selezionato"
            )}
          </p>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button className="btn-primary" type="button" disabled={busy || parsedRows.length === 0} onClick={() => void runBulkSearch()}>
            <RefreshIcon className="h-4 w-4" />
            {busy ? "Elaborazione…" : "Elabora righe"}
          </button>
          <button className="btn-secondary" type="button" disabled={busy || results.length === 0} onClick={exportCsv}>
            <DocumentIcon className="h-4 w-4" />
            Export CSV
          </button>
          <button className="btn-secondary" type="button" disabled={busy || results.length === 0} onClick={exportXlsx}>
            <DocumentIcon className="h-4 w-4" />
            Export Excel
          </button>
        </div>
      </article>

      <article className="panel-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-gray-900">Riepilogo</p>
            <p className="mt-1 text-sm text-gray-500">Contatori sintetici dell’elaborazione.</p>
          </div>
          <div className="flex flex-wrap gap-2 text-sm text-gray-700">
            <span className="rounded-full bg-gray-100 px-3 py-1">Totale: {summary.total}</span>
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">FOUND: {summary.found}</span>
            <span className="rounded-full bg-gray-100 px-3 py-1">NOT_FOUND: {summary.notFound}</span>
            <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-700">MULTIPLE: {summary.multiple}</span>
            <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-800">INVALID: {summary.invalid}</span>
            <span className="rounded-full bg-red-50 px-3 py-1 text-red-700">ERROR: {summary.error}</span>
          </div>
        </div>
      </article>

      <article className="panel-card">
        {busy && results.length === 0 ? (
          <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Elaborazione…</div>
        ) : results.length === 0 ? (
          <EmptyState icon={DocumentIcon} title="Nessun risultato" description="Carica un file e avvia l’elaborazione per vedere la preview." />
        ) : (
          <DataTable data={results.slice(0, 500)} columns={columns} initialPageSize={12} />
        )}
      </article>
    </div>
  );
}
