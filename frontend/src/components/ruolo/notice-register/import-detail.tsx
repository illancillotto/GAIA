"use client";

import { useState } from "react";
import type { RegisterPage } from "@/types/notice-register";
import { registerError } from "./client";
import { downloadImport, type ImportBatch, type ImportRow } from "./import-client";
import { ConfirmImport } from "./import-forms";
import { AnomalyLabels, Field, inputClass, JsonDetails, Pagination, ReadState, panelClass } from "./presentation";
import { useRegisterResource } from "./use-register-resource";
import { ImportConflict } from "./import-conflict";

export const OUTCOMES: Record<string, string> = { new: "Nuovo", duplicate: "Duplicato", conflict: "Conflitto da verificare", imported: "Importato" };

function ImportRows({ token, batch, canEdit, onSelect }: { token: string; batch: ImportBatch; canEdit: boolean; onSelect: (id: string) => void }) {
  const [page, setPage] = useState(1);
  const [review, setReview] = useState("all");
  const [revision, setRevision] = useState(0);
  const result = useRegisterResource<RegisterPage<ImportRow>>(token, `/importazioni/${batch.id}/righe?page=${page}&page_size=10&review=${review}`, revision);
  return <section className="space-y-3"><h3 className="text-lg font-semibold">Righe e anomalie</h3>
    <Field label="Stato conflitti"><select className={inputClass} value={review} onChange={(event) => { setPage(1); setReview(event.target.value); }}><option value="all">Tutte le righe</option><option value="open">Conflitti aperti</option><option value="resolved">Conflitti risolti</option></select></Field>
    <ReadState {...result} />{result.data && <>
      {result.data.items.length === 0 && <p>Nessuna riga per questo filtro.</p>}
      {result.data.items.map((row) => <article key={row.id} className={panelClass}>
        <h4 className="break-all font-semibold">Riga {row.row_number} | {row.payload.document_number}</h4>
        <p className="my-2 text-sm">{row.resolution ? "Conflitto risolto" : OUTCOMES[row.outcome]} | CF: {row.payload.tax_code ?? "Assente"}</p>
        <AnomalyLabels values={row.anomalies} />
        <JsonDetails title="Dati originali e normalizzati" value={row.payload} />
        {row.document_id && <button className="btn-secondary mt-3" onClick={() => onSelect(row.document_id!)}>{row.outcome === "conflict" ? "Apri documento esistente da confrontare" : "Apri documento nel registro"}</button>}
        {row.outcome === "conflict" && batch.status === "confirmed" && row.document_id && <ImportConflict token={token} batchId={batch.id} row={row} canEdit={canEdit} onSaved={() => setRevision(revision + 1)} />}
      </article>)}
      <Pagination page={page} total={result.data.total} pageSize={10} onPage={setPage} />
    </>}
  </section>;
}

function BatchContent({ token, batch, canEdit, onRefresh, onSelect }: { token: string; batch: ImportBatch; canEdit: boolean; onRefresh: () => void; onSelect: (id: string) => void }) {
  const [error, setError] = useState<string | null>(null);
  async function download() {
    setError(null);
    try { await downloadImport(token, batch); }
    catch (err) { setError(registerError(err)); }
  }
  return <div className="space-y-5">
    <h3 className="break-all text-xl font-semibold">{batch.filename}</h3>
    <p className="text-sm">{batch.status === "confirmed" ? "Importazione confermata" : "Anteprima: registro non modificato"} | Righe: {batch.summary.rows} | Righe non operative escluse: {batch.summary.ignored_non_operational}</p>
    <ul className="flex flex-wrap gap-3 text-sm">{Object.entries(batch.summary.outcomes).map(([key, count]) => <li key={key}>{OUTCOMES[key]}: {count}</li>)}</ul>
    <p className="break-all text-xs text-gray-600">SHA-256: {batch.digest} | Parser: {batch.parser_version}</p>
    <p className="text-sm">Preparato da utente {batch.actor_id} | {batch.created_at}</p>
    {batch.confirmed_by !== null && <p className="text-sm">Confermato da utente {batch.confirmed_by} | {batch.confirmed_at} | {batch.reason}</p>}
    <button className="btn-secondary" onClick={download}>Scarica originale conservato</button>
    {error && <p role="alert" className="text-rose-800">{error}</p>}
    {canEdit && batch.status === "preview" && <ConfirmImport token={token} batch={batch} onSaved={onRefresh} />}
    <p className="text-xs text-gray-600">I conteggi descrivono l&apos;esito originale dell&apos;importazione. Usa il filtro per distinguere i conflitti aperti dai risolti.</p>
    <ImportRows key={`${batch.id}:${batch.status}`} token={token} batch={batch} canEdit={canEdit} onSelect={onSelect} />
  </div>;
}

export function ImportDetail({ token, batchId, canEdit, onSelect }: { token: string; batchId: string; canEdit: boolean; onSelect: (id: string) => void }) {
  const [revision, setRevision] = useState(0);
  const result = useRegisterResource<ImportBatch>(token, `/importazioni/${batchId}`, revision);
  return <section className={panelClass}>
    <button className="btn-secondary mb-4" onClick={() => setRevision(revision + 1)}>Ricarica importazione</button>
    <ReadState {...result} />{result.data && <BatchContent key={`${batchId}:${revision}`} token={token} batch={result.data} canEdit={canEdit} onSelect={onSelect} onRefresh={() => setRevision(revision + 1)} />}
  </section>;
}
