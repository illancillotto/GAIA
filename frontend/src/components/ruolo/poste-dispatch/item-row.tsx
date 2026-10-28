"use client";

import { useState } from "react";

import {
  acceptPosteManualAddress,
  cancelPosteItem,
  getPosteItemDocument,
  updatePosteRecipient,
} from "@/lib/ruolo-poste-dispatch-api";
import type { PosteDispatchItem, PosteDispatchRecipient } from "@/types/ruolo-poste-dispatch";
import { STATUS_TONES, errorMessage, euro, statusLabel } from "./labels";

const EDITABLE = ["address_pending", "address_review", "address_ok", "draft_error", "draft_missing"];
const CANCELLABLE = [...EDITABLE, "draft_created", "draft_priced", "draft_uncertain"];
const FIELDS: { key: keyof PosteDispatchRecipient; label: string }[] = [
  { key: "name", label: "Nominativo" },
  { key: "name_extra", label: "Seconda riga nominativo" },
  { key: "address", label: "Indirizzo" },
  { key: "cap", label: "CAP" },
  { key: "city", label: "Comune" },
  { key: "province", label: "Provincia" },
];

type Props = { token: string; lotId: string; item: PosteDispatchItem; canEdit: boolean; onChanged: () => void };

function RecipientEditor({ token, lotId, item, onChanged, onClose }: Omit<Props, "canEdit"> & { onClose: () => void }) {
  const [draft, setDraft] = useState<PosteDispatchRecipient>(item.recipient);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    try {
      await updatePosteRecipient(token, lotId, item.id, draft);
      onClose();
      onChanged();
    } catch (err) {
      setError(errorMessage(err, "Destinatario non salvato"));
    }
  }

  return <div className="mt-3 grid gap-2 sm:grid-cols-2">
    {FIELDS.map((field) => <label key={field.key} className="text-xs text-slate-600">{field.label}
      <input className="form-control w-full" value={draft[field.key]} onChange={(event) => setDraft({ ...draft, [field.key]: event.target.value })} />
    </label>)}
    {error && <p role="alert" className="text-sm text-rose-800 sm:col-span-2">{error}</p>}
    <div className="flex gap-2 sm:col-span-2">
      <button type="button" className="btn-primary" onClick={() => void save()}>Salva e riverifica</button>
      <button type="button" className="btn-secondary" onClick={onClose}>Chiudi</button>
    </div>
  </div>;
}

function ItemSummary({ item }: { item: PosteDispatchItem }) {
  const { recipient } = item;
  const tracking = item.tracking_number ? ` · raccomandata ${item.tracking_number}` : "";
  return <div className="flex flex-wrap items-start justify-between gap-2">
    <div>
      <p className="font-semibold text-slate-900">{recipient.name} {recipient.name_extra}</p>
      <p className="text-slate-600">{recipient.address}, {recipient.cap} {recipient.city} {recipient.province}</p>
      <p className="text-xs text-slate-500">{item.shipment_name} · bozza {item.poste_draft_id || "-"} · {euro(item.price_amount)}{tracking}</p>
    </div>
    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${STATUS_TONES[item.status] ?? "bg-slate-100 text-slate-700"}`}>{statusLabel(item.status)}</span>
  </div>;
}

function ItemNotes({ item }: { item: PosteDispatchItem }) {
  const review = item.address_review;
  const problems = review?.problems?.length ? `: ${review.problems.join(", ")}` : "";
  return <>
    {review?.reason && <p className="mt-2 text-amber-900">{review.reason}{problems}</p>}
    {review?.suggestions?.length ? <p className="mt-1 text-xs text-slate-600">Proposte Poste: {review.suggestions.join(" | ")}</p> : null}
    {item.error_detail && <p className="mt-2 text-rose-800">{item.error_detail}</p>}
  </>;
}

type Actions = { openDocument: () => void; edit: () => void; manual: () => void; cancel: () => void };

function ItemActions({ status, canEdit, actions }: { status: string; canEdit: boolean; actions: Actions }) {
  return <div className="mt-3 flex flex-wrap gap-2">
    {status !== "sent" && status !== "cancelled" && <button type="button" className="btn-secondary" onClick={actions.openDocument}>Apri PDF</button>}
    {canEdit && EDITABLE.includes(status) && <button type="button" className="btn-secondary" onClick={actions.edit}>Correggi destinatario</button>}
    {canEdit && status === "address_review" && <button type="button" className="btn-secondary" onClick={actions.manual}>Usa indirizzo manuale</button>}
    {canEdit && CANCELLABLE.includes(status) && <button type="button" className="btn-secondary" onClick={actions.cancel}>Annulla</button>}
  </div>;
}

export function ItemRow({ token, lotId, item, canEdit, onChanged }: Props) {
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function act(action: () => Promise<unknown>, fallback: string) {
    setError(null);
    try {
      await action();
      onChanged();
    } catch (err) {
      setError(errorMessage(err, fallback));
    }
  }

  const actions: Actions = {
    openDocument: () => void act(async () => window.open(URL.createObjectURL(await getPosteItemDocument(token, lotId, item.id)), "_blank", "noopener"), "PDF non disponibile"),
    edit: () => setEditing(!editing),
    manual: () => void act(() => acceptPosteManualAddress(token, lotId, item.id), "Indirizzo non accettato"),
    cancel: () => void act(() => cancelPosteItem(token, lotId, item.id), "Annullamento non riuscito"),
  };

  return <li className="rounded-2xl border border-slate-200 p-4 text-sm">
    <ItemSummary item={item} />
    <ItemNotes item={item} />
    {error && <p role="alert" className="mt-2 text-rose-800">{error}</p>}
    <ItemActions status={item.status} canEdit={canEdit} actions={actions} />
    {editing && <RecipientEditor token={token} lotId={lotId} item={item} onChanged={onChanged} onClose={() => setEditing(false)} />}
  </li>;
}
