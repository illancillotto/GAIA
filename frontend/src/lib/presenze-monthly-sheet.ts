// Giornaliera2 presentation contract. Keep the GAIA/GaTe copies and fixtures aligned.
export type MonthlyRecord = Record<string, unknown>;
export const MONTHLY_ROWS = [
  "Ordinario feriale", "Ordinario festivo", "Ordinario notturno", "Ordinario festivo notturno",
  "Straordinario feriale", "Straordinario festivo", "Straordinario notturno", "Straordinario festivo notturno",
  "Totale ore", "KM auto", "Trasferta", "Reperibilità", "Causale assenza",
] as const;
export type MonthlyDay = {
  date: string; weekend: boolean; present: boolean; values: Array<number | string | null>;
};
export function monthlyNumber(record: MonthlyRecord, ...keys: string[]): number | null {
  for (const key of keys) {
    const value = record[key];
    if (value === undefined) continue;
    if (value === null || value === "") return null;
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed < 0) throw new Error("Valore non valido: " + key);
    return parsed;
  }
  return null;
}
export function monthlyDuration(minutes: number): string {
  return Math.floor(minutes / 60) + ":" + String(Math.round(minutes % 60)).padStart(2, "0");
}
export function monthlyCalendar(month: string): MonthlyDay[] {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(month)) throw new Error("Mese non valido");
  const [year, number] = month.split("-").map(Number);
  const count = new Date(Date.UTC(year!, number!, 0)).getUTCDate();
  return Array.from({ length: count }, (_, i) => ({
    date: month + "-" + String(i + 1).padStart(2, "0"),
    weekend: [0, 6].includes(new Date(Date.UTC(year!, number! - 1, i + 1)).getUTCDay()),
    present: false, values: Array(13).fill(null),
  }));
}
export function monthlyAbsence(record: MonthlyRecord): string | null {
  if (record.export_absence_code) return String(record.export_absence_code);
  const prefixes: Record<string, string> = {
    "ASS.SIN": "PS", ASSG: "AG", DON: "DS", EXFEST: "RC", EXFEST_HH: "RC", EXFESTCOLL: "RC",
    FERIE: "F", FERIECOLL: "F", INF: "I", MA7: "L.104", MA7HH: "L.104", MAL: "M", MALNOI: "M",
    MALOSP: "M", MB5G3: "L.104", "P. ORD": "P", "P. STR": "PST", "P.ORD": "P", PSERV: "PS", PSIEST: "PS", PSIRSA: "PS", SOSPD: "SD",
  };
  const causes: Record<string, string> = { ferie: "F", malattia: "M", permesso: "P", riposo: "RS", assenza_da_giustificare: "AG" };
  const prefix = String(record.request_description ?? "").split(" - ")[0]!.trim().toUpperCase();
  return prefixes[prefix] ?? causes[String(record.absence_cause ?? record.resolved_absence_cause ?? "")] ?? null;
}
export function monthlyNightReclassification(record: MonthlyRecord, night: number): number {
  if (record.contract_kind !== "operaio") return 0;
  if (night < 5) return night;
  if (!["OPE0613", "OPE0714"].includes(String(record.schedule_code))) return 0;
  const punches = record.detail_punch_rows as Array<{ entry_time?: string; exit_time?: string }> | undefined;
  if (!punches?.length) return 0;
  const times = monthlyPunchIntervals(punches);
  if (!times) return 0;
  const first = Math.min(...times.map(t => t[0]!));
  const last = Math.max(...times.map(t => t[1]!));
  if (record.schedule_code === "OPE0714" && last < 780) return 0;
  const early = 360 - first;
  return early > 0 && early < 30 && night === early ? early : 0;
}
export function monthlyBuckets(record: MonthlyRecord): Array<number | null> {
  const ordinary = monthlyNumber(record, "export_ordinary_minutes", "ordinary_minutes");
  const extra = monthlyNumber(record, "export_extra_minutes", "effective_extra_minutes");
  const names = ["ordinary_night_minutes", "shift_festive_day_minutes", "shift_festive_night_minutes", "overtime_day_minutes", "overtime_festive_minutes", "overtime_night_minutes", "overtime_festive_night_minutes"];
  const [night, festive, festiveNight, ...overtime] = names.map(key => monthlyNumber(record, "export_" + key, key) ?? 0);
  const special = record.export_special_day ?? record.special_day;
  if (![night, festive, festiveNight, ...overtime].some(Boolean)) {
    return special ? [0, ordinary, 0, 0, 0, extra, 0, 0] : [ordinary, 0, 0, 0, extra, 0, 0, 0];
  }
  const ferial = (ordinary ?? 0) - night! - festive! - festiveNight!;
  if (ferial < 0 || overtime.reduce((a, b) => a + b, 0) !== (extra ?? 0)) {
    throw new Error("Ripartizione ore incoerente: " + String(record.work_date));
  }
  const early = monthlyNightReclassification(record, night!);
  return [ferial + early, festive!, night! - early, festiveNight!, ...overtime];
}
export function monthlyValues(record: MonthlyRecord): Array<number | string | null> {
  const buckets = monthlyBuckets(record);
  const ordinary = monthlyNumber(record, "export_ordinary_minutes", "ordinary_minutes");
  const extra = monthlyNumber(record, "export_extra_minutes", "effective_extra_minutes");
  const total = ordinary === null && extra === null ? null : buckets.reduce<number>((sum, value) => sum + (value ?? 0), 0);
  const quantity = monthlyNumber(record, "reperibilita_quantity") ?? 0;
  const available = record.reperibilita_giornaliera === true || (record.reperibilita_unit !== "none" && quantity > 0);
  const rest = record.contract_kind === "operaio" && ["DOM", "SAB", "RIPTURN"].includes(String(record.schedule_code)) && total === 0;
  return [...buckets, total, monthlyNumber(record, "km_value"), record.trasferta_montano ? "M" : monthlyNumber(record, "trasferta_minutes"), available ? 1 : 0, monthlyAbsence(record) ?? (rest ? "RS" : null)];
}
export function buildMonthlySheet(month: string, records: MonthlyRecord[]) {
  const days = monthlyCalendar(month);
  for (const record of records) {
    const day = days.find(item => item.date === record.work_date);
    if (!day || day.present) throw new Error("Data fuori mese o duplicata: " + String(record.work_date));
    day.present = true;
    day.values = monthlyValues(record);
  }
  const totals = MONTHLY_ROWS.map((_, index) => {
    const values = days.filter(day => day.present).map(day => day.values[index]);
    if (index === 12) return days.filter(day => day.values[12] && day.values[12] !== "RS" && Number(day.values[8]) === 0).length;
    if (!values.some(value => typeof value === "number")) return null;
    return values.reduce<number>((sum, value) => sum + (typeof value === "number" ? value : 0), 0);
  });
  return { month, days, totals, ...monthlyCounts(days, records), missingDays: days.filter(day => !day.present).length };
}
export function monthlyCell(value: number | string | null, row: number): string {
  if (value === null) return "—";
  if (typeof value === "string") return value;
  return row < 9 || row === 10 ? monthlyDuration(value) : String(value);
}

