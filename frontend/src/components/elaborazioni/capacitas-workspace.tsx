"use client";

import * as XLSX from "xlsx";
import { useEffect, useMemo, useState } from "react";

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
  createCapacitasTerreniJob,
  getCapacitasFogli,
  getCapacitasSezioni,
  listCapacitasCredentials,
  listCapacitasTerreniJobs,
  rerunCapacitasTerreniJob,
  searchCapacitasFrazioni,
  searchCapacitasInvolture,
  searchCapacitasTerreni,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type {
  CapacitasAnagrafica,
  CapacitasCredential,
  CapacitasLookupOption,
  CapacitasSearchResult,
  CapacitasTerreniBatchItemInput,
  CapacitasTerreniJob,
  CapacitasTerreniSearchResult,
  CapacitasTerrenoRow,
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

function renderTerrenoLabel(row: CapacitasTerrenoRow): string {
  const foglio = row.Foglio ?? "—";
  const particella = row.Partic ?? "—";
  const sub = row.Sub?.trim();
  return `${foglio}/${particella}${sub ? `/${sub}` : ""}`;
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
    default:
      return { label: "In attesa", className: "bg-slate-50 text-slate-700 ring-slate-200" };
  }
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

function isTerreniBatchResult(value: unknown): value is {
  processed_items: number;
  failed_items: number;
  imported_rows: number;
  linked_units: number;
} {
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

export function ElaborazioniCapacitasWorkspace({ embedded = false }: { embedded?: boolean }) {
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

  const [territoryQuery, setTerritoryQuery] = useState("");
  const [frazioni, setFrazioni] = useState<CapacitasLookupOption[]>([]);
  const [sezioni, setSezioni] = useState<CapacitasLookupOption[]>([]);
  const [fogli, setFogli] = useState<CapacitasLookupOption[]>([]);
  const [terreniResults, setTerreniResults] = useState<CapacitasTerreniSearchResult | null>(null);
  const [terreniJobs, setTerreniJobs] = useState<CapacitasTerreniJob[]>([]);
  const [terreniLookupBusy, setTerreniLookupBusy] = useState(false);
  const [terreniSearching, setTerreniSearching] = useState(false);
  const [terreniJobsLoading, setTerreniJobsLoading] = useState(false);
  const [terreniJobBusyId, setTerreniJobBusyId] = useState<number | null>(null);
  const [terreniCreatingJob, setTerreniCreatingJob] = useState(false);
  const [terreniError, setTerreniError] = useState<string | null>(null);
  const [terreniStatusMessage, setTerreniStatusMessage] = useState<string | null>(null);
  const [terreniMode, setTerreniMode] = useState<"manual" | "massive">("manual");
  const [terreniForm, setTerreniForm] = useState({
    credential_id: "",
    frazione_id: "",
    sezione: "",
    foglio: "",
    particella: "",
    sub: "",
    fetch_certificati: true,
    fetch_details: true,
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

  const activeCredential = useMemo(
    () => credentials.find((credential) => String(credential.id) === formState.credential_id) ?? null,
    [credentials, formState.credential_id],
  );
  const activeTerreniCredential = useMemo(
    () => credentials.find((credential) => String(credential.id) === terreniForm.credential_id) ?? null,
    [credentials, terreniForm.credential_id],
  );
  const activeCredentialsCount = credentials.filter((credential) => credential.active).length;
  const jobsInFlight = terreniJobs.some((job) => job.status === "pending" || job.status === "processing");

  useEffect(() => {
    void loadCredentials();
    void loadTerreniJobs();
  }, []);

  useEffect(() => {
    if (!jobsInFlight) return undefined;

    const timer = window.setInterval(() => {
      void loadTerreniJobs(true);
    }, JOB_POLL_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [jobsInFlight]);

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
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento credenziali Capacitas");
    } finally {
      setLoadingCredentials(false);
    }
  }

  async function loadTerreniJobs(silent = false): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    if (!silent) {
      setTerreniJobsLoading(true);
    }
    try {
      const nextJobs = await listCapacitasTerreniJobs(token);
      setTerreniJobs(nextJobs);
      if (!silent) {
        setTerreniError(null);
      }
    } catch (loadError) {
      if (!silent) {
        setTerreniError(loadError instanceof Error ? loadError.message : "Errore caricamento job Terreni");
      }
    } finally {
      if (!silent) {
        setTerreniJobsLoading(false);
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

  async function handleLookupFrazioni(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !territoryQuery.trim()) return;

    setTerreniLookupBusy(true);
    try {
      const options = await searchCapacitasFrazioni(
        token,
        territoryQuery.trim(),
        terreniForm.credential_id ? Number.parseInt(terreniForm.credential_id, 10) : undefined,
      );
      setFrazioni(options);
      setTerreniError(null);
      setTerreniStatusMessage(options.length > 0 ? `${options.length} frazioni trovate.` : "Nessuna frazione trovata.");
      if (options.length === 1) {
        await applyFrazioneSelection(options[0].id);
      }
    } catch (lookupError) {
      setTerreniError(lookupError instanceof Error ? lookupError.message : "Errore lookup frazioni Capacitas");
    } finally {
      setTerreniLookupBusy(false);
    }
  }

  async function loadSezioniAndFogli(frazioneId: string, sezioneValue = ""): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !frazioneId) return;

    const credentialId = terreniForm.credential_id ? Number.parseInt(terreniForm.credential_id, 10) : undefined;
    const [nextSezioni, nextFogli] = await Promise.all([
      getCapacitasSezioni(token, frazioneId, credentialId),
      getCapacitasFogli(token, frazioneId, sezioneValue, credentialId),
    ]);
    setSezioni(nextSezioni);
    setFogli(nextFogli);
  }

  async function applyFrazioneSelection(frazioneId: string): Promise<void> {
    setTerreniForm((current) => ({
      ...current,
      frazione_id: frazioneId,
      sezione: "",
      foglio: "",
    }));
    setSezioni([]);
    setFogli([]);
    try {
      await loadSezioniAndFogli(frazioneId);
    } catch (lookupError) {
      setTerreniError(lookupError instanceof Error ? lookupError.message : "Errore caricamento sezioni e fogli");
    }
  }

  async function handleSezioneChange(nextSezione: string): Promise<void> {
    setTerreniForm((current) => ({ ...current, sezione: nextSezione, foglio: "" }));
    if (!terreniForm.frazione_id) return;
    try {
      const token = getStoredAccessToken();
      if (!token) return;
      const credentialId = terreniForm.credential_id ? Number.parseInt(terreniForm.credential_id, 10) : undefined;
      const nextFogli = await getCapacitasFogli(token, terreniForm.frazione_id, nextSezione, credentialId);
      setFogli(nextFogli);
      setTerreniError(null);
    } catch (lookupError) {
      setTerreniError(lookupError instanceof Error ? lookupError.message : "Errore caricamento fogli");
    }
  }

  async function handleSearchTerreni(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !terreniForm.frazione_id) return;

    setTerreniSearching(true);
    try {
      const response = await searchCapacitasTerreni(token, {
        frazione_id: terreniForm.frazione_id,
        sezione: terreniForm.sezione || "",
        foglio: terreniForm.foglio || "",
        particella: terreniForm.particella.trim(),
        sub: terreniForm.sub.trim(),
        credential_id: terreniForm.credential_id ? Number.parseInt(terreniForm.credential_id, 10) : undefined,
      });
      setTerreniResults(response);
      setTerreniError(null);
      setTerreniStatusMessage(`Preview aggiornata: ${response.total} righe trovate.`);
    } catch (searchError) {
      setTerreniResults(null);
      setTerreniError(searchError instanceof Error ? searchError.message : "Errore ricerca Terreni");
    } finally {
      setTerreniSearching(false);
    }
  }

  async function handleCreateTerreniJob(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !terreniForm.frazione_id || !terreniForm.particella.trim()) return;

    setTerreniCreatingJob(true);
    try {
      const job = await createCapacitasTerreniJob(token, {
        credential_id: terreniForm.credential_id ? Number.parseInt(terreniForm.credential_id, 10) : undefined,
        items: [
          {
            label: `${terreniForm.foglio || "?"}/${terreniForm.particella.trim()}${terreniForm.sub.trim() ? `/${terreniForm.sub.trim()}` : ""}`,
            frazione_id: terreniForm.frazione_id,
            sezione: terreniForm.sezione || "",
            foglio: terreniForm.foglio || "",
            particella: terreniForm.particella.trim(),
            sub: terreniForm.sub.trim(),
            fetch_certificati: terreniForm.fetch_certificati,
            fetch_details: terreniForm.fetch_details,
          },
        ],
      });
      setTerreniStatusMessage(`Job #${job.id} creato e avviato in background.`);
      setTerreniError(null);
      await loadTerreniJobs();
    } catch (createError) {
      setTerreniError(createError instanceof Error ? createError.message : "Errore avvio job Terreni");
    } finally {
      setTerreniCreatingJob(false);
    }
  }

  async function handleRerunJob(jobId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setTerreniJobBusyId(jobId);
    try {
      await rerunCapacitasTerreniJob(token, jobId);
      setTerreniStatusMessage(`Job #${jobId} rilanciato.`);
      setTerreniError(null);
      await loadTerreniJobs();
    } catch (rerunError) {
      setTerreniError(rerunError instanceof Error ? rerunError.message : "Errore rerun job Terreni");
    } finally {
      setTerreniJobBusyId(null);
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
        items: terreniBatchItems,
      });
      setTerreniStatusMessage(`Job batch #${job.id} creato con ${terreniBatchItems.length} righe e avviato in background.`);
      await loadTerreniJobs();
    } catch (createError) {
      setTerreniBatchError(createError instanceof Error ? createError.message : "Errore avvio job batch Terreni");
    } finally {
      setTerreniBatchCreatingJob(false);
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
            <ElaborazioneMiniStat compact={embedded} eyebrow="Preview Terreni" value={terreniResults?.total ?? 0} description="Righe Terreni dell'ultima preview." tone={terreniResults && terreniResults.total > 0 ? "success" : "default"} />
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
                <DocumentIcon className="h-3.5 w-3.5" />
                Terreni
              </>
            }
            title="Lookup territorio e sync Terreni"
            description="Lavora in modalita manuale oppure carica un file Excel/CSV per creare un job batch Terreni senza compilare le righe una per una."
            actions={
              <button className="btn-secondary" disabled={terreniJobsLoading} onClick={() => void loadTerreniJobs()} type="button">
                <RefreshIcon className="mr-2 h-4 w-4" />
                Aggiorna job
              </button>
            }
          />
          <div className="space-y-6 p-6">
            <div className="flex flex-wrap gap-2">
              <button className={terreniMode === "manual" ? "btn-primary" : "btn-secondary"} onClick={() => setTerreniMode("manual")} type="button">
                Manuale
              </button>
              <button className={terreniMode === "massive" ? "btn-primary" : "btn-secondary"} onClick={() => setTerreniMode("massive")} type="button">
                Massiva da file
              </button>
            </div>

            {terreniMode === "manual" ? (
              <>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                  <label className="space-y-2 xl:col-span-2">
                    <span className="label-caption">Comune / frazione Capacitas</span>
                    <div className="flex gap-2">
                      <input
                        className="form-control"
                        placeholder="es. Uras, Oristano, Massama..."
                        value={territoryQuery}
                        onChange={(event) => setTerritoryQuery(event.target.value)}
                      />
                      <button className="btn-secondary shrink-0" disabled={terreniLookupBusy || !territoryQuery.trim()} onClick={() => void handleLookupFrazioni()} type="button">
                        {terreniLookupBusy ? "Lookup..." : "Cerca"}
                      </button>
                    </div>
                  </label>
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
                  <label className="space-y-2">
                    <span className="label-caption">Frazione selezionata</span>
                    <select
                      className="form-control"
                      value={terreniForm.frazione_id}
                      onChange={(event) => void applyFrazioneSelection(event.target.value)}
                    >
                      <option value="">Seleziona frazione</option>
                      {frazioni.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.display}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-2">
                    <span className="label-caption">Sezione</span>
                    <select
                      className="form-control"
                      disabled={!terreniForm.frazione_id}
                      value={terreniForm.sezione}
                      onChange={(event) => void handleSezioneChange(event.target.value)}
                    >
                      <option value="">Tutte</option>
                      {sezioni.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.display}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                  <label className="space-y-2">
                    <span className="label-caption">Foglio</span>
                    <select
                      className="form-control"
                      disabled={!terreniForm.frazione_id}
                      value={terreniForm.foglio}
                      onChange={(event) => setTerreniForm((current) => ({ ...current, foglio: event.target.value }))}
                    >
                      <option value="">Tutti</option>
                      {fogli.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.display}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-2">
                    <span className="label-caption">Particella</span>
                    <input
                      className="form-control"
                      placeholder="680"
                      value={terreniForm.particella}
                      onChange={(event) => setTerreniForm((current) => ({ ...current, particella: event.target.value }))}
                    />
                  </label>
                  <label className="space-y-2">
                    <span className="label-caption">Sub</span>
                    <input
                      className="form-control"
                      placeholder="facoltativo"
                      value={terreniForm.sub}
                      onChange={(event) => setTerreniForm((current) => ({ ...current, sub: event.target.value }))}
                    />
                  </label>
                  <label className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
                    <input
                      checked={terreniForm.fetch_certificati}
                      className="h-4 w-4 accent-[#1D4E35]"
                      type="checkbox"
                      onChange={(event) => setTerreniForm((current) => ({ ...current, fetch_certificati: event.target.checked }))}
                    />
                    <span className="text-sm text-gray-700">Scarica certificati</span>
                  </label>
                  <label className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
                    <input
                      checked={terreniForm.fetch_details}
                      className="h-4 w-4 accent-[#1D4E35]"
                      type="checkbox"
                      onChange={(event) => setTerreniForm((current) => ({ ...current, fetch_details: event.target.checked }))}
                    />
                    <span className="text-sm text-gray-700">Scarica dettagli terreno</span>
                  </label>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <button
                    className="btn-secondary"
                    disabled={terreniSearching || !terreniForm.frazione_id}
                    onClick={() => void handleSearchTerreni()}
                    type="button"
                  >
                    {terreniSearching ? "Preview..." : "Preview Terreni"}
                  </button>
                  <button
                    className="btn-primary"
                    disabled={terreniCreatingJob || !terreniForm.frazione_id || !terreniForm.particella.trim()}
                    onClick={() => void handleCreateTerreniJob()}
                    type="button"
                  >
                    {terreniCreatingJob ? "Avvio..." : "Avvia sync in background"}
                  </button>
                  {activeTerreniCredential ? (
                    <span className="text-xs text-gray-500">
                      Credenziale forzata: {activeTerreniCredential.label} · fascia {activeTerreniCredential.allowed_hours_start}:00-
                      {activeTerreniCredential.allowed_hours_end}:00
                    </span>
                  ) : (
                    <span className="text-xs text-gray-500">Anche per Terreni il backend puo selezionare automaticamente un account disponibile.</span>
                  )}
                </div>
              </>
            ) : (
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
            )}

            {terreniStatusMessage ? (
              <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 px-4 py-3 text-sm text-emerald-800">
                {terreniStatusMessage}
              </div>
            ) : null}
          </div>
        </article>

        {terreniMode === "manual" ? (
          <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
            <ElaborazionePanelHeader
              badge={
                <>
                  <SearchIcon className="h-3.5 w-3.5" />
                  Preview Terreni
                </>
              }
              title={terreniResults == null ? "Nessuna preview Terreni" : `${terreniResults.total} righe restituite da ricercaTerreni`}
              description="La preview consente di validare frazione, foglio e particella prima di creare il job di import."
            />
            {terreniResults == null ? (
              <div className="p-5">
                <EmptyState
                  icon={DocumentIcon}
                  title="Nessuna preview Terreni"
                  description="Esegui prima il lookup frazioni e poi lancia una preview per verificare le righe Terreni."
                />
              </div>
            ) : terreniResults.rows.length === 0 ? (
              <div className="p-5">
                <EmptyState
                  icon={SearchIcon}
                  title="Nessuna riga trovata"
                  description="La combinazione selezionata non ha prodotto risultati sulla griglia Terreni."
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Particella</th>
                      <th>CCO</th>
                      <th>Anno</th>
                      <th>Superficie</th>
                      <th>Riordino / stato</th>
                      <th>Meta</th>
                    </tr>
                  </thead>
                  <tbody>
                    {terreniResults.rows.map((row, index) => (
                      <tr key={`${row.ID ?? row.CCO ?? index}`}>
                        <td className="font-medium text-gray-900">{renderTerrenoLabel(row)}</td>
                        <td>{row.CCO ?? "—"}</td>
                        <td>{row.Anno ?? "—"}</td>
                        <td>{row.Superficie ?? "—"}</td>
                        <td>
                          <div className="flex flex-wrap items-center gap-2">
                            {row.BacDescr ? <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700">{row.BacDescr}</span> : null}
                            {row.row_visual_state ? (
                              <span className="rounded-full bg-[#eef5f1] px-2.5 py-1 text-xs text-[#1D4E35]">{row.row_visual_state}</span>
                            ) : null}
                          </div>
                        </td>
                        <td className="text-xs text-gray-500">
                          {row.COM ?? "—"} · {row.FRA ?? "—"} · {row.ID ?? "n/d"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </article>
        ) : (
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
                        <td>
                          {item.foglio}/{item.particella}
                        </td>
                        <td>{item.sub || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </article>
        )}

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
                            <button className="btn-secondary" disabled={terreniJobBusyId === job.id} onClick={() => void handleRerunJob(job.id)} type="button">
                              {terreniJobBusyId === job.id ? "Rerun..." : "Rilancia"}
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
