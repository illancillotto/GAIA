"use client";

import { type ColumnDef, type SortingState } from "@tanstack/react-table";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { NetworkDeviceModal } from "@/components/network/network-device-modal";
import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { DataTable } from "@/components/table/data-table";
import { Badge } from "@/components/ui/badge";
import { getNetworkDevices } from "@/lib/api";
import type { NetworkDevice } from "@/types/api";

const DEFAULT_SORTING: SortingState = [
  { id: "status_order", desc: false },
  { id: "ip_address_order", desc: false },
];

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

const columns: ColumnDef<NetworkDevice>[] = [
  {
    id: "host",
    accessorFn: (row) => row.display_name || row.hostname || row.ip_address,
    header: "Host",
    sortingFn: (left, right) => {
      const leftValue = (left.original.display_name || left.original.hostname || left.original.ip_address).toLowerCase();
      const rightValue = (right.original.display_name || right.original.hostname || right.original.ip_address).toLowerCase();
      return leftValue.localeCompare(rightValue, "it");
    },
    cell: ({ row }) => (
      <div>
        <p className="font-medium text-gray-900">{row.original.display_name || row.original.hostname || row.original.ip_address}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <span className="text-xs text-gray-500">{row.original.hostname || row.original.dns_name || "Host non risolto"}</span>
        </div>
        <p className="text-xs text-gray-500">{row.original.ip_address}</p>
      </div>
    ),
  },
  {
    id: "status_order",
    accessorFn: (row) => statusOrder(row.status),
    header: "Stato",
    sortingFn: (left, right) => statusOrder(left.original.status) - statusOrder(right.original.status),
    cell: ({ row }) => <NetworkStatusBadge status={row.original.status} />,
  },
  {
    id: "ip_address_order",
    accessorFn: (row) => toComparableIp(row.ip_address),
    header: "IP",
    sortingFn: (left, right) => toComparableIp(left.original.ip_address) - toComparableIp(right.original.ip_address),
    cell: ({ row }) => row.original.ip_address,
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
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [deviceType, setDeviceType] = useState(searchParams.get("type") ?? "");
  const [vendor, setVendor] = useState(searchParams.get("vendor") ?? "");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null);

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

  const normalizedSearch = search.trim().toLowerCase();
  const filteredItems = items.filter((item) => {
    const searchHaystack = [
      item.display_name,
      item.hostname,
      item.ip_address,
      item.mac_address,
      item.asset_label,
      item.notes,
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
    if (status && item.status !== status) {
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

  const availableDeviceTypes = Array.from(new Set(items.map((item) => item.device_type).filter(Boolean))).sort((left, right) => (left || "").localeCompare(right || "", "it"));
  const availableVendors = Array.from(new Set(items.map((item) => item.vendor).filter(Boolean))).sort((left, right) => (left || "").localeCompare(right || "", "it"));

  return (
    <div className="page-stack">
      <article className="panel-card">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[minmax(0,1.4fr)_180px_220px_220px_auto]">
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
        columns={columns}
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
