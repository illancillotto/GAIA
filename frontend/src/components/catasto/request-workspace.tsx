"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { ProtectedPage } from "@/components/app/protected-page";
import { CatastoHero, CatastoMiniStat, CatastoNoticeCard, CatastoPanelHeader } from "@/components/catasto/module-chrome";
import { CatastoStatusBadge } from "@/components/catasto/status-badge";
import { DocumentIcon, FolderIcon, LockIcon, RefreshIcon, SearchIcon } from "@/components/ui/icons";
import { ApiError, createCatastoBatch, createCatastoSingleVisura, getCatastoComuni, startCatastoBatch } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatastoBatchDetail, CatastoComune, CatastoSingleVisuraPayload } from "@/types/api";

type ValidationRowError = {
  row_index: number;
  errors: string[];
};

type WorkspaceMode = "single" | "batch";

type RequestWorkspaceProps = {
  initialMode?: WorkspaceMode;
};

const DEFAULT_VALUES: CatastoSingleVisuraPayload = {
  comune: "",
  catasto: "Terreni e Fabbricati",
  sezione: "",
  foglio: "",
  particella: "",
  subalterno: "",
  tipo_visura: "Sintetica",
};

const TEMPLATE_CSV = [
  "citta,catasto,sezione,foglio,particella,subalterno,tipo_visura",
  "MARRUBIU,Terreni,,12,603,,Sintetica",
  "ORISTANO,Terreni e Fabbricati,,5,120,3,Completa",
].join("\n");

