"use client";

import type { SisterCredentialAvailabilitySchedule } from "@/types/api";

const DAYS = ["Lunedi", "Martedi", "Mercoledi", "Giovedi", "Venerdi", "Sabato", "Domenica"];
const SHORT_DAYS = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"];
const MAX_WINDOWS_PER_DAY = 4;
const DEFAULT_WINDOW = { start: "18:00", end: "08:00" };

export const OUTSIDE_OFFICE_SCHEDULE: SisterCredentialAvailabilitySchedule = {
  timezone: "Europe/Rome",
  weekly: {
    "0": [{ start: "18:00", end: "08:00" }],
    "1": [{ start: "18:00", end: "08:00" }],
    "2": [{ start: "18:00", end: "08:00" }],
    "3": [{ start: "18:00", end: "08:00" }],
    "4": [{ start: "18:00", end: "08:00" }],
    "5": [{ start: "00:00", end: "00:00" }],
    "6": [{ start: "00:00", end: "00:00" }],
  },
};

function copySchedule(schedule: SisterCredentialAvailabilitySchedule): SisterCredentialAvailabilitySchedule {
  return {
    timezone: "Europe/Rome",
    weekly: Object.fromEntries(
      Object.entries(schedule.weekly).map(([day, windows]) => [day, windows.map((window) => ({ ...window }))]),
    ),
  };
}

export function defaultSisterSchedule(): SisterCredentialAvailabilitySchedule {
  return copySchedule(OUTSIDE_OFFICE_SCHEDULE);
}

export function formatSisterSchedule(
  enabled: boolean,
  schedule: SisterCredentialAvailabilitySchedule | null,
): string {
  if (!enabled) return "Sempre disponibile";
  if (!schedule) return "Nessuna fascia configurata";
  const days = SHORT_DAYS.flatMap((label, day) => {
    const windows = schedule.weekly[String(day)] ?? [];
    return windows.length > 0
      ? [`${label} ${windows.map((window) => `${window.start}-${window.end}`).join(", ")}`]
      : [];
  });
  return days.length > 0 ? days.join(" · ") : "Nessuna fascia configurata";
}

function romeClock(date: Date): { weekday: number; minute: number } {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Europe/Rome",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  const weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].indexOf(values.weekday);
  return { weekday, minute: Number(values.hour) * 60 + Number(values.minute) };
}

