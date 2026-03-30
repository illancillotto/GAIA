"use client";

import Link from "next/link";
import { type ColumnDef } from "@tanstack/react-table";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { DataTable } from "@/components/table/data-table";
import { Badge } from "@/components/ui/badge";
import { getNetworkDevice, getNetworkDevices } from "@/lib/api";
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
  const searchParams = useSearchParams();
  const [items, setItems] = useState<NetworkDevice[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null);
  const [selectedDevice, setSelectedDevice] = useState<NetworkDevice | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

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

  function closeModal() {
    setSelectedDeviceId(null);
    setSelectedDevice(null);
    setDetailError(null);
  }

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

      <DataTable data={items} columns={columns} initialPageSize={12} onRowClick={(row) => setSelectedDeviceId(row.id)} />

      {selectedDeviceId ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
            <div className="sticky top-0 flex items-start justify-between gap-4 border-b border-gray-100 bg-white px-6 py-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Dettaglio dispositivo</p>
                <h2 className="mt-2 text-2xl font-semibold text-gray-900">
                  {selectedDevice?.display_name || selectedDevice?.hostname || selectedDevice?.ip_address || `Dispositivo #${selectedDeviceId}`}
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  Vista rapida senza lasciare la lista dispositivi.
                </p>
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
