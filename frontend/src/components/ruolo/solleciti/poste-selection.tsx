"use client";

import { useState } from "react";

import { createPosteLot } from "@/lib/ruolo-poste-dispatch-api";
import type { RuoloTributiReminderBatchItemResponse } from "@/types/ruolo";
import type { PosteDispatchLotDetail } from "@/types/ruolo-poste-dispatch";
import { errorMessage } from "@/components/ruolo/poste-dispatch/labels";

export const MAX_POSTE_ITEMS = 50;

type Item = RuoloTributiReminderBatchItemResponse;
type Selected = { id: string; label: string };

// Same rule as the backend candidates: only generated PDFs can become Poste drafts.
export function canSendToPoste(item: Item): boolean {
  return item.status === "generated" && (item.generated_document_path ?? "").toLowerCase().endsWith(".pdf");
}

// The selection survives switching between generated batches, so one Poste lot can gather several of them.
export function usePosteSelection() {
  const [selected, setSelected] = useState<Selected[]>([]);
  function toggle(item: Item) {
    setSelected((current) => {
      if (current.some((entry) => entry.id === item.id)) return current.filter((entry) => entry.id !== item.id);
      if (current.length >= MAX_POSTE_ITEMS) return current;
      return [...current, { id: item.id, label: item.display_name || item.codice_fiscale }];
    });
  }
  return { selected, toggle, isSelected: (id: string) => selected.some((entry) => entry.id === id), clear: () => setSelected([]) };
}

type SelectProps = { item: Item; canEdit: boolean; checked: boolean; onToggle: (item: Item) => void };

export function SelectForPoste({ item, canEdit, checked, onToggle }: SelectProps) {
  if (!canEdit || !canSendToPoste(item)) return null;
  return <label className="mt-3 flex items-center gap-2 text-sm font-medium text-slate-800">
    <input type="checkbox" checked={checked} onChange={() => onToggle(item)} />
    Seleziona per Posta Online
  </label>;
}

type BarProps = { token: string; selection: ReturnType<typeof usePosteSelection>; onCreated: (lot: PosteDispatchLotDetail) => void };

export function SelectionBar({ token, selection, onCreated }: BarProps) {
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const count = selection.selected.length;

  async function upload() {
    setBusy(true);
    setError(null);
    try {
      const lot = await createPosteLot(token, title, selection.selected.map((entry) => entry.id));
      selection.clear();
      setTitle("");
      onCreated(lot);
    } catch (err) {
      setError(errorMessage(err, "Lotto Poste non creato"));
    } finally {
      setBusy(false);
    }
  }

  return <section aria-label="Selezione per Posta Online" className="rounded-[28px] border border-sky-200 bg-sky-50 p-5 text-sm text-sky-950">
    <p className="font-semibold">{count} di massimo {MAX_POSTE_ITEMS} solleciti selezionati</p>
    {count > 0 && <p className="mt-1 text-sky-900">{selection.selected.map((entry) => entry.label).join(", ")}</p>}
    <div className="mt-3 flex flex-wrap gap-2">
      <input className="form-control min-w-64 flex-1" aria-label="Titolo lotto Poste" placeholder="Es. Solleciti 2021 Oristano" value={title} onChange={(event) => setTitle(event.target.value)} />
      <button type="button" className="btn-primary" disabled={busy || !title.trim() || count === 0} onClick={() => void upload()}>{busy ? "Creazione..." : `Carica su Poste (${count})`}</button>
      {count > 0 && <button type="button" className="btn-secondary" disabled={busy} onClick={selection.clear}>Svuota</button>}
    </div>
    <p className="mt-2 text-xs text-sky-900">Crea il lotto Posta Online: poi verifica indirizzi e crea le bozze nella scheda Posta Online. INVIA resta all&apos;operatore, su Poste.</p>
    {error && <p role="alert" className="mt-2 text-rose-800">{error}</p>}
  </section>;
}
