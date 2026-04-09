"use client";

import { useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon } from "@/components/ui/icons";
import { RiordinoConfirmDialog } from "@/components/riordino/shared/confirm-dialog";
import { formatRiordinoDate, formatRiordinoFileSize, formatRiordinoLabel } from "@/components/riordino/shared/format";
import { deleteRiordinoDocument, downloadRiordinoDocument, uploadRiordinoDocument } from "@/lib/riordino-api";
import { ApiError } from "@/lib/api";
import type { RiordinoDocument, RiordinoPhase } from "@/types/riordino";

type RiordinoDocumentPanelProps = {
  token: string;
  practiceId: string;
  phases: RiordinoPhase[];
  documents: RiordinoDocument[];
  onUpdated: () => Promise<void>;
};

const DOCUMENT_TYPES = [
  "decreto",
  "ricorso",
  "verbale_commissione",
  "estratto_mappa",
  "file_pregeo",
  "documento_docte",
  "documento_finale",
  "altro",
];

export function RiordinoDocumentPanel({ token, practiceId, phases, documents, onUpdated }: RiordinoDocumentPanelProps) {
  const [documentType, setDocumentType] = useState("decreto");
  const [phaseId, setPhaseId] = useState("");
  const [stepId, setStepId] = useState("");
  const [notes, setNotes] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<RiordinoDocument | null>(null);

  const selectedPhase = useMemo(() => phases.find((phase) => phase.id === phaseId) ?? null, [phaseId, phases]);
  const steps = selectedPhase?.steps ?? [];

  async function handleUpload() {
    if (!file) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await uploadRiordinoDocument(token, practiceId, {
        file,
        document_type: documentType,
        phase_id: phaseId || null,
        step_id: stepId || null,
        notes: notes || null,
      });
      setFile(null);
      setNotes("");
      setStepId("");
      await onUpdated();
    } catch (currentError) {
      setError(resolveActionError(currentError, "Impossibile caricare il documento"));
    } finally {
      setBusy(false);
    }
  }

  async function handleDownload(documentId: string, originalFilename: string) {
    setBusy(true);
    setError(null);
    try {
      const blob = await downloadRiordinoDocument(token, documentId);
      const blobUrl = URL.createObjectURL(blob);
      const link = window.document.createElement("a");
      link.href = blobUrl;
      link.download = originalFilename;
      link.click();
      URL.revokeObjectURL(blobUrl);
    } catch (currentError) {
      setError(resolveActionError(currentError, "Impossibile scaricare il documento"));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(documentId: string) {
    setBusy(true);
    setError(null);
    try {
      await deleteRiordinoDocument(token, documentId);
      await onUpdated();
      setConfirmDelete(null);
    } catch (currentError) {
      setError(resolveActionError(currentError, "Impossibile eliminare il documento"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
      <article className="panel-card">
        <p className="section-title">Documenti</p>
        <div className="mt-4 space-y-3">
          {documents.length === 0 ? (
            <EmptyState icon={DocumentIcon} title="Nessun documento" description="I documenti caricati per la pratica compariranno qui." />
          ) : (
            documents.map((document) => (
              <div key={document.id} className="rounded-2xl border border-gray-100 px-4 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-gray-900">{document.original_filename}</p>
                  {document.deleted_at ? <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-700">eliminato</span> : null}
                </div>
                <p className="mt-1 text-sm text-gray-600">
                  {formatRiordinoLabel(document.document_type)} • {formatRiordinoFileSize(document.file_size_bytes)} • {formatRiordinoDate(document.uploaded_at, true)}
                </p>
                {document.notes ? <p className="mt-2 text-sm text-gray-600">{document.notes}</p> : null}
                {!document.deleted_at ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button className="btn-secondary" disabled={busy} onClick={() => void handleDownload(document.id, document.original_filename)} type="button">
                      Scarica
                    </button>
                    <button className="btn-secondary" disabled={busy} onClick={() => setConfirmDelete(document)} type="button">
                      Soft delete
                    </button>
                  </div>
                ) : null}
              </div>
            ))
          )}
        </div>
      </article>

      <article className="panel-card">
        <p className="section-title">Carica documento</p>
        <div className="mt-4 grid gap-3">
          <select className="form-control" value={documentType} onChange={(event) => setDocumentType(event.target.value)}>
            {DOCUMENT_TYPES.map((item) => (
              <option key={item} value={item}>{formatRiordinoLabel(item)}</option>
            ))}
          </select>
          <select
            className="form-control"
            value={phaseId}
            onChange={(event) => {
              setPhaseId(event.target.value);
              setStepId("");
            }}
          >
            <option value="">Fase opzionale</option>
            {phases.map((phase) => (
              <option key={phase.id} value={phase.id}>{phase.phase_code}</option>
            ))}
          </select>
          <select className="form-control" value={stepId} onChange={(event) => setStepId(event.target.value)} disabled={!phaseId}>
            <option value="">Step opzionale</option>
            {steps.map((step) => (
              <option key={step.id} value={step.id}>{step.code} · {step.title}</option>
            ))}
          </select>
          <input className="form-control" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          <textarea className="form-control min-h-24" placeholder="Note documento" value={notes} onChange={(event) => setNotes(event.target.value)} />
          <button className="btn-primary" disabled={busy || file === null} onClick={() => void handleUpload()} type="button">
            Carica documento
          </button>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </div>
      </article>

      <RiordinoConfirmDialog
        open={confirmDelete !== null}
        title="Confermare soft delete documento?"
        description={confirmDelete ? `Il documento ${confirmDelete.original_filename} verrà marcato come eliminato ma resterà tracciato nello storico.` : ""}
        confirmLabel="Conferma delete"
        cancelLabel="Annulla"
        tone="danger"
        busy={busy}
        onCancel={() => setConfirmDelete(null)}
        onConfirm={() => confirmDelete ? handleDelete(confirmDelete.id) : undefined}
      />
    </div>
  );
}
  function resolveActionError(currentError: unknown, fallback: string): string {
    if (currentError instanceof ApiError && currentError.status === 409) {
      return "Dati modificati da un altro utente. Ricarica la pratica e riprova.";
    }
    return currentError instanceof Error ? currentError.message : fallback;
  }
