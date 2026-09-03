"use client";

import type {
  SisterCredentialAvailabilitySchedule,
  SisterCredentialAvailabilityWindow,
  SisterCredentialNthWeekdayException,
} from "@/types/api";

const DAYS = ["Lunedi", "Martedi", "Mercoledi", "Giovedi", "Venerdi", "Sabato", "Domenica"];
const SHORT_DAYS = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"];
const MAX_WINDOWS_PER_DAY = 4;
const DEFAULT_WINDOW = { start: "15:00", end: "07:30" };
const FIRST_SATURDAY_WINDOW = { start: "14:00", end: "00:00" };
const VALID_TIME = /^(?:[01]\d|2[0-3]):[0-5]\d$/;

export const FIRST_SATURDAY_EXCEPTION: SisterCredentialNthWeekdayException = {
  kind: "nth_weekday_of_month",
  weekday: 5,
  occurrence: 1,
  windows: [{ ...FIRST_SATURDAY_WINDOW }],
};

export const OUTSIDE_OFFICE_SCHEDULE: SisterCredentialAvailabilitySchedule = {
  timezone: "Europe/Rome",
  weekly: {
    "0": [{ start: "15:00", end: "07:30" }],
    "1": [{ start: "15:00", end: "07:30" }],
    "2": [{ start: "15:00", end: "07:30" }],
    "3": [{ start: "15:00", end: "07:30" }],
    "4": [{ start: "15:00", end: "07:30" }],
    "5": [{ start: "00:00", end: "00:00" }],
    "6": [{ start: "00:00", end: "00:00" }],
  },
  exceptions: [{ ...FIRST_SATURDAY_EXCEPTION, windows: [{ ...FIRST_SATURDAY_WINDOW }] }],
};

function copyWindows(windows: SisterCredentialAvailabilityWindow[]): SisterCredentialAvailabilityWindow[] {
  return windows.map((window) => ({ ...window }));
}

function copySchedule(schedule: SisterCredentialAvailabilitySchedule): SisterCredentialAvailabilitySchedule {
  return {
    timezone: "Europe/Rome",
    weekly: Object.fromEntries(
      Object.entries(schedule.weekly).map(([day, windows]) => [day, copyWindows(windows)]),
    ),
    exceptions: (schedule.exceptions ?? []).map((item) => ({ ...item, windows: copyWindows(item.windows) })),
  };
}

export function defaultSisterSchedule(): SisterCredentialAvailabilitySchedule {
  return copySchedule(OUTSIDE_OFFICE_SCHEDULE);
}

function exceptionLabels(schedule: SisterCredentialAvailabilitySchedule): string[] {
  return (schedule.exceptions ?? []).flatMap((item) => {
    if (item.kind !== "nth_weekday_of_month" || item.windows.length === 0) {
      return [];
    }
    const day = SHORT_DAYS[item.weekday] ?? "Giorno";
    return [`${item.occurrence}° ${day} ${item.windows.map((window) => `${window.start}-${window.end}`).join(", ")}`];
  });
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
  const labels = [...days, ...exceptionLabels(schedule)];
  return labels.length > 0 ? labels.join(" · ") : "Nessuna fascia configurata";
}

function romeClock(date: Date): { weekday: number; minute: number; year: number; month: number; day: number } {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Europe/Rome",
    weekday: "short",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  const weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].indexOf(values.weekday);
  return {
    weekday,
    minute: Number(values.hour) * 60 + Number(values.minute),
    year: Number(values.year),
    month: Number(values.month),
    day: Number(values.day),
  };
}

