"use client";

import { useState, type FormEvent } from "react";
import type { RegisterDetail, RegisterPage, RegisterSummary } from "@/types/notice-register";
import { DocumentComparison } from "./document-comparison";
import { MutationForm, type MutationContext } from "./mutation-form";
import { Field, inputClass, Pagination, panelClass, ReadState } from "./presentation";
import { useRegisterResource } from "./use-register-resource";

function ReconcileSelection({ source, targetId, context }: { source: RegisterDetail; targetId: string; context: MutationContext }) {
  const result = useRegisterResource<RegisterDetail>(context.token, `/${targetId}`);
  return <div className="space-y-3"><ReadState {...result} />{result.data && <>
    <DocumentComparison document={result.data} />
    <MutationForm {...context} path={`/${source.id}/riconciliazione`} method="POST" title="Conferma riconciliazione Poste"
      buildData={(form) => ({ target_document_id: result.data!.id, target_version: result.data!.version, confirmed: form.get("confirmed") === "on" })}>
      <p className="text-sm sm:col-span-2">Invii ed evidenze di {source.document_number} saranno associati al documento scelto. La scheda Poste restera consultabile in Riconciliati. Notifica e STEP torneranno da verificare; nessun invio viene autorizzato.</p>
      <Field label="Confermo documento, destinatario, riferimenti annuali e invii"><input name="confirmed" type="checkbox" required /></Field>
    </MutationForm>
  </>}</div>;
}

function ReconcileResults({ source, query, context }: { source: RegisterDetail; query: string; context: MutationContext }) {
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const params = new URLSearchParams({ q: query, reconciliation_candidates: "true", page: String(page), page_size: "10" });
  const result = useRegisterResource<RegisterPage<RegisterSummary>>(context.token, `?${params}`);
  return <div className="space-y-3"><ReadState {...result} />{result.data && <>
    {result.data.items.length === 0 && <p>Nessun documento compatibile. La destinazione deve avere posizioni annuali e non essere una scheda Poste.</p>}
    {result.data.items.map((document) => <article key={document.id} className="rounded-xl border border-gray-200 p-3 text-sm">
      <p className="break-all">{document.document_number} | CF: {document.tax_code ?? "Assente"} | Posizioni: {document.position_count}</p>
      <button className="btn-secondary mt-2" onClick={() => setSelected(document.id)}>Confronta {document.document_number}</button>
    </article>)}
    <Pagination page={page} pageSize={10} total={result.data.total} onPage={(value) => { setSelected(null); setPage(value); }} />
  </>}
    {selected && <ReconcileSelection key={selected} source={source} targetId={selected} context={context} />}
  </div>;
}

export function ReconciliationPanel({ source, context }: { source: RegisterDetail; context: MutationContext }) {
  const [query, setQuery] = useState("");
  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setQuery(String(new FormData(event.currentTarget).get("q")).trim());
  }
  return <section className={`${panelClass} space-y-4`} aria-label="Riconciliazione Poste">
    <h3 className="text-lg font-semibold">Associa Poste a un documento del registro</h3>
    <p className="text-sm">Confronta originale, tracking ed evidenze prima di procedere. La ricerca per CF propone candidati, non prova una corrispondenza.</p>
    <form aria-label="Cerca documento da riconciliare" className="flex flex-wrap items-end gap-3" onSubmit={search}>
      <Field label="Numero documento, riferimento annuale, tracking o CF"><input className={inputClass} type="search" name="q" required minLength={3} maxLength={100} /></Field>
      <button className="btn-secondary">Cerca documenti</button>
    </form>
    {query && <ReconcileResults key={query} source={source} query={query} context={context} />}
  </section>;
}
