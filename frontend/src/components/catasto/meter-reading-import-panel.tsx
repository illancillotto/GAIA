"use client";

import { useState } from "react";

import { AlertBanner } from "@/components/ui/alert-banner";
import { catastoImportMeterReadings, catastoValidateMeterReadingsImport } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import { CatastoFilePicker } from "./file-picker";
import { MeterReadingImportReport, type MeterReadingImportReportItem } from "./meter-reading-import-report";

export function MeterReadingImportPanel() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [ignoredTempFiles, setIgnoredTempFiles] = useState<string[]>([]);
  const [anno, setAnno] = useState("");
  const [mode, setMode] = useState<"upsert" | "import" | "replace">("upsert");
  const [previews, setPreviews] = useState<MeterReadingImportReportItem[]>([]);
  const [busy, setBusy] = useState<"validate" | "import" | null>(null);
  const [messages, setMessages] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [progressMessage, setProgressMessage] = useState<string | null>(null);

  function handleSelectedFiles(files: File[]) {
    const ignored = files.filter((file) => file.name.startsWith("~$")).map((file) => file.name);
    const accepted = files.filter((file) => !file.name.startsWith("~$"));
    setIgnoredTempFiles(ignored);
    setSelectedFiles(accepted);
    if (accepted.length === 0 && ignored.length > 0) {
      setError("I file temporanei di Excel (~$...) non sono importabili. Seleziona i file .xlsx reali.");
      return;
    }
    setError(null);
  }

  async function validateSingleFile(token: string, file: File): Promise<MeterReadingImportReportItem> {
    const preview = await catastoValidateMeterReadingsImport(token, file, {
      anno: anno ? Number(anno) : undefined,
    });
    return { filename: file.name, preview };
  }

  async function handleValidateAll() {
    const token = getStoredAccessToken();
    if (!token || selectedFiles.length === 0) return;
    try {
      setBusy("validate");
      setError(null);
      setMessages([]);
      setProgressMessage("Validazione file in corso...");
      const results: MeterReadingImportReportItem[] = [];
      for (const file of selectedFiles) {
        setProgressMessage(`Validazione ${file.name}...`);
        results.push(await validateSingleFile(token, file));
      }
      setPreviews(results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Validazione fallita");
    } finally {
      setProgressMessage(null);
      setBusy(null);
    }
  }

  async function handleImportAll() {
    const token = getStoredAccessToken();
    if (!token || selectedFiles.length === 0) return;
    try {
      setBusy("import");
      setError(null);
      setMessages([]);
      setProgressMessage("Import file in corso...");
      const importMessages: string[] = [];
      const nextPreviews: MeterReadingImportReportItem[] = [];
      for (const file of selectedFiles) {
        setProgressMessage(`Import ${file.name}...`);
        const result = await catastoImportMeterReadings(token, file, {
          anno: anno ? Number(anno) : undefined,
          mode,
        });
        importMessages.push(
          `${file.name}: ${result.righe_importate} righe salvate, ${result.righe_con_warning} con warning, ${result.righe_scartate} scartate.`,
        );
        nextPreviews.push(await validateSingleFile(token, file));
      }
      setMessages(importMessages);
      setPreviews(nextPreviews);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import fallito");
    } finally {
      setProgressMessage(null);
      setBusy(null);
    }
  }

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4">
          <p className="section-title">Import Excel letture</p>
          <p className="section-copy">Carica uno o piu file Excel distrettuali: il sistema deduce automaticamente il distretto dal nome file e importa ogni file in sequenza.</p>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <CatastoFilePicker
            id="catasto-meter-readings-file"
            label="File Excel"
            accept=".xlsx"
            files={selectedFiles}
            multiple
            disabled={busy !== null}
            onChange={() => undefined}
            onChangeFiles={handleSelectedFiles}
            hint="Usa file `.xlsx` nel formato tipo `D01-Sinis 2025.xlsx`. I file temporanei Excel `~$...` vengono ignorati automaticamente."
          />
          <label className="block text-sm font-medium text-slate-700">
            Anno override
            <input className="form-control mt-1" value={anno} onChange={(event) => setAnno(event.target.value)} />
            <span className="mt-1 block text-xs font-normal text-slate-400">Lascia il valore corretto per forzarlo su tutti i file, oppure svuota il campo per dedurlo dal nome file.</span>
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Modalità import
            <select className="form-control mt-1" value={mode} onChange={(event) => setMode(event.target.value as "upsert" | "import" | "replace")}>
              <option value="upsert">Upsert</option>
              <option value="import">Solo se assente</option>
              <option value="replace">Replace</option>
            </select>
          </label>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <button className="btn-secondary" onClick={() => void handleValidateAll()} disabled={selectedFiles.length === 0 || busy !== null} type="button">
            {busy === "validate" ? "Validazione..." : "Valida file"}
          </button>
          <button className="btn-primary" onClick={() => void handleImportAll()} disabled={selectedFiles.length === 0 || busy !== null} type="button">
            {busy === "import" ? "Import in corso..." : "Importa letture"}
          </button>
          {progressMessage ? <span className="text-sm text-slate-500">{progressMessage}</span> : null}
        </div>
      </div>

      {error ? (
        <AlertBanner variant="danger" title="Errore">
          {error}
        </AlertBanner>
      ) : null}

      {ignoredTempFiles.length > 0 ? (
        <AlertBanner variant="warning" title="File ignorati">
          <div className="space-y-1">
            <p>I file temporanei di Excel non vengono importati.</p>
            {ignoredTempFiles.map((file) => (
              <p key={file}>{file}</p>
            ))}
          </div>
        </AlertBanner>
      ) : null}

      {messages.length > 0 ? (
        <AlertBanner variant="info" title="Esito import">
          <div className="space-y-1">
            {messages.map((message) => (
              <p key={message}>{message}</p>
            ))}
          </div>
        </AlertBanner>
      ) : null}

      <MeterReadingImportReport previews={previews} />
    </div>
  );
}
