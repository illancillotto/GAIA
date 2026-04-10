"use client";

import { useMemo, useState } from "react";

import { ApiError } from "@/lib/api";
import { RiordinoConfirmDialog } from "@/components/riordino/shared/confirm-dialog";
import { RiordinoStatusBadge } from "@/components/riordino/shared/status-badge";
import { formatRiordinoDate, formatRiordinoLabel } from "@/components/riordino/shared/format";
import { advanceRiordinoStep, reopenRiordinoStep, skipRiordinoStep } from "@/lib/riordino-api";
import type { RiordinoStep } from "@/types/riordino";

type RiordinoStepCardProps = {
  token: string;
  practiceId: string;
  step: RiordinoStep;
  onUpdated: () => Promise<void>;
};

const DECISION_OUTCOMES: Record<string, string[]> = {
  F2_VERIFICA: ["conforme", "non_conforme"],
  F1_OSSERVAZIONI: ["ricorsi_presenti", "nessun_ricorso"],
};

export function RiordinoStepCard({ token, practiceId, step, onUpdated }: RiordinoStepCardProps) {
  const [outcomeCode, setOutcomeCode] = useState(step.outcome_code ?? "");
  const [outcomeNotes, setOutcomeNotes] = useState(step.outcome_notes ?? "");
  const [skipReason, setSkipReason] = useState(step.skip_reason ?? "");
  const [busyAction, setBusyAction] = useState<"advance" | "skip" | "reopen" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<"advance" | "skip" | "reopen" | null>(null);

  const canAdvance = step.status === "todo" || step.status === "in_progress";
  const canReopen = step.status === "done";
  const outcomeOptions = useMemo(() => DECISION_OUTCOMES[step.code] ?? ["conforme", "non_conforme"], [step.code]);

  function resolveActionError(error: unknown, fallback: string): string {
    if (error instanceof ApiError && error.status === 409) {
      return "Dati modificati da un altro utente. Ricarica la pratica e riprova.";
    }
    return error instanceof Error ? error.message : fallback;
  }

  async function handleAdvance() {
    setBusyAction("advance");
    setActionError(null);
    try {
      await advanceRiordinoStep(token, practiceId, step.id, {
        outcome_code: step.is_decision ? outcomeCode : undefined,
        outcome_notes: outcomeNotes || undefined,
      });
      await onUpdated();
      setConfirmAction(null);
    } catch (error) {
      setActionError(resolveActionError(error, "Impossibile completare lo step"));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSkip() {
    setBusyAction("skip");
    setActionError(null);
    try {
      await skipRiordinoStep(token, practiceId, step.id, { skip_reason: skipReason });
      await onUpdated();
      setConfirmAction(null);
    } catch (error) {
      setActionError(resolveActionError(error, "Impossibile saltare lo step"));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleReopen() {
    setBusyAction("reopen");
    setActionError(null);
    try {
      await reopenRiordinoStep(token, practiceId, step.id);
      await onUpdated();
      setConfirmAction(null);
    } catch (error) {
      setActionError(resolveActionError(error, "Impossibile riaprire lo step"));
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <article className="rounded-2xl border border-gray-100 bg-white px-5 py-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-[#EAF3E8] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">{step.code}</span>
        <RiordinoStatusBadge value={step.status} dueAt={step.due_at} />
        {step.branch ? <span className="text-xs text-gray-500">ramo {formatRiordinoLabel(step.branch)}</span> : null}
        {step.is_required ? <span className="text-xs font-medium text-gray-500">obbligatorio</span> : null}
        {step.requires_document ? <span className="text-xs font-medium text-gray-500">doc richiesto</span> : null}
      </div>
      <div className="mt-3 flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-base font-semibold text-gray-900">{step.title}</p>
          <p className="mt-1 text-sm text-gray-500">
            Scadenza {formatRiordinoDate(step.due_at)} • Avvio {formatRiordinoDate(step.started_at, true)} • Chiusura {formatRiordinoDate(step.completed_at, true)}
          </p>
        </div>
        <div className="rounded-xl bg-gray-50 px-3 py-2 text-xs text-gray-600">
          {step.documents.length} doc • {step.checklist_items.filter((item) => item.is_checked).length}/{step.checklist_items.length} checklist
        </div>
      </div>

      {step.outcome_code || step.outcome_notes || step.skip_reason ? (
        <div className="mt-3 rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 text-sm text-gray-600">
          {step.outcome_code ? <p>Esito: <span className="font-medium text-gray-800">{formatRiordinoLabel(step.outcome_code)}</span></p> : null}
          {step.outcome_notes ? <p className="mt-1">Note esito: {step.outcome_notes}</p> : null}
          {step.skip_reason ? <p className="mt-1">Motivo skip: {step.skip_reason}</p> : null}
        </div>
      ) : null}

      {step.checklist_items.length > 0 ? (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">Checklist</p>
          <div className="mt-2 grid gap-2">
            {step.checklist_items.map((item) => (
              <div key={item.id} className="flex items-start gap-2 rounded-xl border border-gray-100 px-3 py-2 text-sm text-gray-600">
                <span className={`mt-0.5 h-2.5 w-2.5 rounded-full ${item.is_checked ? "bg-emerald-500" : item.is_blocking ? "bg-red-400" : "bg-gray-300"}`} />
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {canAdvance || canReopen ? (
        <div className="mt-4 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
          {step.is_decision && canAdvance ? (
            <div className="grid gap-3 md:grid-cols-2">
              <label className="text-sm text-gray-600">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-widest text-gray-400">Esito decisione</span>
                <select className="form-control" value={outcomeCode} onChange={(event) => setOutcomeCode(event.target.value)}>
                  <option value="">Seleziona esito</option>
                  {outcomeOptions.map((option) => (
                    <option key={option} value={option}>{formatRiordinoLabel(option)}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm text-gray-600 md:col-span-2">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-widest text-gray-400">Note esito</span>
                <textarea className="form-control min-h-24" value={outcomeNotes} onChange={(event) => setOutcomeNotes(event.target.value)} />
              </label>
            </div>
          ) : null}

          {canAdvance ? (
            <div className="mt-4 flex flex-wrap gap-2">
              <button className="btn-primary" disabled={busyAction !== null} onClick={() => setConfirmAction("advance")} type="button">
                {busyAction === "advance" ? "Completamento..." : "Completa step"}
              </button>
              <input
                className="form-control min-w-[240px] flex-1"
                placeholder="Motivo skip manuale"
                value={skipReason}
                onChange={(event) => setSkipReason(event.target.value)}
              />
              <button className="btn-secondary" disabled={busyAction !== null || !skipReason.trim()} onClick={() => setConfirmAction("skip")} type="button">
                {busyAction === "skip" ? "Skip..." : "Salta step"}
              </button>
            </div>
          ) : null}

          {canReopen ? (
            <div className="mt-4 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={busyAction !== null} onClick={() => setConfirmAction("reopen")} type="button">
                {busyAction === "reopen" ? "Riapertura..." : "Riapri step"}
              </button>
            </div>
          ) : null}

          {actionError ? <p className="mt-3 text-sm text-red-600">{actionError}</p> : null}
        </div>
      ) : null}

      <RiordinoConfirmDialog
        open={confirmAction === "advance"}
        title={`Completare lo step ${step.code}?`}
        description="L'azione registra l'esito operativo dello step e aggiorna il workflow della pratica."
        confirmLabel="Completa step"
        busy={busyAction === "advance"}
        onCancel={() => setConfirmAction(null)}
        onConfirm={handleAdvance}
      />
      <RiordinoConfirmDialog
        open={confirmAction === "skip"}
        title={`Saltare lo step ${step.code}?`}
        description="Lo step verrà marcato come saltato. Assicurati che il motivo inserito sia corretto e auditabile."
        confirmLabel="Conferma skip"
        busy={busyAction === "skip"}
        onCancel={() => setConfirmAction(null)}
        onConfirm={handleSkip}
      />
      <RiordinoConfirmDialog
        open={confirmAction === "reopen"}
        title={`Riaprire lo step ${step.code}?`}
        description="Lo step tornerà in lavorazione e l'esito corrente verrà annullato."
        confirmLabel="Riapri step"
        busy={busyAction === "reopen"}
        onCancel={() => setConfirmAction(null)}
        onConfirm={handleReopen}
      />
    </article>
  );
}
