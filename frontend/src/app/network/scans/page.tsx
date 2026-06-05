"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { Badge } from "@/components/ui/badge";
import { getNetworkScans, triggerNetworkScan } from "@/lib/api";
import type { NetworkScan } from "@/types/api";

function getScanTypeLabel(scanType: string) {
  if (scanType === "arp") {
    return "Discovery ARP";
  }
  return "Scansione completa";
}

function getScanTypeBadge(scanType: string) {
  if (scanType === "arp") {
    return <Badge variant="warning">ARP</Badge>;
  }
  return <Badge variant="info">Completa</Badge>;
}

function ScanMetricCard({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: number | string;
  tone?: "default" | "success" | "warning";
}) {
  const toneClass =
    tone === "success"
      ? "border-emerald-100 bg-emerald-50/70"
      : tone === "warning"
        ? "border-amber-100 bg-amber-50/70"
        : "border-gray-100 bg-gray-50/80";

  return (
    <div className={`rounded-2xl border px-4 py-3 ${toneClass}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function ScansContent({ token }: { token: string }) {
  const [scans, setScans] = useState<NetworkScan[]>([]);
  const [isTriggeringScan, setIsTriggeringScan] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadScans = useCallback(async () => {
    try {
      const response = await getNetworkScans(token);
      setScans(response);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento scansioni");
    }
  }, [token]);

  useEffect(() => {
    void loadScans();
  }, [loadScans]);

  async function handleTriggerScan(scanType: "incremental" | "arp") {
    setIsTriggeringScan(true);
    try {
      await triggerNetworkScan(token, { scan_type: scanType });
      await loadScans();
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore durante l’avvio della scansione");
    } finally {
      setIsTriggeringScan(false);
    }
  }

  return (
    <div className="page-stack">
      <article className="panel-card overflow-hidden">
        <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr] xl:items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Rilevamento rete</p>
            <h2 className="mt-2 text-2xl font-semibold text-gray-900">Storico snapshot e discovery operativa</h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-gray-600">
              Usa la scansione completa per aggiornare host, porte ed enrichment. Usa la discovery ARP per far emergere piu rapidamente i device presenti sul segmento locale ma ancora non classificati.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <button className="btn-secondary h-full justify-center py-3" onClick={() => void handleTriggerScan("arp")} type="button" disabled={isTriggeringScan}>
              {isTriggeringScan ? "Discovery in corso" : "Discovery ARP"}
            </button>
            <button className="btn-primary h-full justify-center py-3" onClick={() => void handleTriggerScan("incremental")} type="button" disabled={isTriggeringScan}>
              {isTriggeringScan ? "Scansione in corso" : "Scansione completa"}
            </button>
          </div>
        </div>
      </article>

      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Storico non disponibile</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      {scans.map((scan) => (
        <article key={scan.id} className="panel-card overflow-hidden">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                {getScanTypeBadge(scan.scan_type)}
                <NetworkStatusBadge status={scan.status} />
              </div>
              <div>
                <p className="text-lg font-semibold text-gray-900">Snapshot #{scan.id}</p>
                <p className="mt-1 text-sm text-gray-500">
                  {getScanTypeLabel(scan.scan_type)} · Range {scan.network_range}
                </p>
              </div>
            </div>
            <div className="rounded-2xl border border-gray-100 bg-gray-50/80 px-4 py-3 text-right">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-500">Avviato da</p>
              <p className="mt-2 text-sm font-medium text-gray-900">{scan.initiated_by || "scheduler"}</p>
              <p className="mt-1 text-xs text-gray-500">{new Date(scan.started_at).toLocaleString("it-IT")}</p>
            </div>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-3 xl:grid-cols-6">
            <ScanMetricCard label="Host scanditi" value={scan.hosts_scanned} />
            <ScanMetricCard label="Host attivi" value={scan.active_hosts} tone="success" />
            <ScanMetricCard label="Aggiornati" value={scan.discovered_devices} />
            <ScanMetricCard label="Nuovi" value={scan.delta.new_devices_count} tone={scan.delta.new_devices_count > 0 ? "warning" : "default"} />
            <ScanMetricCard label="Scomparsi" value={scan.delta.missing_devices_count} tone={scan.delta.missing_devices_count > 0 ? "warning" : "default"} />
            <ScanMetricCard label="Modificati" value={scan.delta.changed_devices_count} tone={scan.delta.changed_devices_count > 0 ? "warning" : "default"} />
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 pt-4">
            <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
              <span className="rounded-full bg-gray-100 px-3 py-1">Snapshot coerente dello stato rete</span>
              <span className="rounded-full bg-gray-100 px-3 py-1">Delta calcolato rispetto alla scansione precedente</span>
            </div>
            <Link href={`/network/scans/${scan.id}`} className="inline-flex items-center rounded-full bg-[#1D4E35] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#163b29]">
              Apri dettaglio
            </Link>
          </div>
        </article>
      ))}

      {scans.length === 0 && !loadError ? (
        <article className="panel-card text-sm text-gray-500">Nessuna scansione disponibile.</article>
      ) : null}
    </div>
  );
}

export default function NetworkScansPage() {
  return (
    <NetworkModulePage
      title="Scansioni"
      description="Storico degli snapshot di rete eseguiti manualmente o da scheduler."
      breadcrumb="Storico"
    >
      {({ token }) => <ScansContent token={token} />}
    </NetworkModulePage>
  );
}
