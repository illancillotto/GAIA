"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { NetworkModulePage } from "@/components/network/network-module-page";
import { NetworkStatusBadge } from "@/components/network/network-status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon } from "@/components/ui/icons";
import { getNetworkAlerts, listNetworkDeviceAssignees, updateNetworkAlert } from "@/lib/api";
import type { NetworkAlert, NetworkAssignedUserSummary } from "@/types/api";

type AlertVerificationStatus =
  | "pending"
  | "investigating"
  | "confirmed"
  | "false_positive"
  | "tolerated";

type AlertBucketProps = {
  alerts: NetworkAlert[];
  emptyTitle: string;
  emptyDescription: string;
  pendingAlertId: number | null;
  assignees: NetworkAssignedUserSummary[];
  draftAssignments: Record<number, string>;
  draftVerificationStatuses: Record<number, AlertVerificationStatus>;
  draftNotes: Record<number, string>;
  onAlertUpdate: (alertId: number, payload: { status?: "resolved" | "ignored"; assigned_to_user_id?: number | null; verification_status?: AlertVerificationStatus; verification_notes?: string | null }) => void;
  onDraftAssignmentChange: (alertId: number, value: string) => void;
  onDraftVerificationStatusChange: (alertId: number, value: AlertVerificationStatus) => void;
  onDraftNotesChange: (alertId: number, value: string) => void;
};

