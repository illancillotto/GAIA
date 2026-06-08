"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { AlertTriangleIcon, SearchIcon, ServerIcon, TruckIcon, UserIcon } from "@/components/ui/icons";
import { cn } from "@/lib/cn";
import {
  getCurrentUser,
  getInazCollaboratorSummary,
  getNetworkDevices,
  listAllApplicationUsers,
  listAllInazCollaborators,
  listInazDailyRecords,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type {
  ApplicationUser,
  CurrentUser,
  InazCollaborator,
  InazDailyRecord,
  InazEventSummary,
  NetworkDevice,
} from "@/types/api";
import {
  getOperatorDetail,
  getOperators,
  type OperatorDetailResponse,
} from "@/features/operazioni/api/client";

type OperatorListItem = {
  id: string;
  wc_id: number;
  username: string | null;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  tax: string | null;
  role: string | null;
  enabled: boolean;
  gaia_user_id: number | null;
  wc_synced_at: string | null;
  created_at: string;
  updated_at: string;
  current_fuel_cards: { id: string; codice: string | null; pan: string; is_blocked: boolean; expires_at: string | null }[];
};

type SelectedOperatorBundle = {
  detail: OperatorDetailResponse | null;
  collaborator: InazCollaborator | null;
  inazSummary: InazEventSummary[];
  inazRecords: InazDailyRecord[];
  gaiaUser: ApplicationUser | null;
  devices: NetworkDevice[];
};

type OperatorHealthRow = {
  operator: OperatorListItem;
  gaiaUser: ApplicationUser | null;
  collaborator: InazCollaborator | null;
  devices: NetworkDevice[];
  anomalyScore: number;
  flags: string[];
};

const integerFormatter = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 0 });
const decimalFormatter = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 1 });

function currentMonthBounds(): { start: string; end: string; label: string } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const format = (value: Date) =>
    `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
  return {
    start: format(start),
    end: format(end),
    label: new Intl.DateTimeFormat("it-IT", { month: "long", year: "numeric" }).format(start),
  };
}

function displayOperatorName(operator: Pick<OperatorListItem, "first_name" | "last_name" | "username" | "email" | "wc_id">): string {
  const fullName = `${operator.first_name ?? ""} ${operator.last_name ?? ""}`.trim();
  return fullName || operator.username || operator.email || `Operatore ${operator.wc_id}`;
}

function initialsForOperator(operator: Pick<OperatorListItem, "first_name" | "last_name" | "username" | "email" | "wc_id">): string {
  const parts = displayOperatorName(operator).split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "OP";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("it-IT");
}

function parseNumeric(value: string | null | undefined): number | null {
  if (value == null || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatNumeric(value: string | number | null | undefined, suffix?: string): string {
  const parsed = typeof value === "number" ? value : parseNumeric(value);
  if (parsed == null) return "—";
  const formatted = Number.isInteger(parsed) ? integerFormatter.format(parsed) : decimalFormatter.format(parsed);
  return suffix ? `${formatted} ${suffix}` : formatted;
}

function formatMinutes(minutes: number | null | undefined): string {
  if (minutes == null) return "—";
  const absolute = Math.abs(minutes);
  const hours = Math.floor(absolute / 60);
  const mins = absolute % 60;
  const prefix = minutes < 0 ? "-" : "";
  return `${prefix}${hours}h ${String(mins).padStart(2, "0")}m`;
}

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size >= 100 || index === 0 ? size.toFixed(0) : size.toFixed(1)} ${units[index]}`;
}

function hasInazAnomaly(record: InazDailyRecord): boolean {
  return (
    record.detail_anomalies.length > 0 ||
    Boolean(record.detail_error) ||
    Boolean(record.detail_status?.toLowerCase().includes("anom")) ||
    Boolean(record.stato?.toLowerCase().includes("anom"))
  );
}

async function listAllOperators(): Promise<OperatorListItem[]> {
  const items: OperatorListItem[] = [];
  let page = 1;
  const pageSize = 100;

  while (true) {
    const response = await getOperators({ page: String(page), page_size: String(pageSize) }) as {
      items?: OperatorListItem[];
      total?: number;
    };
    const batch = response.items ?? [];
    items.push(...batch);
    if (batch.length === 0 || items.length >= (response.total ?? items.length)) {
      return items;
    }
    page += 1;
  }
}

async function listAllNetworkDevices(token: string): Promise<NetworkDevice[]> {
  const items: NetworkDevice[] = [];
  let page = 1;
  const pageSize = 100;

  while (true) {
    const response = await getNetworkDevices(token, { page, pageSize });
    items.push(...response.items);
    if (response.items.length === 0 || items.length >= response.total) {
      return items;
    }
    page += 1;
  }
}

async function listAllInazRecordsForCollaborator(
  token: string,
  collaboratorId: string,
  dateFrom: string,
  dateTo: string,
): Promise<InazDailyRecord[]> {
  const items: InazDailyRecord[] = [];
  let page = 1;
  const pageSize = 100;

  while (true) {
    const response = await listInazDailyRecords(token, { collaboratorId, dateFrom, dateTo, page, pageSize });
    items.push(...response.items);
    if (response.items.length === 0 || items.length >= response.total) {
      return items;
    }
    page += 1;
  }
}

