import Link from "next/link";
import { type FormEvent } from "react";

import { ParcelControlForms } from "@/components/ruolo/parcel-control-forms";
import { CONTROL_LABELS } from "@/components/ruolo/parcel-control-table";
import type { ControlCase } from "@/types/parcel-control";

type Props = { practice: ControlCase; busy: boolean; editable: boolean;
  save: (action: string, data: Record<string, unknown>, reason: string) => Promise<void> };

export function ParcelControlDetail({ practice, busy, editable, save }: Props) {
  return <div className="space-y-5">
    <h2 className="text-xl font-semibold">{practice.current.label} · {CONTROL_LABELS[practice.status]}</h2>
    <p>Responsabile: {practice.responsible_id}. Il dato originale del ruolo resta conservato separatamente.</p>
    <section className="rounded-xl border bg-white p-4"><h3 className="font-semibold">Avvisi e storico all&apos;apertura</h3>
      <p>Le particelle già a ruolo nel 2011–2025 restano in istruttoria anche dentro, o parzialmente dentro, un centro abitato. La presenza storica non autorizza il reinserimento.</p>
      {practice.original.notice && <p>{practice.original.notice.name} · CF {practice.original.notice.tax_code.original || "mancante"}</p>}
      {practice.original.occurrences.map(row => <p key={row.row_id}>
        {row.year} · <Link href={`/ruolo/avvisi/${row.avviso_id}`}>{row.codice_cnc}</Link> · {row.name} · CF {row.tax_code.original || "mancante"}
        {row.tax_code.anomaly && ` (${CONTROL_LABELS[row.tax_code.anomaly]})`}
        {row.catasto_status && ` · Evidenza AdE: ${row.catasto_status}`}
      </p>)}
    </section>
    <section className="rounded-xl border bg-white p-4"><h3 className="font-semibold">Evidenze e intestatari verificati</h3>
      {practice.evidence.map(entry => <p key={entry.id}>{entry.kind} · {entry.source} · {entry.reference} · {entry.result} · {entry.scope}</p>)}
      {practice.matches.map(match => <p key={match.id}>{match.name} · {match.tax_code} · {match.right} · {match.share} · {match.period} · {CONTROL_LABELS[match.status]}</p>)}
    </section>
    <section className="rounded-xl border bg-white p-4"><h3 className="font-semibold">Visure SISTER</h3>
      <p>Gli errori tecnici e i risultati senza corrispondenze non dimostrano l&apos;inesistenza catastale.</p>
      {practice.visure.map(visura => <div key={visura.id} className="mt-3 border-t pt-3">
        <p>{visura.search_mode === "immobile" ? "Per particella catastale" : "Per soggetto"} · {visura.status} · {visura.error}</p>
        <Link href={`/elaborazioni/batches/${visura.batch_id}`} className="text-green-800 underline">Apri elaborazione per avvio, documenti e gestione errori</Link>
        {visura.extraction?.owners?.map((owner, index) => <p key={index}>{owner.denominazione} · {owner.codice_fiscale} · {owner.diritto} · {owner.quota}</p>)}
        {visura.search_mode === "soggetto" && <p>Il parser corrente estrae un solo riferimento: verificare il documento completo per le altre particelle.</p>}
        {editable && visura.status === "completed" && visura.search_mode === "soggetto" && <button className="btn-secondary" disabled={busy}
          onClick={() => void save("recover", { evidence_id: practice.evidence.find(entry => entry.request_id === visura.id)?.id }, "Acquisizione riferimento estratto dalla visura per soggetto")}>Acquisisci particella estratta</button>}
      </div>)}
      {editable && <VisuraForm practice={practice} busy={busy} save={save} />}
    </section>
    <section className="rounded-xl border bg-white p-4"><h3 className="font-semibold">Particelle recuperate tramite visura per soggetto</h3>
      <p>Una particella mai a ruolo non entra nella coda di recupero. Prima della proposta occorre documentare almeno una presenza nel 2011–2025.</p>
      {practice.parcels.map(parcel => <p key={parcel.id}>{parcel.reference.comune_nome} · {parcel.reference.foglio}/{parcel.reference.particella} · {parcel.status} · Verifica territoriale e confronto ruolo necessari</p>)}
    </section>
    {editable && <ParcelControlForms practice={practice} busy={busy} save={save} />}
    <section className="rounded-xl border bg-white p-4"><h3 className="font-semibold">Proposte da verificare</h3>
      {practice.proposals.map(proposal => <div key={proposal.id} className="mt-3 border-t pt-3">
        <p>{proposal.label} · {proposal.year} · {proposal.verified_tax_code} · {CONTROL_LABELS[proposal.status]}</p>
        <p>{proposal.eligibility_rule} · Dubbi: {proposal.residual_doubts}</p>
        {editable && <DecisionForm proposalId={proposal.id} busy={busy} save={save} />}
      </div>)}
    </section>
    <section className="rounded-xl border bg-white p-4"><h3 className="font-semibold">Storico delle decisioni</h3>
      {practice.audit.map((event, index) => <p key={index}>{event.created_at} · Operatore {event.actor_id} · {event.action} · {event.reason}</p>)}
    </section>
  </div>;
}

