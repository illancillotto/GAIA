"use client";

import * as XLSX from "xlsx";
import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/table/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertBanner } from "@/components/ui/alert-banner";
import { DocumentIcon, RefreshIcon } from "@/components/ui/icons";
import { catastoDeleteElaborazioniMassiveJobs, catastoDownloadElaborazioneMassivaJobExport, catastoGetElaborazioneMassivaJob, catastoListElaborazioniMassiveJobs, catastoUploadElaborazioneMassivaJob } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnagraficaBulkJobItem, CatAnagraficaBulkRowResult, CatIntestatario } from "@/types/catasto";

import { CatastoFilePicker } from "../file-picker";

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

function intestatarioDisplayName(intestatario: CatIntestatario): string {
  return (
    intestatario.denominazione ??
    intestatario.ragione_sociale ??
    [intestatario.cognome, intestatario.nome].filter(Boolean).join(" ")
  );
}

function formatJobStatus(status: BulkOperationHistoryItem["status"]): string {
  if (status === "pending") return "IN CODA";
  if (status === "processing") return "IN ELABORAZIONE";
  if (status === "completed") return "COMPLETATO";
  return "FALLITO";
}

type BulkSummary = {
  total: number;
  found: number;
  notFound: number;
  multiple: number;
  invalid: number;
  error: number;
};

type BulkOperationHistoryItem = CatAnagraficaBulkJobItem;
const BULK_JOB_POLL_INTERVAL_MS = 1500;

