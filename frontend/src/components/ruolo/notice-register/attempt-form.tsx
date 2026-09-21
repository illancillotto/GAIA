"use client";

import { MutationForm, type MutationContext } from "./mutation-form";
import { Field, inputClass } from "./presentation";

function attemptPayload(form: FormData) {
  return {
    channel: String(form.get("channel")),
    tracking_code: String(form.get("tracking_code")).trim() || null,
    sent_at: new Date(String(form.get("sent_at"))).toISOString(),
    evidence_reference: String(form.get("evidence_reference")).trim(),
    confirmed: form.get("confirmed") === "on",
  };
}

export function AttemptForm({ documentId, context }: { documentId: string; context: MutationContext }) {
  return <details className="space-y-3">
    <summary className="cursor-pointer font-medium">Registra invio gia effettuato</summary>
    <MutationForm {...context} path={`/${documentId}/invii`} method="POST" title="Invio gia effettuato" buildData={attemptPayload}>
      <p className="text-sm text-gray-600 sm:col-span-2">Solo registrazione storica: GAIA non spedisce nulla. Il tentativo non prova la notifica; la valutazione torna da verificare e quella precedente resta nello storico. Prima di salvare controlla gli invii gia presenti, inclusi quelli importati da Poste.</p>
      <Field label="Canale"><select className={inputClass} name="channel" defaultValue="posta"><option value="posta">Posta</option><option value="pec">PEC</option><option value="messo">Messo notificatore</option><option value="altro">Altro</option></select></Field>
      <Field label="Tracking o protocollo (facoltativo)"><input className={inputClass} name="tracking_code" maxLength={100} /></Field>
      <Field label="Data e ora invio (ora locale)"><input className={inputClass} name="sent_at" type="datetime-local" required /></Field>
      <Field label="Riferimento evidenza dell'invio"><input className={inputClass} name="evidence_reference" required /></Field>
      <label className="flex items-start gap-2 text-sm sm:col-span-2"><input type="checkbox" name="confirmed" required />Confermo che l&apos;invio e gia avvenuto e ho controllato gli eventi esistenti.</label>
    </MutationForm>
  </details>;
}
