"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { getNetworkScans, triggerNetworkScan } from "@/lib/api";
import type { NetworkScan } from "@/types/api";

function ScansContent({ token }: { token: string }) {
  const [scans, setScans] = useState<NetworkScan[]>([]);
  const [isTriggeringScan, setIsTriggeringScan] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  async function loadScans() {
    try {
      const response = await getNetworkScans(token);
      setScans(response);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento scansioni");
    }
  }

  useEffect(() => {
    void loadScans();
  }, [token]);

  async function handleTriggerScan() {
    setIsTriggeringScan(true);
    try {
      await triggerNetworkScan(token);
      await loadScans();
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore durante l’avvio della scansione");
    } finally {
      setIsTriggeringScan(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="flex justify-end">
        <button className="btn-primary" onClick={handleTriggerScan} type="button" disabled={isTriggeringScan}>
          {isTriggeringScan ? "Scansione in corso" : "Nuova scansione"}
        </button>
      </div>

      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Storico non disponibile</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      {scans.map((scan) => (
        <article key={scan.id} className="panel-card">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-gray-900">Snapshot #{scan.id}</p>
              <p className="mt-1 text-sm text-gray-500">
                Range {scan.network_range} · {scan.scan_type}
              </p>
            </div>
            <NetworkStatusBadge status={scan.status} />
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-4">
            <div>
              <p className="label-caption">Host scanditi</p>
              <p className="mt-1 text-sm text-gray-800">{scan.hosts_scanned}</p>
            </div>
            <div>
              <p className="label-caption">Host attivi</p>
              <p className="mt-1 text-sm text-gray-800">{scan.active_hosts}</p>
            </div>
            <div>
              <p className="label-caption">Dispositivi aggiornati</p>
              <p className="mt-1 text-sm text-gray-800">{scan.discovered_devices}</p>
            </div>
            <div>
              <p className="label-caption">Avviato da</p>
              <p className="mt-1 text-sm text-gray-800">{scan.initiated_by || "scheduler"}</p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-gray-400">
            <span>{new Date(scan.started_at).toLocaleString("it-IT")}</span>
            <Link href={`/network/scans/${scan.id}`} className="font-medium text-[#1D4E35]">
              Apri dettaglio
            </Link>
          </div>
        </article>
      ))}

      {scans.length === 0 && !loadError ? (
        <article className="panel-card text-sm text-gray-500">Nessuna scansione disponibile.</article>
      ) : null}
    </div>
  );
}

export default function NetworkScansPage() {
  return (
    <NetworkModulePage
      title="Scansioni"
      description="Storico degli snapshot di rete eseguiti manualmente o da scheduler."
      breadcrumb="Storico"
    >
      {({ token }) => <ScansContent token={token} />}
    </NetworkModulePage>
  );
}
