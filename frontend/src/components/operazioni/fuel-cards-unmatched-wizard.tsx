"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { assignFuelCard, getUnmatchedFuelCards, ignoreFuelCardDriver } from "@/features/operazioni/api/client";
import { cn } from "@/lib/cn";

type FuelCardItem = {
  id: string;
  pan: string;
  codice: string | null;
  sigla: string | null;
  cod: string | null;
  driver: string | null;
  is_blocked: boolean;
  expires_at: string | null;
};

type OperatorItem = {
  id: string;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  username: string | null;
};

type FuelCardsUnmatchedWizardProps = {
  open: boolean;
  onClose: (didUpdate: boolean) => void;
  operators: OperatorItem[];
};

function operatorLabel(operator: OperatorItem): string {
  const name = `${operator.last_name ?? ""} ${operator.first_name ?? ""}`.trim();
  return name || operator.email || operator.username || "Operatore";
}

function normalizeKey(value: string): string {
  return value
    .trim()
    .toUpperCase()
    .replace(/[(),.]/g, " ")
    .replace(/\s+/g, " ")
    .replace(/[^A-Z0-9 ]+/g, "")
    .replace(/\s+/g, "");
}

function suggestOperatorId(driver: string | null, operators: OperatorItem[]): string | null {
  if (!driver) return null;
  const driverBase = driver.split("(")[0]?.trim() ?? driver;
  const driverKey = normalizeKey(driverBase.replace(",", " "));
  if (!driverKey) return null;

  let best: { id: string; score: number } | null = null;
  for (const op of operators) {
    const label = operatorLabel(op);
    const key = normalizeKey(label);
    if (!key) continue;
    let score = 0;
    if (driverKey === key) score = 10_000;
    else if (driverKey.includes(key) || key.includes(driverKey)) score = 2_000 + Math.min(driverKey.length, key.length);
    else {
      // token overlap heuristic
      const tokens = label.toUpperCase().replace(/[^A-Z0-9 ]+/g, " ").split(/\s+/).filter(Boolean);
      const driverTokens = driverBase.toUpperCase().replace(/[^A-Z0-9 ]+/g, " ").split(/\s+/).filter(Boolean);
      const overlap = tokens.filter((t) => driverTokens.includes(t)).length;
      score = overlap * 100 + Math.min(driverKey.length, key.length);
    }
    if (!best || score > best.score) best = { id: op.id, score };
  }
  if (!best || best.score < 220) return null;
  return best.id;
}

