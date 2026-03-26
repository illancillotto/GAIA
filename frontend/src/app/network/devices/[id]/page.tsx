"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { getNetworkDevice } from "@/lib/api";
import type { NetworkDevice } from "@/types/api";

function DeviceDetailContent({ token, deviceId }: { token: string; deviceId: number }) {
  const [device, setDevice] = useState<NetworkDevice | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDevice() {
      try {
        const response = await getNetworkDevice(token, deviceId);
        setDevice(response);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento dispositivo");
      }
    }

    void loadDevice();
  }, [deviceId, token]);

  if (loadError) {
    return (
      <article className="panel-card">
        <p className="text-sm font-medium text-red-700">Dispositivo non disponibile</p>
        <p className="mt-2 text-sm text-gray-600">{loadError}</p>
      </article>
    );
  }

  if (!device) {
    return <article className="panel-card text-sm text-gray-500">Caricamento dettaglio dispositivo.</article>;
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <article className="panel-card">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="section-title">Identità dispositivo</p>
            <p className="mt-1 text-lg font-medium text-gray-900">{device.hostname || device.ip_address}</p>
          </div>
          <NetworkStatusBadge status={device.status} />
        </div>
        <dl className="mt-5 grid gap-4 md:grid-cols-2">
          <div>
            <dt className="label-caption">IP</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.ip_address}</dd>
          </div>
          <div>
            <dt className="label-caption">MAC</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.mac_address || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">Vendor</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.vendor || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">Tipo dispositivo</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.device_type || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">Sistema operativo</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.operating_system || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">Porte aperte</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.open_ports || "n/d"}</dd>
          </div>
        </dl>
      </article>

      <article className="panel-card">
        <p className="section-title">Timeline monitoraggio</p>
        <dl className="mt-5 space-y-4">
          <div>
            <dt className="label-caption">Prima rilevazione</dt>
            <dd className="mt-1 text-sm text-gray-800">{new Date(device.first_seen_at).toLocaleString("it-IT")}</dd>
          </div>
          <div>
            <dt className="label-caption">Ultima rilevazione</dt>
            <dd className="mt-1 text-sm text-gray-800">{new Date(device.last_seen_at).toLocaleString("it-IT")}</dd>
          </div>
          <div>
            <dt className="label-caption">Ultimo scan</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.last_scan_id ? `Snapshot #${device.last_scan_id}` : "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">Monitorato</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.is_monitored ? "Si" : "No"}</dd>
          </div>
        </dl>
      </article>
    </div>
  );
}

export default function NetworkDeviceDetailPage() {
  const params = useParams<{ id: string }>();
  const deviceId = Number(params.id);

  return (
    <NetworkModulePage
      title="Dettaglio dispositivo"
      description="Scheda tecnica del dispositivo rilevato, con stato corrente e metadati osservati in scansione."
      breadcrumb={`ID ${params.id}`}
    >
      {({ token }) => <DeviceDetailContent token={token} deviceId={deviceId} />}
    </NetworkModulePage>
  );
}
