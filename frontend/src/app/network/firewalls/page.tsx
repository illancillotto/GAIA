"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { FilterPillGroup } from "@/components/network/filter-pill-group";
import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { NetworkTrackToggle } from "@/components/network/network-track-toggle";
import { EmptyState } from "@/components/ui/empty-state";
import { RefreshIcon, ServerIcon } from "@/components/ui/icons";
import {
  createNetworkTrackedSubject,
  getNetworkFirewalls,
  getNetworkFirewallEvents,
  getNetworkFirewallLogCoverage,
  getNetworkFirewallMetrics,
  listNetworkTrackedSubjects,
  pollNetworkFirewallMetrics,
} from "@/lib/api";
import { buildNetworkTrackingKey } from "@/lib/network-device-utils";
import type {
  NetworkFirewall,
  NetworkFirewallEvent,
  NetworkFirewallLogCoverageSummary,
  NetworkFirewallMetric,
  NetworkTrackedSubject,
} from "@/types/api";

const SEVERITY_FILTER_OPTIONS = [
  { value: "", label: "Tutte" },
  { value: "critical", label: "Critical" },
  { value: "danger", label: "Danger" },
  { value: "warning", label: "Warning" },
  { value: "info", label: "Info" },
] as const;

const METRIC_LABELS: Record<string, string> = {
  if_number: "Interfacce",
  sys_uptime_ticks: "Uptime",
  sys_descr: "Descrizione SNMP",
  sys_name: "Nome sistema",
};

const LOG_COVERAGE_WINDOW_HOURS = 168;

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

