"use client";

import { useEffect, useMemo, useState } from "react";

import { FilterPillGroup } from "@/components/network/filter-pill-group";
import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkTrackToggle } from "@/components/network/network-track-toggle";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { BellIcon, ServerIcon } from "@/components/ui/icons";
import {
  createNetworkTrackedSubject,
  getNetworkDevices,
  getNetworkTrackedSubjectActivities,
  listNetworkTrackedSubjects,
  updateNetworkTrackedSubject,
} from "@/lib/api";
import type { NetworkDevice, NetworkTrackedSubject, NetworkTrackedSubjectActivitySummary } from "@/types/api";

const ENTITY_OPTIONS = [
  { value: "", label: "Tutti" },
  { value: "ip", label: "IP" },
  { value: "domain", label: "Domini" },
  { value: "url", label: "URL" },
] as const;

const TRACKING_SCOPE_OPTIONS = [
  { value: "", label: "Tutti" },
  { value: "device", label: "Dispositivi" },
  { value: "web", label: "Traffico esterno" },
] as const;

function isPrivateNetworkIp(value: string | null | undefined) {
  if (!value) {
    return false;
  }
  return value.startsWith("10.") || value.startsWith("192.168.") || /^172\.(1[6-9]|2\d|3[0-1])\./.test(value);
}

function isDeviceLikeTrackedSubject(subject: NetworkTrackedSubject) {
  if (subject.entity_type === "device") {
    return true;
  }
  if (subject.entity_type !== "ip") {
    return false;
  }

  const normalizedNotes = subject.notes?.toLowerCase() ?? "";
  const normalizedLabel = [subject.label, subject.resolved_label].filter(Boolean).join(" ").toLowerCase();
  return (
    isPrivateNetworkIp(subject.value) &&
    (normalizedNotes.startsWith("device interno") ||
      normalizedNotes.includes("associato a") ||
      normalizedLabel.includes("device interno"))
  );
}

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

function metricTone(label: string) {
  switch (label) {
    case "Allowed":
      return "border-emerald-100 bg-emerald-50/80 text-emerald-950";
    case "Blocked":
      return "border-amber-100 bg-amber-50/80 text-amber-950";
    case "Ultimo visto":
      return "border-sky-100 bg-sky-50/80 text-sky-950";
    default:
      return "border-gray-100 bg-white text-gray-950";
  }
}

