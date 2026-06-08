"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { NetworkTrackToggle } from "@/components/network/network-track-toggle";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { Badge } from "@/components/ui/badge";
import { ChevronRightIcon } from "@/components/ui/icons";
import {
  createNetworkTrackedSubject,
  getNetworkDevice,
  listNetworkDeviceAssignees,
  listNetworkTrackedSubjects,
  updateNetworkDevice,
} from "@/lib/api";
import {
  buildDeviceTrackingKey,
  buildNetworkTrackingKey,
  formatIpWithReference,
  getNetworkDeviceAdminUrl,
  isPrivateNetworkIp,
} from "@/lib/network-device-utils";
import type { NetworkAssignedUserSummary, NetworkDevice, NetworkTrackedSubject } from "@/types/api";

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

function formatTrafficEndpoint(ipAddress: string | null, peerIp: string | null, peerLabel: string | null) {
  const base = ipAddress || "n/d";
  if (ipAddress && peerIp && ipAddress === peerIp && peerLabel && peerLabel !== ipAddress) {
    return `${ipAddress} · ${peerLabel}`;
  }
  return base;
}

function getIpInfoUrl(ipAddress: string) {
  return `https://www.whatismyip.com/ip/${encodeURIComponent(ipAddress)}/`;
}

export function NetworkDeviceModal({ token, deviceId, open, onClose, onUpdated }: NetworkDeviceModalProps) {
  const [selectedDevice, setSelectedDevice] = useState<NetworkDevice | null>(null);
  const [applicationUsers, setApplicationUsers] = useState<NetworkAssignedUserSummary[]>([]);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [trackingError, setTrackingError] = useState<string | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [lifecycleState, setLifecycleState] = useState<"active" | "retired">("active");
  const [assignedUserId, setAssignedUserId] = useState("");
  const [assignedUserSearch, setAssignedUserSearch] = useState("");
  const [assetLabel, setAssetLabel] = useState("");
  const [notes, setNotes] = useState("");
  const [isKnownDevice, setIsKnownDevice] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [trackedSubjects, setTrackedSubjects] = useState<NetworkTrackedSubject[]>([]);
  const [trackingBusyKey, setTrackingBusyKey] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const adminUrl = selectedDevice ? getNetworkDeviceAdminUrl(selectedDevice) : null;
  const trackedSubjectMap = useMemo(
    () =>
      new Map<string, NetworkTrackedSubject>(
        trackedSubjects
          .filter((subject) => subject.is_active)
          .map((subject) => [`${subject.entity_type}:${subject.normalized_value}`, subject] as const),
      ),
    [trackedSubjects],
  );

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

  function upsertTrackedSubject(subject: NetworkTrackedSubject) {
    setTrackedSubjects((current) => {
      const next = current.filter((item) => item.id !== subject.id);
      next.unshift(subject);
      return next;
    });
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
        setLifecycleState(response.lifecycle_state);
        setAssignedUserId(response.assigned_user_id ? String(response.assigned_user_id) : "");
        setAssignedUserSearch("");
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

  useEffect(() => {
    async function loadUsers() {
      if (!open) {
        setApplicationUsers([]);
        return;
      }
      try {
        const users = await listNetworkDeviceAssignees(token);
        setApplicationUsers(users);
      } catch {
        setApplicationUsers([]);
      }
    }

    void loadUsers();
  }, [open, token]);

  useEffect(() => {
    async function loadTrackedSubjects() {
      if (!open) {
        setTrackedSubjects([]);
        setTrackingError(null);
        return;
      }
      try {
        const subjects = await listNetworkTrackedSubjects(token, { windowHours: 168 });
        setTrackedSubjects(subjects);
        setTrackingError(null);
      } catch (error) {
        setTrackingError(error instanceof Error ? error.message : "Errore caricamento tracking");
      }
    }

    void loadTrackedSubjects();
  }, [open, token]);

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
        lifecycle_state: lifecycleState,
        assigned_user_id: lifecycleState === "retired" ? null : assignedUserId ? Number(assignedUserId) : null,
        asset_label: assetLabel || null,
        notes: notes || null,
        is_known_device: isKnownDevice,
      });
      setSelectedDevice(updated);
      setDisplayName(updated.display_name || "");
      setLifecycleState(updated.lifecycle_state);
      setAssignedUserId(updated.assigned_user_id ? String(updated.assigned_user_id) : "");
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

  async function handleTrackSubject(
    key: string,
    payload:
      | { entity_type: "device"; device_id: number; label?: string | null; notes?: string | null }
      | { entity_type: "ip" | "domain" | "url"; value: string; label?: string | null; notes?: string | null },
  ) {
    setTrackingBusyKey(key);
    setTrackingError(null);
    try {
      const subject = await createNetworkTrackedSubject(token, payload);
      upsertTrackedSubject(subject);
    } catch (error) {
      setTrackingError(error instanceof Error ? error.message : "Errore durante l'attivazione del tracking");
    } finally {
      setTrackingBusyKey(null);
    }
  }

  if (!open || !deviceId) {
    return null;
  }

  const sortedUsers = [...applicationUsers].sort((left, right) => {
    const leftLabel = (left.full_name || left.username).toLowerCase();
    const rightLabel = (right.full_name || right.username).toLowerCase();
    return leftLabel.localeCompare(rightLabel, "it");
  });
  const normalizedAssignedUserSearch = assignedUserSearch.trim().toLowerCase();
  const filteredUsers =
    normalizedAssignedUserSearch.length >= 3
      ? sortedUsers.filter((user) => {
          const label = `${user.full_name || ""} ${user.username || ""}`.toLowerCase();
          return label.includes(normalizedAssignedUserSearch);
        })
      : sortedUsers;
  const trackedDeviceSubject = selectedDevice ? trackedSubjectMap.get(buildDeviceTrackingKey(selectedDevice.id)) : null;
  const selectedDetentore =
    assignedUserId && assignedUserId !== ""
      ? applicationUsers.find((user) => String(user.id) === assignedUserId) ?? null
      : null;
  const currentAssignedUserLabel =
    selectedDetentore?.full_name ||
    selectedDetentore?.username ||
    selectedDevice?.assigned_user?.full_name ||
    selectedDevice?.assigned_user?.username ||
    null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
      <div className="max-h-[94vh] w-full max-w-[92rem] overflow-y-auto rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="sticky top-0 flex items-start justify-between gap-4 border-b border-gray-100 bg-white px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Dettaglio dispositivo</p>
            <h2 className="mt-2 text-2xl font-semibold text-gray-900">
              {selectedDevice?.resolved_label || selectedDevice?.display_name || selectedDevice?.hostname || selectedDevice?.ip_address || `Dispositivo #${deviceId}`}
            </h2>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <p className="text-sm text-gray-500">Vista rapida senza lasciare il contesto operativo.</p>
              {selectedDevice?.lifecycle_state === "retired" ? <Badge variant="neutral">Rotamato</Badge> : null}
            </div>
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
                          {selectedDevice.resolved_label || selectedDevice.display_name || selectedDevice.hostname || selectedDevice.ip_address}
                        </p>
                        <p className="mt-1 text-sm text-gray-500">
                          {selectedDevice.asset_label || selectedDevice.dns_name || "Nessuna label assegnata"}
                        </p>
                        <p className="mt-1 text-xs text-gray-500">
                          Fonte label: {selectedDevice.label_source === "application_user" ? "utente applicativo" : selectedDevice.label_source}
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
                      <div className="flex flex-wrap items-center justify-end gap-2">
                        <NetworkTrackToggle
                          tracked={Boolean(trackedDeviceSubject)}
                          label={trackedDeviceSubject ? "Device tracciato" : "Traccia device"}
                          busy={trackingBusyKey === buildDeviceTrackingKey(selectedDevice.id)}
                          onClick={() =>
                            void handleTrackSubject(buildDeviceTrackingKey(selectedDevice.id), {
                              entity_type: "device",
                              device_id: selectedDevice.id,
                              label: selectedDevice.resolved_label,
                            })
                          }
                        />
                        <NetworkStatusBadge status={selectedDevice.status} />
                      </div>
                    </div>
                    <dl className="mt-5 grid gap-x-8 gap-y-4 md:grid-cols-2 xl:grid-cols-3">
                      <div>
                        <dt className="label-caption">IP</dt>
                        <dd className="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-800">
                          <span>{formatIpWithReference(selectedDevice)}</span>
                          {selectedDevice.ip_address && !isPrivateNetworkIp(selectedDevice.ip_address) ? (
                            <a
                              href={getIpInfoUrl(selectedDevice.ip_address)}
                              target="_blank"
                              rel="noreferrer"
                              className="rounded-full border border-[#d6e5db] bg-white px-3 py-1 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                            >
                              Info IP
                            </a>
                          ) : null}
                        </dd>
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
                        <dt className="label-caption">Utente associato</dt>
                        <dd className="mt-1 text-sm text-gray-800">
                          <div className="flex flex-wrap items-center gap-2">
                            <span>{selectedDevice.assigned_user?.full_name || selectedDevice.assigned_user?.username || "n/d"}</span>
                            {selectedDevice.assigned_user?.is_placeholder_profile ? (
                              <Badge variant="warning">Profilo placeholder</Badge>
                            ) : null}
                          </div>
                        </dd>
                      </div>
                      <div>
                        <dt className="label-caption">Ciclo di vita</dt>
                        <dd className="mt-1 text-sm text-gray-800">
                          {selectedDevice.lifecycle_state === "retired" ? "Rotamato" : "Attivo"}
                        </dd>
                      </div>
                      <div>
                        <dt className="label-caption">Data rotamazione</dt>
                        <dd className="mt-1 text-sm text-gray-800">
                          {selectedDevice.retired_at ? new Date(selectedDevice.retired_at).toLocaleString("it-IT") : "n/d"}
                        </dd>
                      </div>
                      <div>
                        <dt className="label-caption">Interno</dt>
                        <dd className="mt-1 text-sm text-gray-800">{selectedDevice.assigned_user?.phone_extension || "n/d"}</dd>
                      </div>
                      <div>
                        <dt className="label-caption">Stato profilo</dt>
                        <dd className="mt-1 text-sm text-gray-800">
                          {selectedDevice.assigned_user
                            ? selectedDevice.assigned_user.is_active
                              ? "Attivo"
                              : "Inattivo"
                            : "n/d"}
                        </dd>
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
                  {trackingError ? <p className="mb-3 text-sm text-red-600">{trackingError}</p> : null}
                  {saveError ? <p className="mb-3 text-sm text-red-600">{saveError}</p> : null}
                  {saveMessage ? <p className="mb-3 text-sm text-[#1D4E35]">{saveMessage}</p> : null}
                  <div className="space-y-4">
                    <label className="block text-sm font-medium text-gray-700">
                      Detentore
                      <input
                        className="form-control mt-1"
                        value={assignedUserSearch}
                        onChange={(event) => setAssignedUserSearch(event.target.value)}
                        placeholder="Cerca detentore per nome o username"
                        disabled={lifecycleState === "retired"}
                      />
                      <div className="mt-2 rounded-2xl border border-gray-200 bg-[#FAFBF8] p-3">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-gray-400">Selezione corrente</p>
                            <p className="mt-1 text-sm font-medium text-gray-900">{currentAssignedUserLabel || "Nessun utente assegnato"}</p>
                          </div>
                          <button
                            className="rounded-full border border-[#d6e5db] bg-white px-3 py-1 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5] disabled:cursor-not-allowed disabled:opacity-50"
                            type="button"
                            onClick={() => {
                              setAssignedUserId("");
                              setAssignedUserSearch("");
                            }}
                            disabled={lifecycleState === "retired" || !assignedUserId}
                          >
                            Rimuovi
                          </button>
                        </div>

                        {normalizedAssignedUserSearch.length >= 3 ? (
                          <div className="mt-3 max-h-56 space-y-2 overflow-y-auto pr-1">
                            {filteredUsers.length ? (
                              filteredUsers.map((user) => {
                                const isSelected = assignedUserId === String(user.id);
                                return (
                                  <button
                                    key={user.id}
                                    type="button"
                                    onClick={() => {
                                      setAssignedUserId(String(user.id));
                                      setAssignedUserSearch(user.full_name || user.username);
                                    }}
                                    disabled={lifecycleState === "retired"}
                                    className={`flex w-full items-center justify-between rounded-xl border px-3 py-2 text-left transition ${
                                      isSelected
                                        ? "border-emerald-200 bg-emerald-50/70"
                                        : "border-gray-200 bg-white hover:border-[#b9d2c1] hover:bg-[#f7faf6]"
                                    }`}
                                  >
                                    <div className="min-w-0">
                                      <p className="truncate text-sm font-medium text-gray-900">{user.full_name || user.username}</p>
                                      <p className="mt-0.5 truncate text-xs text-gray-500">
                                        {user.username}
                                        {user.is_active ? "" : " · inattivo"}
                                      </p>
                                    </div>
                                    {isSelected ? (
                                      <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold text-[#1D4E35]">Selezionato</span>
                                    ) : null}
                                  </button>
                                );
                              })
                            ) : (
                              <p className="text-xs text-gray-500">Nessun detentore corrisponde alla ricerca.</p>
                            )}
                          </div>
                        ) : (
                          <p className="mt-3 text-xs text-gray-500">Digita almeno 3 caratteri per vedere i risultati.</p>
                        )}
                      </div>
                      {normalizedAssignedUserSearch.length > 0 && normalizedAssignedUserSearch.length < 3 ? (
                        <span className="mt-1 block text-xs text-gray-500">Digita almeno 3 caratteri per filtrare l’elenco.</span>
                      ) : null}
                      <span className="mt-1 block text-xs text-gray-500">
                        Usa `Nessun utente assegnato` quando il PC cambia detentore o è in transizione.
                      </span>
                    </label>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <label className="block text-sm font-medium text-gray-700">
                        Stato apparato
                        <select
                          className="form-control mt-1"
                          value={lifecycleState}
                          onChange={(event) => setLifecycleState(event.target.value as "active" | "retired")}
                        >
                          <option value="active">Attivo</option>
                          <option value="retired">Rotamato</option>
                        </select>
                      </label>
                      <div className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-600">
                        {lifecycleState === "retired"
                          ? "Il device viene sganciato dall'utente e rimosso dal monitoraggio attivo."
                          : "Il device resta assegnabile e visibile nel monitoraggio di rete."}
                      </div>
                    </div>
                    <label className="block text-sm font-medium text-gray-700">
                      Label locale dispositivo
                      <input
                        className="form-control mt-1"
                        value={displayName}
                        onChange={(event) => setDisplayName(event.target.value)}
                        placeholder="Fallback se non esiste un utente associato"
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
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={() => {
                          setAssignedUserId("");
                          setLifecycleState("active");
                        }}
                        disabled={isSaving}
                      >
                        Sgancia utente
                      </button>
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={() => {
                          setLifecycleState("retired");
                          setAssignedUserId("");
                        }}
                        disabled={isSaving}
                      >
                        Segna come rotamato
                      </button>
                    </div>
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
                                  {peer.label && peer.label !== peer.ip_address ? `${peer.ip_address} · ${peer.label}` : peer.ip_address}
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                <a
                                  href={getIpInfoUrl(peer.ip_address)}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="rounded-full border border-[#d6e5db] bg-white px-3 py-1 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                                >
                                  Info IP
                                </a>
                                <NetworkTrackToggle
                                  compact
                                  tracked={Boolean(peer.tracked_subject_id || trackedSubjectMap.get(buildNetworkTrackingKey("ip", peer.ip_address)))}
                                  label="Traccia IP"
                                  busy={trackingBusyKey === buildNetworkTrackingKey("ip", peer.ip_address)}
                                  onClick={() =>
                                    void handleTrackSubject(buildNetworkTrackingKey("ip", peer.ip_address), {
                                      entity_type: "ip",
                                      value: peer.ip_address,
                                      label: peer.label && peer.label !== peer.ip_address ? peer.label : null,
                                    })
                                  }
                                />
                                <p className="text-xs text-gray-500">{peer.events_count} eventi</p>
                              </div>
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
                          const peerTrackKey = event.peer_ip ? buildNetworkTrackingKey("ip", event.peer_ip) : null;
                          const domainTrackKey = event.peer_label ? buildNetworkTrackingKey("domain", event.peer_label) : null;
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
                              {formatTrafficEndpoint(event.src_ip, event.peer_ip, event.peer_label)}
                              {" → "}
                              {formatTrafficEndpoint(event.dst_ip, event.peer_ip, event.peer_label)}
                              {" · "}In {formatBytes(event.bytes_in)} · Out {formatBytes(event.bytes_out)}
                            </p>
                            <div className="mt-3 flex flex-wrap gap-2">
                              {event.peer_ip ? (
                                <>
                                  <a
                                    href={getIpInfoUrl(event.peer_ip)}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="rounded-full border border-[#d6e5db] bg-white px-3 py-1 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                                  >
                                    Info IP
                                  </a>
                                  <NetworkTrackToggle
                                    compact
                                    tracked={Boolean(event.tracked_peer_ip_subject_id || trackedSubjectMap.get(peerTrackKey!))}
                                    label="Traccia IP"
                                    busy={trackingBusyKey === peerTrackKey}
                                    onClick={() =>
                                      void handleTrackSubject(peerTrackKey!, {
                                        entity_type: "ip",
                                        value: event.peer_ip!,
                                        label: event.peer_label && event.peer_label !== event.peer_ip ? event.peer_label : null,
                                      })
                                    }
                                  />
                                </>
                              ) : null}
                              {event.peer_label ? (
                                <NetworkTrackToggle
                                  compact
                                  tracked={Boolean(event.tracked_peer_label_subject_id || trackedSubjectMap.get(domainTrackKey!))}
                                  label="Traccia dominio"
                                  busy={trackingBusyKey === domainTrackKey}
                                  onClick={() =>
                                    void handleTrackSubject(domainTrackKey!, {
                                      entity_type: "domain",
                                      value: event.peer_label!,
                                    })
                                  }
                                />
                              ) : null}
                            </div>
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
                <details key={selectedDevice.id} className="group">
                  <summary className="flex cursor-pointer list-none items-start justify-between gap-4 [&::-webkit-details-marker]:hidden">
                    <div className="min-w-0">
                      <p className="section-title">Posizionamento e storico</p>
                      <p className="section-copy">Ultime posizioni note e snapshot recenti del dispositivo.</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2 pt-0.5 text-xs text-gray-500">
                      <span>
                        {selectedDevice.positions.length} posiz.
                        {" · "}
                        {selectedDevice.scan_history.length} snapshot
                      </span>
                      <ChevronRightIcon className="h-4 w-4 text-gray-400 transition-transform group-open:rotate-90" />
                    </div>
                  </summary>
                  <div className="mt-4 grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
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
                            <p className="mt-2 text-xs text-gray-500">{entry.resolved_label || entry.assigned_user_label || entry.hostname || entry.ip_address} · {entry.ip_address} · {entry.open_ports || "porte n/d"}</p>
                          </div>
                        ))}
                        {selectedDevice.scan_history.length === 0 ? <p className="text-sm text-gray-500">Nessuno snapshot disponibile.</p> : null}
                      </div>
                    </div>
                  </div>
                </details>
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
