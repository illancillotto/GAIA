"use client";

import { useState } from "react";
import type { RegisterAttempt, RegisterAudit, RegisterEvidence, RegisterPage } from "@/types/notice-register";
import { JsonDetails, Pagination, panelClass, ReadState } from "./presentation";
import { useRegisterResource } from "./use-register-resource";

type TimelineKind = "evidenze" | "invii" | "storico";
type TimelineEntry = RegisterEvidence | RegisterAttempt | RegisterAudit;

function TimelineItem({ entry }: { entry: TimelineEntry }) {
  if ("action" in entry) return <article className="space-y-2 border-b border-gray-200 py-3">
    <p>Versione {entry.version} | {entry.action} | Operatore #{entry.actor_id}</p><p>{entry.created_at}</p><p>{entry.reason}</p>
    <JsonDetails title="Valori precedenti" value={entry.before_json} /><JsonDetails title="Valori successivi" value={entry.after_json} />
  </article>;
  if ("kind" in entry) return <article className="space-y-2 border-b border-gray-200 py-3">
    <p>{entry.kind} | {entry.occurred_on ?? "Data assente"} | {entry.source_system}</p><p className="break-words">{entry.reference}</p>
    <p className="break-all">ID evidenza per la valutazione: <code>{entry.id}</code></p><JsonDetails title="Evidenza originale" value={entry.original_json} />
  </article>;
  return <article className="space-y-2 border-b border-gray-200 py-3"><p>{entry.channel} | {entry.tracking_code ?? "Tracking assente"}</p><p>{entry.sent_at ?? "Data invio assente"} | {entry.source_system}</p><p>Un invio non e una prova di notifica.</p></article>;
}

function TimelinePage({ token, documentId, kind }: { token: string; documentId: string; kind: TimelineKind }) {
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const resource = useRegisterResource<RegisterPage<TimelineEntry>>(token, `/${documentId}/${kind}?page=${page}&page_size=10`, revision);
  return <div className="mt-3 text-sm">
    <button className="btn-secondary" onClick={() => setRevision(revision + 1)}>Ricarica eventi</button>
    <ReadState loading={resource.loading} error={resource.error} />
    {resource.data && <>
      {resource.data.items.length === 0 && <p className="py-3">Nessun evento registrato.</p>}
      {resource.data.items.map((entry) => <TimelineItem key={entry.id} entry={entry} />)}
      <Pagination page={page} pageSize={10} total={resource.data.total} onPage={setPage} />
    </>}
  </div>;
}

export function RegisterTimeline({ token, documentId }: { token: string; documentId: string }) {
  const [kind, setKind] = useState<TimelineKind>("evidenze");
  return <section aria-label="Eventi del documento" className={panelClass}>
    <h3 className="mb-3 text-lg font-semibold">Evidenze, invii e storico</h3>
    <div className="flex flex-wrap gap-2">{(["evidenze", "invii", "storico"] as const).map((value) => <button key={value} className="btn-secondary" aria-pressed={kind === value} onClick={() => setKind(value)}>{value}</button>)}</div>
    <TimelinePage key={kind} token={token} documentId={documentId} kind={kind} />
  </section>;
}