function TrackingContent({ token }: { token: string }) {
  const [subjects, setSubjects] = useState<NetworkTrackedSubject[]>([]);
  const [deviceSuggestions, setDeviceSuggestions] = useState<NetworkDevice[]>([]);
  const [selectedSuggestedDevice, setSelectedSuggestedDevice] = useState<NetworkDevice | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [trackingScope, setTrackingScope] = useState<"" | "device" | "web">("");
  const [entityFilter, setEntityFilter] = useState<"" | "ip" | "domain" | "url">("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [formType, setFormType] = useState<"ip" | "domain" | "url">("ip");
  const [formValue, setFormValue] = useState("");
  const [formLabel, setFormLabel] = useState("");
  const [formNotes, setFormNotes] = useState("");
  const [quickSearch, setQuickSearch] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [busySubjectId, setBusySubjectId] = useState<number | null>(null);
  const [expandedSubject, setExpandedSubject] = useState<NetworkTrackedSubject | null>(null);
  const [expandedActivity, setExpandedActivity] = useState<NetworkTrackedSubjectActivitySummary | null>(null);
  const [expandedLoading, setExpandedLoading] = useState(false);
  const [expandedError, setExpandedError] = useState<string | null>(null);

  useEffect(() => {
    async function loadSubjects() {
      setIsLoading(true);
      try {
        const response = await listNetworkTrackedSubjects(token, {
          includeInactive,
          windowHours: 168,
          search: search || undefined,
        });
        setSubjects(response);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore caricamento tracking");
      } finally {
        setIsLoading(false);
      }
    }

    void loadSubjects();
  }, [entityFilter, includeInactive, search, token]);

  useEffect(() => {
    const normalized = quickSearch.trim();
    if (!normalized) {
      setDeviceSuggestions([]);
      return;
    }

    let isCancelled = false;
    const timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          const response = await getNetworkDevices(token, {
            search: normalized,
            page: 1,
            pageSize: 6,
          });
          if (!isCancelled) {
            setDeviceSuggestions(response.items);
          }
        } catch {
          if (!isCancelled) {
            setDeviceSuggestions([]);
          }
        }
      })();
    }, 200);

    return () => {
      isCancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [quickSearch, token]);

  const summary = useMemo(() => {
    return {
      total: subjects.length,
      active: subjects.filter((item) => item.is_active).length,
      devices: subjects.filter((item) => isDeviceLikeTrackedSubject(item)).length,
      endpoints: subjects.filter((item) => !isDeviceLikeTrackedSubject(item)).length,
    };
  }, [subjects]);

  const quickSearchMatches = useMemo(() => {
    const normalized = quickSearch.trim().toLowerCase();
    if (!normalized) {
      return [];
    }
    return subjects
      .filter((subject) => {
        const haystack = [subject.value, subject.label, subject.resolved_label, subject.notes, subject.entity_type]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(normalized);
      })
      .slice(0, 6);
  }, [quickSearch, subjects]);

  const quickSearchDeviceMatches = useMemo(() => {
    const normalized = quickSearch.trim().toLowerCase();
    if (!normalized) {
      return [];
    }
    return deviceSuggestions
      .filter((device) => {
        const haystack = [
          device.ip_address,
          device.hostname,
          device.display_name,
          device.resolved_label,
          device.assigned_user?.full_name,
          device.assigned_user?.username,
          device.asset_label,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(normalized);
      })
      .slice(0, 6);
  }, [deviceSuggestions, quickSearch]);
  const visibleSubjects = useMemo(() => {
    return subjects.filter((subject) => {
      const isDeviceLike = isDeviceLikeTrackedSubject(subject);
      if (trackingScope === "device" && !isDeviceLike) {
        return false;
      }
      if (trackingScope === "web" && isDeviceLike) {
        return false;
      }
      if (entityFilter && subject.entity_type !== entityFilter) {
        return false;
      }
      return true;
    });
  }, [entityFilter, subjects, trackingScope]);

  async function handleCreate() {
    if (!selectedSuggestedDevice && !formValue.trim()) {
      setSubmitError("Inserisci un valore da tracciare.");
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const subject = await createNetworkTrackedSubject(
        token,
        selectedSuggestedDevice
          ? {
              entity_type: "device",
              device_id: selectedSuggestedDevice.id,
              label: formLabel.trim() || null,
              notes: formNotes.trim() || null,
            }
          : {
              entity_type: formType,
              value: formValue.trim(),
              label: formLabel.trim() || null,
              notes: formNotes.trim() || null,
            },
      );
      setSubjects((current) => [subject, ...current.filter((item) => item.id !== subject.id)]);
      setFormValue("");
      setFormLabel("");
      setFormNotes("");
      setSelectedSuggestedDevice(null);
      setIncludeInactive(false);
      setTrackingScope("");
      setEntityFilter("");
      setSearch("");
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Errore creazione tracking");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleToggle(subject: NetworkTrackedSubject) {
    setBusySubjectId(subject.id);
    setLoadError(null);
    try {
      const updated = await updateNetworkTrackedSubject(token, subject.id, { is_active: !subject.is_active });
      setSubjects((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore aggiornamento tracking");
    } finally {
      setBusySubjectId(null);
    }
  }

  async function handleOpenExpandedSubject(subject: NetworkTrackedSubject) {
    setExpandedSubject(subject);
    setExpandedLoading(true);
    setExpandedError(null);
    try {
      const activity = await getNetworkTrackedSubjectActivities(token, subject.id, { windowHours: 168, limit: 50 });
      setExpandedActivity(activity);
    } catch (error) {
      setExpandedError(error instanceof Error ? error.message : "Errore caricamento scheda completa");
      setExpandedActivity(null);
    } finally {
      setExpandedLoading(false);
    }
  }

  function applySuggestion(subject: NetworkTrackedSubject) {
    setSelectedSuggestedDevice(null);
    if (subject.entity_type === "ip" || subject.entity_type === "domain" || subject.entity_type === "url") {
      setFormType(subject.entity_type);
      setFormValue(subject.value);
      setFormLabel(subject.label || subject.resolved_label || "");
      setFormNotes(subject.notes || "");
      setQuickSearch(subject.value);
    }
  }

  function applyDeviceSuggestion(device: NetworkDevice) {
    setSelectedSuggestedDevice(device);
    setFormType("ip");
    setFormValue(device.ip_address);
    setFormLabel(device.assigned_user?.full_name || device.resolved_label || device.display_name || device.hostname || "");
    setFormNotes(
      device.assigned_user?.full_name
        ? `Device interno associato a ${device.assigned_user.full_name}`
        : `Device interno: ${device.resolved_label || device.hostname || device.ip_address}`,
    );
    setQuickSearch(device.resolved_label || device.display_name || device.hostname || device.ip_address);
  }

  return (
    <div className="page-stack">
      {expandedSubject ? (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/45 px-4 py-6 backdrop-blur-sm md:p-8">
          <button
            aria-label="Chiudi scheda completa tracking"
            className="absolute inset-0"
            onClick={() => {
              setExpandedSubject(null);
              setExpandedActivity(null);
              setExpandedError(null);
            }}
            type="button"
          />
          <div className="relative z-10 max-h-[calc(100vh-2rem)] w-full max-w-6xl overflow-y-auto rounded-[30px] border border-[#DCE7DF] bg-[linear-gradient(180deg,#FFFFFF_0%,#FBFCF9_100%)] shadow-[0_30px_80px_rgba(15,23,42,0.16)] md:max-h-[calc(100vh-4rem)]">
            <div className="sticky top-0 border-b border-[#E7EFE9] bg-white/95 px-6 py-5 backdrop-blur">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Scheda completa tracking</p>
                  <p className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-gray-950">{expandedSubject.resolved_label}</p>
                  <p className="mt-1 break-all font-mono text-sm text-gray-500">{expandedSubject.value}</p>
                </div>
                <button
                  className="btn-secondary"
                  type="button"
                  onClick={() => {
                    setExpandedSubject(null);
                    setExpandedActivity(null);
                    setExpandedError(null);
                  }}
                >
                  Chiudi
                </button>
              </div>
            </div>

            <div className="p-6">
              {expandedLoading ? <p className="text-sm text-gray-500">Caricamento dettaglio completo.</p> : null}
              {expandedError ? <p className="text-sm text-red-600">{expandedError}</p> : null}
              {!expandedLoading && !expandedError ? (
                <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
                  <aside className="space-y-4">
                    <MetricCard label="Eventi" value={expandedActivity?.total_events ?? expandedSubject.activity_summary?.total_events ?? 0} />
                    <MetricCard label="Allowed" value={expandedActivity?.allowed_events ?? expandedSubject.activity_summary?.allowed_events ?? 0} />
                    <MetricCard label="Blocked" value={expandedActivity?.blocked_events ?? expandedSubject.activity_summary?.blocked_events ?? 0} />
                    <MetricCard
                      label="Ultimo visto"
                      value={
                        expandedActivity?.last_observed_at
                          ? new Date(expandedActivity.last_observed_at).toLocaleString("it-IT")
                          : expandedSubject.activity_summary?.last_observed_at
                            ? new Date(expandedSubject.activity_summary.last_observed_at).toLocaleString("it-IT")
                            : "n/d"
                      }
                    />
                  </aside>
                  <section className="rounded-[24px] border border-[#E7EFE9] bg-[#F8FBF8] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-400">Ultimi eventi</p>
                      <span className="text-xs text-gray-400">Prime {Math.min(expandedActivity?.recent_events.length ?? 0, 50)} voci</span>
                    </div>
                    <div className="mt-4 max-h-[42rem] space-y-3 overflow-y-auto pr-1">
                      {expandedActivity?.recent_events.map((event) => (
                        <div key={`${expandedSubject.id}-expanded-${event.id}`} className="relative rounded-[22px] border border-[#E6F0EA] bg-white px-4 py-4">
                          <div className="absolute left-0 top-4 h-10 w-1 rounded-r-full bg-[#9FC7AB]" />
                          <div className="pl-3">
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <p className="font-medium text-gray-950">{event.event_type}</p>
                              <span className="rounded-full bg-[#F3F8F1] px-2.5 py-1 text-[11px] font-semibold text-[#1D4E35]">
                                {event.protocol || "n/d"}
                              </span>
                            </div>
                            <p className="mt-2 text-xs text-gray-500">
                              {(event.src_device_label || event.src_ip || "src n/d")} → {(event.dst_device_label || event.dst_ip || "dst n/d")}
                            </p>
                            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
                              <span>Match {event.matched_on}</span>
                              <span>In {formatBytes(event.bytes_in)}</span>
                              <span>Out {formatBytes(event.bytes_out)}</span>
                              <span>{new Date(event.observed_at).toLocaleString("it-IT")}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                      {!expandedActivity?.recent_events.length ? (
                        <div className="rounded-[22px] border border-dashed border-[#D9E8DE] bg-white/70 px-4 py-6 text-sm text-gray-500">
                          Nessun evento correlato nel periodo osservato.
                        </div>
                      ) : null}
                    </div>
                  </section>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}

      <article className="overflow-hidden rounded-[30px] border border-[#DCE7DF] bg-[radial-gradient(circle_at_top_left,#F6FBF7_0%,#FFFFFF_48%,#FBFCF9_100%)] shadow-[0_24px_60px_rgba(15,23,42,0.06)]">
        <div className="grid gap-6 p-6 xl:grid-cols-[1.1fr_0.9fr] xl:p-7">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Centro di tracciamento</p>
            <p className="mt-3 max-w-2xl text-3xl font-semibold tracking-[-0.03em] text-gray-950">
              Device interni e target esterni in una console unica.
            </p>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-gray-600">
              Monitora apparati, IP, domini e URL osservati dal firewall Sophos. I riepiloghi usano sempre la finestra operativa delle ultime 168 ore.
            </p>

            <div className="mt-5 flex flex-wrap gap-2">
              <span className="rounded-full border border-[#D9E8DE] bg-white px-3 py-1.5 text-xs font-medium text-[#1D4E35]">Tracking interno</span>
              <span className="rounded-full border border-[#D9E8DE] bg-white px-3 py-1.5 text-xs font-medium text-[#1D4E35]">Peer esterni</span>
              <span className="rounded-full border border-[#D9E8DE] bg-white px-3 py-1.5 text-xs font-medium text-[#1D4E35]">Correlazione eventi</span>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <MetricCard label="Totale" value={summary.total} />
            <MetricCard label="Attivi" value={summary.active} />
            <MetricCard label="Device" value={summary.devices} />
            <MetricCard label="IP / URL / domini" value={summary.endpoints} />
          </div>
        </div>
      </article>

      <article className="overflow-hidden rounded-[30px] border border-[#E3EAE5] bg-white shadow-[0_20px_48px_rgba(15,23,42,0.05)]">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
          <div className="px-6 pt-6">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Aggiungi target</p>
            <p className="mt-3 text-2xl font-semibold tracking-[-0.02em] text-gray-950">Registra rapidamente nuovi osservati.</p>
            <p className="mt-2 text-sm leading-6 text-gray-600">Usa suggerimenti, esempi rapidi o selezione device per creare tracking senza errori di classificazione.</p>
          </div>
          <div className="flex flex-wrap gap-2 px-6 pt-6 text-xs">
            <span className="rounded-full border border-[#D9E8DE] bg-[#F5FAF6] px-3 py-1.5 font-medium text-[#1D4E35]">IP pubblici</span>
            <span className="rounded-full border border-[#D9E8DE] bg-[#F5FAF6] px-3 py-1.5 font-medium text-[#1D4E35]">Domini applicativi</span>
            <span className="rounded-full border border-[#D9E8DE] bg-[#F5FAF6] px-3 py-1.5 font-medium text-[#1D4E35]">URL sensibili</span>
          </div>
        </div>

        <div className="grid gap-6 px-6 pb-6 xl:grid-cols-[0.82fr_1.18fr]">
          <div className="space-y-4">
            <div className="rounded-[26px] border border-[#D8E7DD] bg-[linear-gradient(135deg,#F1F8F3_0%,#FBFDFB_100%)] px-5 py-5">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#1D4E35]">Uso consigliato</p>
              <div className="mt-4 space-y-3">
                <div className="rounded-[22px] border border-white/80 bg-white/90 px-4 py-3 shadow-[0_10px_22px_rgba(15,23,42,0.04)]">
                  <p className="text-sm font-medium text-gray-900">Device interni</p>
                  <p className="mt-1 text-xs leading-5 text-gray-600">
                    Per i PC e gli apparati usa il flag direttamente da dettaglio dispositivo, firewall o statistiche.
                  </p>
                </div>
                <div className="rounded-[22px] border border-white/80 bg-white/90 px-4 py-3 shadow-[0_10px_22px_rgba(15,23,42,0.04)]">
                  <p className="text-sm font-medium text-gray-900">IP e peer esterni</p>
                  <p className="mt-1 text-xs leading-5 text-gray-600">
                    Inserisci qui un IP quando vuoi seguire destinazioni ricorrenti, resolver, CDN o endpoint sospetti.
                  </p>
                </div>
                <div className="rounded-[22px] border border-white/80 bg-white/90 px-4 py-3 shadow-[0_10px_22px_rgba(15,23,42,0.04)]">
                  <p className="text-sm font-medium text-gray-900">Domini e URL</p>
                  <p className="mt-1 text-xs leading-5 text-gray-600">
                    Usa il dominio per famiglie di traffico e l’URL quando vuoi osservare un path o servizio preciso.
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-[26px] border border-[#E7EFE9] bg-[#FAFCFA] px-4 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-400">Esempi rapidi</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {[
                  { type: "ip" as const, value: "8.8.8.8", label: "Resolver pubblico" },
                  { type: "domain" as const, value: "dns.google", label: "Dominio applicativo" },
                  { type: "url" as const, value: "https://dns.google", label: "URL completo" },
                ].map((example) => (
                  <button
                    key={example.value}
                    type="button"
                    onClick={() => {
                      setFormType(example.type);
                      setFormValue(example.value);
                      setFormLabel(example.label);
                    }}
                    className="rounded-full border border-[#D9E8DE] bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:border-[#8CB39D] hover:bg-[#F4FAF6] hover:text-[#1D4E35]"
                  >
                    {example.value}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-[26px] border border-[#E5ECE6] bg-[linear-gradient(180deg,#FFFFFF_0%,#FBFCFA_100%)] px-5 py-5 shadow-[0_18px_40px_rgba(15,23,42,0.05)]">
            <div className="rounded-[22px] border border-[#E7EFE9] bg-[#F8FBF8] px-4 py-4">
              <label className="block text-sm font-medium text-gray-700">
                Ricerca rapida
                <input
                  className="form-control mt-1"
                  value={quickSearch}
                  onChange={(event) => setQuickSearch(event.target.value)}
                  placeholder="Cerca un IP, dominio o URL gia osservato o gia tracciato"
                />
              </label>
              {quickSearchMatches.length ? (
                <div className="mt-3 space-y-2">
                  {quickSearchMatches.map((subject) => (
                    <button
                    key={`quick-${subject.id}`}
                    type="button"
                    onClick={() => applySuggestion(subject)}
                    className="flex w-full items-start justify-between gap-3 rounded-[18px] border border-[#E0E8E2] bg-white px-3 py-3 text-left transition hover:border-[#8CB39D] hover:bg-[#F3F8F1]"
                  >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-gray-900">{subject.resolved_label}</p>
                        <p className="mt-1 truncate text-xs text-gray-500">{subject.value}</p>
                      </div>
                      <Badge variant="neutral">{subject.entity_type.toUpperCase()}</Badge>
                    </button>
                  ))}
                </div>
              ) : null}
              {quickSearchDeviceMatches.length ? (
                <div className="mt-3 space-y-2">
                  {quickSearchDeviceMatches.map((device) => (
                    <button
                    key={`device-${device.id}`}
                    type="button"
                    onClick={() => applyDeviceSuggestion(device)}
                    className="flex w-full items-start justify-between gap-3 rounded-[18px] border border-[#E0E8E2] bg-white px-3 py-3 text-left transition hover:border-[#8CB39D] hover:bg-[#F3F8F1]"
                  >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-gray-900">
                          {device.assigned_user?.full_name || device.resolved_label}
                        </p>
                        <p className="mt-1 truncate text-xs text-gray-500">
                          {device.ip_address}
                          {device.hostname ? ` · ${device.hostname}` : ""}
                        </p>
                      </div>
                      <Badge variant="neutral">DEVICE</Badge>
                    </button>
                  ))}
                </div>
              ) : null}
              {!quickSearchMatches.length && !quickSearchDeviceMatches.length && quickSearch.trim() ? (
                <p className="mt-3 text-xs text-gray-500">Nessun target esistente corrisponde alla ricerca.</p>
              ) : (
                !quickSearch.trim() ? (
                  <p className="mt-3 text-xs text-gray-500">
                  Recupera un target gia noto e usalo come base senza ricompilare tutto il form.
                  </p>
                ) : null
              )}
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-[180px_minmax(0,1fr)]">
              <label className="block text-sm font-medium text-gray-700">
                Tipo target
                <select className="form-control mt-1" value={formType} onChange={(event) => setFormType(event.target.value as "ip" | "domain" | "url")}>
                  <option value="ip">IP</option>
                  <option value="domain">Dominio</option>
                  <option value="url">URL</option>
                </select>
              </label>
              <label className="block text-sm font-medium text-gray-700">
                Valore da tracciare
                <input
                  className="form-control mt-1"
                  value={formValue}
                  onChange={(event) => {
                    setFormValue(event.target.value);
                    setSelectedSuggestedDevice(null);
                  }}
                  placeholder={formType === "ip" ? "es. 8.8.8.8" : formType === "domain" ? "es. example.org" : "https://example.org/path"}
                />
              </label>
            </div>

            {selectedSuggestedDevice ? (
              <div className="mt-4 rounded-[22px] border border-emerald-200 bg-emerald-50/70 px-4 py-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#1D4E35]">Creazione come dispositivo</p>
                    <p className="mt-1 text-sm font-medium text-gray-900">
                      {selectedSuggestedDevice.assigned_user?.full_name || selectedSuggestedDevice.resolved_label || selectedSuggestedDevice.display_name || selectedSuggestedDevice.hostname || selectedSuggestedDevice.ip_address}
                    </p>
                    <p className="mt-1 text-xs text-gray-600">
                      Device #{selectedSuggestedDevice.id} · {selectedSuggestedDevice.ip_address}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="rounded-full border border-[#b7d7c2] bg-white px-3 py-1 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                    onClick={() => setSelectedSuggestedDevice(null)}
                  >
                    Usa come IP normale
                  </button>
                </div>
              </div>
            ) : null}

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="block text-sm font-medium text-gray-700">
                Label operativa
                <input className="form-control mt-1" value={formLabel} onChange={(event) => setFormLabel(event.target.value)} placeholder="Nome sintetico per la console operativa" />
              </label>
              <label className="block text-sm font-medium text-gray-700">
                Note
                <input className="form-control mt-1" value={formNotes} onChange={(event) => setFormNotes(event.target.value)} placeholder="Motivo del monitoraggio o contesto operativo" />
              </label>
            </div>

            {submitError ? <p className="mt-4 text-sm text-red-600">{submitError}</p> : null}

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 pt-4">
              <p className="text-xs text-gray-500">
                Il target verra aggiunto senza duplicati e riattivato automaticamente se era stato disattivato.
              </p>
              <button type="button" className="btn-primary" onClick={() => void handleCreate()} disabled={isSubmitting}>
                {isSubmitting ? "Salvataggio..." : "Aggiungi tracking"}
              </button>
            </div>
          </div>
        </div>
      </article>

      <article className="rounded-[30px] border border-[#E3EAE5] bg-[linear-gradient(180deg,#FFFFFF_0%,#FBFCFA_100%)] p-6 shadow-[0_18px_44px_rgba(15,23,42,0.05)]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Filtri elenco</p>
            <p className="mt-3 text-2xl font-semibold tracking-[-0.02em] text-gray-950">Separa subito dispositivi e traffico esterno.</p>
            <p className="mt-2 text-sm leading-6 text-gray-600">Usa ambito, sottotipo e ricerca testuale per ridurre il perimetro ai target davvero operativi.</p>
          </div>
          <label className="inline-flex items-center gap-2 rounded-full border border-[#D9E8DE] bg-[#F7FAF7] px-3 py-2 text-sm text-gray-600">
            <input type="checkbox" checked={includeInactive} onChange={(event) => setIncludeInactive(event.target.checked)} />
            Mostra anche disattivati
          </label>
        </div>
        <div className="mt-5 grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
          <input
            className="form-control bg-white"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Cerca per valore, label o note"
          />
          <div className="rounded-[24px] border border-[#E7EFE9] bg-[#F8FBF8] p-4">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-gray-400">Ambito</p>
              <FilterPillGroup options={TRACKING_SCOPE_OPTIONS} value={trackingScope} onChange={(value) => {
                setTrackingScope(value);
                if (value === "device") {
                  setEntityFilter("");
                }
              }} />
            </div>
            {trackingScope !== "device" ? (
              <div className="mt-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-gray-400">Tipo target esterno</p>
                <FilterPillGroup options={ENTITY_OPTIONS} value={entityFilter} onChange={setEntityFilter} />
              </div>
            ) : null}
          </div>
        </div>
        {loadError ? <p className="mt-4 text-sm text-red-600">{loadError}</p> : null}
      </article>

      {isLoading ? (
        <article className="panel-card text-sm text-gray-500">Caricamento tracking.</article>
      ) : visibleSubjects.length === 0 ? (
        <article className="panel-card">
          <EmptyState
            icon={BellIcon}
            title={
              trackingScope === "device"
                ? "Nessun dispositivo tracciato"
                : trackingScope === "web"
                  ? "Nessun target esterno tracciato"
                  : "Nessun target tracciato"
            }
            description={
              trackingScope === "device"
                ? "Attiva il tracking dai dettagli dispositivo o dalle viste operative di rete."
                : "Usa i flag nelle viste operative oppure registra qui un IP, dominio o URL."
            }
          />
        </article>
      ) : (
        <section className="grid gap-4">
          {visibleSubjects.map((subject) => {
            const isDeviceLike = isDeviceLikeTrackedSubject(subject);
            const scanHistory = subject.scan_history ?? [];
            const recentEvents = subject.activity_summary?.recent_events ?? [];
            return (
              <article
                key={subject.id}
                className="overflow-hidden rounded-[28px] border border-[#E4ECE6] bg-[linear-gradient(180deg,#FFFFFF_0%,#FBFCF9_100%)] shadow-[0_18px_44px_rgba(15,23,42,0.06)]"
              >
                <div className="h-1.5 bg-[linear-gradient(90deg,#1D4E35_0%,#7EB68E_55%,#E2F2E7_100%)]" />
                <div className="p-5 md:p-6">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={subject.is_active ? "success" : "neutral"}>{subject.is_active ? "Attivo" : "Disattivo"}</Badge>
                        <span className="rounded-full border border-[#D9E8DE] bg-[#F5FAF6] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#1D4E35]">
                          {isDeviceLike ? "Device" : subject.entity_type}
                        </span>
                      </div>

                      <div className="mt-4 rounded-[24px] border border-[#E7EFE9] bg-[#F7FAF7] px-4 py-4">
                        <div className="flex flex-wrap items-start justify-between gap-4">
                          <div className="min-w-0">
                            <p className="text-2xl font-semibold tracking-[-0.02em] text-gray-950">{subject.resolved_label}</p>
                            <p className="mt-1 break-all font-mono text-sm text-gray-500">{subject.value}</p>
                          </div>
                          <div className="text-right text-xs text-gray-400">
                            <p>Creato da {subject.created_by_username || "n/d"}</p>
                            <p className="mt-1">Aggiornato {new Date(subject.updated_at).toLocaleString("it-IT")}</p>
                          </div>
                        </div>
                        {subject.notes ? <p className="mt-3 max-w-3xl text-sm leading-6 text-gray-600">{subject.notes}</p> : null}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center justify-end gap-2">
                      <button
                        type="button"
                        className="rounded-full border border-[#D9E8DE] bg-white px-3 py-1.5 text-xs font-medium text-[#1D4E35] transition hover:bg-[#F4FAF6]"
                        onClick={() => void handleOpenExpandedSubject(subject)}
                      >
                        Visualizza scheda completa
                      </button>
                      <NetworkTrackToggle
                        tracked={subject.is_active}
                        label={subject.is_active ? "Disattiva" : "Riattiva"}
                        busy={busySubjectId === subject.id}
                        onClick={() => void handleToggle(subject)}
                      />
                    </div>
                  </div>

                  <div className={`mt-5 grid gap-4 ${isDeviceLike ? "xl:grid-cols-[280px_minmax(0,1.25fr)_minmax(0,0.95fr)]" : "xl:grid-cols-[280px_minmax(0,1fr)]"}`}>
                    <aside className="space-y-4">
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                        <MetricCard compact label="Eventi" value={subject.activity_summary?.total_events ?? 0} />
                        <MetricCard compact label="Allowed" value={subject.activity_summary?.allowed_events ?? 0} />
                        <MetricCard compact label="Blocked" value={subject.activity_summary?.blocked_events ?? 0} />
                        <MetricCard
                          compact
                          label="Ultimo visto"
                          value={subject.activity_summary?.last_observed_at ? new Date(subject.activity_summary.last_observed_at).toLocaleString("it-IT") : "n/d"}
                        />
                      </div>

                      <div className="rounded-[24px] border border-[#E7EFE9] bg-[#F8FBF8] p-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-400">Traffico aggregato</p>
                        <div className="mt-3 grid gap-3">
                          <div className="rounded-2xl border border-[#E6F0EA] bg-white px-3 py-3">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-400">Ingresso</p>
                            <p className="mt-1 text-lg font-semibold text-gray-950">{formatBytes(subject.activity_summary?.bytes_in ?? 0)}</p>
                          </div>
                          <div className="rounded-2xl border border-[#E6F0EA] bg-white px-3 py-3">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-400">Uscita</p>
                            <p className="mt-1 text-lg font-semibold text-gray-950">{formatBytes(subject.activity_summary?.bytes_out ?? 0)}</p>
                          </div>
                        </div>
                      </div>
                    </aside>

                    <section className="rounded-[24px] border border-[#E7EFE9] bg-[#F8FBF8] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-400">Ultimi eventi</p>
                        <span className="text-xs text-gray-400">{recentEvents.length ? `${Math.min(recentEvents.length, 50)} voci` : "Nessun match"}</span>
                      </div>
                      <div className="mt-4 max-h-[28rem] space-y-3 overflow-y-auto pr-1">
                        {recentEvents.slice(0, 50).map((event) => (
                          <div key={`${subject.id}-${event.id}`} className="relative rounded-[22px] border border-[#E6F0EA] bg-white px-4 py-4">
                            <div className="absolute left-0 top-4 h-10 w-1 rounded-r-full bg-[#9FC7AB]" />
                            <div className="pl-3">
                              <div className="flex flex-wrap items-center justify-between gap-3">
                                <p className="font-medium text-gray-950">{event.event_type}</p>
                                <span className="rounded-full bg-[#F3F8F1] px-2.5 py-1 text-[11px] font-semibold text-[#1D4E35]">
                                  {event.protocol || "n/d"}
                                </span>
                              </div>
                              <p className="mt-2 text-xs text-gray-500">
                                {event.src_ip || "src n/d"} → {event.dst_ip || "dst n/d"}
                              </p>
                              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
                                <span>Match {event.matched_on}</span>
                                <span>In {formatBytes(event.bytes_in)}</span>
                                <span>Out {formatBytes(event.bytes_out)}</span>
                              </div>
                            </div>
                          </div>
                        ))}
                        {!recentEvents.length ? (
                          <div className="rounded-[22px] border border-dashed border-[#D9E8DE] bg-white/70 px-4 py-6 text-sm text-gray-500">
                            Nessun evento correlato nel periodo osservato.
                          </div>
                        ) : null}
                      </div>
                    </section>

                    {isDeviceLike ? (
                      <section className="rounded-[24px] border border-[#E7EFE9] bg-[#F8FBF8] p-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-400">Snapshot dispositivo</p>
                          <span className="text-xs text-gray-400">{scanHistory.length ? `${Math.min(scanHistory.length, 4)} snapshot` : "Nessun dato"}</span>
                        </div>
                        <div className="mt-4 space-y-3">
                          {scanHistory.slice(0, 4).map((entry) => (
                            <div key={`${subject.id}-scan-${entry.scan_id}-${entry.observed_at}`} className="rounded-[22px] border border-[#E6F0EA] bg-white px-4 py-4">
                              <div className="flex items-center justify-between gap-3">
                                <p className="font-medium text-gray-950">Snapshot #{entry.scan_id}</p>
                                <Badge variant={entry.status === "online" ? "success" : "neutral"}>{entry.status}</Badge>
                              </div>
                              <p className="mt-2 text-xs text-gray-500">
                                {entry.ip_address}
                                {entry.hostname ? ` · ${entry.hostname}` : ""}
                              </p>
                              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
                                <span>Porte {entry.open_ports || "n/d"}</span>
                                <span>{new Date(entry.observed_at).toLocaleString("it-IT")}</span>
                              </div>
                            </div>
                          ))}
                          {!scanHistory.length ? (
                            <div className="rounded-[22px] border border-dashed border-[#D9E8DE] bg-white/70 px-4 py-6 text-sm text-gray-500">
                              Nessuno snapshot storico disponibile per questo device.
                            </div>
                          ) : null}
                        </div>
                      </section>
                    ) : null}
                  </div>
                </div>
              </article>
            );
          })}
        </section>
      )}
    </div>
  );
}

function MetricCard({ label, value, compact = false }: { label: string; value: string | number; compact?: boolean }) {
  return (
    <div
      className={`rounded-[22px] border shadow-[0_8px_24px_rgba(15,23,42,0.04)] ${metricTone(label)} ${
        compact ? "px-3 py-3" : "px-4 py-4"
      }`}
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">{label}</p>
      <p className={`mt-2 font-semibold tracking-[-0.02em] ${compact ? "text-lg leading-6" : "text-xl"}`}>{value}</p>
    </div>
  );
}

export default function NetworkTrackingPage() {
  return (
    <NetworkModulePage
      title="Tracking"
      description="Target monitorati nel modulo rete: device interni, IP, domini e URL osservati dal firewall Sophos."
      breadcrumb="Tracking"
    >
      {({ token }) => <TrackingContent token={token} />}
    </NetworkModulePage>
  );
}
