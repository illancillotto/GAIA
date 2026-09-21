"use client";

import type { RegisterDetail } from "@/types/notice-register";
import { DocumentComparison } from "./document-comparison";
import { MutationForm, type MutationContext } from "./mutation-form";
import { Field, ReadState, panelClass } from "./presentation";
import { useRegisterResource } from "./use-register-resource";

export function ReconciliationUndo({ source, context }: { source: RegisterDetail; context: MutationContext }) {
  const result = useRegisterResource<RegisterDetail>(context.token, `/${source.reconciled_into_id}`);
  return <section className={`${panelClass} space-y-3`}>
    <h3 className="text-lg font-semibold">Rettifica riconciliazione errata</h3>
    <p className="text-sm">Annulla il collegamento, poi seleziona il documento corretto. Se ci sono modifiche o import successivi dipendenti, il server blocca l&apos;annullamento. Le precedenti valutazioni di notifica e STEP non saranno ripristinate.</p>
    <ReadState {...result} />
    {result.data && <>
      <DocumentComparison document={result.data} />
      <MutationForm {...context} path={`/${source.id}/riconciliazione/annulla`} method="POST" title="Annulla riconciliazione"
        buildData={(form) => ({ target_document_id: result.data!.id, target_version: result.data!.version, confirmed: form.get("confirmed") === "on" })}>
        <Field label="Confermo il ripristino di invii ed evidenze nella scheda Poste"><input name="confirmed" type="checkbox" required /></Field>
      </MutationForm>
    </>}
  </section>;
}
