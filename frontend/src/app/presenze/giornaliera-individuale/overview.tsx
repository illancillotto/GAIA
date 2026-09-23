import { buildMonthlySheet, monthlyCell } from "@/lib/presenze-monthly-sheet";
import { monthlyDayStatus, monthlyDisplayCell } from "@/lib/presenze-monthly-presentation";

type Props = { report: ReturnType<typeof buildMonthlySheet>; today: string };
export function MonthlyOverview({ report, today }: Props) {
  const attention = report.days.filter(day => ["warning", "danger"].includes(monthlyDayStatus(day, today).tone)).length;
  const stats = [
    ["Ore nel prospetto", monthlyCell(report.totals[8], 8), "Ore e minuti: 7:30 significa 7 ore e 30 minuti."],
    ["Giorni con ore", String(report.workedDays), "Giorni con almeno un minuto di lavoro nel prospetto."],
    ["Giorni di assenza", String(report.totals[12]), "Giorni con causale di assenza e senza ore. Il riposo non è contato."],
    ["Da controllare", String(attention), "Giorni trascorsi senza dati, ore non disponibili o assenza da giustificare. Oggi senza dati non è un errore."],
  ];
  const legend = [["work", "Ore registrate"], ["absence", "Assenza indicata"], ["neutral", "Riposo / nessuna ora"], ["warning", "Dati da controllare"], ["danger", "Da giustificare"], ["future", "Da venire"]];
  return <div className="monthly-overview">
    <p className="monthly-explanation">Situazione del mese in base ai dati disponibili, non presenza in tempo reale. Tocca un giorno per leggere il dettaglio. I giorni futuri sono indicati come ‘Da venire’.</p>
    <div className="monthly-stats">{stats.map(([label, value, hint]) => <details key={label} className="monthly-stat" title={hint}><summary><span>{label}</span><strong>{value}</strong></summary><p>{hint}</p></details>)}</div>
    <p className="monthly-legend">{legend.map(([tone, label]) => <span key={tone} className={`monthly-tone-${tone}`}>{label}</span>)}</p>
    <div className="monthly-days">{report.days.map(day => {
      const status = monthlyDayStatus(day, today);
      return <details key={day.date} className={`monthly-day monthly-tone-${status.tone}`}>
        <summary><strong>{day.date.slice(8)} {new Date(day.date + "T12:00:00Z").toLocaleDateString("it-IT", { weekday: "short", timeZone: "UTC" })}</strong><span>{status.label}</span><span className="monthly-day-hours">Ore: {monthlyCell(day.values[8], 8)}</span></summary>
        <p>{day.date} · Ore: {monthlyCell(day.values[8], 8)} · Causale: {monthlyDisplayCell(day.values[12], 12)}. — significa dato non disponibile. I dati futuri non attestano una presenza.</p>
      </details>;
    })}</div>
  </div>;
}