function canAccessModule(currentUser: CurrentUser, moduleKey: string): boolean {
  return currentUser.role === "admin" || currentUser.role === "super_admin" || currentUser.enabled_modules.includes(moduleKey);
}

function buildHealthRows(
  operators: OperatorListItem[],
  gaiaUserMap: Map<number, ApplicationUser>,
  collaboratorByUserId: Map<number, InazCollaborator>,
  devicesByUserId: Map<number, NetworkDevice[]>,
): OperatorHealthRow[] {
  return operators.map((operator) => {
    const gaiaUser = operator.gaia_user_id != null ? gaiaUserMap.get(operator.gaia_user_id) ?? null : null;
    const collaborator = operator.gaia_user_id != null ? collaboratorByUserId.get(operator.gaia_user_id) ?? null : null;
    const devices = operator.gaia_user_id != null ? devicesByUserId.get(operator.gaia_user_id) ?? [] : [];
    const blockedEvents = devices.reduce((sum, device) => sum + (device.traffic_summary?.blocked_events ?? 0), 0);
    const flags: string[] = [];

    if (!operator.enabled) flags.push("Operatore disabilitato");
    if (!operator.gaia_user_id) flags.push("Non collegato a GAIA");
    if (gaiaUser && !gaiaUser.is_active) flags.push("Account GAIA inattivo");
    if (operator.gaia_user_id && !collaborator) flags.push("Nessun mapping Inaz");
    if (operator.gaia_user_id && devices.length === 0) flags.push("Nessun device rete");
    if (blockedEvents > 0) flags.push(`${blockedEvents} eventi rete bloccati`);
    if ((operator.current_fuel_cards?.length ?? 0) === 0) flags.push("Nessuna fuel card");

    return {
      operator,
      gaiaUser,
      collaborator,
      devices,
      anomalyScore: flags.length,
      flags,
    };
  });
}

