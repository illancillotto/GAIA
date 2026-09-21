"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import type { CandidateResult, RegisterPage, RegisterPosition } from "@/types/notice-register";
import { MutationForm, RecordForm, type MutationContext } from "./mutation-form";
import { Field, inputClass, Pagination, panelClass, ReadState, RECOVERIES } from "./presentation";
import { useRegisterResource } from "./use-register-resource";

function CandidateResults({ context, path, query }: { context: MutationContext; path: string; query: string }) {
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<CandidateResult | null>(null);
  const resource = useRegisterResource<RegisterPage<CandidateResult>>(context.token, `${path}/candidati?${new URLSearchParams({ q: query, page: String(page), page_size: "10" })}`);
  return <div className="space-y-3">
    <ReadState loading={resource.loading} error={resource.error} />
    {resource.data && <>
      {resource.data.items.length === 0 && <p>Nessun candidato. Il riferimento Incass non e un codice CNC.</p>}
      {resource.data.items.map((candidate) => <article key={candidate.id} className="rounded-xl border border-gray-200 p-3 text-sm">
        <p className="font-semibold">{candidate.codice_cnc} | {candidate.anno_tributario}</p>
        <p>{candidate.nominativo_raw ?? "Nominativo assente"} | {candidate.codice_fiscale_raw ?? "CF assente"}</p>
        <p>Importo originario: {candidate.importo_totale_euro ?? "non disponibile"} EUR (non saldo corrente)</p>
        <p className="break-all text-xs">UUID: {candidate.id}</p>
        <button className="btn-secondary mt-2" disabled={candidate.already_linked} onClick={() => setSelected(candidate)}>{candidate.already_linked ? "Gia collegato" : `Seleziona ${candidate.codice_cnc}`}</button>
      </article>)}
      <Pagination page={page} pageSize={10} total={resource.data.total} onPage={(next) => { setSelected(null); setPage(next); }} />
    </>}
    {selected && <MutationForm key={selected.id} {...context} path={`${path}/collegamento`} method="PUT" title="Conferma collegamento"
      buildData={() => ({ avviso_id: selected.id, confirmed: true })}>
      <p className="break-words text-sm sm:col-span-2">Collega {selected.codice_cnc} ({selected.anno_tributario}) - {selected.nominativo_raw ?? "Nominativo assente"}, {selected.codice_fiscale_raw ?? "CF assente"}.</p>
      <Field label="Confermo di aver verificato documento, destinatario e annualita"><input type="checkbox" required /></Field>
    </MutationForm>}
  </div>;
}

function CandidateSearch({ context, path }: { context: MutationContext; path: string }) {
  const [query, setQuery] = useState("");
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setQuery(String(new FormData(event.currentTarget).get("q")).trim());
  }
  return <div className="space-y-3">
    <form aria-label="Cerca avviso da collegare" onSubmit={submit} className="flex flex-wrap items-end gap-3">
      <Field label="CNC, CF, nominativo o UUID"><input className={inputClass} name="q" required minLength={3} maxLength={100} type="search" /></Field>
      <button className="btn-secondary">Cerca candidati</button>
    </form>
    {query && <CandidateResults key={query} context={context} path={path} query={query} />}
  </div>;
}

export function PositionPanel({ position, documentId, context, canEdit }: { position: RegisterPosition; documentId: string; context: MutationContext; canEdit: boolean }) {
  const path = `/${documentId}/posizioni/${position.id}`;
  return <article className={`${panelClass} space-y-4`}>
    <h3 className="break-all text-lg font-semibold">{position.tax_year} | {position.source_namespace}: {position.source_reference}</h3>
    <p className="text-sm">STEP: {position.recovery ? RECOVERIES[position.recovery.state] : "Da verificare"}</p>
    {position.avviso ? <p className="text-sm">Avviso collegato: <Link className="text-[#1D4E35] underline" href={`/ruolo/tributi/${position.avviso.id}`}>{position.avviso.codice_cnc}</Link> | {position.avviso.codice_fiscale_raw}</p> : <p className="text-sm text-amber-900">Nessun avviso collegato</p>}
    {position.recovery && <p className="break-words text-sm">Pratica: {position.recovery.case_reference ?? "-"} | Verifica: {position.recovery.verified_on ?? "-"} | Importo: {position.recovery.amount ?? "-"} EUR<br />Riferimento: {position.recovery.evidence_reference ?? "-"}</p>}
    {canEdit && <>
      <details><summary className="cursor-pointer font-medium">Cerca e collega avviso</summary><div className="mt-3"><CandidateSearch context={context} path={path} /></div></details>
      {position.avviso_id && <details><summary className="cursor-pointer font-medium">Scollega avviso</summary><MutationForm {...context} path={`${path}/collegamento`} method="PUT" title="Conferma scollegamento" buildData={() => ({ avviso_id: null, confirmed: true })}>
        <p className="text-sm">La posizione resta nel registro; notifica e STEP tornano da verificare.</p>
        <Field label="Confermo lo scollegamento"><input required type="checkbox" /></Field>
      </MutationForm></details>}
      <details><summary className="cursor-pointer font-medium">Correggi riferimento annuale</summary><RecordForm {...context} path={path} method="PUT" title="Correggi posizione" kind="position" initial={{ ...position }} /></details>
      <details><summary className="cursor-pointer font-medium">Registra verifica STEP</summary><RecordForm {...context} path={`${path}/step`} method="PUT" title="Verifica STEP" kind="recovery" initial={{ ...position.recovery }} /></details>
    </>}
  </article>;
}
