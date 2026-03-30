"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, RefreshIcon, ServerIcon } from "@/components/ui/icons";
import { getNetworkAlerts, getNetworkDashboard, getNetworkDevice, getNetworkDevices, triggerNetworkScan } from "@/lib/api";
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
  const [selectedDevice, setSelectedDevice] = useState<NetworkDevice | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
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

  useEffect(() => {
    async function loadDeviceDetail() {
      if (!selectedDeviceId) {
        setSelectedDevice(null);
        setDetailError(null);
        return;
      }

      setIsLoadingDetail(true);
      try {
        const response = await getNetworkDevice(token, selectedDeviceId);
        setSelectedDevice(response);
        setDetailError(null);
      } catch (error) {
        setDetailError(error instanceof Error ? error.message : "Errore nel caricamento dettaglio dispositivo");
      } finally {
        setIsLoadingDetail(false);
      }
    }

    void loadDeviceDetail();
  }, [selectedDeviceId, token]);

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

  function closeModal() {
    setSelectedDeviceId(null);
    setSelectedDevice(null);
    setDetailError(null);
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

      {selectedDeviceId ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
            <div className="sticky top-0 flex items-start justify-between gap-4 border-b border-gray-100 bg-white px-6 py-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Dettaglio dispositivo</p>
                <h2 className="mt-2 text-2xl font-semibold text-gray-900">
                  {selectedDevice?.display_name || selectedDevice?.hostname || selectedDevice?.ip_address || `Dispositivo #${selectedDeviceId}`}
                </h2>
                <p className="mt-1 text-sm text-gray-500">Vista rapida dalla dashboard senza lasciare il contesto operativo.</p>
              </div>
              <button className="btn-secondary" type="button" onClick={closeModal}>
                Chiudi
              </button>
            </div>

            <div className="px-6 py-6">
              {isLoadingDetail ? (
                <p className="text-sm text-gray-500">Caricamento dettaglio dispositivo.</p>
              ) : detailError ? (
                <p className="text-sm text-red-600">{detailError}</p>
              ) : selectedDevice ? (
                <div className="space-y-6">
                  <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                    <article className="panel-card">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="section-title">Identità dispositivo</p>
                          <p className="mt-1 text-lg font-medium text-gray-900">
                            {selectedDevice.display_name || selectedDevice.hostname || selectedDevice.ip_address}
                          </p>
                          <p className="mt-1 text-sm text-gray-500">
                            {selectedDevice.asset_label || selectedDevice.dns_name || "Nessuna etichetta assegnata"}
                          </p>
                        </div>
                        <NetworkStatusBadge status={selectedDevice.status} />
                      </div>
                      <dl className="mt-5 grid gap-4 md:grid-cols-2">
                        <div>
                          <dt className="label-caption">IP</dt>
                          <dd className="mt-1 text-sm text-gray-800">{selectedDevice.ip_address}</dd>
                        </div>
                        <div>
                          <dt className="label-caption">MAC</dt>
                          <dd className="mt-1 text-sm text-gray-800">{selectedDevice.mac_address || "n/d"}</dd>
                        </div>
                        <div>
                          <dt className="label-caption">Vendor</dt>
                          <dd className="mt-1 text-sm text-gray-800">{selectedDevice.vendor || "n/d"}</dd>
                        </div>
                        <div>
                          <dt className="label-caption">Modello</dt>
                          <dd className="mt-1 text-sm text-gray-800">{selectedDevice.model_name || "n/d"}</dd>
                        </div>
                        <div>
                          <dt className="label-caption">Tipo dispositivo</dt>
                          <dd className="mt-1 text-sm text-gray-800">{selectedDevice.device_type || "n/d"}</dd>
                        </div>
                        <div>
                          <dt className="label-caption">Sistema operativo</dt>
                          <dd className="mt-1 text-sm text-gray-800">{selectedDevice.operating_system || "n/d"}</dd>
                        </div>
                        <div>
                          <dt className="label-caption">Hostname</dt>
                          <dd className="mt-1 text-sm text-gray-800">{selectedDevice.hostname || "n/d"}</dd>
                        </div>
                        <div>
                          <dt className="label-caption">Sorgente nome</dt>
                          <dd className="mt-1 text-sm text-gray-800">{selectedDevice.hostname_source || "n/d"}</dd>
                        </div>
                        <div>
                          <dt className="label-caption">Porte aperte</dt>
                          <dd className="mt-1 text-sm text-gray-800">{selectedDevice.open_ports || "n/d"}</dd>
                        </div>
                        <div>
                          <dt className="label-caption">Posizione</dt>
                          <dd className="mt-1 text-sm text-gray-800">{selectedDevice.location_hint || "n/d"}</dd>
                        </div>
                      </dl>
                    </article>

                    <article className="panel-card">
                      <p className="section-title">Timeline monitoraggio</p>
                      <dl className="mt-5 space-y-4">
                        <div>
                          <dt className="label-caption">Prima rilevazione</dt>
                          <dd className="mt-1 text-sm text-gray-800">{new Date(selectedDevice.first_seen_at).toLocaleString("it-IT")}</dd>
                        </div>
                        <div>
                          <dt className="label-caption">Ultima rilevazione</dt>
                          <dd className="mt-1 text-sm text-gray-800">{new Date(selectedDevice.last_seen_at).toLocaleString("it-IT")}</dd>
                        </div>
                        <div>
                          <dt className="label-caption">Ultimo scan</dt>
                          <dd className="mt-1 text-sm text-gray-800">{selectedDevice.last_scan_id ? `Snapshot #${selectedDevice.last_scan_id}` : "n/d"}</dd>
                        </div>
                        <div>
                          <dt className="label-caption">Monitorato</dt>
                          <dd className="mt-1 text-sm text-gray-800">{selectedDevice.is_monitored ? "Si" : "No"}</dd>
                        </div>
                      </dl>
                    </article>
                  </div>

                  <article className="panel-card">
                    <div className="mb-4">
                      <p className="section-title">Posizionamento e storico</p>
                      <p className="section-copy">Ultime posizioni note e snapshot recenti del dispositivo.</p>
                    </div>
                    <div className="grid gap-6 xl:grid-cols-2">
                      <div>
                        <p className="label-caption">Posizioni planimetria</p>
                        <div className="mt-3 space-y-3">
                          {selectedDevice.positions.map((position) => (
                            <div key={position.id} className="rounded-lg border border-gray-100 px-4 py-3 text-sm text-gray-700">
                              <p className="font-medium text-gray-900">Planimetria #{position.floor_plan_id}</p>
                              <p className="mt-1">Coordinate: {position.x}, {position.y}</p>
                              <p className="mt-1">{position.label || "Etichetta non impostata"}</p>
                            </div>
                          ))}
                          {selectedDevice.positions.length === 0 ? <p className="text-sm text-gray-500">Nessuna posizione registrata.</p> : null}
                        </div>
                      </div>
                      <div>
                        <p className="label-caption">Ultimi snapshot</p>
                        <div className="mt-3 space-y-3">
                          {selectedDevice.scan_history.map((entry) => (
                            <div key={`${entry.scan_id}-${entry.observed_at}`} className="rounded-lg border border-gray-100 px-4 py-3">
                              <div className="flex items-center justify-between gap-3">
                                <p className="text-sm font-medium text-gray-900">Snapshot #{entry.scan_id}</p>
                                <NetworkStatusBadge status={entry.status} />
                              </div>
                              <p className="mt-1 text-xs text-gray-500">{new Date(entry.observed_at).toLocaleString("it-IT")}</p>
                              <p className="mt-2 text-xs text-gray-500">{entry.hostname || entry.ip_address} · {entry.open_ports || "porte n/d"}</p>
                            </div>
                          ))}
                          {selectedDevice.scan_history.length === 0 ? <p className="text-sm text-gray-500">Nessuno snapshot disponibile.</p> : null}
                        </div>
                      </div>
                    </div>
                  </article>

                  <div className="flex justify-end">
                    <Link href={`/network/devices/${selectedDevice.id}`} className="btn-secondary" onClick={closeModal}>
                      Apri pagina completa
                    </Link>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
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
