import Link from "next/link";

import type { ControlRow } from "@/types/parcel-control";

export const CONTROL_YEARS = Array.from({ length: 15 }, (_, index) => 2011 + index);
export const CONTROL_LABELS: Record<string, string> = {
  present: "Presente", absent: "Assente", not_verifiable: "Non verificabile",
  open: "Aperta", investigating: "Da approfondire", closed: "Conclusa", excluded: "Esclusa",
  review_required: "Da verificare", confirmed: "Confermata", proposed: "Proposto",
  missing: "Mancante", incomplete: "Incompleto", invalid: "Non valido", inconsistent: "Incoerente",
};

export function ParcelControlTable({ items, open, busy }: {
  items: ControlRow[]; open: (item: ControlRow) => void; busy: boolean;
}) {
  return <div className="overflow-x-auto rounded-xl border bg-white">
    <table className="w-full text-left text-sm">
      <thead><tr><th className="p-3">Particella</th>{CONTROL_YEARS.map(year => <th key={year}>{year}</th>)}
        <th>Prima / ultima</th><th>Controlli</th><th>Pratica</th></tr></thead>
      <tbody>{items.map(item => <tr key={item.id} className="border-t">
        <td className="p-3">{item.label}</td>
        {CONTROL_YEARS.map(year => <td key={year} className="p-2">{CONTROL_LABELS[item.years[year]]}</td>)}
        <td>{item.first_year} / {item.last_year}</td>
        <td>{item.cf_anomaly && <p>CF da verificare</p>}{item.identity_incomplete && <p>Identificativo incompleto</p>}
          <p>Territorio da verificare</p></td>
        <td className="p-3">{item.case_id
          ? <Link href={`/ruolo/particelle?vista=cases&pratica=${item.case_id}`}>{CONTROL_LABELS[item.case_status as string]}</Link>
          : <button disabled={busy} className="btn-secondary" onClick={() => open(item)}>Apri pratica</button>}</td>
      </tr>)}</tbody>
    </table>
    {items.length === 0 && <p className="p-4">Nessuna particella in questa vista. Aggiorna l&apos;analisi per censire lo storico.</p>}
  </div>;
}
