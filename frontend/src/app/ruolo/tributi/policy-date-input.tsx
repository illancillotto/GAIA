import { useEffect, useId, useRef } from "react";
import { CalendarIcon } from "@/components/ui/icons";

export function formatPolicyDate(value: string | null | undefined): string {
  return value?.replace(/^(\d{4})-(\d{2})-(\d{2})$/, "$3/$2/$1") || "-";
}

function parseDateInput(value: string): string | null {
  const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);
  if (!match) return null;
  const [, day, month, year] = match;
  const iso = `${year}-${month}-${day}`;
  const date = new Date(`${iso}T00:00:00Z`);
  if (Number(year) < 1 || date.getUTCDate() !== Number(day)) return null;
  return iso;
}

export function PolicyDateInput({ label, value, onChange }: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const display = value ? formatPolicyDate(value) : "";
  const iso = parseDateInput(display);
  useEffect(() => {
    input.current!.setCustomValidity(display && !iso ? "Inserisci una data valida nel formato gg/mm/aaaa." : "");
  }, [display, iso]);
  return (
    <div className="grid gap-1 text-xs font-semibold text-gray-600">
      <label htmlFor={id}>{label}</label>
      <div className="relative min-w-0">
        <input ref={input} id={id} type="text" placeholder="gg/mm/aaaa" maxLength={10} value={display} onChange={(event) => onChange(parseDateInput(event.target.value) ?? event.target.value)} className="w-full rounded-xl border border-gray-200 py-2 pl-3 pr-10 text-sm font-normal outline-none focus:border-amber-400" />
        <div className="absolute inset-y-0 right-1 flex w-8 items-center justify-center rounded-lg focus-within:ring-2 focus-within:ring-amber-500">
          <CalendarIcon className="h-4 w-4" />
          <input aria-label={`Calendario ${label}`} type="date" value={iso ?? ""} onChange={(event) => onChange(event.target.value)} className="absolute inset-0 w-full cursor-pointer opacity-0 [&::-webkit-calendar-picker-indicator]:absolute [&::-webkit-calendar-picker-indicator]:inset-0 [&::-webkit-calendar-picker-indicator]:h-full [&::-webkit-calendar-picker-indicator]:w-full" />
        </div>
      </div>
    </div>
  );
}
