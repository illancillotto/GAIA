"use client";

import type { SisterCredentialAvailabilitySchedule } from "@/types/api";

const DAYS = ["Lunedi", "Martedi", "Mercoledi", "Giovedi", "Venerdi", "Sabato", "Domenica"];

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
  function updateDay(day: number, enabled: boolean, field?: "start" | "end", value?: string): void {
    const current = props.schedule.weekly[String(day)]?.[0] ?? { start: "18:00", end: "08:00" };
    const weekly = { ...props.schedule.weekly };
    weekly[String(day)] = enabled ? [{ ...current, ...(field && value ? { [field]: value } : {}) }] : [];
    props.onScheduleChange({ timezone: "Europe/Rome", weekly });
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
        const window = props.schedule.weekly[String(day)]?.[0];
        return <div className="grid items-center gap-2 rounded-xl bg-white px-3 py-2 sm:grid-cols-[120px_1fr]" key={label}>
          <label className="flex items-center gap-2 text-sm font-semibold text-gray-800"><input aria-label={`${label} disponibile`} checked={Boolean(window)} className="h-4 w-4 accent-[#1D4E35]" onChange={(event) => updateDay(day, event.target.checked)} type="checkbox" />{label}</label>
          {window ? <div className="flex items-center gap-2 text-xs text-gray-600"><span>Dalle</span><input aria-label={`${label} dalle`} className="form-control max-w-28 py-1.5" onChange={(event) => updateDay(day, true, "start", event.target.value)} type="time" value={window.start} /><span>alle</span><input aria-label={`${label} alle`} className="form-control max-w-28 py-1.5" onChange={(event) => updateDay(day, true, "end", event.target.value)} type="time" value={window.end} />{window.start === window.end ? <span className="font-semibold text-[#326447]">Tutto il giorno</span> : null}</div> : <span className="text-xs text-gray-500">Riservata all&apos;operatore per tutta la giornata</span>}
        </div>;
      })}
      <p className="pt-1 text-xs text-gray-500">Se l&apos;ora finale e precedente a quella iniziale, la fascia continua durante la notte successiva.</p>
    </div> : null}
  </section>;
}