function VisuraForm({ practice, busy, save }: Omit<Props, "editable">) {
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>;
    const { reason, scope, match_id, ...request } = values;
    await save("visura/richiesta", { request, scope, match_id }, reason);
  }
  return <form onSubmit={submit} className="mt-4 grid gap-3 md:grid-cols-2">
    <label>Ricerca<select name="search_mode" className="form-control"><option value="immobile">Per particella catastale</option><option value="soggetto">Per soggetto verificato</option></select></label>
    <label>Intestatario verificato<select name="match_id" className="form-control"><option value="">Non richiesto per particella</option>
      {practice.matches.filter(match => match.status === "confirmed").map(match => <option key={match.id} value={match.id}>{match.name} · {match.tax_code}</option>)}</select></label>
    <label>Comune SISTER<input name="comune" defaultValue={practice.current.reference.comune_nome} className="form-control" /></label>
    <label>Catasto<select name="catasto" className="form-control"><option value="Terreni">Terreni</option><option value="Fabbricati">Fabbricati</option></select></label>
    <label>Sezione<input name="sezione" defaultValue={practice.current.reference.sezione || ""} className="form-control" /></label>
    <label>Foglio<input name="foglio" defaultValue={practice.current.reference.foglio} className="form-control" /></label>
    <label>Particella<input name="particella" defaultValue={practice.current.reference.particella} className="form-control" /></label>
    <label>Subalterno<input name="subalterno" defaultValue={practice.current.reference.subalterno} className="form-control" /></label>
    <label>Tipo visura<select name="tipo_visura" className="form-control"><option>Sintetica</option><option>Analitica</option><option>Completa</option></select></label>
    <label>Ambito effettivo della ricerca<input name="scope" required className="form-control" placeholder="Ufficio provinciale e territorio interrogato" /></label>
    <label>Motivazione<input name="reason" required minLength={3} className="form-control" /></label>
    <button disabled={busy} className="btn-secondary">Prepara richiesta SISTER</button>
  </form>;
}

function DecisionForm({ proposalId, busy, save }: { proposalId: string; busy: boolean; save: Props["save"] }) {
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>;
    await save("decision", { proposal_id: proposalId, status: values.status }, values.reason);
  }
  return <form onSubmit={submit} className="mt-2 flex flex-wrap gap-2">
    <select name="status" aria-label="Esito proposta" className="form-control"><option value="investigating">Richiedi approfondimento</option><option value="excluded">Escludi</option><option value="confirmed">Conferma proposta</option></select>
    <input name="reason" aria-label="Motivazione decisione" required minLength={3} className="form-control" />
    <button disabled={busy} className="btn-secondary">Registra decisione</button>
  </form>;
}
