"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { getNetworkScan } from "@/lib/api";
import type { NetworkScan } from "@/types/api";

function ScanDetailContent({ token, scanId }: { token: string; scanId: number }) {
  const [scan, setScan] = useState<NetworkScan | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadScan() {
      try {
        const response = await getNetworkScan(token, scanId);
        setScan(response);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento snapshot");
      }
    }

    void loadScan();
  }, [scanId, token]);

  if (loadError) {
    return (
      <article className="panel-card">
        <p className="text-sm font-medium text-red-700">Snapshot non disponibile</p>
        <p className="mt-2 text-sm text-gray-600">{loadError}</p>
      </article>
    );
  }

  if (!scan) {
    return <article className="panel-card text-sm text-gray-500">Caricamento snapshot in corso.</article>;
  }

  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <article className="panel-card">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="section-title">Informazioni snapshot</p>
            <p className="mt-1 text-lg font-medium text-gray-900">Scansione #{scan.id}</p>
          </div>
          <NetworkStatusBadge status={scan.status} />
        </div>
        <dl className="mt-5 grid gap-4 md:grid-cols-2">
          <div>
            <dt className="label-caption">Range</dt>
            <dd className="mt-1 text-sm text-gray-800">{scan.network_range}</dd>
          </div>
          <div>
            <dt className="label-caption">Tipo</dt>
            <dd className="mt-1 text-sm text-gray-800">{scan.scan_type}</dd>
          </div>
          <div>
            <dt className="label-caption">Host scanditi</dt>
            <dd className="mt-1 text-sm text-gray-800">{scan.hosts_scanned}</dd>
          </div>
          <div>
            <dt className="label-caption">Host attivi</dt>
            <dd className="mt-1 text-sm text-gray-800">{scan.active_hosts}</dd>
          </div>
        </dl>
      </article>

      <article className="panel-card">
        <p className="section-title">Audit operativo</p>
        <dl className="mt-5 space-y-4">
          <div>
            <dt className="label-caption">Iniziato</dt>
            <dd className="mt-1 text-sm text-gray-800">{new Date(scan.started_at).toLocaleString("it-IT")}</dd>
          </div>
          <div>
            <dt className="label-caption">Completato</dt>
            <dd className="mt-1 text-sm text-gray-800">{new Date(scan.completed_at).toLocaleString("it-IT")}</dd>
          </div>
          <div>
            <dt className="label-caption">Avviato da</dt>
            <dd className="mt-1 text-sm text-gray-800">{scan.initiated_by || "scheduler"}</dd>
          </div>
          <div>
            <dt className="label-caption">Note</dt>
            <dd className="mt-1 text-sm text-gray-800">{scan.notes || "Nessuna nota registrata."}</dd>
          </div>
        </dl>
      </article>
    </div>
  );
}

export default function NetworkScanDetailPage() {
  const params = useParams<{ id: string }>();
  const scanId = Number(params.id);

  return (
    <NetworkModulePage
      title="Dettaglio snapshot"
      description="Metadati dello snapshot di scansione e indicatori principali del ciclo eseguito."
      breadcrumb={`Snapshot ${params.id}`}
    >
      {({ token }) => <ScanDetailContent token={token} scanId={scanId} />}
    </NetworkModulePage>
  );
}
