"use client";

import Image from "next/image";
import { useCallback, useEffect, useState } from "react";

import {
  getPresenzeWhatsAppQr,
  getPresenzeWhatsAppSession,
  logoutPresenzeWhatsAppSession,
  startPresenzeWhatsAppSession,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { PresenzeWhatsAppSession } from "@/types/api";

import { whatsappSessionLabel } from "./whatsapp-ui";

const QR_STATUSES = new Set(["starting", "scan_qr_code"]);

export function WhatsAppSessionManager() {
  const [open, setOpen] = useState(false);
  const [session, setSession] = useState<PresenzeWhatsAppSession | null>(null);
  const [qr, setQr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      const current = await getPresenzeWhatsAppSession(token);
      setSession(current);
      if (QR_STATUSES.has(current.status)) {
        try {
          setQr((await getPresenzeWhatsAppQr(token)).image_data_url);
        } catch {
          setQr(null);
        }
      } else {
        setQr(null);
      }
      setError(null);
    } catch (reason) {
      setError(errorMessage(reason, "Impossibile leggere la sessione WAHA"));
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    void refresh();
    const timer = window.setInterval(refresh, 3000);
    return () => window.clearInterval(timer);
  }, [open, refresh]);

  async function start() {
    await runAction(startPresenzeWhatsAppSession, "Impossibile avviare la sessione WAHA");
  }

  async function logout() {
    if (!window.confirm("Disconnettere il numero WhatsApp da GAIA?")) return;
    await runAction(logoutPresenzeWhatsAppSession, "Impossibile disconnettere la sessione WAHA");
  }

  async function runAction(
    action: (token: string) => Promise<PresenzeWhatsAppSession>,
    fallback: string,
  ) {
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(true);
    try {
      setSession(await action(token));
      setError(null);
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason, fallback));
    } finally {
      setBusy(false);
    }
  }

  return (
    <SessionManagerCard
      open={open}
      session={session}
      qr={qr}
      busy={busy}
      error={error}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      onRefresh={() => void refresh()}
      onStart={() => void start()}
      onLogout={() => void logout()}
    />
  );
}

type ManagerCardProps = DialogProps & { open: boolean; onOpen: () => void };

function SessionManagerCard(props: ManagerCardProps) {
  return (
    <section className="rounded-[28px] border border-sky-900/15 bg-gradient-to-br from-white to-sky-50 p-5 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-700">Solo super admin</p>
          <h2 className="mt-1 text-xl font-semibold">Numero WhatsApp</h2>
          <p className="mt-1 text-sm text-slate-500">Associa il telefono e controlla la sessione senza uscire da GAIA.</p>
        </div>
        <button className="btn-secondary" type="button" onClick={props.onOpen}>
          Gestisci collegamento
        </button>
      </div>
      {props.open ? <SessionDialog {...props} /> : null}
    </section>
  );
}

type DialogProps = {
  session: PresenzeWhatsAppSession | null;
  qr: string | null;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onRefresh: () => void;
  onStart: () => void;
  onLogout: () => void;
};

export function SessionDialog(props: DialogProps) {
  const connected = props.session?.status === "working";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-3 sm:p-6" role="dialog" aria-modal="true" aria-labelledby="whatsapp-session-title">
      <div className="w-full max-w-4xl overflow-hidden rounded-[32px] bg-[#f7fafc] shadow-2xl">
        <header className="flex items-start justify-between border-b border-slate-200 bg-white px-5 py-4 sm:px-8">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-700">Collegamento protetto</p>
            <h2 id="whatsapp-session-title" className="mt-1 text-2xl font-semibold">Associa WhatsApp a GAIA</h2>
            <p className="mt-1 text-sm text-slate-500">Il QR e le credenziali restano all&apos;interno dell&apos;infrastruttura GAIA.</p>
          </div>
          <button className="btn-secondary" type="button" onClick={props.onClose}>Chiudi</button>
        </header>
        <div className="grid gap-6 p-5 sm:p-8 md:grid-cols-[0.85fr_1.15fr]">
          <div className="rounded-3xl border border-slate-200 bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Stato sessione</p>
            <p className="mt-2 text-2xl font-semibold text-slate-950">{whatsappSessionLabel(props.session?.status)}</p>
            {props.session?.display_name || props.session?.phone ? (
              <div className="mt-4 rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-950">
                <p className="font-semibold">{props.session.display_name ?? "Numero collegato"}</p>
                <p className="mt-1">{props.session.phone ? `+${props.session.phone}` : "Telefono disponibile"}</p>
              </div>
            ) : null}
            {props.error ? <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700" role="alert">{props.error}</p> : null}
            <div className="mt-5 flex flex-wrap gap-3">
              {connected ? (
                <button className="btn-secondary border-rose-200 text-rose-700" type="button" disabled={props.busy} onClick={props.onLogout}>Disconnetti numero</button>
              ) : (
                <button className="btn-primary" type="button" disabled={props.busy} onClick={props.onStart}>{props.busy ? "Avvio..." : "Avvia e genera QR"}</button>
              )}
              <button className="btn-secondary" type="button" disabled={props.busy} onClick={props.onRefresh}>Aggiorna stato</button>
            </div>
          </div>
          <div className="flex min-h-[360px] items-center justify-center rounded-3xl border border-sky-200 bg-white p-5 text-center">
            {props.qr ? (
              <div>
                <Image className="mx-auto h-72 w-72 max-w-full" src={props.qr} width={288} height={288} unoptimized alt="QR per associare WhatsApp a GAIA" />
                <p className="mt-4 text-sm font-medium text-slate-700">WhatsApp → Dispositivi collegati → Collega un dispositivo</p>
              </div>
            ) : connected ? (
              <div><p className="text-5xl text-emerald-600">✓</p><p className="mt-4 font-semibold text-emerald-900">Numero collegato correttamente</p></div>
            ) : (
              <div><p className="text-lg font-semibold text-slate-800">QR non ancora disponibile</p><p className="mt-2 text-sm text-slate-500">Avvia la sessione. GAIA aggiornerà automaticamente questa schermata.</p></div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}
