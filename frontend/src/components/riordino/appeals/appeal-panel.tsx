"use client";

import { useMemo, useState } from "react";

import { RiordinoConfirmDialog } from "@/components/riordino/shared/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon } from "@/components/ui/icons";
import { formatRiordinoDate, formatRiordinoLabel } from "@/components/riordino/shared/format";
import { RiordinoStatusBadge } from "@/components/riordino/shared/status-badge";
import { createRiordinoAppeal, resolveRiordinoAppeal } from "@/lib/riordino-api";
import { ApiError } from "@/lib/api";
import type { RiordinoAppeal } from "@/types/riordino";

type RiordinoAppealPanelProps = {
  token: string;
  practiceId: string;
  appeals: RiordinoAppeal[];
  onUpdated: () => Promise<void>;
};

const RESOLUTION_STATUSES = ["resolved_accepted", "resolved_rejected", "withdrawn"];

export function RiordinoAppealPanel({ token, practiceId, appeals, onUpdated }: RiordinoAppealPanelProps) {
  const [appellantName, setAppellantName] = useState("");
  const [filedAt, setFiledAt] = useState("");
  const [deadlineAt, setDeadlineAt] = useState("");
  const [commissionName, setCommissionName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resolveNotes, setResolveNotes] = useState<Record<string, string>>({});
  const [resolveStatuses, setResolveStatuses] = useState<Record<string, string>>({});
  const [confirmResolveAppeal, setConfirmResolveAppeal] = useState<RiordinoAppeal | null>(null);

  const openCount = useMemo(
    () => appeals.filter((appeal) => appeal.status === "open" || appeal.status === "under_review").length,
    [appeals],
  );

  function resolveActionError(currentError: unknown, fallback: string): string {
    if (currentError instanceof ApiError && currentError.status === 409) {
      return "Dati modificati da un altro utente. Ricarica la pratica e riprova.";
    }
    return currentError instanceof Error ? currentError.message : fallback;
  }

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      await createRiordinoAppeal(token, practiceId, {
        appellant_name: appellantName,
        filed_at: filedAt,
        deadline_at: deadlineAt || null,
        commission_name: commissionName || null,
      });
      setAppellantName("");
      setFiledAt("");
      setDeadlineAt("");
      setCommissionName("");
      await onUpdated();
    } catch (currentError) {
      setError(resolveActionError(currentError, "Impossibile creare il ricorso"));
    } finally {
      setBusy(false);
    }
  }

  async function handleResolve(appealId: string) {
    setBusy(true);
    setError(null);
    try {
      await resolveRiordinoAppeal(token, practiceId, appealId, {
        status: resolveStatuses[appealId] || "resolved_accepted",
        resolution_notes: resolveNotes[appealId] || null,
      });
      await onUpdated();
      setConfirmResolveAppeal(null);
    } catch (currentError) {
      setError(resolveActionError(currentError, "Impossibile risolvere il ricorso"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1.3fr_0.9fr]">
      <article className="panel-card">
        <div className="flex flex-wrap items-center gap-3">
          <p className="section-title">Ricorsi</p>
          <RiordinoStatusBadge value={openCount > 0 ? "blocked" : "completed"} />
        </div>
        <p className="section-copy mt-1">Ricorsi registrati nella Fase 1 e relativo stato di lavorazione.</p>
        <div className="mt-4 space-y-3">
          {appeals.length === 0 ? (
            <EmptyState icon={DocumentIcon} title="Nessun ricorso" description="I ricorsi registrati per la pratica compariranno qui." />
          ) : (
            appeals.map((appeal) => (
              <div key={appeal.id} className="rounded-2xl border border-gray-100 px-4 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-gray-900">{appeal.appellant_name}</p>
                  <RiordinoStatusBadge value={appeal.status} />
                </div>
                <p className="mt-1 text-sm text-gray-600">
                  Deposito {formatRiordinoDate(appeal.filed_at)} • Termine {formatRiordinoDate(appeal.deadline_at)} • Commissione {appeal.commission_name || "—"}
                </p>
                {appeal.resolution_notes ? <p className="mt-2 text-sm text-gray-600">{appeal.resolution_notes}</p> : null}
                {(appeal.status === "open" || appeal.status === "under_review") ? (
                  <div className="mt-3 grid gap-2 md:grid-cols-[200px_minmax(0,1fr)_auto]">
                    <select
                      className="form-control"
                      value={resolveStatuses[appeal.id] ?? "resolved_accepted"}
                      onChange={(event) => setResolveStatuses((current) => ({ ...current, [appeal.id]: event.target.value }))}
                    >
                      {RESOLUTION_STATUSES.map((status) => (
                        <option key={status} value={status}>{formatRiordinoLabel(status)}</option>
                      ))}
                    </select>
                    <input
                      className="form-control"
                      placeholder="Note risoluzione"
                      value={resolveNotes[appeal.id] ?? ""}
                      onChange={(event) => setResolveNotes((current) => ({ ...current, [appeal.id]: event.target.value }))}
                    />
                    <button className="btn-secondary" disabled={busy} onClick={() => setConfirmResolveAppeal(appeal)} type="button">
                      Risolvi
                    </button>
                  </div>
                ) : null}
              </div>
            ))
          )}
        </div>
      </article>

      <article className="panel-card">
        <p className="section-title">Nuovo ricorso</p>
        <div className="mt-4 grid gap-3">
          <label className="text-sm text-gray-600">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-widest text-gray-400">Ricorrente</span>
            <input className="form-control" value={appellantName} onChange={(event) => setAppellantName(event.target.value)} />
          </label>
          <label className="text-sm text-gray-600">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-widest text-gray-400">Data deposito</span>
            <input className="form-control" type="date" value={filedAt} onChange={(event) => setFiledAt(event.target.value)} />
          </label>
          <label className="text-sm text-gray-600">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-widest text-gray-400">Scadenza</span>
            <input className="form-control" type="date" value={deadlineAt} onChange={(event) => setDeadlineAt(event.target.value)} />
          </label>
          <label className="text-sm text-gray-600">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-widest text-gray-400">Commissione</span>
            <input className="form-control" value={commissionName} onChange={(event) => setCommissionName(event.target.value)} />
          </label>
          <button className="btn-primary" disabled={busy || !appellantName.trim() || !filedAt} onClick={() => void handleCreate()} type="button">
            Crea ricorso
          </button>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </div>
      </article>

      <RiordinoConfirmDialog
        open={confirmResolveAppeal !== null}
        title="Risolvere il ricorso selezionato?"
        description={confirmResolveAppeal ? `Il ricorso di ${confirmResolveAppeal.appellant_name} verrà aggiornato con l'esito scelto.` : ""}
        confirmLabel="Risolvi ricorso"
        busy={busy}
        onCancel={() => setConfirmResolveAppeal(null)}
        onConfirm={() => confirmResolveAppeal ? handleResolve(confirmResolveAppeal.id) : undefined}
      />
    </div>
  );
}
