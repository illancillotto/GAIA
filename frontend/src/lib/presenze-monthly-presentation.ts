import type { MonthlyDay } from "./presenze-monthly-sheet";

// Same presentation contract in GAIA. These labels describe records, never live presence.
export function monthlyAbsenceLabel(code: string): string {
  const labels: Record<string, string> = {
    F: "Ferie", M: "Malattia", I: "Infortunio", P: "Permesso", PST: "Permesso straordinario",
    PS: "Permesso di servizio / sindacale", AG: "Assenza da giustificare", RS: "Riposo",
    "L.104": "Permesso legge 104", DS: "Donazione sangue", RC: "Recupero / ex festività", SD: "Sospensione",
  };
  return labels[code] ?? "Causale " + code;
}
export function monthlyDayStatus(day: MonthlyDay, today: string) {
  const code = String(day.values[12] ?? "");
  if (day.date > today) return { tone: "future", label: code ? "Previsto: " + monthlyAbsenceLabel(code) : "Da venire" };
  if (!day.present) return day.date === today
    ? { tone: "neutral", label: "In attesa di dati" }
    : { tone: "warning", label: "Dati mancanti" };
  const worked = Number(day.values[8]) > 0;
  if (code === "AG") return { tone: "danger", label: "Da giustificare" };
  if (code) return { tone: code === "RS" ? "neutral" : "absence", label: (worked ? "Ore + " : "") + monthlyAbsenceLabel(code) };
  if (worked) return { tone: "work", label: "Ore registrate" };
  return day.values[8] === null
    ? { tone: "warning", label: "Ore non disponibili" }
    : { tone: "neutral", label: "Nessuna ora registrata" };
}
export function monthlyCellTone(day: MonthlyDay, row: number, today: string): string {
  const value = day.values[row];
  if (day.date > today) return "future";
  if (!day.present) return "missing";
  if (row === 12 && value) return monthlyDayStatus(day, today).tone;
  if (typeof value === "number" && value > 0) return row >= 4 && row < 8 ? "extra" : "work";
  return day.weekend ? "weekend" : "quiet";
}
export function monthlyDisplayCell(value: number | string | null, row: number): string {
  if (row === 12 && typeof value === "string") return monthlyAbsenceLabel(value);
  if (row === 10 && value === "M") return "Montana";
  if (value === null) return "—";
  if (typeof value === "string") return value;
  return row < 9 || row === 10
    ? Math.floor(value / 60) + ":" + String(Math.round(value % 60)).padStart(2, "0")
    : String(value);
}
