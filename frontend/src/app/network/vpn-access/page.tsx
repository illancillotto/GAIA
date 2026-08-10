"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { FilterPillGroup } from "@/components/network/filter-pill-group";
import { NetworkModulePage } from "@/components/network/network-module-page";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { RefreshIcon, ShieldIcon, UserIcon } from "@/components/ui/icons";
import {
  listNetworkVpnAccessDevices,
  listNetworkVpnAccessSessions,
  updateNetworkVpnAccessDeviceStatus,
} from "@/lib/api";
import type {
  CurrentUser,
  NetworkVpnAccessDevice,
  NetworkVpnAccessSession,
  NetworkVpnDeviceStatus,
} from "@/types/api";

const DEVICE_STATUS_OPTIONS = [
  { value: "", label: "Tutti" },
  { value: "active", label: "Attivi" },
  { value: "blocked", label: "Bloccati" },
  { value: "revoked", label: "Revocati" },
] as const;

const SESSION_EVENT_OPTIONS = [
  { value: "", label: "Tutte" },
  { value: "login_allowed", label: "Consentite" },
  { value: "login_blocked", label: "Bloccate" },
] as const;

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "n/d";
  }
  return new Date(value).toLocaleString("it-IT");
}

function statusBadgeVariant(status: NetworkVpnDeviceStatus): "success" | "danger" | "warning" | "neutral" {
  if (status === "active") return "success";
  if (status === "blocked") return "warning";
  if (status === "revoked") return "danger";
  return "neutral";
}

function statusLabel(status: NetworkVpnDeviceStatus): string {
  if (status === "active") return "Attivo";
  if (status === "blocked") return "Bloccato";
  if (status === "revoked") return "Revocato";
  return status;
}

function sessionEventLabel(eventType: string): string {
  if (eventType === "login_allowed") return "Login consentito";
  if (eventType === "login_blocked") return "Login bloccato";
  return eventType;
}

function shortHash(value: string | null | undefined): string {
  if (!value) {
    return "n/d";
  }
  return value.length > 12 ? `${value.slice(0, 12)}…` : value;
}

function canManageVpnAccess(currentUser: CurrentUser): boolean {
  return currentUser.role === "admin" || currentUser.role === "super_admin";
}

