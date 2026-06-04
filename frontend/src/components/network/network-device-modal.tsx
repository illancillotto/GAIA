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

function toTitleCase(value: string) {
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function formatEventType(eventType: string) {
  const parts = eventType.split(".").filter(Boolean);
  const action = parts.pop() ?? eventType;
  const context = parts.map((part) => toTitleCase(part)).join(" / ");
  const normalizedAction = action.toLowerCase();
  const actionTone =
    normalizedAction === "allowed"
      ? "bg-emerald-50 text-emerald-700 border-emerald-100"
      : normalizedAction === "denied" || normalizedAction === "blocked" || normalizedAction === "dropped"
        ? "bg-rose-50 text-rose-700 border-rose-100"
        : "bg-gray-50 text-gray-700 border-gray-100";
  return {
    context: context || "Evento Sophos",
    action: toTitleCase(action),
    actionTone,
  };
}

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

  function formatBytes(value: number) {
    if (!Number.isFinite(value) || value <= 0) {
      return "0 B";
    }
    const units = ["B", "KB", "MB", "GB", "TB"];
    let size = value;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex += 1;
    }
    return `${size >= 100 || unitIndex === 0 ? size.toFixed(0) : size.toFixed(1)} ${units[unitIndex]}`;
  }

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
      <div className="max-h-[94vh] w-full max-w-[92rem] overflow-y-auto rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
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
              <div className="grid gap-6 xl:grid-cols-[1.35fr_0.85fr]">
                <div className="space-y-6">
                  <article className="panel-card min-h-0">
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
                    <dl className="mt-5 grid gap-x-8 gap-y-4 md:grid-cols-2 xl:grid-cols-3">
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

                  <article className="panel-card min-h-0">
                    <p className="section-title">Timeline monitoraggio</p>
                    <dl className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                      <div className="rounded-xl bg-gray-50 px-4 py-3">
                        <dt className="label-caption">Prima rilevazione</dt>
                        <dd className="mt-1 text-sm text-gray-800">{new Date(selectedDevice.first_seen_at).toLocaleString("it-IT")}</dd>
                      </div>
                      <div className="rounded-xl bg-gray-50 px-4 py-3">
                        <dt className="label-caption">Ultima rilevazione</dt>
                        <dd className="mt-1 text-sm text-gray-800">{new Date(selectedDevice.last_seen_at).toLocaleString("it-IT")}</dd>
                      </div>
                      <div className="rounded-xl bg-gray-50 px-4 py-3">
                        <dt className="label-caption">Ultimo scan</dt>
                        <dd className="mt-1 text-sm text-gray-800">{selectedDevice.last_scan_id ? `Snapshot #${selectedDevice.last_scan_id}` : "n/d"}</dd>
                      </div>
                      <div className="rounded-xl bg-gray-50 px-4 py-3">
                        <dt className="label-caption">Monitorato</dt>
                        <dd className="mt-1 text-sm text-gray-800">{selectedDevice.is_monitored ? "Si" : "No"}</dd>
                      </div>
                    </dl>
                  </article>
                </div>

                <article className="panel-card min-h-0">
                  <div className="mb-4">
                    <p className="section-title">Label e note operative</p>
                    <p className="section-copy">Riconoscimento rapido e annotazioni contestuali.</p>
                  </div>
                  {saveError ? <p className="mb-3 text-sm text-red-600">{saveError}</p> : null}
                  {saveMessage ? <p className="mb-3 text-sm text-[#1D4E35]">{saveMessage}</p> : null}
                  <div className="space-y-4">
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
                    <label className="block text-sm font-medium text-gray-700">
                      Note
                      <textarea
                        className="form-control mt-1 min-h-32"
                        value={notes}
                        onChange={(event) => setNotes(event.target.value)}
                        placeholder="Annotazioni utili per riconoscere o gestire il dispositivo."
                      />
                    </label>
                    <label className="flex items-center gap-3 rounded-xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm font-medium text-gray-700">
                      <input checked={isKnownDevice} onChange={(event) => setIsKnownDevice(event.target.checked)} type="checkbox" />
                      Dispositivo conosciuto
                    </label>
                  </div>
                  <div className="mt-4 flex justify-end">
                    <button className="btn-primary" onClick={() => void handleSave()} type="button" disabled={isSaving}>
                      {isSaving ? "Salvataggio..." : "Salva"}
                    </button>
                  </div>
                </article>
              </div>

              <article className="panel-card">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="section-title">Traffico osservato</p>
                    <p className="section-copy">
                      Sintesi dagli eventi Sophos delle ultime {selectedDevice.traffic_summary?.window_hours ?? 24} ore per il dispositivo.
                    </p>
                  </div>
                  <div className="text-right text-xs text-gray-500">
                    Ultimo evento{" "}
                    {selectedDevice.traffic_summary?.last_observed_at
                      ? new Date(selectedDevice.traffic_summary.last_observed_at).toLocaleString("it-IT")
                      : "n/d"}
                  </div>
                </div>
                <div className="mt-5 grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
                  <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 px-4 py-4">
                    <p className="label-caption">Traffico in ingresso</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">
                      {formatBytes(selectedDevice.traffic_summary?.bytes_in ?? 0)}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">Dati ricevuti dal dispositivo.</p>
                  </div>
                  <div className="rounded-2xl border border-sky-100 bg-sky-50/70 px-4 py-4">
                    <p className="label-caption">Traffico in uscita</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">
                      {formatBytes(selectedDevice.traffic_summary?.bytes_out ?? 0)}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">Dati inviati dal dispositivo.</p>
                  </div>
                  <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4">
                    <p className="label-caption">Eventi consentiti</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">
                      {selectedDevice.traffic_summary?.allowed_events ?? 0}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">Connessioni o eventi marcati come allowed.</p>
                  </div>
                  <div className="rounded-2xl border border-amber-100 bg-amber-50/70 px-4 py-4">
                    <p className="label-caption">Eventi bloccati</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">
                      {selectedDevice.traffic_summary?.blocked_events ?? 0}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      Denied, blocked o drop. Totale eventi: {selectedDevice.traffic_summary?.total_events ?? 0}
                    </p>
                  </div>
                </div>
                <div className="mt-6 grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
                  <div>
                    <p className="label-caption">Peer principali</p>
                    <div className="mt-3 space-y-3">
                      {selectedDevice.traffic_summary?.top_peers.length ? (
                        selectedDevice.traffic_summary.top_peers.map((peer) => (
                          <div key={peer.ip_address} className="rounded-lg border border-gray-100 px-4 py-3">
                            <div className="flex items-center justify-between gap-3">
                              <div>
                                <p className="text-sm font-medium text-gray-900">
                                  {peer.ip_address}
                                  {peer.label ? ` -> ${peer.label}` : ""}
                                </p>
                              </div>
                              <p className="text-xs text-gray-500">{peer.events_count} eventi</p>
                            </div>
                            <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
                              <span>In: {formatBytes(peer.bytes_in)}</span>
                              <span>Out: {formatBytes(peer.bytes_out)}</span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-gray-500">Nessun peer osservato per il dispositivo nel periodo selezionato.</p>
                      )}
                    </div>
                  </div>
                  <div>
                    <p className="label-caption">Ultimi eventi traffico</p>
                    <div className="mt-3 space-y-3">
                      {selectedDevice.traffic_summary?.recent_events.length ? (
                        selectedDevice.traffic_summary.recent_events.map((event) => {
                          const eventType = formatEventType(event.event_type);
                          return (
                          <div key={event.id} className="rounded-lg border border-gray-100 px-4 py-3">
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="rounded-full bg-[#F3F8F1] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#1D4E35]">
                                  {eventType.context}
                                </span>
                                <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${eventType.actionTone}`}>
                                  {eventType.action}
                                </span>
                              </div>
                              <div className="flex items-center gap-2 text-xs text-gray-500">
                                <span>{event.protocol || "n/d"}</span>
                                <span>{new Date(event.observed_at).toLocaleString("it-IT")}</span>
                              </div>
                            </div>
                            <p className="mt-2 text-xs text-gray-500">
                              {event.src_ip || "n/d"} → {event.dst_ip || "n/d"}
                              {event.peer_label ? ` · ${event.peer_label}` : ""}
                              {" · "}In {formatBytes(event.bytes_in)} · Out {formatBytes(event.bytes_out)}
                            </p>
                          </div>
                        )})
                      ) : (
                        <p className="text-sm text-gray-500">Nessun evento Sophos correlato al dispositivo.</p>
                      )}
                    </div>
                  </div>
                </div>
              </article>

              <article className="panel-card">
                <div className="mb-4">
                  <p className="section-title">Posizionamento e storico</p>
                  <p className="section-copy">Ultime posizioni note e snapshot recenti del dispositivo.</p>
                </div>
                <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
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
