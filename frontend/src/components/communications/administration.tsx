"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ProtectedPage } from "@/components/app/protected-page";
import { communications } from "@/lib/communications-api";
import { useSessionBootstrap } from "@/lib/use-session-bootstrap";
import { AccountAdministration } from "./admin-accounts";
import { TemplateAdministration } from "./admin-templates";

type Monitor = { paused: boolean; transport_enabled: boolean; worker_seen_at: string | null; queues: Record<string, number>; uncertain: number; unmatched_receipts: number };

export function CommunicationsAdministration() {
  const session = useSessionBootstrap();
  if (session.status !== "ready" || !session.token || !session.currentUser) return <p role="status">Verifica accesso...</p>;
  if (!["admin", "super_admin"].includes(session.currentUser.role)) return <p role="alert">Amministrazione non autorizzata.</p>;
  return <ProtectedPage title="GAIA Communications" description="Account, template e monitoraggio dei trasporti." requiredRoles={["admin", "super_admin"]}>
    <Link className="btn-secondary" href="/ruolo/tributi/solleciti/pec">Invio solleciti</Link>
    <Administration token={session.token} />
  </ProtectedPage>;
}

function Administration({ token }: { token: string }) {
  const [monitor, setMonitor] = useState<Monitor | null>(null);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    try { setMonitor(await communications<Monitor>(token, "/admin/monitor")); setError(""); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "Monitoraggio non disponibile"); }
  }, [token]);
  useEffect(() => { void refresh(); const timer = setInterval(() => void refresh(), 10000); return () => clearInterval(timer); }, [refresh]);
  async function pause(paused: boolean) {
    try { await communications(token, "/admin/pause", { paused }); await refresh(); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "Pausa fallita"); }
  }
  return <div className="mt-5 space-y-6">
    <section className="space-y-3 rounded-2xl border bg-white p-5"><h2 className="text-lg font-semibold">Servizio e code</h2>
      {error && <p role="alert" className="text-rose-800">{error}</p>}
      {monitor && <><p>Ultimo heartbeat worker: {monitor.worker_seen_at || "Mai rilevato"}. Trasporto: {monitor.transport_enabled ? "abilitato dalla configurazione di esecuzione" : "disabilitato dalla configurazione di esecuzione"}.</p><p>Invii: {monitor.paused ? "in pausa globale" : "coda attiva"}. Messaggi incerti: {monitor.uncertain}. Ricevute non correlate: {monitor.unmatched_receipts}.</p><dl className="flex flex-wrap gap-4">{Object.entries(monitor.queues).map(([state, count]) => <div key={state}><dt>{state}</dt><dd className="font-semibold">{count}</dd></div>)}</dl><button className="btn-secondary" onClick={() => void pause(!monitor.paused)}>{monitor.paused ? "Riprendi coda invii" : "Pausa globale invii"}</button></>}
      <button className="btn-secondary ml-2" onClick={() => void refresh()}>Aggiorna monitoraggio</button>
      <p className="text-sm text-slate-600">L&apos;heartbeat attesta il processo. La disponibilità SMTP/IMAP compare sui singoli account. La pausa non annulla una trasmissione già iniziata. Il trasporto reale richiede abilitazione separata e autorizzazione operativa.</p>
    </section>
    <AccountAdministration token={token} />
    <TemplateAdministration token={token} />
  </div>;
}