function OperatorCruscottoContent() {
  const [token, setToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [operators, setOperators] = useState<OperatorListItem[]>([]);
  const [users, setUsers] = useState<ApplicationUser[]>([]);
  const [collaborators, setCollaborators] = useState<InazCollaborator[]>([]);
  const [devices, setDevices] = useState<NetworkDevice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [scope, setScope] = useState<"all" | "anomalies" | "with_network" | "with_inaz">("all");
  const [selectedOperatorId, setSelectedOperatorId] = useState<string | null>(null);
  const [selectedBundle, setSelectedBundle] = useState<SelectedOperatorBundle | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const deferredSearch = useDeferredValue(search.trim().toLowerCase());
  const monthBounds = useMemo(() => currentMonthBounds(), []);
  const gaiaAccessEnabled = currentUser ? canAccessModule(currentUser, "accessi") : false;
  const inazAccessEnabled = currentUser ? canAccessModule(currentUser, "inaz") : false;
  const networkAccessEnabled = currentUser ? canAccessModule(currentUser, "rete") : false;

  useEffect(() => {
    const accessToken = getStoredAccessToken();
    if (!accessToken) {
      setLoadError("Sessione non disponibile.");
      setIsLoading(false);
      return;
    }
    setToken(accessToken);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadBase() {
      if (!token) {
        return;
      }
      setIsLoading(true);
      try {
        const sessionUser = await getCurrentUser(token);
        if (cancelled) return;
        setCurrentUser(sessionUser);

        const tasks: Promise<unknown>[] = [listAllOperators()];
        if (canAccessModule(sessionUser, "accessi")) {
          tasks.push(listAllApplicationUsers(token));
        }
        if (canAccessModule(sessionUser, "inaz")) {
          tasks.push(listAllInazCollaborators(token));
        }
        if (canAccessModule(sessionUser, "rete")) {
          tasks.push(listAllNetworkDevices(token));
        }

        const results = await Promise.all(tasks);
        if (cancelled) return;

        const nextOperators = results[0] as OperatorListItem[];
        let index = 1;

        setOperators(nextOperators);
        setUsers(canAccessModule(sessionUser, "accessi") ? (results[index++] as ApplicationUser[]) : []);
        setCollaborators(canAccessModule(sessionUser, "inaz") ? (results[index++] as InazCollaborator[]) : []);
        setDevices(canAccessModule(sessionUser, "rete") ? (results[index++] as NetworkDevice[]) : []);
        setSelectedOperatorId((current) => current ?? nextOperators[0]?.id ?? null);
        setLoadError(null);
      } catch (error) {
        if (!cancelled) {
          setLoadError(error instanceof Error ? error.message : "Errore caricamento cruscotto operatori");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadBase();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const gaiaUserMap = useMemo(() => new Map(users.map((item) => [item.id, item])), [users]);
  const collaboratorByUserId = useMemo(
    () =>
      new Map(
        collaborators
          .filter((item) => item.application_user_id != null)
          .map((item) => [item.application_user_id as number, item]),
      ),
    [collaborators],
  );
  const devicesByUserId = useMemo(() => {
    const next = new Map<number, NetworkDevice[]>();
    devices.forEach((device) => {
      if (device.assigned_user_id == null) return;
      const bucket = next.get(device.assigned_user_id) ?? [];
      bucket.push(device);
      next.set(device.assigned_user_id, bucket);
    });
    return next;
  }, [devices]);

  const healthRows = useMemo(
    () => buildHealthRows(operators, gaiaUserMap, collaboratorByUserId, devicesByUserId),
    [collaboratorByUserId, devicesByUserId, gaiaUserMap, operators],
  );

  const filteredRows = useMemo(() => {
    return healthRows
      .filter((row) => {
        if (scope === "anomalies" && row.anomalyScore === 0) return false;
        if (scope === "with_network" && row.devices.length === 0) return false;
        if (scope === "with_inaz" && !row.collaborator) return false;
        if (!deferredSearch) return true;
        const haystack = [
          displayOperatorName(row.operator),
          row.operator.username,
          row.operator.email,
          row.operator.tax,
          row.gaiaUser?.username,
          row.gaiaUser?.full_name,
          row.collaborator?.employee_code,
          row.collaborator?.name,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(deferredSearch);
      })
      .sort((a, b) => b.anomalyScore - a.anomalyScore || displayOperatorName(a.operator).localeCompare(displayOperatorName(b.operator), "it"));
  }, [deferredSearch, healthRows, scope]);

  useEffect(() => {
    if (!filteredRows.length) {
      setSelectedOperatorId(null);
      return;
    }
    if (!selectedOperatorId || !filteredRows.some((row) => row.operator.id === selectedOperatorId)) {
      setSelectedOperatorId(filteredRows[0].operator.id);
    }
  }, [filteredRows, selectedOperatorId]);

  useEffect(() => {
    if (!selectedOperatorId || !token) {
      setSelectedBundle(null);
      return;
    }

    const authToken = token;
    const operatorId = selectedOperatorId;
    const selectedRow = healthRows.find((row) => row.operator.id === operatorId);
    if (!selectedRow) return;

    let cancelled = false;

    async function loadSelected() {
      setDetailLoading(true);
      try {
        const detail = await getOperatorDetail(operatorId);
        if (cancelled) return;

        const collaborator =
          detail.operator.gaia_user_id != null ? collaboratorByUserId.get(detail.operator.gaia_user_id) ?? null : null;
        const gaiaUser =
          detail.operator.gaia_user_id != null ? gaiaUserMap.get(detail.operator.gaia_user_id) ?? null : null;
        const assignedDevices =
          detail.operator.gaia_user_id != null ? devicesByUserId.get(detail.operator.gaia_user_id) ?? [] : [];

        let inazSummary: InazEventSummary[] = [];
        let inazRecords: InazDailyRecord[] = [];

        if (collaborator && inazAccessEnabled) {
          const collaboratorId = collaborator.id;
          const [summaryResponse, recordsResponse] = await Promise.all([
            getInazCollaboratorSummary(authToken, collaboratorId, monthBounds.start, monthBounds.end),
            listAllInazRecordsForCollaborator(authToken, collaboratorId, monthBounds.start, monthBounds.end),
          ]);
          if (cancelled) return;
          inazSummary = summaryResponse.items;
          inazRecords = recordsResponse;
        }

        setSelectedBundle({
          detail,
          collaborator,
          inazSummary,
          inazRecords,
          gaiaUser,
          devices: assignedDevices,
        });
        setDetailError(null);
      } catch (error) {
        if (!cancelled) {
          setDetailError(error instanceof Error ? error.message : "Errore caricamento dettaglio operatore");
        }
      } finally {
        if (!cancelled) {
          setDetailLoading(false);
        }
      }
    }

    void loadSelected();
    return () => {
      cancelled = true;
    };
  }, [
    collaboratorByUserId,
    devicesByUserId,
    gaiaUserMap,
    healthRows,
    inazAccessEnabled,
    monthBounds.end,
    monthBounds.start,
    selectedOperatorId,
    token,
  ]);

  const selectedRow = useMemo(
    () => healthRows.find((row) => row.operator.id === selectedOperatorId) ?? null,
    [healthRows, selectedOperatorId],
  );

  const selectedInazAnomalies = useMemo(
    () => selectedBundle?.inazRecords.filter(hasInazAnomaly) ?? [],
    [selectedBundle],
  );
  const selectedBlockedEvents = useMemo(
    () => selectedBundle?.devices.reduce((sum, item) => sum + (item.traffic_summary?.blocked_events ?? 0), 0) ?? 0,
    [selectedBundle],
  );
  const selectedAllowedEvents = useMemo(
    () => selectedBundle?.devices.reduce((sum, item) => sum + (item.traffic_summary?.allowed_events ?? 0), 0) ?? 0,
    [selectedBundle],
  );
  const selectedBytes = useMemo(
    () => selectedBundle?.devices.reduce((sum, item) => sum + (item.traffic_summary?.bytes_in ?? 0) + (item.traffic_summary?.bytes_out ?? 0), 0) ?? 0,
    [selectedBundle],
  );

  const timelineRows = useMemo(() => {
    if (!selectedBundle || !selectedRow) return [];
    const items = [
      {
        label: "Ultimo login GAIA",
        value: selectedBundle.gaiaUser?.last_login_at ?? null,
        meta: selectedBundle.gaiaUser?.last_login_ip ? `IP ${selectedBundle.gaiaUser.last_login_ip}` : "Nessun login registrato",
      },
      {
        label: "Ultima presenza Inaz",
        value: selectedBundle.collaborator?.last_seen_at ?? null,
        meta: selectedBundle.collaborator?.employee_code ? `Matricola ${selectedBundle.collaborator.employee_code}` : "Nessun mapping Inaz",
      },
      {
        label: "Ultimo rifornimento",
        value: selectedBundle.detail?.recent_fuel_logs[0]?.fueled_at ?? null,
        meta: selectedBundle.detail?.recent_fuel_logs[0]?.vehicle_label ?? "Nessun rifornimento",
      },
      {
        label: "Ultima sessione mezzo",
        value: selectedBundle.detail?.recent_usage_sessions[0]?.started_at ?? null,
        meta: selectedBundle.detail?.recent_usage_sessions[0]?.vehicle_label ?? "Nessuna sessione mezzo",
      },
      {
        label: "Ultimo evento rete",
        value:
          [...selectedBundle.devices]
            .flatMap((device) => device.traffic_summary?.recent_events ?? [])
            .sort((a, b) => new Date(b.observed_at).getTime() - new Date(a.observed_at).getTime())[0]?.observed_at ?? null,
        meta:
          [...selectedBundle.devices]
            .flatMap((device) => device.traffic_summary?.recent_events ?? [])
            .sort((a, b) => new Date(b.observed_at).getTime() - new Date(a.observed_at).getTime())[0]?.peer_label ?? "Nessun evento rete",
      },
    ]
      .filter((item) => item.value)
      .sort((a, b) => new Date(String(b.value)).getTime() - new Date(String(a.value)).getTime());

    return items;
  }, [selectedBundle, selectedRow]);

  const topNetworkPeers = useMemo(() => {
    const aggregated = new Map<string, { label: string; count: number; bytes: number }>();
    (selectedBundle?.devices ?? []).forEach((device) => {
      device.traffic_summary?.top_peers.forEach((peer) => {
        const key = peer.label || peer.ip_address;
        const current = aggregated.get(key) ?? { label: key, count: 0, bytes: 0 };
        current.count += peer.events_count;
        current.bytes += peer.bytes_in + peer.bytes_out;
        aggregated.set(key, current);
      });
    });
    return [...aggregated.values()].sort((a, b) => b.count - a.count).slice(0, 5);
  }, [selectedBundle]);

  const quickMetrics = useMemo(() => {
    const anomalyOperators = healthRows.filter((row) => row.anomalyScore > 0).length;
    const mappedGaiaOperators = healthRows.filter((row) => row.operator.gaia_user_id != null).length;
    const mappedInazOperators = healthRows.filter((row) => row.collaborator != null).length;
    const networkedOperators = healthRows.filter((row) => row.devices.length > 0).length;
    return { anomalyOperators, mappedGaiaOperators, mappedInazOperators, networkedOperators };
  }, [healthRows]);

  return (
    <div className="space-y-6">
      <article className="panel-card border-[#d9e5dc] bg-[radial-gradient(circle_at_top_left,_rgba(140,179,157,0.16),_transparent_38%),linear-gradient(180deg,#ffffff_0%,#f8fbf8_100%)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="section-title">Cruscotto operatori</p>
            <p className="section-copy">
              Vista unica per operatore con segnali GAIA, Inaz, rete e utilizzo mezzi nello stesso contesto operativo.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link className="btn-secondary" href="/operazioni/operatori">Apri gestione operatori</Link>
            <Link className="btn-secondary" href="/inaz/anomalie">Apri anomalie Inaz</Link>
            <Link className="btn-secondary" href="/network/tracking">Apri tracking rete</Link>
          </div>
        </div>

        <div className="surface-grid mt-6">
          <MetricCard label="Operatori" value={operators.length} sub="Perimetro caricato" />
          <MetricCard label="Con anomalie" value={quickMetrics.anomalyOperators} sub="Operatori con almeno un segnale da verificare" variant="warning" />
          <MetricCard label="Mappati GAIA" value={quickMetrics.mappedGaiaOperators} sub="Operatori collegati a utente applicativo" />
          <MetricCard label="Mappati Inaz" value={quickMetrics.mappedInazOperators} sub={`Collaboratore disponibile a ${monthBounds.label}`} />
          <MetricCard label="Con device rete" value={quickMetrics.networkedOperators} sub="Operatori con almeno un dispositivo assegnato" />
        </div>
      </article>

      {loadError ? <article className="panel-card border border-red-200 bg-red-50 text-sm text-red-700">{loadError}</article> : null}

      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <article className="panel-card min-h-[720px] xl:sticky xl:top-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="section-title">Operatori</p>
              <p className="section-copy">Ricerca e triage rapido sugli operatori caricati.</p>
            </div>
            <Badge variant="neutral">{filteredRows.length}</Badge>
          </div>

          <label className="mt-4 flex items-center gap-3 rounded-2xl border border-gray-200 bg-white px-4 py-3">
            <SearchIcon className="h-4 w-4 text-gray-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Cerca nome, username, matricola, CF"
              className="w-full border-0 bg-transparent text-sm text-gray-900 outline-none placeholder:text-gray-400"
            />
          </label>

          <div className="mt-4 flex flex-wrap gap-2">
            {[
              { value: "all", label: "Tutti" },
              { value: "anomalies", label: "Con anomalie" },
              { value: "with_network", label: "Con rete" },
              { value: "with_inaz", label: "Con Inaz" },
            ].map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => setScope(item.value as typeof scope)}
                className={cn(
                  "rounded-full border px-3 py-1.5 text-xs font-semibold transition",
                  scope === item.value
                    ? "border-[#1D4E35] bg-[#EAF3E8] text-[#1D4E35]"
                    : "border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:text-gray-900",
                )}
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="mt-5 space-y-3 overflow-y-auto pr-1 xl:max-h-[calc(100vh-280px)]">
            {isLoading ? (
              <p className="text-sm text-gray-500">Caricamento operatori.</p>
            ) : filteredRows.length === 0 ? (
              <EmptyState icon={UserIcon} title="Nessun operatore trovato" description="Rivedi ricerca o filtri del cruscotto." />
            ) : (
              filteredRows.map((row) => (
                <button
                  key={row.operator.id}
                  type="button"
                  onClick={() => setSelectedOperatorId(row.operator.id)}
                  className={cn(
                    "w-full rounded-[22px] border p-4 text-left transition",
                    selectedOperatorId === row.operator.id
                      ? "border-[#8CB39D] bg-[#f6fbf7] shadow-sm"
                      : "border-gray-200 bg-white hover:border-[#c8d7cb] hover:bg-[#fbfdfb]",
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[#EAF3E8] text-sm font-semibold text-[#1D4E35]">
                      {initialsForOperator(row.operator)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-gray-900">{displayOperatorName(row.operator)}</p>
                          <p className="truncate text-xs text-gray-500">{row.operator.role?.replaceAll("_", " ") || "Senza ruolo"}</p>
                        </div>
                        {row.anomalyScore > 0 ? <Badge variant="warning">{row.anomalyScore}</Badge> : <Badge variant="success">ok</Badge>}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {row.operator.gaia_user_id ? <span className="rounded-full bg-sky-50 px-2 py-0.5 text-[11px] font-medium text-sky-700">GAIA</span> : null}
                        {row.collaborator ? <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">Inaz</span> : null}
                        {row.devices.length > 0 ? <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">Rete</span> : null}
                        {(row.operator.current_fuel_cards?.length ?? 0) > 0 ? <span className="rounded-full bg-violet-50 px-2 py-0.5 text-[11px] font-medium text-violet-700">Mezzi</span> : null}
                      </div>
                      <p className="mt-2 line-clamp-2 text-xs text-gray-500">{row.flags[0] ?? "Nessuna anomalia immediata rilevata."}</p>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </article>

        <div className="space-y-6">
          {!selectedRow ? (
            <article className="panel-card">
              <EmptyState icon={UserIcon} title="Seleziona un operatore" description="Apri un operatore a sinistra per vedere la scheda aggregata." />
            </article>
          ) : (
            <>
              <article className="panel-card border-[#d9e5dc] bg-[linear-gradient(180deg,#ffffff_0%,#f8fbf8_100%)]">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <div className="flex h-16 w-16 items-center justify-center rounded-[22px] bg-[#EAF3E8] text-lg font-semibold text-[#1D4E35]">
                      {initialsForOperator(selectedRow.operator)}
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">Scheda operatore 360</p>
                      <h3 className="mt-1 text-2xl font-semibold text-gray-900">{displayOperatorName(selectedRow.operator)}</h3>
                      <p className="mt-1 text-sm text-gray-500">
                        {selectedRow.operator.role?.replaceAll("_", " ") || "Senza ruolo"} · WC {selectedRow.operator.wc_id}
                        {selectedRow.operator.gaia_user_id ? ` · GAIA ${selectedRow.operator.gaia_user_id}` : ""}
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {!selectedRow.operator.enabled ? <Badge variant="danger">Operatore disabilitato</Badge> : <Badge variant="success">Operatore attivo</Badge>}
                    {selectedBundle?.gaiaUser && !selectedBundle.gaiaUser.is_active ? <Badge variant="danger">Account GAIA inattivo</Badge> : null}
                    {!selectedRow.collaborator && inazAccessEnabled ? <Badge variant="warning">Senza mapping Inaz</Badge> : null}
                    {selectedBlockedEvents > 0 ? <Badge variant="warning">{selectedBlockedEvents} blocchi rete</Badge> : null}
                  </div>
                </div>

                <div className="surface-grid mt-6">
                  <MetricCard label="Login GAIA" value={selectedBundle?.gaiaUser?.login_count ?? 0} sub={selectedBundle?.gaiaUser?.last_login_at ? `Ultimo ${formatDateTime(selectedBundle.gaiaUser.last_login_at)}` : "Nessun login registrato"} />
                  <MetricCard label="Anomalie Inaz" value={selectedInazAnomalies.length} sub={`Mese ${monthBounds.label}`} variant={selectedInazAnomalies.length > 0 ? "warning" : "default"} />
                  <MetricCard label="Device rete" value={selectedBundle?.devices.length ?? 0} sub={`${selectedAllowedEvents} consentiti / ${selectedBlockedEvents} bloccati`} variant={selectedBlockedEvents > 0 ? "warning" : "default"} />
                  <MetricCard label="Sessioni mezzo" value={selectedBundle?.detail?.stats.usage_sessions_count ?? 0} sub={`${formatNumeric(selectedBundle?.detail?.stats.total_km_travelled, "km")} percorsi`} />
                  <MetricCard label="Fuel card" value={selectedBundle?.detail?.stats.fuel_cards_count ?? 0} sub={`${formatNumeric(selectedBundle?.detail?.stats.total_liters, "L")} riforniti`} />
                </div>
              </article>

              {detailError ? <article className="panel-card border border-red-200 bg-red-50 text-sm text-red-700">{detailError}</article> : null}

              {detailLoading ? (
                <article className="panel-card text-sm text-gray-500">Caricamento scheda operatore.</article>
              ) : selectedBundle ? (
                <>
                  <div className="grid gap-6 xl:grid-cols-2">
                    <article className="panel-card">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="section-title">Riepilogo GAIA</p>
                          <p className="section-copy">Stato account, login e dati applicativi disponibili.</p>
                        </div>
                        <UserIcon className="h-5 w-5 text-gray-400" />
                      </div>
                      {gaiaAccessEnabled ? (
                        <div className="mt-4 grid gap-3 sm:grid-cols-2">
                          <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4 text-sm">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Account</p>
                            <p className="mt-2 font-medium text-gray-900">{selectedBundle.gaiaUser?.username ?? "Non collegato"}</p>
                            <p className="mt-1 text-gray-500">{selectedBundle.gaiaUser?.email ?? selectedRow.operator.email ?? "—"}</p>
                          </div>
                          <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4 text-sm">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Ultimo login</p>
                            <p className="mt-2 font-medium text-gray-900">{formatDateTime(selectedBundle.gaiaUser?.last_login_at)}</p>
                            <p className="mt-1 text-gray-500">{selectedBundle.gaiaUser?.last_login_ip ? `IP ${selectedBundle.gaiaUser.last_login_ip}` : "IP non disponibile"}</p>
                          </div>
                          <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4 text-sm">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Permessi</p>
                            <p className="mt-2 font-medium text-gray-900">
                              {selectedBundle.gaiaUser
                                ? selectedBundle.gaiaUser.enabled_modules.join(", ") || "Nessun modulo"
                                : "Nessun utente GAIA"}
                            </p>
                          </div>
                          <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4 text-sm">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Profilo</p>
                            <p className="mt-2 font-medium text-gray-900">{selectedBundle.gaiaUser?.full_name ?? displayOperatorName(selectedRow.operator)}</p>
                            <p className="mt-1 text-gray-500">{selectedBundle.gaiaUser?.is_active ? "Attivo" : "Non attivo"}</p>
                          </div>
                        </div>
                      ) : (
                        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                          Il tuo profilo non ha accesso al modulo Accessi: il riepilogo sessioni GAIA non e disponibile.
                        </div>
                      )}
                    </article>

                    <article className="panel-card">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="section-title">Riepilogo Inaz</p>
                          <p className="section-copy">Presenze e saldo eventi del mese operativo corrente.</p>
                        </div>
                        <AlertTriangleIcon className="h-5 w-5 text-gray-400" />
                      </div>
                      {inazAccessEnabled ? selectedBundle.collaborator ? (
                        <>
                          <div className="mt-4 grid gap-3 sm:grid-cols-2">
                            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4 text-sm">
                              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Collaboratore</p>
                              <p className="mt-2 font-medium text-gray-900">{selectedBundle.collaborator.name}</p>
                              <p className="mt-1 text-gray-500">Matricola {selectedBundle.collaborator.employee_code}</p>
                            </div>
                            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4 text-sm">
                              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Ultima presenza</p>
                              <p className="mt-2 font-medium text-gray-900">{formatDateTime(selectedBundle.collaborator.last_seen_at)}</p>
                              <p className="mt-1 text-gray-500">{selectedInazAnomalies.length} giornate anomale nel mese</p>
                            </div>
                          </div>

                          <div className="mt-4 rounded-2xl border border-gray-100">
                            <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
                              <p className="text-sm font-medium text-gray-900">Saldi ed eventi</p>
                              <Link className="text-xs font-medium text-[#1D4E35] underline" href={`/inaz/collaboratori/${selectedBundle.collaborator.id}`}>
                                Apri dettaglio Inaz
                              </Link>
                            </div>
                            <div className="divide-y divide-gray-100">
                              {selectedBundle.inazSummary.slice(0, 6).map((item) => (
                                <div key={item.id} className="grid gap-2 px-4 py-3 sm:grid-cols-[1fr_auto]">
                                  <div>
                                    <p className="text-sm font-medium text-gray-900">{item.description}</p>
                                    <p className="mt-1 text-xs text-gray-500">
                                      {item.valid_from ? `${formatDate(item.valid_from)} - ${formatDate(item.valid_to)}` : `${monthBounds.label}`}
                                    </p>
                                  </div>
                                  <div className="text-right text-xs text-gray-600">
                                    <p>Saldo {formatMinutes(item.saldo_minutes)}</p>
                                    <p>Fruito {formatMinutes(item.fruito_minutes)}</p>
                                  </div>
                                </div>
                              ))}
                              {selectedBundle.inazSummary.length === 0 ? (
                                <div className="px-4 py-6 text-sm text-gray-500">Nessun riepilogo Inaz disponibile per il mese corrente.</div>
                              ) : null}
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                          Nessun collaboratore Inaz collegato a questo operatore.
                        </div>
                      ) : (
                        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                          Il tuo profilo non ha accesso al modulo Inaz.
                        </div>
                      )}
                    </article>
                  </div>

                  <div className="grid gap-6 xl:grid-cols-2">
                    <article className="panel-card">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="section-title">Rete e navigazione</p>
                          <p className="section-copy">Dispositivi assegnati, traffico recente e peer principali.</p>
                        </div>
                        <ServerIcon className="h-5 w-5 text-gray-400" />
                      </div>
                      {networkAccessEnabled ? selectedBundle.devices.length > 0 ? (
                        <>
                          <div className="mt-4 grid gap-3 sm:grid-cols-2">
                            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4 text-sm">
                              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Device</p>
                              <p className="mt-2 font-medium text-gray-900">{selectedBundle.devices.length}</p>
                              <p className="mt-1 text-gray-500">{selectedAllowedEvents} eventi consentiti</p>
                            </div>
                            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4 text-sm">
                              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Traffico</p>
                              <p className="mt-2 font-medium text-gray-900">{formatBytes(selectedBytes)}</p>
                              <p className="mt-1 text-gray-500">{selectedBlockedEvents} eventi bloccati</p>
                            </div>
                          </div>

                          <div className="mt-4 rounded-2xl border border-gray-100">
                            <div className="border-b border-gray-100 px-4 py-3">
                              <p className="text-sm font-medium text-gray-900">Dispositivi assegnati</p>
                            </div>
                            <div className="divide-y divide-gray-100">
                              {selectedBundle.devices.slice(0, 6).map((device) => (
                                <div key={device.id} className="grid gap-2 px-4 py-3 sm:grid-cols-[1fr_auto]">
                                  <div>
                                    <p className="text-sm font-medium text-gray-900">{device.resolved_label}</p>
                                    <p className="mt-1 text-xs text-gray-500">{device.ip_address} · {device.operating_system || device.device_type || "Tipo non rilevato"}</p>
                                  </div>
                                  <div className="text-right text-xs text-gray-600">
                                    <p>{device.traffic_summary?.total_events ?? 0} eventi</p>
                                    <p>{device.traffic_summary?.blocked_events ?? 0} bloccati</p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="mt-4 rounded-2xl border border-gray-100">
                            <div className="border-b border-gray-100 px-4 py-3">
                              <p className="text-sm font-medium text-gray-900">Peer / domini principali</p>
                            </div>
                            <div className="divide-y divide-gray-100">
                              {topNetworkPeers.length > 0 ? topNetworkPeers.map((item) => (
                                <div key={item.label} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                                  <div>
                                    <p className="font-medium text-gray-900">{item.label}</p>
                                    <p className="mt-1 text-xs text-gray-500">{formatBytes(item.bytes)}</p>
                                  </div>
                                  <Badge variant="info">{item.count} eventi</Badge>
                                </div>
                              )) : (
                                <div className="px-4 py-6 text-sm text-gray-500">Nessun peer rilevante disponibile.</div>
                              )}
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                          Nessun dispositivo rete assegnato a questo operatore.
                        </div>
                      ) : (
                        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                          Il tuo profilo non ha accesso al modulo Rete.
                        </div>
                      )}
                    </article>

                    <article className="panel-card">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="section-title">Mezzi e carburante</p>
                          <p className="section-copy">Sessioni mezzo, rifornimenti e carte correnti dal dominio Operazioni.</p>
                        </div>
                        <TruckIcon className="h-5 w-5 text-gray-400" />
                      </div>
                      <div className="mt-4 grid gap-3 sm:grid-cols-2">
                        <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4 text-sm">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Sessioni mezzo</p>
                          <p className="mt-2 font-medium text-gray-900">{selectedBundle.detail?.stats.usage_sessions_count ?? 0}</p>
                          <p className="mt-1 text-gray-500">Totale km {formatNumeric(selectedBundle.detail?.stats.total_km_travelled, "km")}</p>
                        </div>
                        <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4 text-sm">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Rifornimenti</p>
                          <p className="mt-2 font-medium text-gray-900">{selectedBundle.detail?.stats.fuel_logs_count ?? 0}</p>
                          <p className="mt-1 text-gray-500">Totale litri {formatNumeric(selectedBundle.detail?.stats.total_liters, "L")}</p>
                        </div>
                      </div>

                      <div className="mt-4 rounded-2xl border border-gray-100">
                        <div className="border-b border-gray-100 px-4 py-3">
                          <p className="text-sm font-medium text-gray-900">Fuel card correnti</p>
                        </div>
                        <div className="flex flex-wrap gap-2 px-4 py-4">
                          {selectedBundle.detail?.current_fuel_cards.length ? selectedBundle.detail.current_fuel_cards.map((card) => (
                            <span key={card.id} className="rounded-full border border-[#d5e2d8] bg-[#f8fbf8] px-3 py-1 text-xs font-semibold text-[#1D4E35]">
                              {card.codice || card.pan}
                            </span>
                          )) : <p className="text-sm text-gray-500">Nessuna fuel card assegnata.</p>}
                        </div>
                      </div>

                      <div className="mt-4 rounded-2xl border border-gray-100">
                        <div className="border-b border-gray-100 px-4 py-3">
                          <p className="text-sm font-medium text-gray-900">Ultime sessioni e rifornimenti</p>
                        </div>
                        <div className="divide-y divide-gray-100">
                          {[...(selectedBundle.detail?.recent_usage_sessions ?? []).slice(0, 3).map((item) => ({
                            id: `session-${item.id}`,
                            title: item.vehicle_label,
                            meta: `Sessione mezzo · ${formatDateTime(item.started_at)}`,
                            extra: `${formatNumeric(item.km_travelled, "km")} · ${item.status}`,
                          })), ...(selectedBundle.detail?.recent_fuel_logs ?? []).slice(0, 3).map((item) => ({
                            id: `fuel-${item.id}`,
                            title: item.vehicle_label,
                            meta: `Rifornimento · ${formatDateTime(item.fueled_at)}`,
                            extra: `${formatNumeric(item.liters, "L")} · ${item.station_name || "stazione n/d"}`,
                          }))].slice(0, 6).map((item) => (
                            <div key={item.id} className="px-4 py-3 text-sm">
                              <p className="font-medium text-gray-900">{item.title}</p>
                              <p className="mt-1 text-xs text-gray-500">{item.meta}</p>
                              <p className="mt-1 text-xs text-gray-600">{item.extra}</p>
                            </div>
                          ))}
                          {(selectedBundle.detail?.recent_usage_sessions.length ?? 0) === 0 &&
                          (selectedBundle.detail?.recent_fuel_logs.length ?? 0) === 0 ? (
                            <div className="px-4 py-6 text-sm text-gray-500">Nessun dato mezzi disponibile.</div>
                          ) : null}
                        </div>
                      </div>
                    </article>
                  </div>

                  <article className="panel-card">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="section-title">Timeline unificata</p>
                        <p className="section-copy">Ultimi segnali rilevanti tra login, Inaz, rete e mezzi.</p>
                      </div>
                      <Badge variant="neutral">{timelineRows.length}</Badge>
                    </div>
                    <div className="mt-4 grid gap-3 lg:grid-cols-2">
                      {timelineRows.length > 0 ? timelineRows.map((item) => (
                        <div key={`${item.label}-${item.value}`} className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">{item.label}</p>
                          <p className="mt-2 text-sm font-medium text-gray-900">{formatDateTime(String(item.value))}</p>
                          <p className="mt-1 text-xs text-gray-500">{item.meta}</p>
                        </div>
                      )) : (
                        <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-6 text-sm text-gray-500">
                          Nessuna timeline disponibile per questo operatore.
                        </div>
                      )}
                    </div>
                  </article>
                </>
              ) : null}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function OperatoriCruscottoPage() {
  return (
    <ProtectedPage
      title="Cruscotto operatori"
      description="Vista aggregata per operatore con dati da GAIA, Inaz, rete e utilizzo mezzi."
      breadcrumb="Amministrazione"
      requiredModule="accessi"
      requiredRoles={["admin", "super_admin"]}
    >
      <OperatorCruscottoContent />
    </ProtectedPage>
  );
}
