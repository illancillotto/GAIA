"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getVehicles,
  importFleetTransactions,
  resolveFleetTransactions,
  type UnresolvedRow,
} from "@/features/operazioni/api/client";

type ImportFleetTransactionsModalProps = {
  open: boolean;
  onClose: (didImport: boolean) => void;
};

type ImportResult = {
  imported: number;
  skipped: number;
  errors: string[];
  rows_read: number;
  matched_white_refuels?: number;
  unresolved: UnresolvedRow[];
};

type VehicleOption = { id: string; label: string };

// Group unresolved rows by operator_name (or card_code for no_card_operator)
function groupKey(row: UnresolvedRow): string {
  if (row.operator_name) return `op:${row.operator_name}`;
  return `card:${row.card_code ?? row.targa ?? "?"}`;
}

function groupLabel(row: UnresolvedRow): string {
  if (row.operator_name) return row.operator_name;
  return row.card_code ? `Tessera ${row.card_code}` : row.targa ?? "?";
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

// ─── Step 1: file upload ───────────────────────────────────────────────────

function UploadStep({
  onResult,
}: {
  onResult: (result: ImportResult) => void;
}) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleImport(): Promise<void> {
    if (!selectedFile) { setError("Seleziona un file .xlsx da importare."); return; }
    setIsImporting(true);
    setError(null);
    try {
      const response = await importFleetTransactions(selectedFile);
      onResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import non riuscito");
    } finally {
      setIsImporting(false);
    }
  }

  function handleFile(file: File | null): void {
    setSelectedFile(file);
    setError(null);
  }

  return (
    <div className="space-y-5 px-6 py-6">
      <label
        className={`block rounded-[24px] border-2 border-dashed px-5 py-8 text-center transition ${
          isDragging ? "border-[#1D4E35] bg-[#edf5f0]" : "border-[#d9dfd6] bg-[#fbfcfa]"
        }`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFile(e.dataTransfer.files?.[0] ?? null); }}
      >
        <input type="file" accept=".xlsx" className="hidden" onChange={(e) => handleFile(e.target.files?.[0] ?? null)} />
        <p className="text-sm font-semibold text-gray-900">
          {selectedFile ? selectedFile.name : "Trascina qui il file .xlsx oppure selezionalo dal computer"}
        </p>
        <p className="mt-2 text-sm text-gray-500">
          Formato supportato: Excel `.xlsx` transazioni flotte con campi `Targa`, `Identificativo`, `Data`, `Ora`, `Km`, `Volume`.
        </p>
        <span className="btn-secondary mt-4 inline-flex">Scegli file</span>
      </label>

      <div className="rounded-[24px] border border-[#d9dfd6] bg-[#fbfcfa] px-4 py-4 text-sm text-gray-600">
        Matching mezzi: `Targa`, `Identificativo`, `Veicolo` contro `plate_number`, `wc_vehicle_id`, `asset_tag`, `code`.
      </div>

      {error && <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

      <div className="flex justify-end gap-3 border-t border-gray-100 pt-5">
        <button className="btn-primary" type="button" onClick={() => void handleImport()} disabled={isImporting}>
          {isImporting ? "Import in corso..." : "Importa"}
        </button>
      </div>
    </div>
  );
}

// ─── Step 2: result summary (possibly with wizard CTA) ───────────────────

