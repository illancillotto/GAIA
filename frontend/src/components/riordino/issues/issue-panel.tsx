"use client";

import { useState } from "react";

import { RiordinoConfirmDialog } from "@/components/riordino/shared/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon } from "@/components/ui/icons";
import { formatRiordinoDate, formatRiordinoLabel } from "@/components/riordino/shared/format";
import { RiordinoStatusBadge } from "@/components/riordino/shared/status-badge";
import { closeRiordinoIssue, createRiordinoIssue } from "@/lib/riordino-api";
import { ApiError } from "@/lib/api";
import type { RiordinoIssue, RiordinoPhase } from "@/types/riordino";

type RiordinoIssuePanelProps = {
  token: string;
  practiceId: string;
  phases: RiordinoPhase[];
  issues: RiordinoIssue[];
  onUpdated: () => Promise<void>;
};

const ISSUE_CATEGORIES = ["administrative", "technical", "cadastral", "documentary", "gis"];
const ISSUE_SEVERITIES = ["low", "medium", "high", "blocking"];

export function RiordinoIssuePanel({ token, practiceId, phases, issues, onUpdated }: RiordinoIssuePanelProps) {
  const [title, setTitle] = useState("");
  const [issueType, setIssueType] = useState("anomalia");
  const [category, setCategory] = useState("administrative");
  const [severity, setSeverity] = useState("medium");
  const [description, setDescription] = useState("");
  const [phaseId, setPhaseId] = useState<string>("");
  const [stepId, setStepId] = useState<string>("");
  const [closeNotes, setCloseNotes] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmCloseIssue, setConfirmCloseIssue] = useState<RiordinoIssue | null>(null);

  function resolveActionError(currentError: unknown, fallback: string): string {
    if (currentError instanceof ApiError && currentError.status === 409) {
      return "Dati modificati da un altro utente. Ricarica la pratica e riprova.";
    }
    return currentError instanceof Error ? currentError.message : fallback;
  }

  const selectedPhase = phases.find((phase) => phase.id === phaseId) ?? null;
  const steps = selectedPhase?.steps ?? [];

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      await createRiordinoIssue(token, practiceId, {
        title,
        type: issueType,
        category,
        severity,
        description: description || null,
        phase_id: phaseId || null,
        step_id: stepId || null,
      });
      setTitle("");
      setDescription("");
      setPhaseId("");
      setStepId("");
      await onUpdated();
    } catch (currentError) {
      setError(resolveActionError(currentError, "Impossibile creare l'issue"));
    } finally {
      setBusy(false);
    }
  }

  async function handleClose(issueId: string) {
    setBusy(true);
    setError(null);
    try {
      await closeRiordinoIssue(token, practiceId, issueId, {
        resolution_notes: closeNotes[issueId] || "Chiusura issue da workspace",
      });
      await onUpdated();
      setConfirmCloseIssue(null);
    } catch (currentError) {
      setError(resolveActionError(currentError, "Impossibile chiudere l'issue"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
      <article className="panel-card">
        <p className="section-title">Issue e anomalie</p>
        <div className="mt-4 space-y-3">
          {issues.length === 0 ? (
            <EmptyState icon={AlertTriangleIcon} title="Nessuna issue" description="Le anomalie aperte o chiuse compariranno qui." />
          ) : (
            issues.map((issue) => (
              <div key={issue.id} className="rounded-2xl border border-gray-100 px-4 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-gray-900">{issue.title}</p>
                  <RiordinoStatusBadge value={issue.status} />
                  <RiordinoStatusBadge value={issue.severity} />
                </div>
                <p className="mt-1 text-sm text-gray-600">
                  {formatRiordinoLabel(issue.category)} • {formatRiordinoLabel(issue.type)} • aperta il {formatRiordinoDate(issue.opened_at, true)}
                </p>
                {issue.description ? <p className="mt-2 text-sm text-gray-600">{issue.description}</p> : null}
                {issue.status !== "closed" ? (
                  <div className="mt-3 grid gap-2 md:grid-cols-[minmax(0,1fr)_auto]">
                    <input
                      className="form-control"
                      placeholder="Note risoluzione"
                      value={closeNotes[issue.id] ?? ""}
                      onChange={(event) => setCloseNotes((current) => ({ ...current, [issue.id]: event.target.value }))}
                    />
                    <button className="btn-secondary" disabled={busy} onClick={() => setConfirmCloseIssue(issue)} type="button">
                      Chiudi issue
                    </button>
                  </div>
                ) : issue.resolution_notes ? (
                  <p className="mt-3 text-sm text-gray-600">Risoluzione: {issue.resolution_notes}</p>
                ) : null}
              </div>
            ))
          )}
        </div>
      </article>

      <article className="panel-card">
        <p className="section-title">Nuova issue</p>
        <div className="mt-4 grid gap-3">
          <input className="form-control" placeholder="Titolo issue" value={title} onChange={(event) => setTitle(event.target.value)} />
          <input className="form-control" placeholder="Tipologia" value={issueType} onChange={(event) => setIssueType(event.target.value)} />
          <select className="form-control" value={category} onChange={(event) => setCategory(event.target.value)}>
            {ISSUE_CATEGORIES.map((item) => (
              <option key={item} value={item}>{formatRiordinoLabel(item)}</option>
            ))}
          </select>
          <select className="form-control" value={severity} onChange={(event) => setSeverity(event.target.value)}>
            {ISSUE_SEVERITIES.map((item) => (
              <option key={item} value={item}>{formatRiordinoLabel(item)}</option>
            ))}
          </select>
          <select
            className="form-control"
            value={phaseId}
            onChange={(event) => {
              setPhaseId(event.target.value);
              setStepId("");
            }}
          >
            <option value="">Fase opzionale</option>
            {phases.map((phase) => (
              <option key={phase.id} value={phase.id}>{phase.phase_code}</option>
            ))}
          </select>
          <select className="form-control" value={stepId} onChange={(event) => setStepId(event.target.value)} disabled={!phaseId}>
            <option value="">Step opzionale</option>
            {steps.map((step) => (
              <option key={step.id} value={step.id}>{step.code} · {step.title}</option>
            ))}
          </select>
          <textarea className="form-control min-h-24" placeholder="Descrizione" value={description} onChange={(event) => setDescription(event.target.value)} />
          <button className="btn-primary" disabled={busy || !title.trim()} onClick={() => void handleCreate()} type="button">
            Crea issue
          </button>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </div>
      </article>

      <RiordinoConfirmDialog
        open={confirmCloseIssue !== null}
        title="Chiudere l'issue selezionata?"
        description={confirmCloseIssue ? `L'issue ${confirmCloseIssue.title} verrà chiusa con le note di risoluzione correnti.` : ""}
        confirmLabel="Chiudi issue"
        busy={busy}
        onCancel={() => setConfirmCloseIssue(null)}
        onConfirm={() => confirmCloseIssue ? handleClose(confirmCloseIssue.id) : undefined}
      />
    </div>
  );
}
