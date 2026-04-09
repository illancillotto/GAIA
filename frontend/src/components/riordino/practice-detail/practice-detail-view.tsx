"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { RiordinoAppealPanel } from "@/components/riordino/appeals/appeal-panel";
import { RiordinoDocumentPanel } from "@/components/riordino/documents/document-panel";
import { RiordinoGisPanel } from "@/components/riordino/gis/gis-panel";
import { RiordinoIssuePanel } from "@/components/riordino/issues/issue-panel";
import { RiordinoConfirmDialog } from "@/components/riordino/shared/confirm-dialog";
import { formatRiordinoDate, formatRiordinoLabel } from "@/components/riordino/shared/format";
import { RiordinoStatusBadge } from "@/components/riordino/shared/status-badge";
import { RiordinoTimelinePanel } from "@/components/riordino/timeline/timeline-panel";
import { RiordinoStepCard } from "@/components/riordino/workflow/step-card";
import { RiordinoWorkflowStepper } from "@/components/riordino/workflow/workflow-stepper";
import {
  completeRiordinoPhase,
  downloadRiordinoPracticeDossier,
  downloadRiordinoPracticeSummary,
  getRiordinoPractice,
  listRiordinoAppeals,
  listRiordinoDocuments,
  listRiordinoEvents,
  listRiordinoGisLinks,
  listRiordinoIssues,
  startRiordinoPhase,
} from "@/lib/riordino-api";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import type {
  RiordinoAppeal,
  RiordinoDocument,
  RiordinoEvent,
  RiordinoGisLink,
  RiordinoIssue,
  RiordinoPracticeDetail,
} from "@/types/riordino";

type WorkspaceTab = "documents" | "issues" | "appeals" | "gis" | "timeline";

const tabs: { id: WorkspaceTab; label: string }[] = [
  { id: "documents", label: "Documenti" },
  { id: "issues", label: "Issue" },
  { id: "appeals", label: "Ricorsi" },
  { id: "gis", label: "GIS" },
  { id: "timeline", label: "Timeline" },
];

