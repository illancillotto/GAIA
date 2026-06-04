"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { NetworkDeviceModal } from "@/components/network/network-device-modal";
import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, RefreshIcon, ServerIcon } from "@/components/ui/icons";
import { getNetworkAlerts, getNetworkDashboard, getNetworkDevices, getNetworkFirewalls, getNetworkFirewallMetrics, triggerNetworkScan } from "@/lib/api";
import { getNetworkDeviceAdminUrl } from "@/lib/network-device-utils";
import type { NetworkAlert, NetworkDashboardSummary, NetworkDevice, NetworkFirewall, NetworkFirewallMetric } from "@/types/api";

const emptySummary: NetworkDashboardSummary = {
  total_devices: 0,
  online_devices: 0,
  offline_devices: 0,
  open_alerts: 0,
  firewalls_online: 0,
  scans_last_24h: 0,
  floor_plans: 0,
  latest_scan_at: null,
};

type DashboardLifecycleFilter = "all" | "active" | "retired";
type DashboardAssignmentFilter = "all" | "assigned" | "unassigned";

function DashboardContent({ token }: { token: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [summary, setSummary] = useState<NetworkDashboardSummary>(emptySummary);
  const [recentDevices, setRecentDevices] = useState<NetworkDevice[]>([]);
  const [onlineDevices, setOnlineDevices] = useState<NetworkDevice[]>([]);
  const [alerts, setAlerts] = useState<NetworkAlert[]>([]);
  const [firewalls, setFirewalls] = useState<NetworkFirewall[]>([]);
  const [firewallMetrics, setFirewallMetrics] = useState<NetworkFirewallMetric[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isTriggeringScan, setIsTriggeringScan] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null);
  const [onlineFilter, setOnlineFilter] = useState(searchParams.get("online") ?? "");
  const [recentFilter, setRecentFilter] = useState(searchParams.get("recent") ?? "");
  const [alertFilter, setAlertFilter] = useState(searchParams.get("alerts") ?? "");
  const [lifecycleFilter, setLifecycleFilter] = useState<DashboardLifecycleFilter>(() => {
    const initialValue = searchParams.get("lifecycle");
    if (initialValue === "active" || initialValue === "retired") {
      return initialValue;
    }
    return "all";
  });
  const [assignmentFilter, setAssignmentFilter] = useState<DashboardAssignmentFilter>(() => {
    const initialValue = searchParams.get("assignment");
    if (initialValue === "assigned" || initialValue === "unassigned") {
      return initialValue;
    }
    return "all";
  });

  const loadData = useCallback(async () => {
    try {
      const [dashboard, recentDeviceResponse, onlineDeviceResponse, alertItems, firewallItems] = await Promise.all([
        getNetworkDashboard(token),
        getNetworkDevices(token, { pageSize: 12 }),
        getNetworkDevices(token, { status: "online", pageSize: 100 }),
        getNetworkAlerts(token),
        getNetworkFirewalls(token),
      ]);
      const primaryFirewall = firewallItems[0] ?? null;
      const metricItems = primaryFirewall ? await getNetworkFirewallMetrics(token, primaryFirewall.id, { limit: 6 }) : [];
      setSummary(dashboard);
      setRecentDevices(recentDeviceResponse.items);
      setOnlineDevices(onlineDeviceResponse.items);
      setAlerts(alertItems.slice(0, 5));
      setFirewalls(firewallItems);
      setFirewallMetrics(metricItems);
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
    const params = new URLSearchParams(searchParams.toString());

    if (onlineFilter.trim()) {
      params.set("online", onlineFilter.trim());
    } else {
      params.delete("online");
    }

    if (recentFilter.trim()) {
      params.set("recent", recentFilter.trim());
    } else {
      params.delete("recent");
    }

    if (alertFilter.trim()) {
      params.set("alerts", alertFilter.trim());
    } else {
      params.delete("alerts");
    }

    if (lifecycleFilter !== "all") {
      params.set("lifecycle", lifecycleFilter);
    } else {
      params.delete("lifecycle");
    }

    if (assignmentFilter !== "all") {
      params.set("assignment", assignmentFilter);
    } else {
      params.delete("assignment");
    }

    const nextQuery = params.toString();
    const nextUrl = nextQuery ? `${pathname}?${nextQuery}` : pathname;
    router.replace(nextUrl, { scroll: false });
  }, [
    alertFilter,
    assignmentFilter,
    lifecycleFilter,
    onlineFilter,
    pathname,
    recentFilter,
    router,
    searchParams,
  ]);

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

  function matchesDashboardDeviceFilters(device: NetworkDevice) {
    if (lifecycleFilter === "active" && device.lifecycle_state !== "active") {
      return false;
    }
    if (lifecycleFilter === "retired" && device.lifecycle_state !== "retired") {
      return false;
    }
    if (assignmentFilter === "assigned" && !device.assigned_user_id) {
      return false;
    }
    if (assignmentFilter === "unassigned" && (device.assigned_user_id || device.lifecycle_state === "retired")) {
      return false;
    }
    return true;
  }

  const filteredOnlineDevices = onlineDevices.filter((device) => {
    const haystack = [
      device.resolved_label,
      device.display_name,
      device.hostname,
      device.ip_address,
      device.mac_address,
      device.device_type,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return matchesDashboardDeviceFilters(device) && haystack.includes(onlineFilter.trim().toLowerCase());
  });
  const filteredRecentDevices = recentDevices.filter((device) => {
    const haystack = [
      device.resolved_label,
      device.display_name,
      device.hostname,
      device.ip_address,
      device.mac_address,
      device.device_type,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return matchesDashboardDeviceFilters(device) && haystack.includes(recentFilter.trim().toLowerCase());
  });
  const filteredAlerts = alerts.filter((alert) => {
    const haystack = [alert.title, alert.message, alert.alert_type, alert.severity].filter(Boolean).join(" ").toLowerCase();
    return haystack.includes(alertFilter.trim().toLowerCase());
  });
  const unassignedDevices = recentDevices.filter(
    (device) =>
      !device.assigned_user_id &&
      device.lifecycle_state !== "retired" &&
      lifecycleFilter !== "retired" &&
      haystacklessAssignmentMatch(assignmentFilter),
  );
  const activeDevicesCount = recentDevices.filter((device) => device.lifecycle_state === "active").length;
  const retiredDevicesCount = recentDevices.filter((device) => device.lifecycle_state === "retired").length;
  const assignedDevicesCount = recentDevices.filter((device) => Boolean(device.assigned_user_id)).length;
  const unassignedDevicesCount = recentDevices.filter((device) => !device.assigned_user_id && device.lifecycle_state !== "retired").length;

  function haystacklessAssignmentMatch(filter: DashboardAssignmentFilter) {
    return filter === "all" || filter === "unassigned";
  }

  return (
    <div className="page-stack">
      <ModuleWorkspaceHero
        badge={
          <>
            <ServerIcon className="h-3.5 w-3.5" />
            Workspace Rete
          </>
        }
        title="Monitoraggio LAN, inventario dispositivi e alert operativi."
        description="Tracciamento host conosciuti, stato online/offline e segnalazioni per assenze prolungate o nodi non registrati."
        actions={
          <>
            {loadError ? (
              <ModuleWorkspaceNoticeCard title="Caricamento non riuscito" description={loadError} tone="danger" />
            ) : (
              <ModuleWorkspaceNoticeCard
                title="Scansione manuale"
                description="Avvia un nuovo giro di rilevamento quando serve aggiornare subito la vista senza attendere i job schedulati."
              />
            )}
            <button className="btn-primary w-fit" onClick={handleScanTrigger} type="button" disabled={isTriggeringScan}>
              <RefreshIcon className="h-4 w-4" />
              {isTriggeringScan ? "Scansione in corso" : "Avvia scansione"}
            </button>
          </>
        }
      >
        <ModuleWorkspaceKpiRow>
          <ModuleWorkspaceKpiTile label="Dispositivi" variant="emerald" value={summary.total_devices} hint="host in anagrafica" />
          <ModuleWorkspaceKpiTile label="Online" variant="emerald" value={summary.online_devices} hint="raggiungibili" />
          <ModuleWorkspaceKpiTile
            label="Offline"
            variant={summary.offline_devices > 0 ? "amber" : "default"}
            value={summary.offline_devices}
            hint="non rilevati"
          />
          <ModuleWorkspaceKpiTile
            label="Alert"
            variant={summary.open_alerts > 0 ? "amber" : "default"}
            value={summary.open_alerts}
            hint="sconosciuti / assenti"
          />
          <ModuleWorkspaceKpiTile
            label="Firewall"
            variant={summary.firewalls_online > 0 ? "emerald" : "amber"}
            value={summary.firewalls_online}
            hint="sorgenti attive"
          />
        </ModuleWorkspaceKpiRow>
      </ModuleWorkspaceHero>

      <article className="panel-card">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="section-title">Filtri dashboard</p>
            <p className="section-copy">Applica gli stessi criteri ai blocchi dispositivi della panoramica.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <select className="form-control min-w-[190px]" value={lifecycleFilter} onChange={(event) => setLifecycleFilter(event.target.value as DashboardLifecycleFilter)}>
              <option value="all">Tutti i cicli vita</option>
              <option value="active">Attivi ({activeDevicesCount})</option>
              <option value="retired">Rotamati ({retiredDevicesCount})</option>
            </select>
            <select className="form-control min-w-[210px]" value={assignmentFilter} onChange={(event) => setAssignmentFilter(event.target.value as DashboardAssignmentFilter)}>
              <option value="all">Tutte le assegnazioni</option>
              <option value="assigned">Con utente ({assignedDevicesCount})</option>
              <option value="unassigned">Senza utente ({unassignedDevicesCount})</option>
            </select>
          </div>
        </div>
      </article>

      <div className="grid gap-6 xl:grid-cols-4">
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
                    <p className="text-sm font-medium text-gray-900">{device.resolved_label || device.display_name || device.hostname || device.ip_address}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {device.ip_address} · {device.mac_address || "MAC n/d"}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {device.assigned_user?.is_placeholder_profile ? <Badge variant="warning">Profilo placeholder</Badge> : null}
                      {device.lifecycle_state === "retired" ? <Badge variant="neutral">Rotamato</Badge> : null}
                    </div>
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
              <p className="section-title">Device non assegnati</p>
              <p className="section-copy">Host senza collegamento a `application_users`.</p>
            </div>
            <BadgeCount value={unassignedDevices.length} />
          </div>

          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento dispositivi in corso.</p>
          ) : unassignedDevices.length === 0 ? (
            <EmptyState
              icon={ServerIcon}
              title="Nessun device non assegnato"
              description="Tutti i dispositivi recenti hanno gia un utente o un profilo collegato."
            />
          ) : (
            <div className="max-h-[28rem] space-y-3 overflow-y-auto pr-1">
              {unassignedDevices.map((device) => (
                <button
                  key={device.id}
                  type="button"
                  onClick={() => setSelectedDeviceId(device.id)}
                  className="flex w-full items-center justify-between rounded-lg border border-amber-100 bg-amber-50/40 px-4 py-3 text-left transition hover:bg-amber-50"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">{device.resolved_label || device.display_name || device.hostname || device.ip_address}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {device.ip_address} · {device.device_type || "tipo n/d"}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Badge variant="warning">Senza utente</Badge>
                      {device.is_known_device ? <Badge variant="info">Conosciuto</Badge> : null}
                    </div>
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
              <p className="section-title">Firewall Sophos</p>
              <p className="section-copy">Stato appliance, ultima visibilità e metriche SNMP recenti.</p>
            </div>
            <Link href="/network/firewalls" className="text-sm font-medium text-[#1D4E35]">
              Apri firewall
            </Link>
          </div>

          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento firewall in corso.</p>
          ) : firewalls.length === 0 ? (
            <EmptyState
              icon={ServerIcon}
              title="Nessun firewall configurato"
              description="La telemetria Sophos non ha ancora registrato appliance nel modulo rete."
            />
          ) : (
            <div className="space-y-3">
              {firewalls.slice(0, 1).map((firewall) => (
                <div key={firewall.id} className="rounded-lg border border-gray-100 px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{firewall.name}</p>
                      <p className="mt-1 text-xs text-gray-500">
                        {firewall.management_ip || "IP gestione n/d"} · {firewall.model_name || firewall.vendor}
                      </p>
                    </div>
                    <NetworkStatusBadge status={firewall.status} />
                  </div>
                  <div className="mt-3 space-y-2">
                    {firewallMetrics.length === 0 ? (
                      <p className="text-xs text-gray-500">Nessuna metrica SNMP ancora registrata.</p>
                    ) : (
                      firewallMetrics.map((metric) => (
                        <div key={metric.id} className="flex items-center justify-between gap-3 text-xs">
                          <span className="text-gray-500">{metric.metric_key}</span>
                          <span className="font-medium text-gray-800">
                            {metric.metric_text ?? metric.metric_value ?? "n/d"}{metric.unit ? ` ${metric.unit}` : ""}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
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
                    <p className="text-sm font-medium text-gray-900">{device.resolved_label || device.display_name || device.hostname || device.ip_address}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {device.ip_address} · {device.mac_address || "MAC n/d"} · {device.device_type || "tipo n/d"}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {device.assigned_user?.is_placeholder_profile ? <Badge variant="warning">Profilo placeholder</Badge> : null}
                      {device.lifecycle_state === "retired" ? <Badge variant="neutral">Rotamato</Badge> : null}
                      {!device.assigned_user_id && device.lifecycle_state !== "retired" ? <Badge variant="warning">Senza utente</Badge> : null}
                    </div>
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

        <article className="panel-card xl:col-span-1">
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
