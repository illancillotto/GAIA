"use client";

import { MonthlySheetControls } from "./controls";
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
  const refresh = () => setReload(value => value + 1);

  return <ProtectedPage title="Giornaliera individuale" description="Scegli il dipendente e il mese. Controlla ore, assenze e giorni da verificare." breadcrumb="Giornaliera individuale" requiredModule="presenze">
    <section className="space-y-4 rounded-xl border bg-white p-5 text-slate-900">
      <MonthlySheetControls month={month} setMonth={setMonth} people={people} personId={personId} setPersonId={setPersonId} person={person} refresh={refresh} hasReport={Boolean(report)} />
      {loading && <p role="status">Caricamento…</p>}
      {error && <p role="alert">{error}</p>}
      {report && person && <MonthlySheetTable report={report} name={person.name} code={person.employee_code} />}
      {!loading && !error && people.length === 0 && <p>Nessun dipendente disponibile.</p>}
    </section>
  </ProtectedPage>;
}
