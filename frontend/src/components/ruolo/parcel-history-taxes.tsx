import Link from "next/link";
import type { ParcelHistory, ParcelTaxEntry } from "@/types/parcel-history";

export function historyMoney(value: number | null) {
  return value === null ? "Non disponibile" : new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function TaxEntry({ entry }: { entry: ParcelTaxEntry }) {
  return <article className="rounded-xl border border-slate-200 bg-white p-4">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h4 className="font-semibold text-slate-900">{entry.name || "Contribuente non indicato"}</h4>
        <p className="mt-1 text-sm text-slate-600">CF: {entry.tax_code || "non indicato"}</p>
        {entry.partita_tax_code && entry.partita_tax_code !== entry.tax_code && <p className="mt-1 text-sm text-amber-800">CF della partita: {entry.partita_tax_code} · Da confrontare con l’avviso</p>}
        {entry.co_holders && <p className="mt-1 text-sm">Cointestazione riportata: {entry.co_holders}</p>}
      </div>
      <Link className="btn-secondary" href={`/ruolo/tributi/${entry.notice_id}`}>Apri tributo {entry.notice_number}</Link>
    </div>
    <dl className="mt-4 grid grid-cols-2 gap-3 text-sm lg:grid-cols-4">
      <div><dt className="text-slate-500">Manutenzione</dt><dd>{historyMoney(entry.maintenance)}</dd></div>
      <div><dt className="text-slate-500">Irrigazione</dt><dd>{historyMoney(entry.irrigation)}</dd></div>
      <div><dt className="text-slate-500">Istituzionale</dt><dd>{historyMoney(entry.institutional)}</dd></div>
      <div><dt className="text-slate-500">Totale della riga</dt><dd className="font-semibold">{historyMoney(entry.total)}</dd></div>
    </dl>
    <details className="mt-3 text-sm"><summary className="cursor-pointer text-slate-600">Superfici e dati della riga originale</summary>
      <p className="mt-2">Superficie catastale: {entry.area_ha ?? "non indicata"} ha · Irrigata: {entry.irrigated_ha ?? "non indicata"} ha</p>
      <p>Coltura: {entry.crop || "non indicata"} · Distretto: {entry.district || "non indicato"}</p>
      <Link href={`/ruolo/avvisi/${entry.notice_id}`} className="mt-2 inline-block underline">Apri avviso originale</Link>
    </details>
  </article>;
}

export function ParcelHistoryTaxes({ history }: { history: ParcelHistory }) {
  const years = Array.from({ length: history.last_year - history.first_year + 1 }, (_, index) => history.first_year + index);
  return <section aria-label="Tributi nel tempo" className="space-y-5">
    <div><h2 className="text-lg font-semibold">Tributi nel tempo</h2><p className="mt-1 text-sm text-slate-600">Chi risulta nei ruoli importati, anno per anno. Il contribuente può essere diverso dal proprietario catastale.</p></div>
    <p className="rounded-lg bg-slate-100 p-3 text-sm">Gli importi si riferiscono alla singola riga della particella, non al totale dell’avviso. Un dato mancante non vale zero. Pagamenti e rettifiche sono consultabili in «Apri tributo».</p>
    <ol className="space-y-5 border-l-2 border-emerald-200 pl-4 sm:pl-6">{years.map(year => {
      const entries = history.taxes.filter(entry => entry.year === year);
      return <li key={year} className="relative"><span className="absolute -left-[23px] top-2 h-3 w-3 rounded-full bg-emerald-700 sm:-left-[31px]" />
        <h3 className="mb-2 flex flex-wrap items-center gap-2 text-lg font-semibold">{year}{year === history.first_year && <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-800">Prima presenza disponibile</span>}</h3>
        {entries.length ? <div className="space-y-3">{entries.map(entry => <TaxEntry key={entry.id} entry={entry} />)}</div>
          : <p className="rounded-xl border border-dashed p-4 text-sm text-slate-600">Nessuna riga importata per questo anno. Presenza non verificabile; non dimostra cessazione o mancato pagamento.</p>}
      </li>;
    })}</ol>
  </section>;
}
