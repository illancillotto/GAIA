"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { getNetworkDevice, updateNetworkDevice } from "@/lib/api";
import type { NetworkDevice } from "@/types/api";

function DeviceDetailContent({ token, deviceId }: { token: string; deviceId: number }) {
  const [device, setDevice] = useState<NetworkDevice | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [assetLabel, setAssetLabel] = useState("");
  const [locationHint, setLocationHint] = useState("");
  const [notes, setNotes] = useState("");
  const [deviceType, setDeviceType] = useState("");
  const [operatingSystem, setOperatingSystem] = useState("");
  const [modelName, setModelName] = useState("");
  const [isMonitored, setIsMonitored] = useState(true);

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

  useEffect(() => {
    if (!device) {
      return;
    }
    setDisplayName(device.display_name || "");
    setAssetLabel(device.asset_label || "");
    setLocationHint(device.location_hint || "");
    setNotes(device.notes || "");
    setDeviceType(device.device_type || "");
    setOperatingSystem(device.operating_system || "");
    setModelName(device.model_name || "");
    setIsMonitored(device.is_monitored);
  }, [device]);

  async function handleSave() {
    if (!device) {
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaveMessage(null);

    try {
      const updated = await updateNetworkDevice(token, device.id, {
        display_name: displayName || null,
        asset_label: assetLabel || null,
        location_hint: locationHint || null,
        notes: notes || null,
        model_name: modelName || null,
        device_type: deviceType || null,
        operating_system: operatingSystem || null,
        is_monitored: isMonitored,
      });
      setDevice(updated);
      setSaveMessage("Metadati dispositivo aggiornati.");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore salvataggio dispositivo");
    } finally {
      setIsSaving(false);
    }
  }

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
            <p className="mt-1 text-lg font-medium text-gray-900">{device.display_name || device.hostname || device.ip_address}</p>
            <p className="mt-1 text-sm text-gray-500">{device.asset_label || device.dns_name || "Nessuna etichetta assegnata"}</p>
          </div>
          <NetworkStatusBadge status={device.status} />
        </div>
        <dl className="mt-5 grid gap-4 md:grid-cols-2">
          <div>
            <dt className="label-caption">IP</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.ip_address}</dd>
          </div>
          <div>
            <dt className="label-caption">Nome assegnato</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.display_name || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">Asset label</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.asset_label || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">MAC</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.mac_address || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">DNS</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.dns_name || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">Sorgente nome</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.hostname_source || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">Vendor</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.vendor || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">Modello</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.model_name || "n/d"}</dd>
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
          <div>
            <dt className="label-caption">Posizione</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.location_hint || "n/d"}</dd>
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

      <article className="panel-card xl:col-span-2">
        <div className="mb-4">
          <p className="section-title">Sorgenti rilevazione</p>
          <p className="section-copy">Origine del nome e dei metadati osservati automaticamente durante le scansioni.</p>
        </div>
        <dl className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div>
            <dt className="label-caption">Hostname attivo</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.hostname || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">Fonte hostname</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.hostname_source || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">DNS</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.metadata_sources?.dns || device.dns_name || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">mDNS</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.metadata_sources?.mdns || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">NetBIOS</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.metadata_sources?.netbios || "n/d"}</dd>
          </div>
          <div>
            <dt className="label-caption">SNMP community</dt>
            <dd className="mt-1 text-sm text-gray-800">{device.metadata_sources?.snmp || "n/d"}</dd>
          </div>
        </dl>
      </article>

      <article className="panel-card xl:col-span-2">
        <div className="mb-4">
          <p className="section-title">Anagrafica interna</p>
          <p className="section-copy">Nome leggibile, etichetta apparato e note operative assegnate manualmente.</p>
        </div>
        {saveError ? <p className="mb-3 text-sm text-red-600">{saveError}</p> : null}
        {saveMessage ? <p className="mb-3 text-sm text-[#1D4E35]">{saveMessage}</p> : null}
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block text-sm font-medium text-gray-700">
            Nome dispositivo
            <input className="form-control mt-1" value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="es. Switch Core Piano Terra" />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Asset label
            <input className="form-control mt-1" value={assetLabel} onChange={(event) => setAssetLabel(event.target.value)} placeholder="es. SW-PT-01" />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Modello
            <input className="form-control mt-1" value={modelName} onChange={(event) => setModelName(event.target.value)} placeholder="es. CRS326-24G-2S+, DS920+, LaserJet M404" />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Tipo dispositivo
            <input className="form-control mt-1" value={deviceType} onChange={(event) => setDeviceType(event.target.value)} placeholder="es. switch, printer, server" />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Sistema operativo
            <input className="form-control mt-1" value={operatingSystem} onChange={(event) => setOperatingSystem(event.target.value)} placeholder="es. Windows 11, RouterOS, Synology DSM" />
          </label>
          <label className="block text-sm font-medium text-gray-700 md:col-span-2">
            Posizione / ufficio
            <input className="form-control mt-1" value={locationHint} onChange={(event) => setLocationHint(event.target.value)} placeholder="es. CED piano terra, ufficio protocollo, corridoio rack" />
          </label>
          <label className="block text-sm font-medium text-gray-700 md:col-span-2">
            Note
            <textarea className="form-control mt-1 min-h-28" value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Annotazioni utili per riconoscere o gestire il dispositivo." />
          </label>
          <label className="flex items-center gap-3 text-sm font-medium text-gray-700 md:col-span-2">
            <input checked={isMonitored} onChange={(event) => setIsMonitored(event.target.checked)} type="checkbox" />
            Monitoraggio attivo
          </label>
        </div>
        <div className="mt-4 flex justify-end">
          <button className="btn-primary" onClick={() => void handleSave()} type="button" disabled={isSaving}>
            {isSaving ? "Salvataggio..." : "Salva metadati"}
          </button>
        </div>
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
