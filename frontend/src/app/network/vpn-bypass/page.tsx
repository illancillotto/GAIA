"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { FilterPillGroup } from "@/components/network/filter-pill-group";
import { NetworkModulePage } from "@/components/network/network-module-page";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, ShieldIcon } from "@/components/ui/icons";
import {
  createNetworkDetectionWatchlistRule,
  getNetworkAlerts,
  getNetworkDetectionWatchlist,
  getNetworkVpnBypassArpTimeline,
  getNetworkVpnBypassSummary,
  listNetworkTrackedSubjects,
  updateNetworkDetectionWatchlistRule,
} from "@/lib/api";
import type {
  NetworkAlert,
  NetworkArpTimelineItem,
  NetworkDetectionWatchlistRule,
  NetworkTrackedSubject,
  NetworkVpnBypassSummary,
} from "@/types/api";

const RISK_OPTIONS = [
  { value: "", label: "Tutti" },
  { value: "vpn", label: "VPN" },
  { value: "proxy", label: "Proxy" },
  { value: "tor", label: "Tor" },
  { value: "dns", label: "Encrypted DNS" },
] as const;

const TRACKING_SCOPE_OPTIONS = [
  { value: "all", label: "Tutti" },
  { value: "tracked", label: "Solo tracked" },
  { value: "untracked", label: "Solo untracked" },
] as const;

const NETWORK_TRACKING_WIKI_HREF =
  "/wiki?q=Aiutami%20a%20fare%20triage%20nel%20modulo%20network%20di%20GAIA%20per%20segnali%20VPN%2C%20proxy%2C%20Tor%20o%20DNS%20cifrato%20mentre%20la%20pagina%20Tracking%20Rete%20e%20in%20costruzione.";

function tagLabel(tag: string) {
  const labels: Record<string, string> = {
    vpn_suspected: "VPN sospetta",
    proxy_suspected: "Proxy sospetto",
    tor_suspected: "Tor sospetto",
    encrypted_dns: "Encrypted DNS",
    vpn_port: "Porta VPN",
    wireguard_port: "WireGuard",
  };
  return labels[tag] || tag;
}

function tagTone(tag: string) {
  if (tag === "vpn_suspected" || tag === "proxy_suspected" || tag === "tor_suspected") {
    return "danger";
  }
  if (tag === "encrypted_dns" || tag === "vpn_port" || tag === "wireguard_port") {
    return "warning";
  }
  return "neutral";
}

function suspiciousCountForRisk(subject: NetworkTrackedSubject, riskFilter: "" | "vpn" | "proxy" | "tor" | "dns") {
  const summary = subject.activity_summary;
  if (!summary) return 0;
  if (riskFilter === "vpn") return summary.vpn_suspected_events;
  if (riskFilter === "proxy") return summary.proxy_suspected_events;
  if (riskFilter === "tor") return summary.tor_suspected_events;
  if (riskFilter === "dns") return summary.encrypted_dns_events;
  return summary.suspicious_events;
}

function isBypassSignalTag(tag: string) {
  return ["vpn_suspected", "proxy_suspected", "tor_suspected", "encrypted_dns", "vpn_port", "wireguard_port"].includes(tag);
}

function suspiciousReasonLabel(reason: string) {
  const labels: Record<string, string> = {
    same_ip_multiple_macs: "Stesso IP con MAC multipli",
    same_mac_multiple_ips: "Stesso MAC su IP multipli",
    rapid_reappearances: "Ricomparse rapide",
  };
  return labels[reason] || reason;
}

function formatIpWithMacHistory(
  ipAddress: string,
  scanHistory: Array<{ ip_address: string; mac_address: string | null }> | undefined,
) {
  const macs = Array.from(
    new Set(
      (scanHistory ?? [])
        .filter((item) => item.ip_address === ipAddress)
        .map((item) => item.mac_address)
        .filter((value): value is string => Boolean(value)),
    ),
  );
  if (macs.length === 0) {
    return ipAddress;
  }
  const [currentMac, ...legacyMacs] = macs;
  return legacyMacs.length > 0
    ? `${ipAddress} · ${currentMac} (ex ${legacyMacs.join(", ")})`
    : `${ipAddress} · ${currentMac}`;
}

function formatMacHistory(
  ipAddress: string,
  scanHistory: Array<{ ip_address: string; mac_address: string | null }> | undefined,
) {
  const macs = Array.from(
    new Set(
      (scanHistory ?? [])
        .filter((item) => item.ip_address === ipAddress)
        .map((item) => item.mac_address)
        .filter((value): value is string => Boolean(value)),
    ),
  );
  if (macs.length === 0) {
    return null;
  }
  const [currentMac, ...legacyMacs] = macs;
  return legacyMacs.length > 0
    ? `${currentMac} (ex ${legacyMacs.join(", ")})`
    : currentMac;
}

function formatEventLabel(eventType: string) {
  return eventType
    .split(".")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" / ");
}

function formatEventTypeParts(eventType: string) {
  const parts = eventType.split(".").filter(Boolean);
  const context = parts[0] ? parts[0].replaceAll("_", " ") : "evento";
  const channel = parts[1] ? parts[1].replaceAll("_", " ") : null;
  const action = parts[2] ? parts[2].replaceAll("_", " ") : null;
  return {
    context: context.charAt(0).toUpperCase() + context.slice(1),
    channel: channel ? channel.charAt(0).toUpperCase() + channel.slice(1) : null,
    action: action ? action.charAt(0).toUpperCase() + action.slice(1) : null,
  };
}

