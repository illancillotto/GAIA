import type { PresenzeDailyRecord } from "@/types/api";

type DailyCellIndicator = { label: string; className?: string };

export function dailyCellIndicators(record: PresenzeDailyRecord, extra: number, authorizedLabel: string | null): DailyCellIndicator[] {
  const indicators = [
    { present: extra > 0, label: "▲", className: "text-emerald-600" },
    { present: record.km_value != null, label: "🚗" },
    { present: (record.trasferta_minutes ?? 0) > 0 || record.trasferta_montano, label: "T", className: "text-sky-600" },
    { present: record.reperibilita_unit !== "none", label: "R", className: "text-amber-700" },
  ].filter((indicator) => indicator.present);
  if (authorizedLabel) {
    indicators.push({ present: true, label: "✅", className: "text-emerald-700" });
  } else if (record.detail_requests.length > 0) {
    indicators.push({ present: true, label: "✉", className: "text-sky-600" });
  }
  return indicators;
}

export function kmInputPresentation(value: number | null, draft: string | undefined, canEdit: boolean, saving: boolean): { defaultValue: string; disabled: boolean } {
  return {
    defaultValue: draft ?? (value != null ? String(value) : ""),
    disabled: !canEdit || saving,
  };
}
