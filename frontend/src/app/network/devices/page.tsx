"use client";

import { type ColumnDef, type SortingState } from "@tanstack/react-table";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { NetworkDeviceModal } from "@/components/network/network-device-modal";
import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { DataTable } from "@/components/table/data-table";
import { Badge } from "@/components/ui/badge";
import { bulkUpdateNetworkDevices, getNetworkDevices } from "@/lib/api";
import { formatIpWithReference } from "@/lib/network-device-utils";
import type { NetworkDevice } from "@/types/api";

const DEFAULT_SORTING: SortingState = [
  { id: "status_order", desc: false },
  { id: "ip_address_order", desc: false },
];

type DeviceKnowledgeFilter = "all" | "known" | "unknown" | "arp_unknown";
type DeviceLifecycleFilter = "all" | "active" | "retired";
type DeviceAssignmentFilter = "all" | "assigned" | "unassigned";

function toComparableIp(ipAddress: string): number {
  const parts = ipAddress.split(".").map((part) => Number(part));
  if (parts.length !== 4 || parts.some((part) => Number.isNaN(part) || part < 0 || part > 255)) {
    return Number.MAX_SAFE_INTEGER;
  }
  return (((parts[0] * 256 + parts[1]) * 256 + parts[2]) * 256) + parts[3];
}

function statusOrder(status: string): number {
  if (status === "online") {
    return 0;
  }
  if (status === "warning") {
    return 1;
  }
  return 2;
}

function getLastOnlineAt(device: NetworkDevice): string | null {
  const lastOnlineSnapshot = device.scan_history.find((entry) => entry.status === "online");
  const candidate = lastOnlineSnapshot?.observed_at || device.last_seen_at;
  return candidate ? new Date(candidate).toLocaleString("it-IT") : null;
}

const columns: ColumnDef<NetworkDevice>[] = [
  {
    id: "host",
    accessorFn: (row) => row.resolved_label || row.display_name || row.hostname || row.ip_address,
    header: "Host",
    sortingFn: (left, right) => {
      const leftValue = (left.original.resolved_label || left.original.display_name || left.original.hostname || left.original.ip_address).toLowerCase();
      const rightValue = (right.original.resolved_label || right.original.display_name || right.original.hostname || right.original.ip_address).toLowerCase();
      return leftValue.localeCompare(rightValue, "it");
    },
    cell: ({ row }) => (
      <div>
        <p className="font-medium text-gray-900">{row.original.resolved_label || row.original.display_name || row.original.hostname || row.original.ip_address}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          {row.original.lifecycle_state === "retired" ? <Badge variant="neutral">Rotamato</Badge> : null}
          {row.original.metadata_sources?.discovery === "arp" && !row.original.is_known_device ? (
            <Badge variant="warning">Da ARP</Badge>
          ) : null}
          <span className="text-xs text-gray-500">
            {row.original.assigned_user?.username
              ? `Utente ${row.original.assigned_user.username}`
              : row.original.hostname || row.original.dns_name || "Host non risolto"}
          </span>
        </div>
        <p className="text-xs text-gray-500">{formatIpWithReference(row.original)}</p>
      </div>
    ),
  },
  {
    id: "status_order",
    accessorFn: (row) => statusOrder(row.status),
    header: "Stato",
    sortingFn: (left, right) => statusOrder(left.original.status) - statusOrder(right.original.status),
    cell: ({ row }) => (
      <div>
        <NetworkStatusBadge status={row.original.status} />
        {row.original.status === "offline" ? (
          <p className="mt-1 text-xs text-gray-500">Ultimo online: {getLastOnlineAt(row.original) || "n/d"}</p>
        ) : null}
      </div>
    ),
  },
  {
    id: "ip_address_order",
    accessorFn: (row) => toComparableIp(row.ip_address),
    header: "IP",
    sortingFn: (left, right) => toComparableIp(left.original.ip_address) - toComparableIp(right.original.ip_address),
    cell: ({ row }) => (
      <div>
        <p className="text-sm text-gray-900">{row.original.ip_address}</p>
        <p className="text-xs text-gray-500">{row.original.assigned_user?.full_name || row.original.assigned_user?.username || row.original.resolved_label}</p>
      </div>
    ),
  },
  {
    accessorKey: "mac_address",
    header: "MAC",
    cell: ({ row }) => row.original.mac_address || "n/d",
  },
  {
    accessorKey: "asset_label",
    header: "Label",
    cell: ({ row }) =>
      row.original.asset_label ? <Badge variant="info">{row.original.asset_label}</Badge> : <span className="text-gray-400">n/d</span>,
  },
  {
    accessorKey: "notes",
    header: "Note",
    cell: ({ row }) => (
      <div className="max-w-xs text-sm text-gray-700">
        {row.original.notes ? <p className="line-clamp-3">{row.original.notes}</p> : <span className="text-gray-400">n/d</span>}
      </div>
    ),
  },
  {
    accessorKey: "device_type",
    header: "Tipo",
    cell: ({ row }) => row.original.device_type || "n/d",
  },
  {
    accessorKey: "model_name",
    header: "Modello",
    cell: ({ row }) => row.original.model_name || row.original.vendor || "n/d",
  },
  {
    accessorKey: "open_ports",
    header: "Porte",
    cell: ({ row }) => row.original.open_ports || "n/d",
  },
];

