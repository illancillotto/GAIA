"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { getNetworkDevice, updateNetworkDevice } from "@/lib/api";
import { getNetworkDeviceAdminUrl } from "@/lib/network-device-utils";
import type { NetworkDevice } from "@/types/api";

type NetworkDeviceModalProps = {
  token: string;
  deviceId: number | null;
  open: boolean;
  onClose: () => void;
  onUpdated?: (device: NetworkDevice) => void;
};

export function NetworkDeviceModal({ token, deviceId, open, onClose, onUpdated }: NetworkDeviceModalProps) {
  const [selectedDevice, setSelectedDevice] = useState<NetworkDevice | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [assetLabel, setAssetLabel] = useState("");
  const [notes, setNotes] = useState("");
  const [isKnownDevice, setIsKnownDevice] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const adminUrl = selectedDevice ? getNetworkDeviceAdminUrl(selectedDevice) : null;

  useEffect(() => {
    async function loadDeviceDetail() {
      if (!open || !deviceId) {
        setSelectedDevice(null);
        setDetailError(null);
        setSaveError(null);
        setSaveMessage(null);
        return;
      }

      setIsLoadingDetail(true);
      try {
        const response = await getNetworkDevice(token, deviceId);
        setSelectedDevice(response);
        setDisplayName(response.display_name || "");
        setAssetLabel(response.asset_label || "");
        setNotes(response.notes || "");
        setIsKnownDevice(response.is_known_device);
        setDetailError(null);
      } catch (error) {
        setDetailError(error instanceof Error ? error.message : "Errore nel caricamento dettaglio dispositivo");
      } finally {
        setIsLoadingDetail(false);
      }
    }

    void loadDeviceDetail();
  }, [deviceId, open, token]);

  async function handleSave() {
    if (!selectedDevice) {
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaveMessage(null);

    try {
      const updated = await updateNetworkDevice(token, selectedDevice.id, {
        display_name: displayName || null,
        asset_label: assetLabel || null,
        notes: notes || null,
        is_known_device: isKnownDevice,
      });
      setSelectedDevice(updated);
      setDisplayName(updated.display_name || "");
      setAssetLabel(updated.asset_label || "");
      setNotes(updated.notes || "");
      setIsKnownDevice(updated.is_known_device);
      setSaveMessage("Scheda dispositivo aggiornata.");
      onUpdated?.(updated);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Errore salvataggio dispositivo");
    } finally {
      setIsSaving(false);
    }
  }

  if (!open || !deviceId) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="sticky top-0 flex items-start justify-between gap-4 border-b border-gray-100 bg-white px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Dettaglio dispositivo</p>
            <h2 className="mt-2 text-2xl font-semibold text-gray-900">
              {selectedDevice?.display_name || selectedDevice?.hostname || selectedDevice?.ip_address || `Dispositivo #${deviceId}`}
            </h2>
            <p className="mt-1 text-sm text-gray-500">Vista rapida senza lasciare il contesto operativo.</p>
          </div>
          <button className="btn-secondary" type="button" onClick={onClose}>
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
                        {selectedDevice.asset_label || selectedDevice.dns_name || "Nessuna label assegnata"}
                      </p>
                      {adminUrl ? (
                        <a
                          href={adminUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-2 inline-flex text-sm font-medium text-[#1D4E35] underline underline-offset-4"
                        >
                          Apri pagina admin
                        </a>
                      ) : null}
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
                      <dt className="label-caption">Dispositivo conosciuto</dt>
                      <dd className="mt-1 text-sm text-gray-800">{selectedDevice.is_known_device ? "Si" : "No"}</dd>
                    </div>
                    <div>
                      <dt className="label-caption">Pagina admin</dt>
                      <dd className="mt-1 text-sm text-gray-800 break-all">
                        {adminUrl ? (
                          <a href={adminUrl} target="_blank" rel="noreferrer" className="text-[#1D4E35] underline underline-offset-4">
                            {adminUrl}
                          </a>
                        ) : (
                          "n/d"
                        )}
                      </dd>
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
                  <p className="section-title">Label e note operative</p>
                  <p className="section-copy">Etichette manuali per riconoscere rapidamente il dispositivo e annotazioni contestuali.</p>
                </div>
                {saveError ? <p className="mb-3 text-sm text-red-600">{saveError}</p> : null}
                {saveMessage ? <p className="mb-3 text-sm text-[#1D4E35]">{saveMessage}</p> : null}
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Nome dispositivo
                    <input
                      className="form-control mt-1"
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                      placeholder="es. Stampante Protocollo"
                    />
                  </label>
                  <label className="block text-sm font-medium text-gray-700">
                    Label dispositivo
                    <input
                      className="form-control mt-1"
                      value={assetLabel}
                      onChange={(event) => setAssetLabel(event.target.value)}
                      placeholder="es. PRN-PROT-01"
                    />
                  </label>
                  <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                    Note
                    <textarea
                      className="form-control mt-1 min-h-28"
                      value={notes}
                      onChange={(event) => setNotes(event.target.value)}
                      placeholder="Annotazioni utili per riconoscere o gestire il dispositivo."
                    />
                  </label>
                  <label className="flex items-center gap-3 text-sm font-medium text-gray-700 md:col-span-2">
                    <input checked={isKnownDevice} onChange={(event) => setIsKnownDevice(event.target.checked)} type="checkbox" />
                    Dispositivo conosciuto
                  </label>
                </div>
                <div className="mt-4 flex justify-end">
                  <button className="btn-primary" onClick={() => void handleSave()} type="button" disabled={isSaving}>
                    {isSaving ? "Salvataggio..." : "Salva label e note"}
                  </button>
                </div>
              </article>

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
                <Link href={`/network/devices/${selectedDevice.id}`} className="btn-secondary" onClick={onClose}>
                  Apri pagina completa
                </Link>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
