"use client";

import Link from "next/link";
import { type ColumnDef } from "@tanstack/react-table";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { DataTable } from "@/components/table/data-table";
import { Badge } from "@/components/ui/badge";
import { getNetworkDevices } from "@/lib/api";
import type { NetworkDevice } from "@/types/api";

const columns: ColumnDef<NetworkDevice>[] = [
  {
    accessorKey: "hostname",
    header: "Host",
    cell: ({ row }) => (
      <div>
        <p className="font-medium text-gray-900">{row.original.display_name || row.original.hostname || row.original.ip_address}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          {row.original.asset_label ? <Badge variant="info">{row.original.asset_label}</Badge> : null}
          <span className="text-xs text-gray-500">{row.original.hostname || row.original.dns_name || "Host non risolto"}</span>
        </div>
        <p className="text-xs text-gray-500">{row.original.ip_address}</p>
      </div>
    ),
  },
  {
    accessorKey: "status",
    header: "Stato",
    cell: ({ row }) => <NetworkStatusBadge status={row.original.status} />,
  },
  {
    accessorKey: "mac_address",
    header: "MAC",
    cell: ({ row }) => row.original.mac_address || "n/d",
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
  const router = useRouter();
  const searchParams = useSearchParams();
  const [items, setItems] = useState<NetworkDevice[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDevices() {
      try {
        const response = await getNetworkDevices(token, {
          search: search || undefined,
          status: status || undefined,
          pageSize: 100,
        });
        setItems(response.items);
        setTotal(response.total);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento dispositivi");
      }
    }

    void loadDevices();
  }, [search, status, token]);

  return (
    <div className="page-stack">
      <article className="panel-card">
        <div className="grid gap-4 md:grid-cols-[1fr_180px_auto]">
          <input
            className="form-control"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Cerca per IP, hostname o MAC"
          />
          <select className="form-control" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Tutti gli stati</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
          </select>
          <div className="flex items-center justify-between rounded-lg bg-gray-50 px-4 text-sm text-gray-500">
            <span>{total} dispositivi</span>
            <Link href="/network/scans" className="font-medium text-[#1D4E35]">
              Storico scansioni
            </Link>
          </div>
        </div>
        {loadError ? <p className="mt-4 text-sm text-red-600">{loadError}</p> : null}
      </article>

      <DataTable data={items} columns={columns} initialPageSize={12} onRowClick={(row) => router.push(`/network/devices/${row.id}`)} />
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