function formatBytes(value: number | null | undefined) {
  if (!value || value <= 0) {
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

function parseEventDetails(event: NetworkFirewallEvent) {
  const rawPayload = event.raw_payload;
  const parsed =
    rawPayload && typeof rawPayload === "object" && "parsed" in rawPayload && rawPayload.parsed && typeof rawPayload.parsed === "object"
      ? (rawPayload.parsed as Record<string, unknown>)
      : null;

  const readNumber = (key: string) => {
    const value = parsed?.[key];
    const numeric = Number(typeof value === "string" || typeof value === "number" ? value : 0);
    return Number.isFinite(numeric) ? numeric : 0;
  };

  const readText = (key: string) => {
    const value = parsed?.[key];
    return typeof value === "string" && value.trim().length > 0 ? value : null;
  };

  return {
    bytesSent: readNumber("bytes_sent"),
    bytesReceived: readNumber("bytes_received"),
    ruleName: readText("fw_rule_name"),
    url: readText("url"),
    domain: readText("domain"),
    srcZone: readText("src_zone"),
    dstZone: readText("dst_zone"),
  };
}

function formatEventEndpoint(ipAddress: string | null, label: string | null, fallback: string) {
  if (!ipAddress) {
    return fallback;
  }
  if (label && label !== ipAddress) {
    return `${ipAddress} · ${label}`;
  }
  return ipAddress;
}

function getCoverageTone(status: "ok" | "missing" | "observed") {
  if (status === "ok") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (status === "missing") {
    return "border-rose-200 bg-rose-50 text-rose-800";
  }
  return "border-amber-200 bg-amber-50 text-amber-800";
}

function FirewallsContent({ token }: { token: string }) {
  const [firewalls, setFirewalls] = useState<NetworkFirewall[]>([]);
  const [selectedFirewallId, setSelectedFirewallId] = useState<number | null>(null);
  const [events, setEvents] = useState<NetworkFirewallEvent[]>([]);
  const [metrics, setMetrics] = useState<NetworkFirewallMetric[]>([]);
  const [logCoverage, setLogCoverage] = useState<NetworkFirewallLogCoverageSummary | null>(null);
  const [trackedSubjects, setTrackedSubjects] = useState<NetworkTrackedSubject[]>([]);
  const [severityFilter, setSeverityFilter] = useState("");
  const [eventSearch, setEventSearch] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [trackingError, setTrackingError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [trackingBusyKey, setTrackingBusyKey] = useState<string | null>(null);

  const loadFirewalls = useCallback(async () => {
    try {
      const firewallItems = await getNetworkFirewalls(token);
      setFirewalls(firewallItems);
      const nextSelectedId = firewallItems[0]?.id ?? null;
      setSelectedFirewallId((current) => current ?? nextSelectedId);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento firewall");
    }
  }, [token]);

  const loadDetails = useCallback(async (firewallId: number, severity: string) => {
    try {
      const [eventItems, metricItems, coverage] = await Promise.all([
        getNetworkFirewallEvents(token, firewallId, { severity: severity || undefined, limit: 50 }),
        getNetworkFirewallMetrics(token, firewallId, { limit: 25 }),
        getNetworkFirewallLogCoverage(token, firewallId, { windowHours: LOG_COVERAGE_WINDOW_HOURS }),
      ]);
      setEvents(eventItems);
      setMetrics(metricItems);
      setLogCoverage(coverage);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento dettaglio firewall");
    }
  }, [token]);

  useEffect(() => {
    void loadFirewalls();
  }, [loadFirewalls]);

  useEffect(() => {
    async function loadTracking() {
      try {
        const subjects = await listNetworkTrackedSubjects(token, { windowHours: 168 });
        setTrackedSubjects(subjects);
        setTrackingError(null);
      } catch (error) {
        setTrackingError(error instanceof Error ? error.message : "Errore caricamento tracking");
      }
    }

    void loadTracking();
  }, [token]);

  useEffect(() => {
    if (selectedFirewallId === null) {
      setEvents([]);
      setMetrics([]);
      setLogCoverage(null);
      return;
    }
    void loadDetails(selectedFirewallId, severityFilter);
  }, [loadDetails, selectedFirewallId, severityFilter]);

  async function handlePoll() {
    if (selectedFirewallId === null) {
      return;
    }
    setIsPolling(true);
    try {
      await pollNetworkFirewallMetrics(token, selectedFirewallId);
      await loadDetails(selectedFirewallId, severityFilter);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore durante il polling SNMP");
    } finally {
      setIsPolling(false);
    }
  }

  const selectedFirewall = firewalls.find((item) => item.id === selectedFirewallId) ?? null;
  const trackedSubjectMap = useMemo(
    () =>
      new Map<string, NetworkTrackedSubject>(
        trackedSubjects
          .filter((subject) => subject.is_active)
          .map((subject) => [`${subject.entity_type}:${subject.normalized_value}`, subject] as const),
      ),
    [trackedSubjects],
  );
  const latestMetricByKey = useMemo(() => {
    const map = new Map<string, NetworkFirewallMetric>();
    for (const metric of metrics) {
      if (!map.has(metric.metric_key)) {
        map.set(metric.metric_key, metric);
      }
    }
    return Array.from(map.values());
  }, [metrics]);

  const filteredEvents = useMemo(() => {
    const normalizedSearch = eventSearch.trim().toLowerCase();
    if (!normalizedSearch) {
      return events;
    }

    return events.filter((event) => {
      const details = parseEventDetails(event);
      const haystack = [
        event.event_type,
        event.message,
        event.src_ip,
        event.dst_ip,
        event.src_device_label,
        event.dst_device_label,
        event.protocol,
        event.severity,
        details.ruleName,
        details.domain,
        details.url,
        details.srcZone,
        details.dstZone,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(normalizedSearch);
    });
  }, [eventSearch, events]);

  async function handleTrack(
    key: string,
    payload:
      | { entity_type: "ip" | "domain" | "url"; value: string; label?: string | null; notes?: string | null },
  ) {
    setTrackingBusyKey(key);
    setTrackingError(null);
    try {
      const subject = await createNetworkTrackedSubject(token, payload);
      setTrackedSubjects((current) => [subject, ...current.filter((item) => item.id !== subject.id)]);
    } catch (error) {
      setTrackingError(error instanceof Error ? error.message : "Errore durante l'attivazione del tracking");
    } finally {
      setTrackingBusyKey(null);
    }
  }

  return (
    <div className="page-stack">
      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Telemetria firewall non disponibile</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <article className="panel-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="section-title">Appliance</p>
              <p className="section-copy">Firewall registrati dal collector Sophos.</p>
            </div>
          </div>

          {firewalls.length === 0 ? (
            <EmptyState
              icon={ServerIcon}
              title="Nessun firewall disponibile"
              description="Avvia prima i collector Sophos oppure collega l’XGS87."
            />
          ) : (
            <div className="space-y-3">
              {firewalls.map((firewall) => (
                <button
                  key={firewall.id}
                  type="button"
                  onClick={() => setSelectedFirewallId(firewall.id)}
                  className={`w-full rounded-lg border px-4 py-3 text-left transition ${
                    firewall.id === selectedFirewallId ? "border-[#1D4E35] bg-[#F3F8F1]" : "border-gray-100 hover:bg-gray-50"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{firewall.name}</p>
                      <p className="mt-1 text-xs text-gray-500">{firewall.management_ip || "IP gestione n/d"}</p>
                    </div>
                    <NetworkStatusBadge status={firewall.status} />
                  </div>
                </button>
              ))}
            </div>
          )}
        </article>

        <div className="page-stack">
          <article className="panel-card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="section-title">{selectedFirewall?.name || "Dettaglio firewall"}</p>
                <p className="section-copy">
                  {selectedFirewall
                    ? `${selectedFirewall.management_ip || "IP n/d"} · ${selectedFirewall.model_name || selectedFirewall.vendor}`
                    : "Seleziona un firewall per visualizzare metriche ed eventi."}
                </p>
              </div>
              <button className="btn-primary" type="button" onClick={handlePoll} disabled={selectedFirewallId === null || isPolling}>
                <RefreshIcon className="h-4 w-4" />
                {isPolling ? "Polling in corso" : "Poll SNMP"}
              </button>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {latestMetricByKey.map((metric) => (
                <div key={metric.metric_key} className="rounded-2xl border border-gray-100 bg-white px-4 py-4">
                  <p className="text-xs uppercase tracking-wide text-gray-400">{METRIC_LABELS[metric.metric_key] || metric.metric_key}</p>
                  <p className="mt-2 text-sm font-medium text-gray-900">
                    {metric.metric_text ?? metric.metric_value ?? "n/d"}{metric.unit ? ` ${metric.unit}` : ""}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">{new Date(metric.observed_at).toLocaleString("it-IT")}</p>
                </div>
              ))}
            </div>
          </article>

          <article className="panel-card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="section-title">Coverage log Sophos</p>
                <p className="section-copy">
                  Verifica automatica delle famiglie attese nelle ultime {logCoverage?.window_hours ?? LOG_COVERAGE_WINDOW_HOURS} ore.
                </p>
              </div>
              <div className="text-right text-xs text-gray-500">
                <p>{logCoverage?.total_events ?? 0} eventi osservati</p>
                <p>{logCoverage ? new Date(logCoverage.generated_at).toLocaleString("it-IT") : "—"}</p>
              </div>
            </div>

            {logCoverage ? (
              <>
                <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                  {logCoverage.expected_families.map((family) => (
                    <div key={family.family_key} className={`rounded-2xl border px-4 py-4 ${getCoverageTone(family.status)}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-[11px] uppercase tracking-[0.16em] opacity-70">{family.label}</p>
                          <p className="mt-2 text-2xl font-semibold">{family.observed_count}</p>
                        </div>
                        <span className="rounded-full bg-white/70 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide">
                          {family.status === "ok" ? "Ok" : "Missing"}
                        </span>
                      </div>
                      <p className="mt-2 text-xs opacity-80">
                        {family.last_observed_at ? new Date(family.last_observed_at).toLocaleString("it-IT") : "Nessun evento nella finestra"}
                      </p>
                      {family.examples.length > 0 ? <p className="mt-2 text-xs opacity-80">{family.examples.join(" · ")}</p> : null}
                    </div>
                  ))}
                </div>

                <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
                  <div className="rounded-2xl border border-gray-100 bg-white px-4 py-4">
                    <p className="text-sm font-semibold text-gray-900">Verifica attesa</p>
                    <p className="mt-1 text-sm text-gray-600">
                      {logCoverage.missing_expected_families.length === 0
                        ? "Tutte le famiglie attese stanno arrivando dal Sophos."
                        : `Mancano: ${logCoverage.missing_expected_families.join(", ")}.`}
                    </p>
                    {logCoverage.additional_families.length > 0 ? (
                      <p className="mt-3 text-xs text-gray-500">
                        Altre famiglie osservate:{" "}
                        {logCoverage.additional_families
                          .slice(0, 4)
                          .map((item) => `${item.label} (${item.observed_count})`)
                          .join(" · ")}
                      </p>
                    ) : null}
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-white px-4 py-4">
                    <p className="text-sm font-semibold text-gray-900">Top eventi recenti</p>
                    <div className="mt-3 space-y-2">
                      {logCoverage.top_event_types.length > 0 ? (
                        logCoverage.top_event_types.map((item) => (
                          <div key={item.key} className="flex items-center justify-between gap-3 text-sm">
                            <span className="truncate text-gray-600">{item.label}</span>
                            <span className="font-medium text-gray-900">{item.count}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-gray-500">Nessun evento nella finestra.</p>
                      )}
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <p className="mt-4 text-sm text-gray-500">Coverage non disponibile.</p>
            )}
          </article>

          <article className="panel-card">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="section-title">Eventi recenti</p>
                <p className="section-copy">Log syslog Sophos correlati nel modulo rete.</p>
              </div>
              <div className="flex w-full flex-wrap justify-end gap-3 xl:w-auto">
                <input
                  className="form-control w-full xl:w-80"
                  value={eventSearch}
                  onChange={(event) => setEventSearch(event.target.value)}
                  placeholder="Cerca per IP, utente, dominio, regola"
                />
                <select className="form-control w-full xl:w-52" value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
                  <option value="">Tutte le severita</option>
                  <option value="critical">Critical</option>
                  <option value="danger">Danger</option>
                  <option value="warning">Warning</option>
                  <option value="info">Info</option>
                </select>
              </div>
            </div>
            {trackingError ? <p className="mb-4 text-sm text-red-600">{trackingError}</p> : null}
            <div className="mb-4">
              <FilterPillGroup options={SEVERITY_FILTER_OPTIONS} value={severityFilter} onChange={setSeverityFilter} />
            </div>
            <p className="mb-4 text-xs text-gray-500">{filteredEvents.length} eventi mostrati</p>

            {filteredEvents.length === 0 ? (
              <EmptyState
                icon={ServerIcon}
                title="Nessun evento disponibile"
                description="Nessun log Sophos corrisponde ai filtri attuali."
              />
            ) : (
              <div className="space-y-3">
                {filteredEvents.map((event) => {
                  const details = parseEventDetails(event);
                  const eventType = formatEventType(event.event_type);
                  const srcTrackKey = event.src_ip ? buildNetworkTrackingKey("ip", event.src_ip) : null;
                  const dstTrackKey = event.dst_ip ? buildNetworkTrackingKey("ip", event.dst_ip) : null;
                  const domainTrackKey = details.domain ? buildNetworkTrackingKey("domain", details.domain) : null;
                  const urlTrackKey = details.url ? buildNetworkTrackingKey("url", details.url) : null;
                  return (
                  <div key={event.id} className="rounded-2xl border border-gray-100 bg-white px-5 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full bg-[#F3F8F1] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#1D4E35]">
                            {eventType.context}
                          </span>
                          <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${eventType.actionTone}`}>
                            {eventType.action}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-gray-500">
                          {formatEventEndpoint(event.src_ip, event.src_device_label, "src n/d")}
                          {" → "}
                          {formatEventEndpoint(event.dst_ip, event.dst_device_label, "dst n/d")}
                          {event.protocol ? ` · ${event.protocol}` : ""}
                          {details.srcZone || details.dstZone ? ` · ${details.srcZone || "?"} → ${details.dstZone || "?"}` : ""}
                        </p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {event.src_ip ? (
                            <NetworkTrackToggle
                              compact
                              tracked={Boolean(event.tracked_src_ip_subject_id || trackedSubjectMap.get(srcTrackKey!))}
                              label="Traccia src"
                              busy={trackingBusyKey === srcTrackKey}
                              onClick={() =>
                                void handleTrack(srcTrackKey!, {
                                  entity_type: "ip",
                                  value: event.src_ip!,
                                  label: event.src_device_label && event.src_device_label !== event.src_ip ? event.src_device_label : null,
                                })
                              }
                            />
                          ) : null}
                          {event.dst_ip ? (
                            <NetworkTrackToggle
                              compact
                              tracked={Boolean(event.tracked_dst_ip_subject_id || trackedSubjectMap.get(dstTrackKey!))}
                              label="Traccia dst"
                              busy={trackingBusyKey === dstTrackKey}
                              onClick={() =>
                                void handleTrack(dstTrackKey!, {
                                  entity_type: "ip",
                                  value: event.dst_ip!,
                                  label: event.dst_device_label && event.dst_device_label !== event.dst_ip ? event.dst_device_label : null,
                                })
                              }
                            />
                          ) : null}
                        </div>
                      </div>
                      <NetworkStatusBadge status={event.severity} />
                    </div>
                    <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      <div className="rounded-xl bg-gray-50 px-3 py-2">
                        <p className="text-[11px] uppercase tracking-wide text-gray-400">Traffico uscita</p>
                        <p className="mt-1 text-sm font-medium text-gray-900">{formatBytes(details.bytesSent)}</p>
                      </div>
                      <div className="rounded-xl bg-gray-50 px-3 py-2">
                        <p className="text-[11px] uppercase tracking-wide text-gray-400">Traffico ingresso</p>
                        <p className="mt-1 text-sm font-medium text-gray-900">{formatBytes(details.bytesReceived)}</p>
                      </div>
                      <div className="rounded-xl bg-gray-50 px-3 py-2 md:col-span-2">
                        <p className="text-[11px] uppercase tracking-wide text-gray-400">Regola</p>
                        <p className="mt-1 truncate text-sm font-medium text-gray-900">{details.ruleName || "n/d"}</p>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-sm text-gray-600">
                      <span className="inline-flex flex-wrap items-center gap-2">
                        <span><span className="text-gray-400">Dominio:</span> {details.domain || "n/d"}</span>
                        {details.domain ? (
                          <NetworkTrackToggle
                            compact
                            tracked={Boolean(event.tracked_domain_subject_id || trackedSubjectMap.get(domainTrackKey!))}
                            label="Traccia"
                            busy={trackingBusyKey === domainTrackKey}
                            onClick={() =>
                              void handleTrack(domainTrackKey!, {
                                entity_type: "domain",
                                value: details.domain!,
                              })
                            }
                          />
                        ) : null}
                      </span>
                      <span className="inline-flex flex-wrap items-center gap-2">
                        <span><span className="text-gray-400">URL:</span> {details.url || "n/d"}</span>
                        {details.url ? (
                          <NetworkTrackToggle
                            compact
                            tracked={Boolean(event.tracked_url_subject_id || trackedSubjectMap.get(urlTrackKey!))}
                            label="Traccia"
                            busy={trackingBusyKey === urlTrackKey}
                            onClick={() =>
                              void handleTrack(urlTrackKey!, {
                                entity_type: "url",
                                value: details.url!,
                              })
                            }
                          />
                        ) : null}
                      </span>
                    </div>
                    <div className="mt-3 flex items-center justify-between gap-3">
                      <p className="text-xs text-gray-400">{new Date(event.observed_at).toLocaleString("it-IT")}</p>
                      <details className="max-w-full text-xs text-gray-500">
                        <summary className="cursor-pointer select-none text-[#1D4E35]">Dettaglio grezzo</summary>
                        <pre className="mt-2 max-w-full overflow-x-auto whitespace-pre-wrap rounded-xl bg-gray-50 p-3 text-[11px] leading-5 text-gray-600">
                          {event.message || "Nessun dettaglio aggiuntivo."}
                        </pre>
                      </details>
                    </div>
                  </div>
                )})}
              </div>
            )}
          </article>
        </div>
      </div>
    </div>
  );
}

export default function NetworkFirewallsPage() {
  return (
    <NetworkModulePage
      title="Firewall"
      description="Telemetria Sophos XGS: appliance registrate, metriche SNMP ed eventi syslog correlati."
      breadcrumb="Firewall"
    >
      {({ token }) => <FirewallsContent token={token} />}
    </NetworkModulePage>
  );
}