export function CatastoRequestWorkspace({ initialMode = "single" }: RequestWorkspaceProps) {
  const router = useRouter();
  const [mode, setMode] = useState<WorkspaceMode>(initialMode);

  useEffect(() => {
    setMode(initialMode);
  }, [initialMode]);

  const [comuni, setComuni] = useState<CatastoComune[]>([]);
  const [singleError, setSingleError] = useState<string | null>(null);
  const [singleBusy, setSingleBusy] = useState(false);

  const [batchName, setBatchName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [draftBatch, setDraftBatch] = useState<CatastoBatchDetail | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationRowError[]>([]);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [batchBusy, setBatchBusy] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CatastoSingleVisuraPayload>({
    defaultValues: DEFAULT_VALUES,
  });

  useEffect(() => {
    async function loadComuni(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        const result = await getCatastoComuni(token);
        setComuni(result);
        setSingleError(null);
        if (result[0]) {
          reset({ ...DEFAULT_VALUES, comune: result[0].nome });
        }
      } catch (loadError) {
        setSingleError(loadError instanceof Error ? loadError.message : "Errore caricamento comuni");
      }
    }

    void loadComuni();
  }, [reset]);

  async function onSubmitSingle(values: CatastoSingleVisuraPayload): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setSingleBusy(true);
    try {
      const batch = await createCatastoSingleVisura(token, {
        ...values,
        sezione: values.sezione?.trim() || undefined,
        subalterno: values.subalterno?.trim() || undefined,
      });
      setSingleError(null);
      router.push(`/catasto/batches/${batch.id}`);
    } catch (submitError) {
      setSingleError(submitError instanceof Error ? submitError.message : "Errore avvio visura singola");
      setSingleBusy(false);
    }
  }

  async function handleUploadBatch(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !file) return;

    setBatchBusy(true);
    try {
      const createdBatch = await createCatastoBatch(token, file, batchName);
      setDraftBatch(createdBatch);
      setValidationErrors([]);
      setBatchError(null);
    } catch (uploadError) {
      if (
        uploadError instanceof ApiError &&
        uploadError.detailData &&
        typeof uploadError.detailData === "object" &&
        "errors" in uploadError.detailData
      ) {
        const detail = uploadError.detailData as { errors?: ValidationRowError[] };
        setValidationErrors(detail.errors ?? []);
      } else {
        setValidationErrors([]);
      }
      setDraftBatch(null);
      setBatchError(uploadError instanceof Error ? uploadError.message : "Errore upload batch");
    } finally {
      setBatchBusy(false);
    }
  }

  async function handleStartBatch(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !draftBatch) return;

    setBatchBusy(true);
    try {
      await startCatastoBatch(token, draftBatch.id);
      router.push(`/catasto/batches/${draftBatch.id}`);
    } catch (startError) {
      setBatchError(startError instanceof Error ? startError.message : "Errore avvio batch");
      setBatchBusy(false);
    }
  }

  function handleDownloadTemplate(): void {
    const blob = new Blob([TEMPLATE_CSV], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = window.document.createElement("a");
    anchor.href = url;
    anchor.download = "catasto-template.csv";
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <ProtectedPage
      title="Nuova richiesta Catasto"
      description="Un unico punto di ingresso per visura puntuale e import massivo."
      breadcrumb="Catasto / Nuova richiesta"
    >
      <CatastoHero
        badge={
          <>
            <FolderIcon className="h-3.5 w-3.5" />
            Nuova richiesta
          </>
        }
        title="Un solo ingresso per il modulo Catasto: scegli se lavorare una singola particella o un lotto completo."
        description="La pagina separa chiaramente i due casi d'uso ma li tiene nello stesso percorso. Prima scegli il tipo di lavoro, poi compili solo i campi rilevanti."
        actions={
          mode === "single" ? (
            singleError ? (
              <CatastoNoticeCard title="Errore visura singola" description={singleError} tone="danger" />
            ) : (
              <CatastoNoticeCard
                title="Flusso rapido"
                description="Usa la modalità singola quando hai già comune, foglio e particella e vuoi partire subito."
              />
            )
          ) : batchError ? (
            <CatastoNoticeCard title="Errore batch" description={batchError} tone="danger" />
          ) : draftBatch ? (
            <CatastoNoticeCard
              title="Bozza batch pronta"
              description={`Sono state importate ${draftBatch.total_items} righe. Rivedi l'anteprima e poi avvia.`}
              tone="success"
            />
          ) : (
            <CatastoNoticeCard
              title="Import guidato"
              description="Usa la modalità batch quando lavori da CSV o XLSX e vuoi validare l'intero lotto prima dell'avvio."
            />
          )
        }
      >
        <div className="grid gap-3 sm:grid-cols-4">
          <CatastoMiniStat eyebrow="Modalità attiva" value={mode === "single" ? "Singola" : "Batch"} description="Puoi cambiare modalità in qualsiasi momento senza uscire dalla pagina." tone="success" />
          <CatastoMiniStat eyebrow="Comuni" value={comuni.length} description="Archivio comuni disponibile per richieste puntuali." />
          <CatastoMiniStat eyebrow="File batch" value={file ? file.name : "Nessun file"} description="CSV e XLSX supportati per l'import massivo." />
          <CatastoMiniStat eyebrow="Validazione" value={validationErrors.length} description="Righe batch con errori bloccanti rilevate." tone={validationErrors.length > 0 ? "warning" : "default"} />
        </div>
      </CatastoHero>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <CatastoPanelHeader
          badge={
            <>
              <RefreshIcon className="h-3.5 w-3.5" />
              Scelta del flusso
            </>
          }
          title="Scegli come vuoi lavorare"
          description="La modalità singola è pensata per una richiesta veloce. La modalità batch è pensata per import, controllo e avvio massivo."
        />
        <div className="grid gap-4 p-6 md:grid-cols-2">
          <button
            className={`rounded-[24px] border p-5 text-left transition ${mode === "single" ? "border-[#1D4E35] bg-[#eef6f0] shadow-sm" : "border-gray-200 bg-white hover:border-gray-300"}`}
            onClick={() => setMode("single")}
            type="button"
          >
            <div className="flex items-center gap-3">
              <div className={`rounded-2xl p-3 ${mode === "single" ? "bg-[#1D4E35] text-white" : "bg-gray-100 text-gray-700"}`}>
                <SearchIcon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-base font-semibold text-gray-900">Visura singola</p>
                <p className="mt-1 text-sm leading-6 text-gray-600">Un immobile o una particella, avvio immediato.</p>
              </div>
            </div>
          </button>
          <button
            className={`rounded-[24px] border p-5 text-left transition ${mode === "batch" ? "border-[#1D4E35] bg-[#eef6f0] shadow-sm" : "border-gray-200 bg-white hover:border-gray-300"}`}
            onClick={() => setMode("batch")}
            type="button"
          >
            <div className="flex items-center gap-3">
              <div className={`rounded-2xl p-3 ${mode === "batch" ? "bg-[#1D4E35] text-white" : "bg-gray-100 text-gray-700"}`}>
                <DocumentIcon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-base font-semibold text-gray-900">Import batch</p>
                <p className="mt-1 text-sm leading-6 text-gray-600">Più righe da file, validazione e preview prima del run.</p>
              </div>
            </div>
          </button>
        </div>
      </article>

      {mode === "single" ? (
        <form
          className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel"
          onSubmit={(event) => void handleSubmit(onSubmitSingle)(event)}
        >
          <CatastoPanelHeader
            badge={
              <>
                <LockIcon className="h-3.5 w-3.5" />
                Dati richiesta
              </>
            }
            title="Parametri catastali della visura singola"
            description="Compila i campi strettamente necessari. Sezione e subalterno restano opzionali."
          />
          <div className="p-6">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <label className="space-y-2 xl:col-span-2">
                <span className="label-caption">Comune</span>
                <select className="form-control" {...register("comune", { required: "Seleziona un comune" })}>
                  <option value="">Seleziona comune</option>
                  {comuni.map((comune) => (
                    <option key={comune.id} value={comune.nome}>
                      {comune.nome}
                    </option>
                  ))}
                </select>
                {errors.comune ? <p className="text-xs text-red-600">{errors.comune.message}</p> : null}
              </label>

              <label className="space-y-2">
                <span className="label-caption">Catasto</span>
                <select className="form-control" {...register("catasto", { required: true })}>
                  <option value="Terreni">Terreni</option>
                  <option value="Terreni e Fabbricati">Terreni e Fabbricati</option>
                </select>
              </label>

              <label className="space-y-2">
                <span className="label-caption">Foglio</span>
                <input
                  className="form-control"
                  inputMode="numeric"
                  placeholder="Es. 5"
                  {...register("foglio", {
                    required: "Foglio obbligatorio",
                    pattern: { value: /^\d+$/, message: "Inserisci un valore numerico" },
                  })}
                />
                {errors.foglio ? <p className="text-xs text-red-600">{errors.foglio.message}</p> : null}
              </label>

              <label className="space-y-2">
                <span className="label-caption">Particella</span>
                <input
                  className="form-control"
                  inputMode="numeric"
                  placeholder="Es. 120"
                  {...register("particella", {
                    required: "Particella obbligatoria",
                    pattern: { value: /^\d+$/, message: "Inserisci un valore numerico" },
                  })}
                />
                {errors.particella ? <p className="text-xs text-red-600">{errors.particella.message}</p> : null}
              </label>

              <label className="space-y-2">
                <span className="label-caption">Subalterno</span>
                <input
                  className="form-control"
                  inputMode="numeric"
                  placeholder="Opzionale"
                  {...register("subalterno", {
                    pattern: { value: /^\d*$/, message: "Solo valori numerici" },
                  })}
                />
                {errors.subalterno ? <p className="text-xs text-red-600">{errors.subalterno.message}</p> : null}
              </label>

              <label className="space-y-2">
                <span className="label-caption">Sezione</span>
                <input className="form-control" placeholder="Opzionale" {...register("sezione")} />
              </label>

              <label className="space-y-2">
                <span className="label-caption">Tipo visura</span>
                <select className="form-control" {...register("tipo_visura", { required: true })}>
                  <option value="Sintetica">Sintetica</option>
                  <option value="Completa">Completa</option>
                </select>
              </label>
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button className="btn-primary" disabled={singleBusy || comuni.length === 0} type="submit">
                {singleBusy ? "Avvio in corso..." : "Avvia visura singola"}
              </button>
              <p className="text-xs text-gray-400">
                La richiesta crea un batch da una sola riga e parte subito se le credenziali SISTER sono presenti.
              </p>
            </div>
          </div>
        </form>
      ) : (
        <>
          <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
            <CatastoPanelHeader
              badge={
                <>
                  <DocumentIcon className="h-3.5 w-3.5" />
                  Sorgente dati
                </>
              }
              title="Caricamento file e validazione preliminare"
              description="Il batch viene validato subito, ma non parte finché non premi Avvia batch."
            />
            <div className="p-6">
              <div className="grid gap-4 md:grid-cols-[1.2fr,1fr]">
                <label className="space-y-2">
                  <span className="label-caption">Nome batch</span>
                  <input
                    className="form-control"
                    onChange={(event) => setBatchName(event.target.value)}
                    placeholder="Lotto marzo 2026"
                    value={batchName}
                  />
                </label>
                <label className="space-y-2">
                  <span className="label-caption">File CSV / XLSX</span>
                  <input
                    accept=".csv,.xlsx"
                    className="form-control py-2"
                    onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                    type="file"
                  />
                </label>
              </div>
              <div className="mt-5 flex flex-wrap items-center gap-3">
                <button className="btn-primary" disabled={batchBusy || !file} onClick={() => void handleUploadBatch()} type="button">
                  {batchBusy ? "Validazione..." : "Carica e valida"}
                </button>
                <button className="btn-secondary" onClick={handleDownloadTemplate} type="button">
                  Scarica template CSV
                </button>
                <span className="text-xs text-gray-400">Il batch resta `pending` finché non confermi l’avvio.</span>
              </div>
            </div>
          </article>

          {validationErrors.length > 0 ? (
            <article className="overflow-hidden rounded-[28px] border border-red-100 bg-white shadow-panel">
              <CatastoPanelHeader
                badge={
                  <>
                    <RefreshIcon className="h-3.5 w-3.5" />
                    Validazione
                  </>
                }
                title="Righe da correggere prima dell'avvio"
                description="Ogni errore è bloccante. Correggi il file e ripeti l'upload."
              />
              <div className="space-y-3 p-6">
                {validationErrors.map((item) => (
                  <div key={item.row_index} className="rounded-lg border border-red-100 bg-red-50 px-4 py-3">
                    <p className="text-sm font-medium text-red-800">Riga {item.row_index}</p>
                    <p className="mt-1 text-sm text-red-700">{item.errors.join(" ")}</p>
                  </div>
                ))}
              </div>
            </article>
          ) : null}

          {draftBatch ? (
            <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
              <CatastoPanelHeader
                badge={
                  <>
                    <FolderIcon className="h-3.5 w-3.5" />
                    Preview batch
                  </>
                }
                title={draftBatch.name ?? draftBatch.id}
                description={`${draftBatch.total_items} righe importate${draftBatch.skipped_items > 0 ? ` · ${draftBatch.skipped_items} record saltati` : ""}`}
                actions={
                  <button className="btn-primary" disabled={batchBusy} onClick={() => void handleStartBatch()} type="button">
                    Avvia batch
                  </button>
                }
              />
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Riga</th>
                      <th>Comune</th>
                      <th>Riferimento</th>
                      <th>Tipo</th>
                      <th>Stato</th>
                      <th>Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {draftBatch.requests.map((request) => (
                      <tr key={request.id}>
                        <td>{request.row_index}</td>
                        <td>{request.comune}</td>
                        <td>
                          Fg.{request.foglio} Part.{request.particella}
                          {request.subalterno ? ` Sub.${request.subalterno}` : ""}
                        </td>
                        <td>{request.tipo_visura}</td>
                        <td><CatastoStatusBadge status={request.status} /></td>
                        <td>{request.error_message ?? request.current_operation ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          ) : null}
        </>
      )}
    </ProtectedPage>
  );
}
