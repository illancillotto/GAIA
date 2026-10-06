import { useState, type FormEvent } from "react";

import type { ControlCase } from "@/types/parcel-control";

type Props = { practice: ControlCase; busy: boolean; save: (action: string, data: Record<string, unknown>, reason: string) => Promise<void> };

function fields(event: FormEvent<HTMLFormElement>): Record<string, string> {
  event.preventDefault();
  return Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>;
}

export function ParcelControlForms({ practice, busy, save }: Props) {
  const [action, setAction] = useState("evidence");
  async function submit(event: FormEvent<HTMLFormElement>) {
    const values = fields(event);
    const { reason, ...data } = values;
    if (action === "evidence") {
      await save(action, { ...data, years: data.years.split(",").map(Number) }, reason);
    } else if (action === "match") {
      await save(action, { ...data, evidence_ids: [data.evidence_id] }, reason);
    } else if (action === "proposal") {
      await save(action, { ...data, year: Number(data.year), evidence_ids: practice.evidence.map(entry => entry.id) }, reason);
    } else {
      await save(action, data, reason);
    }
  }
  return <section className="rounded-xl border bg-white p-4">
    <h3 className="font-semibold">Prossima azione</h3>
    <label>Azione<select value={action} onChange={event => setAction(event.target.value)} className="form-control">
      <option value="evidence">Registra evidenza</option><option value="match">Verifica intestatario</option>
      <option value="proposal">Prepara proposta</option><option value="status">Aggiorna stato pratica</option>
      <option value="parcel_status">Aggiorna esito di un immobile</option>
    </select></label>
    <form key={action} onSubmit={submit} className="mt-3 grid gap-3 md:grid-cols-2">
      {action === "evidence" && <>
        <label>Particella<select name="parcel_id" className="form-control"><option value={practice.parcel_id || ""}>{practice.current.label}</option>
          {practice.parcels.map(parcel => <option key={parcel.id} value={parcel.id}>{parcel.reference.foglio}/{parcel.reference.particella}</option>)}</select></label>
        <label>Tipo evidenza<select name="kind" className="form-control"><option value="document">Documento</option>
          <option value="cadastre">Esistenza catastale</option><option value="territory">Verifica territoriale</option>
          <option value="historical_title">Titolarità storica</option><option value="role_check">Confronto con il ruolo</option></select></label>
        <label>Fonte<input name="source" required className="form-control" /></label>
        <label>Riferimento documentale<input name="reference" required className="form-control" /></label>
        <label>Data evidenza<input name="observed_at" type="date" required className="form-control" /></label>
        <label>Versione della fonte<input name="version" className="form-control" /></label>
        <label>Ambito verificato<input name="scope" className="form-control" /></label>
        <label>Esito<select name="result" className="form-control"><option value="verification_required">Da verificare</option>
          <option value="existing">Esistente</option><option value="suppressed">Soppressa con evidenza</option>
          <option value="inside_outside_town">Nel consorzio e fuori centro abitato</option>
          <option value="outside">Fuori consorzio</option><option value="inside_town">In centro abitato</option>
          <option value="absent">Assenza verificata dal ruolo</option></select></label>
        <label>Annualità verificate, separate da virgola<input name="years" defaultValue="2025" className="form-control" /></label>
      </>}
      {action === "match" && <>
        <label>Intestatario<input name="name" required className="form-control" /></label>
        <label>Codice fiscale<input name="tax_code" required className="form-control" /></label>
        <label>Tipo soggetto<select name="subject_kind" className="form-control"><option value="PF">Persona fisica</option><option value="PNF">Soggetto diverso da persona fisica</option></select></label>
        <label>Diritto<input name="right" required className="form-control" /></label>
        <label>Quota<input name="share" required className="form-control" placeholder="1/1" /></label>
        <label>Periodo documentato<input name="period" required className="form-control" /></label>
        <label>Evidenza<select name="evidence_id" required className="form-control"><option value="">Seleziona</option>
          {practice.evidence.map(entry => <option key={entry.id} value={entry.id}>{entry.reference || entry.kind}</option>)}</select></label>
        <label>Abbinamento<select name="status" className="form-control"><option value="proposed">Proposto</option><option value="confirmed">Confermato dall&apos;operatore</option></select></label>
        <label>Contraddizioni e dubbi<input name="contradictions" className="form-control" /></label>
      </>}
      {action === "proposal" && <>
        <label>Particella<select name="parcel_id" className="form-control"><option value={practice.parcel_id || ""}>{practice.current.label}</option>
          {practice.parcels.map(parcel => <option key={parcel.id} value={parcel.id}>{parcel.reference.comune_nome} {parcel.reference.foglio}/{parcel.reference.particella}</option>)}</select></label>
        <label>Intestatario verificato<select name="match_id" required className="form-control"><option value="">Seleziona</option>
          {practice.matches.filter(match => match.status === "confirmed").map(match => <option key={match.id} value={match.id}>{match.name} · {match.tax_code}</option>)}</select></label>
        <label>Annualità<input name="year" type="number" min="2020" max="2025" defaultValue="2025" required className="form-control" /></label>
        <label>Tipo proposta<select name="kind" className="form-control"><option value="insertion">Inserimento ruolo 2025</option><option value="rectification">Rettifica posizione</option><option value="historical_review">Valutazione annualità pregresse</option></select></label>
        <label>Componente tributaria<input name="component" required className="form-control" /></label>
        <label>Regola tributaria applicata<input name="eligibility_rule" required className="form-control" /></label>
        <label>Dubbi residui<input name="residual_doubts" className="form-control" /></label>
      </>}
      {action === "status" && <label>Stato<select name="status" className="form-control"><option value="open">Aperta</option><option value="investigating">Da approfondire</option><option value="closed">Conclusa</option><option value="excluded">Esclusa</option></select></label>}
      {action === "parcel_status" && <><label>Immobile<select name="parcel_id" className="form-control">
        {practice.parcels.map(parcel => <option key={parcel.id} value={parcel.id}>{parcel.reference.foglio}/{parcel.reference.particella}</option>)}</select></label>
        <label>Esito immobile<select name="status" className="form-control"><option value="investigating">Da approfondire</option><option value="verified">Verificato</option><option value="excluded">Escluso</option></select></label></>}
      <label>Motivazione<textarea name="reason" minLength={3} required className="form-control" /></label>
      <button type="submit" disabled={busy} className="btn-primary">Salva nella pratica</button>
    </form>
  </section>;
}
