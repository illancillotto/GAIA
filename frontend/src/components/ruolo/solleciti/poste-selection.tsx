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
  // A whole batch from the list: all its reminders in, or all out when they are all in already.
  function toggleAll(entries: Selected[]) {
    setSelected((current) => {
      const ids = new Set(current.map((entry) => entry.id));
      if (entries.every((entry) => ids.has(entry.id))) return current.filter((entry) => !entries.some((other) => other.id === entry.id));
      return [...current, ...entries.filter((entry) => !ids.has(entry.id))].slice(0, MAX_POSTE_ITEMS);
    });
  }
  return { selected, toggle, toggleAll, isSelected: (id: string) => selected.some((entry) => entry.id === id), clear: () => setSelected([]) };
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

  if (count === 0) return null;
  const names = selection.selected.map((entry) => entry.label).join(", ");
  // Sticky at the bottom: the checkboxes sit deep in the batch detail, the upload must stay at hand.
  return <section aria-label="Selezione per Posta Online" className="sticky bottom-4 z-20 rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-950 shadow-lg">
    <div className="flex flex-wrap items-center gap-3">
      <div className="min-w-0 flex-1 basis-64">
        <p className="font-semibold">{count} di massimo {MAX_POSTE_ITEMS} solleciti selezionati</p>
        <p className="truncate text-sky-900" title={names}>{names}</p>
      </div>
      <input className="form-control min-w-0 flex-1 basis-56" aria-label="Titolo lotto Poste" placeholder="Titolo lotto, es. Solleciti 2021 Oristano" value={title} onChange={(event) => setTitle(event.target.value)} />
      <button type="button" className="btn-primary" disabled={busy || !title.trim()} onClick={() => void upload()}>{busy ? "Creazione..." : `Carica su Poste (${count})`}</button>
      <button type="button" className="btn-secondary" disabled={busy} onClick={selection.clear}>Svuota</button>
    </div>
    <p className="mt-2 text-xs text-sky-900">Crea il lotto Posta Online: poi verifica indirizzi e crea le bozze nella scheda Posta Online. INVIA resta all&apos;operatore, su Poste.</p>
    {error && <p role="alert" className="mt-2 text-rose-800">{error}</p>}
  </section>;
}
