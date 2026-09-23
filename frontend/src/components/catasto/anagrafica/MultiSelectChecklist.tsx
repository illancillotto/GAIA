"use client";

import { useMemo, useState } from "react";

export type MultiSelectOption = { value: string; label: string };

type MultiSelectChecklistProps = {
  label: string;
  options: MultiSelectOption[];
  selected: string[];
  onChange: (selected: string[]) => void;
  disabled?: boolean;
  emptyMessage?: string;
};

export function MultiSelectChecklist({
  label,
  options,
  selected,
  onChange,
  disabled = false,
  emptyMessage = "Nessuna opzione disponibile.",
}: MultiSelectChecklistProps) {
  const [filter, setFilter] = useState("");
  const selectedSet = useMemo(() => new Set(selected), [selected]);
  const visible = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    return needle ? options.filter((option) => option.label.toLowerCase().includes(needle)) : options;
  }, [filter, options]);

  function toggle(value: string): void {
    onChange(selectedSet.has(value) ? selected.filter((item) => item !== value) : [...selected, value]);
  }

  function selectVisible(): void {
    const next = new Set(selected);
    for (const option of visible) next.add(option.value);
    onChange(options.filter((option) => next.has(option.value)).map((option) => option.value));
  }

  function clearVisible(): void {
    const hidden = new Set(visible.map((option) => option.value));
    onChange(selected.filter((value) => !hidden.has(value)));
  }

  return (
    <fieldset className="min-w-64 flex-1 text-sm" disabled={disabled}>
      <legend className="label-caption">
        {label} <span className="font-normal text-gray-500">({selected.length} selezionati)</span>
      </legend>
      <div className="mt-1 flex flex-wrap items-center gap-2">
        <input
          type="search"
          aria-label={`Filtra ${label.toLowerCase()}`}
          placeholder="Filtra..."
          className="min-w-40 flex-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 shadow-sm"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
        />
        <button type="button" className="btn-secondary" disabled={visible.length === 0} onClick={selectVisible}>
          Seleziona tutti
        </button>
        <button type="button" className="btn-secondary" disabled={selected.length === 0} onClick={clearVisible}>
          Deseleziona
        </button>
      </div>
      <div className="mt-2 max-h-48 overflow-y-auto rounded-lg border border-gray-300 bg-white p-2 shadow-sm">
        {options.length === 0 ? (
          <p className="px-1 py-0.5 text-sm text-gray-500">{emptyMessage}</p>
        ) : visible.length === 0 ? (
          <p className="px-1 py-0.5 text-sm text-gray-500">Nessun risultato per il filtro.</p>
        ) : (
          visible.map((option) => (
            <label key={option.value} className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-sm text-gray-900 hover:bg-gray-50">
              <input type="checkbox" checked={selectedSet.has(option.value)} onChange={() => toggle(option.value)} />
              <span>{option.label}</span>
            </label>
          ))
        )}
      </div>
    </fieldset>
  );
}