function toMinutes(value: string): number {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

export function sisterCredentialIsAvailable(
  enabled: boolean,
  schedule: SisterCredentialAvailabilitySchedule | null,
  at = new Date(),
): boolean {
  if (!enabled) return true;
  if (!schedule) return false;
  const { weekday, minute } = romeClock(at);
  const todayAvailable = (schedule.weekly[String(weekday)] ?? []).some((window) => {
    const start = toMinutes(window.start);
    const end = toMinutes(window.end);
    return start === end || (start < end ? start <= minute && minute < end : minute >= start);
  });
  if (todayAvailable) return true;
  return (schedule.weekly[String((weekday + 6) % 7)] ?? []).some((window) => {
    const start = toMinutes(window.start);
    const end = toMinutes(window.end);
    return start > end && minute < end;
  });
}

export function nextSisterAvailability(
  enabled: boolean,
  schedule: SisterCredentialAvailabilitySchedule | null,
  at = new Date(),
): Date | null {
  if (sisterCredentialIsAvailable(enabled, schedule, at)) return at;
  const validTime = /^(?:[01]\d|2[0-3]):[0-5]\d$/;
  const hasValidWindow = schedule && Object.entries(schedule.weekly).some(([day, windows]) =>
    /^[0-6]$/.test(day) && windows.some((window) => validTime.test(window.start) && validTime.test(window.end)),
  );
  if (!hasValidWindow) return null;
  const candidate = new Date(at);
  candidate.setSeconds(0, 0);
  while (true) {
    candidate.setTime(candidate.getTime() + 60_000);
    if (sisterCredentialIsAvailable(enabled, schedule, candidate)) return new Date(candidate);
  }
}

type SisterAvailabilityScheduleEditorProps = {
  enabled: boolean;
  schedule: SisterCredentialAvailabilitySchedule;
  onEnabledChange: (enabled: boolean) => void;
  onScheduleChange: (schedule: SisterCredentialAvailabilitySchedule) => void;
};

export function SisterAvailabilityScheduleEditor(props: SisterAvailabilityScheduleEditorProps) {
  function replaceDay(day: number, windows: SisterCredentialAvailabilitySchedule["weekly"][string]): void {
    const weekly = { ...props.schedule.weekly };
    weekly[String(day)] = windows;
    props.onScheduleChange({ timezone: "Europe/Rome", weekly });
  }

  function toggleDay(day: number, enabled: boolean): void {
    replaceDay(day, enabled ? [{ ...DEFAULT_WINDOW }] : []);
  }

  function updateWindow(day: number, index: number, field: "start" | "end", value: string): void {
    const windows = props.schedule.weekly[String(day)].map((window, currentIndex) =>
      currentIndex === index ? { ...window, [field]: value } : window,
    );
    replaceDay(day, windows);
  }

  function addWindow(day: number): void {
    replaceDay(day, [...props.schedule.weekly[String(day)], { ...DEFAULT_WINDOW }]);
  }

  function removeWindow(day: number, index: number): void {
    replaceDay(day, props.schedule.weekly[String(day)].filter((_, currentIndex) => currentIndex !== index));
  }

  return <section className="rounded-2xl border border-[#dbe6dc] bg-[#f6faf6] p-4 md:col-span-2 lg:col-span-3">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <label className="flex max-w-xl items-start gap-3">
        <input checked={props.enabled} className="mt-1 h-4 w-4 accent-[#1D4E35]" onChange={(event) => props.onEnabledChange(event.target.checked)} type="checkbox" />
        <span><span className="block text-sm font-semibold text-gray-900">Usa solo fuori dall&apos;orario dell&apos;operatore</span><span className="mt-1 block text-xs leading-5 text-gray-600">Il worker avvia nuove sessioni soltanto nelle fasce indicate. I test manuali restano sempre disponibili.</span></span>
      </label>
      <button className="rounded-xl border border-[#b9cdbd] bg-white px-3 py-2 text-xs font-semibold text-[#1D4E35]" onClick={() => props.onScheduleChange(defaultSisterSchedule())} type="button">Applica fuori orario ufficio</button>
    </div>
    {props.enabled ? <div className="mt-4 space-y-2 border-t border-[#dbe6dc] pt-4">
      {DAYS.map((label, day) => {
        const windows = props.schedule.weekly[String(day)] ?? [];
        return <div className="grid items-start gap-3 rounded-xl bg-white px-3 py-3 sm:grid-cols-[120px_1fr]" key={label}>
          <label className="flex items-center gap-2 pt-2 text-sm font-semibold text-gray-800"><input aria-label={`${label} disponibile`} checked={windows.length > 0} className="h-4 w-4 accent-[#1D4E35]" onChange={(event) => toggleDay(day, event.target.checked)} type="checkbox" />{label}</label>
          {windows.length > 0 ? <div className="space-y-2">
            {windows.map((window, index) => {
              const startLabel = index === 0 ? `${label} dalle` : `${label} fascia ${index + 1} dalle`;
              const endLabel = index === 0 ? `${label} alle` : `${label} fascia ${index + 1} alle`;
              return <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600" key={`${index}-${window.start}-${window.end}`}>
                <span className="w-14 font-semibold text-gray-500">Fascia {index + 1}</span>
                <span>Dalle</span><input aria-label={startLabel} className="form-control max-w-28 py-1.5" onChange={(event) => updateWindow(day, index, "start", event.target.value)} type="time" value={window.start} />
                <span>alle</span><input aria-label={endLabel} className="form-control max-w-28 py-1.5" onChange={(event) => updateWindow(day, index, "end", event.target.value)} type="time" value={window.end} />
                {window.start === window.end ? <span className="font-semibold text-[#326447]">Tutto il giorno</span> : null}
                <button aria-label={`Rimuovi fascia ${index + 1} ${label}`} className="rounded-lg border border-red-100 px-2 py-1 font-semibold text-red-600 transition hover:bg-red-50" onClick={() => removeWindow(day, index)} type="button">Rimuovi</button>
              </div>;
            })}
            <button className="rounded-lg border border-[#b9cdbd] px-2.5 py-1.5 text-xs font-semibold text-[#1D4E35] disabled:cursor-not-allowed disabled:opacity-45" disabled={windows.length >= MAX_WINDOWS_PER_DAY} onClick={() => addWindow(day)} type="button">Aggiungi fascia {label}</button>
          </div> : <span className="pt-2 text-xs text-gray-500">Nessun utilizzo automatico in questa giornata</span>}
        </div>;
      })}
      <p className="pt-1 text-xs text-gray-500">Puoi impostare fino a quattro fasce per giorno. Se l&apos;ora finale e precedente a quella iniziale, la fascia continua durante la notte successiva.</p>
    </div> : null}
  </section>;
}
