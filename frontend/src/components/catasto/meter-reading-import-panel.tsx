"use client";

import { useEffect, useState } from "react";

import { AlertBanner } from "@/components/ui/alert-banner";
import { catastoImportMeterReadings, catastoListDistretti, catastoValidateMeterReadingsImport } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatDistretto, CatMeterReadingImportPreview } from "@/types/catasto";

import { MeterReadingImportReport } from "./meter-reading-import-report";

export function MeterReadingImportPanel() {
  const [distretti, setDistretti] = useState<CatDistretto[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedDistrettoId, setSelectedDistrettoId] = useState("");
  const [anno, setAnno] = useState(String(new Date().getFullYear()));
  const [mode, setMode] = useState<"upsert" | "import" | "replace">("upsert");
  const [preview, setPreview] = useState<CatMeterReadingImportPreview | null>(null);
  const [busy, setBusy] = useState<"validate" | "import" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const token = getStoredAccessToken();
      if (!token) return;
      try {
        setDistretti(await catastoListDistretti(token));
      } catch {
        setDistretti([]);
      }
    }
    void load();
  }, []);

  async function handleValidate() {
    const token = getStoredAccessToken();
    if (!token || !selectedFile) return;
    try {
      setBusy("validate");
      setError(null);
      setMessage(null);
      const result = await catastoValidateMeterReadingsImport(token, selectedFile, {
        anno: anno ? Number(anno) : undefined,
        distrettoId: selectedDistrettoId || undefined,
      });
      setPreview(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Validazione fallita");
    } finally {
      setBusy(null);
    }
  }

  async function handleImport() {
    const token = getStoredAccessToken();
    if (!token || !selectedFile) return;
    try {
      setBusy("import");
      setError(null);
      const result = await catastoImportMeterReadings(token, selectedFile, {
        anno: anno ? Number(anno) : undefined,
        distrettoId: selectedDistrettoId || undefined,
        mode,
      });
      setMessage(`Import completato: ${result.righe_importate} righe salvate, ${result.righe_con_warning} con warning, ${result.righe_scartate} scartate.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import fallito");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4">
          <p className="section-title">Import Excel letture</p>
          <p className="section-copy">Carica il file distrettuale, valida il tracciato e poi salva le letture in Catasto.</p>
        </div>

        <div className="grid gap-4 lg:grid-cols-4">
          <label className="block text-sm font-medium text-slate-700">
            File Excel
            <input className="form-control mt-1" type="file" accept=".xlsx,.xls" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Distretto
            <select className="form-control mt-1" value={selectedDistrettoId} onChange={(event) => setSelectedDistrettoId(event.target.value)}>
              <option value="">Deduzione da file</option>
              {distretti.map((item) => (
                <option key={item.id} value={item.id}>
                  D{item.num_distretto} {item.nome_distretto ?? ""}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Anno
            <input className="form-control mt-1" value={anno} onChange={(event) => setAnno(event.target.value)} />
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
          <button className="btn-secondary" onClick={() => void handleValidate()} disabled={!selectedFile || busy !== null} type="button">
            {busy === "validate" ? "Validazione..." : "Valida file"}
          </button>
          <button className="btn-primary" onClick={() => void handleImport()} disabled={!selectedFile || busy !== null} type="button">
            {busy === "import" ? "Import in corso..." : "Importa letture"}
          </button>
        </div>
      </div>

      {error ? (
        <AlertBanner variant="danger" title="Errore">
          {error}
        </AlertBanner>
      ) : null}

      {message ? (
        <AlertBanner variant="info" title="Esito import">
          {message}
        </AlertBanner>
      ) : null}

      <MeterReadingImportReport preview={preview} />
    </div>
  );
}