export function monthlyCounts(days: MonthlyDay[], records: MonthlyRecord[]) {
  const workedDays = days.filter(day => Number(day.values[8]) > 0).length;
  const justifiedDays = records.filter(record => Number(record.justified_minutes) > 0 && !Number(monthlyValues(record)[8])).length;
  const paidRestDays = days.filter(day => monthlyPaidSaturday(day, records)).length;
  return { workedDays, paidDays: workedDays + justifiedDays + paidRestDays };
}
export function monthlyPaidSaturday(day: MonthlyDay, records: MonthlyRecord[]): boolean {
  const date = new Date(day.date + "T12:00:00Z");
  if (!day.present || date.getUTCDay() !== 6 || Number(day.values[8]) > 0) return false;
  const person = records.find(record => record.work_date === day.date)!;
  if (person.contract_kind !== "operaio") return false;
  const week = Array.from({ length: 5 }, (_, index) => {
    const previous = new Date(date.getTime() - (5 - index) * 86400000).toISOString().slice(0, 10);
    const record = records.find(item => item.work_date === previous);
    return record ? monthlyNumber(record, "export_ordinary_minutes", "ordinary_minutes") ?? 0 : 0;
  });
  return week.every(minutes => minutes > 0) && week.reduce((a, b) => a + b, 0) >= 2280;
}

export function monthlyPunchIntervals(punches: Array<{ entry_time?: string; exit_time?: string }>): number[][] | null {
  const times = punches.map(p => [p.entry_time, p.exit_time].map(t => {
    if (!t || !/^\d{2}:\d{2}/.test(t)) return NaN;
    return Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5));
  }));
  if (times.some(([start, end]) => !Number.isFinite(start) || !Number.isFinite(end) || end! <= start! || end! > 1320)) return null;
  return times;
}
