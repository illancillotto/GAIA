"use client";

import { useState } from "react";
import type { RegisterDetail } from "@/types/notice-register";
import { RecordForm, type MutationContext } from "./mutation-form";
import { PositionPanel } from "./position-panel";
import { AnomalyLabels, JsonDetails, NOTIFICATIONS, panelClass, ReadState } from "./presentation";
import { RegisterTimeline } from "./timeline";
import { useRegisterResource } from "./use-register-resource";
import { ReconciliationPanel } from "./reconciliation-panel";
import { ReconciliationUndo } from "./reconciliation-undo";
import { EligibilityPanel } from "./eligibility-panel";
import { AttemptForm } from "./attempt-form";

function DocumentForms({ document, context }: { document: RegisterDetail; context: MutationContext }) {
  const path = `/${document.id}`;
  return <section aria-label="Operazioni documento" className={`${panelClass} space-y-4`}>
    <AttemptForm documentId={document.id} context={context} />
    <details><summary className="cursor-pointer font-medium">Correggi documento storico</summary><RecordForm {...context} path={path} method="PUT" title="Correggi documento" kind="document" initial={{ ...document }} /></details>
    <details><summary className="cursor-pointer font-medium">Aggiungi posizione annuale</summary><RecordForm {...context} path={`${path}/posizioni`} method="POST" title="Nuova posizione" kind="position" initial={{ source_namespace: "incass" }} /></details>
    <details><summary className="cursor-pointer font-medium">Registra evidenza</summary><RecordForm {...context} path={`${path}/evidenze`} method="POST" title="Nuova evidenza" kind="evidence" initial={{}} /></details>
    <details><summary className="cursor-pointer font-medium">Valuta notifica</summary><RecordForm {...context} path={`${path}/notifica`} method="PUT" title="Valutazione notifica" kind="notification" initial={{ ...document.notification }} /></details>
  </section>;
}

function DocumentContent({ document, context, canEdit, onSelect }: { document: RegisterDetail; context: MutationContext; canEdit: boolean; onSelect: (id: string) => void }) {
  const editable = canEdit && !document.reconciled_into_id;
  return <div className="space-y-4">
    <header className={`${panelClass} space-y-3`}>
      <h2 className="break-all text-2xl font-semibold">{document.document_number}</h2>
      <p>{document.tax_code ?? "CF non disponibile"} | Emesso: {document.issued_on ?? "Data assente"}</p>
      <p>Notifica: <strong>{NOTIFICATIONS[document.notification_state]}</strong> | Perfezionamento: {document.notification?.notified_on ?? "-"}</p>
      <p className="text-sm text-gray-600">Origine: {document.source_system} | Versione: {document.version}</p>
      <AnomalyLabels values={document.anomalies} />
      <JsonDetails title="Documento originale (sola lettura)" value={document.original_json} />
    </header>
    <EligibilityPanel token={context.token} documentId={document.id} />
    {document.reconciled_into_id && <section className={panelClass}><p>Scheda Poste riconciliata. Originale e storico restano consultabili; invii ed evidenze si trovano nel documento di destinazione.</p><button className="btn-secondary mt-3" onClick={() => onSelect(document.reconciled_into_id!)}>Apri documento riconciliato</button></section>}
    {editable && <DocumentForms document={document} context={context} />}
    {canEdit && document.reconciled_into_id && <ReconciliationUndo source={document} context={context} />}
    {editable && document.source_system === "poste_db" && document.positions.length === 0 && <ReconciliationPanel source={document} context={context} />}
    <section aria-label="Posizioni annuali" className="space-y-3"><h2 className="text-xl font-semibold">Posizioni annuali</h2>
      {document.positions.length === 0 && !document.reconciled_into_id && <p className={panelClass}>Documento senza posizioni. Aggiungi i riferimenti annuali prima del collegamento.</p>}
      {document.positions.map((position) => <PositionPanel key={position.id} position={position} documentId={document.id} context={context} canEdit={editable} />)}
    </section>
    <RegisterTimeline token={context.token} documentId={document.id} />
  </div>;
}

export function DocumentDetail({ token, documentId, canEdit, onSelect }: { token: string; documentId: string; canEdit: boolean; onSelect: (id: string) => void }) {
  const [revision, setRevision] = useState(0);
  const [saved, setSaved] = useState(false);
  const resource = useRegisterResource<RegisterDetail>(token, `/${documentId}`, revision);
  function reload() { setRevision((current) => current + 1); }
  function onSaved() { setSaved(true); reload(); }
  return <section className="space-y-4">
    <button className="btn-secondary" onClick={reload}>Ricarica documento</button>
    {saved && <p role="status" className="rounded-xl bg-emerald-50 p-3 text-emerald-900">Registrazione salvata. Verifica lo stato aggiornato.</p>}
    <ReadState loading={resource.loading} error={resource.error} />
    {resource.data && <DocumentContent key={`${resource.data.version}:${revision}`} document={resource.data} canEdit={canEdit} onSelect={onSelect}
      context={{ token, version: resource.data.version, onSaved }} />}
  </section>;
}
