"use client";

import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { usePolling } from "@/hooks/use-polling";
import { ApiError, request } from "@/lib/api/core";
import { useSessionBootstrap } from "@/lib/use-session-bootstrap";

type SyncAlert = { id: string; service: string; message: string };

function SyncAlertMonitor({ token }: { token: string }) {
  const [alerts, setAlerts] = useState<SyncAlert[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const mounted = useRef(false);
  const busy = useRef(false);
  const refresh = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      const result = await request<SyncAlert[]>("/elaborazioni/sync-alerts", {
        headers: { Authorization: `Bearer ${token}` }, timeoutMs: 15000,
      });
      if (!mounted.current) return;
      setAlerts(result);
      setDismissed((current) => new Set([...current].filter((id) => result.some((alert) => alert.id === id))));
    } catch (error) {
      if (!mounted.current) return;
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        setAlerts([]);
        return;
      }
      setAlerts((current) => [
        ...current.filter((alert) => alert.id !== "monitor-unavailable"),
        { id: "monitor-unavailable", service: "Monitor sincronizzazioni", message: "Stato non disponibile. Nuovo controllo automatico tra 30 secondi." },
      ]);
    } finally {
      busy.current = false;
    }
  }, [token]);
  useEffect(() => {
    mounted.current = true;
    void refresh();
    return () => { mounted.current = false; };
  }, [refresh]);
  usePolling(refresh, { enabled: true, intervalMs: 30000 });

  const visible = alerts.filter((alert) => !dismissed.has(alert.id));
  if (!visible.length) return null;
  return (
    <aside role="alert" aria-label="Avvisi sincronizzazioni" className="fixed bottom-24 right-4 z-[130] max-h-[60vh] w-[calc(100%-2rem)] max-w-md overflow-y-auto rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950 shadow-xl">
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-semibold">Sincronizzazioni da verificare</h2>
        <button type="button" aria-label="Chiudi avvisi sincronizzazioni" onClick={() => setDismissed(new Set(alerts.map((alert) => alert.id)))} className="rounded px-2 py-1 text-sm focus-visible:outline focus-visible:outline-2">Chiudi</button>
      </div>
      <ul className="mt-2 space-y-2 text-sm">
        {visible.map((alert) => <li key={alert.id}><strong>{alert.service}</strong>: {alert.message}</li>)}
      </ul>
    </aside>
  );
}

function SessionSyncAlerts() {
  const session = useSessionBootstrap();
  if (session.status !== "ready" || !session.token || !session.currentUser) return null;
  if (!["admin", "super_admin"].includes(session.currentUser.role)) return null;
  return <SyncAlertMonitor key={session.token} token={session.token} />;
}

export function HomeSyncAlerts() {
  const pathname = usePathname();
  return pathname === "/" ? <SessionSyncAlerts /> : null;
}