export function RiordinoPracticeDetailView({ token, practiceId }: { token: string; practiceId: string }) {
  const [practice, setPractice] = useState<RiordinoPracticeDetail | null>(null);
  const [appeals, setAppeals] = useState<RiordinoAppeal[]>([]);
  const [issues, setIssues] = useState<RiordinoIssue[]>([]);
  const [documents, setDocuments] = useState<RiordinoDocument[]>([]);
  const [events, setEvents] = useState<RiordinoEvent[]>([]);
  const [gisLinks, setGisLinks] = useState<RiordinoGisLink[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("documents");
  const [phaseBusy, setPhaseBusy] = useState<"start" | "complete" | null>(null);
  const [phaseError, setPhaseError] = useState<string | null>(null);
  const [exportBusy, setExportBusy] = useState<"summary" | "dossier" | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [workspaceNotice, setWorkspaceNotice] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<"start-phase" | "complete-phase" | null>(null);

  function triggerDownload(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const anchor = window.document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
  }

  const currentPhase = useMemo(() => {
    if (!practice) {
      return null;
    }
    return practice.phases.find((phase) => phase.phase_code === practice.current_phase) ?? practice.phases[0] ?? null;
  }, [practice]);
  const exportBasename = practice?.code.toLowerCase() ?? "riordino-practice";

  function resolveActionError(error: unknown, fallback: string): string {
    if (error instanceof ApiError && error.status === 409) {
      setWorkspaceNotice("Dati modificati da un altro utente. Ricarica la pratica per riallineare il workspace.");
      return "Dati modificati da un altro utente. Ricarica la pratica e riprova.";
    }

    return error instanceof Error ? error.message : fallback;
  }

  const refreshWorkspace = useCallback(async () => {
    try {
      const [practiceResponse, appealsResponse, issuesResponse, documentsResponse, eventsResponse, gisResponse] = await Promise.all([
        getRiordinoPractice(token, practiceId),
        listRiordinoAppeals(token, practiceId),
        listRiordinoIssues(token, practiceId),
        listRiordinoDocuments(token, practiceId),
        listRiordinoEvents(token, practiceId),
        listRiordinoGisLinks(token, practiceId),
      ]);
      setPractice(practiceResponse);
      setAppeals(appealsResponse);
      setIssues(issuesResponse);
      setDocuments(documentsResponse.items);
      setEvents(eventsResponse);
      setGisLinks(gisResponse);
      setLoadError(null);
      setWorkspaceNotice(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento pratica");
    }
  }, [practiceId, token]);

  useEffect(() => {
    void refreshWorkspace();
  }, [refreshWorkspace]);

  async function handleStartPhase() {
    if (!currentPhase) {
      return;
    }
    setPhaseBusy("start");
    setPhaseError(null);
    try {
      await startRiordinoPhase(token, practiceId, currentPhase.id);
      await refreshWorkspace();
      setConfirmAction(null);
    } catch (error) {
      setPhaseError(resolveActionError(error, "Impossibile avviare la fase"));
    } finally {
      setPhaseBusy(null);
    }
  }

  async function handleCompletePhase() {
    if (!currentPhase) {
      return;
    }
    setPhaseBusy("complete");
    setPhaseError(null);
    try {
      await completeRiordinoPhase(token, practiceId, currentPhase.id, {});
      await refreshWorkspace();
      setConfirmAction(null);
    } catch (error) {
      setPhaseError(resolveActionError(error, "Impossibile completare la fase"));
    } finally {
      setPhaseBusy(null);
    }
  }

  async function handleExportSummary() {
    setExportBusy("summary");
    setExportError(null);
    try {
      const blob = await downloadRiordinoPracticeSummary(token, practiceId);
      triggerDownload(blob, `${exportBasename}-summary.csv`);
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "Impossibile esportare il riepilogo CSV");
    } finally {
      setExportBusy(null);
    }
  }

  async function handleExportDossier() {
    setExportBusy("dossier");
    setExportError(null);
    try {
      const blob = await downloadRiordinoPracticeDossier(token, practiceId);
      triggerDownload(blob, `${exportBasename}-dossier.zip`);
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "Impossibile esportare il dossier ZIP");
    } finally {
      setExportBusy(null);
    }
  }

  if (loadError && !practice) {
    return <p className="text-sm text-red-600">{loadError}</p>;
  }

  if (!practice || !currentPhase) {
    return <p className="text-sm text-gray-500">Caricamento pratica...</p>;
  }

  return (
    <div className="page-stack">
      {workspaceNotice ? (
        <article className="panel-card border border-amber-200 bg-amber-50/80">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <p className="text-sm font-medium text-amber-900">{workspaceNotice}</p>
            <button className="btn-secondary" onClick={() => void refreshWorkspace()} type="button">
              Ricarica pratica
            </button>
          </div>
        </article>
      ) : null}

      <article className="panel-card">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h3 className="page-heading">{practice.code}</h3>
              <RiordinoStatusBadge value={practice.status} />
              <RiordinoStatusBadge value={practice.current_phase} />
            </div>
            <p className="mt-2 text-base text-gray-700">{practice.title}</p>
            {practice.description ? <p className="mt-1 text-sm text-gray-500">{practice.description}</p> : null}
          </div>
          <div className="grid gap-2 sm:grid-cols-2 xl:min-w-[360px]">
            <div className="rounded-2xl bg-[#F4F7F5] px-4 py-3">
              <p className="text-xs uppercase tracking-widest text-gray-400">Comune / Lotto</p>
              <p className="mt-1 text-sm font-medium text-gray-900">{practice.municipality} • {practice.grid_code}/{practice.lot_code}</p>
            </div>
            <div className="rounded-2xl bg-[#F4F7F5] px-4 py-3">
              <p className="text-xs uppercase tracking-widest text-gray-400">Conteggi</p>
              <p className="mt-1 text-sm font-medium text-gray-900">
                {practice.documents_count} doc • {practice.issues_count} issue • {practice.appeals_count} ricorsi
              </p>
            </div>
            <div className="rounded-2xl bg-[#F4F7F5] px-4 py-3">
              <p className="text-xs uppercase tracking-widest text-gray-400">Apertura</p>
              <p className="mt-1 text-sm font-medium text-gray-900">{formatRiordinoDate(practice.opened_at, true)}</p>
            </div>
            <div className="rounded-2xl bg-[#F4F7F5] px-4 py-3">
              <p className="text-xs uppercase tracking-widest text-gray-400">Responsabile</p>
              <p className="mt-1 text-sm font-medium text-gray-900">Utente #{practice.owner_user_id}</p>
            </div>
          </div>
        </div>
      </article>

      <article className="panel-card">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="section-title">Fase corrente: {formatRiordinoLabel(currentPhase.phase_code)}</p>
              <RiordinoStatusBadge value={currentPhase.status} />
              {currentPhase.steps.some((step) => {
                if (!step.due_at || step.status === "done" || step.status === "skipped") {
                  return false;
                }

                const dueAt = new Date(step.due_at).getTime();
                return !Number.isNaN(dueAt) && dueAt - Date.now() <= 7 * 24 * 60 * 60 * 1000;
              }) ? <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700">Scadenza imminente</span> : null}
            </div>
            <p className="mt-1 text-sm text-gray-500">
              Avvio {formatRiordinoDate(currentPhase.started_at, true)} • Chiusura {formatRiordinoDate(currentPhase.completed_at, true)}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="btn-secondary" disabled={exportBusy !== null} onClick={() => void handleExportSummary()} type="button">
              {exportBusy === "summary" ? "Export CSV..." : "Esporta riepilogo CSV"}
            </button>
            <button className="btn-secondary" disabled={exportBusy !== null} onClick={() => void handleExportDossier()} type="button">
              {exportBusy === "dossier" ? "Export ZIP..." : "Esporta dossier ZIP"}
            </button>
            {currentPhase.status === "not_started" ? (
              <button className="btn-secondary" disabled={phaseBusy !== null} onClick={() => setConfirmAction("start-phase")} type="button">
                {phaseBusy === "start" ? "Avvio..." : "Avvia fase"}
              </button>
            ) : null}
            {currentPhase.status !== "completed" ? (
              <button className="btn-primary" disabled={phaseBusy !== null} onClick={() => setConfirmAction("complete-phase")} type="button">
                {phaseBusy === "complete" ? "Chiusura..." : "Completa fase"}
              </button>
            ) : null}
          </div>
        </div>
        {phaseError ? <p className="mt-3 text-sm text-red-600">{phaseError}</p> : null}
        {exportError ? <p className="mt-3 text-sm text-red-600">{exportError}</p> : null}
      </article>

      <RiordinoWorkflowStepper phase={currentPhase} />

      <article className="panel-card">
        <p className="section-title">Step della fase</p>
        <div className="mt-4 space-y-4">
          {currentPhase.steps.map((step) => (
            <RiordinoStepCard key={step.id} token={token} practiceId={practiceId} step={step} onUpdated={refreshWorkspace} />
          ))}
        </div>
      </article>

      <article className="panel-card">
        <div className="flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={cn(activeTab === tab.id ? "btn-primary" : "btn-secondary")}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>
      </article>

      {activeTab === "documents" ? (
        <RiordinoDocumentPanel token={token} practiceId={practiceId} phases={practice.phases} documents={documents} onUpdated={refreshWorkspace} />
      ) : null}
      {activeTab === "issues" ? (
        <RiordinoIssuePanel token={token} practiceId={practiceId} phases={practice.phases} issues={issues} onUpdated={refreshWorkspace} />
      ) : null}
      {activeTab === "appeals" ? (
        <RiordinoAppealPanel token={token} practiceId={practiceId} appeals={appeals} onUpdated={refreshWorkspace} />
      ) : null}
      {activeTab === "gis" ? (
        <RiordinoGisPanel token={token} practiceId={practiceId} links={gisLinks} onUpdated={refreshWorkspace} />
      ) : null}
      {activeTab === "timeline" ? <RiordinoTimelinePanel events={events} /> : null}

      {loadError ? (
        <article className="panel-card border border-red-100 bg-red-50/60">
          <p className="text-sm font-medium text-red-700">Ultimo errore di refresh</p>
          <p className="mt-1 text-sm text-red-600">{loadError}</p>
        </article>
      ) : null}

      <RiordinoConfirmDialog
        open={confirmAction === "start-phase"}
        title={`Avviare ${formatRiordinoLabel(currentPhase.phase_code)}?`}
        description="L'avvio della fase apre ufficialmente il blocco operativo corrente e viene registrato nella timeline della pratica."
        confirmLabel="Avvia fase"
        busy={phaseBusy === "start"}
        onCancel={() => setConfirmAction(null)}
        onConfirm={handleStartPhase}
      />
      <RiordinoConfirmDialog
        open={confirmAction === "complete-phase"}
        title={`Completare ${formatRiordinoLabel(currentPhase.phase_code)}?`}
        description="La chiusura verifica i vincoli di workflow, ricorsi e issue bloccanti prima di avanzare la pratica."
        confirmLabel="Completa fase"
        busy={phaseBusy === "complete"}
        onCancel={() => setConfirmAction(null)}
        onConfirm={handleCompletePhase}
      />
    </div>
  );
}
