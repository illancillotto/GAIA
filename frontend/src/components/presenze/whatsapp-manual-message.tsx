"use client";

import { useRef, useState } from "react";
import { useSessionBootstrap } from "@/lib/use-session-bootstrap";
import { previewManualWhatsApp, sendManualWhatsApp, type ManualWhatsAppPreview } from "@/lib/api/presenze-whatsapp-manual";
import { recoverablePhoneContact, WhatsAppPhoneRecovery } from "./whatsapp-phone-recovery";

const OUTCOMES: Record<string, string> = {
  SENT: "Messaggio inviato. Consegna e lettura sono consultabili nello storico WhatsApp.",
  DRY_RUN: "Simulazione registrata: nessun messaggio reale inviato.",
  FAILED: "Invio fallito. Controlla lo storico WhatsApp prima di riprovare.",
  UNKNOWN: "Esito incerto: non ripetere l'invio. Verifica lo storico WhatsApp.",
};

export function WhatsAppManualMessage({ recordId }: { recordId: string }) {
  const session = useSessionBootstrap();
  if (!session.token || !["admin", "super_admin"].includes(session.currentUser?.role ?? "")) return null;
  return <ManualMessageForm key={recordId} recordId={recordId} token={session.token} />;
}

export function ManualMessageForm({ recordId, token }: { recordId: string; token: string }) {
  const [preview, setPreview] = useState<ManualWhatsAppPreview | null>(null);
  const [reason, setReason] = useState("");
  const [allowOutsideWindow, setAllowOutsideWindow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [phoneContact, setPhoneContact] = useState<ReturnType<typeof recoverablePhoneContact>>(null);
  const pending = useRef(false);

  async function openPreview() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setNotice("");
    setAllowOutsideWindow(false);
    setPhoneContact(null);
    try {
      const result = await previewManualWhatsApp(token, recordId);
      setPreview(result);
      setReason(result.reason);
    } catch (error) {
      setPhoneContact(recoverablePhoneContact(error));
      setNotice(error instanceof Error ? error.message : "Anteprima non disponibile");
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }

  async function confirmSend() {
    if (pending.current || !preview) return;
    pending.current = true;
    setBusy(true);
    try {
      const result = await sendManualWhatsApp(token, preview, reason.trim(), allowOutsideWindow);
      setNotice(OUTCOMES[result.status] ?? "Esito da verificare nello storico WhatsApp.");
    } catch (error) {
      setNotice(error instanceof Error ? `${error.message}. Verifica lo storico prima di riprovare.` : "Esito da verificare nello storico WhatsApp.");
    } finally {
      setPreview(null);
      pending.current = false;
      setBusy(false);
    }
  }

  return <section className="mt-4 rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sky-950" aria-label="Messaggio manuale WhatsApp">
    <h3 className="text-sm font-semibold">Segnala l&apos;anomalia al collaboratore</h3>
    <p className="mt-1 text-xs">Solo questa giornata. Verifica il motivo e le indicazioni per correggerla su INAZ.</p>
    {!preview ? <button type="button" className="btn-secondary mt-3" disabled={busy} onClick={() => void openPreview()}>Prepara messaggio WhatsApp</button> : <>
      <p className="mt-3 text-sm">{preview.collaborator_name} · {preview.phone_e164} · {preview.work_date}</p>
      {preview.provider === "dry_run" ? <p className="mt-2 font-semibold">Modalità di prova: non verrà inviato un messaggio reale.</p> : null}
      <label className="mt-3 block text-sm">Motivo dell&apos;anomalia
        <textarea className="mt-1 w-full rounded-lg border p-2 text-slate-900" value={reason} maxLength={1500} rows={3} disabled={busy} onChange={(event) => setReason(event.target.value)} />
      </label>
      <p className="text-xs">Descrivi cosa deve verificare, senza inserire dati sanitari o altri dettagli sensibili.</p>
      <pre className="mt-3 whitespace-pre-wrap break-words rounded-lg bg-white p-3 font-sans text-sm" aria-label="Anteprima messaggio">{preview.text.replace(`\n${preview.reason}\n`, () => `\n${reason.trim()}\n`)}</pre>
      <div className="mt-3 flex flex-wrap gap-2">
        <label className="flex w-full items-start gap-2 text-sm">
          <input type="checkbox" checked={allowOutsideWindow} disabled={busy} onChange={(event) => setAllowOutsideWindow(event.target.checked)} />
          Invia anche fuori fascia oraria e nel weekend (solo questo messaggio)
        </label>
        <button type="button" className="btn-primary" disabled={busy || reason.trim().length < 5} onClick={() => void confirmSend()}>{preview.provider === "dry_run" ? "Conferma simulazione" : "Conferma e invia WhatsApp"}</button>
        <button type="button" className="btn-secondary" disabled={busy} onClick={() => setPreview(null)}>Annulla</button>
      </div>
    </>}
    {notice ? <p className="mt-3 text-sm" role="status">{notice}</p> : null}
    <WhatsAppPhoneRecovery contact={phoneContact} token={token} onSaved={openPreview} />
  </section>;
}
