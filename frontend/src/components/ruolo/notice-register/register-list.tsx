"use client";

import { useState, type FormEvent } from "react";
import type { RegisterPage, RegisterSummary, RegisterView } from "@/types/notice-register";
import { queryString } from "./client";
import { AnomalyLabels, Field, inputClass, NOTIFICATIONS, Pagination, panelClass, ReadState, RECOVERIES } from "./presentation";
import { useRegisterResource } from "./use-register-resource";

type Filters = { q: string; tax_year: string; notification_state: string; recovery_state: string };

function RegisterFilters({ onApply }: { onApply: (filters: Filters) => void }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onApply({ q: String(form.get("q")).trim(), tax_year: String(form.get("tax_year")),
      notification_state: String(form.get("notification_state")), recovery_state: String(form.get("recovery_state")) });
  }
  return <form aria-label="Filtri registro" onSubmit={submit} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
    <Field label="Numero, CF, riferimento o tracking"><input className={inputClass} name="q" minLength={3} maxLength={100} type="search" /></Field>
    <Field label="Annualita"><input className={inputClass} name="tax_year" type="number" min={1900} max={9999} /></Field>
    <Field label="Notifica"><select className={inputClass} name="notification_state"><option value="">Tutte</option>{Object.entries(NOTIFICATIONS).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></Field>
    <Field label="STEP"><select className={inputClass} name="recovery_state"><option value="">Tutti</option>{Object.entries(RECOVERIES).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></Field>
    <button className="btn-primary self-end" type="submit">Applica filtri</button>
  </form>;
}

function DocumentCard({ document, onSelect }: { document: RegisterSummary; onSelect: (id: string) => void }) {
  return <article className={panelClass}>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0"><h3 className="break-all text-lg font-semibold">{document.document_number}</h3>
        <p className="text-sm text-gray-600">{document.tax_code ?? "CF non disponibile"} | {document.source_system}</p>
      </div><button className="btn-secondary" onClick={() => onSelect(document.id)}>Apri {document.document_number}</button>
    </div>
    <dl className="my-3 grid gap-2 text-sm sm:grid-cols-3">
      <div><dt className="text-gray-500">Notifica</dt><dd>{NOTIFICATIONS[document.notification_state]}</dd></div>
      <div><dt className="text-gray-500">Posizioni</dt><dd>{document.position_count} | {document.unlinked_count} da collegare</dd></div>
      <div><dt className="text-gray-500">Verifiche STEP aperte</dt><dd>{document.recovery_review_count}</dd></div>
    </dl><AnomalyLabels values={document.anomalies} />
  </article>;
}

export function RegisterList({ token, view, onSelect }: { token: string; view: RegisterView; onSelect: (id: string) => void }) {
  const [filters, setFilters] = useState<Filters>({ q: "", tax_year: "", notification_state: "", recovery_state: "" });
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const path = `?${queryString({ ...filters, view, page: String(page), page_size: "20" })}`;
  const resource = useRegisterResource<RegisterPage<RegisterSummary>>(token, path, revision);
  function apply(next: Filters) { setFilters(next); setPage(1); }
  return <section className="space-y-4" aria-label="Elenco registro">
    <div className={panelClass}><RegisterFilters onApply={apply} /></div>
    <button className="btn-secondary" onClick={() => setRevision(revision + 1)}>Ricarica elenco</button>
    <ReadState loading={resource.loading} error={resource.error} />
    {resource.data && <>
      {resource.data.items.length === 0 && <p className={panelClass}>Nessun documento per i filtri selezionati.</p>}
      <div className="grid gap-3">{resource.data.items.map((document) => <DocumentCard key={document.id} document={document} onSelect={onSelect} />)}</div>
      <Pagination page={page} pageSize={20} total={resource.data.total} onPage={setPage} />
    </>}
  </section>;
}
