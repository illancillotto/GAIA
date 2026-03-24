"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { ProtectedPage } from "@/components/app/protected-page";
import { CatastoStatusBadge } from "@/components/catasto/status-badge";
import { ApiError, createCatastoBatch, startCatastoBatch } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatastoBatchDetail } from "@/types/api";

type ValidationRowError = {
  row_index: number;
  errors: string[];
};

const TEMPLATE_CSV = [
  "citta,catasto,sezione,foglio,particella,subalterno,tipo_visura",
  "MARRUBIU,Terreni,,12,603,,Sintetica",
  "ORISTANO,Terreni e Fabbricati,,5,120,3,Completa",
].join("\n");

export default function CatastoNewBatchPage() {
  const router = useRouter();
  const [batchName, setBatchName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [draftBatch, setDraftBatch] = useState<CatastoBatchDetail | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationRowError[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleUpload(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !file) return;

    setBusy(true);
    try {
      const createdBatch = await createCatastoBatch(token, file, batchName);
      setDraftBatch(createdBatch);
      setValidationErrors([]);
      setError(null);
    } catch (uploadError) {
      if (uploadError instanceof ApiError && uploadError.detailData && typeof uploadError.detailData === "object" && "errors" in uploadError.detailData) {
        const detail = uploadError.detailData as { errors?: ValidationRowError[] };
        setValidationErrors(detail.errors ?? []);
      } else {
        setValidationErrors([]);
      }
      setDraftBatch(null);
      setError(uploadError instanceof Error ? uploadError.message : "Errore upload batch");
    } finally {
      setBusy(false);
    }
  }

  async function handleStart(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !draftBatch) return;

    setBusy(true);
    try {
      await startCatastoBatch(token, draftBatch.id);
      router.push(`/catasto/batches/${draftBatch.id}`);
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Errore avvio batch");
      setBusy(false);
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
      title="Nuovo batch Catasto"
      description="Carica il file sorgente, valida le righe catastali e avvia il worker Playwright."
      breadcrumb="Catasto / Nuovo batch"
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <article className="panel-card">
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
        <div className="mt-5 flex items-center gap-3">
          <button className="btn-primary" disabled={busy || !file} onClick={() => void handleUpload()} type="button">
            {busy ? "Validazione..." : "Carica e valida"}
          </button>
          <button className="btn-secondary" onClick={handleDownloadTemplate} type="button">
            Scarica template CSV
          </button>
          <span className="text-xs text-gray-400">Il batch resta `pending` finché non confermi l’avvio.</span>
        </div>
      </article>

      {validationErrors.length > 0 ? (
        <article className="panel-card border-red-100">
          <p className="section-title text-red-700">Errori di validazione</p>
          <div className="mt-4 space-y-3">
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
        <article className="panel-card overflow-hidden p-0">
          <div className="flex items-center justify-between gap-3 border-b border-gray-100 px-5 py-4">
            <div>
              <p className="section-title">Preview batch</p>
              <p className="section-copy">{draftBatch.name ?? draftBatch.id} · {draftBatch.total_items} richieste validate</p>
            </div>
            <button className="btn-primary" disabled={busy} onClick={() => void handleStart()} type="button">
              Avvia batch
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Riga</th>
                  <th>Comune</th>
                  <th>Riferimento</th>
                  <th>Tipo</th>
                  <th>Stato</th>
                </tr>
              </thead>
              <tbody>
                {draftBatch.requests.map((request) => (
                  <tr key={request.id}>
                    <td>{request.row_index}</td>
                    <td>{request.comune}</td>
                    <td>Fg.{request.foglio} Part.{request.particella}{request.subalterno ? ` Sub.${request.subalterno}` : ""}</td>
                    <td>{request.tipo_visura}</td>
                    <td><CatastoStatusBadge status={request.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ) : null}
    </ProtectedPage>
  );
}
