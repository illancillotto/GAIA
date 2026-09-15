"use client";

import { useState } from "react";

import type { PresenzeWhatsAppMessage, PresenzeWhatsAppOptOut, PresenzeWhatsAppPreview } from "@/types/api";

import { formatWhatsAppDateTime, whatsappSkipLabel, whatsappStatusLabel, whatsappStatusTone } from "./whatsapp-ui";

type MessageDialogProps = {
  message: PresenzeWhatsAppMessage;
  busy: boolean;
  onClose: () => void;
  onReconcile: (sent: boolean, evidence: string, providerMessageId: string) => Promise<void>;
};

export function WhatsAppMessageDialog({ message, busy, onClose, onReconcile }: MessageDialogProps) {
  const [evidence, setEvidence] = useState("");
  const [providerMessageId, setProviderMessageId] = useState(message.provider_message_id ?? "");
  const uncertain = message.status === "SENDING" || message.status === "UNKNOWN";

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/55 p-2 backdrop-blur-sm sm:p-5" role="dialog" aria-modal="true" aria-labelledby="whatsapp-message-title">
      <button className="absolute inset-0 cursor-default" aria-label="Chiudi dettaglio messaggio" onClick={onClose} type="button" />
      <article className="relative flex h-[min(94vh,960px)] w-[min(98vw,112rem)] flex-col overflow-hidden rounded-[28px] border border-white/30 bg-[#fbfcf8] shadow-2xl">
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-5 sm:px-8">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-emerald-700">Tracciamento invio</p>
            <h2 id="whatsapp-message-title" className="mt-1 text-2xl font-semibold text-slate-950">{message.user_label}</h2>
            <p className="mt-1 text-sm text-slate-500">{message.username ? `@${message.username} · ` : ""}{message.phone_e164}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`rounded-full px-3 py-1.5 text-xs font-bold ring-1 ${whatsappStatusTone(message.status)}`}>{whatsappStatusLabel(message.status)}</span>
            <button className="btn-secondary" type="button" onClick={onClose}>Chiudi</button>
          </div>
        </header>
        <div className="grid min-h-0 flex-1 gap-5 overflow-y-auto p-5 sm:p-8 xl:grid-cols-[1.15fr_0.85fr]">
          <section className="rounded-3xl border border-slate-200 bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">Messaggio inviato</p>
            <p className="mt-4 whitespace-pre-wrap rounded-2xl bg-[#eef7ef] p-5 text-sm leading-7 text-slate-800">{message.text_body}</p>
            <div className="mt-5 space-y-2">
              {message.days.map((day) => (
                <div className="flex flex-wrap justify-between gap-2 rounded-2xl border border-slate-100 px-4 py-3" key={`${day.work_date}-${day.problem}`}>
                  <span className="font-semibold text-slate-800">{new Date(`${day.work_date}T12:00:00`).toLocaleDateString("it-IT")}</span>
                  <span className="text-sm text-slate-500">{day.detail}</span>
                </div>
              ))}
            </div>
          </section>
          <aside className="space-y-5">
            <section className="rounded-3xl border border-slate-200 bg-white p-5">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">Linea temporale</p>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <div><dt className="text-slate-400">Creato</dt><dd className="font-semibold text-slate-800">{formatWhatsAppDateTime(message.created_at)}</dd></div>
                <div><dt className="text-slate-400">Aggiornato</dt><dd className="font-semibold text-slate-800">{formatWhatsAppDateTime(message.updated_at)}</dd></div>
                <div><dt className="text-slate-400">Consegnato</dt><dd className="font-semibold text-slate-800">{formatWhatsAppDateTime(message.delivered_at)}</dd></div>
                <div><dt className="text-slate-400">Letto</dt><dd className="font-semibold text-slate-800">{formatWhatsAppDateTime(message.read_at)}</dd></div>
              </dl>
              <p className="mt-4 break-all text-xs text-slate-400">ID provider: {message.provider_message_id ?? "non disponibile"}</p>
            </section>
            {message.error_message ? (
              <section className="rounded-3xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
                <p className="font-bold">{message.error_code ?? "Errore invio"}</p>
                <p className="mt-2">{message.error_message}</p>
              </section>
            ) : null}
            {uncertain ? (
              <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5">
                <h3 className="font-semibold text-amber-950">Riconciliazione manuale</h3>
                <p className="mt-1 text-sm text-amber-800">Verifica il messaggio in WAHA e documenta l’esito. Questa azione non invia nuovamente il testo.</p>
                <textarea className="field mt-4 min-h-24 w-full" value={evidence} onChange={(event) => setEvidence(event.target.value)} placeholder="Evidenza della verifica" />
                <input className="field mt-3 w-full" value={providerMessageId} onChange={(event) => setProviderMessageId(event.target.value)} placeholder="ID messaggio WAHA, se inviato" />
                <div className="mt-4 flex flex-wrap gap-2">
                  <button className="btn-primary" disabled={busy || !evidence.trim() || !providerMessageId.trim()} type="button" onClick={() => void onReconcile(true, evidence, providerMessageId)}>Conferma inviato</button>
                  <button className="btn-secondary" disabled={busy || !evidence.trim()} type="button" onClick={() => void onReconcile(false, evidence, "")}>Segna non inviato</button>
                </div>
              </section>
            ) : null}
          </aside>
        </div>
      </article>
    </div>
  );
}

