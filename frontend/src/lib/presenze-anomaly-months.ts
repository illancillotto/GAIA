import type { PresenzeDailyRecord } from "@/types/api";

export function currentMonthValue(reference = new Date()): string {
  return `${reference.getFullYear()}-${String(reference.getMonth() + 1).padStart(2, "0")}`;
}

export function previousMonthValue(monthValue: string): string {
  const [yearString, monthString] = monthValue.split("-");
  const year = Number(yearString);
  const month = Number(monthString);
  const date = new Date(year, month - 2, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

export function monthBounds(monthValue: string): { start: string; end: string } {
  const [yearString, monthString] = monthValue.split("-");
  const year = Number(yearString);
  const month = Number(monthString);
  const start = `${yearString}-${monthString}-01`;
  const end = `${yearString}-${monthString}-${String(new Date(year, month, 0).getDate()).padStart(2, "0")}`;
  return { start, end };
}

export function monthLabel(monthValue: string, locale = "it-IT"): string {
  const [yearString, monthString] = monthValue.split("-");
  const date = new Date(Number(yearString), Number(monthString) - 1, 1);
  return date.toLocaleDateString(locale, { month: "long", year: "numeric" });
}

export function recentMonths(count: number, anchor = currentMonthValue()): string[] {
  const months: string[] = [];
  let current = anchor;
  for (let index = 0; index < count; index += 1) {
    months.push(current);
    current = previousMonthValue(current);
  }
  return months;
}

export function recordHasAnomaly(record: Pick<PresenzeDailyRecord, "detail_anomalies" | "detail_error">): boolean {
  return record.detail_anomalies.length > 0 || Boolean(record.detail_error);
}

export function countAnomaliesInRecords(records: PresenzeDailyRecord[]): number {
  return records.filter(recordHasAnomaly).length;
}

export type MonthAnomalySummary = { month: string; count: number };

export function summarizeMonthsWithAnomalies(entries: MonthAnomalySummary[]): MonthAnomalySummary[] {
  return entries.filter((entry) => entry.count > 0).sort((left, right) => right.month.localeCompare(left.month));
}

export function shouldAutoLoadPreviousMonth(params: {
  selectedMonth: string;
  calendarMonth: string;
  anomalyCount: number;
  alreadyApplied: boolean;
}): boolean {
  return !params.alreadyApplied && params.selectedMonth === params.calendarMonth && params.anomalyCount === 0;
}
