import "./monthly-sheet.css";
import { MonthlyOverview } from "./overview";
import { monthlyDayStatus, monthlyCellTone, monthlyDisplayCell } from "@/lib/presenze-monthly-presentation";
import { MONTHLY_ROWS, buildMonthlySheet, monthlyCell } from "@/lib/presenze-monthly-sheet";

type Props = { report: ReturnType<typeof buildMonthlySheet>; name: string; code: string };
export function MonthlySheetTable({ report, name, code }: Props) {
  const today = new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Rome" });
  return <div className="space-y-4">
    <h2 className="text-xl font-semibold">{name} · Matricola {code} · {new Date(report.month + "-01T12:00:00Z").toLocaleDateString("it-IT", { month: "long", year: "numeric", timeZone: "UTC" })}</h2>
    <MonthlyOverview report={report} today={today} />
    <div className="overflow-x-auto print:overflow-visible" role="region" tabIndex={0} aria-label="Dettaglio mensile, scorrere per vedere tutti i giorni">
      <table className="monthly-sheet-table w-full border-collapse whitespace-nowrap text-right text-xs tabular-nums print:text-[7px]">
        <caption>Dettaglio ore e indennità · scorri per vedere tutti i giorni →</caption>
        <thead><tr><th scope="col" className="sticky left-0 border bg-slate-100 p-2 text-left">Voce</th>
          {report.days.map(day => <th scope="col" key={day.date} className={`border p-2 ${day.weekend ? "bg-slate-200" : "bg-slate-50"}`}>{day.date.slice(8)}<br />{new Date(day.date + "T12:00:00Z").toLocaleDateString("it-IT", { weekday: "short", timeZone: "UTC" })}</th>)}
          <th scope="col" className="border bg-slate-100 p-2">Totale</th></tr></thead>
        <tbody>{MONTHLY_ROWS.map((label, index) => <tr key={label} className={index === 8 ? "monthly-total-row" : ""}>
          <th scope="row" className="sticky left-0 border bg-slate-100 p-2 text-left">{label}</th>
          {report.days.map(day => <td key={day.date} title={day.date + " · " + label + ": " + monthlyDisplayCell(day.values[index], index) + " · " + monthlyDayStatus(day, today).label} className={`border p-2 print:p-1 monthly-tone-${monthlyCellTone(day, index, today)}`}>{monthlyDisplayCell(day.values[index], index)}</td>)}
          <td className="border bg-slate-100 p-2 font-semibold">{monthlyCell(report.totals[index], index)}</td>
        </tr>)}</tbody>
      </table>
    </div>
    <p className="text-sm text-slate-600">Giorni contributivi calcolati: {report.paidDays}. I totali si riferiscono ai dati disponibili. Non disponibili: KM moto, indennità macchine, centro di costo, lavorazione, saldo banca ore. Reperibilità: numero giornate; M: trasferta montana; RS: riposo settimanale. —: dato non disponibile.</p>
  </div>;
}