type PreviewDialogProps = {
  preview: PresenzeWhatsAppPreview;
  optOuts: PresenzeWhatsAppOptOut[];
  onClose: () => void;
  onRestore: (userId: number) => Promise<void>;
  onUpdatePhone: (userId: number, phone: string) => Promise<void>;
};

export function WhatsAppPreviewDialog({ preview, optOuts, onClose, onRestore, onUpdatePhone }: PreviewDialogProps) {
  const [phoneByUser, setPhoneByUser] = useState<Record<number, string>>({});
  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/55 p-2 backdrop-blur-sm sm:p-5" role="dialog" aria-modal="true" aria-labelledby="whatsapp-preview-title">
      <article className="flex h-[min(94vh,960px)] w-[min(98vw,112rem)] flex-col overflow-hidden rounded-[28px] bg-[#fbfcf8] shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-5 sm:px-8">
          <div><p className="text-xs font-bold uppercase tracking-[0.22em] text-emerald-700">Anteprima senza invio</p><h2 id="whatsapp-preview-title" className="mt-1 text-2xl font-semibold">Prossimi promemoria</h2></div>
          <button className="btn-secondary" type="button" onClick={onClose}>Chiudi</button>
        </header>
        <div className="grid min-h-0 flex-1 gap-5 overflow-y-auto p-5 sm:p-8 xl:grid-cols-2">
          <section><h3 className="text-lg font-semibold">Pronti <span className="text-emerald-700">{preview.ready.length}</span></h3><div className="mt-3 space-y-3">{preview.ready.length ? preview.ready.map((item) => <article className="rounded-3xl border border-emerald-200 bg-white p-5" key={item.collaborator_id}><div className="flex justify-between gap-3"><strong>{item.collaborator_name}</strong><span className="text-sm text-slate-500">{item.phone_e164}</span></div><p className="mt-3 whitespace-pre-wrap rounded-2xl bg-emerald-50 p-4 text-sm leading-6">{item.message_text}</p></article>) : <p className="rounded-3xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">Nessun promemoria pronto in questo momento.</p>}</div></section>
          <section className="space-y-6"><div><h3 className="text-lg font-semibold">Da sistemare <span className="text-amber-700">{preview.skipped.length}</span></h3><div className="mt-3 space-y-3">{preview.skipped.map((item) => <article className="rounded-3xl border border-amber-200 bg-white p-5" key={item.collaborator_id}><strong>{item.collaborator_name}</strong><p className="mt-1 text-sm text-amber-800">{whatsappSkipLabel(item.reason)}</p>{item.application_user_id && (item.reason === "phone_missing" || item.reason === "phone_invalid") ? <div className="mt-3 flex gap-2"><input className="field min-w-0 flex-1" value={phoneByUser[item.application_user_id] ?? ""} onChange={(event) => setPhoneByUser((current) => ({ ...current, [item.application_user_id!]: event.target.value }))} placeholder="+39 333 1234567" /><button className="btn-secondary" type="button" onClick={() => void onUpdatePhone(item.application_user_id!, phoneByUser[item.application_user_id!] ?? "")}>Salva</button></div> : null}</article>)}</div></div>
            <div><h3 className="text-lg font-semibold">Utenti che hanno risposto STOP <span className="text-rose-700">{optOuts.length}</span></h3><div className="mt-3 space-y-3">{optOuts.map((item) => <article className="flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-rose-200 bg-white p-5" key={item.application_user_id}><div><strong>{item.user_label}</strong><p className="text-sm text-slate-500">{item.phone_e164 ?? "Numero non registrato"} · {formatWhatsAppDateTime(item.created_at)}</p></div><button className="btn-secondary" type="button" onClick={() => void onRestore(item.application_user_id)}>Riattiva promemoria</button></article>)}</div></div>
          </section>
        </div>
      </article>
    </div>
  );
}