type BulkProgressState = {
  open: boolean;
  processed: number;
  total: number;
  currentLabel: string;
  phase: "idle" | "processing" | "saving" | "completed" | "error";
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

function formatOperationKind(kind: BulkOperationHistoryItem["kind"]): string {
  if (kind === "CF_PIVA_PARTICELLE") return "CF/P.IVA -> Particelle";
  if (kind === "COMUNE_FOGLIO_PARTICELLA_INTESTATARI") return "Particelle -> Intestatari";
  return "Tipo non rilevato";
}

function inferKindFromHeaders(headers: string[]): "CF_PIVA_PARTICELLE" | "COMUNE_FOGLIO_PARTICELLA_INTESTATARI" {
  const comuneKey = pickColumn(headers, ["comune", "codice_comune", "nome_comune"]);
  const foglioKey = pickColumn(headers, ["foglio"]);
  const particellaKey = pickColumn(headers, ["particella", "mappale"]);
  const cfKey = pickColumn(headers, ["codice_fiscale", "cf"]);
  const pivaKey = pickColumn(headers, ["partita_iva", "piva", "iva"]);

  const hasCadastral = Boolean(comuneKey && foglioKey && particellaKey);
  const hasTax = Boolean(cfKey || pivaKey);

  if (hasTax && !hasCadastral) return "CF_PIVA_PARTICELLE";
  return "COMUNE_FOGLIO_PARTICELLA_INTESTATARI";
}

async function readFileHeadersOnly(
  file: File,
): Promise<{ kind: "CF_PIVA_PARTICELLE" | "COMUNE_FOGLIO_PARTICELLA_INTESTATARI" }> {
  const ext = file.name.toLowerCase().split(".").pop() ?? "";

  const toHeaderRow = (worksheet: XLSX.WorkSheet): unknown[] => {
    return XLSX.utils.sheet_to_json<unknown[]>(worksheet, { header: 1, defval: null, raw: false })[0] ?? [];
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
    throw new Error("File vuoto o senza fogli leggibili.");
  }
  const sheet = workbook.Sheets[firstSheetName];
  const headerRow = toHeaderRow(sheet);
  if (headerRow.length === 0) {
    throw new Error("File vuoto o senza intestazioni.");
  }

  const headers = headerRow.map(normHeader).filter(Boolean);
  const kind = inferKindFromHeaders(headers);

  const comuneKey = pickColumn(headers, ["comune", "codice_comune", "nome_comune"]);
  const foglioKey = pickColumn(headers, ["foglio"]);
  const particellaKey = pickColumn(headers, ["particella", "mappale"]);
  const cfKey = pickColumn(headers, ["codice_fiscale", "cf"]);
  const pivaKey = pickColumn(headers, ["partita_iva", "piva", "iva"]);

  if (kind === "CF_PIVA_PARTICELLE") {
    if (!cfKey && !pivaKey) {
      throw new Error("Colonne minime mancanti. Richieste: codice_fiscale oppure partita_iva.");
    }
  } else {
    if (!comuneKey || !foglioKey || !particellaKey) {
      throw new Error("Colonne minime mancanti. Richieste: comune, foglio, particella (opzionali: sezione, sub). Nel campo comune puoi usare nome comune, codice Capacitas numerico o codice catastale/Belfiore.");
    }
  }
  return { kind };
}

export function AnagraficaBulkPanel() {
  const [inferredKind, setInferredKind] = useState<"CF_PIVA_PARTICELLE" | "COMUNE_FOGLIO_PARTICELLA_INTESTATARI" | null>(
    null,
  );
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [isFileValidated, setIsFileValidated] = useState(false);
  const [results, setResults] = useState<CatAnagraficaBulkRowResult[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [operationHistory, setOperationHistory] = useState<BulkOperationHistoryItem[]>([]);
  const [showDeleteHistoryConfirm, setShowDeleteHistoryConfirm] = useState(false);
  const [bulkProgress, setBulkProgress] = useState<BulkProgressState>({
    open: false,
    processed: 0,
    total: 0,
    currentLabel: "",
    phase: "idle",
  });

  const summary = useMemo(() => buildSummary(results), [results]);
  const busy = isProcessing || isExporting;

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    void (async () => {
      try {
        const { items } = await catastoListElaborazioniMassiveJobs(token, { limit: 5 });
        setOperationHistory(items);
      } catch {
        setOperationHistory([]);
      }
    })();
  }, []);

  async function deleteOperationHistory(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setIsProcessing(true);
    try {
      await catastoDeleteElaborazioniMassiveJobs(token);
      setOperationHistory([]);
      setActiveJobId(null);
      setShowDeleteHistoryConfirm(false);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore cancellazione storico");
    } finally {
      setIsProcessing(false);
    }
  }

  const columns = useMemo<ColumnDef<CatAnagraficaBulkRowResult>[]>(
    () => [
      { header: "Riga", accessorKey: "row_index", cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.row_index}</span> },
      {
        header: "Input",
        id: "input",
        cell: ({ row }) => (
          <div className="text-sm text-gray-700">
            {inferredKind === "CF_PIVA_PARTICELLE" ? (
              <>
                <p className="font-medium">{row.original.codice_fiscale_input ?? row.original.partita_iva_input ?? "—"}</p>
                <p className="text-xs text-gray-500">CF/P.IVA</p>
              </>
            ) : (
              <>
                <p className="font-medium">{row.original.comune_input ?? "—"}</p>
                <p className="text-xs text-gray-500">
                  {row.original.sezione_input ? `Sez.${row.original.sezione_input} ` : ""}
                  Fg.{row.original.foglio_input ?? "—"} Part.{row.original.particella_input ?? "—"}
                  {row.original.sub_input ? ` Sub.${row.original.sub_input}` : ""}
                </p>
              </>
            )}
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
                Distretto: {m.num_distretto ?? "—"} · Sup. cat.: {formatHaFromMq(m.superficie_mq)}
              </p>
              {inferredKind !== "CF_PIVA_PARTICELLE" && m.intestatari.length > 0 ? (
                <p className="mt-1 text-xs text-gray-500">
                  Intestatari:{" "}
                  {m.intestatari
                    .slice(0, 3)
                    .map(intestatarioDisplayName)
                    .filter(Boolean)
                    .join(" · ")}
                  {m.intestatari.length > 3 ? ` (+${m.intestatari.length - 3})` : ""}
                </p>
              ) : null}
              {inferredKind === "CF_PIVA_PARTICELLE" && (row.original.matches_count ?? 0) > 1 ? (
                <p className="mt-1 text-xs text-gray-500">Particelle trovate: {row.original.matches_count}</p>
              ) : null}
            </div>
          );
        },
      },
    ],
    [inferredKind],
  );

  async function validateSelectedFile(file: File): Promise<void> {
    setError(null);
    setIsProcessing(true);
    try {
      const parsed = await readFileHeadersOnly(file);
      setInferredKind(parsed.kind);
      setIsFileValidated(true);
      setResults([]);
      setActiveJobId(null);
      setBulkProgress((prev) => ({ ...prev, open: false }));
    } catch (e) {
      setInferredKind(null);
      setIsFileValidated(false);
      setResults([]);
      setActiveJobId(null);
      setBulkProgress((prev) => ({ ...prev, open: false }));
      setError(e instanceof Error ? e.message : "Errore parsing file");
    } finally {
      setIsProcessing(false);
    }
  }

  async function runBulkSearch(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    if (!sourceFile || !isFileValidated) {
      setError("Carica un file e verifica che contenga righe valide.");
      return;
    }
    setIsProcessing(true);
    setResults([]);
    setActiveJobId(null);
    setBulkProgress({
      open: true,
      processed: 0,
      total: 0,
      currentLabel: "Upload e parsing file in corso...",
      phase: "processing",
    });
    try {
      const job = await catastoUploadElaborazioneMassivaJob(token, sourceFile);
      setActiveJobId(job.id);
      setInferredKind(job.kind);
      setOperationHistory((prev) => [job, ...prev].slice(0, 5));
      let currentJob = job;
      let completed = currentJob.status === "completed" || currentJob.status === "failed";
      while (!completed) {
        setBulkProgress({
          open: true,
          processed: currentJob.processed_rows,
          total: currentJob.total_rows,
          currentLabel: currentJob.current_label ?? "Elaborazione in coda...",
          phase: currentJob.status === "failed" ? "error" : currentJob.status === "completed" ? "completed" : "processing",
        });
        setResults(currentJob.results);
        await new Promise((resolve) => window.setTimeout(resolve, BULK_JOB_POLL_INTERVAL_MS));
        currentJob = await catastoGetElaborazioneMassivaJob(token, job.id);
        setOperationHistory((prev) => [currentJob, ...prev.filter((item) => item.id !== currentJob.id)].slice(0, 5));
        completed = currentJob.status === "completed" || currentJob.status === "failed";
      }

      setResults(currentJob.results);
      setInferredKind(currentJob.kind);
      setOperationHistory((prev) => [currentJob, ...prev.filter((item) => item.id !== currentJob.id)].slice(0, 5));
      setBulkProgress({
        open: true,
        processed: currentJob.processed_rows,
        total: currentJob.total_rows,
        currentLabel: currentJob.current_label ?? (currentJob.status === "completed" ? "Elaborazione completata." : currentJob.error_message ?? "Elaborazione fallita."),
        phase: currentJob.status === "completed" ? "completed" : "error",
      });
      if (currentJob.status === "failed") {
        throw new Error(currentJob.error_message ?? "Errore elaborazione massiva");
      }
      setError(null);
    } catch (e) {
      setBulkProgress((prev) => ({
        ...prev,
        currentLabel: e instanceof Error ? e.message : "Errore elaborazione massiva",
        phase: "error",
      }));
      setError(e instanceof Error ? e.message : "Errore elaborazione massiva");
    } finally {
      setIsProcessing(false);
    }
  }

  async function exportVeloce(format: "csv" | "xlsx"): Promise<void> {
    if (results.length === 0 || !inferredKind) return;
    const token = getStoredAccessToken();
    if (!token || !activeJobId) return;
    setIsExporting(true);
    try {
      const blob = await catastoDownloadElaborazioneMassivaJobExport(token, activeJobId, format);
      triggerDownload(blob, `${inferredKind === "CF_PIVA_PARTICELLE" ? "catasto-intestatari-da-cf" : "catasto-intestatari"}.${format}`);
      setError(null);
    } finally {
      setIsExporting(false);
    }
  }

  const progressPercent =
    bulkProgress.total > 0 ? Math.round((bulkProgress.processed / bulkProgress.total) * 100) : 0;
  const canCloseProgress = bulkProgress.phase === "completed" || bulkProgress.phase === "error";

  return (
    <div className="page-stack">
      {error ? (
        <AlertBanner variant="danger" title="Errore">
          {error}
        </AlertBanner>
      ) : null}

      {showDeleteHistoryConfirm ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <p className="text-lg font-semibold text-gray-900">Cancellare lo storico?</p>
            <p className="mt-2 text-sm text-gray-600">
              Verranno eliminati definitivamente tutti i job di elaborazione massiva salvati per il tuo utente. Dopo il refresh della pagina non saranno più visibili.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" className="btn-secondary" disabled={busy} onClick={() => setShowDeleteHistoryConfirm(false)}>
                Annulla
              </button>
              <button type="button" className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={busy} onClick={() => void deleteOperationHistory()}>
                {busy ? "Cancellazione..." : "Cancella storico"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {bulkProgress.open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-lg font-semibold text-gray-900">
                  {bulkProgress.phase === "completed" ? "Elaborazione completata" : bulkProgress.phase === "error" ? "Elaborazione interrotta" : "Elaborazione in corso"}
                </p>
                <p className="mt-1 text-sm text-gray-600">
                  {bulkProgress.phase === "saving"
                    ? "Salvataggio dei risultati nello storico."
                    : bulkProgress.phase === "completed"
                      ? "Elaborazione completata."
                      : bulkProgress.phase === "error"
                        ? "L'elaborazione si e interrotta."
                        : "Sto processando le righe del file a blocchi."}
                </p>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">
                {progressPercent}%
              </span>
            </div>

            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between text-sm text-gray-600">
                <span>
                  {bulkProgress.processed} di {bulkProgress.total} righe
                </span>
                <span>{bulkProgress.phase === "saving" ? "Salvataggio" : bulkProgress.phase === "completed" ? "Completato" : "Elaborazione"}</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={[
                    "h-full rounded-full transition-all duration-300",
                    bulkProgress.phase === "error" ? "bg-red-500" : bulkProgress.phase === "completed" ? "bg-emerald-500" : "bg-blue-600",
                  ].join(" ")}
                  style={{ width: `${Math.max(progressPercent, bulkProgress.phase === "processing" ? 4 : 0)}%` }}
                />
              </div>
              <p className="mt-3 text-sm text-gray-700">
                Riga corrente: <span className="font-medium">{bulkProgress.currentLabel || "Preparazione..."}</span>
              </p>
            </div>

            {canCloseProgress ? (
              <div className="mt-5 flex justify-end">
                <button type="button" className="btn-primary" onClick={() => setBulkProgress((prev) => ({ ...prev, open: false }))}>
                  Chiudi
                </button>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      <article className="panel-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-gray-900">Template ed upload</p>
            <p className="mt-1 text-sm text-gray-500">
              Seleziona un template, scarica l’esempio e carica un file <span className="font-medium">.xlsx</span> o{" "}
              <span className="font-medium">.csv</span> con le colonne richieste.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary"
              disabled={isProcessing || !sourceFile}
              onClick={() => {
                setSourceFile(null);
                setIsFileValidated(false);
                setResults([]);
                setActiveJobId(null);
                setBulkProgress((prev) => ({ ...prev, open: false }));
                setError(null);
                setInferredKind(null);
              }}
            >
              Reset
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <span className="label-caption">Template CF/P.IVA → Particelle</span>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                onClick={() => {
                  const sheet = XLSX.utils.json_to_sheet([{ codice_fiscale: "RSSMRA80A01H501U", partita_iva: "" }]);
                  const csv = XLSX.utils.sheet_to_csv(sheet);
                  triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), "template-cf-piva-particelle.csv");
                }}
              >
                Template CSV
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                onClick={() => {
                  const wb = XLSX.utils.book_new();
                  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet([{ codice_fiscale: "RSSMRA80A01H501U", partita_iva: "" }]), "template");
                  const out = XLSX.write(wb, { type: "array", bookType: "xlsx" });
                  triggerDownload(
                    new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
                    "template-cf-piva-particelle.xlsx",
                  );
                }}
              >
                Template Excel
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <span className="label-caption">Template Particelle → Intestatari</span>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                onClick={() => {
                  const sheet = XLSX.utils.json_to_sheet([{ comune: "A357", sezione: "", foglio: "5", particella: "120", sub: "" }]);
                  const csv = XLSX.utils.sheet_to_csv(sheet);
                  triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), "template-particelle-intestatari.csv");
                }}
              >
                Template CSV
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                onClick={() => {
                  const wb = XLSX.utils.book_new();
                  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet([{ comune: "A357", sezione: "", foglio: "5", particella: "120", sub: "" }]), "template");
                  const out = XLSX.write(wb, { type: "array", bookType: "xlsx" });
                  triggerDownload(
                    new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
                    "template-particelle-intestatari.xlsx",
                  );
                }}
              >
                Template Excel
              </button>
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-dashed border-gray-200 bg-gray-50/70 p-4">
          <div className="flex flex-wrap items-center gap-3">
            <CatastoFilePicker
              id="catasto-bulk-file"
              label="File ricerca anagrafica"
              accept=".xlsx,.csv"
              file={sourceFile}
              disabled={isProcessing}
              onChange={(file) => {
                if (!file) return;
                setSourceFile(file);
                void validateSelectedFile(file);
              }}
              hint="Carica un file .xlsx o .csv dopo aver scaricato il template corretto."
            />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-gray-900">
                {sourceFile ? sourceFile.name : "Nessun file selezionato"}
              </p>
              <p className="mt-1 text-xs text-gray-500">
                {sourceFile ? (
                  <>
                    Intestazioni verificate lato browser
                    {inferredKind ? ` · ${inferredKind === "CF_PIVA_PARTICELLE" ? "CF/P.IVA → Particelle" : "Particelle → Intestatari"}` : ""}
                    {isFileValidated ? " · pronto per upload backend" : ""}
                  </>
                ) : (
                  "Seleziona il file per validare le colonne; il parsing righe avverrà sul backend."
                )}
              </p>
            </div>
          </div>
        </div>

        {inferredKind ? (
          <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-4">
            <p className="text-sm font-medium text-gray-900">Esportazione</p>
            <p className="mt-3 text-sm text-gray-500">
              Una riga per intestatario.{" "}
              {inferredKind === "CF_PIVA_PARTICELLE"
                ? "Colonne: CF input · P.IVA input · Comune · Foglio · Particella · Sub"
                : "Colonne: Comune · Sezione · Foglio · Particella · Sub"}{" "}
              · Esito · Trovato in esito consorzio · CCO · Link InVolture · Apri InVolture (link cliccabile nel .xlsx) · N intestatari · Rank intestatario (1/n) · CF · Tipo · Cognome · Nome · Denominazione · Ragione Sociale · Data Nascita · Luogo Nascita · Comune Residenza · Indirizzo · CAP · Telefono · Email · Deceduto
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button className="btn-secondary" type="button" disabled={busy || results.length === 0} onClick={() => void exportVeloce("csv")}>
                <DocumentIcon className="h-4 w-4" />
                {isExporting ? "Export CSV..." : "Export CSV"}
              </button>
              <button className="btn-secondary" type="button" disabled={busy || results.length === 0} onClick={() => void exportVeloce("xlsx")}>
                <DocumentIcon className="h-4 w-4" />
                {isExporting ? "Export Excel..." : "Export Excel"}
              </button>
            </div>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button className="btn-primary" type="button" disabled={isProcessing || !sourceFile || !isFileValidated} onClick={() => void runBulkSearch()}>
            <RefreshIcon className="h-4 w-4" />
            {isProcessing ? "Elaborazione…" : "Elabora righe"}
          </button>
        </div>
      </article>

      <article className="panel-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-gray-900">Ultime operazioni</p>
            <p className="mt-1 text-sm text-gray-500">Ultimi 5 job persistiti per il tuo utente, con stato e risultati ricaricabili.</p>
          </div>
          {operationHistory.length > 0 ? (
            <button
              type="button"
              className="btn-secondary"
              disabled={isProcessing}
              onClick={() => setShowDeleteHistoryConfirm(true)}
            >
              Cancella storico
            </button>
          ) : null}
        </div>
        {operationHistory.length === 0 ? (
          <p className="mt-4 text-sm text-gray-500">Nessuna operazione salvata.</p>
        ) : (
          <div className="mt-4 space-y-2">
            {operationHistory.map((item) => (
              <div key={item.id} className="rounded-xl border border-gray-100 bg-gray-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{item.source_filename ?? "Elaborazione senza file"}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {new Intl.DateTimeFormat("it-IT", {
                        dateStyle: "short",
                        timeStyle: "short",
                      }).format(new Date(item.created_at))}{" "}
                      · {formatOperationKind(item.kind)}
                      {item.skipped_rows ? ` · ${item.skipped_rows} righe vuote saltate` : ""}
                    </p>
                    {item.current_label ? <p className="mt-1 text-xs text-gray-500">{item.current_label}</p> : null}
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-gray-700">
                    <span
                      className={[
                        "rounded-full px-2.5 py-1",
                        item.status === "completed"
                          ? "bg-emerald-50 text-emerald-700"
                          : item.status === "failed"
                            ? "bg-red-50 text-red-700"
                            : "bg-blue-50 text-blue-700",
                      ].join(" ")}
                    >
                      {formatJobStatus(item.status)}
                    </span>
                    <span className="rounded-full bg-white px-2.5 py-1">Totale: {item.summary.total}</span>
                    <span className="rounded-full bg-white px-2.5 py-1">Progresso: {item.processed_rows}/{item.total_rows}</span>
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-emerald-700">FOUND: {item.summary.found}</span>
                    <span className="rounded-full bg-white px-2.5 py-1">NOT_FOUND: {item.summary.notFound}</span>
                    <span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-700">MULTIPLE: {item.summary.multiple}</span>
                    <span className="rounded-full bg-red-50 px-2.5 py-1 text-red-700">ERROR: {item.summary.error}</span>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={isProcessing || isExporting}
                    onClick={() => {
                      const token = getStoredAccessToken();
                      if (!token) return;
                      void (async () => {
                        try {
                          const job = await catastoGetElaborazioneMassivaJob(token, item.id);
                          setInferredKind(job.kind);
                          setResults(job.results);
                          setActiveJobId(job.id);
                          setError(null);
                        } catch (e) {
                          setError(e instanceof Error ? e.message : "Errore caricamento job");
                        }
                      })();
                    }}
                  >
                    Ricarica risultati
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={isProcessing || isExporting}
                    onClick={() => {
                      const token = getStoredAccessToken();
                      if (!token) return;
                      void (async () => {
                        setIsExporting(true);
                        try {
                          const blob = await catastoDownloadElaborazioneMassivaJobExport(token, item.id, "csv");
                          triggerDownload(blob, `${item.kind === "CF_PIVA_PARTICELLE" ? "catasto-intestatari-da-cf" : "catasto-intestatari"}.csv`);
                        } catch (e) {
                          setError(e instanceof Error ? e.message : "Errore export job");
                        } finally {
                          setIsExporting(false);
                        }
                      })();
                    }}
                  >
                    {isExporting ? "Export CSV..." : "Riesporta CSV"}
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={isProcessing || isExporting}
                    onClick={() => {
                      const token = getStoredAccessToken();
                      if (!token) return;
                      void (async () => {
                        setIsExporting(true);
                        try {
                          const blob = await catastoDownloadElaborazioneMassivaJobExport(token, item.id, "xlsx");
                          triggerDownload(blob, `${item.kind === "CF_PIVA_PARTICELLE" ? "catasto-intestatari-da-cf" : "catasto-intestatari"}.xlsx`);
                        } catch (e) {
                          setError(e instanceof Error ? e.message : "Errore export job");
                        } finally {
                          setIsExporting(false);
                        }
                      })();
                    }}
                  >
                    {isExporting ? "Export Excel..." : "Riesporta Excel"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
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
