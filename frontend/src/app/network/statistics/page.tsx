"use client";

import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { FilterPillGroup } from "@/components/network/filter-pill-group";
import { NetworkModulePage } from "@/components/network/network-module-page";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, CalendarIcon, GridIcon, ServerIcon } from "@/components/ui/icons";
import { getNetworkStatistics } from "@/lib/api";
import type {
  NetworkStatisticsCountItem,
  NetworkStatisticsSummary,
  NetworkStatisticsTimelinePoint,
  NetworkStatisticsTrafficItem,
} from "@/types/api";

const WINDOW_OPTIONS = [24, 72, 168];

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

function formatIpWithLabel(ipAddress: string | null, label: string) {
  if (!ipAddress) {
    return null;
  }
  if (label && label !== ipAddress) {
    return `${ipAddress} · ${label}`;
  }
  return ipAddress;
}

function CountList({ title, items }: { title: string; items: NetworkStatisticsCountItem[] }) {
  const maxCount = Math.max(...items.map((item) => item.count), 1);

  return (
    <article className="panel-card">
      <p className="section-title">{title}</p>
      <div className="mt-4 space-y-3">
        {items.length === 0 ? (
          <p className="text-sm text-gray-500">Nessun dato disponibile nel perimetro selezionato.</p>
        ) : (
          items.map((item) => (
            <div key={item.key}>
              <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                <span className="truncate font-medium text-gray-800">{item.label}</span>
                <span className="text-gray-500">{item.count}</span>
              </div>
              <div className="h-2 rounded-full bg-gray-100">
                <div className="h-2 rounded-full bg-[#8CB39D]" style={{ width: `${Math.max((item.count / maxCount) * 100, 8)}%` }} />
              </div>
            </div>
          ))
        )}
      </div>
    </article>
  );
}

