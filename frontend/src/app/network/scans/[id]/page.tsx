"use client";

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { getNetworkScan, getNetworkScanDiff, getNetworkScans } from "@/lib/api";
import type { NetworkScan, NetworkScanDetail, NetworkScanDiff } from "@/types/api";

function ScanDetailContent({ token, scanId }: { token: string; scanId: number }) {
  const [scan, setScan] = useState<NetworkScanDetail | null>(null);
  const [scans, setScans] = useState<NetworkScan[]>([]);
  const [comparisonScanId, setComparisonScanId] = useState<number | null>(null);
  const [diff, setDiff] = useState<NetworkScanDiff | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadScan() {
      try {
        const [scanResponse, scansResponse] = await Promise.all([getNetworkScan(token, scanId), getNetworkScans(token)]);
        setScan(scanResponse);
        setScans(scansResponse);
        const fallbackComparison = scansResponse.find((item) => item.id !== scanId)?.id ?? null;
        setComparisonScanId((current) => current ?? fallbackComparison);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento snapshot");
      }
    }

    void loadScan();
  }, [scanId, token]);

  useEffect(() => {
    async function loadDiff() {
      if (!comparisonScanId || comparisonScanId === scanId) {
        setDiff(null);
        return;
      }

      try {
        const response = await getNetworkScanDiff(token, comparisonScanId, scanId);
        setDiff(response);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento diff snapshot");
      }
    }

    void loadDiff();
  }, [comparisonScanId, scanId, token]);

  const comparisonCandidates = useMemo(
    () => scans.filter((item) => item.id !== scanId),
    [scanId, scans],
  );

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
    <div className="page-stack">
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
            <div>
              <dt className="label-caption">Nuovi</dt>
              <dd className="mt-1 text-sm text-gray-800">{scan.delta.new_devices_count}</dd>
            </div>
            <div>
              <dt className="label-caption">Scomparsi</dt>
              <dd className="mt-1 text-sm text-gray-800">{scan.delta.missing_devices_count}</dd>
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

      <article className="panel-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="section-title">Confronto snapshot</p>
            <p className="section-copy">Delta reale tra due scansioni salvate nello storico.</p>
          </div>
          <select
            className="form-control w-full max-w-56"
            value={comparisonScanId ?? ""}
            onChange={(event) => setComparisonScanId(event.target.value ? Number(event.target.value) : null)}
          >
            <option value="">Nessun confronto</option>
            {comparisonCandidates.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                Snapshot #{candidate.id}
              </option>
            ))}
          </select>
        </div>
        {diff ? (
          <>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <div>
                <p className="label-caption">Nuovi</p>
                <p className="mt-1 text-sm text-gray-800">{diff.summary.new_devices_count}</p>
              </div>
              <div>
                <p className="label-caption">Scomparsi</p>
                <p className="mt-1 text-sm text-gray-800">{diff.summary.missing_devices_count}</p>
              </div>
              <div>
                <p className="label-caption">Modificati</p>
                <p className="mt-1 text-sm text-gray-800">{diff.summary.changed_devices_count}</p>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              {diff.changes.map((change) => {
                const reference = change.after || change.before;
                if (!reference) {
                  return null;
                }
                return (
                  <div key={`${change.change_type}-${change.key}`} className="rounded-lg border border-gray-100 px-4 py-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {reference.display_name || reference.hostname || reference.ip_address}
                        </p>
                        <p className="mt-1 text-xs text-gray-500">
                          {reference.ip_address} · {reference.mac_address || "MAC n/d"}
                        </p>
                      </div>
                      <NetworkStatusBadge status={change.change_type} />
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <p className="mt-4 text-sm text-gray-500">Seleziona un altro snapshot per calcolare il diff.</p>
        )}
      </article>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Dispositivi presenti nello snapshot</p>
          <p className="section-copy">Fotografia coerente dello stato devices al termine della scansione.</p>
        </div>
        <div className="space-y-3">
          {scan.devices.map((device) => (
            <div key={device.id} className="rounded-lg border border-gray-100 px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {device.display_name || device.hostname || device.ip_address}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    {device.ip_address} · {device.mac_address || "MAC n/d"} · {device.open_ports || "porte n/d"}
                  </p>
                </div>
                <NetworkStatusBadge status={device.status} />
              </div>
            </div>
          ))}
        </div>
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
      description="Metadati, dispositivi osservati e differenze rispetto a una scansione precedente."
      breadcrumb={`Snapshot ${params.id}`}
    >
      {({ token }) => <ScanDetailContent token={token} scanId={scanId} />}
    </NetworkModulePage>
  );
}
