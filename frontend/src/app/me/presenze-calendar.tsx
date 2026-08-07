"use client";

import { Badge } from "@/components/ui/badge";
import type { PresenzeDailyRecord } from "@/types/api";

type PresenzeCalendarDay = {
  date: string;
  dayNumber: string;
  isCurrentMonth: boolean;
  isToday: boolean;
  isWeekend: boolean;
  record: PresenzeDailyRecord | null;
};

export type PresenzeMonthlyCalendarProps = {
  monthStart: string;
  records: PresenzeDailyRecord[];
  onOpenDailyRecord: (recordId: string) => void;
  today?: string;
};

export const CALENDAR_WEEKDAY_LABELS = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"];

export function formatIsoDate(value: Date): string {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function parseIsoDate(value: string): Date {
  return new Date(`${value}T00:00:00`);
}

function addDays(value: Date, days: number): Date {
  const next = new Date(value);
  next.setDate(next.getDate() + days);
  return next;
}

function isoToday(): string {
  return formatIsoDate(new Date());
}

function formatHours(minutes: number): string {
  return `${(minutes / 60).toFixed(1)} h`;
}

function formatDateLabel(value: string): string {
  return new Intl.DateTimeFormat("it-IT", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(parseIsoDate(value));
}

function requestBadgeLabel(record: PresenzeDailyRecord): string | null {
  if (record.resolved_absence_cause) return record.resolved_absence_cause.replaceAll("_", " ");
  if (record.request_description) return record.request_description;
  return null;
}

function hasWorkedTime(record: PresenzeDailyRecord): boolean {
  if ((record.operational_worked_minutes ?? 0) > 0) return true;
  if ((record.ordinary_minutes ?? 0) > 0) return true;
  if ((record.effective_extra_minutes ?? 0) > 0) return true;
  return record.punches.some((punch) => Boolean(punch.entry_time || punch.exit_time));
}

function isWeekendRecord(record: PresenzeDailyRecord): boolean {
  const day = parseIsoDate(record.work_date).getDay();
  return day === 0 || day === 6;
}

export function detailTone(record: PresenzeDailyRecord): "warning" | "success" | "info" | "neutral" {
  if (isWeekendRecord(record) && !hasWorkedTime(record)) return "info";
  if ((record.detail_anomalies?.length ?? 0) > 0 || record.special_day) return "warning";
  if ((record.effective_extra_minutes ?? 0) > 0) return "success";
  return "neutral";
}

export function calendarCellClass(record: PresenzeDailyRecord | null, isCurrentMonth: boolean, isToday: boolean): string {
  const base = "min-h-[132px] rounded-2xl border p-3 text-left transition";
  const todayRing = isToday ? " ring-2 ring-[#1D4E35]/25" : "";

  if (!record) {
    return `${base} ${isCurrentMonth ? "border-dashed border-gray-200 bg-gray-50/70" : "border-transparent bg-transparent"}${todayRing}`;
  }

  const interactive = "hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-[#1D4E35]/30";
  const tone = detailTone(record);
  if (tone === "warning") return `${base} ${interactive} border-amber-200 bg-amber-50/80${todayRing}`;
  if (tone === "success") return `${base} ${interactive} border-emerald-200 bg-emerald-50/80${todayRing}`;
  if (tone === "info") return `${base} ${interactive} border-blue-100 bg-blue-50/70${todayRing}`;
  return `${base} ${interactive} border-gray-100 bg-white shadow-sm${todayRing}`;
}

export function buildPresenzeMonthCalendar(monthStartIso: string, records: PresenzeDailyRecord[], today = isoToday()): PresenzeCalendarDay[] {
  const monthStart = parseIsoDate(monthStartIso);
  const monthEnd = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0);
  const recordsByDate = new Map(records.map((record) => [record.work_date, record]));
  const firstGridDate = addDays(monthStart, -((monthStart.getDay() + 6) % 7));
  const lastGridDate = addDays(monthEnd, 6 - ((monthEnd.getDay() + 6) % 7));
  const days: PresenzeCalendarDay[] = [];

  for (let date = firstGridDate; date <= lastGridDate; date = addDays(date, 1)) {
    const isoDate = formatIsoDate(date);
    days.push({
      date: isoDate,
      dayNumber: String(date.getDate()),
      isCurrentMonth: date.getMonth() === monthStart.getMonth(),
      isToday: isoDate === today,
      isWeekend: date.getDay() === 0 || date.getDay() === 6,
      record: recordsByDate.get(isoDate) ?? null,
    });
  }

  return days;
}

export function PresenzeMonthlyCalendar({ monthStart, records, onOpenDailyRecord, today }: PresenzeMonthlyCalendarProps) {
  const calendarDays = buildPresenzeMonthCalendar(monthStart, records, today);

  return (
    <div className="overflow-x-auto pb-1">
      <div className="min-w-[760px]">
        <div className="mb-2 grid grid-cols-7 gap-2">
          {CALENDAR_WEEKDAY_LABELS.map((weekday) => (
            <div key={weekday} className="px-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">
              {weekday}
            </div>
          ))}
        </div>
        <div className="grid grid-cols-7 gap-2">
          {calendarDays.map((day) => {
            const record = day.record;
            if (!record) {
              return (
                <div key={day.date} className={calendarCellClass(null, day.isCurrentMonth, day.isToday)}>
                  <div className="flex items-center justify-between">
                    <span className={day.isCurrentMonth ? "text-sm font-semibold text-gray-400" : "text-sm text-gray-300"}>{day.dayNumber}</span>
                    {day.isWeekend && day.isCurrentMonth ? <span className="text-[10px] font-medium text-gray-300">riposo</span> : null}
                  </div>
                </div>
              );
            }

            const status = record.detail_status || record.stato || "Regolare";
            const requestLabel = requestBadgeLabel(record);
            const anomalyCount = record.detail_anomalies?.length ?? 0;

            return (
              <button
                key={day.date}
                aria-label={`Apri dettaglio presenze ${formatDateLabel(record.work_date)}`}
                className={calendarCellClass(record, day.isCurrentMonth, day.isToday)}
                type="button"
                onClick={() => onOpenDailyRecord(record.id)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className={`text-base font-semibold ${day.isCurrentMonth ? "text-gray-900" : "text-gray-400"}`}>{day.dayNumber}</p>
                    <p className="mt-0.5 text-[11px] font-medium text-gray-500">{record.detail_programmed_schedule || record.schedule_code || "Orario n/d"}</p>
                  </div>
                  <Badge variant={detailTone(record)}>{status}</Badge>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-1.5 text-[11px] text-gray-600">
                  <span className="rounded-lg bg-white/75 px-2 py-1">Ord {formatHours(record.ordinary_minutes ?? 0)}</span>
                  <span className="rounded-lg bg-white/75 px-2 py-1">Extra {formatHours(record.effective_extra_minutes ?? 0)}</span>
                  <span className="rounded-lg bg-white/75 px-2 py-1">Ass {formatHours(record.absence_minutes ?? 0)}</span>
                  <span className="rounded-lg bg-white/75 px-2 py-1">KM {record.km_value ?? 0}</span>
                </div>
                {record.punches.length > 0 ? (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {record.punches.slice(0, 2).map((punch) => (
                      <span key={punch.id} className="rounded-full bg-white/80 px-2 py-0.5 text-[10px] text-gray-600">
                        {punch.entry_time || "--:--"}-{punch.exit_time || "--:--"}
                      </span>
                    ))}
                    {record.punches.length > 2 ? <span className="rounded-full bg-white/80 px-2 py-0.5 text-[10px] text-gray-500">+{record.punches.length - 2}</span> : null}
                  </div>
                ) : null}
                {requestLabel || anomalyCount > 0 ? (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {requestLabel ? <span className="rounded-full bg-white/80 px-2 py-0.5 text-[10px] text-gray-600">{requestLabel}</span> : null}
                    {anomalyCount > 0 ? <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800">{anomalyCount} anomalie</span> : null}
                  </div>
                ) : null}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