function AlertCardList({
  alerts,
  emptyTitle,
  emptyDescription,
  pendingAlertId,
  assignees,
  draftAssignments,
  draftVerificationStatuses,
  draftNotes,
  onAlertUpdate,
  onDraftAssignmentChange,
  onDraftVerificationStatusChange,
  onDraftNotesChange,
}: AlertBucketProps) {
  const isBypassCaseAlert = (alert: NetworkAlert) =>
    alert.alert_type === "VPN_BYPASS_SUSPECTED"
    || alert.alert_type === "VPN_BYPASS_TRANSIENT_DEVICE"
    || alert.alert_type === "ARP_EPHEMERAL_DEVICE"
    || alert.alert_type === "ARP_MAC_CHANGE_SUSPECTED"
    || alert.alert_type === "ARP_IP_ROTATION_SUSPECTED";

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
            {alert.assigned_to_full_name || alert.assigned_to_username ? <span>Owner: {alert.assigned_to_full_name || alert.assigned_to_username}</span> : null}
            <span>Verifica: {alert.verification_status}</span>
            {alert.status === "open" ? (
              <>
                <button
                  type="button"
                  className="font-medium text-[#1D4E35]"
                  disabled={pendingAlertId === alert.id}
                  onClick={() => onAlertUpdate(alert.id, { status: "resolved" })}
                >
                  Segna risolto
                </button>
                <button
                  type="button"
                  className="font-medium text-gray-500"
                  disabled={pendingAlertId === alert.id}
                  onClick={() => onAlertUpdate(alert.id, { status: "ignored" })}
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
          {isBypassCaseAlert(alert) ? (
            <div className="mt-4 grid gap-3 rounded-2xl border border-[#E6F0EA] bg-[#FAFCFA] p-4 md:grid-cols-2">
              <label className="text-sm text-gray-700">
                Assegnatario
                <select className="form-control mt-1" value={draftAssignments[alert.id] ?? String(alert.assigned_to_user_id ?? "")} onChange={(event) => onDraftAssignmentChange(alert.id, event.target.value)}>
                  <option value="">Non assegnato</option>
                  {assignees.map((assignee) => (
                    <option key={assignee.id} value={String(assignee.id)}>
                      {assignee.full_name || assignee.username}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm text-gray-700">
                Classificazione
                <select
                  className="form-control mt-1"
                  value={draftVerificationStatuses[alert.id] ?? alert.verification_status}
                  onChange={(event) => onDraftVerificationStatusChange(alert.id, event.target.value as AlertVerificationStatus)}
                >
                  <option value="pending">pending</option>
                  <option value="investigating">investigating</option>
                  <option value="confirmed">confirmed</option>
                  <option value="false_positive">false_positive</option>
                  <option value="tolerated">tolerated</option>
                </select>
              </label>
              <label className="md:col-span-2 text-sm text-gray-700">
                Note verifica
                <textarea
                  className="form-control mt-1 min-h-[88px]"
                  value={draftNotes[alert.id] ?? alert.verification_notes ?? ""}
                  onChange={(event) => onDraftNotesChange(alert.id, event.target.value)}
                  placeholder="Esito verifica, motivo del falso positivo o decisione di tolleranza."
                />
              </label>
              <div className="md:col-span-2 flex justify-end">
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={pendingAlertId === alert.id}
                  onClick={() =>
                    onAlertUpdate(alert.id, {
                      assigned_to_user_id: draftAssignments[alert.id] ? Number(draftAssignments[alert.id]) : null,
                      verification_status: draftVerificationStatuses[alert.id] ?? alert.verification_status,
                      verification_notes: draftNotes[alert.id] ?? alert.verification_notes ?? "",
                    })
                  }
                >
                  Salva gestione caso
                </button>
              </div>
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function AlertsContent({ token }: { token: string }) {
  const [alerts, setAlerts] = useState<NetworkAlert[]>([]);
  const [assignees, setAssignees] = useState<NetworkAssignedUserSummary[]>([]);
  const [severityFilter, setSeverityFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [verificationFilter, setVerificationFilter] = useState<"" | AlertVerificationStatus>("");
  const [assigneeFilter, setAssigneeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pendingAlertId, setPendingAlertId] = useState<number | null>(null);
  const [draftAssignments, setDraftAssignments] = useState<Record<number, string>>({});
  const [draftVerificationStatuses, setDraftVerificationStatuses] = useState<Record<number, AlertVerificationStatus>>({});
  const [draftNotes, setDraftNotes] = useState<Record<number, string>>({});

  useEffect(() => {
    async function loadAlerts() {
      try {
        const [response, assigneesResponse] = await Promise.all([getNetworkAlerts(token), listNetworkDeviceAssignees(token)]);
        setAlerts(response);
        setAssignees(assigneesResponse);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento alert");
      }
    }

    void loadAlerts();
  }, [token]);

  async function handleAlertUpdate(
    alertId: number,
    payload: { status?: "resolved" | "ignored"; assigned_to_user_id?: number | null; verification_status?: AlertVerificationStatus; verification_notes?: string | null },
  ) {
    setPendingAlertId(alertId);
    try {
      const updated = await updateNetworkAlert(token, alertId, payload);
      setAlerts((items) => items.map((item) => (item.id === alertId ? updated : item)));
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore aggiornamento alert");
    } finally {
      setPendingAlertId(null);
    }
  }

  function handleDraftAssignmentChange(alertId: number, value: string) {
    setDraftAssignments((current) => ({ ...current, [alertId]: value }));
  }

  function handleDraftVerificationStatusChange(alertId: number, value: AlertVerificationStatus) {
    setDraftVerificationStatuses((current) => ({ ...current, [alertId]: value }));
  }

  function handleDraftNotesChange(alertId: number, value: string) {
    setDraftNotes((current) => ({ ...current, [alertId]: value }));
  }

  function applyKpiFilter(target: "unassigned" | "investigating" | "confirmed" | "false_positive") {
    setTypeFilter("VPN_BYPASS_SUSPECTED");
    if (target === "unassigned") {
      setAssigneeFilter("unassigned");
      setVerificationFilter("");
      return;
    }
    setAssigneeFilter("");
    setVerificationFilter(target);
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
    if (verificationFilter && alert.verification_status !== verificationFilter) {
      return false;
    }
    if (assigneeFilter === "unassigned" && alert.assigned_to_user_id !== null) {
      return false;
    }
    if (assigneeFilter && assigneeFilter !== "unassigned" && String(alert.assigned_to_user_id ?? "") !== assigneeFilter) {
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
  const vpnBypassAlerts = filteredAlerts.filter(
    (alert) =>
      alert.alert_type === "VPN_BYPASS_SUSPECTED"
      || alert.alert_type === "VPN_BYPASS_TRANSIENT_DEVICE"
      || alert.alert_type === "ARP_EPHEMERAL_DEVICE"
      || alert.alert_type === "ARP_MAC_CHANGE_SUSPECTED"
      || alert.alert_type === "ARP_IP_ROTATION_SUSPECTED",
  );
  const unassignedVpnBypassAlerts = vpnBypassAlerts.filter((alert) => alert.assigned_to_user_id === null);
  const investigatingVpnBypassAlerts = vpnBypassAlerts.filter((alert) => alert.verification_status === "investigating");
  const confirmedVpnBypassAlerts = vpnBypassAlerts.filter((alert) => alert.verification_status === "confirmed");
  const falsePositiveVpnBypassAlerts = vpnBypassAlerts.filter((alert) => alert.verification_status === "false_positive");

  return (
    <div className="page-stack">
      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Alert non disponibili</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <button
          type="button"
          className="panel-card text-left transition hover:-translate-y-0.5 hover:shadow-md bg-[linear-gradient(135deg,#FFF8E6_0%,#FFFFFF_100%)]"
          onClick={() => applyKpiFilter("unassigned")}
        >
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Da assegnare</p>
          <p className="mt-3 text-3xl font-semibold text-gray-900">{unassignedVpnBypassAlerts.length}</p>
          <p className="mt-2 text-sm text-gray-600">Casi bypass ancora senza owner operativo.</p>
        </button>
        <button
          type="button"
          className="panel-card text-left transition hover:-translate-y-0.5 hover:shadow-md bg-[linear-gradient(135deg,#EEF7F1_0%,#FFFFFF_100%)]"
          onClick={() => applyKpiFilter("investigating")}
        >
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">In Investigating</p>
          <p className="mt-3 text-3xl font-semibold text-gray-900">{investigatingVpnBypassAlerts.length}</p>
          <p className="mt-2 text-sm text-gray-600">Verifiche aperte su possibili tentativi di bypass.</p>
        </button>
        <button
          type="button"
          className="panel-card text-left transition hover:-translate-y-0.5 hover:shadow-md bg-[linear-gradient(135deg,#FDECEC_0%,#FFFFFF_100%)]"
          onClick={() => applyKpiFilter("confirmed")}
        >
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-rose-700">Confirmed</p>
          <p className="mt-3 text-3xl font-semibold text-gray-900">{confirmedVpnBypassAlerts.length}</p>
          <p className="mt-2 text-sm text-gray-600">Casi confermati come uso sospetto o bypass reale.</p>
        </button>
        <button
          type="button"
          className="panel-card text-left transition hover:-translate-y-0.5 hover:shadow-md bg-[linear-gradient(135deg,#F3F4F6_0%,#FFFFFF_100%)]"
          onClick={() => applyKpiFilter("false_positive")}
        >
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-700">False Positive</p>
          <p className="mt-3 text-3xl font-semibold text-gray-900">{falsePositiveVpnBypassAlerts.length}</p>
          <p className="mt-2 text-sm text-gray-600">Segnalazioni archiviate come rumore o traffico atteso.</p>
        </button>
      </section>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Filtri alert</p>
          <p className="section-copy">Filtra gli eventi per tipo, severità o testo e separa ciò che richiede azione da ciò che è già stato chiuso.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[minmax(0,1.3fr)_180px_220px_220px_220px]">
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
          <select className="form-control" value={verificationFilter} onChange={(event) => setVerificationFilter(event.target.value as "" | AlertVerificationStatus)}>
            <option value="">Tutte le verifiche</option>
            <option value="pending">pending</option>
            <option value="investigating">investigating</option>
            <option value="confirmed">confirmed</option>
            <option value="false_positive">false_positive</option>
            <option value="tolerated">tolerated</option>
          </select>
          <select className="form-control" value={assigneeFilter} onChange={(event) => setAssigneeFilter(event.target.value)}>
            <option value="">Tutti gli owner</option>
            <option value="unassigned">Non assegnati</option>
            {assignees.map((assignee) => (
              <option key={assignee.id} value={String(assignee.id)}>
                {assignee.full_name || assignee.username}
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
            assignees={assignees}
            draftAssignments={draftAssignments}
            draftVerificationStatuses={draftVerificationStatuses}
            draftNotes={draftNotes}
            onAlertUpdate={(alertId, payload) => void handleAlertUpdate(alertId, payload)}
            onDraftAssignmentChange={handleDraftAssignmentChange}
            onDraftVerificationStatusChange={handleDraftVerificationStatusChange}
            onDraftNotesChange={handleDraftNotesChange}
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
            assignees={assignees}
            draftAssignments={draftAssignments}
            draftVerificationStatuses={draftVerificationStatuses}
            draftNotes={draftNotes}
            onAlertUpdate={(alertId, payload) => void handleAlertUpdate(alertId, payload)}
            onDraftAssignmentChange={handleDraftAssignmentChange}
            onDraftVerificationStatusChange={handleDraftVerificationStatusChange}
            onDraftNotesChange={handleDraftNotesChange}
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