function ResultStep({
  result,
  onWizard,
  onClose,
}: {
  result: ImportResult;
  onWizard: () => void;
  onClose: () => void;
}) {
  return (
    <div className="space-y-5 px-6 py-6">
      <div className="rounded-[24px] border border-[#d9dfd6] bg-[#fbfcfa] p-5">
        <p className="text-sm font-semibold text-gray-900">Esito import</p>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          {[
            { label: "Importate", value: result.imported },
            { label: "Saltate / dup.", value: result.skipped },
            { label: "Righe lette", value: result.rows_read },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-2xl border border-[#e4e8e2] bg-white px-4 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-gray-500">{label}</p>
              <p className="mt-2 text-2xl font-semibold text-[#183325]">{value}</p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm text-gray-600">
          Match con eventi WhiteCompany: <span className="font-semibold text-gray-900">{result.matched_white_refuels ?? 0}</span>
        </p>
        {result.errors.length > 0 && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {result.errors.join(" · ")}
          </div>
        )}
      </div>

      {result.unresolved.length > 0 && (
        <div className="rounded-[24px] border border-amber-200 bg-amber-50 p-5">
          <p className="text-sm font-semibold text-amber-900">
            {result.unresolved.length} transazioni non risolte
          </p>
          <p className="mt-1 text-sm text-amber-800">
            Mezzo o operatore non trovato automaticamente. Puoi assegnare manualmente il veicolo per ciascuna riga.
          </p>
          <button
            className="mt-4 rounded-full bg-amber-700 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-amber-800"
            onClick={onWizard}
          >
            Risolvi {result.unresolved.length} casi →
          </button>
        </div>
      )}

      <div className="flex justify-end border-t border-gray-100 pt-5">
        <button className="btn-secondary" type="button" onClick={onClose}>
          Chiudi
        </button>
      </div>
    </div>
  );
}

// ─── Step 3: wizard ───────────────────────────────────────────────────────

function WizardStep({
  unresolved,
  onDone,
  onBack,
}: {
  unresolved: UnresolvedRow[];
  onDone: (imported: number) => void;
  onBack: () => void;
}) {
  const [vehicles, setVehicles] = useState<VehicleOption[]>([]);
  const [vehicleSearch, setVehicleSearch] = useState<Record<string, string>>({});
  // vehicle_id per row_index (string "skip" = explicit skip)
  const [selections, setSelections] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getVehicles({ page_size: "500" })
      .then((data) => {
        const items = (data.items ?? []) as Array<{ id: string; plate_number: string | null; code: string | null; description: string | null }>;
        setVehicles(items.map((v) => ({
          id: v.id,
          label: [v.plate_number, v.code, v.description].filter(Boolean).join(" · ") || v.id,
        })));
      })
      .catch(() => {/* ignore */});
  }, []);

  // Group rows by operator/card for batch assignment
  const groups = useMemo(() => {
    const map = new Map<string, { label: string; rows: UnresolvedRow[] }>();
    for (const row of unresolved) {
      const key = groupKey(row);
      if (!map.has(key)) map.set(key, { label: groupLabel(row), rows: [] });
      map.get(key)!.rows.push(row);
    }
    return Array.from(map.entries()).map(([key, val]) => ({ key, ...val }));
  }, [unresolved]);

  function setGroupVehicle(groupKey_: string, vehicleId: string) {
    const group = groups.find((g) => g.key === groupKey_);
    if (!group) return;
    setSelections((prev) => {
      const next = { ...prev };
      for (const row of group.rows) next[row.row_index] = vehicleId;
      return next;
    });
  }

  function filteredVehicles(search: string): VehicleOption[] {
    if (!search.trim()) return vehicles.slice(0, 50);
    const q = search.toLowerCase();
    return vehicles.filter((v) => v.label.toLowerCase().includes(q)).slice(0, 50);
  }

  async function handleSubmit() {
    const resolutions = unresolved
      .filter((row) => {
        const sel = selections[row.row_index];
        return sel && sel !== "skip";
      })
      .map((row) => ({
        vehicle_id: selections[row.row_index],
        fueled_at_iso: row.fueled_at_iso ?? "",
        liters: row.liters ?? "0",
        total_cost: row.total_cost,
        odometer_km: row.odometer_km,
        card_code: row.card_code,
        station_name: row.station_name,
        notes_extra: row.notes_extra,
        unresolved_id: row.db_id ?? null,
      }));

    if (resolutions.length === 0) { onDone(0); return; }

    setSubmitting(true);
    setError(null);
    try {
      const result = await resolveFleetTransactions(resolutions);
      onDone(result.imported);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore durante la risoluzione");
    } finally {
      setSubmitting(false);
    }
  }

  const resolvedCount = Object.values(selections).filter((v) => v && v !== "skip").length;
  const skippedCount = Object.values(selections).filter((v) => v === "skip").length;

  return (
    <div className="flex flex-col" style={{ maxHeight: "80vh" }}>
      {/* sticky header */}
      <div className="border-b border-gray-100 px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Wizard — Transazioni non risolte</p>
            <p className="mt-1 text-sm text-gray-600">
              Assegna un veicolo a ciascun gruppo. Puoi applicarlo a tutte le righe dello stesso operatore in un colpo solo.
            </p>
          </div>
          <div className="shrink-0 text-right text-xs text-gray-500">
            <p><span className="font-semibold text-emerald-700">{resolvedCount}</span> assegnate</p>
            <p><span className="font-semibold text-gray-500">{skippedCount}</span> saltate</p>
            <p className="text-gray-400">{unresolved.length - resolvedCount - skippedCount} da gestire</p>
          </div>
        </div>
      </div>

      {/* scrollable groups */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        {groups.map((group) => {
          const groupSearch = vehicleSearch[group.key] ?? "";
          const options = filteredVehicles(groupSearch);
          // Check if all rows in group have same selection
          const groupSel = group.rows[0] ? selections[group.rows[0].row_index] : undefined;
          const allSame = group.rows.every((r) => selections[r.row_index] === groupSel);

          return (
            <div key={group.key} className="rounded-[20px] border border-[#e6ebe5] bg-[#fbfcfa] p-4">
              {/* group header */}
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-gray-900">{group.label}</p>
                  <p className="mt-0.5 text-xs text-gray-500">
                    {group.rows[0]?.reason_type === "no_card_operator" ? "Tessera senza operatore" : "Operatore senza mezzo assegnato"}
                    {" · "}{group.rows.length} transazione{group.rows.length > 1 ? "i" : ""}
                  </p>
                </div>
                {/* batch vehicle selector */}
                <div className="w-full sm:w-64">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 mb-1">
                    Applica veicolo a tutto il gruppo
                  </p>
                  <input
                    type="text"
                    className="form-control w-full text-xs"
                    placeholder="Cerca veicolo..."
                    value={groupSearch}
                    onChange={(e) => setVehicleSearch((prev) => ({ ...prev, [group.key]: e.target.value }))}
                  />
                  {groupSearch && (
                    <div className="mt-1 max-h-40 overflow-y-auto rounded-[12px] border border-[#e6ebe5] bg-white shadow-sm">
                      {options.length === 0 ? (
                        <p className="px-3 py-2 text-xs text-gray-400">Nessun veicolo trovato</p>
                      ) : (
                        options.map((v) => (
                          <button
                            key={v.id}
                            className="block w-full px-3 py-2 text-left text-xs text-gray-800 hover:bg-[#f0f7f3] transition"
                            onClick={() => {
                              setGroupVehicle(group.key, v.id);
                              setVehicleSearch((prev) => ({ ...prev, [group.key]: v.label }));
                            }}
                          >
                            {v.label}
                          </button>
                        ))
                      )}
                    </div>
                  )}
                  {allSame && groupSel && groupSel !== "skip" && (
                    <p className="mt-1 text-[10px] text-emerald-700 font-semibold">
                      ✓ {vehicles.find((v) => v.id === groupSel)?.label ?? groupSel}
                    </p>
                  )}
                </div>
              </div>

              {/* individual rows */}
              <div className="mt-4 space-y-2">
                {group.rows.map((row) => {
                  const sel = selections[row.row_index];
                  const selectedVehicle = sel && sel !== "skip" ? vehicles.find((v) => v.id === sel) : null;
                  return (
                    <div
                      key={row.row_index}
                      className={`flex flex-wrap items-center gap-3 rounded-[14px] border px-3 py-2.5 text-xs transition ${
                        sel === "skip" ? "border-gray-200 bg-gray-50 opacity-50" :
                        selectedVehicle ? "border-emerald-200 bg-emerald-50" :
                        "border-[#e6ebe5] bg-white"
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-gray-800">
                          Riga {row.row_index} — {formatDate(row.fueled_at_iso)}
                        </p>
                        <p className="mt-0.5 text-gray-500">
                          {row.liters ? `${row.liters} L` : ""}
                          {row.total_cost ? ` · €${row.total_cost}` : ""}
                          {row.targa ? ` · Targa: ${row.targa}` : ""}
                        </p>
                        {selectedVehicle && (
                          <p className="mt-0.5 text-emerald-700 font-semibold">{selectedVehicle.label}</p>
                        )}
                      </div>
                      <div className="flex gap-1.5">
                        {sel !== "skip" && (
                          <button
                            className="rounded-full border border-gray-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-gray-600 hover:bg-gray-50"
                            onClick={() => setSelections((prev) => ({ ...prev, [row.row_index]: "skip" }))}
                          >
                            Salta
                          </button>
                        )}
                        {sel === "skip" && (
                          <button
                            className="rounded-full border border-amber-300 bg-amber-50 px-2.5 py-1 text-[10px] font-semibold text-amber-700 hover:bg-amber-100"
                            onClick={() => setSelections((prev) => { const n = { ...prev }; delete n[row.row_index]; return n; })}
                          >
                            Ripristina
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* footer */}
      <div className="border-t border-gray-100 px-6 py-4">
        {error && <p className="mb-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        <div className="flex items-center justify-between gap-3">
          <button className="btn-secondary" onClick={onBack} disabled={submitting}>← Indietro</button>
          <button
            className="btn-primary"
            onClick={() => void handleSubmit()}
            disabled={submitting || resolvedCount === 0}
          >
            {submitting ? "Importazione..." : `Importa ${resolvedCount} transazioni`}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main modal ───────────────────────────────────────────────────────────

type Step = "upload" | "result" | "wizard" | "done";

export function ImportFleetTransactionsModal({ open, onClose }: ImportFleetTransactionsModalProps) {
  const [step, setStep] = useState<Step>("upload");
  const [result, setResult] = useState<ImportResult | null>(null);
  const [wizardImported, setWizardImported] = useState(0);

  const reset = useCallback(() => {
    setStep("upload");
    setResult(null);
    setWizardImported(0);
  }, []);

  useEffect(() => { if (!open) reset(); }, [open, reset]);

  if (!open) return null;

  const handleResult = (r: ImportResult) => {
    setResult(r);
    setStep("result");
  };

  const handleWizardDone = (imported: number) => {
    setWizardImported(imported);
    setStep("done");
  };

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        {/* header */}
        <div className="border-b border-gray-100 px-6 py-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Transazioni flotte</p>
          <h2 className="mt-2 text-2xl font-semibold text-gray-900">
            {step === "wizard" ? "Risolvi transazioni in sospeso" : "Carica file Excel rifornimenti"}
          </h2>
          {step !== "wizard" && (
            <p className="mt-1 text-sm text-gray-500">
              L&apos;import completa i fuel log con i dati non esposti da WhiteCompany. Le righe già importate vengono saltate.
            </p>
          )}
        </div>

        {step === "upload" && <UploadStep onResult={handleResult} />}

        {step === "result" && result && (
          <>
            <ResultStep
              result={result}
              onWizard={() => setStep("wizard")}
              onClose={() => onClose(true)}
            />
          </>
        )}

        {step === "wizard" && result && (
          <WizardStep
            unresolved={result.unresolved}
            onDone={handleWizardDone}
            onBack={() => setStep("result")}
          />
        )}

        {step === "done" && (
          <div className="px-6 py-8 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50">
              <span className="text-2xl text-emerald-600">✓</span>
            </div>
            <p className="text-lg font-semibold text-gray-900">
              {wizardImported > 0 ? `${wizardImported} transazioni importate` : "Operazione completata"}
            </p>
            <p className="mt-2 text-sm text-gray-500">
              {wizardImported > 0
                ? "Le transazioni risolte manualmente sono state aggiunte al registro carburante."
                : "Nessuna nuova transazione da importare."}
            </p>
            <button className="btn-primary mt-6" onClick={() => onClose(true)}>Chiudi</button>
          </div>
        )}
      </div>
    </div>
  );
}
