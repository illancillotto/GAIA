"use client";

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { FilterPillGroup } from "@/components/network/filter-pill-group";
import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { getNetworkScan, getNetworkScanDiff, getNetworkScans } from "@/lib/api";
import { formatIpWithReference } from "@/lib/network-device-utils";
import type { NetworkScan, NetworkScanDetail, NetworkScanDiff } from "@/types/api";

const DIFF_FILTER_OPTIONS = [
  { value: "all", label: "Tutti" },
  { value: "new", label: "Nuovi" },
  { value: "missing", label: "Scomparsi" },
  { value: "changed", label: "Modificati" },
] as const;

const DEVICE_STATUS_FILTER_OPTIONS = [
  { value: "all", label: "Tutti" },
  { value: "online", label: "Online" },
  { value: "offline", label: "Offline" },
] as const;

function ScanDetailContent({ token, scanId }: { token: string; scanId: number }) {
  const [scan, setScan] = useState<NetworkScanDetail | null>(null);
  const [scans, setScans] = useState<NetworkScan[]>([]);
  const [comparisonScanId, setComparisonScanId] = useState<number | null>(null);
  const [diff, setDiff] = useState<NetworkScanDiff | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [deviceSearch, setDeviceSearch] = useState("");
  const [deviceStatusFilter, setDeviceStatusFilter] = useState<"all" | "online" | "offline">("all");
  const [diffTypeFilter, setDiffTypeFilter] = useState<"all" | "new" | "missing" | "changed">("all");
  const [diffSearch, setDiffSearch] = useState("");

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

  const filteredDiffChanges = useMemo(() => {
    if (!diff) {
      return [];
    }

    const normalizedSearch = diffSearch.trim().toLowerCase();

    return diff.changes.filter((change) => {
      const reference = change.after || change.before;
      if (!reference) {
        return false;
      }

      if (diffTypeFilter !== "all" && change.change_type !== diffTypeFilter) {
        return false;
      }

      if (!normalizedSearch) {
        return true;
      }

      const haystack = [
        reference.resolved_label,
        reference.display_name,
        reference.hostname,
        reference.ip_address,
        reference.mac_address,
        reference.vendor,
        reference.model_name,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(normalizedSearch);
    });
  }, [diff, diffSearch, diffTypeFilter]);

  const filteredSnapshotDevices = useMemo(() => {
    if (!scan) {
      return [];
    }

    const normalizedSearch = deviceSearch.trim().toLowerCase();

    return scan.devices.filter((device) => {
      if (deviceStatusFilter !== "all" && device.status !== deviceStatusFilter) {
        return false;
      }

      if (!normalizedSearch) {
        return true;
      }

      const haystack = [
        device.resolved_label,
        device.display_name,
        device.hostname,
        device.ip_address,
        device.mac_address,
        device.vendor,
        device.model_name,
        device.open_ports,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(normalizedSearch);
    });
  }, [deviceSearch, deviceStatusFilter, scan]);

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
          <div className="flex w-full flex-wrap justify-end gap-3 xl:w-auto">
            <input
              className="form-control w-full xl:w-72"
              value={diffSearch}
              onChange={(event) => setDiffSearch(event.target.value)}
              placeholder="Cerca nel diff per IP, MAC o nome"
            />
            <select
              className="form-control w-full xl:w-44"
              value={diffTypeFilter}
              onChange={(event) => setDiffTypeFilter(event.target.value as "all" | "new" | "missing" | "changed")}
            >
              <option value="all">Tutte le variazioni</option>
              <option value="new">Nuovi</option>
              <option value="missing">Scomparsi</option>
              <option value="changed">Modificati</option>
            </select>
            <select
              className="form-control w-full xl:w-56"
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
            <div className="mt-4">
              <FilterPillGroup options={DIFF_FILTER_OPTIONS} value={diffTypeFilter} onChange={setDiffTypeFilter} />
            </div>
            <div className="mt-4 flex items-center justify-between gap-3 text-xs text-gray-500">
              <span>{filteredDiffChanges.length} variazioni mostrate</span>
            </div>
            <div className="mt-4 space-y-3">
              {filteredDiffChanges.map((change) => {
                const reference = change.after || change.before;
                if (!reference) {
                  return null;
                }
                return (
                  <div key={`${change.change_type}-${change.key}`} className="rounded-lg border border-gray-100 px-4 py-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {reference.resolved_label || reference.display_name || reference.hostname || reference.ip_address}
                        </p>
                        <p className="mt-1 text-xs text-gray-500">
                          {formatIpWithReference(reference)} · {reference.mac_address || "MAC n/d"}
                        </p>
                      </div>
                      <NetworkStatusBadge status={change.change_type} />
                    </div>
                  </div>
                );
              })}
            </div>
            {filteredDiffChanges.length === 0 ? (
              <div className="rounded-lg border border-dashed border-gray-200 px-4 py-6 text-sm text-gray-500">
                Nessuna variazione corrisponde ai filtri selezionati.
              </div>
            ) : null}
          </>
        ) : (
          <p className="mt-4 text-sm text-gray-500">Seleziona un altro snapshot per calcolare il diff.</p>
        )}
      </article>

      <article className="panel-card">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="section-title">Dispositivi presenti nello snapshot</p>
            <p className="section-copy">Fotografia coerente dello stato devices al termine della scansione.</p>
          </div>
          <div className="flex w-full flex-wrap justify-end gap-3 xl:w-auto">
            <input
              className="form-control w-full xl:w-80"
              value={deviceSearch}
              onChange={(event) => setDeviceSearch(event.target.value)}
              placeholder="Cerca per IP, MAC, nome o porte"
            />
            <select
              className="form-control w-full xl:w-44"
              value={deviceStatusFilter}
              onChange={(event) => setDeviceStatusFilter(event.target.value as "all" | "online" | "offline")}
            >
              <option value="all">Tutti gli stati</option>
              <option value="online">Online</option>
              <option value="offline">Offline</option>
            </select>
          </div>
        </div>
        <div className="mb-4">
          <FilterPillGroup options={DEVICE_STATUS_FILTER_OPTIONS} value={deviceStatusFilter} onChange={setDeviceStatusFilter} />
        </div>
        <p className="mb-4 text-xs text-gray-500">{filteredSnapshotDevices.length} dispositivi mostrati</p>
        <div className="space-y-3">
          {filteredSnapshotDevices.map((device) => (
            <div key={device.id} className="rounded-lg border border-gray-100 px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {device.resolved_label || device.display_name || device.hostname || device.ip_address}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    {formatIpWithReference(device)} · {device.mac_address || "MAC n/d"} · {device.open_ports || "porte n/d"}
                  </p>
                </div>
                <NetworkStatusBadge status={device.status} />
              </div>
            </div>
          ))}
        </div>
        {filteredSnapshotDevices.length === 0 ? (
          <div className="mt-4 rounded-lg border border-dashed border-gray-200 px-4 py-6 text-sm text-gray-500">
            Nessun dispositivo corrisponde ai filtri selezionati.
          </div>
        ) : null}
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
