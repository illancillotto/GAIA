"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { NetworkDeviceModal } from "@/components/network/network-device-modal";
import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, RefreshIcon, ServerIcon } from "@/components/ui/icons";
import { getNetworkAlerts, getNetworkDashboard, getNetworkDevices, triggerNetworkScan } from "@/lib/api";
import { getNetworkDeviceAdminUrl } from "@/lib/network-device-utils";
import type { NetworkAlert, NetworkDashboardSummary, NetworkDevice } from "@/types/api";

const emptySummary: NetworkDashboardSummary = {
  total_devices: 0,
  online_devices: 0,
  offline_devices: 0,
  open_alerts: 0,
  scans_last_24h: 0,
  floor_plans: 0,
  latest_scan_at: null,
};

function DashboardContent({ token }: { token: string }) {
  const [summary, setSummary] = useState<NetworkDashboardSummary>(emptySummary);
  const [recentDevices, setRecentDevices] = useState<NetworkDevice[]>([]);
  const [onlineDevices, setOnlineDevices] = useState<NetworkDevice[]>([]);
  const [alerts, setAlerts] = useState<NetworkAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isTriggeringScan, setIsTriggeringScan] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null);
  const [onlineFilter, setOnlineFilter] = useState("");
  const [recentFilter, setRecentFilter] = useState("");
  const [alertFilter, setAlertFilter] = useState("");

  const loadData = useCallback(async () => {
    try {
      const [dashboard, recentDeviceResponse, onlineDeviceResponse, alertItems] = await Promise.all([
        getNetworkDashboard(token),
        getNetworkDevices(token, { pageSize: 12 }),
        getNetworkDevices(token, { status: "online", pageSize: 100 }),
        getNetworkAlerts(token),
      ]);
      setSummary(dashboard);
      setRecentDevices(recentDeviceResponse.items);
      setOnlineDevices(onlineDeviceResponse.items);
      setAlerts(alertItems.slice(0, 5));
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento dati");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  async function handleScanTrigger() {
    setIsTriggeringScan(true);
    try {
      await triggerNetworkScan(token);
      await loadData();
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore durante la scansione");
    } finally {
      setIsTriggeringScan(false);
    }
  }

  function handleDeviceUpdated(updatedDevice: NetworkDevice) {
    setRecentDevices((currentItems) => currentItems.map((item) => (item.id === updatedDevice.id ? { ...item, ...updatedDevice } : item)));
    setOnlineDevices((currentItems) => currentItems.map((item) => (item.id === updatedDevice.id ? { ...item, ...updatedDevice } : item)));
  }

  const filteredOnlineDevices = onlineDevices.filter((device) => {
    const haystack = [
      device.display_name,
      device.hostname,
      device.ip_address,
      device.mac_address,
      device.device_type,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(onlineFilter.trim().toLowerCase());
  });
  const filteredRecentDevices = recentDevices.filter((device) => {
    const haystack = [
      device.display_name,
      device.hostname,
      device.ip_address,
      device.mac_address,
      device.device_type,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(recentFilter.trim().toLowerCase());
  });
  const filteredAlerts = alerts.filter((alert) => {
    const haystack = [alert.title, alert.message, alert.alert_type, alert.severity].filter(Boolean).join(" ").toLowerCase();
    return haystack.includes(alertFilter.trim().toLowerCase());
  });

  return (
    <div className="page-stack">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-gray-500">
          Monitoraggio read-only della LAN con snapshot incrementali e alert per nuovi host o host offline.
        </p>
        <button className="btn-primary" onClick={handleScanTrigger} type="button" disabled={isTriggeringScan}>
          <RefreshIcon className="h-4 w-4" />
          {isTriggeringScan ? "Scansione in corso" : "Avvia scansione"}
        </button>
      </div>

      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Caricamento non riuscito</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      <div className="surface-grid">
        <MetricCard label="Dispositivi totali" value={summary.total_devices} sub="Host rilevati nell’ultima base dati" />
        <MetricCard label="Online" value={summary.online_devices} sub="Host raggiungibili all’ultimo scan" variant="success" />
        <MetricCard label="Offline" value={summary.offline_devices} sub="Host non rilevati nell’ultimo scan" variant={summary.offline_devices > 0 ? "danger" : "default"} />
        <MetricCard label="Alert aperti" value={summary.open_alerts} sub="Nuovi dispositivi o host non raggiungibili" variant={summary.open_alerts > 0 ? "warning" : "default"} />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <article className="panel-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="section-title">Dispositivi online</p>
              <p className="section-copy">Host attualmente raggiungibili nell’ultimo scan.</p>
            </div>
            <BadgeCount value={filteredOnlineDevices.length} />
          </div>

          <input
            className="form-control mb-4"
            value={onlineFilter}
            onChange={(event) => setOnlineFilter(event.target.value)}
            placeholder="Filtra online per IP, host o MAC"
          />

          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento dispositivi in corso.</p>
          ) : filteredOnlineDevices.length === 0 ? (
            <EmptyState
              icon={ServerIcon}
              title="Nessun dispositivo online"
              description="Non risultano host raggiungibili con i filtri correnti."
            />
          ) : (
            <div className="max-h-[28rem] space-y-3 overflow-y-auto pr-1">
              {filteredOnlineDevices.map((device) => (
                <button
                  key={device.id}
                  type="button"
                  onClick={() => setSelectedDeviceId(device.id)}
                  className="flex w-full items-center justify-between rounded-lg border border-gray-100 px-4 py-3 text-left transition hover:bg-gray-50"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">{device.display_name || device.hostname || device.ip_address}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {device.ip_address} · {device.mac_address || "MAC n/d"}
                    </p>
                    {device.asset_label || device.notes ? (
                      <p className="mt-1 text-xs text-gray-500">
                        {device.asset_label || "Nessuna label"}{device.notes ? ` · ${device.notes}` : ""}
                      </p>
                    ) : null}
                  </div>
                  <NetworkStatusBadge status={device.status} />
                </button>
              ))}
            </div>
          )}
        </article>

        <article className="panel-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="section-title">Dispositivi recenti</p>
              <p className="section-copy">Ultimi host rilevati o aggiornati nel monitoraggio.</p>
            </div>
            <Link href="/network/devices" className="text-sm font-medium text-[#1D4E35]">
              Apri lista completa
            </Link>
          </div>

          <input
            className="form-control mb-4"
            value={recentFilter}
            onChange={(event) => setRecentFilter(event.target.value)}
            placeholder="Filtra recenti per IP, host o MAC"
          />

          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento dispositivi in corso.</p>
          ) : filteredRecentDevices.length === 0 ? (
            <EmptyState
              icon={ServerIcon}
              title="Nessun dispositivo rilevato"
              description="Nessun dispositivo corrisponde ai filtri correnti."
            />
          ) : (
            <div className="max-h-[28rem] space-y-3 overflow-y-auto pr-1">
              {filteredRecentDevices.map((device) => (
                <button
                  key={device.id}
                  type="button"
                  onClick={() => setSelectedDeviceId(device.id)}
                  className="flex w-full items-center justify-between rounded-lg border border-gray-100 px-4 py-3 text-left transition hover:bg-gray-50"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">{device.display_name || device.hostname || device.ip_address}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {device.ip_address} · {device.mac_address || "MAC n/d"} · {device.device_type || "tipo n/d"}
                    </p>
                    {device.asset_label || device.notes ? (
                      <p className="mt-1 text-xs text-gray-500">
                        {device.asset_label || "Nessuna label"}{device.notes ? ` · ${device.notes}` : ""}
                      </p>
                    ) : null}
                    {getNetworkDeviceAdminUrl(device) ? (
                      <p className="mt-1 text-xs text-[#1D4E35]">Pagina admin disponibile</p>
                    ) : null}
                  </div>
                  <NetworkStatusBadge status={device.status} />
                </button>
              ))}
            </div>
          )}
        </article>

        <article className="panel-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="section-title">Alert attivi</p>
              <p className="section-copy">Segnalazioni correnti da revisionare.</p>
            </div>
            <Link href="/network/alerts" className="text-sm font-medium text-[#1D4E35]">
              Apri alert
            </Link>
          </div>

          <input
            className="form-control mb-4"
            value={alertFilter}
            onChange={(event) => setAlertFilter(event.target.value)}
            placeholder="Filtra alert per titolo, messaggio o severità"
          />

          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento alert in corso.</p>
          ) : filteredAlerts.length === 0 ? (
            <EmptyState
              icon={AlertTriangleIcon}
              title="Nessun alert visibile"
              description="Nessun alert corrisponde ai filtri correnti."
            />
          ) : (
            <div className="max-h-[28rem] space-y-3 overflow-y-auto pr-1">
              {filteredAlerts.map((alert) => (
                <div key={alert.id} className="rounded-lg border border-gray-100 px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-gray-900">{alert.title}</p>
                    <NetworkStatusBadge status={alert.severity} />
                  </div>
                  <p className="mt-2 text-sm text-gray-600">{alert.message || "Nessun dettaglio aggiuntivo."}</p>
                </div>
              ))}
            </div>
          )}
        </article>
      </div>

      <NetworkDeviceModal
        token={token}
        deviceId={selectedDeviceId}
        open={selectedDeviceId !== null}
        onClose={() => setSelectedDeviceId(null)}
        onUpdated={handleDeviceUpdated}
      />
    </div>
  );
}

function BadgeCount({ value }: { value: number }) {
  return (
    <span className="rounded-full bg-[#EAF3E8] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">
      {value}
    </span>
  );
}

export default function NetworkPage() {
  return (
    <NetworkModulePage
      title="Dashboard"
      description="Vista operativa dello stato della rete LAN, degli alert aperti e dell’ultima attività di scansione."
    >
      {({ token }) => <DashboardContent token={token} />}
    </NetworkModulePage>
  );
}