function VpnAccessContent({ token, currentUser }: { token: string; currentUser: CurrentUser }) {
  const [devices, setDevices] = useState<NetworkVpnAccessDevice[]>([]);
  const [sessions, setSessions] = useState<NetworkVpnAccessSession[]>([]);
  const [devicesTotal, setDevicesTotal] = useState(0);
  const [sessionsTotal, setSessionsTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<NetworkVpnDeviceStatus | "">("");
  const [eventFilter, setEventFilter] = useState("");
  const [userIdFilter, setUserIdFilter] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [busyDeviceId, setBusyDeviceId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const parsedUserId = useMemo(() => {
    const trimmed = userIdFilter.trim();
    if (!trimmed) {
      return undefined;
    }
    const numeric = Number(trimmed);
    return Number.isInteger(numeric) && numeric > 0 ? numeric : undefined;
  }, [userIdFilter]);

  const loadData = useCallback(async () => {
    if (!canManageVpnAccess(currentUser)) {
      return;
    }
    setIsLoading(true);
    try {
      const [deviceResponse, sessionResponse] = await Promise.all([
        listNetworkVpnAccessDevices(token, {
          userId: parsedUserId,
          status: statusFilter,
          limit: 100,
        }),
        listNetworkVpnAccessSessions(token, {
          userId: parsedUserId,
          eventType: eventFilter,
          limit: 100,
        }),
      ]);
      setDevices(deviceResponse.items);
      setDevicesTotal(deviceResponse.total);
      setSessions(sessionResponse.items);
      setSessionsTotal(sessionResponse.total);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento accessi VPN");
    } finally {
      setIsLoading(false);
    }
  }, [currentUser, eventFilter, parsedUserId, statusFilter, token]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  async function handleStatusChange(device: NetworkVpnAccessDevice, status: NetworkVpnDeviceStatus) {
    setBusyDeviceId(device.id);
    setActionMessage(null);
    try {
      await updateNetworkVpnAccessDeviceStatus(token, device.id, status);
      setActionMessage(`Dispositivo #${device.id} aggiornato a ${statusLabel(status).toLowerCase()}.`);
      await loadData();
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore aggiornamento dispositivo VPN");
    } finally {
      setBusyDeviceId(null);
    }
  }

  const activeDevices = devices.filter((device) => device.status === "active").length;
  const blockedDevices = devices.filter((device) => device.status === "blocked").length;
  const revokedDevices = devices.filter((device) => device.status === "revoked").length;
  const blockedSessions = sessions.filter((session) => session.event_type === "login_blocked").length;

  if (!canManageVpnAccess(currentUser)) {
    return (
      <article className="panel-card">
        <Badge variant="danger">Admin richiesto</Badge>
        <h3 className="mt-3 text-lg font-semibold text-gray-950">Accesso VPN riservato agli amministratori</h3>
        <p className="mt-2 text-sm text-gray-600">
          La gestione dei dispositivi VPN puo bloccare o revocare accessi applicativi GAIA.
        </p>
      </article>
    );
  }

  return (
    <>
      <section className="grid gap-4 lg:grid-cols-4">
        <MetricCard label="Dispositivi caricati" value={devicesTotal} sub="nel filtro corrente" />
        <MetricCard label="Attivi" value={activeDevices} sub="conteggiati nel limite" variant="success" />
        <MetricCard label="Bloccati / revocati" value={blockedDevices + revokedDevices} sub="richiedono verifica CED" variant="warning" />
        <MetricCard label="Login bloccati" value={blockedSessions} sub={`${sessionsTotal} sessioni caricate`} variant={blockedSessions > 0 ? "danger" : "default"} />
      </section>

      <section className="panel-card">
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-gray-500" htmlFor="vpn-user-id">
              User ID GAIA
            </label>
            <input
              id="vpn-user-id"
              className="form-control mt-1"
              inputMode="numeric"
              placeholder="Tutti gli utenti"
              value={userIdFilter}
              onChange={(event) => setUserIdFilter(event.target.value)}
            />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Stato dispositivi</p>
            <div className="mt-2">
              <FilterPillGroup
                options={DEVICE_STATUS_OPTIONS}
                value={statusFilter}
                onChange={(value) => setStatusFilter(value as NetworkVpnDeviceStatus | "")}
              />
            </div>
          </div>
          <button className="btn-secondary" disabled={isLoading} type="button" onClick={() => void loadData()}>
            <RefreshIcon className="h-4 w-4" />
            {isLoading ? "Aggiorno…" : "Aggiorna"}
          </button>
        </div>
        {loadError ? <p className="mt-4 text-sm font-medium text-red-700">{loadError}</p> : null}
        {actionMessage ? <p className="mt-4 text-sm font-medium text-emerald-700">{actionMessage}</p> : null}
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
        <article className="panel-card">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-gray-950">Dispositivi autorizzati</h3>
              <p className="mt-1 text-sm text-gray-600">Ogni device attivo viene conteggiato nel limite utente.</p>
            </div>
            <Badge variant="info">{devices.length} visibili</Badge>
          </div>

          {devices.length === 0 ? (
            <EmptyState icon={ShieldIcon} title="Nessun dispositivo VPN" description="Non ci sono dispositivi nel filtro corrente." />
          ) : (
            <div className="divide-y divide-gray-100">
              {devices.map((device) => (
                <div key={device.id} className="grid gap-4 py-4 lg:grid-cols-[minmax(0,1fr)_auto]">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="font-semibold text-gray-950">{device.display_name || `Dispositivo #${device.id}`}</h4>
                      <Badge variant={statusBadgeVariant(device.status)}>{statusLabel(device.status)}</Badge>
                    </div>
                    <dl className="mt-3 grid gap-2 text-sm text-gray-600 sm:grid-cols-2">
                      <Detail label="User ID" value={String(device.user_id)} />
                      <Detail label="Ultimo IP" value={device.last_client_ip || "n/d"} />
                      <Detail label="Client device ID" value={shortHash(device.client_device_id)} />
                      <Detail label="Fingerprint" value={shortHash(device.device_fingerprint)} />
                      <Detail label="Primo accesso" value={formatDateTime(device.first_seen_at)} />
                      <Detail label="Ultimo accesso" value={formatDateTime(device.last_seen_at)} />
                    </dl>
                    {device.user_agent_sample ? (
                      <p className="mt-3 line-clamp-2 text-xs text-gray-500">{device.user_agent_sample}</p>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap items-start gap-2 lg:justify-end">
                    <StatusButton
                      disabled={busyDeviceId === device.id || device.status === "active"}
                      label="Attiva"
                      onClick={() => void handleStatusChange(device, "active")}
                    />
                    <StatusButton
                      disabled={busyDeviceId === device.id || device.status === "blocked"}
                      label="Blocca"
                      onClick={() => void handleStatusChange(device, "blocked")}
                    />
                    <StatusButton
                      danger
                      disabled={busyDeviceId === device.id || device.status === "revoked"}
                      label="Revoca"
                      onClick={() => void handleStatusChange(device, "revoked")}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="panel-card">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-gray-950">Sessioni e blocchi</h3>
              <p className="mt-1 text-sm text-gray-600">Audit applicativo generato al login GAIA.</p>
            </div>
            <Badge variant={blockedSessions > 0 ? "warning" : "neutral"}>{sessionsTotal} totali</Badge>
          </div>

          <div className="mb-4">
            <FilterPillGroup options={SESSION_EVENT_OPTIONS} value={eventFilter} onChange={setEventFilter} />
          </div>

          {sessions.length === 0 ? (
            <EmptyState icon={UserIcon} title="Nessuna sessione VPN" description="Non ci sono sessioni nel filtro corrente." />
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => (
                <div key={session.id} className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <Badge variant={session.event_type === "login_blocked" ? "danger" : "success"}>
                      {sessionEventLabel(session.event_type)}
                    </Badge>
                    <span className="text-xs text-gray-500">{formatDateTime(session.observed_at)}</span>
                  </div>
                  <p className="mt-2 text-sm font-medium text-gray-950">{session.username || `User #${session.user_id ?? "n/d"}`}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    IP {session.client_ip || "n/d"} · Device {session.device_id ?? "non registrato"}
                  </p>
                  {session.blocked_reason ? (
                    <p className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
                      Motivo blocco: {session.blocked_reason}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </article>
      </section>
    </>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-gray-400">{label}</dt>
      <dd className="mt-0.5 break-all text-gray-800">{value}</dd>
    </div>
  );
}

function StatusButton({
  danger = false,
  disabled,
  label,
  onClick,
}: {
  danger?: boolean;
  disabled: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className={
        danger
          ? "rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
          : "btn-secondary"
      }
      disabled={disabled}
      type="button"
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function MetricCard({
  label,
  value,
  sub,
  variant = "default",
}: {
  label: string;
  value: string | number;
  sub: string;
  variant?: "default" | "success" | "warning" | "danger";
}) {
  const tone =
    variant === "success"
      ? "border-emerald-100 bg-emerald-50"
      : variant === "warning"
        ? "border-amber-100 bg-amber-50"
        : variant === "danger"
          ? "border-red-100 bg-red-50"
          : "border-gray-100 bg-white";
  return (
    <article className={`rounded-2xl border px-5 py-4 shadow-sm ${tone}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-gray-950">{value}</p>
      <p className="mt-1 text-sm text-gray-600">{sub}</p>
    </article>
  );
}

export default function NetworkVpnAccessPage() {
  return (
    <NetworkModulePage
      title="Accessi VPN GAIA"
      description="Dispositivi autorizzati, sessioni applicative e blocchi legati all'accesso remoto ufficiale via Sophos VPN."
      breadcrumb="GAIA Rete / Accessi VPN"
      actions={
        <span className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
          <ShieldIcon className="h-4 w-4" />
          Limite operativo: 4 device attivi
        </span>
      }
    >
      {({ token, currentUser }) => <VpnAccessContent token={token} currentUser={currentUser} />}
    </NetworkModulePage>
  );
}
