"use client";

import { useState } from "react";
import { ProtectedPage } from "@/components/app/protected-page";
import { useMonthlyPeople, useMonthlyReport } from "./use-monthly-sheet";
import { MonthlySheetTable } from "./table";

export default function MonthlySheetPage() {
  const [personId, setPersonId] = useState("");
  const [month, setMonth] = useState(() => new Date().toLocaleDateString("sv-SE").slice(0, 7));
  const [reload, setReload] = useState(0);
  const { people, error: directoryError } = useMonthlyPeople(setPersonId);
  const person = people.find(item => item.id === personId);
  const { report, error: reportError, loading } = useMonthlyReport(month, person, reload);
  const error = directoryError || reportError;

  return <ProtectedPage title="Giornaliera individuale" description="Scegli il dipendente e il mese. Controlla ore, assenze e giorni da verificare." breadcrumb="Giornaliera individuale" requiredModule="presenze">
    <section className="space-y-4 rounded-xl border bg-white p-5 text-slate-900">
      <div className="flex flex-wrap items-end gap-4 print:hidden">
        <label>Mese<input aria-label="Mese" type="month" className="block rounded border p-2" value={month} onChange={event => setMonth(event.target.value)} /></label>
        <label>Dipendente<select aria-label="Dipendente" className="block max-w-full rounded border p-2" value={personId} onChange={event => setPersonId(event.target.value)}>
          {people.map(item => <option key={item.id} value={item.id}>{item.name} · {item.employee_code}</option>)}
        </select></label>
        <button type="button" className="rounded border px-4 py-2" onClick={() => setReload(value => value + 1)}>Aggiorna</button>
        <button type="button" className="rounded border px-4 py-2 disabled:cursor-not-allowed disabled:opacity-50" disabled={!report} onClick={() => window.print()}>Stampa / PDF</button>
      </div>
      {loading && <p role="status">Caricamento…</p>}
      {error && <p role="alert">{error}</p>}
      {report && person && <MonthlySheetTable report={report} name={person.name} code={person.employee_code} />}
      {!loading && !error && people.length === 0 && <p>Nessun dipendente disponibile.</p>}
    </section>
  </ProtectedPage>;
}