function TrafficList({ title, items }: { title: string; items: NetworkStatisticsTrafficItem[] }) {
  return (
    <article className="panel-card">
      <p className="section-title">{title}</p>
      <div className="mt-4 space-y-3">
        {items.length === 0 ? (
          <p className="text-sm text-gray-500">Nessun traffico osservato nel periodo selezionato.</p>
        ) : (
          items.map((item) => (
            <div key={`${title}-${item.label}-${item.ip_address || "na"}`} className="rounded-xl border border-gray-100 px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-900">{item.label}</p>
                  {item.ip_address ? <p className="mt-1 text-xs text-gray-500">{formatIpWithLabel(item.ip_address, item.label)}</p> : null}
                </div>
                <Badge variant="info">{item.events_count} eventi</Badge>
              </div>
              <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
                <span>In {formatBytes(item.bytes_in)}</span>
                <span>Out {formatBytes(item.bytes_out)}</span>
                <span>Tot {formatBytes(item.bytes_total)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </article>
  );
}

function TimelineCard({ items }: { items: NetworkStatisticsTimelinePoint[] }) {
  const maxCount = Math.max(...items.map((item) => item.events_count), 1);

  return (
    <article className="panel-card">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="section-title">Timeline traffico</p>
          <p className="section-copy">Distribuzione per finestra oraria degli eventi Sophos aggregati.</p>
        </div>
        <Badge variant="neutral">{items.length} bucket</Badge>
      </div>
      <div className="mt-5 space-y-3">
        {items.length === 0 ? (
          <EmptyState icon={CalendarIcon} title="Nessuna timeline disponibile" description="Mancano eventi Sophos nel periodo selezionato." />
        ) : (
          items.map((item) => (
            <div key={item.bucket}>
              <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                <span className="font-medium text-gray-800">{item.bucket}</span>
                <span className="text-gray-500">{item.events_count} eventi</span>
              </div>
              <div className="h-2 rounded-full bg-gray-100">
                <div className="h-2 rounded-full bg-[#1D4E35]" style={{ width: `${Math.max((item.events_count / maxCount) * 100, 6)}%` }} />
              </div>
              <div className="mt-1 flex flex-wrap gap-3 text-xs text-gray-500">
                <span>In {formatBytes(item.bytes_in)}</span>
                <span>Out {formatBytes(item.bytes_out)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </article>
  );
}

function StatisticsContent({ token }: { token: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [windowHours, setWindowHours] = useState<number>(() => {
    const raw = Number(searchParams.get("window") || 24);
    return WINDOW_OPTIONS.includes(raw) ? raw : 24;
  });
  const [stats, setStats] = useState<NetworkStatisticsSummary | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      setIsLoading(true);
      try {
        const response = await getNetworkStatistics(token, { windowHours });
        setStats(response);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento statistiche rete");
      } finally {
        setIsLoading(false);
      }
    }

    void loadStats();
  }, [token, windowHours]);

  useEffect(() => {
    const params = new URLSearchParams(searchParams.toString());
    if (windowHours !== 24) {
      params.set("window", String(windowHours));
    } else {
      params.delete("window");
    }
    const nextQuery = params.toString();
    router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, { scroll: false });
  }, [pathname, router, searchParams, windowHours]);

  const overviewNotice = useMemo(() => {
    if (!stats) {
      return "Nessun dato caricato.";
    }
    return `${stats.total_events} eventi Sophos, ${stats.unique_domains} domini e ${stats.unique_external_peers} peer esterni nella finestra selezionata.`;
  }, [stats]);

  return (
    <div className="page-stack">
      <ModuleWorkspaceHero
        badge={
          <>
            <GridIcon className="h-3.5 w-3.5" />
            Analytics Rete
          </>
        }
        title="Statistiche operative su rete, dispositivi e navigazione."
        description="Vista aggregata per operatore: stato dell'infrastruttura, assegnazioni device, navigazione osservata dal firewall Sophos e distribuzione del traffico."
        actions={
          <>
            <ModuleWorkspaceNoticeCard
              title="Finestra osservazione"
              description={`Perimetro corrente: ultime ${windowHours} ore.`}
              tone="info"
            />
            <ModuleWorkspaceNoticeCard
              title="Sintesi traffico"
              description={overviewNotice}
              tone={stats && stats.blocked_events > 0 ? "warning" : "success"}
            />
          </>
        }
      >
        <ModuleWorkspaceKpiRow>
          <ModuleWorkspaceKpiTile label="Dispositivi attivi" value={stats?.active_devices ?? "—"} hint="in esercizio" variant="emerald" />
          <ModuleWorkspaceKpiTile label="Online" value={stats?.online_devices ?? "—"} hint="raggiungibili" variant="emerald" />
          <ModuleWorkspaceKpiTile label="Senza utente" value={stats?.unassigned_devices ?? "—"} hint="da assegnare" variant={(stats?.unassigned_devices ?? 0) > 0 ? "amber" : "default"} />
          <ModuleWorkspaceKpiTile label="Eventi Sophos" value={stats?.total_events ?? "—"} hint={`ultime ${windowHours}h`} variant="default" />
          <ModuleWorkspaceKpiTile label="Blocchi" value={stats?.blocked_events ?? "—"} hint="deny / block / drop" variant={(stats?.blocked_events ?? 0) > 0 ? "amber" : "default"} />
        </ModuleWorkspaceKpiRow>
      </ModuleWorkspaceHero>

      <article className="panel-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="section-title">Contesto analisi</p>
            <p className="section-copy">Scegli l'orizzonte temporale per ricalcolare navigazione, top device e timeline traffico.</p>
          </div>
          <select className="form-control min-w-[220px]" value={windowHours} onChange={(event) => setWindowHours(Number(event.target.value))}>
            {WINDOW_OPTIONS.map((value) => (
              <option key={value} value={value}>
                Ultime {value} ore
              </option>
            ))}
          </select>
        </div>
        <div className="mt-4">
          <FilterPillGroup
            options={WINDOW_OPTIONS.map((value) => ({ value: String(value), label: `Ultime ${value}h` }))}
            value={String(windowHours)}
            onChange={(value) => setWindowHours(Number(value))}
          />
        </div>
        {loadError ? <p className="mt-4 text-sm text-red-600">{loadError}</p> : null}
      </article>

      {isLoading ? (
        <article className="panel-card text-sm text-gray-500">Caricamento statistiche rete.</article>
      ) : !stats ? (
        <article className="panel-card">
          <EmptyState icon={AlertTriangleIcon} title="Statistiche non disponibili" description="Non sono riuscito a costruire il riepilogo della rete." />
        </article>
      ) : (
        <>
          <section className="grid gap-6 xl:grid-cols-4">
            <article className="panel-card xl:col-span-2">
              <p className="section-title">Stato rete e anagrafica dispositivi</p>
              <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                <MetricCard label="Totale dispositivi" value={stats.total_devices} sub="storico in anagrafica" />
                <MetricCard label="Rotamati" value={stats.retired_devices} sub="fuori monitoraggio" />
                <MetricCard label="Monitorati" value={stats.monitored_devices} sub="poll attivo" />
                <MetricCard label="Conosciuti" value={stats.known_devices} sub="classificati" />
                <MetricCard label="Sconosciuti" value={stats.unknown_devices} sub="da verificare" />
                <MetricCard label="Profili placeholder" value={stats.placeholder_profiles} sub="utente creato automaticamente" />
                <MetricCard label="Con utente" value={stats.assigned_devices} sub="mappati a application_users" />
                <MetricCard label="Con traffico" value={stats.devices_with_traffic} sub={`ultime ${stats.window_hours}h`} />
                <MetricCard label="Alert aperti" value={stats.open_alerts} sub="anomalie correnti" />
              </div>
            </article>

            <article className="panel-card xl:col-span-2">
              <p className="section-title">Navigazione e traffico</p>
              <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                <MetricCard label="Traffico in ingresso" value={formatBytes(stats.bytes_in)} sub="dati ricevuti" />
                <MetricCard label="Traffico in uscita" value={formatBytes(stats.bytes_out)} sub="dati inviati" />
                <MetricCard label="Domini osservati" value={stats.unique_domains} sub="host applicativi unici" />
                <MetricCard label="Peer esterni" value={stats.unique_external_peers} sub="IP pubblici unici" />
                <MetricCard label="Eventi allowed" value={stats.allowed_events} sub="navigazione consentita" />
                <MetricCard label="Firewall censiti" value={stats.firewall_count} sub="sorgenti telemetriche" />
              </div>
            </article>
          </section>

          <section className="grid gap-6 xl:grid-cols-4">
            <CountList title="Top tipi dispositivo" items={stats.top_device_types} />
            <CountList title="Top vendor" items={stats.top_vendors} />
            <CountList title="Top uffici / sedi" items={stats.top_offices} />
            <CountList title="Top assegnatari" items={stats.top_assignees} />
          </section>

          <section className="grid gap-6 xl:grid-cols-4">
            <CountList title="Severità eventi" items={stats.severity_breakdown} />
            <CountList title="Protocolli" items={stats.protocol_breakdown} />
            <CountList title="Top eventi Sophos" items={stats.top_event_types} />
            <CountList title="Top regole firewall" items={stats.top_firewall_rules} />
          </section>

          <section className="grid gap-6 xl:grid-cols-3">
            <TrafficList title="Top domini navigati" items={stats.top_domains} />
            <TrafficList title="Top destinazioni esterne" items={stats.top_destinations} />
            <TrafficList title="Top sorgenti interne" items={stats.top_source_devices} />
          </section>

          <TimelineCard items={stats.hourly_timeline} />
        </>
      )}
    </div>
  );
}

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub: string }) {
  return (
    <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
      <p className="label-caption">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
      <p className="mt-1 text-xs text-gray-500">{sub}</p>
    </div>
  );
}

export default function NetworkStatisticsPage() {
  return (
    <NetworkModulePage
      title="Statistiche"
      description="Analisi aggregata di rete, dispositivi e navigazione osservata dal firewall."
      breadcrumb="Statistiche"
    >
      {({ token }) => <StatisticsContent token={token} />}
    </NetworkModulePage>
  );
}
