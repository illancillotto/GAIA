"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon } from "@/components/ui/icons";
import { getNetworkAlerts, updateNetworkAlert } from "@/lib/api";
import type { NetworkAlert } from "@/types/api";

type AlertBucketProps = {
  alerts: NetworkAlert[];
  emptyTitle: string;
  emptyDescription: string;
  pendingAlertId: number | null;
  onAlertUpdate: (alertId: number, status: "resolved" | "ignored") => void;
};

function AlertCardList({ alerts, emptyTitle, emptyDescription, pendingAlertId, onAlertUpdate }: AlertBucketProps) {
  if (alerts.length === 0) {
    return (
      <EmptyState
        icon={AlertTriangleIcon}
        title={emptyTitle}
        description={emptyDescription}
      />
    );
  }

  return (
    <div className="space-y-4">
      {alerts.map((alert) => (
        <article key={alert.id} className="panel-card">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-gray-900">{alert.title}</p>
              <p className="mt-1 text-sm text-gray-500">{alert.message || "Nessun dettaglio ulteriore."}</p>
            </div>
            <div className="flex items-center gap-2">
              <NetworkStatusBadge status={alert.severity} />
              <NetworkStatusBadge status={alert.status} />
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-gray-400">
            <span>Tipo: {alert.alert_type}</span>
            <span>Creato: {new Date(alert.created_at).toLocaleString("it-IT")}</span>
            {alert.status === "open" ? (
              <>
                <button
                  type="button"
                  className="font-medium text-[#1D4E35]"
                  disabled={pendingAlertId === alert.id}
                  onClick={() => onAlertUpdate(alert.id, "resolved")}
                >
                  Segna risolto
                </button>
                <button
                  type="button"
                  className="font-medium text-gray-500"
                  disabled={pendingAlertId === alert.id}
                  onClick={() => onAlertUpdate(alert.id, "ignored")}
                >
                  Ignora
                </button>
              </>
            ) : null}
            {alert.scan_id ? (
              <Link href={`/network/scans/${alert.scan_id}`} className="font-medium text-[#1D4E35]">
                Snapshot #{alert.scan_id}
              </Link>
            ) : null}
          </div>
        </article>
      ))}
    </div>
  );
}

function AlertsContent({ token }: { token: string }) {
  const [alerts, setAlerts] = useState<NetworkAlert[]>([]);
  const [severityFilter, setSeverityFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pendingAlertId, setPendingAlertId] = useState<number | null>(null);

  useEffect(() => {
    async function loadAlerts() {
      try {
        const response = await getNetworkAlerts(token);
        setAlerts(response);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento alert");
      }
    }

    void loadAlerts();
  }, [token]);

  async function handleAlertUpdate(alertId: number, status: "resolved" | "ignored") {
    setPendingAlertId(alertId);
    try {
      const updated = await updateNetworkAlert(token, alertId, { status });
      setAlerts((items) => items.map((item) => (item.id === alertId ? updated : item)));
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore aggiornamento alert");
    } finally {
      setPendingAlertId(null);
    }
  }

  const availableAlertTypes = useMemo(
    () => Array.from(new Set(alerts.map((alert) => alert.alert_type))).sort((left, right) => left.localeCompare(right, "it")),
    [alerts],
  );
  const normalizedSearch = search.trim().toLowerCase();
  const filteredAlerts = alerts.filter((alert) => {
    if (severityFilter && alert.severity !== severityFilter) {
      return false;
    }
    if (typeFilter && alert.alert_type !== typeFilter) {
      return false;
    }
    if (!normalizedSearch) {
      return true;
    }
    const haystack = [alert.title, alert.message, alert.alert_type, alert.severity]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(normalizedSearch);
  });

  const activeAlerts = filteredAlerts.filter((alert) => alert.status === "open");
  const archivedAlerts = filteredAlerts.filter((alert) => alert.status === "resolved");

  return (
    <div className="page-stack">
      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Alert non disponibili</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Filtri alert</p>
          <p className="section-copy">Filtra gli eventi per tipo, severità o testo e separa ciò che richiede azione da ciò che è già stato chiuso.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[minmax(0,1.3fr)_220px_260px]">
          <input
            className="form-control"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Cerca per titolo, messaggio o tipo alert"
          />
          <select className="form-control" value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
            <option value="">Tutte le severità</option>
            <option value="warning">Warning</option>
            <option value="danger">Danger</option>
            <option value="info">Info</option>
          </select>
          <select className="form-control" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
            <option value="">Tutti i tipi</option>
            {availableAlertTypes.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
      </article>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="space-y-4">
          <article className="panel-card">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="section-title">Alert in corso</p>
                <p className="section-copy">Eventi aperti che richiedono una decisione operativa.</p>
              </div>
              <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-medium text-red-600">
                {activeAlerts.length}
              </span>
            </div>
          </article>
          <AlertCardList
            alerts={activeAlerts}
            emptyTitle="Nessun alert in corso"
            emptyDescription="Non ci sono eventi aperti con i filtri correnti."
            pendingAlertId={pendingAlertId}
            onAlertUpdate={(alertId, status) => void handleAlertUpdate(alertId, status)}
          />
        </section>

        <section className="space-y-4">
          <article className="panel-card">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="section-title">Archiviati</p>
                <p className="section-copy">Alert risolti e chiusi, mantenuti come storico operativo.</p>
              </div>
              <span className="rounded-full bg-green-50 px-2.5 py-1 text-xs font-medium text-green-700">
                {archivedAlerts.length}
              </span>
            </div>
          </article>
          <AlertCardList
            alerts={archivedAlerts}
            emptyTitle="Nessun alert archiviato"
            emptyDescription="Non ci sono alert risolti con i filtri correnti."
            pendingAlertId={pendingAlertId}
            onAlertUpdate={(alertId, status) => void handleAlertUpdate(alertId, status)}
          />
        </section>
      </div>
    </div>
  );
}

export default function NetworkAlertsPage() {
  return (
    <NetworkModulePage
      title="Alert"
      description="Elenco degli eventi generati per dispositivi sconosciuti o conosciuti ma assenti a lungo dalla rete."
      breadcrumb="Alert"
    >
      {({ token }) => <AlertsContent token={token} />}
    </NetworkModulePage>
  );
}
