"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { getNetworkAlerts } from "@/lib/api";
import type { NetworkAlert } from "@/types/api";

function AlertsContent({ token }: { token: string }) {
  const [alerts, setAlerts] = useState<NetworkAlert[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAlerts() {
      try {
        const response = await getNetworkAlerts(token);
        setAlerts(response);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento alert");
      }
    }

    void loadAlerts();
  }, [token]);

  return (
    <div className="page-stack">
      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Alert non disponibili</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      {alerts.map((alert) => (
        <article key={alert.id} className="panel-card">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-gray-900">{alert.title}</p>
              <p className="mt-1 text-sm text-gray-500">{alert.message || "Nessun dettaglio ulteriore."}</p>
            </div>
            <div className="flex items-center gap-2">
              <NetworkStatusBadge status={alert.severity} />
              <NetworkStatusBadge status={alert.status} />
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-gray-400">
            <span>Tipo: {alert.alert_type}</span>
            <span>Creato: {new Date(alert.created_at).toLocaleString("it-IT")}</span>
            {alert.scan_id ? (
              <Link href={`/network/scans/${alert.scan_id}`} className="font-medium text-[#1D4E35]">
                Snapshot #{alert.scan_id}
              </Link>
            ) : null}
          </div>
        </article>
      ))}

      {alerts.length === 0 && !loadError ? (
        <article className="panel-card text-sm text-gray-500">Nessun alert attivo nel modulo rete.</article>
      ) : null}
    </div>
  );
}

export default function NetworkAlertsPage() {
  return (
    <NetworkModulePage
      title="Alert"
      description="Elenco degli eventi aperti generati dalle scansioni di rete."
      breadcrumb="Alert"
    >
      {({ token }) => <AlertsContent token={token} />}
    </NetworkModulePage>
  );
}
