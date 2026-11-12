import Link from "next/link";
import type { ParcelHistory, ParcelOwner } from "@/types/parcel-history";

export function historyDate(value: string | null) {
  return value ? value.slice(0, 10).split("-").reverse().join("/") : "Data non disponibile";
}

function Owner({ owner }: { owner: ParcelOwner }) {
  return <div><p className="font-medium">{owner.name || "Intestatario non estratto"}</p>
    <p className="text-sm text-slate-600">CF: {owner.tax_code || "non indicato"} · {owner.right || "Diritto non indicato"} · Quota {owner.share || "non indicata"}</p></div>;
}

export function ParcelHistoryCadastre({ history }: { history: ParcelHistory }) {
  const { cadastre } = history;
  return <section aria-label="Proprietà catastale" className="space-y-5">
    <div><h2 className="text-lg font-semibold">Proprietà catastale</h2><p className="mt-1 text-sm text-slate-600">Passaggi e diritti risultanti dai documenti catastali collegati alla particella e consultabili con il tuo account.</p></div>
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm"><strong>Catena completa da verificare sui documenti.</strong> Le estrazioni disponibili possono contenere lacune. La visura attuale fotografa gli intestatari alla data della consultazione e non prova la proprietà negli anni precedenti.</div>
    {cadastre.documents.length === 0 && <div className="rounded-xl border border-dashed bg-white p-6"><h3 className="font-semibold">Manca una visura storica collegata e consultabile</h3><p className="mt-2 text-sm text-slate-600">I ruoli da soli non ricostruiscono la catena di proprietà. Acquisisci o collega una visura storica per documentare i passaggi, le quote e le eventuali soppressioni.</p></div>}
    <Link className="btn-secondary inline-flex" href="/catasto">Apri Catasto e visure SISTER</Link>
    <h3 className="font-semibold">Passaggi documentati</h3>
    {!cadastre.events.length && <p className="text-sm text-slate-600">Nessun passaggio storico estratto. Consulta i documenti disponibili o acquisisci una visura storica.</p>}
    <ol className="space-y-3">{cadastre.events.map(event => <li key={event.id} className="rounded-xl border bg-white p-4">
      <p className="mb-2 text-sm font-semibold text-emerald-800">Decorrenza: {historyDate(event.from_date)}</p><Owner owner={event} />
      <p className="mt-2 text-sm">{event.act || "Atto non estratto"} · Data atto: {historyDate(event.act_date)}</p>
      <a href={`#documento-${event.document_id}`} className="mt-2 inline-block text-sm underline">Vedi documento fonte</a>
    </li>)}</ol>
    <h3 className="font-semibold">Documenti e intestatari rilevati</h3>
    {cadastre.documents.map(document => <article id={`documento-${document.id}`} key={document.id} className="scroll-mt-8 rounded-xl border bg-white p-4">
      <h4 className="break-words font-semibold">{document.filename}</h4>
      <Link href={`/catasto/documents/${document.id}`} className="mt-2 inline-block text-sm font-medium text-emerald-800 underline">Apri visura originale</Link>
      <p className="mt-1 text-sm text-slate-600">{document.type} · Rilevazione: {historyDate(document.observed_at)} · Acquisizione: {historyDate(document.recorded_at)}</p>
      {document.suppressed && <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm font-semibold text-amber-900">Soppressione catastale documentata · {historyDate(document.suppressed_at)}. Non equivale alla cessazione del tributo.</p>}
      {document.ambiguous && <p className="mt-3 text-sm text-amber-800">Documento con riferimenti non univoci: intestatari e passaggi non attribuiti automaticamente.</p>}
      {document.extraction_status !== "completed" && <p className="mt-3 text-sm text-slate-600">Estrazione non disponibile o non completata: verifica il documento originale.</p>}
      <div className="mt-3 space-y-3">{document.owners.map((owner, index) => <Owner key={index} owner={owner} />)}</div>
    </article>)}
  </section>;
}
