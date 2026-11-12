"use client";

import { useTemplateCatalog, type TemplateDraft } from "./use-template-catalog";

export function TemplateCatalog({ token, disabled, onSelect, onVariables }: { token: string; disabled: boolean; onSelect: (draft: TemplateDraft) => void; onVariables?: (variables: Record<string, string>) => void }) {
  const { catalog, status, load } = useTemplateCatalog(token, onVariables);
  return <section aria-label="Modelli di partenza" className="space-y-3 rounded-lg border bg-slate-50 p-3">
    <button type="button" className="btn-secondary" disabled={disabled || status.busy} onClick={() => void load()}>Modelli di partenza 2021 e variabili</button>
    {status.error && <p role="alert" className="text-rose-800">{status.error}</p>}
    {catalog && <><p className="text-sm">{catalog.note}</p><div className="flex flex-wrap gap-2">{catalog.proposals.map((proposal) => <button type="button" className="btn-secondary" key={proposal.code} disabled={disabled || status.busy} onClick={() => onSelect({ ...proposal })}>Usa {proposal.name}</button>)}</div>
      <details><summary>Variabili disponibili · solo testo semplice</summary><dl className="mt-2 space-y-2 text-sm">{Object.entries(catalog.variables).map(([name, description]) => <div key={name}><dt className="font-mono">{`{{${name}}}`}</dt><dd>{description}</dd></div>)}</dl></details></>}
  </section>;
}
