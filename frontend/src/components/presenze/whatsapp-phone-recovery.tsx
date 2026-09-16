"use client";

import { useRef, useState } from "react";
import { ApiError } from "@/lib/api/core";
import { updatePresenzeWhatsAppPhone } from "@/lib/api/presenze-whatsapp";

type PhoneContact = { application_user_id: number; collaborator_name: string };

export function recoverablePhoneContact(error: unknown): PhoneContact | null {
  if (!(error instanceof ApiError)) return null;
  const detail = error.detailData as Partial<PhoneContact> & { code?: string } | null;
  if (!detail || !["operator_profile_missing", "phone_missing", "phone_invalid"].includes(detail.code ?? "")) return null;
  if (typeof detail.application_user_id !== "number" || typeof detail.collaborator_name !== "string") return null;
  return { application_user_id: detail.application_user_id, collaborator_name: detail.collaborator_name };
}

export function WhatsAppPhoneRecovery({ contact, token, onSaved }: { contact: PhoneContact | null; token: string; onSaved: () => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(false);

  async function save() {
    if (pending.current || !contact) return;
    const normalized = phone.replace(/[\s().-]/g, "").replace(/^00/, "+");
    if (!/^\+?[1-9]\d{7,14}$/.test(normalized)) {
      setError("Inserisci un numero valido, con prefisso internazionale (es. +39).");
      return;
    }
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      await updatePresenzeWhatsAppPhone(token, contact.application_user_id, normalized);
      await onSaved();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Salvataggio del numero non riuscito");
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }

  if (!contact) return null;
  if (!editing) return <button type="button" className="btn-secondary mt-3" onClick={() => setEditing(true)}>Aggiungi numero WhatsApp</button>;
  return <div className="mt-3 rounded-lg border border-sky-200 bg-white p-3">
    <p className="text-sm">Numero WhatsApp di {contact.collaborator_name}</p>
    <label className="mt-2 block text-sm">Telefono del collaboratore
      <input type="tel" autoComplete="tel" className="mt-1 block w-full rounded-lg border p-2 text-slate-900" placeholder="+39 333 1234567" maxLength={50} value={phone} disabled={busy} onChange={(event) => setPhone(event.target.value)} />
    </label>
    <p className="mt-2 text-xs">Il numero viene salvato nel profilo del collaboratore. Il salvataggio non invia messaggi.</p>
    {error ? <p role="alert" className="mt-2 text-sm text-rose-700">{error}</p> : null}
    <div className="mt-3 flex flex-wrap gap-2">
      <button type="button" className="btn-primary" disabled={busy || !phone.trim()} onClick={() => void save()}>Salva numero e prepara messaggio</button>
      <button type="button" className="btn-secondary" disabled={busy} onClick={() => setEditing(false)}>Annulla</button>
    </div>
  </div>;
}