function DevicesContent({ token }: { token: string }) {
  const searchParams = useSearchParams();
  const [items, setItems] = useState<NetworkDevice[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [knowledgeFilter, setKnowledgeFilter] = useState<DeviceKnowledgeFilter>(() => {
    const initialValue = searchParams.get("known");
    if (initialValue === "known" || initialValue === "unknown" || initialValue === "arp_unknown") {
      return initialValue;
    }
    return "all";
  });
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [lifecycleFilter, setLifecycleFilter] = useState<DeviceLifecycleFilter>(() => {
    const initialValue = searchParams.get("lifecycle");
    if (initialValue === "active" || initialValue === "retired") {
      return initialValue;
    }
    return "all";
  });
  const [assignmentFilter, setAssignmentFilter] = useState<DeviceAssignmentFilter>(() => {
    const initialValue = searchParams.get("assignment");
    if (initialValue === "assigned" || initialValue === "unassigned") {
      return initialValue;
    }
    return "all";
  });
  const [deviceType, setDeviceType] = useState(searchParams.get("type") ?? "");
  const [vendor, setVendor] = useState(searchParams.get("vendor") ?? "");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [bulkLocation, setBulkLocation] = useState("");
  const [bulkNote, setBulkNote] = useState("");
  const [isBulkSaving, setIsBulkSaving] = useState(false);
  const [bulkMessage, setBulkMessage] = useState<string | null>(null);

  useEffect(() => {
    async function loadDevices() {
      try {
        const response = await getNetworkDevices(token, {
          pageSize: 126,
        });
        setItems(response.items);
        setTotal(Math.min(response.total, 126));
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento dispositivi");
      }
    }

    void loadDevices();
  }, [token]);

  function handleDeviceUpdated(updatedDevice: NetworkDevice) {
    setItems((currentItems) => currentItems.map((item) => (item.id === updatedDevice.id ? { ...item, ...updatedDevice } : item)));
  }

  function toggleSelected(deviceId: number) {
    setSelectedIds((current) => (current.includes(deviceId) ? current.filter((value) => value !== deviceId) : [...current, deviceId]));
  }

  async function applyBulkUpdate(payload: { is_known_device?: boolean | null; location_hint?: string | null; notes_append?: string | null }) {
    if (selectedIds.length === 0) {
      return;
    }
    setIsBulkSaving(true);
    setBulkMessage(null);
    setLoadError(null);
    try {
      const response = await bulkUpdateNetworkDevices(token, {
        device_ids: selectedIds,
        ...payload,
      });
      setItems((currentItems) => {
        const updatedById = new Map(response.items.map((item) => [item.id, item]));
        return currentItems.map((item) => updatedById.get(item.id) ?? item);
      });
      setBulkMessage(`${response.updated_count} dispositivi aggiornati.`);
      setSelectedIds([]);
      if (payload.location_hint !== undefined) {
        setBulkLocation("");
      }
      if (payload.notes_append !== undefined) {
        setBulkNote("");
      }
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore aggiornamento massivo dispositivi");
    } finally {
      setIsBulkSaving(false);
    }
  }

  const normalizedSearch = search.trim().toLowerCase();
  const filteredItems = items.filter((item) => {
    const searchHaystack = [
      item.resolved_label,
      item.display_name,
      item.hostname,
      item.ip_address,
      item.mac_address,
      item.asset_label,
      item.notes,
      item.assigned_user?.username,
      item.assigned_user?.full_name,
      item.vendor,
      item.model_name,
      item.device_type,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    if (normalizedSearch && !searchHaystack.includes(normalizedSearch)) {
      return false;
    }
    if (knowledgeFilter === "known" && !item.is_known_device) {
      return false;
    }
    if (knowledgeFilter === "unknown" && item.is_known_device) {
      return false;
    }
    if (knowledgeFilter === "arp_unknown" && (item.is_known_device || item.metadata_sources?.discovery !== "arp")) {
      return false;
    }
    if (status && item.status !== status) {
      return false;
    }
    if (lifecycleFilter === "active" && item.lifecycle_state !== "active") {
      return false;
    }
    if (lifecycleFilter === "retired" && item.lifecycle_state !== "retired") {
      return false;
    }
    if (assignmentFilter === "assigned" && !item.assigned_user_id) {
      return false;
    }
    if (assignmentFilter === "unassigned" && (item.assigned_user_id || item.lifecycle_state === "retired")) {
      return false;
    }
    if (deviceType && item.device_type !== deviceType) {
      return false;
    }
    if (vendor && item.vendor !== vendor) {
      return false;
    }
    return true;
  });

  const knownDevicesCount = items.filter((item) => item.is_known_device).length;
  const unknownDevicesCount = items.length - knownDevicesCount;
  const arpUnknownDevicesCount = items.filter((item) => !item.is_known_device && item.metadata_sources?.discovery === "arp").length;
  const activeDevicesCount = items.filter((item) => item.lifecycle_state === "active").length;
  const retiredDevicesCount = items.filter((item) => item.lifecycle_state === "retired").length;
  const assignedDevicesCount = items.filter((item) => Boolean(item.assigned_user_id)).length;
  const unassignedDevicesCount = items.filter((item) => !item.assigned_user_id && item.lifecycle_state !== "retired").length;

  const availableDeviceTypes = Array.from(new Set(items.map((item) => item.device_type).filter(Boolean))).sort((left, right) => (left || "").localeCompare(right || "", "it"));
  const availableVendors = Array.from(new Set(items.map((item) => item.vendor).filter(Boolean))).sort((left, right) => (left || "").localeCompare(right || "", "it"));
  const selectedDevicesCount = selectedIds.length;
  const columnsWithSelection: ColumnDef<NetworkDevice>[] = [
    {
      id: "select",
      header: "",
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={selectedIds.includes(row.original.id)}
          onChange={() => toggleSelected(row.original.id)}
          onClick={(event) => event.stopPropagation()}
          className="h-4 w-4 rounded border-gray-300"
          aria-label={`Seleziona dispositivo ${row.original.resolved_label || row.original.ip_address}`}
        />
      ),
      enableSorting: false,
    },
    ...columns,
  ];

  return (
    <div className="page-stack">
      <article className="panel-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="section-title">Azioni massive</p>
            <p className="section-copy">Seleziona piu device per accelerare la presa in carico di host sconosciuti, soprattutto quelli emersi da ARP.</p>
          </div>
          <Badge variant={selectedDevicesCount > 0 ? "warning" : "neutral"}>{selectedDevicesCount} selezionati</Badge>
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-[auto_auto_minmax(0,260px)_minmax(0,320px)]">
          <button
            className="btn-secondary"
            type="button"
            disabled={selectedDevicesCount === 0 || isBulkSaving}
            onClick={() => void applyBulkUpdate({ is_known_device: true })}
          >
            Segna come noti
          </button>
          <button
            className="btn-secondary"
            type="button"
            disabled={selectedDevicesCount === 0 || isBulkSaving}
            onClick={() => setSelectedDeviceId(selectedIds[0] ?? null)}
          >
            Apri primo selezionato
          </button>
          <div className="flex gap-2">
            <input
              className="form-control"
              value={bulkLocation}
              onChange={(event) => setBulkLocation(event.target.value)}
              placeholder="Location comune"
            />
            <button
              className="btn-secondary whitespace-nowrap"
              type="button"
              disabled={selectedDevicesCount === 0 || isBulkSaving || !bulkLocation.trim()}
              onClick={() => void applyBulkUpdate({ location_hint: bulkLocation.trim() })}
            >
              Imposta location
            </button>
          </div>
          <div className="flex gap-2">
            <input
              className="form-control"
              value={bulkNote}
              onChange={(event) => setBulkNote(event.target.value)}
              placeholder="Nota operativa da aggiungere"
            />
            <button
              className="btn-secondary whitespace-nowrap"
              type="button"
              disabled={selectedDevicesCount === 0 || isBulkSaving || !bulkNote.trim()}
              onClick={() => void applyBulkUpdate({ notes_append: bulkNote.trim() })}
            >
              Aggiungi nota
            </button>
          </div>
        </div>
        {bulkMessage ? <p className="mt-3 text-sm text-emerald-700">{bulkMessage}</p> : null}
      </article>
      <article className="panel-card">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="inline-flex rounded-xl border border-gray-200 bg-gray-50 p-1">
            <button
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                knowledgeFilter === "all" ? "bg-white text-gray-900 shadow-sm" : "text-gray-600 hover:text-gray-900"
              }`}
              type="button"
              onClick={() => setKnowledgeFilter("all")}
            >
              Tutti
            </button>
            <button
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                knowledgeFilter === "known" ? "bg-white text-[#1D4E35] shadow-sm" : "text-gray-600 hover:text-gray-900"
              }`}
              type="button"
              onClick={() => setKnowledgeFilter("known")}
            >
              Conosciuti ({knownDevicesCount})
            </button>
            <button
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                knowledgeFilter === "unknown" ? "bg-white text-amber-700 shadow-sm" : "text-gray-600 hover:text-gray-900"
              }`}
              type="button"
              onClick={() => setKnowledgeFilter("unknown")}
            >
              Sconosciuti ({unknownDevicesCount})
            </button>
            <button
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                knowledgeFilter === "arp_unknown" ? "bg-white text-orange-700 shadow-sm" : "text-gray-600 hover:text-gray-900"
              }`}
              type="button"
              onClick={() => setKnowledgeFilter("arp_unknown")}
            >
              Da ARP ({arpUnknownDevicesCount})
            </button>
          </div>
          <p className="text-xs text-gray-500">Filtra rapidamente l&apos;inventario tra dispositivi censiti, sconosciuti e host emersi dalla discovery ARP da censire.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[minmax(0,1.4fr)_180px_190px_190px_220px_220px_auto]">
          <input
            className="form-control"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Cerca per IP, hostname, MAC, label o note"
          />
          <select className="form-control" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Tutti gli stati</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
          </select>
          <select className="form-control" value={lifecycleFilter} onChange={(event) => setLifecycleFilter(event.target.value as DeviceLifecycleFilter)}>
            <option value="all">Tutti i cicli vita</option>
            <option value="active">Attivi ({activeDevicesCount})</option>
            <option value="retired">Rotamati ({retiredDevicesCount})</option>
          </select>
          <select className="form-control" value={assignmentFilter} onChange={(event) => setAssignmentFilter(event.target.value as DeviceAssignmentFilter)}>
            <option value="all">Tutte le assegnazioni</option>
            <option value="assigned">Con utente ({assignedDevicesCount})</option>
            <option value="unassigned">Senza utente ({unassignedDevicesCount})</option>
          </select>
          <select className="form-control" value={deviceType} onChange={(event) => setDeviceType(event.target.value)}>
            <option value="">Tutti i tipi</option>
            {availableDeviceTypes.map((value) => (
              <option key={value} value={value || ""}>
                {value}
              </option>
            ))}
          </select>
          <select className="form-control" value={vendor} onChange={(event) => setVendor(event.target.value)}>
            <option value="">Tutti i vendor</option>
            {availableVendors.map((value) => (
              <option key={value} value={value || ""}>
                {value}
              </option>
            ))}
          </select>
          <div className="flex items-center rounded-lg bg-gray-50 px-4 text-sm text-gray-500">
            <span>{filteredItems.length} di {total} dispositivi</span>
          </div>
        </div>
        <p className="mt-3 text-xs text-gray-500">La vista carica i primi 126 dispositivi e li ordina di default per stato online e indirizzo IP.</p>
        {loadError ? <p className="mt-4 text-sm text-red-600">{loadError}</p> : null}
      </article>

      <DataTable
        data={filteredItems}
        columns={columnsWithSelection}
        initialPageSize={63}
        initialSorting={DEFAULT_SORTING}
        onRowClick={(row) => setSelectedDeviceId(row.id)}
      />

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

export default function NetworkDevicesPage() {
  return (
    <NetworkModulePage
      title="Dispositivi"
      description="Inventario operativo dei dispositivi di rete rilevati dalle scansioni GAIA Rete."
      breadcrumb="Lista"
    >
      {({ token }) => <DevicesContent token={token} />}
    </NetworkModulePage>
  );
}
