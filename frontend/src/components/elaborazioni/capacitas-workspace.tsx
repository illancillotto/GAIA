"use client";

import * as XLSX from "xlsx";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ElaborazioneHero,
  ElaborazioneMiniStat,
  ElaborazioneNoticeCard,
  ElaborazionePanelHeader,
} from "@/components/elaborazioni/module-chrome";
import { ElaborazioneWorkspaceModal } from "@/components/elaborazioni/workspace-modal";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, LockIcon, RefreshIcon, SearchIcon, ServerIcon, UsersIcon } from "@/components/ui/icons";
import {
  createCapacitasAnagraficaHistoryJob,
  createCapacitasParticelleSyncJob,
  createCapacitasTerreniJob,
  deleteCapacitasAnagraficaHistoryJob,
  deleteCapacitasParticelleSyncJob,
  deleteCapacitasTerreniJob,
  listCapacitasAnagraficaHistoryJobs,
  listCapacitasParticelleSyncJobs,
  listCapacitasCredentials,
  listCapacitasTerreniJobs,
  rerunCapacitasAnagraficaHistoryJob,
  rerunCapacitasParticelleSyncJob,
  rerunCapacitasTerreniJob,
  searchCapacitasInvolture,
  isAuthError,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type {
  CapacitasAnagrafica,
  CapacitasAnagraficaHistoryImportItemInput,
  CapacitasAnagraficaHistoryImportJob,
  CapacitasAnagraficaHistoryImportResult,
  CapacitasCredential,
  CapacitasParticelleSyncJob,
  CapacitasSearchResult,
  CapacitasTerreniBatchItemInput,
  CapacitasTerreniBatchResult,
  CapacitasTerreniJob,
} from "@/types/api";

const SEARCH_TYPE_OPTIONS = [
  { value: 0, label: "Denominazione esatta" },
  { value: 1, label: "Denominazione inizia per" },
  { value: 2, label: "Codice fiscale" },
  { value: 3, label: "CCO / FRA / CCS" },
  { value: 4, label: "Denominazione contiene" },
  { value: 5, label: "Utenza" },
  { value: 6, label: "Indirizzo" },
  { value: 7, label: "Data di nascita" },
  { value: 9, label: "Contiene storico" },
  { value: 10, label: "Avviso" },
  { value: 11, label: "Titolo" },
  { value: 12, label: "Partita IVA" },
  { value: 13, label: "Codice soggetto" },
];

const JOB_POLL_INTERVAL_MS = 5000;

function renderIdentity(row: CapacitasAnagrafica): string {
  return row.Denominazione ?? row.CodiceFiscale ?? row.PartitaIva ?? row.CCO ?? "Record";
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("it-IT");
}

function renderJobStatus(status: string): { label: string; className: string } {
  switch (status) {
    case "succeeded":
      return { label: "Completato", className: "bg-emerald-50 text-emerald-700 ring-emerald-200" };
    case "completed_with_errors":
      return { label: "Con errori", className: "bg-amber-50 text-amber-700 ring-amber-200" };
    case "failed":
      return { label: "Fallito", className: "bg-rose-50 text-rose-700 ring-rose-200" };
    case "processing":
      return { label: "In corso", className: "bg-sky-50 text-sky-700 ring-sky-200" };
    case "queued_resume":
      return { label: "Ripresa pianificata", className: "bg-violet-50 text-violet-700 ring-violet-200" };
    default:
      return { label: "In attesa", className: "bg-slate-50 text-slate-700 ring-slate-200" };
  }
}

function TerreniJobCompletionModal({
  job,
  onClose,
  onShowErrors,
}: {
  job: CapacitasTerreniJob;
  onClose: () => void;
  onShowErrors: (job: CapacitasTerreniJob) => void;
}) {
  const result = isTerreniBatchResult(job.result_json) ? job.result_json : null;
  const tone = renderJobStatus(job.status);
  const isTerminal = job.status === "succeeded" || job.status === "completed_with_errors" || job.status === "failed";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/35 px-4">
      <div className="w-full max-w-lg rounded-3xl bg-white shadow-2xl">
        <div className="px-6 pt-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-gray-400">
                Job #{job.id} {isTerminal ? "completato" : "in corso"}
              </p>
              <h3 className="mt-1 text-lg font-semibold text-gray-900">Report elaborazione Terreni</h3>
            </div>
            <button
              aria-label="Chiudi"
              className="mt-0.5 rounded-full p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-gray-700"
              onClick={onClose}
              type="button"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path d="M6 18L18 6M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>

          <div className="mt-4 flex items-center gap-3">
            <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${tone.className}`}>
              {tone.label}
            </span>
            <span className="text-xs text-gray-400">
              {formatDateTime(job.started_at)} → {formatDateTime(job.completed_at)}
            </span>
          </div>
        </div>

        {result ? (
          <div className="mt-5 grid grid-cols-2 gap-px bg-gray-100 border-t border-gray-100">
            {(
              [
                ["Item processati", result.processed_items],
                ["Righe importate", result.imported_rows],
                ["Unità linkate", result.linked_units],
                ["Occupazioni linkate", result.linked_occupancies],
                ["Certificati importati", result.imported_certificati],
                ["Dettagli importati", result.imported_details],
              ] as [string, number][]
            ).map(([label, value]) => (
              <div className="bg-white px-6 py-3" key={label}>
                <p className="text-xs text-gray-500">{label}</p>
                <p className="mt-0.5 text-xl font-semibold text-gray-900">{value}</p>
              </div>
            ))}
          </div>
        ) : job.error_detail ? (
          <div className="mt-4 px-6 pb-2 text-sm text-rose-700">{job.error_detail}</div>
        ) : null}

        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-gray-100 px-6 py-4">
          {result && result.failed_items > 0 ? (
            <button className="btn-secondary text-amber-700" onClick={() => onShowErrors(job)} type="button">
              Vedi {result.failed_items} errori
            </button>
          ) : null}
          <button className="btn-primary" onClick={onClose} type="button">
            Chiudi
          </button>
        </div>
      </div>
    </div>
  );
}

function TerreniJobErrorsModal({ job, onClose }: { job: CapacitasTerreniJob; onClose: () => void }) {
  const result = isTerreniBatchResult(job.result_json) ? job.result_json : null;
  const failedItems = result ? result.items.filter((item) => !item.ok) : [];

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-gray-950/35 px-4 py-12">
      <div className="w-full max-w-2xl rounded-3xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-gray-400">Job #{job.id}</p>
            <h3 className="mt-0.5 text-lg font-semibold text-gray-900">
              {failedItems.length} item con errore
            </h3>
          </div>
          <button
            aria-label="Chiudi"
            className="rounded-full p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-gray-700"
            onClick={onClose}
            type="button"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path d="M6 18L18 6M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
        <div className="divide-y divide-gray-100 px-6 py-2 max-h-[60vh] overflow-y-auto">
          {failedItems.length === 0 ? (
            <p className="py-4 text-sm text-gray-500">Nessun errore da mostrare.</p>
          ) : (
            failedItems.map((item, i) => (
              <div className="py-3" key={i}>
                <div className="font-medium text-sm text-gray-900">{item.label ?? item.search_key}</div>
                {item.label ? <div className="text-xs text-gray-400 mb-1">{item.search_key}</div> : null}
                <div className="text-sm text-rose-700">{item.error ?? "Errore sconosciuto"}</div>
              </div>
            ))
          )}
        </div>
        <div className="flex justify-end border-t border-gray-100 px-6 py-4">
          <button className="btn-secondary" onClick={onClose} type="button">
            Chiudi
          </button>
        </div>
      </div>
    </div>
  );
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
}

function normalizeImportHeader(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_")
    .replace(/[^\w]/g, "_");
}

function pickImportColumn(headers: string[], aliases: string[]): string | null {
  const set = new Set(headers);
  for (const alias of aliases) {
    if (set.has(alias)) return alias;
  }
  return null;
}

function stringifyImportCell(value: unknown): string {
  if (value == null) return "";
  return String(value).trim();
}

async function readTerreniBatchFile(
  file: File,
): Promise<{ items: CapacitasTerreniBatchItemInput[]; skipped: number }> {
  const ext = file.name.toLowerCase().split(".").pop() ?? "";
  const workbook =
    ext === "csv" ? XLSX.read(await file.text(), { type: "string" }) : XLSX.read(await file.arrayBuffer(), { type: "array" });
  const firstSheetName = workbook.SheetNames[0];
  if (!firstSheetName) return { items: [], skipped: 0 };

  const worksheet = workbook.Sheets[firstSheetName];
  const data = XLSX.utils.sheet_to_json<Record<string, unknown>>(worksheet, { defval: null, raw: false });
  if (data.length === 0) return { items: [], skipped: 0 };

  const headers = Object.keys(data[0] ?? {}).map(normalizeImportHeader);
  const headerMap = new Map<string, string>();
  for (const rawKey of Object.keys(data[0] ?? {})) {
    headerMap.set(normalizeImportHeader(rawKey), rawKey);
  }

  const comuneKey = pickImportColumn(headers, ["comune", "frazione", "localita"]);
  const sezioneKey = pickImportColumn(headers, ["sezione"]);
  const foglioKey = pickImportColumn(headers, ["foglio"]);
  const particellaKey = pickImportColumn(headers, ["particella", "mappale"]);
  const subKey = pickImportColumn(headers, ["sub", "subalterno"]);

  if (!comuneKey || !foglioKey || !particellaKey) {
    throw new Error(
      "Colonne minime mancanti. Richieste: comune, foglio, particella. Facoltative: sezione, sub.",
    );
  }

  let skipped = 0;
  const items: CapacitasTerreniBatchItemInput[] = [];

  for (let index = 0; index < data.length; index += 1) {
    const record = data[index] ?? {};
    const comune = stringifyImportCell(record[headerMap.get(comuneKey) ?? comuneKey]);
    const foglio = stringifyImportCell(record[headerMap.get(foglioKey) ?? foglioKey]);
    const particella = stringifyImportCell(record[headerMap.get(particellaKey) ?? particellaKey]);
    const sezione = sezioneKey ? stringifyImportCell(record[headerMap.get(sezioneKey) ?? sezioneKey]) : "";
    const sub = subKey ? stringifyImportCell(record[headerMap.get(subKey) ?? subKey]) : "";

    if (!comune && !foglio && !particella && !sub) {
      skipped += 1;
      continue;
    }
    if (!comune || !foglio || !particella) {
      throw new Error(`Riga ${index + 2} non valida: servono comune, foglio e particella.`);
    }

    items.push({
      label: `${comune} ${foglio}/${particella}${sub ? `/${sub}` : ""}`,
      comune,
      sezione,
      foglio,
      particella,
      sub,
    });
  }

  return { items, skipped };
}

function downloadTerreniTemplate(format: "csv" | "xlsx"): void {
  const exampleRows = [
    { comune: "Uras", sezione: "", foglio: "1", particella: "680", sub: "" },
    { comune: "Uras", sezione: "", foglio: "14", particella: "1695", sub: "" },
  ];

  if (format === "csv") {
    const csv = XLSX.utils.sheet_to_csv(XLSX.utils.json_to_sheet(exampleRows));
    triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), "capacitas-terreni-template.csv");
    return;
  }

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(exampleRows), "terreni");
  XLSX.utils.book_append_sheet(
    workbook,
    XLSX.utils.json_to_sheet([
      { campo: "comune", obbligatorio: "si", descrizione: "Comune o frazione da risolvere su Capacitas, meglio se specifico." },
      { campo: "foglio", obbligatorio: "si", descrizione: "Foglio catastale usato in ricercaTerreni." },
      { campo: "particella", obbligatorio: "si", descrizione: "Particella catastale." },
      { campo: "sezione", obbligatorio: "no", descrizione: "Sezione Capacitas se presente." },
      { campo: "sub", obbligatorio: "no", descrizione: "Subalterno o sub particella." },
      { campo: "note", obbligatorio: "no", descrizione: "Colonna libera ignorata dal sistema se presente." },
    ]),
    "istruzioni",
  );

  const out = XLSX.write(workbook, { type: "array", bookType: "xlsx" });
  triggerDownload(
    new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
    "capacitas-terreni-template.xlsx",
  );
}

async function readAnagraficaHistoryBatchFile(
  file: File,
): Promise<{ items: CapacitasAnagraficaHistoryImportItemInput[]; skipped: number }> {
  const ext = file.name.toLowerCase().split(".").pop() ?? "";
  const workbook =
    ext === "csv" ? XLSX.read(await file.text(), { type: "string" }) : XLSX.read(await file.arrayBuffer(), { type: "array" });
  const firstSheetName = workbook.SheetNames[0];
  if (!firstSheetName) return { items: [], skipped: 0 };

  const worksheet = workbook.Sheets[firstSheetName];
  const data = XLSX.utils.sheet_to_json<Record<string, unknown>>(worksheet, { defval: null, raw: false });
  if (data.length === 0) return { items: [], skipped: 0 };

  const headers = Object.keys(data[0] ?? {}).map(normalizeImportHeader);
  const headerMap = new Map<string, string>();
  for (const rawKey of Object.keys(data[0] ?? {})) {
    headerMap.set(normalizeImportHeader(rawKey), rawKey);
  }

  const subjectIdKey = pickImportColumn(headers, ["subject_id"]);
  const idxanaKey = pickImportColumn(headers, ["idxana"]);
  if (!subjectIdKey && !idxanaKey) {
    throw new Error("Colonne minime mancanti. Richieste: subject_id e/o idxana.");
  }

  let skipped = 0;
  const items: CapacitasAnagraficaHistoryImportItemInput[] = [];
  for (let index = 0; index < data.length; index += 1) {
    const record = data[index] ?? {};
    const subject_id = subjectIdKey ? stringifyImportCell(record[headerMap.get(subjectIdKey) ?? subjectIdKey]) : "";
    const idxana = idxanaKey ? stringifyImportCell(record[headerMap.get(idxanaKey) ?? idxanaKey]) : "";
    if (!subject_id && !idxana) {
      skipped += 1;
      continue;
    }
    items.push({ subject_id: subject_id || null, idxana: idxana || null });
  }

  return { items, skipped };
}

function downloadAnagraficaHistoryTemplate(format: "csv" | "xlsx"): void {
  const exampleRows = [
    { subject_id: "550e8400-e29b-41d4-a716-446655440000", idxana: "" },
    { subject_id: "", idxana: "48A9749E-96BF-4617-A019-046BF4CECA2B" },
  ];

  if (format === "csv") {
    const csv = XLSX.utils.sheet_to_csv(XLSX.utils.json_to_sheet(exampleRows));
    triggerDownload(new Blob([csv], { type: "text/csv;charset=utf-8" }), "capacitas-anagrafica-storico-template.csv");
    return;
  }

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(exampleRows), "storico");
  const out = XLSX.write(workbook, { type: "array", bookType: "xlsx" });
  triggerDownload(
    new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
    "capacitas-anagrafica-storico-template.xlsx",
  );
}

function isTerreniBatchResult(value: unknown): value is CapacitasTerreniBatchResult {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  return (
    typeof (value as { processed_items?: unknown }).processed_items === "number" &&
    typeof (value as { failed_items?: unknown }).failed_items === "number" &&
    typeof (value as { imported_rows?: unknown }).imported_rows === "number" &&
    typeof (value as { linked_units?: unknown }).linked_units === "number"
  );
}

function isParticelleSyncJobResult(value: unknown): value is {
  total_items: number;
  processed_items: number;
  success_items: number;
  failed_items: number;
  skipped_items: number;
  progress_percent: number;
  current_label?: string | null;
  throttle_ms: number;
  aggressive_window: boolean;
  recheck_hours: number;
  speed_multiplier?: number;
  parallel_workers?: number;
  recent_items: Array<{ particella_id: string; label: string; status: string; message: string }>;
} {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  return (
    typeof (value as { total_items?: unknown }).total_items === "number" &&
    typeof (value as { processed_items?: unknown }).processed_items === "number" &&
    typeof (value as { progress_percent?: unknown }).progress_percent === "number"
  );
}

function isHistoryImportJobResult(value: unknown): value is CapacitasAnagraficaHistoryImportResult & {
  progress_percent?: number;
  current_label?: string | null;
} {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  return (
    typeof (value as { processed?: unknown }).processed === "number" &&
    typeof (value as { imported?: unknown }).imported === "number" &&
    typeof (value as { skipped?: unknown }).skipped === "number" &&
    typeof (value as { failed?: unknown }).failed === "number"
  );
}

export function ElaborazioniCapacitasWorkspace({ embedded = false }: { embedded?: boolean }) {
  const searchParams = useSearchParams();
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [credentials, setCredentials] = useState<CapacitasCredential[]>([]);
  const [results, setResults] = useState<CapacitasSearchResult | null>(null);
  const [loadingCredentials, setLoadingCredentials] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formState, setFormState] = useState({
    q: "",
    tipo_ricerca: 1,
    solo_con_beni: false,
    credential_id: "",
  });

  const [terreniJobs, setTerreniJobs] = useState<CapacitasTerreniJob[]>([]);
  const [terreniJobsLoading, setTerreniJobsLoading] = useState(false);
  const [terreniJobBusyId, setTerreniJobBusyId] = useState<number | null>(null);
  const [terreniDeletingJobId, setTerreniDeletingJobId] = useState<number | null>(null);
  const [terreniJobErrorsModal, setTerreniJobErrorsModal] = useState<CapacitasTerreniJob | null>(null);
  const [terreniCompletedJobModal, setTerreniCompletedJobModal] = useState<CapacitasTerreniJob | null>(null);
  const [terreniMonitorSessionExpired, setTerreniMonitorSessionExpired] = useState(false);
  const inFlightJobIds = useRef<Set<number>>(new Set());
  const [particelleJobs, setParticelleJobs] = useState<CapacitasParticelleSyncJob[]>([]);
  const [particelleJobsLoading, setParticelleJobsLoading] = useState(false);
  const [particelleCreatingJob, setParticelleCreatingJob] = useState(false);
  const [particelleJobBusyId, setParticelleJobBusyId] = useState<number | null>(null);
  const [particelleDeletingJobId, setParticelleDeletingJobId] = useState<number | null>(null);
  const [particelleMonitorSessionExpired, setParticelleMonitorSessionExpired] = useState(false);
  const particelleInFlightJobIds = useRef<Set<number>>(new Set());
  const [particelleError, setParticelleError] = useState<string | null>(null);
  const [particelleStatusMessage, setParticelleStatusMessage] = useState<string | null>(null);
  const [particelleSyncForm, setParticelleSyncForm] = useState({
    credential_id: "",
    only_due: true,
    limit: "",
    fetch_certificati: true,
    fetch_details: true,
    double_speed: false,
    parallel_workers: 1,
  });
  const [terreniError, setTerreniError] = useState<string | null>(null);
  const [terreniStatusMessage, setTerreniStatusMessage] = useState<string | null>(null);
  const [terreniForm, setTerreniForm] = useState({
    credential_id: "",
  });
  const [terreniExecutionForm, setTerreniExecutionForm] = useState({
    double_speed: false,
    parallel_workers: 1,
    throttle_ms: "",
    auto_resume: false,
  });
  const [terreniBatchFile, setTerreniBatchFile] = useState<File | null>(null);
  const [terreniBatchItems, setTerreniBatchItems] = useState<CapacitasTerreniBatchItemInput[]>([]);
  const [terreniBatchSkipped, setTerreniBatchSkipped] = useState(0);
  const [terreniBatchBusy, setTerreniBatchBusy] = useState(false);
  const [terreniBatchCreatingJob, setTerreniBatchCreatingJob] = useState(false);
  const [terreniBatchContinueOnError, setTerreniBatchContinueOnError] = useState(true);
  const [terreniBatchFetchCertificati, setTerreniBatchFetchCertificati] = useState(true);
  const [terreniBatchFetchDetails, setTerreniBatchFetchDetails] = useState(true);
  const [terreniBatchError, setTerreniBatchError] = useState<string | null>(null);
  const [historyMode, setHistoryMode] = useState<"manual" | "file">("manual");
  const [historyForm, setHistoryForm] = useState({
    credential_id: "",
    subject_ids: "",
    idxana_list: "",
    continue_on_error: true,
  });
  const [historyBatchFile, setHistoryBatchFile] = useState<File | null>(null);
  const [historyBatchItems, setHistoryBatchItems] = useState<CapacitasAnagraficaHistoryImportItemInput[]>([]);
  const [historyBatchSkipped, setHistoryBatchSkipped] = useState(0);
  const [historyBatchBusy, setHistoryBatchBusy] = useState(false);
  const [historyImporting, setHistoryImporting] = useState(false);
  const [historyJobs, setHistoryJobs] = useState<CapacitasAnagraficaHistoryImportJob[]>([]);
  const [historyJobsLoading, setHistoryJobsLoading] = useState(false);
  const [historyJobBusyId, setHistoryJobBusyId] = useState<number | null>(null);
  const [historyDeletingJobId, setHistoryDeletingJobId] = useState<number | null>(null);
  const [historyMonitorSessionExpired, setHistoryMonitorSessionExpired] = useState(false);
  const historyInFlightJobIds = useRef<Set<number>>(new Set());
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyStatusMessage, setHistoryStatusMessage] = useState<string | null>(null);
  const [historyResult, setHistoryResult] = useState<CapacitasAnagraficaHistoryImportResult | null>(null);

  const activeCredential = useMemo(
    () => credentials.find((credential) => String(credential.id) === formState.credential_id) ?? null,
    [credentials, formState.credential_id],
  );
  const activeCredentialsCount = credentials.filter((credential) => credential.active).length;
  const jobsInFlight =
    !terreniMonitorSessionExpired &&
    terreniJobs.some((job) => job.status === "pending" || job.status === "processing" || job.status === "queued_resume");
  const particelleJobsInFlight =
    !particelleMonitorSessionExpired &&
    particelleJobs.some((job) => job.status === "pending" || job.status === "processing" || job.status === "queued_resume");
  const historyJobsInFlight =
    !historyMonitorSessionExpired &&
    historyJobs.some((job) => job.status === "pending" || job.status === "processing" || job.status === "queued_resume");
  const terreniReportJob = terreniCompletedJobModal
    ? terreniJobs.find((job) => job.id === terreniCompletedJobModal.id) ?? terreniCompletedJobModal
    : null;
  const terreniErrorsJob = terreniJobErrorsModal
    ? terreniJobs.find((job) => job.id === terreniJobErrorsModal.id) ?? terreniJobErrorsModal
    : null;
  const latestHistoryJob = historyJobs[0] ?? null;
  const latestHistoryResult = latestHistoryJob && isHistoryImportJobResult(latestHistoryJob.result_json) ? latestHistoryJob.result_json : historyResult;

  useEffect(() => {
    void loadCredentials();
    void loadTerreniJobs();
    void loadParticelleJobs();
    void loadHistoryJobs();
  }, []);

  useEffect(() => {
    const q = searchParams.get("q");
    const tipo = searchParams.get("tipo");
    if (!q) return;
    setFormState((s) => ({
      ...s,
      q,
      tipo_ricerca: tipo !== null && /^\d+$/.test(tipo) ? Number(tipo) : s.tipo_ricerca,
    }));
  }, [searchParams]);

  useEffect(() => {
    if (!jobsInFlight) return undefined;

    const timer = window.setInterval(() => {
      void loadTerreniJobs(true);
    }, JOB_POLL_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [jobsInFlight]);

  useEffect(() => {
    if (!particelleJobsInFlight) return undefined;

    const timer = window.setInterval(() => {
      void loadParticelleJobs(true);
    }, JOB_POLL_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [particelleJobsInFlight]);

  useEffect(() => {
    if (!historyJobsInFlight) return undefined;

    const timer = window.setInterval(() => {
      void loadHistoryJobs(true);
    }, JOB_POLL_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [historyJobsInFlight]);

  async function loadCredentials(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setLoadingCredentials(true);
    try {
      const nextCredentials = await listCapacitasCredentials(token);
      setCredentials(nextCredentials);
      setError(null);
      setFormState((current) => ({
        ...current,
        credential_id: current.credential_id ? current.credential_id : nextCredentials.length === 1 ? String(nextCredentials[0].id) : "",
      }));
      setTerreniForm((current) => ({
        ...current,
        credential_id:
          current.credential_id ? current.credential_id : nextCredentials.length === 1 ? String(nextCredentials[0].id) : "",
      }));
      setParticelleSyncForm((current) => ({
        ...current,
        credential_id:
          current.credential_id ? current.credential_id : nextCredentials.length === 1 ? String(nextCredentials[0].id) : "",
      }));
      setHistoryForm((current) => ({
        ...current,
        credential_id:
          current.credential_id ? current.credential_id : nextCredentials.length === 1 ? String(nextCredentials[0].id) : "",
      }));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento credenziali Capacitas");
    } finally {
      setLoadingCredentials(false);
    }
  }

  async function loadTerreniJobs(silent = false): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      setTerreniMonitorSessionExpired(true);
      setTerreniError("Sessione GAIA scaduta: il monitor Terreni si ferma, ma i job backend gia avviati possono continuare.");
      setTerreniStatusMessage("Rientra in GAIA per riprendere il polling del monitor Terreni.");
      return;
    }

    if (!silent) {
      setTerreniJobsLoading(true);
    }
    try {
      const nextJobs = await listCapacitasTerreniJobs(token);
      setTerreniMonitorSessionExpired(false);
      const prevInFlight = inFlightJobIds.current;
      const terminalStatuses = new Set(["succeeded", "completed_with_errors", "failed"]);

      if (silent && prevInFlight.size > 0) {
        const justCompleted = nextJobs.find(
          (j) => prevInFlight.has(j.id) && terminalStatuses.has(j.status),
        );
        if (justCompleted) {
          setTerreniCompletedJobModal(justCompleted);
        }
      }

      inFlightJobIds.current = new Set(
        nextJobs.filter((j) => j.status === "pending" || j.status === "processing" || j.status === "queued_resume").map((j) => j.id),
      );

      setTerreniJobs(nextJobs);
      if (!silent) {
        setTerreniError(null);
      }
    } catch (loadError) {
      if (isAuthError(loadError)) {
        setTerreniMonitorSessionExpired(true);
        setTerreniError("Sessione GAIA scaduta: il monitor Terreni si ferma, ma i job backend gia avviati possono continuare.");
        setTerreniStatusMessage("Rientra in GAIA per riprendere il polling del monitor Terreni.");
        return;
      }
      if (!silent) {
        setTerreniError(loadError instanceof Error ? loadError.message : "Errore caricamento job Terreni");
      }
    } finally {
      if (!silent) {
        setTerreniJobsLoading(false);
      }
    }
  }

  async function loadParticelleJobs(silent = false): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      setParticelleMonitorSessionExpired(true);
      setParticelleError("Sessione GAIA scaduta: il monitor particelle si ferma, ma i job backend gia avviati possono continuare.");
      setParticelleStatusMessage("Rientra in GAIA per riprendere il polling della sync progressiva particelle.");
      return;
    }

    if (!silent) {
      setParticelleJobsLoading(true);
    }
    try {
      const nextJobs = await listCapacitasParticelleSyncJobs(token);
      setParticelleMonitorSessionExpired(false);
      const prevInFlight = particelleInFlightJobIds.current;
      const terminalStatuses = new Set(["succeeded", "completed_with_errors", "failed"]);

      particelleInFlightJobIds.current = new Set(
        nextJobs.filter((job) => job.status === "pending" || job.status === "processing" || job.status === "queued_resume").map((job) => job.id),
      );

      setParticelleJobs(nextJobs);
      if (!silent && prevInFlight.size > 0 && nextJobs.some((job) => prevInFlight.has(job.id) && terminalStatuses.has(job.status))) {
        setParticelleStatusMessage("Sync progressiva particelle aggiornata.");
      }
      if (!silent) {
        setParticelleError(null);
      }
    } catch (loadError) {
      if (isAuthError(loadError)) {
        setParticelleMonitorSessionExpired(true);
        setParticelleError("Sessione GAIA scaduta: il monitor particelle si ferma, ma i job backend gia avviati possono continuare.");
        setParticelleStatusMessage("Rientra in GAIA per riprendere il polling della sync progressiva particelle.");
        return;
      }
      if (!silent) {
        setParticelleError(loadError instanceof Error ? loadError.message : "Errore caricamento job particelle");
      }
    } finally {
      if (!silent) {
        setParticelleJobsLoading(false);
      }
    }
  }

  async function loadHistoryJobs(silent = false): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      setHistoryMonitorSessionExpired(true);
      setHistoryError("Sessione GAIA scaduta: il monitor storico si ferma, ma i job backend gia avviati possono continuare.");
      setHistoryStatusMessage("Rientra in GAIA per riprendere il polling del monitor storico anagrafico.");
      return;
    }

    if (!silent) {
      setHistoryJobsLoading(true);
    }
    try {
      const nextJobs = await listCapacitasAnagraficaHistoryJobs(token);
      setHistoryMonitorSessionExpired(false);
      const prevInFlight = historyInFlightJobIds.current;
      const terminalStatuses = new Set(["succeeded", "completed_with_errors", "failed"]);

      historyInFlightJobIds.current = new Set(
        nextJobs.filter((job) => job.status === "pending" || job.status === "processing" || job.status === "queued_resume").map((job) => job.id),
      );
      setHistoryJobs(nextJobs);

      const latestCompleted = nextJobs.find((job) => terminalStatuses.has(job.status) && isHistoryImportJobResult(job.result_json));
      if (latestCompleted && isHistoryImportJobResult(latestCompleted.result_json)) {
        setHistoryResult(latestCompleted.result_json);
      }

      if (!silent && prevInFlight.size > 0 && nextJobs.some((job) => prevInFlight.has(job.id) && terminalStatuses.has(job.status))) {
        setHistoryStatusMessage("Storico anagrafico aggiornato.");
      }
      if (!silent) {
        setHistoryError(null);
      }
    } catch (loadError) {
      if (isAuthError(loadError)) {
        setHistoryMonitorSessionExpired(true);
        setHistoryError("Sessione GAIA scaduta: il monitor storico si ferma, ma i job backend gia avviati possono continuare.");
        setHistoryStatusMessage("Rientra in GAIA per riprendere il polling del monitor storico anagrafico.");
        return;
      }
      if (!silent) {
        setHistoryError(loadError instanceof Error ? loadError.message : "Errore caricamento job storico anagrafico");
      }
    } finally {
      if (!silent) {
        setHistoryJobsLoading(false);
      }
    }
  }

  async function handleSearch(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setSearching(true);
    try {
      const payload = {
        q: formState.q.trim(),
        tipo_ricerca: formState.tipo_ricerca,
        solo_con_beni: formState.solo_con_beni,
        credential_id: formState.credential_id ? Number.parseInt(formState.credential_id, 10) : undefined,
      };
      const response = await searchCapacitasInvolture(token, payload);
      setResults(response);
      setError(null);
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : "Errore ricerca inVOLTURE");
      setResults(null);
    } finally {
      setSearching(false);
    }
  }

  async function handleRerunJob(jobId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setTerreniJobBusyId(jobId);
    try {
      await rerunCapacitasTerreniJob(token, jobId);
      setTerreniMonitorSessionExpired(false);
      setTerreniStatusMessage(`Job #${jobId} rilanciato.`);
      setTerreniError(null);
      await loadTerreniJobs();
    } catch (rerunError) {
      setTerreniError(rerunError instanceof Error ? rerunError.message : "Errore rerun job Terreni");
    } finally {
      setTerreniJobBusyId(null);
    }
  }

  async function handleDeleteJob(jobId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setTerreniDeletingJobId(jobId);
    try {
      await deleteCapacitasTerreniJob(token, jobId);
      setTerreniStatusMessage(`Job #${jobId} eliminato.`);
      setTerreniError(null);
      setTerreniJobs((current) => current.filter((job) => job.id !== jobId));
    } catch (deleteError) {
      setTerreniError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione job Terreni");
    } finally {
      setTerreniDeletingJobId(null);
    }
  }

  async function handleCreateParticelleSyncJob(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setParticelleCreatingJob(true);
    try {
      const job = await createCapacitasParticelleSyncJob(token, {
        credential_id: particelleSyncForm.credential_id ? Number.parseInt(particelleSyncForm.credential_id, 10) : undefined,
        only_due: particelleSyncForm.only_due,
        limit: particelleSyncForm.limit.trim() ? Number.parseInt(particelleSyncForm.limit, 10) : undefined,
        fetch_certificati: particelleSyncForm.fetch_certificati,
        fetch_details: particelleSyncForm.fetch_details,
        double_speed: particelleSyncForm.double_speed,
        parallel_workers: particelleSyncForm.parallel_workers,
      });
      setParticelleMonitorSessionExpired(false);
      setParticelleStatusMessage(
        `Job progressivo particelle #${job.id} creato in ${particelleSyncForm.double_speed ? "doppia velocita" : "velocita standard"} con ${particelleSyncForm.parallel_workers} worker e avviato in background.`,
      );
      setParticelleError(null);
      await loadParticelleJobs();
    } catch (createError) {
      setParticelleError(createError instanceof Error ? createError.message : "Errore avvio job particelle");
    } finally {
      setParticelleCreatingJob(false);
    }
  }

  async function handleRerunParticelleJob(jobId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setParticelleJobBusyId(jobId);
    try {
      await rerunCapacitasParticelleSyncJob(token, jobId);
      setParticelleMonitorSessionExpired(false);
      setParticelleStatusMessage(`Job particelle #${jobId} rilanciato.`);
      setParticelleError(null);
      await loadParticelleJobs();
    } catch (rerunError) {
      setParticelleError(rerunError instanceof Error ? rerunError.message : "Errore rerun job particelle");
    } finally {
      setParticelleJobBusyId(null);
    }
  }

  async function handleDeleteParticelleJob(jobId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setParticelleDeletingJobId(jobId);
    try {
      await deleteCapacitasParticelleSyncJob(token, jobId);
      setParticelleStatusMessage(`Job particelle #${jobId} eliminato.`);
      setParticelleError(null);
      setParticelleJobs((current) => current.filter((job) => job.id !== jobId));
    } catch (deleteError) {
      setParticelleError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione job particelle");
    } finally {
      setParticelleDeletingJobId(null);
    }
  }

  async function handleParseTerreniBatchFile(file: File): Promise<void> {
    setTerreniBatchBusy(true);
    setTerreniBatchError(null);
    try {
      const parsed = await readTerreniBatchFile(file);
      if (parsed.items.length === 0) {
        throw new Error("File vuoto o senza righe valide per il batch Terreni.");
      }
      setTerreniBatchItems(parsed.items);
      setTerreniBatchSkipped(parsed.skipped);
      setTerreniStatusMessage(`File caricato: ${parsed.items.length} righe pronte per il job batch.`);
    } catch (parseError) {
      setTerreniBatchItems([]);
      setTerreniBatchSkipped(0);
      setTerreniBatchError(parseError instanceof Error ? parseError.message : "Errore parsing file Terreni");
    } finally {
      setTerreniBatchBusy(false);
    }
  }

  async function handleCreateTerreniBatchJob(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || terreniBatchItems.length === 0) return;

    setTerreniBatchCreatingJob(true);
    setTerreniBatchError(null);
    try {
      const job = await createCapacitasTerreniJob(token, {
        credential_id: terreniForm.credential_id ? Number.parseInt(terreniForm.credential_id, 10) : undefined,
        continue_on_error: terreniBatchContinueOnError,
        fetch_certificati: terreniBatchFetchCertificati,
        fetch_details: terreniBatchFetchDetails,
        double_speed: terreniExecutionForm.double_speed,
        parallel_workers: terreniExecutionForm.parallel_workers,
        throttle_ms: terreniExecutionForm.throttle_ms.trim() ? Number.parseInt(terreniExecutionForm.throttle_ms, 10) : undefined,
        auto_resume: terreniExecutionForm.auto_resume,
        items: terreniBatchItems,
      });
      setTerreniMonitorSessionExpired(false);
      setTerreniStatusMessage(
        `Job batch #${job.id} creato con ${terreniBatchItems.length} righe in ${terreniExecutionForm.double_speed ? "doppia velocita" : "velocita standard"} e ${terreniExecutionForm.parallel_workers} worker${terreniExecutionForm.throttle_ms.trim() ? ` · pausa ${terreniExecutionForm.throttle_ms.trim()}ms` : ""}${terreniExecutionForm.auto_resume ? " · auto-resume attivo" : ""}.`,
      );
      await loadTerreniJobs();
    } catch (createError) {
      setTerreniBatchError(createError instanceof Error ? createError.message : "Errore avvio job batch Terreni");
    } finally {
      setTerreniBatchCreatingJob(false);
    }
  }

  function parseManualHistoryItems(): CapacitasAnagraficaHistoryImportItemInput[] {
    const subjectIds = historyForm.subject_ids
      .split(/[\n,;\t ]+/)
      .map((value) => value.trim())
      .filter(Boolean);
    const idxanaList = historyForm.idxana_list
      .split(/[\n,;\t ]+/)
      .map((value) => value.trim())
      .filter(Boolean);

    return [
      ...subjectIds.map((subject_id) => ({ subject_id, idxana: null })),
      ...idxanaList.map((idxana) => ({ subject_id: null, idxana })),
    ];
  }

  async function handleParseHistoryBatchFile(file: File): Promise<void> {
    setHistoryBatchBusy(true);
    setHistoryError(null);
    try {
      const parsed = await readAnagraficaHistoryBatchFile(file);
      if (parsed.items.length === 0) {
        throw new Error("File vuoto o senza righe valide per lo storico anagrafico.");
      }
      setHistoryBatchItems(parsed.items);
      setHistoryBatchSkipped(parsed.skipped);
      setHistoryStatusMessage(`File storico caricato: ${parsed.items.length} righe pronte per l'import.`);
    } catch (parseError) {
      setHistoryBatchItems([]);
      setHistoryBatchSkipped(0);
      setHistoryError(parseError instanceof Error ? parseError.message : "Errore parsing file storico anagrafico");
    } finally {
      setHistoryBatchBusy(false);
    }
  }

  async function handleImportAnagraficaHistory(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setHistoryImporting(true);
    setHistoryError(null);
    try {
      const credentialId = historyForm.credential_id ? Number.parseInt(historyForm.credential_id, 10) : undefined;
      const items = historyMode === "file" ? historyBatchItems : parseManualHistoryItems();
      const job = await createCapacitasAnagraficaHistoryJob(token, {
        credential_id: credentialId,
        continue_on_error: historyForm.continue_on_error,
        auto_resume: true,
        items,
      });
      setHistoryMonitorSessionExpired(false);
      setHistoryStatusMessage(`Job storico #${job.id} creato con ${items.length} righe e avviato in background.`);
      await loadHistoryJobs();
    } catch (importError) {
      setHistoryError(importError instanceof Error ? importError.message : "Errore import storico anagrafico");
    } finally {
      setHistoryImporting(false);
    }
  }

  async function handleRerunHistoryJob(jobId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setHistoryJobBusyId(jobId);
    try {
      await rerunCapacitasAnagraficaHistoryJob(token, jobId);
      setHistoryMonitorSessionExpired(false);
      setHistoryStatusMessage(`Job storico #${jobId} rilanciato.`);
      setHistoryError(null);
      await loadHistoryJobs();
    } catch (rerunError) {
      setHistoryError(rerunError instanceof Error ? rerunError.message : "Errore rerun job storico anagrafico");
    } finally {
      setHistoryJobBusyId(null);
    }
  }

  async function handleDeleteHistoryJob(jobId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setHistoryDeletingJobId(jobId);
    try {
      await deleteCapacitasAnagraficaHistoryJob(token, jobId);
      setHistoryStatusMessage(`Job storico #${jobId} eliminato.`);
      setHistoryError(null);
      setHistoryJobs((current) => current.filter((job) => job.id !== jobId));
    } catch (deleteError) {
      setHistoryError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione job storico anagrafico");
    } finally {
      setHistoryDeletingJobId(null);
    }
  }

  const content = (
    <>
      <div className="space-y-6">
        <ElaborazioneHero
          compact={embedded}
          badge={
            <>
              <UsersIcon className="h-3.5 w-3.5" />
              Capacitas inVOLTURE
            </>
          }
          title={embedded ? "Ricerca inVOLTURE" : "Ricerca anagrafica e Terreni sul portale inVOLTURE usando il pool account del modulo Elaborazioni."}
          description={
            embedded
              ? "Esegui ricerche anagrafiche o Terreni e controlla il risultato usando il pool credenziali."
              : "La schermata mette in evidenza il pool disponibile, la credenziale effettiva selezionata e i nuovi job Terreni in background in un layout coerente con il resto del modulo."
          }
          actions={
            error || terreniError ? (
              <ElaborazioneNoticeCard compact={embedded} title="Errore operativo" description={error ?? terreniError ?? "Errore sconosciuto"} tone="danger" />
            ) : (
              <>
                <ElaborazioneNoticeCard
                  compact={embedded}
                  title="Credenziali dedicate"
                  description="Se non selezioni un account manualmente, il backend sceglie una credenziale attiva nella finestra oraria corretta."
                />
                <button className="btn-secondary" onClick={() => setSettingsModalOpen(true)} type="button">
                  Apri Credenziali
                </button>
              </>
            )
          }
        >
          <div className="grid gap-3 sm:grid-cols-4">
            <ElaborazioneMiniStat compact={embedded} eyebrow="Pool" value={`${activeCredentialsCount}/${credentials.length}`} description="Account attivi sul totale configurato." />
            <ElaborazioneMiniStat compact={embedded} eyebrow="Ricerca anagrafica" value={results?.total ?? 0} description="Record restituiti dall'ultima ricerca." tone={results && results.total > 0 ? "success" : "default"} />
            <ElaborazioneMiniStat compact={embedded} eyebrow="Preview Terreni" value={terreniBatchItems.length} description="Righe Terreni dell'ultima preview." tone={terreniBatchItems.length > 0 ? "success" : "default"} />
            <ElaborazioneMiniStat compact={embedded} eyebrow="Job Terreni" value={terreniJobs.length} description={jobsInFlight ? "Sono presenti job in corso." : "Nessun job in esecuzione."} tone={jobsInFlight ? "warning" : "default"} />
          </div>
        </ElaborazioneHero>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <LockIcon className="h-3.5 w-3.5" />
                Ricerca anagrafica
              </>
            }
            title="Parametri della query inVOLTURE"
            description="Usa Codice fiscale per ricerche puntuali oppure modalità lessicali sulla denominazione."
          />
          <div className="p-6">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <label className="space-y-2 xl:col-span-2">
                <span className="label-caption">Valore ricerca</span>
                <input
                  className="form-control"
                  placeholder="Codice fiscale, denominazione, CCO~FRA~CCS..."
                  value={formState.q}
                  onChange={(event) => setFormState((current) => ({ ...current, q: event.target.value }))}
                />
              </label>
              <label className="space-y-2">
                <span className="label-caption">Tipo ricerca</span>
                <select
                  className="form-control"
                  value={formState.tipo_ricerca}
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      tipo_ricerca: Number.parseInt(event.target.value, 10),
                    }))
                  }
                >
                  {SEARCH_TYPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-2">
                <span className="label-caption">Credenziale</span>
                <select
                  className="form-control"
                  value={formState.credential_id}
                  onChange={(event) => setFormState((current) => ({ ...current, credential_id: event.target.value }))}
                >
                  <option value="">Auto-selezione backend</option>
                  {credentials.map((credential) => (
                    <option key={credential.id} value={credential.id}>
                      {credential.label} · {credential.username}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
                <input
                  checked={formState.solo_con_beni}
                  className="h-4 w-4 accent-[#1D4E35]"
                  type="checkbox"
                  onChange={(event) => setFormState((current) => ({ ...current, solo_con_beni: event.target.checked }))}
                />
                <span className="text-sm text-gray-700">Solo soggetti con beni</span>
              </label>
              <button
                className="btn-primary"
                disabled={searching || !formState.q.trim() || loadingCredentials}
                onClick={() => void handleSearch()}
                type="button"
              >
                {searching ? "Ricerca in corso..." : "Avvia ricerca"}
              </button>
              {activeCredential ? (
                <span className="text-xs text-gray-500">
                  Credenziale forzata: {activeCredential.label} · fascia {activeCredential.allowed_hours_start}:00-
                  {activeCredential.allowed_hours_end}:00
                </span>
              ) : (
                <span className="text-xs text-gray-500">
                  Se non forzi un account, il backend seleziona automaticamente una credenziale attiva nella fascia oraria corrente.
                </span>
              )}
            </div>
          </div>
        </article>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <RefreshIcon className="h-3.5 w-3.5" />
                Sync particelle
              </>
            }
            title="Sincronizzazione progressiva particelle GAIA"
            description="Rilegge progressivamente le particelle correnti gia presenti a database, traccia l'ultima data di sync e usa una politica piu aggressiva solo dopo le 19:00."
            actions={
              <button className="btn-secondary" disabled={particelleJobsLoading} onClick={() => void loadParticelleJobs()} type="button">
                <RefreshIcon className="mr-2 h-4 w-4" />
                Aggiorna job
              </button>
            }
          />
          <div className="space-y-6 p-6">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-7">
              <label className="space-y-2">
                <span className="label-caption">Credenziale</span>
                <select
                  className="form-control"
                  value={particelleSyncForm.credential_id}
                  onChange={(event) => setParticelleSyncForm((current) => ({ ...current, credential_id: event.target.value }))}
                >
                  <option value="">Auto-selezione backend</option>
                  {credentials.map((credential) => (
                    <option key={credential.id} value={credential.id}>
                      {credential.label} · {credential.username}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-2">
                <span className="label-caption">Limite run</span>
                <input
                  className="form-control"
                  placeholder="Vuoto = tutte le dovute"
                  value={particelleSyncForm.limit}
                  onChange={(event) => setParticelleSyncForm((current) => ({ ...current, limit: event.target.value }))}
                />
              </label>
              <label className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
                <input
                  checked={particelleSyncForm.only_due}
                  className="h-4 w-4 accent-[#1D4E35]"
                  type="checkbox"
                  onChange={(event) => setParticelleSyncForm((current) => ({ ...current, only_due: event.target.checked }))}
                />
                <span className="text-sm text-gray-700">Solo particelle dovute</span>
              </label>
              <label className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
                <input
                  checked={particelleSyncForm.fetch_certificati}
                  className="h-4 w-4 accent-[#1D4E35]"
                  type="checkbox"
                  onChange={(event) => setParticelleSyncForm((current) => ({ ...current, fetch_certificati: event.target.checked }))}
                />
                <span className="text-sm text-gray-700">Scarica certificati</span>
              </label>
              <label className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
                <input
                  checked={particelleSyncForm.fetch_details}
                  className="h-4 w-4 accent-[#1D4E35]"
                  type="checkbox"
                  onChange={(event) => setParticelleSyncForm((current) => ({ ...current, fetch_details: event.target.checked }))}
                />
                <span className="text-sm text-gray-700">Scarica dettagli</span>
              </label>
              <button
                className={
                  particelleSyncForm.double_speed
                    ? "rounded-lg border border-[#1D4E35] bg-[#eef7ef] px-4 py-3 text-left text-sm font-semibold text-[#1D4E35]"
                    : "rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 text-left text-sm font-semibold text-gray-700 transition hover:border-[#1D4E35]/30 hover:bg-[#f5faf5]"
                }
                onClick={() => setParticelleSyncForm((current) => ({ ...current, double_speed: !current.double_speed }))}
                type="button"
              >
                <span className="block">{particelleSyncForm.double_speed ? "Doppia velocita attiva" : "Doppia velocita"}</span>
                <span className="mt-1 block text-xs font-normal text-gray-500">
                  {particelleSyncForm.double_speed ? "Pausa dimezzata per questo job." : "Porta la pausa diurna da 900ms a 450ms."}
                </span>
              </button>
              <button
                className={
                  particelleSyncForm.parallel_workers > 1
                    ? "rounded-lg border border-[#1D4E35] bg-[#eef7ef] px-4 py-3 text-left text-sm font-semibold text-[#1D4E35]"
                    : "rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 text-left text-sm font-semibold text-gray-700 transition hover:border-[#1D4E35]/30 hover:bg-[#f5faf5]"
                }
                onClick={() =>
                  setParticelleSyncForm((current) => ({
                    ...current,
                    parallel_workers: current.parallel_workers > 1 ? 1 : 2,
                  }))
                }
                type="button"
              >
                <span className="block">{particelleSyncForm.parallel_workers > 1 ? "Parallelo x2 attivo" : "Parallelo x2"}</span>
                <span className="mt-1 block text-xs font-normal text-gray-500">
                  {particelleSyncForm.parallel_workers > 1 ? "Usa 2 sessioni Capacitas dedicate." : "Divide il job su 2 worker."}
                </span>
              </button>
            </div>

            {particelleError ? (
              <div className="rounded-2xl border border-rose-100 bg-rose-50/70 px-4 py-3 text-sm text-rose-800">{particelleError}</div>
            ) : null}
            {particelleStatusMessage ? (
              <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 px-4 py-3 text-sm text-emerald-800">{particelleStatusMessage}</div>
            ) : null}

            <div className="flex flex-wrap items-center gap-3">
              <button className="btn-primary" disabled={particelleCreatingJob} onClick={() => void handleCreateParticelleSyncJob()} type="button">
                {particelleCreatingJob ? "Avvio..." : "Avvia sync progressiva"}
              </button>
              <span className="text-xs text-gray-500">
                Di giorno rientrano soprattutto particelle non sincronizzate nelle ultime 24h. La pausa base e 900ms; con doppia velocita diventa 450ms. Il parallelo x2 apre due sessioni Capacitas dedicate e divide la coda.
              </span>
            </div>
          </div>
        </article>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <ServerIcon className="h-3.5 w-3.5" />
                Job particelle
              </>
            }
            title="Monitor sync progressiva particelle"
            description="Polling del job catalogo particelle con barra percentuale, finestra oraria attiva e dettaglio degli ultimi record processati."
          />
          {particelleJobsLoading ? (
            <div className="p-5 text-sm text-gray-500">Caricamento job particelle...</div>
          ) : particelleJobs.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={ServerIcon}
                title="Nessun job particelle registrato"
                description="Avvia la prima sync progressiva per popolare lo storico dei job e tenere in linea il catalogo particelle."
              />
            </div>
          ) : (
            <div className="space-y-4 p-6">
              {particelleJobs.map((job) => {
                const result = isParticelleSyncJobResult(job.result_json) ? job.result_json : null;
                const tone = renderJobStatus(job.status);
                return (
                  <div className="rounded-[24px] border border-gray-100 bg-[#fbfcfb] p-5" key={job.id}>
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-semibold text-gray-900">Job #{job.id}</span>
                          <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${tone.className}`}>
                            {tone.label}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-gray-500">
                          creato {formatDateTime(job.created_at)} · start {formatDateTime(job.started_at)} · end {formatDateTime(job.completed_at)}
                        </p>
                        {result ? (
                          <p className="mt-2 text-sm text-gray-600">
                            {result.aggressive_window ? "Fascia serale aggressiva" : "Fascia diurna conservativa"} · pausa {result.throttle_ms} ms
                            {result.speed_multiplier && result.speed_multiplier > 1 ? ` · velocita x${result.speed_multiplier}` : ""} · worker {result.parallel_workers ?? 1} · ricontrollo target {result.recheck_hours}h
                            {job.status === "queued_resume" ? " · resume automatico pianificato dopo restart backend" : ""}
                          </p>
                        ) : null}
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <button className="btn-secondary" disabled={particelleJobBusyId === job.id} onClick={() => void handleRerunParticelleJob(job.id)} type="button">
                          {particelleJobBusyId === job.id ? "Rerun..." : "Rilancia"}
                        </button>
                        <button
                          className="btn-secondary"
                          disabled={
                            particelleDeletingJobId === job.id ||
                            job.status === "pending" ||
                            job.status === "processing" ||
                            job.status === "queued_resume"
                          }
                          onClick={() => void handleDeleteParticelleJob(job.id)}
                          type="button"
                        >
                          {particelleDeletingJobId === job.id ? "Elimina..." : "Elimina"}
                        </button>
                      </div>
                    </div>

                    {result ? (
                      <>
                        <div className="mt-4 flex items-center justify-between gap-3">
                          <div>
                            <p className="text-sm font-medium text-gray-900">
                              <span className="font-semibold">{result.processed_items}</span> / {result.total_items} particelle processate
                            </p>
                            <p className="mt-1 text-xs text-gray-500">
                              ok {result.success_items} · skipped {result.skipped_items} · failed {result.failed_items}
                              {result.current_label ? ` · in corso: ${result.current_label}` : ""}
                            </p>
                          </div>
                          <div className="rounded-full bg-white px-3 py-1 text-sm font-semibold text-[#1D4E35] shadow-sm">{result.progress_percent}%</div>
                        </div>
                        <div className="mt-3 h-3 overflow-hidden rounded-full bg-[#dfe9df]">
                          <div className="h-full rounded-full bg-[#1D4E35] transition-all duration-500" style={{ width: `${result.progress_percent}%` }} />
                        </div>
                        <div className="mt-4 overflow-x-auto">
                          <table className="data-table">
                            <thead>
                              <tr>
                                <th>Particella</th>
                                <th>Stato</th>
                                <th>Messaggio</th>
                              </tr>
                            </thead>
                            <tbody>
                              {result.recent_items.slice().reverse().slice(0, 8).map((item) => (
                                <tr key={`${job.id}-${item.particella_id}-${item.label}`}>
                                  <td className="font-medium text-gray-900">{item.label}</td>
                                  <td>
                                    <span
                                      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${
                                        item.status === "synced"
                                          ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                                          : item.status === "failed"
                                            ? "bg-rose-50 text-rose-700 ring-rose-200"
                                            : "bg-amber-50 text-amber-700 ring-amber-200"
                                      }`}
                                    >
                                      {item.status}
                                    </span>
                                  </td>
                                  <td className="text-sm text-gray-700">{item.message}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </>
                    ) : job.error_detail ? (
                      <div className="mt-4 text-sm text-rose-700">{job.error_detail}</div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </article>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <SearchIcon className="h-3.5 w-3.5" />
                Risultati ricerca
              </>
            }
            title={results == null ? "Nessuna ricerca eseguita" : `${results.total} record restituiti dal portale`}
            description="I risultati sono riportati così come esposti da inVOLTURE, senza reinterpretazione lato frontend."
          />
          {results == null ? (
            <div className="p-5">
              <EmptyState
                icon={SearchIcon}
                title="Avvia una ricerca Capacitas"
                description="Inserisci un criterio e lancia una ricerca per vedere gli anagrafici restituiti da inVOLTURE."
              />
            </div>
          ) : results.rows.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={SearchIcon}
                title="Nessun risultato"
                description="Il portale non ha restituito anagrafiche compatibili con i parametri selezionati."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Nominativo</th>
                    <th>Codice fiscale</th>
                    <th>Partita IVA</th>
                    <th>Comune</th>
                    <th>CCO</th>
                    <th>Patrimonio</th>
                    <th>Meta</th>
                  </tr>
                </thead>
                <tbody>
                  {results.rows.map((row, index) => (
                    <tr key={`${row.CCO ?? row.IDXANA ?? row.id ?? index}`}>
                      <td className="font-medium text-gray-900">{renderIdentity(row)}</td>
                      <td>{row.CodiceFiscale ?? "—"}</td>
                      <td>{row.PartitaIva ?? "—"}</td>
                      <td>{row.Comune ?? "—"}</td>
                      <td>{row.CCO ?? "—"}</td>
                      <td>{row.Patrimonio ?? "—"}</td>
                      <td className="text-xs text-gray-500">
                        {row.Stato ?? "—"} · {row.IDXANA ?? row.id ?? "n/d"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <UsersIcon className="h-3.5 w-3.5" />
                Storico anagrafico
              </>
            }
            title="Import storico anagrafiche Capacitas"
            description="Recupera lo storico remoto Involture partendo da subject_id GAIA, IDXANA o file batch e persiste gli snapshot in anagrafica."
            actions={
              <button className="btn-secondary" disabled={historyJobsLoading} onClick={() => void loadHistoryJobs()} type="button">
                <RefreshIcon className="mr-2 h-4 w-4" />
                Aggiorna job
              </button>
            }
          />
          <div className="space-y-6 p-6">
            <div className="flex flex-wrap gap-2">
              <button className={historyMode === "manual" ? "btn-primary" : "btn-secondary"} onClick={() => setHistoryMode("manual")} type="button">
                Manuale
              </button>
              <button className={historyMode === "file" ? "btn-primary" : "btn-secondary"} onClick={() => setHistoryMode("file")} type="button">
                Batch da file
              </button>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <label className="space-y-2">
                <span className="label-caption">Credenziale</span>
                <select
                  className="form-control"
                  value={historyForm.credential_id}
                  onChange={(event) => setHistoryForm((current) => ({ ...current, credential_id: event.target.value }))}
                >
                  <option value="">Auto-selezione backend</option>
                  {credentials.map((credential) => (
                    <option key={credential.id} value={credential.id}>
                      {credential.label} · {credential.username}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 xl:col-span-2">
                <input
                  checked={historyForm.continue_on_error}
                  className="h-4 w-4 accent-[#1D4E35]"
                  type="checkbox"
                  onChange={(event) => setHistoryForm((current) => ({ ...current, continue_on_error: event.target.checked }))}
                />
                <span className="text-sm text-gray-700">Continua se una riga fallisce</span>
              </label>
              {historyMode === "file" ? (
                <div className="flex flex-wrap gap-2 xl:justify-end">
                  <button className="btn-secondary" onClick={() => downloadAnagraficaHistoryTemplate("xlsx")} type="button">
                    Template Excel
                  </button>
                  <button className="btn-secondary" onClick={() => downloadAnagraficaHistoryTemplate("csv")} type="button">
                    Template CSV
                  </button>
                </div>
              ) : null}
            </div>

            {historyMode === "manual" ? (
              <div className="grid gap-4 lg:grid-cols-2">
                <label className="space-y-2">
                  <span className="label-caption">Lista subject_id</span>
                  <textarea
                    className="form-control min-h-36"
                    placeholder="Uno per riga o separati da virgola"
                    value={historyForm.subject_ids}
                    onChange={(event) => setHistoryForm((current) => ({ ...current, subject_ids: event.target.value }))}
                  />
                </label>
                <label className="space-y-2">
                  <span className="label-caption">Lista IDXANA</span>
                  <textarea
                    className="form-control min-h-36"
                    placeholder="Uno per riga o separati da virgola"
                    value={historyForm.idxana_list}
                    onChange={(event) => setHistoryForm((current) => ({ ...current, idxana_list: event.target.value }))}
                  />
                </label>
              </div>
            ) : (
              <div className="rounded-[24px] border border-dashed border-[#cfd8cf] bg-[#f8fbf8] p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-2">
                    <p className="text-sm font-semibold text-gray-900">Import batch subject_id / idxana</p>
                    <p className="text-sm text-gray-600">
                      Carica un file Excel o CSV con colonne <span className="font-medium text-gray-900">subject_id</span> e/o <span className="font-medium text-gray-900">idxana</span>.
                    </p>
                  </div>
                  <button
                    className="btn-secondary"
                    disabled={historyBatchBusy || historyBatchItems.length === 0}
                    onClick={() => {
                      setHistoryBatchFile(null);
                      setHistoryBatchItems([]);
                      setHistoryBatchSkipped(0);
                      setHistoryError(null);
                    }}
                    type="button"
                  >
                    Reset
                  </button>
                </div>

                <label className="mt-4 block space-y-2">
                  <span className="label-caption">File batch</span>
                  <input
                    accept=".xlsx,.xls,.csv"
                    className="form-control"
                    disabled={historyBatchBusy}
                    type="file"
                    onChange={(event) => {
                      const file = event.target.files?.[0] ?? null;
                      setHistoryBatchFile(file);
                      if (!file) {
                        setHistoryBatchItems([]);
                        setHistoryBatchSkipped(0);
                        setHistoryError(null);
                        return;
                      }
                      void handleParseHistoryBatchFile(file);
                    }}
                  />
                </label>
              </div>
            )}

            {historyError ? (
              <div className="rounded-2xl border border-rose-100 bg-rose-50/70 px-4 py-3 text-sm text-rose-800">{historyError}</div>
            ) : null}
            {historyStatusMessage ? (
              <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 px-4 py-3 text-sm text-emerald-800">{historyStatusMessage}</div>
            ) : null}

            <div className="flex flex-wrap items-center gap-3">
              <button
                className="btn-primary"
                disabled={
                  historyImporting ||
                  (historyMode === "manual"
                    ? parseManualHistoryItems().length === 0
                    : historyBatchItems.length === 0 || historyBatchFile == null)
                }
                onClick={() => void handleImportAnagraficaHistory()}
                type="button"
              >
                {historyImporting ? "Import in corso..." : "Avvia import storico"}
              </button>
              <span className="text-sm text-gray-500">
                {historyMode === "manual"
                  ? `${parseManualHistoryItems().length} righe pronte`
                  : historyBatchFile
                    ? `${historyBatchItems.length} righe pronte${historyBatchSkipped > 0 ? ` · ${historyBatchSkipped} vuote saltate` : ""}`
                    : "Nessun file selezionato"}
              </span>
            </div>
          </div>
        </article>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <ServerIcon className="h-3.5 w-3.5" />
                Job storico
              </>
            }
            title="Monitor import storico anagrafico"
            description="Job persistenti con auto-resume dopo restart backend e report progressivo per lo storico anagrafiche Capacitas."
          />
          {historyJobsLoading ? (
            <div className="p-5 text-sm text-gray-500">Caricamento job storico...</div>
          ) : historyJobs.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={ServerIcon}
                title="Nessun job storico registrato"
                description="Avvia un import storico manuale o batch per popolare il monitor dei job persistenti."
              />
            </div>
          ) : (
            <div className="space-y-4 p-6">
              {historyJobs.map((job) => {
                const tone = renderJobStatus(job.status);
                const result = isHistoryImportJobResult(job.result_json) ? job.result_json : null;
                const payloadItems = Array.isArray((job.payload_json as { items?: unknown[] } | null)?.items)
                  ? ((job.payload_json as { items?: unknown[] }).items?.length ?? 0)
                  : 0;
                const totalItems = payloadItems > 0 ? payloadItems : result ? Math.max(result.processed, 1) : 1;
                const progress = typeof (job.result_json as { progress_percent?: unknown } | null)?.progress_percent === "number"
                  ? Number((job.result_json as { progress_percent?: number }).progress_percent)
                  : result
                    ? Math.min(100, Math.max(0, Math.round((result.processed / totalItems) * 100)))
                    : 0;
                return (
                  <div className="rounded-[24px] border border-gray-100 bg-[#fbfcfb] p-5" key={job.id}>
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-semibold text-gray-900">Job #{job.id}</span>
                          <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${tone.className}`}>
                            {tone.label}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-gray-500">
                          creato {formatDateTime(job.created_at)} · start {formatDateTime(job.started_at)} · end {formatDateTime(job.completed_at)}
                        </p>
                        {job.status === "queued_resume" ? (
                          <p className="mt-2 text-sm text-gray-600">Resume automatico pianificato dopo restart backend.</p>
                        ) : null}
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <button className="btn-secondary" disabled={historyJobBusyId === job.id} onClick={() => void handleRerunHistoryJob(job.id)} type="button">
                          {historyJobBusyId === job.id ? "Rerun..." : "Rilancia"}
                        </button>
                        <button
                          className="btn-secondary"
                          disabled={
                            historyDeletingJobId === job.id ||
                            job.status === "pending" ||
                            job.status === "processing" ||
                            job.status === "queued_resume"
                          }
                          onClick={() => void handleDeleteHistoryJob(job.id)}
                          type="button"
                        >
                          {historyDeletingJobId === job.id ? "Elimina..." : "Elimina"}
                        </button>
                      </div>
                    </div>
                    {result ? (
                      <>
                        <div className="mt-4 flex items-center justify-between gap-3">
                          <div>
                            <p className="text-sm font-medium text-gray-900">
                              <span className="font-semibold">{result.processed}</span> processati · {result.snapshot_records_imported} snapshot
                            </p>
                            <p className="mt-1 text-xs text-gray-500">
                              imported {result.imported} · skipped {result.skipped} · failed {result.failed}
                            </p>
                          </div>
                          <div className="rounded-full bg-white px-3 py-1 text-sm font-semibold text-[#1D4E35] shadow-sm">{progress}%</div>
                        </div>
                        <div className="mt-3 h-3 overflow-hidden rounded-full bg-[#dfe9df]">
                          <div className="h-full rounded-full bg-[#1D4E35] transition-all duration-500" style={{ width: `${progress}%` }} />
                        </div>
                      </>
                    ) : job.error_detail ? (
                      <p className="mt-4 text-sm text-rose-700">{job.error_detail}</p>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </article>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <ServerIcon className="h-3.5 w-3.5" />
                Report storico
              </>
            }
            title={
              latestHistoryResult == null
                ? "Nessun report storico disponibile"
                : `${latestHistoryResult.processed} processati · ${latestHistoryResult.snapshot_records_imported} snapshot importati`
            }
            description="Report aggregato dell'ultima importazione storico anagrafico eseguita dal workspace Capacitas."
          />
          {latestHistoryResult == null ? (
            <div className="p-5">
              <EmptyState
                icon={ServerIcon}
                title="Nessun report disponibile"
                description="Esegui un'importazione manuale o batch per vedere conteggi e dettaglio dei record storici."
              />
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-px border-y border-gray-100 bg-gray-100 md:grid-cols-5">
                {(
                  [
                    ["Processed", latestHistoryResult.processed],
                    ["Imported", latestHistoryResult.imported],
                    ["Skipped", latestHistoryResult.skipped],
                    ["Failed", latestHistoryResult.failed],
                    ["Snapshot", latestHistoryResult.snapshot_records_imported],
                  ] as [string, number][]
                ).map(([label, value]) => (
                  <div className="bg-white px-6 py-3" key={label}>
                    <p className="text-xs text-gray-500">{label}</p>
                    <p className="mt-0.5 text-xl font-semibold text-gray-900">{value}</p>
                  </div>
                ))}
              </div>
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Input</th>
                      <th>Soggetto risolto</th>
                      <th>Stato</th>
                      <th>Storico</th>
                      <th>Messaggio</th>
                    </tr>
                  </thead>
                  <tbody>
                    {latestHistoryResult.items.map((item, index) => (
                      <tr key={`${item.subject_id ?? "none"}-${item.idxana ?? "none"}-${index}`}>
                        <td className="text-sm text-gray-700">
                          <div className="font-medium text-gray-900">{item.subject_id ?? "—"}</div>
                          <div className="text-xs text-gray-500">{item.idxana ?? "—"}</div>
                        </td>
                        <td className="text-xs text-gray-500">{item.resolved_subject_id ?? "—"}</td>
                        <td>
                          <span
                            className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${
                              item.status === "imported"
                                ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                                : item.status === "failed"
                                  ? "bg-rose-50 text-rose-700 ring-rose-200"
                                  : "bg-amber-50 text-amber-700 ring-amber-200"
                            }`}
                          >
                            {item.status}
                          </span>
                        </td>
                        <td className="text-sm text-gray-700">
                          {item.imported_records}/{item.history_records_total} importati
                          {item.skipped_records > 0 ? ` · ${item.skipped_records} skipped` : ""}
                        </td>
                        <td className="text-sm text-gray-700">{item.error ?? item.message ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </article>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <DocumentIcon className="h-3.5 w-3.5" />
                Terreni
              </>
            }
            title="Lookup territorio e sync Terreni"
            description="Carica un file Excel/CSV per creare un job batch Terreni; la sync singola ora vive direttamente nella scheda particella del Catasto."
            actions={
              <button className="btn-secondary" disabled={terreniJobsLoading} onClick={() => void loadTerreniJobs()} type="button">
                <RefreshIcon className="mr-2 h-4 w-4" />
                Aggiorna job
              </button>
            }
          />
          <div className="space-y-6 p-6">
            <div className="rounded-[24px] border border-dashed border-[#cfd8cf] bg-[#f8fbf8] p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-2">
                    <p className="text-sm font-semibold text-gray-900">Import massivo da Excel o CSV</p>
                    <p className="text-sm text-gray-600">
                      Carica un file con colonne standardizzate per creare un unico job batch Terreni. Colonne minime:
                      <span className="font-medium text-gray-900"> comune, foglio, particella</span>.
                    </p>
                    <p className="text-xs text-gray-500">
                      Il backend risolve il comune nella frazione Capacitas corretta. Se il nome e ambiguo, il job segnala l’errore e ti chiede un valore piu specifico.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button className="btn-secondary" onClick={() => downloadTerreniTemplate("xlsx")} type="button">
                      Template Excel
                    </button>
                    <button className="btn-secondary" onClick={() => downloadTerreniTemplate("csv")} type="button">
                      Template CSV
                    </button>
                    <button
                      className="btn-secondary"
                      disabled={terreniBatchBusy || terreniBatchItems.length === 0}
                      onClick={() => {
                        setTerreniBatchFile(null);
                        setTerreniBatchItems([]);
                        setTerreniBatchSkipped(0);
                        setTerreniBatchError(null);
                      }}
                      type="button"
                    >
                      Reset
                    </button>
                  </div>
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <label className="space-y-2">
                    <span className="label-caption">Credenziale</span>
                    <select
                      className="form-control"
                      value={terreniForm.credential_id}
                      onChange={(event) => setTerreniForm((current) => ({ ...current, credential_id: event.target.value }))}
                    >
                      <option value="">Auto-selezione backend</option>
                      {credentials.map((credential) => (
                        <option key={credential.id} value={credential.id}>
                          {credential.label} · {credential.username}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-2 xl:col-span-2">
                    <span className="label-caption">File batch</span>
                    <input
                      accept=".xlsx,.xls,.csv"
                      className="form-control"
                      disabled={terreniBatchBusy}
                      type="file"
                      onChange={(event) => {
                        const file = event.target.files?.[0] ?? null;
                        setTerreniBatchFile(file);
                        if (!file) {
                          setTerreniBatchItems([]);
                          setTerreniBatchSkipped(0);
                          setTerreniBatchError(null);
                          return;
                        }
                        void handleParseTerreniBatchFile(file);
                      }}
                    />
                  </label>
                  <label className="flex items-center gap-3 rounded-lg border border-gray-100 bg-white px-4 py-3">
                    <input
                      checked={terreniBatchContinueOnError}
                      className="h-4 w-4 accent-[#1D4E35]"
                      type="checkbox"
                      onChange={(event) => setTerreniBatchContinueOnError(event.target.checked)}
                    />
                    <span className="text-sm text-gray-700">Continua se una riga fallisce</span>
                  </label>
                  <label className="flex items-center gap-3 rounded-lg border border-gray-100 bg-white px-4 py-3">
                    <input
                      checked={terreniBatchFetchCertificati}
                      className="h-4 w-4 accent-[#1D4E35]"
                      type="checkbox"
                      onChange={(event) => setTerreniBatchFetchCertificati(event.target.checked)}
                    />
                    <span className="text-sm text-gray-700">Scarica certificati</span>
                  </label>
                  <label className="flex items-center gap-3 rounded-lg border border-gray-100 bg-white px-4 py-3">
                    <input
                      checked={terreniBatchFetchDetails}
                      className="h-4 w-4 accent-[#1D4E35]"
                      type="checkbox"
                      onChange={(event) => setTerreniBatchFetchDetails(event.target.checked)}
                    />
                    <span className="text-sm text-gray-700">Scarica dettagli terreno</span>
                  </label>
                </div>

                {terreniBatchError ? (
                  <div className="mt-4 rounded-2xl border border-rose-100 bg-rose-50/70 px-4 py-3 text-sm text-rose-800">
                    {terreniBatchError}
                  </div>
                ) : null}

                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    className="btn-primary"
                    disabled={terreniBatchBusy || terreniBatchCreatingJob || terreniBatchItems.length === 0}
                    onClick={() => void handleCreateTerreniBatchJob()}
                    type="button"
                  >
                    {terreniBatchCreatingJob ? "Avvio..." : "Avvia job batch"}
                  </button>
                  <span className="text-sm text-gray-500">
                    {terreniBatchFile ? (
                      <>
                        <span className="font-medium text-gray-800">{terreniBatchFile.name}</span> · {terreniBatchItems.length} righe pronte
                        {terreniBatchSkipped > 0 ? ` · ${terreniBatchSkipped} vuote saltate` : ""}
                      </>
                    ) : (
                      "Nessun file selezionato"
                    )}
                  </span>
                </div>
              </div>

            <div className="grid gap-4 xl:grid-cols-4">
              <button
                className={
                  terreniExecutionForm.double_speed
                    ? "rounded-lg border border-[#1D4E35] bg-[#eef7ef] px-4 py-3 text-left text-sm font-semibold text-[#1D4E35]"
                    : "rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 text-left text-sm font-semibold text-gray-700 transition hover:border-[#1D4E35]/30 hover:bg-[#f5faf5]"
                }
                onClick={() => setTerreniExecutionForm((current) => ({ ...current, double_speed: !current.double_speed }))}
                type="button"
              >
                <span className="block">{terreniExecutionForm.double_speed ? "Doppia velocita attiva" : "Doppia velocita"}</span>
                <span className="mt-1 block text-xs font-normal text-gray-500">
                  {terreniExecutionForm.double_speed ? "Riduce la pausa automatica del job Terreni." : "Usa una pausa piu aggressiva tra richieste e righe."}
                </span>
              </button>
              <button
                className={
                  terreniExecutionForm.parallel_workers > 1
                    ? "rounded-lg border border-[#1D4E35] bg-[#eef7ef] px-4 py-3 text-left text-sm font-semibold text-[#1D4E35]"
                    : "rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 text-left text-sm font-semibold text-gray-700 transition hover:border-[#1D4E35]/30 hover:bg-[#f5faf5]"
                }
                onClick={() =>
                  setTerreniExecutionForm((current) => ({
                    ...current,
                    parallel_workers: current.parallel_workers > 1 ? 1 : 2,
                  }))
                }
                type="button"
              >
                <span className="block">{terreniExecutionForm.parallel_workers > 1 ? "Parallelo x2 attivo" : "Parallelo x2"}</span>
                <span className="mt-1 block text-xs font-normal text-gray-500">
                  {terreniExecutionForm.parallel_workers > 1 ? "Apre 2 sessioni Capacitas dedicate per il job." : "Divide il batch su due worker concorrenti."}
                </span>
              </button>
              <label className="space-y-2 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
                <span className="label-caption">Pausa richieste (ms)</span>
                <input
                  className="form-control"
                  inputMode="numeric"
                  min={0}
                  placeholder="Auto"
                  value={terreniExecutionForm.throttle_ms}
                  onChange={(event) => setTerreniExecutionForm((current) => ({ ...current, throttle_ms: event.target.value.replace(/[^\d]/g, "") }))}
                />
                <span className="block text-xs text-gray-500">Vuoto = automatico. Valori piu bassi spingono di piu il portale.</span>
              </label>
              <button
                className={
                  terreniExecutionForm.auto_resume
                    ? "rounded-lg border border-[#1D4E35] bg-[#eef7ef] px-4 py-3 text-left text-sm font-semibold text-[#1D4E35]"
                    : "rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 text-left text-sm font-semibold text-gray-700 transition hover:border-[#1D4E35]/30 hover:bg-[#f5faf5]"
                }
                onClick={() => setTerreniExecutionForm((current) => ({ ...current, auto_resume: !current.auto_resume }))}
                type="button"
              >
                <span className="block">{terreniExecutionForm.auto_resume ? "Auto-resume attivo" : "Auto-resume"}</span>
                <span className="mt-1 block text-xs font-normal text-gray-500">
                  {terreniExecutionForm.auto_resume
                    ? "Il job batch viene ripianificato automaticamente dopo restart backend."
                    : "Mantiene il batch recuperabile al riavvio del backend."}
                </span>
              </button>
            </div>

            {terreniStatusMessage ? (
              <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 px-4 py-3 text-sm text-emerald-800">
                {terreniStatusMessage}
              </div>
            ) : null}
          </div>
        </article>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <DocumentIcon className="h-3.5 w-3.5" />
                Preview file
              </>
            }
            title={terreniBatchItems.length === 0 ? "Nessun file batch caricato" : `${terreniBatchItems.length} righe pronte per il job`}
            description={`Preview locale del file importato. Certificati: ${terreniBatchFetchCertificati ? "si" : "no"} · Dettagli: ${terreniBatchFetchDetails ? "si" : "no"}.`}
          />
          {terreniBatchItems.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={DocumentIcon}
                title="Carica un file batch"
                description="Scarica il template, compila le righe e carica il file per vedere la preview locale."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Label</th>
                    <th>Comune</th>
                    <th>Sezione</th>
                    <th>Foglio</th>
                    <th>Particella</th>
                    <th>Sub</th>
                  </tr>
                </thead>
                <tbody>
                  {terreniBatchItems.slice(0, 100).map((item, index) => (
                    <tr key={`${item.comune ?? ""}-${item.foglio}-${item.particella}-${item.sub ?? ""}-${index}`}>
                      <td className="font-medium text-gray-900">{item.label ?? "—"}</td>
                      <td>{item.comune ?? "—"}</td>
                      <td>{item.sezione || "—"}</td>
                      <td>{item.foglio}</td>
                      <td>{item.particella}</td>
                      <td>{item.sub || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <ServerIcon className="h-3.5 w-3.5" />
                Job Terreni
              </>
            }
            title="Monitor job Capacitas Terreni"
            description="Ogni job batch resta persistito, viene avviato subito in background e può essere rilanciato manualmente."
          />
          {terreniJobsLoading ? (
            <div className="p-5 text-sm text-gray-500">Caricamento job Terreni...</div>
          ) : terreniJobs.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={ServerIcon}
                title="Nessun job registrato"
                description="Avvia un primo sync Terreni per popolare lo storico job e monitorare gli stati di esecuzione."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Job</th>
                    <th>Stato</th>
                    <th>Creato</th>
                    <th>Timeline</th>
                    <th>Risultato</th>
                    <th>Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {terreniJobs.map((job) => {
                    const tone = renderJobStatus(job.status);
                    const result = isTerreniBatchResult(job.result_json) ? job.result_json : null;
                    return (
                      <tr key={job.id}>
                        <td>
                          <div className="font-medium text-gray-900">#{job.id}</div>
                          <div className="text-xs text-gray-500">
                            cred. {job.credential_id ?? "auto"} · richiedente {job.requested_by_user_id ?? "n/d"}
                          </div>
                        </td>
                        <td>
                          <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${tone.className}`}>
                            {tone.label}
                          </span>
                        </td>
                        <td>{formatDateTime(job.created_at)}</td>
                        <td className="text-xs text-gray-500">
                          start {formatDateTime(job.started_at)}
                          <br />
                          end {formatDateTime(job.completed_at)}
                        </td>
                        <td className="text-sm">
                          {result ? (
                            <div className="space-y-1">
                              <div>
                                {result.processed_items} item · {result.imported_rows} righe · {result.linked_units} unità
                              </div>
                              <div className="text-xs text-gray-500">
                                worker {result.parallel_workers ?? 1}
                                {result.speed_multiplier && result.speed_multiplier > 1 ? ` · velocita x${result.speed_multiplier}` : ""}
                                {typeof result.throttle_ms === "number" ? ` · pausa ${result.throttle_ms}ms` : ""}
                                {job.status === "queued_resume" ? " · resume automatico pianificato" : ""}
                              </div>
                              {result.failed_items > 0 ? <div className="text-amber-700">{result.failed_items} item con errore</div> : null}
                            </div>
                          ) : job.error_detail ? (
                            <span className="text-rose-700">{job.error_detail}</span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td>
                          <div className="flex flex-wrap items-center gap-2">
                            {result ? (
                              <button className="btn-secondary" onClick={() => setTerreniCompletedJobModal(job)} type="button">
                                Dettagli
                              </button>
                            ) : null}
                            {result && result.failed_items > 0 ? (
                              <button className="btn-secondary text-amber-700" onClick={() => setTerreniJobErrorsModal(job)} type="button">
                                Errori
                              </button>
                            ) : null}
                            <button className="btn-secondary" disabled={terreniJobBusyId === job.id} onClick={() => void handleRerunJob(job.id)} type="button">
                              {terreniJobBusyId === job.id ? "Rerun..." : "Rilancia"}
                            </button>
                            <button
                              className="btn-secondary"
                              disabled={
                                terreniDeletingJobId === job.id ||
                                job.status === "pending" ||
                                job.status === "processing" ||
                                job.status === "queued_resume"
                              }
                              onClick={() => void handleDeleteJob(job.id)}
                              type="button"
                            >
                              {terreniDeletingJobId === job.id ? "Elimina..." : "Elimina"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </article>
      </div>
      <ElaborazioneWorkspaceModal
        description="Configurazione credenziali aperta in modale per mantenere il contesto della ricerca Capacitas."
        href="/elaborazioni/settings"
        onClose={() => setSettingsModalOpen(false)}
        open={settingsModalOpen}
        title="Credenziali"
      />
      {terreniErrorsJob ? (
        <TerreniJobErrorsModal job={terreniErrorsJob} onClose={() => setTerreniJobErrorsModal(null)} />
      ) : null}
      {terreniReportJob ? (
        <TerreniJobCompletionModal
          job={terreniReportJob}
          onClose={() => setTerreniCompletedJobModal(null)}
          onShowErrors={(job) => {
            setTerreniCompletedJobModal(null);
            setTerreniJobErrorsModal(job);
          }}
        />
      ) : null}
    </>
  );

  if (embedded) {
    return content;
  }

  return (
    <ProtectedPage
      title="Capacitas inVOLTURE"
      description="Ricerca anagrafica e workspace Terreni operativo sul portale inVOLTURE usando il pool credenziali Capacitas."
      breadcrumb="Elaborazioni / Capacitas"
      requiredModule="catasto"
    >
      {content}
    </ProtectedPage>
  );
}
