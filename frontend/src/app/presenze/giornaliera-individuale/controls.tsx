import { InazSyncControl } from "@/components/presenze/inaz-sync-control";
import type { useMonthlyPeople } from "./use-monthly-sheet";

type Person = ReturnType<typeof useMonthlyPeople>["people"][number];
type Props = {
  month: string; setMonth: (month: string) => void;
  people: Person[]; personId: string; setPersonId: (id: string) => void;
  person: Person | undefined; refresh: () => void; hasReport: boolean;
};

export function MonthlySheetControls({ month, setMonth, people, personId, setPersonId, person, refresh, hasReport }: Props) {
  return <>
      <div className="flex flex-wrap items-end gap-4 print:hidden">
        <label>Mese<input aria-label="Mese" type="month" className="block rounded border p-2" value={month} onChange={event => setMonth(event.target.value)} /></label>
        <label>Dipendente<select aria-label="Dipendente" className="block max-w-full rounded border p-2" value={personId} onChange={event => setPersonId(event.target.value)}>
          {people.map(item => <option key={item.id} value={item.id}>{item.name} · {item.employee_code}</option>)}
        </select></label>
        <button type="button" className="rounded border px-4 py-2" onClick={refresh}>Aggiorna</button>
        <button type="button" className="rounded border px-4 py-2 disabled:cursor-not-allowed disabled:opacity-50" disabled={!hasReport} onClick={() => window.print()}>Stampa / PDF</button>
      </div>
      <InazSyncControl month={month} employeeCode={person?.employee_code} onCompleted={refresh} />
  </>;
}
