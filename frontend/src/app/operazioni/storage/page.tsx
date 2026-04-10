"use client";

import { useCallback, useEffect, useState } from "react";

import {
  OperazioniCollectionHero,
  OperazioniCollectionPanel,
  OperazioniHeroNotice,
  OperazioniMetricStrip,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import { ServerIcon } from "@/components/ui/icons";
import { getStorageAlerts, getStorageLatestMetric, recalculateStorage } from "@/features/operazioni/api/client";

type StorageMetric = {
  measured_at: string;
  total_bytes_used: number;
  quota_bytes: number;
  percentage_used: number;
  active_alerts: { level: string; threshold: number }[];
};

type StorageAlert = {
  id: string;
  level: string;
  threshold: number;
  triggered_at: string;
};

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** index;
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function StorageContent() {
  const [metric, setMetric] = useState<StorageMetric | null>(null);
  const [alerts, setAlerts] = useState<StorageAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [metricData, alertsData] = await Promise.all([getStorageLatestMetric(), getStorageAlerts()]);
      setMetric(metricData as StorageMetric);
      setAlerts(Array.isArray(alertsData) ? (alertsData as StorageAlert[]) : []);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento storage");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  async function handleRecalculate() {
    try {
      setIsRefreshing(true);
      await recalculateStorage();
      await loadData();
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel ricalcolo storage");
    } finally {
      setIsRefreshing(false);
    }
  }

  const percentageUsed = metric?.percentage_used ?? 0;

  return (
    <div className="page-stack">
      <OperazioniCollectionHero
        eyebrow="Attachment quota"
        icon={<ServerIcon className="h-3.5 w-3.5" />}
        title="Monitoraggio storage allegati, soglie attive e spazio residuo del modulo."
        description="La pagina espone l'ultimo campionamento disponibile e consente di forzare un nuovo ricalcolo della quota senza uscire dal modulo."
      >
        {loadError ? (
          <OperazioniHeroNotice title="Caricamento non riuscito" description={loadError} tone="danger" />
        ) : (
          <OperazioniHeroNotice
            title="Ultimo campionamento"
            description={
              metric?.measured_at
                ? `Rilevato il ${new Date(metric.measured_at).toLocaleString("it-IT")}.`
                : "Nessun campionamento disponibile, verra generato al primo accesso."
            }
          />
        )}
        <div className="rounded-2xl border border-white/80 bg-white/75 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Azione rapida</p>
          <button type="button" className="btn-secondary mt-3" onClick={() => void handleRecalculate()} disabled={isRefreshing}>
            {isRefreshing ? "Ricalcolo in corso..." : "Ricalcola quota"}
          </button>
        </div>
      </OperazioniCollectionHero>

      <OperazioniMetricStrip>
        <MetricCard label="Spazio utilizzato" value={formatBytes(metric?.total_bytes_used ?? 0)} sub="Occupazione attuale allegati" />
        <MetricCard label="Quota totale" value={formatBytes(metric?.quota_bytes ?? 0)} sub="Capienza configurata" />
        <MetricCard label="Percentuale" value={`${percentageUsed.toFixed(1)}%`} sub="Quota consumata" variant={percentageUsed >= 95 ? "danger" : percentageUsed >= 70 ? "warning" : "success"} />
        <MetricCard label="Alert attivi" value={alerts.length} sub="Soglie attualmente superate" variant={alerts.length > 0 ? "warning" : "default"} />
      </OperazioniMetricStrip>

      <OperazioniCollectionPanel
        title="Stato storage"
        description="Dettagli dell'ultimo rilievo quota e segnalazione delle soglie già oltrepassate."
        count={alerts.length}
      >
        {isLoading ? (
          <p className="text-sm text-gray-500">Caricamento storage in corso.</p>
        ) : (
          <div className="grid gap-4 lg:grid-cols-[1.15fr,0.85fr]">
            <div className="rounded-2xl border border-[#e6ebe5] bg-[#fbfcfa] p-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#667267]">Occupazione</p>
              <div className="mt-4 h-3 overflow-hidden rounded-full bg-[#e8ede8]">
                <div
                  className={`h-full rounded-full ${percentageUsed >= 95 ? "bg-rose-500" : percentageUsed >= 70 ? "bg-amber-500" : "bg-emerald-500"}`}
                  style={{ width: `${Math.min(percentageUsed, 100)}%` }}
                />
              </div>
              <p className="mt-3 text-sm text-gray-600">
                {formatBytes(metric?.total_bytes_used ?? 0)} usati su {formatBytes(metric?.quota_bytes ?? 0)}.
              </p>
            </div>
            <div className="rounded-2xl border border-[#e6ebe5] bg-[#fbfcfa] p-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#667267]">Alert live</p>
              <p className="mt-3 text-sm text-gray-600">
                {alerts.length > 0 ? `${alerts.length} soglie attive richiedono presidio.` : "Nessuna soglia attiva al momento."}
              </p>
            </div>
          </div>
        )}
      </OperazioniCollectionPanel>

      <OperazioniCollectionPanel
        title="Soglie alert"
        description="Soglie operative del modulo e stato corrente in base ai dati rilevati."
        count={3}
      >
        <div className="space-y-3">
          {[
            { level: "70%", label: "Warning", tone: "bg-amber-50 text-amber-700" },
            { level: "85%", label: "Warning alto", tone: "bg-orange-50 text-orange-700" },
            { level: "95%", label: "Critico", tone: "bg-rose-50 text-rose-700" },
          ].map((threshold) => (
            <div key={threshold.level} className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3">
              <div className="flex items-center gap-3">
                <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${threshold.tone}`}>{threshold.level}</span>
                <span className="text-sm font-medium text-gray-900">{threshold.label}</span>
              </div>
              <span className="text-sm text-gray-500">
                {alerts.some((alert) => `${alert.threshold}%` === threshold.level) ? "Superata" : "Non superata"}
              </span>
            </div>
          ))}
        </div>
      </OperazioniCollectionPanel>
    </div>
  );
}

export default function StoragePage() {
  return (
    <OperazioniModulePage
      title="Storage allegati"
      description="Quota storage allegati e alert sulle soglie."
      breadcrumb="Monitoraggio"
    >
      {() => <StorageContent />}
    </OperazioniModulePage>
  );
}
