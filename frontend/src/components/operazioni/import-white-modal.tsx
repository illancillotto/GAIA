"use client";

import { useEffect, useState } from "react";

import { importWhiteReports } from "@/features/operazioni/api/client";

type ImportWhiteModalProps = {
  open: boolean;
  onClose: (didImport: boolean) => void;
};

type ImportResult = {
  imported: number;
  skipped: number;
  errors: string[];
  categories_created: string[];
  total_events_created: number;
};

export function ImportWhiteModal({ open, onClose }: ImportWhiteModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);

  useEffect(() => {
    if (!open) {
      setSelectedFile(null);
      setIsDragging(false);
      setIsImporting(false);
      setError(null);
      setResult(null);
    }
  }, [open]);

  if (!open) {
    return null;
  }

  async function handleImport(): Promise<void> {
    if (!selectedFile) {
      setError("Seleziona un file .xlsx da importare.");
      return;
    }

    setIsImporting(true);
    setError(null);
    try {
      const response = await importWhiteReports(selectedFile);
      setResult(response);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Import non riuscito");
    } finally {
      setIsImporting(false);
    }
  }

  function handleFile(file: File | null): void {
    setSelectedFile(file);
    setResult(null);
    setError(null);
  }

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="border-b border-gray-100 px-6 py-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Import White Company</p>
          <h2 className="mt-2 text-2xl font-semibold text-gray-900">Carica file Excel segnalazioni</h2>
          <p className="mt-1 text-sm text-gray-500">
            L&apos;import è idempotente: i codici già presenti vengono saltati senza sovrascrivere i dati esistenti.
          </p>
        </div>

        <div className="space-y-5 px-6 py-6">
          <label
            className={`block rounded-[24px] border-2 border-dashed px-5 py-8 text-center transition ${
              isDragging ? "border-[#1D4E35] bg-[#edf5f0]" : "border-[#d9dfd6] bg-[#fbfcfa]"
            }`}
            onDragOver={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setIsDragging(false);
              handleFile(event.dataTransfer.files?.[0] ?? null);
            }}
          >
            <input
              type="file"
              accept=".xlsx"
              className="hidden"
              onChange={(event) => handleFile(event.target.files?.[0] ?? null)}
            />
            <p className="text-sm font-semibold text-gray-900">
              {selectedFile ? selectedFile.name : "Trascina qui il file .xlsx oppure selezionalo dal computer"}
            </p>
            <p className="mt-2 text-sm text-gray-500">Formato supportato: Excel `.xlsx` esportato da White Company.</p>
            <span className="btn-secondary mt-4 inline-flex">Scegli file</span>
          </label>

          {error ? <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

          {result ? (
            <div className="rounded-[24px] border border-[#d9dfd6] bg-[#fbfcfa] p-5">
              <p className="text-sm font-semibold text-gray-900">Esito import</p>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl border border-[#e4e8e2] bg-white px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-gray-500">Importate</p>
                  <p className="mt-2 text-2xl font-semibold text-[#183325]">{result.imported}</p>
                </div>
                <div className="rounded-2xl border border-[#e4e8e2] bg-white px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-gray-500">Saltate</p>
                  <p className="mt-2 text-2xl font-semibold text-[#183325]">{result.skipped}</p>
                </div>
                <div className="rounded-2xl border border-[#e4e8e2] bg-white px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-gray-500">Eventi creati</p>
                  <p className="mt-2 text-2xl font-semibold text-[#183325]">{result.total_events_created}</p>
                </div>
              </div>
              {result.categories_created.length > 0 ? (
                <p className="mt-4 text-sm text-gray-600">Categorie create: {result.categories_created.join(", ")}</p>
              ) : null}
              {result.errors.length > 0 ? (
                <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  Errori: {result.errors.join(" · ")}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-gray-100 px-6 py-5">
          <button className="btn-secondary" type="button" onClick={() => onClose(Boolean(result))} disabled={isImporting}>
            Chiudi
          </button>
          <button className="btn-primary" type="button" onClick={() => void handleImport()} disabled={isImporting}>
            {isImporting ? "Import in corso..." : "Importa"}
          </button>
        </div>
      </div>
    </div>
  );
}
