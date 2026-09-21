"use client";

import { useState } from "react";
import type { RegisterDetail } from "@/types/notice-register";
import type { ImportRow } from "./import-client";
import { DocumentComparison } from "./document-comparison";
import { MutationForm } from "./mutation-form";
import { Field, inputClass, ReadState } from "./presentation";
import { useRegisterResource } from "./use-register-resource";

export const DECISIONS: Record<string, string> = { keep_existing: "Mantieni dati esistenti", register_evidence: "Conserva variante come evidenza" };

function ConflictComparison({ token, batchId, row, canEdit, onSaved, documentId }: { token: string; batchId: string; row: ImportRow; canEdit: boolean; onSaved: () => void; documentId: string }) {
  const result = useRegisterResource<RegisterDetail>(token, `/${documentId}`);
  if (result.data?.reconciled_into_id) return <ConflictComparison token={token} batchId={batchId} row={row} canEdit={canEdit} onSaved={onSaved} documentId={result.data.reconciled_into_id} />;
  return <div className="mt-3 space-y-3"><ReadState {...result} />{result.data && <>
    <DocumentComparison document={result.data} />
    {canEdit && <MutationForm token={token} version={result.data.version} onSaved={onSaved} path={`/importazioni/${batchId}/righe/${row.id}/risoluzione`} method="POST" title="Risolvi conflitto importazione"
      buildData={(form) => ({ decision: String(form.get("decision")), fingerprint: row.fingerprint, document_id: result.data!.id, confirmed: form.get("confirmed") === "on" })}>
      <Field label="Decisione sul conflitto"><select className={inputClass} name="decision">{Object.entries(DECISIONS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
      <p className="text-sm sm:col-span-2">Nessuna scelta sovrascrive i campi. La nuova evidenza riapre la verifica della notifica. Per correggere i dati, apri il documento e usa le operazioni di correzione prima di risolvere il conflitto.</p>
      <Field label="Confermo di aver confrontato originale, variante e dati correnti"><input name="confirmed" type="checkbox" required /></Field>
    </MutationForm>}
  </>}</div>;
}

export function ImportConflict({ token, batchId, row, canEdit, onSaved }: { token: string; batchId: string; row: ImportRow; canEdit: boolean; onSaved: () => void }) {
  const [comparing, setComparing] = useState(false);
  if (row.resolution) return <div className="mt-3 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-950">
    <p>Conflitto risolto: {DECISIONS[row.resolution.decision]}</p>
    <p>Operatore #{row.resolution.actor_id} | {row.resolution.decided_at} | Versione {row.resolution.document_version}</p>
    <p className="break-words">{row.resolution.reason}</p>
  </div>;
  return <div className="mt-3">
    <button className="btn-secondary" onClick={() => setComparing(!comparing)}>{comparing ? "Chiudi confronto" : "Confronta variante e risolvi"}</button>
    {comparing && <ConflictComparison token={token} batchId={batchId} row={row} canEdit={canEdit} onSaved={onSaved} documentId={row.document_id!} />}
  </div>;
}