export function FuelCardsUnmatchedWizard({ open, onClose, operators }: FuelCardsUnmatchedWizardProps) {
  const [items, setItems] = useState<FuelCardItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<FuelCardItem | null>(null);
  const [selectedOperatorId, setSelectedOperatorId] = useState("");
  const [operatorSearch, setOperatorSearch] = useState("");
  const [note, setNote] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [didUpdate, setDidUpdate] = useState(false);

  const operatorOptions = useMemo(() => {
    const normalized = operatorSearch.trim().toLowerCase();
    return [...operators]
      .map((op) => ({ value: op.id, label: operatorLabel(op) }))
      .filter((opt) => (normalized ? opt.label.toLowerCase().includes(normalized) : true))
      .sort((a, b) => a.label.localeCompare(b.label, "it"));
  }, [operatorSearch, operators]);

  const suggestedOperator = useMemo(() => {
    if (!selected) return null;
    const id = suggestOperatorId(selected.driver, operators);
    if (!id) return null;
    const match = operators.find((op) => op.id === id);
    return match ? { id, label: operatorLabel(match) } : null;
  }, [operators, selected]);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const payload = await getUnmatchedFuelCards({ page_size: "50" });
      setItems((payload.items ?? []) as FuelCardItem[]);
      setTotal((payload.total ?? payload.items?.length ?? 0) as number);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore caricamento carte non matchate");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    void loadData();
  }, [loadData, open]);

  useEffect(() => {
    if (!open) {
      setItems([]);
      setTotal(0);
      setError(null);
      setSelected(null);
      setSelectedOperatorId("");
      setOperatorSearch("");
      setNote("");
      setIsSaving(false);
      setDidUpdate(false);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    if (!selected) return;
    const suggestion = suggestOperatorId(selected.driver, operators);
    if (suggestion) {
      setSelectedOperatorId(suggestion);
    } else {
      setSelectedOperatorId("");
    }
    setOperatorSearch("");
    setNote("");
  }, [open, operators, selected]);

  if (!open) return null;

  async function handleAssign(): Promise<void> {
    if (!selected) return;
    if (!selectedOperatorId) {
      setError("Seleziona un operatore per completare l'assegnazione.");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await assignFuelCard(selected.id, {
        wc_operator_id: selectedOperatorId,
        driver_raw: selected.driver ?? null,
        note: note.trim() ? note.trim() : null,
      });
      setDidUpdate(true);
      setSelected(null);
      setSelectedOperatorId("");
      setNote("");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Assegnazione non riuscita");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleIgnore(): Promise<void> {
    if (!selected) return;
    setIsSaving(true);
    setError(null);
    try {
      await ignoreFuelCardDriver(selected.id, note.trim() ? note.trim() : null);
      setDidUpdate(true);
      setSelected(null);
      setSelectedOperatorId("");
      setOperatorSearch("");
      setNote("");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operazione non riuscita");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
      <div className="w-full max-w-4xl rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="border-b border-gray-100 px-6 py-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Wizard match driver</p>
          <h2 className="mt-2 text-2xl font-semibold text-gray-900">Carte con Driver non matchato</h2>
          <p className="mt-1 text-sm text-gray-500">
            Qui gestisci i casi in cui la colonna Driver dell&apos;Excel non corrisponde automaticamente a un operatore esistente.
          </p>
        </div>

        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.2fr,0.8fr]">
          <div>
            <div className="mb-3 flex items-center justify-between gap-3">
              <p className="text-sm text-gray-600">
                Totale non matchate: <span className="font-semibold text-gray-900">{total}</span>
              </p>
              <button className="btn-secondary" type="button" onClick={() => void loadData()} disabled={isLoading}>
                Aggiorna
              </button>
            </div>

            {error ? (
              <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
            ) : null}

            {isLoading ? (
              <p className="text-sm text-gray-500">Caricamento in corso.</p>
            ) : items.length === 0 ? (
              <div className="rounded-[24px] border border-[#d9dfd6] bg-[#fbfcfa] px-4 py-4 text-sm text-gray-600">
                Nessuna carta da matchare.
              </div>
            ) : (
              <div className="max-h-[28rem] overflow-y-auto pr-1">
                <div className="space-y-3">
                  {items.map((card) => {
                    const isSelected = selected?.id === card.id;
                    return (
                      <button
                        key={card.id}
                        type="button"
                        className={cn(
                          "w-full rounded-[24px] border px-4 py-4 text-left transition",
                          isSelected
                            ? "border-[#1D4E35]/30 bg-[#edf5f0]"
                            : "border-[#e6ebe5] bg-[linear-gradient(180deg,_#ffffff,_#fbfcfa)] hover:-translate-y-0.5 hover:border-[#c9d6cd] hover:shadow-sm",
                        )}
                        onClick={() => setSelected(card)}
                      >
                        <p className="text-sm font-semibold text-gray-900">PAN {card.pan}</p>
                        <p className="mt-1 truncate text-xs text-gray-500">
                          Driver: {card.driver || "—"}
                          {card.codice ? ` · Codice ${card.codice}` : ""}
                          {card.sigla ? ` · ${card.sigla}` : ""}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          <div className="rounded-[28px] border border-[#d9dfd6] bg-[#fbfcfa] p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#5f6d61]">Assegnazione</p>
            {selected ? (
              <div className="mt-3 space-y-3">
                <div className="rounded-2xl border border-[#e4e8e2] bg-white px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-gray-500">Carta selezionata</p>
                  <p className="mt-2 text-sm font-semibold text-gray-900">PAN {selected.pan}</p>
                  <p className="mt-1 text-xs text-gray-500">Driver: {selected.driver || "—"}</p>
                </div>

                <label className="block">
                  <span className="label-caption">Operatore</span>
                  <input
                    className="form-control mt-2"
                    value={operatorSearch}
                    onChange={(e) => setOperatorSearch(e.target.value)}
                    placeholder="Cerca operatore..."
                  />
                  <select
                    className="form-control mt-2"
                    value={selectedOperatorId}
                    onChange={(e) => setSelectedOperatorId(e.target.value)}
                  >
                    <option value="">Seleziona operatore…</option>
                    {operatorOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  {suggestedOperator ? (
                    <p className="mt-2 text-xs text-gray-500">
                      Suggerimento: <span className="font-medium text-gray-700">{suggestedOperator.label}</span>
                    </p>
                  ) : null}
                </label>

                <label className="block">
                  <span className="label-caption">Nota (opzionale)</span>
                  <input className="form-control mt-2" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Es. correzione manuale driver" />
                </label>

                <button className="btn-primary w-full" type="button" onClick={() => void handleAssign()} disabled={isSaving}>
                  {isSaving ? "Salvataggio..." : "Assegna carta"}
                </button>
                <button className="btn-secondary w-full" type="button" onClick={() => void handleIgnore()} disabled={isSaving}>
                  Segna driver come ignorato
                </button>
              </div>
            ) : (
              <p className="mt-3 text-sm text-gray-600">Seleziona una carta a sinistra per assegnarla manualmente.</p>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-gray-100 px-6 py-5">
          <button className="btn-secondary" type="button" onClick={() => onClose(didUpdate)} disabled={isSaving}>
            Chiudi
          </button>
        </div>
      </div>
    </div>
  );
}

