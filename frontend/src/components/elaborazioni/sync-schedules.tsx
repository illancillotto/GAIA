"use client";

import { useEffect, useState } from "react";
import { getElaborazioneAutoJobControls, updateElaborazioneAutoJobControl } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { syncError } from "@/lib/sync-dashboard-model";
import type { ElaborazioneAutoJobControl } from "@/types/api";

export function SyncSchedules({ onOpen }: { onOpen: (href: string, title: string) => void }) {
  const [controls, setControls] = useState<ElaborazioneAutoJobControl[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    let mounted = true;
    void getElaborazioneAutoJobControls(token).then((items) => {
      if (mounted) setControls(items);
    }).catch((cause: unknown) => { if (mounted) setError(syncError(cause)); });
    return () => { mounted = false; };
  }, []);
  async function toggle(control: ElaborazioneAutoJobControl) {
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(control.key);
    try {
      await updateElaborazioneAutoJobControl(token, control.key, { enabled: !control.enabled });
      setControls(await getElaborazioneAutoJobControls(token));
      setError(null);
    } catch (cause) { setError(syncError(cause)); }
    finally { setBusy(null); }
  }
  return (
    <section aria-label="Pianificazioni automatiche" className="rounded-[24px] border border-[#d9dfd6] bg-white p-5 sm:p-6">
      <h2 className="text-xl font-semibold text-[#163524]">Pianificazioni automatiche</h2>
      <p className="mt-1 text-sm text-stone-500">Scegli quali sincronizzazioni eseguire automaticamente. Disattivare una pianificazione interrompe gli avvii automatici successivi.</p>
      {error ? <p role="alert" className="mt-4 break-words text-sm text-amber-800">{error}</p> : null}
      <div className="mt-5 grid gap-3 lg:grid-cols-2">
        {controls.map((control) => (
          <article key={control.key} className="flex flex-col rounded-2xl border border-stone-200 p-4">
            <div className="flex items-start justify-between gap-3">
              <h3 className="font-semibold text-stone-800">{control.label}</h3>
              <span className="text-xs font-semibold text-stone-600">{control.enabled ? "Attivo" : "Disattivato"}</span>
            </div>
            <p className="mt-2 text-sm text-stone-500">{control.description}</p>
            <p className="mt-2 text-sm text-stone-700">{control.detail ?? "Pianificazione non disponibile"}</p>
            <div className="mt-auto flex flex-wrap items-center gap-3 pt-4">
              <button type="button" className="btn-secondary" disabled={busy !== null} onClick={() => void toggle(control)}>
                {busy === control.key ? "Aggiornamento..." : control.enabled ? "Disattiva" : "Attiva"}
              </button>
              {control.management_href ? <button type="button" className="btn-secondary" aria-haspopup="dialog" onClick={() => onOpen(control.management_href!, control.label)}>Configura</button> : null}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
