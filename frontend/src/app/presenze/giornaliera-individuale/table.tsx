import { MONTHLY_ROWS, buildMonthlySheet, monthlyCell } from "@/lib/presenze-monthly-sheet";

type Props = { report: ReturnType<typeof buildMonthlySheet>; name: string; code: string };
export function MonthlySheetTable({ report, name, code }: Props) {
  return <div className="space-y-4">
    <h2 className="text-xl font-semibold">{name} · Matricola {code} · {report.month}</h2>
    <p>Ore in h:mm · Giorni lavorati: {report.workedDays} · Giorni contributivi calcolati: {report.paidDays} · Giorni senza dati: {report.missingDays}. I totali si riferiscono ai dati disponibili.</p>
    <div className="overflow-x-auto print:overflow-visible">
      <table className="w-full border-collapse whitespace-nowrap text-right text-xs tabular-nums print:text-[7px]">
        <caption className="sr-only">Giornaliera mensile individuale</caption>
        <thead><tr><th scope="col" className="sticky left-0 border bg-slate-100 p-2 text-left">Voce</th>
          {report.days.map(day => <th scope="col" key={day.date} className={`border p-2 ${day.weekend ? "bg-slate-200" : "bg-slate-50"}`}>{day.date.slice(8)}<br />{new Date(day.date + "T12:00:00Z").toLocaleDateString("it-IT", { weekday: "short", timeZone: "UTC" })}</th>)}
          <th scope="col" className="border bg-slate-100 p-2">Totale</th></tr></thead>
        <tbody>{MONTHLY_ROWS.map((label, index) => <tr key={label}>
          <th scope="row" className="sticky left-0 border bg-slate-100 p-2 text-left">{label}</th>
          {report.days.map(day => <td key={day.date} title={day.date + (day.present ? "" : " · Dati non disponibili")} className={`border p-2 print:p-1 ${day.weekend ? "bg-slate-200" : ""}`}>{monthlyCell(day.values[index], index)}</td>)}
          <td className="border bg-slate-100 p-2 font-semibold">{monthlyCell(report.totals[index], index)}</td>
        </tr>)}</tbody>
      </table>
    </div>
    <p className="text-sm text-slate-600">Non disponibili: KM moto, indennità macchine, centro di costo, lavorazione, saldo banca ore. Reperibilità: numero giornate; M: trasferta montana; RS: riposo settimanale. —: dato non disponibile.</p>
  </div>;
}