function toMinutes(value: string): number {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

function previousCalendarDay(
  year: number,
  month: number,
  day: number,
  weekday: number,
): { day: number; weekday: number } {
  const previous = new Date(Date.UTC(year, month - 1, day - 1));
  return { day: previous.getUTCDate(), weekday: (weekday + 6) % 7 };
}

function windowsForDate(
  schedule: SisterCredentialAvailabilitySchedule,
  weekday: number,
  dayOfMonth: number,
): SisterCredentialAvailabilityWindow[] {
  const occurrence = Math.floor((dayOfMonth - 1) / 7) + 1;
  const match = (schedule.exceptions ?? []).find((item) => (
    item.kind === "nth_weekday_of_month"
    && item.weekday === weekday
    && item.occurrence === occurrence
  ));
  return match ? match.windows ?? [] : schedule.weekly[String(weekday)] ?? [];
}

function windowContainsMinute(window: SisterCredentialAvailabilityWindow, minute: number): boolean {
  const start = toMinutes(window.start);
  const end = toMinutes(window.end);
  return start === end || (start < end ? start <= minute && minute < end : minute >= start);
}

function overnightTailContains(window: SisterCredentialAvailabilityWindow, minute: number): boolean {
  return toMinutes(window.start) > toMinutes(window.end) && minute < toMinutes(window.end);
}

function windowsAreValid(windows: SisterCredentialAvailabilityWindow[]): boolean {
  return windows.some((window) => VALID_TIME.test(window.start) && VALID_TIME.test(window.end));
}

function scheduleHasValidWindow(schedule: SisterCredentialAvailabilitySchedule | null): boolean {
  if (!schedule) return false;
  const weeklyValid = Object.entries(schedule.weekly).some(([day, windows]) => (
    /^[0-6]$/.test(day) && windowsAreValid(windows)
  ));
  return weeklyValid || (schedule.exceptions ?? []).some((item) => (
    item.kind === "nth_weekday_of_month" && windowsAreValid(item.windows)
  ));
}

export function sisterCredentialIsAvailable(
  enabled: boolean,
  schedule: SisterCredentialAvailabilitySchedule | null,
  at = new Date(),
): boolean {
  if (!enabled) return true;
  if (!schedule) return false;
  const clock = romeClock(at);
  if (windowsForDate(schedule, clock.weekday, clock.day).some((window) => windowContainsMinute(window, clock.minute))) {
    return true;
  }
  const previous = previousCalendarDay(clock.year, clock.month, clock.day, clock.weekday);
  return windowsForDate(schedule, previous.weekday, previous.day).some((window) => overnightTailContains(window, clock.minute));
}

export function nextSisterAvailability(
  enabled: boolean,
  schedule: SisterCredentialAvailabilitySchedule | null,
  at = new Date(),
): Date | null {
  if (sisterCredentialIsAvailable(enabled, schedule, at)) return at;
  if (!scheduleHasValidWindow(schedule)) return null;
  const candidate = new Date(at);
  candidate.setSeconds(0, 0);
  while (true) {
    candidate.setTime(candidate.getTime() + 60_000);
    if (sisterCredentialIsAvailable(enabled, schedule, candidate)) return new Date(candidate);
  }
}

function firstSaturdayException(
  schedule: SisterCredentialAvailabilitySchedule,
): SisterCredentialNthWeekdayException | null {
  return (schedule.exceptions ?? []).find((item) => (
    item.kind === "nth_weekday_of_month" && item.weekday === 5 && item.occurrence === 1
  )) ?? null;
}

function withFirstSaturday(
  schedule: SisterCredentialAvailabilitySchedule,
  exception: SisterCredentialNthWeekdayException | null,
): SisterCredentialAvailabilitySchedule {
  const others = (schedule.exceptions ?? []).filter((item) => (
    !(item.kind === "nth_weekday_of_month" && item.weekday === 5 && item.occurrence === 1)
  ));
  return {
    timezone: "Europe/Rome",
    weekly: schedule.weekly,
    exceptions: exception ? [...others, exception] : others,
  };
}

type SisterAvailabilityScheduleEditorProps = {
  enabled: boolean;
  schedule: SisterCredentialAvailabilitySchedule;
  onEnabledChange: (enabled: boolean) => void;
  onScheduleChange: (schedule: SisterCredentialAvailabilitySchedule) => void;
};

function FirstSaturdayExceptionEditor(props: {
  schedule: SisterCredentialAvailabilitySchedule;
  onScheduleChange: (schedule: SisterCredentialAvailabilitySchedule) => void;
}) {
  const exception = firstSaturdayException(props.schedule);
  const window = exception?.windows[0] ?? FIRST_SATURDAY_WINDOW;

  function toggle(enabled: boolean): void {
    props.onScheduleChange(withFirstSaturday(
      props.schedule,
      enabled ? { ...FIRST_SATURDAY_EXCEPTION, windows: [{ ...FIRST_SATURDAY_WINDOW }] } : null,
    ));
  }

  function updateField(field: "start" | "end", value: string): void {
    props.onScheduleChange(withFirstSaturday(props.schedule, {
      ...FIRST_SATURDAY_EXCEPTION,
      windows: [{ ...window, [field]: value }],
    }));
  }

  return <div className="rounded-xl bg-white px-3 py-3">
    <label className="flex items-start gap-2 text-sm font-semibold text-gray-800">
      <input
        aria-label="Primo sabato del mese diverso"
        checked={exception != null}
        className="mt-1 h-4 w-4 accent-[#1D4E35]"
        onChange={(event) => toggle(event.target.checked)}
        type="checkbox"
      />
      <span>
        Primo sabato del mese
        <span className="mt-1 block text-xs font-normal leading-5 text-gray-600">
          Sostituisce le fasce del sabato. La coda notturna del venerdi resta valida fino alle 07:30.
        </span>
      </span>
    </label>
    {exception != null ? <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-600">
      <span>Dalle</span>
      <input aria-label="Primo sabato dalle" className="form-control max-w-28 py-1.5" onChange={(event) => updateField("start", event.target.value)} type="time" value={window.start} />
      <span>in poi, fino alle</span>
      <input aria-label="Primo sabato alle" className="form-control max-w-28 py-1.5" onChange={(event) => updateField("end", event.target.value)} type="time" value={window.end} />
    </div> : null}
  </div>;
}

export function SisterAvailabilityScheduleEditor(props: SisterAvailabilityScheduleEditorProps) {
  function commit(weekly: SisterCredentialAvailabilitySchedule["weekly"]): void {
    props.onScheduleChange({
      timezone: "Europe/Rome",
      weekly,
      exceptions: props.schedule.exceptions ?? [],
    });
  }

  function replaceDay(day: number, windows: SisterCredentialAvailabilitySchedule["weekly"][string]): void {
    commit({ ...props.schedule.weekly, [String(day)]: windows });
  }

  function toggleDay(day: number, enabled: boolean): void {
    replaceDay(day, enabled ? [{ ...DEFAULT_WINDOW }] : []);
  }

  function updateWindow(day: number, index: number, field: "start" | "end", value: string): void {
    replaceDay(day, props.schedule.weekly[String(day)].map((window, currentIndex) => (
      currentIndex === index ? { ...window, [field]: value } : window
    )));
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
      <FirstSaturdayExceptionEditor onScheduleChange={props.onScheduleChange} schedule={props.schedule} />
      <p className="pt-1 text-xs text-gray-500">Puoi impostare fino a quattro fasce per giorno. Se l&apos;ora finale e precedente a quella iniziale, la fascia continua durante la notte successiva. Il primo sabato del mese, se attivo, sostituisce le fasce del sabato.</p>
    </div> : null}
  </section>;
}