function describeDestination(event: NonNullable<NetworkTrackedSubject["activity_summary"]>["recent_events"][number]) {
  if (event.url) {
    return {
      title: event.domain || event.url,
      subtitle: `URL completa: ${event.url}`,
    };
  }
  if (event.domain) {
    return {
      title: event.domain,
      subtitle: event.dst_ip ? `Dominio risolto verso ${event.dst_ip}` : "Dominio osservato nel traffico web",
    };
  }
  if (event.dst_device_label) {
    return {
      title: event.dst_device_label,
      subtitle: event.dst_ip ? `Host interno o noto: ${event.dst_ip}` : "Host interno noto",
    };
  }
  if (event.dst_ip) {
    return {
      title: event.dst_ip,
      subtitle: "Destinazione IP osservata nel traffico",
    };
  }
  return {
    title: "n/d",
    subtitle: "Destinazione non presente nell'evento",
  };
}

function kpiClassName(baseTone: string, value: number) {
  if (value <= 0) {
    return "border-[#E6F0EA] bg-white text-gray-500";
  }
  return baseTone;
}

function VpnBypassContent({ token }: { token: string }) {
  const [subjects, setSubjects] = useState<NetworkTrackedSubject[]>([]);
  const [alerts, setAlerts] = useState<NetworkAlert[]>([]);
  const [watchlist, setWatchlist] = useState<NetworkDetectionWatchlistRule[]>([]);
  const [arpTimeline, setArpTimeline] = useState<NetworkArpTimelineItem[]>([]);
  const [summary, setSummary] = useState<NetworkVpnBypassSummary | null>(null);
  const [riskFilter, setRiskFilter] = useState<"" | "vpn" | "proxy" | "tor" | "dns">("");
  const [trackingScope, setTrackingScope] = useState<"all" | "tracked" | "untracked">("all");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [savingRuleId, setSavingRuleId] = useState<number | null>(null);
  const [creatingRule, setCreatingRule] = useState(false);
  const [formCategory, setFormCategory] = useState<"vpn" | "proxy" | "tor" | "encrypted_dns">("vpn");
  const [formRuleMode, setFormRuleMode] = useState<"detect" | "allow">("detect");
  const [formMatchType, setFormMatchType] = useState<"keyword" | "domain" | "url" | "ip">("keyword");
  const [formPattern, setFormPattern] = useState("");
  const [formLabel, setFormLabel] = useState("");
  const [trackingModalSubject, setTrackingModalSubject] = useState<NetworkTrackedSubject | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [summaryResponse, trackedSubjects, alertItems, watchlistItems, arpTimelineItems] = await Promise.all([
          getNetworkVpnBypassSummary(token, { windowHours: 168 }),
          listNetworkTrackedSubjects(token, { windowHours: 168, includeInactive: false, includeInferred: true }),
          getNetworkAlerts(token),
          getNetworkDetectionWatchlist(token),
          getNetworkVpnBypassArpTimeline(token, { windowHours: 168, limit: 10 }),
        ]);
        setSummary(summaryResponse);
        setSubjects(trackedSubjects);
        setAlerts(
          alertItems.filter((item) =>
            item.alert_type === "VPN_BYPASS_SUSPECTED"
            || item.alert_type === "VPN_BYPASS_TRANSIENT_DEVICE"
            || item.alert_type === "ARP_EPHEMERAL_DEVICE"
            || item.alert_type === "ARP_MAC_CHANGE_SUSPECTED"
            || item.alert_type === "ARP_IP_ROTATION_SUSPECTED",
          ),
        );
        setWatchlist(watchlistItems);
        setArpTimeline(arpTimelineItems);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore caricamento console bypass");
      }
    }
    void load();
  }, [token]);

  const suspiciousSubjects = useMemo(() => {
    return subjects
      .filter((subject) => suspiciousCountForRisk(subject, riskFilter) > 0)
      .sort((left, right) => {
        const leftTrackedRank = left.device_id !== null ? 0 : 1;
        const rightTrackedRank = right.device_id !== null ? 0 : 1;
        if (leftTrackedRank !== rightTrackedRank) {
          return leftTrackedRank - rightTrackedRank;
        }
        return suspiciousCountForRisk(right, riskFilter) - suspiciousCountForRisk(left, riskFilter);
      });
  }, [riskFilter, subjects]);
  const trackedSuspiciousSubjects = useMemo(
    () => suspiciousSubjects.filter((subject) => subject.device_id !== null),
    [suspiciousSubjects],
  );
  const untrackedSuspiciousSubjects = useMemo(
    () => suspiciousSubjects.filter((subject) => subject.device_id === null),
    [suspiciousSubjects],
  );
  const detectRules = useMemo(() => watchlist.filter((item) => item.rule_mode === "detect"), [watchlist]);
  const allowRules = useMemo(() => watchlist.filter((item) => item.rule_mode === "allow"), [watchlist]);
  const suspiciousArpTimeline = useMemo(
    () => arpTimeline.filter((item) => item.suspicious_reasons.length > 0 || item.rapid_reappearances > 0),
    [arpTimeline],
  );
  const openBypassAlerts = useMemo(
    () => alerts.filter((item) => item.status === "open"),
    [alerts],
  );
  const subjectByDeviceId = useMemo(
    () =>
      new Map(
        subjects.filter((subject) => subject.device_id !== null).map((subject) => [subject.device_id as number, subject]),
      ),
    [subjects],
  );
  const topSuspiciousSubject = suspiciousSubjects[0] ?? null;
  const kpiCards = [
    {
      label: "Target sospetti",
      value: summary?.total_subjects ?? 0,
      tone: "text-rose-700 bg-rose-50 border-rose-100",
      note: "soggetti da verificare",
    },
    {
      label: "Eventi sospetti",
      value: summary?.total_suspicious_events ?? 0,
      tone: "text-amber-700 bg-amber-50 border-amber-100",
      note: "traffico compatibile con bypass",
    },
    {
      label: "Alert aperti",
      value: summary?.open_alerts ?? 0,
      tone: "text-fuchsia-700 bg-fuchsia-50 border-fuchsia-100",
      note: "casi già alzati dal sistema",
    },
    {
      label: "Device spariti",
      value: summary?.transient_device_alerts ?? 0,
      tone: "text-slate-700 bg-slate-100 border-slate-200",
      note: "presenza breve poi offline",
    },
    {
      label: "ARP transienti",
      value: summary?.arp_ephemeral_alerts ?? 0,
      tone: "text-orange-700 bg-orange-50 border-orange-100",
      note: "host ARP effimeri",
    },
    {
      label: "ARP identity",
      value: summary?.arp_identity_alerts ?? 0,
      tone: "text-yellow-700 bg-yellow-50 border-yellow-100",
      note: "stesso IP con MAC diversi",
    },
    {
      label: "ARP spoofing",
      value: summary?.arp_spoofing_alerts ?? 0,
      tone: "text-red-700 bg-red-50 border-red-100",
      note: "stesso MAC su IP multipli",
    },
    {
      label: "Regole watchlist",
      value: summary?.watchlist_rules ?? watchlist.length,
      tone: "text-emerald-700 bg-emerald-50 border-emerald-100",
      note: "detection + whitelist attive",
    },
  ] as const;

  function handleExportCsv() {
    const rows = [
      ["subject_id", "entity_type", "label", "value", "suspicious_events", "vpn_events", "proxy_events", "tor_events", "encrypted_dns_events", "top_tags"].join(","),
      ...suspiciousSubjects.map((subject) =>
        [
          subject.id,
          subject.entity_type,
          `"${(subject.resolved_label || "").replaceAll('"', '""')}"`,
          `"${(subject.value || "").replaceAll('"', '""')}"`,
          subject.activity_summary?.suspicious_events ?? 0,
          subject.activity_summary?.vpn_suspected_events ?? 0,
          subject.activity_summary?.proxy_suspected_events ?? 0,
          subject.activity_summary?.tor_suspected_events ?? 0,
          subject.activity_summary?.encrypted_dns_events ?? 0,
          `"${(subject.activity_summary?.top_detection_tags ?? []).join(" | ").replaceAll('"', '""')}"`,
        ].join(","),
      ),
    ];
    const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "network-vpn-bypass-report.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  async function handleToggleRule(rule: NetworkDetectionWatchlistRule) {
    setSavingRuleId(rule.id);
    try {
      const updated = await updateNetworkDetectionWatchlistRule(token, rule.id, { is_active: !rule.is_active });
      setWatchlist((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore aggiornamento watchlist");
    } finally {
      setSavingRuleId(null);
    }
  }

  async function handleCreateRule() {
    if (!formPattern.trim()) {
      setLoadError("Inserisci un pattern watchlist.");
      return;
    }
    setCreatingRule(true);
    try {
      const created = await createNetworkDetectionWatchlistRule(token, {
        category: formCategory,
        rule_mode: formRuleMode,
        match_type: formMatchType,
        pattern: formPattern.trim(),
        label: formLabel.trim() || null,
        is_active: true,
      });
      setWatchlist((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setFormPattern("");
      setFormLabel("");
      setFormRuleMode("detect");
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore creazione regola watchlist");
    } finally {
      setCreatingRule(false);
    }
  }

  function renderSuspiciousSubjectCard(subject: NetworkTrackedSubject) {
    const recentEvents = subject.activity_summary?.recent_events ?? [];
    const macLabel = subject.device_id !== null ? formatMacHistory(subject.value, subject.scan_history) : null;
    return (
      <article key={subject.id} className="rounded-[28px] border border-[#E4ECE6] bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="neutral">{subject.entity_type.toUpperCase()}</Badge>
              <Badge variant={subject.device_id !== null ? "success" : "neutral"}>
                {subject.device_id !== null ? "Tracked device" : "Untracked"}
              </Badge>
              <Badge variant="danger">{suspiciousCountForRisk(subject, riskFilter)} segnali</Badge>
            </div>
            <p className="mt-3 text-xl font-semibold text-gray-950">{subject.resolved_label}</p>
            <p className="mt-1 break-all font-mono text-sm text-gray-500">
              {subject.device_id !== null ? formatIpWithMacHistory(subject.value, subject.scan_history) : subject.value}
            </p>
            {macLabel ? <p className="mt-1 break-all font-mono text-xs text-gray-500">MAC {macLabel}</p> : null}
          </div>
          <button
            type="button"
            className="rounded-full border border-[#D9E8DE] bg-[#F7FAF7] px-3 py-1.5 text-xs font-medium text-[#1D4E35]"
            onClick={() => setTrackingModalSubject(subject)}
          >
            Apri tracking
          </button>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {(subject.activity_summary?.top_detection_tags ?? []).map((tag) => (
            <Badge key={`${subject.id}-${tag}`} variant={tagTone(tag)}>{tagLabel(tag)}</Badge>
          ))}
        </div>
        {recentEvents.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">Ultimo segnale</p>
            <p className="mt-2 text-sm font-medium text-gray-950">{formatEventLabel(recentEvents[0].event_type)}</p>
            <p className="mt-1 text-xs text-gray-500">{new Date(recentEvents[0].observed_at).toLocaleString("it-IT")}</p>
          </div>
        ) : null}
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <div className="rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] px-3 py-3 text-sm">
            <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">VPN</p>
            <p className="mt-2 font-semibold text-gray-950">{subject.activity_summary?.vpn_suspected_events ?? 0}</p>
          </div>
          <div className="rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] px-3 py-3 text-sm">
            <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Proxy</p>
            <p className="mt-2 font-semibold text-gray-950">{subject.activity_summary?.proxy_suspected_events ?? 0}</p>
          </div>
          <div className="rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] px-3 py-3 text-sm">
            <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Tor</p>
            <p className="mt-2 font-semibold text-gray-950">{subject.activity_summary?.tor_suspected_events ?? 0}</p>
          </div>
          <div className="rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] px-3 py-3 text-sm">
            <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Encrypted DNS</p>
            <p className="mt-2 font-semibold text-gray-950">{subject.activity_summary?.encrypted_dns_events ?? 0}</p>
          </div>
        </div>
      </article>
    );
  }

  return (
    <div className="page-stack">
      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Console bypass non disponibile</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      <article className="overflow-hidden rounded-[30px] border border-[#DCE7DF] bg-[radial-gradient(circle_at_top_left,#F6FBF7_0%,#FFFFFF_46%,#FBFCF9_100%)] shadow-[0_24px_60px_rgba(15,23,42,0.06)]">
        <div className="grid gap-6 p-6 xl:grid-cols-[1.05fr_0.95fr] xl:p-7">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">VPN / Proxy Bypass</p>
            <p className="mt-3 max-w-2xl text-3xl font-semibold tracking-[-0.03em] text-gray-950">
              Segnali operativi di tentativi di aggiramento dei blocchi.
            </p>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-gray-600">
              La vista usa eventi Sophos e watchlist interne per evidenziare traffico compatibile con VPN, proxy, Tor o DNS cifrato.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Badge variant="danger">{openBypassAlerts.length} alert aperti</Badge>
              <Badge variant="warning">{suspiciousArpTimeline.length} anomalie ARP</Badge>
              <Badge variant="info">{detectRules.length} regole detect</Badge>
              <Badge variant="success">{allowRules.length} whitelist</Badge>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link href="/network/alerts" className="rounded-full border border-[#D9E8DE] bg-white px-4 py-2 text-sm font-medium text-[#1D4E35] shadow-sm">
                Apri coda alert
              </Link>
              <Link href={NETWORK_TRACKING_WIKI_HREF} className="rounded-full border border-[#D9E8DE] bg-[#F7FAF7] px-4 py-2 text-sm font-medium text-[#1D4E35]">
                Apri assistente Wiki
              </Link>
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <div className="rounded-[24px] border border-[#E4ECE6] bg-white/90 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">Focus attuale</p>
                <p className="mt-2 text-lg font-semibold text-gray-950">
                  {riskFilter === "" ? "Tutti i segnali" : `Filtro ${RISK_OPTIONS.find((item) => item.value === riskFilter)?.label ?? riskFilter}`}
                </p>
                <p className="mt-1 text-sm text-gray-600">La console mostra il sottoinsieme operativo che stai triaggiando.</p>
              </div>
              <div className="rounded-[24px] border border-[#E4ECE6] bg-white/90 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">Target prioritario</p>
                <p className="mt-2 text-lg font-semibold text-gray-950">{topSuspiciousSubject?.resolved_label ?? "Nessuno"}</p>
                <p className="mt-1 text-sm text-gray-600">
                  {topSuspiciousSubject ? `${suspiciousCountForRisk(topSuspiciousSubject, riskFilter)} segnali nella finestra corrente` : "Nessun soggetto sopra soglia"}
                </p>
              </div>
              <div className="rounded-[24px] border border-[#E4ECE6] bg-white/90 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">Vista target</p>
                <p className="mt-2 text-lg font-semibold text-gray-950">
                  {trackingScope === "all" ? "Tracked + untracked" : trackingScope === "tracked" ? "Solo tracked" : "Solo untracked"}
                </p>
                <p className="mt-1 text-sm text-gray-600">Separazione utile per distinguere device interni e indicatori esterni.</p>
              </div>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {kpiCards.map((card) => (
              <div key={card.label} className={`rounded-[22px] border px-4 py-4 transition-colors ${kpiClassName(card.tone, card.value)}`}>
                <div className="flex items-start justify-between gap-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] opacity-75">{card.label}</p>
                  {card.value > 0 ? <span className="rounded-full bg-white/70 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-gray-600">attivo</span> : null}
                </div>
                <p className="mt-2 text-2xl font-semibold text-gray-950">{card.value}</p>
                <p className="mt-1 text-xs text-gray-500">{card.note}</p>
              </div>
            ))}
          </div>
        </div>
      </article>

      <article className="panel-card">
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-end">
          <div className="space-y-4">
            <div>
              <p className="section-title">Triage operativo</p>
              <p className="section-copy">Riduci la vista al rischio che vuoi verificare e scegli se lavorare solo su tracked o untracked.</p>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-gray-400">Filtro rischio</p>
                <FilterPillGroup options={RISK_OPTIONS} value={riskFilter} onChange={(value) => setRiskFilter(value as "" | "vpn" | "proxy" | "tor" | "dns")} />
              </div>
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-gray-400">Perimetro target</p>
                <FilterPillGroup
                  options={TRACKING_SCOPE_OPTIONS}
                  value={trackingScope}
                  onChange={(value) => setTrackingScope(value as "all" | "tracked" | "untracked")}
                />
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="rounded-full border border-[#D9E8DE] bg-[#F8FBF8] px-4 py-2 text-sm text-[#1D4E35]">
              {trackedSuspiciousSubjects.length} tracked · {untrackedSuspiciousSubjects.length} untracked
            </div>
            <button type="button" className="btn-secondary" onClick={handleExportCsv} disabled={suspiciousSubjects.length === 0}>
              Esporta CSV
            </button>
          </div>
        </div>
      </article>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_420px]">
        <section className="space-y-4">
          <article className="panel-card">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="section-title">Target sospetti</p>
                <p className="section-copy">Solo soggetti con segnali di bypass nella finestra operativa.</p>
              </div>
              <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700">{suspiciousSubjects.length}</span>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] px-4 py-3">
                <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Tracked</p>
                <p className="mt-2 text-xl font-semibold text-gray-950">{trackedSuspiciousSubjects.length}</p>
              </div>
              <div className="rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] px-4 py-3">
                <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Untracked</p>
                <p className="mt-2 text-xl font-semibold text-gray-950">{untrackedSuspiciousSubjects.length}</p>
              </div>
              <div className="rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] px-4 py-3">
                <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Top target</p>
                <p className="mt-2 truncate text-sm font-semibold text-gray-950">{topSuspiciousSubject?.resolved_label ?? "Nessuno"}</p>
              </div>
            </div>
          </article>
          {suspiciousSubjects.length === 0 ? (
            <EmptyState icon={ShieldIcon} title="Nessun target sospetto" description="Non ci sono soggetti con i filtri correnti." />
          ) : (
            <div className="space-y-5">
              {(trackingScope === "all" || trackingScope === "tracked") && trackedSuspiciousSubjects.length > 0 ? (
                <section className="space-y-4">
                  <div className="flex items-center justify-between gap-3 rounded-2xl border border-[#D9E8DE] bg-[#F8FBF8] px-4 py-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#1D4E35]">Tracked Device</p>
                      <p className="mt-1 text-sm text-gray-600">Device noti o monitorati con segnali di bypass.</p>
                    </div>
                    <span className="rounded-full bg-[#E8F3EC] px-2.5 py-1 text-xs font-medium text-[#1D4E35]">{trackedSuspiciousSubjects.length}</span>
                  </div>
                  {trackedSuspiciousSubjects.map(renderSuspiciousSubjectCard)}
                </section>
              ) : null}
              {(trackingScope === "all" || trackingScope === "untracked") && untrackedSuspiciousSubjects.length > 0 ? (
                <section className="space-y-4">
                  <div className="flex items-center justify-between gap-3 rounded-2xl border border-[#E5E7EB] bg-[#FBFBFC] px-4 py-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">Target Esterni / Untracked</p>
                      <p className="mt-1 text-sm text-gray-600">IP, domini o URL sospetti non ancora agganciati a un device tracciato.</p>
                    </div>
                    <span className="rounded-full bg-[#EEF1F4] px-2.5 py-1 text-xs font-medium text-slate-600">{untrackedSuspiciousSubjects.length}</span>
                  </div>
                  {untrackedSuspiciousSubjects.map(renderSuspiciousSubjectCard)}
                </section>
              ) : null}
              {trackingScope === "tracked" && trackedSuspiciousSubjects.length === 0 ? (
                <EmptyState icon={ShieldIcon} title="Nessun tracked sospetto" description="Non ci sono device tracciati con i filtri correnti." />
              ) : null}
              {trackingScope === "untracked" && untrackedSuspiciousSubjects.length === 0 ? (
                <EmptyState icon={ShieldIcon} title="Nessun untracked sospetto" description="Non ci sono target esterni o non agganciati con i filtri correnti." />
              ) : null}
            </div>
          )}

          <article className="panel-card">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="section-title">Timeline ARP</p>
                <p className="section-copy">Storico persistito per IP/MAC con segnali di churn, ricomparse rapide e possibili spoofing.</p>
              </div>
              <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">{suspiciousArpTimeline.length}</span>
            </div>
            {suspiciousArpTimeline.length === 0 ? (
              <div className="mt-4">
                <EmptyState icon={ShieldIcon} title="Nessuna anomalia ARP" description="Nella finestra corrente non risultano pattern ARP sospetti." />
              </div>
            ) : (
              <div className="mt-4 grid gap-4">
                {suspiciousArpTimeline.map((item) => (
                  <article key={item.scope_key} className={`rounded-[26px] border p-5 shadow-sm ${item.suspicious_reasons.includes("same_mac_multiple_ips") ? "border-red-200 bg-red-50/40" : "border-[#E6E1C9] bg-[#FFFDF6]"}`}>
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <div className="flex flex-wrap gap-2">
                          <Badge variant={item.device_id !== null ? "success" : "neutral"}>
                            {item.device_id !== null ? "Tracked ARP" : "Untracked ARP"}
                          </Badge>
                          {item.suspicious_reasons.map((reason) => (
                            <Badge key={`${item.scope_key}-${reason}`} variant="warning">{suspiciousReasonLabel(reason)}</Badge>
                          ))}
                        </div>
                        <p className="mt-3 text-xl font-semibold text-gray-950">{item.resolved_label || item.primary_ip_address || item.scope_key}</p>
                        <p className="mt-1 font-mono text-sm text-gray-500">
                          {item.primary_ip_address || "IP n/d"} {item.primary_mac_address ? `· ${item.primary_mac_address}` : ""}
                        </p>
                      </div>
                      <div className="grid min-w-[220px] gap-2 sm:grid-cols-2">
                        <div className="rounded-2xl border border-[#EEE7CF] bg-white px-3 py-3 text-sm">
                          <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Ricomparse rapide</p>
                          <p className="mt-2 font-semibold text-gray-950">{item.rapid_reappearances}</p>
                        </div>
                        <div className="rounded-2xl border border-[#EEE7CF] bg-white px-3 py-3 text-sm">
                          <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Osservazioni</p>
                          <p className="mt-2 font-semibold text-gray-950">{item.observations_count}</p>
                        </div>
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Badge variant="neutral">{item.online_appearances} online</Badge>
                      <Badge variant="neutral">{item.offline_appearances} offline</Badge>
                      {item.device_id !== null ? <Badge variant="success">agganciato a device tracciato</Badge> : <Badge variant="warning">richiede correlazione manuale</Badge>}
                      {item.suspicious_reasons.includes("same_mac_multiple_ips") ? <Badge variant="danger">priorita alta</Badge> : null}
                    </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-3">
                      <div className="rounded-2xl border border-[#EEE7CF] bg-white px-3 py-3 text-sm">
                        <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">IP distinti</p>
                        <p className="mt-2 font-medium text-gray-950">{item.distinct_ip_addresses.join(", ") || "n/d"}</p>
                      </div>
                      <div className="rounded-2xl border border-[#EEE7CF] bg-white px-3 py-3 text-sm">
                        <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">MAC distinti</p>
                        <p className="mt-2 font-medium text-gray-950">{item.distinct_mac_addresses.join(", ") || "n/d"}</p>
                      </div>
                      <div className="rounded-2xl border border-[#EEE7CF] bg-white px-3 py-3 text-sm">
                        <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Finestra</p>
                        <p className="mt-2 font-medium text-gray-950">
                          {new Date(item.first_observed_at).toLocaleString("it-IT")} {"->"} {new Date(item.last_observed_at).toLocaleString("it-IT")}
                        </p>
                      </div>
                    </div>
                    <div className="mt-4 space-y-2">
                      {item.observations.map((observation) => (
                        <div key={`${item.scope_key}-${observation.scan_id}-${observation.observed_at}`} className="rounded-xl border border-[#F2EBD4] bg-white/80 px-3 py-2.5 text-xs text-gray-700">
                          <p className="font-medium text-gray-950">{new Date(observation.observed_at).toLocaleString("it-IT")} · {observation.status}</p>
                          <p className="mt-1 font-mono">{observation.ip_address}{observation.mac_address ? ` · ${observation.mac_address}` : ""}</p>
                          {observation.hostname ? <p className="mt-1">{observation.hostname}</p> : null}
                        </div>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </article>

        </section>

        <aside className="space-y-4 xl:sticky xl:top-6 self-start">
          <article className="panel-card">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="section-title">Alert aperti</p>
                <p className="section-copy mt-1">Alert automatici generati quando l&apos;ingest vede segnali sospetti.</p>
              </div>
              <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700">{openBypassAlerts.length}</span>
            </div>
            <div className="mt-4 space-y-3">
              {openBypassAlerts.length === 0 ? (
                <EmptyState icon={AlertTriangleIcon} title="Nessun alert aperto" description="Nella finestra corrente non risultano casi aperti di bypass." />
              ) : (
                openBypassAlerts.map((alert) => (
                  <div key={alert.id} className={`rounded-2xl border px-4 py-3 ${alert.alert_type === "ARP_IP_ROTATION_SUSPECTED" ? "border-red-200 bg-red-50/70" : "border-rose-200 bg-rose-50/70"}`}>
                    <p className="text-sm font-medium text-rose-950">{alert.title}</p>
                    <p className="mt-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-rose-700">{alert.alert_type}</p>
                    <p className="mt-1 text-xs leading-5 text-rose-900">{alert.message || "Nessun dettaglio."}</p>
                    {alert.alert_type === "VPN_BYPASS_TRANSIENT_DEVICE" && alert.device_id !== null ? (() => {
                      const subject = subjectByDeviceId.get(alert.device_id);
                      const recentBypassEvents = (subject?.activity_summary?.recent_events ?? [])
                        .filter((event) => event.detection_tags.some(isBypassSignalTag))
                        .slice(0, 3);
                      const lastSeenAt = subject?.scan_history?.[0]?.observed_at ?? null;
                      if (!subject) {
                        return null;
                      }
                      return (
                        <div className="mt-3 rounded-xl border border-rose-200/70 bg-white/70 p-3">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-rose-700">Timeline caso</p>
                          <div className="mt-2 space-y-2 text-xs text-rose-950">
                            <p>
                              <span className="font-medium">Target:</span> {subject.resolved_label}
                            </p>
                            {lastSeenAt ? (
                              <p>
                                <span className="font-medium">Ultimo seen in rete:</span> {new Date(lastSeenAt).toLocaleString("it-IT")}
                              </p>
                            ) : null}
                            {recentBypassEvents.map((event) => (
                              <div key={event.id} className="rounded-lg border border-rose-100 bg-rose-50/60 px-2.5 py-2">
                                <p className="font-medium">{new Date(event.observed_at).toLocaleString("it-IT")}</p>
                                <p className="mt-1">{event.event_type} {event.protocol ? `· ${event.protocol}` : ""}</p>
                                <div className="mt-1 flex flex-wrap gap-1">
                                  {event.detection_tags.filter(isBypassSignalTag).map((tag) => (
                                    <Badge key={`${event.id}-${tag}`} variant={tagTone(tag)}>{tagLabel(tag)}</Badge>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })() : null}
                  </div>
                ))
              )}
            </div>
          </article>

          <article className="panel-card">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="section-title">Watchlist</p>
                <p className="section-copy mt-1">Regole amministrabili che alimentano la detection di provider e segnali noti.</p>
              </div>
              <div className="flex flex-col items-end gap-2">
                <Badge variant="info">{detectRules.length} detect</Badge>
                <Badge variant="success">{allowRules.length} allow</Badge>
              </div>
            </div>
            <div className="mt-4 grid gap-3 rounded-[24px] border border-[#E6F0EA] bg-[#F8FBF8] p-4">
              <select className="form-control" value={formCategory} onChange={(event) => setFormCategory(event.target.value as "vpn" | "proxy" | "tor" | "encrypted_dns")}>
                <option value="vpn">VPN</option>
                <option value="proxy">Proxy</option>
                <option value="tor">Tor</option>
                <option value="encrypted_dns">Encrypted DNS</option>
              </select>
              <select className="form-control" value={formRuleMode} onChange={(event) => setFormRuleMode(event.target.value as "detect" | "allow")}>
                <option value="detect">Detection</option>
                <option value="allow">Whitelist</option>
              </select>
              <select className="form-control" value={formMatchType} onChange={(event) => setFormMatchType(event.target.value as "keyword" | "domain" | "url" | "ip")}>
                <option value="keyword">Keyword</option>
                <option value="domain">Domain</option>
                <option value="url">URL</option>
                <option value="ip">IP</option>
              </select>
              <input className="form-control" value={formPattern} onChange={(event) => setFormPattern(event.target.value)} placeholder="Pattern da monitorare" />
              <input className="form-control" value={formLabel} onChange={(event) => setFormLabel(event.target.value)} placeholder="Label operativa opzionale" />
              <button type="button" className="btn-primary" disabled={creatingRule} onClick={() => void handleCreateRule()}>
                {creatingRule ? "Salvataggio..." : "Aggiungi regola"}
              </button>
            </div>
            <div className="mt-4 max-h-[32rem] space-y-3 overflow-y-auto">
              {[...detectRules, ...allowRules].map((rule) => (
                <div key={rule.id} className="rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-gray-950">{rule.label || rule.pattern}</p>
                      <p className="mt-1 text-xs text-gray-500">{rule.category} · {rule.rule_mode === "allow" ? "whitelist" : "detect"} · {rule.match_type}</p>
                      <p className="mt-1 break-all text-xs text-gray-600">{rule.pattern}</p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <Badge variant={rule.rule_mode === "allow" ? "success" : "info"}>
                        {rule.rule_mode === "allow" ? "Allow" : "Detect"}
                      </Badge>
                    <button
                      type="button"
                      className="rounded-full border border-[#D9E8DE] bg-white px-3 py-1 text-xs font-medium text-[#1D4E35]"
                      disabled={savingRuleId === rule.id}
                      onClick={() => void handleToggleRule(rule)}
                    >
                      {rule.is_active ? "Disattiva" : "Riattiva"}
                    </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </article>
        </aside>
      </div>

      {trackingModalSubject ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4" onClick={() => setTrackingModalSubject(null)}>
          <div
            className="max-h-[92vh] w-full max-w-6xl overflow-hidden rounded-[32px] border border-[#DCE7DF] bg-white shadow-[0_30px_80px_rgba(15,23,42,0.24)]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4 border-b border-[#E6F0EA] bg-[radial-gradient(circle_at_top_left,#F6FBF7_0%,#FFFFFF_65%)] px-6 py-5">
              <div>
                {(() => {
                  const macLabel = trackingModalSubject.device_id !== null
                    ? formatMacHistory(trackingModalSubject.value, trackingModalSubject.scan_history)
                    : null;
                  return (
                    <>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Tracking rapido</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-gray-950">{trackingModalSubject.resolved_label}</h2>
                <p className="mt-1 break-all font-mono text-sm text-gray-500">
                  {trackingModalSubject.device_id !== null ? formatIpWithMacHistory(trackingModalSubject.value, trackingModalSubject.scan_history) : trackingModalSubject.value}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge variant="neutral">{trackingModalSubject.entity_type.toUpperCase()}</Badge>
                  <Badge variant={trackingModalSubject.device_id !== null ? "success" : "warning"}>
                    {trackingModalSubject.device_id !== null ? "Tracked" : "Untracked"}
                  </Badge>
                  <Badge variant="danger">{trackingModalSubject.activity_summary?.suspicious_events ?? 0} segnali</Badge>
                </div>
                {macLabel ? <p className="mt-3 break-all font-mono text-sm text-gray-600">MAC: {macLabel}</p> : null}
                    </>
                  );
                })()}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Link href={NETWORK_TRACKING_WIKI_HREF} className="rounded-full border border-[#D9E8DE] bg-[#F7FAF7] px-4 py-2 text-sm font-medium text-[#1D4E35]">
                  Apri assistente Wiki
                </Link>
                <button type="button" className="rounded-full border border-[#D9E8DE] bg-white px-4 py-2 text-sm font-medium text-gray-700" onClick={() => setTrackingModalSubject(null)}>
                  Chiudi
                </button>
              </div>
            </div>

            <div className="max-h-[calc(90vh-110px)] overflow-y-auto px-6 py-5">
              <div className="grid gap-4 md:grid-cols-4">
                <div className="rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] px-4 py-4">
                  <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">VPN</p>
                  <p className="mt-2 text-xl font-semibold text-gray-950">{trackingModalSubject.activity_summary?.vpn_suspected_events ?? 0}</p>
                </div>
                <div className="rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] px-4 py-4">
                  <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Proxy</p>
                  <p className="mt-2 text-xl font-semibold text-gray-950">{trackingModalSubject.activity_summary?.proxy_suspected_events ?? 0}</p>
                </div>
                <div className="rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] px-4 py-4">
                  <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Tor</p>
                  <p className="mt-2 text-xl font-semibold text-gray-950">{trackingModalSubject.activity_summary?.tor_suspected_events ?? 0}</p>
                </div>
                <div className="rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] px-4 py-4">
                  <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Encrypted DNS</p>
                  <p className="mt-2 text-xl font-semibold text-gray-950">{trackingModalSubject.activity_summary?.encrypted_dns_events ?? 0}</p>
                </div>
              </div>

              <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.3fr)_360px]">
                <section className="space-y-4">
                  <div className="rounded-[24px] border border-[#E6F0EA] bg-[#FBFCFB] p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">Eventi recenti</p>
                    <div className="mt-3 space-y-3">
                      {(trackingModalSubject.activity_summary?.recent_events ?? []).length === 0 ? (
                        <EmptyState icon={ShieldIcon} title="Nessun evento recente" description="Non ci sono eventi recenti disponibili per questo soggetto." />
                      ) : (
                        (trackingModalSubject.activity_summary?.recent_events ?? []).map((event) => {
                          const parts = formatEventTypeParts(event.event_type);
                          const destination = describeDestination(event);
                          return (
                          <div key={event.id} className="rounded-2xl border border-[#E6F0EA] bg-white px-4 py-3">
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <div className="flex flex-wrap gap-2">
                                  <Badge variant="neutral">{parts.context}</Badge>
                                  {parts.channel ? <Badge variant="neutral">{parts.channel}</Badge> : null}
                                  {parts.action ? <Badge variant="info">{parts.action}</Badge> : null}
                                </div>
                                <p className="mt-2 text-sm font-medium text-gray-950">{formatEventLabel(event.event_type)}</p>
                                <p className="mt-1 text-xs text-gray-500">{new Date(event.observed_at).toLocaleString("it-IT")}</p>
                              </div>
                              <Badge variant={event.detection_tags.some((tag) => tag === "vpn_suspected" || tag === "proxy_suspected" || tag === "tor_suspected") ? "danger" : "warning"}>
                                {event.protocol || "Evento"}
                              </Badge>
                            </div>
                            <div className="mt-3 flex flex-wrap gap-2">
                              {event.detection_tags.map((tag) => (
                                <Badge key={`${event.id}-${tag}`} variant={tagTone(tag)}>{tagLabel(tag)}</Badge>
                              ))}
                            </div>
                            <div className="mt-3 grid gap-3 md:grid-cols-2">
                              <div className="rounded-xl border border-[#EEF3EF] bg-[#FAFCFA] px-3 py-2">
                                <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Sorgente</p>
                                <p className="mt-1 text-sm text-gray-950">{event.src_device_label || event.src_ip || "n/d"}</p>
                              </div>
                              <div className="rounded-xl border border-[#EEF3EF] bg-[#FAFCFA] px-3 py-2">
                                <p className="text-[11px] uppercase tracking-[0.14em] text-gray-400">Destinazione</p>
                                <p className="mt-1 text-sm font-medium text-gray-950">{destination.title}</p>
                                <p className="mt-1 text-xs text-gray-500">{destination.subtitle}</p>
                              </div>
                            </div>
                          </div>
                        )})
                      )}
                    </div>
                  </div>
                </section>

                <aside className="space-y-4">
                  <div className="rounded-[24px] border border-[#E6F0EA] bg-[#FBFCFB] p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">Tags principali</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {(trackingModalSubject.activity_summary?.top_detection_tags ?? []).length === 0 ? (
                        <p className="text-sm text-gray-500">Nessun tag disponibile.</p>
                      ) : (
                        (trackingModalSubject.activity_summary?.top_detection_tags ?? []).map((tag) => (
                          <Badge key={`top-${trackingModalSubject.id}-${tag}`} variant={tagTone(tag)}>{tagLabel(tag)}</Badge>
                        ))
                      )}
                    </div>
                  </div>
                  <div className="rounded-[24px] border border-[#E6F0EA] bg-[#FBFCFB] p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">Storico rete</p>
                    <div className="mt-3 space-y-2">
                      {trackingModalSubject.scan_history.length === 0 ? (
                        <p className="text-sm text-gray-500">Nessuno snapshot rete disponibile.</p>
                      ) : (
                        trackingModalSubject.scan_history.map((item) => (
                          <div key={`${trackingModalSubject.id}-${item.scan_id}-${item.observed_at}`} className="rounded-xl border border-[#EEF3EF] bg-white px-3 py-2">
                            <p className="text-sm font-medium text-gray-950">{formatIpWithMacHistory(item.ip_address, trackingModalSubject.scan_history)}</p>
                            <p className="mt-1 text-xs text-gray-500">{new Date(item.observed_at).toLocaleString("it-IT")} · {item.status}</p>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </aside>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function NetworkVpnBypassPage() {
  return (
    <NetworkModulePage
      title="VPN / Proxy Bypass"
      description="Console dedicata ai segnali di aggiramento dei blocchi osservati dal firewall."
      breadcrumb="VPN / Proxy Bypass"
    >
      {({ token }) => <VpnBypassContent token={token} />}
    </NetworkModulePage>
  );
}
