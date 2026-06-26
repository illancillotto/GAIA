"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { EmptyState } from "@/components/ui/empty-state";
import { CheckIcon } from "@/components/ui/icons";
import {
  createPresenzeRecoveryAdjustment,
  deletePresenzeRecoveryAdjustment,
  getPresenzeCollaboratorCalendar,
  getPresenzeRecoveryDashboard,
  listPresenzeRecoveryAdjustments,
  reviewPresenzeRecoveryAdjustment,
  updatePresenzeRecoveryAdjustment,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { getPresenzeCompanyLabel } from "@/lib/presenze-display";
import type {
  PresenzeDailyRecord,
  PresenzeRecoveryAdjustment,
  PresenzeRecoveryDashboardResponse,
} from "@/types/api";

type AdjustmentFormState = {
  id: string | null;
  adjustmentDate: string;
  deltaDays: string;
  kind: "credit" | "debit" | "correction";
  reason: string;
  note: string;
};

const EMPTY_FORM: AdjustmentFormState = {
  id: null,
  adjustmentDate: "",
  deltaDays: "",
  kind: "correction",
  reason: "",
  note: "",
};

function currentYearBounds(): { start: string; end: string } {
  const now = new Date();
  return {
    start: `${now.getFullYear()}-01-01`,
    end: `${now.getFullYear()}-12-31`,
  };
}

function formatDateLabel(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("it-IT", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(`${value}T00:00:00`));
}

function formatDateTimeLabel(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function adjustmentStatusTone(status: PresenzeRecoveryAdjustment["approval_status"]): string {
  if (status === "approved") return "bg-emerald-100 text-emerald-800";
  if (status === "rejected") return "bg-red-100 text-red-800";
  return "bg-amber-100 text-amber-800";
}

function adjustmentStatusLabel(status: PresenzeRecoveryAdjustment["approval_status"]): string {
  if (status === "approved") return "Approvata";
  if (status === "rejected") return "Respinta";
  return "In attesa";
}

function activityLabel(record: PresenzeDailyRecord): string {
  if (record.grants_recovery_day) return `Maturato +${record.recovery_day_credit}`;
  if (record.uses_recovery_day) return `Fruito -${record.recovery_day_debit}`;
  return "Nessun movimento";
}

function activityTone(record: PresenzeDailyRecord): string {
  if (record.grants_recovery_day) return "border-violet-200 bg-violet-50 text-violet-900";
  if (record.uses_recovery_day) return "border-fuchsia-200 bg-fuchsia-50 text-fuchsia-900";
  return "border-gray-200 bg-gray-50 text-gray-700";
}

export default function PresenzeRecuperiPage() {
  const initialBounds = currentYearBounds();
  const [dashboard, setDashboard] = useState<PresenzeRecoveryDashboardResponse | null>(null);
  const [dateFrom, setDateFrom] = useState(initialBounds.start);
  const [dateTo, setDateTo] = useState(initialBounds.end);
  const [searchTerm, setSearchTerm] = useState("");
  const [negativeOnly, setNegativeOnly] = useState(false);
  const [pendingValidationOnly, setPendingValidationOnly] = useState(false);
  const [pendingAdjustmentsOnly, setPendingAdjustmentsOnly] = useState(false);
  const [manualAdjustmentsOnly, setManualAdjustmentsOnly] = useState(false);
  const [selectedCollaboratorId, setSelectedCollaboratorId] = useState<string>("");
  const [records, setRecords] = useState<PresenzeDailyRecord[]>([]);
  const [adjustments, setAdjustments] = useState<PresenzeRecoveryAdjustment[]>([]);
  const [form, setForm] = useState<AdjustmentFormState>(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const selectedItem = useMemo(
    () => dashboard?.items.find((item) => item.collaborator_id === selectedCollaboratorId) ?? null,
    [dashboard, selectedCollaboratorId],
  );

  const loadDashboard = useCallback(async (preserveSelection = true) => {
    const token = getStoredAccessToken();
    if (!token) return;
    setLoading(true);
    try {
      const nextDashboard = await getPresenzeRecoveryDashboard(token, {
        dateFrom,
        dateTo,
        q: searchTerm.trim() || undefined,
        negativeOnly,
        pendingValidationOnly,
        pendingAdjustmentsOnly,
        manualAdjustmentsOnly,
      });
      setDashboard(nextDashboard);
      setSelectedCollaboratorId((current) => {
        if (preserveSelection && current && nextDashboard.items.some((item) => item.collaborator_id === current)) {
          return current;
        }
        return nextDashboard.items[0]?.collaborator_id ?? "";
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento dashboard recuperi");
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, manualAdjustmentsOnly, negativeOnly, pendingAdjustmentsOnly, pendingValidationOnly, searchTerm]);

  const loadDetail = useCallback(async (collaboratorId: string) => {
    const token = getStoredAccessToken();
    if (!token || !collaboratorId) return;
    setDetailLoading(true);
    try {
      const [calendar, adjustmentRows] = await Promise.all([
        getPresenzeCollaboratorCalendar(token, collaboratorId, dateFrom, dateTo),
        listPresenzeRecoveryAdjustments(token, collaboratorId),
      ]);
      setRecords(calendar.items.filter((item) => item.grants_recovery_day || item.uses_recovery_day));
      setAdjustments(adjustmentRows);
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : "Errore caricamento dettaglio recuperi");
    } finally {
      setDetailLoading(false);
    }
  }, [dateFrom, dateTo]);

  useEffect(() => {
    void loadDashboard(false);
  }, [loadDashboard]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void loadDashboard(false);
    }, 250);
    return () => window.clearTimeout(handle);
  }, [loadDashboard]);

  useEffect(() => {
    if (!selectedCollaboratorId) {
      setRecords([]);
      setAdjustments([]);
      return;
    }
    void loadDetail(selectedCollaboratorId);
  }, [loadDetail, selectedCollaboratorId]);

  async function handleSubmit() {
    const token = getStoredAccessToken();
    if (!token || !selectedCollaboratorId) return;
    const deltaDays = Number(form.deltaDays);
    if (!form.adjustmentDate || !form.reason.trim() || !Number.isInteger(deltaDays) || deltaDays === 0) {
      setError("Compila data, motivo e delta giorni intero diverso da zero.");
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      if (form.id == null) {
        await createPresenzeRecoveryAdjustment(token, {
          collaborator_id: selectedCollaboratorId,
          adjustment_date: form.adjustmentDate,
          delta_days: deltaDays,
          kind: form.kind,
          reason: form.reason.trim(),
          note: form.note.trim() || null,
        });
        setSuccess("Rettifica recupero creata.");
      } else {
        await updatePresenzeRecoveryAdjustment(token, form.id, {
          adjustment_date: form.adjustmentDate,
          delta_days: deltaDays,
          kind: form.kind,
          reason: form.reason.trim(),
          note: form.note.trim() || null,
        });
        setSuccess("Rettifica recupero aggiornata.");
      }
      setForm(EMPTY_FORM);
      await Promise.all([loadDashboard(), loadDetail(selectedCollaboratorId)]);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Errore salvataggio rettifica");
    } finally {
      setSaving(false);
    }
  }

  async function handleReview(adjustmentId: string, approvalStatus: "approved" | "rejected") {
    const token = getStoredAccessToken();
    if (!token || !selectedCollaboratorId) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await reviewPresenzeRecoveryAdjustment(token, adjustmentId, {
        approval_status: approvalStatus,
        approval_note: approvalStatus === "rejected" ? "Da rivedere da HR." : "Verificata da HR.",
      });
      setSuccess(approvalStatus === "approved" ? "Rettifica approvata." : "Rettifica respinta.");
      await Promise.all([loadDashboard(), loadDetail(selectedCollaboratorId)]);
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "Errore revisione rettifica");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(adjustmentId: string) {
    const token = getStoredAccessToken();
    if (!token || !selectedCollaboratorId) return;
    setDeletingId(adjustmentId);
    setError(null);
    setSuccess(null);
    try {
      await deletePresenzeRecoveryAdjustment(token, adjustmentId);
      if (form.id === adjustmentId) {
        setForm(EMPTY_FORM);
      }
      setSuccess("Rettifica eliminata.");
      await Promise.all([loadDashboard(), loadDetail(selectedCollaboratorId)]);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione rettifica");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <ProtectedPage
      title="Recuperi giornaliere"
      description="Dashboard HR per controllo, monitoraggio e rettifica dei recuperi maturati e fruiti."
      breadcrumb="Giornaliere"
      requiredModule="presenze"
      requiredRoles={["hr_manager", "admin", "super_admin"]}
    >
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <article className="panel-card space-y-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="section-title">Controllo recuperi</p>
              <p className="section-copy">Saldo derivato da festivita soppresse e riposi compensativi. Le rettifiche manuali entrano nel saldo solo dopo approvazione HR.</p>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <label className="block text-sm font-medium text-gray-700">
                Dal
                <input className="form-control mt-1" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
              </label>
              <label className="block text-sm font-medium text-gray-700">
                Al
                <input className="form-control mt-1" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
              </label>
              <label className="block text-sm font-medium text-gray-700">
                Cerca
                <input className="form-control mt-1 w-56" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Nome, matricola, azienda" />
              </label>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
            <div className="rounded-2xl border border-violet-100 bg-violet-50 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-violet-600">Maturati</p>
              <p className="mt-2 text-2xl font-semibold text-violet-950">{dashboard?.matured_days_total ?? 0}</p>
            </div>
            <div className="rounded-2xl border border-fuchsia-100 bg-fuchsia-50 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-fuchsia-600">Fruiti</p>
              <p className="mt-2 text-2xl font-semibold text-fuchsia-950">{dashboard?.used_days_total ?? 0}</p>
            </div>
            <div className="rounded-2xl border border-sky-100 bg-sky-50 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-sky-600">Rettifiche</p>
              <p className="mt-2 text-2xl font-semibold text-sky-950">{dashboard?.manual_delta_days_total ?? 0}</p>
            </div>
            <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-emerald-600">Saldo</p>
              <p className="mt-2 text-2xl font-semibold text-emerald-950">{dashboard?.balance_days_total ?? 0}</p>
            </div>
            <div className="rounded-2xl border border-amber-100 bg-amber-50 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-amber-600">Da validare</p>
              <p className="mt-2 text-2xl font-semibold text-amber-950">{dashboard?.pending_validation_total ?? 0}</p>
            </div>
            <div className="rounded-2xl border border-orange-100 bg-orange-50 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-orange-600">Rettifiche in attesa</p>
              <p className="mt-2 text-2xl font-semibold text-orange-950">{dashboard?.pending_adjustments_total ?? 0}</p>
            </div>
            <div className="rounded-2xl border border-red-100 bg-red-50 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-red-600">Saldi negativi</p>
              <p className="mt-2 text-2xl font-semibold text-red-950">{dashboard?.negative_balance_total ?? 0}</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${negativeOnly ? "bg-red-600 text-white" : "bg-red-50 text-red-700"}`} type="button" onClick={() => setNegativeOnly((current) => !current)}>
              Solo saldi negativi
            </button>
            <button className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${pendingValidationOnly ? "bg-amber-600 text-white" : "bg-amber-50 text-amber-700"}`} type="button" onClick={() => setPendingValidationOnly((current) => !current)}>
              Solo da validare
            </button>
            <button className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${pendingAdjustmentsOnly ? "bg-orange-600 text-white" : "bg-orange-50 text-orange-700"}`} type="button" onClick={() => setPendingAdjustmentsOnly((current) => !current)}>
              Solo rettifiche in attesa
            </button>
            <button className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${manualAdjustmentsOnly ? "bg-sky-700 text-white" : "bg-sky-50 text-sky-700"}`} type="button" onClick={() => setManualAdjustmentsOnly((current) => !current)}>
              Solo con rettifiche manuali
            </button>
          </div>
        </article>

        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <article className="panel-card">
            <div className="mb-4">
              <p className="section-title">Collaboratori monitorati</p>
              <p className="section-copy">Clicca una riga per aprire dettaglio, cronologia e rettifiche manuali.</p>
            </div>
            {loading ? (
              <p className="text-sm text-gray-500">Caricamento dashboard recuperi...</p>
            ) : !dashboard || dashboard.items.length === 0 ? (
              <EmptyState icon={CheckIcon} title="Nessun movimento recuperi" description="Nel periodo selezionato non risultano recuperi maturati, fruiti o rettifiche manuali." />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-[0.14em] text-gray-500">
                      <th className="py-3 pr-4">Collaboratore</th>
                      <th className="py-3 pr-4">Maturati</th>
                      <th className="py-3 pr-4">Fruiti</th>
                      <th className="py-3 pr-4">Rettifiche</th>
                      <th className="py-3 pr-4">Saldo</th>
                      <th className="py-3 pr-4">Validazioni</th>
                      <th className="py-3">Workflow HR</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {dashboard.items.map((item) => {
                      const isSelected = item.collaborator_id === selectedCollaboratorId;
                      return (
                        <tr
                          key={item.collaborator_id}
                          onClick={() => setSelectedCollaboratorId(item.collaborator_id)}
                          className={`cursor-pointer transition ${isSelected ? "bg-[#eef7f0]" : "hover:bg-gray-50"}`}
                        >
                          <td className="py-3 pr-4">
                            <p className="font-medium text-gray-900">{item.collaborator_name}</p>
                            <p className="text-xs text-gray-500">{item.employee_code} · {getPresenzeCompanyLabel(null, item.company_code, "Globale")}</p>
                          </td>
                          <td className="py-3 pr-4 text-violet-800">{item.matured_days}</td>
                          <td className="py-3 pr-4 text-fuchsia-800">{item.used_days}</td>
                          <td className="py-3 pr-4 text-sky-800">
                            {item.manual_delta_days}
                            {item.manual_adjustment_count > 0 ? <span className="ml-2 text-xs text-sky-500">({item.manual_adjustment_count})</span> : null}
                          </td>
                          <td className={`py-3 pr-4 font-semibold ${item.balance_days < 0 ? "text-red-700" : "text-emerald-700"}`}>{item.balance_days}</td>
                          <td className="py-3 pr-4">
                            {item.pending_validation_count > 0 ? (
                              <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">{item.pending_validation_count} da validare</span>
                            ) : (
                              <span className="text-xs text-gray-400">Allineato</span>
                            )}
                          </td>
                          <td className="py-3">
                            {item.pending_adjustment_count > 0 ? (
                              <span className="rounded-full bg-orange-100 px-2.5 py-1 text-xs font-medium text-orange-800">{item.pending_adjustment_count} in attesa</span>
                            ) : item.last_adjustment_status ? (
                              <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${adjustmentStatusTone(item.last_adjustment_status)}`}>{adjustmentStatusLabel(item.last_adjustment_status)}</span>
                            ) : (
                              <span className="text-xs text-gray-400">Nessuna rettifica</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </article>

          <div className="space-y-6">
            <article className="panel-card">
              <div className="mb-4 flex items-start justify-between gap-4">
                <div>
                  <p className="section-title">{selectedItem?.collaborator_name ?? "Seleziona un collaboratore"}</p>
                  <p className="section-copy">
                    {selectedItem ? `${selectedItem.employee_code} · azienda ${selectedItem.company_code ?? "n/d"}` : "Apri una riga per vedere dettaglio saldi e cronologia."}
                  </p>
                </div>
                {selectedItem ? (
                  <Link href={`/presenze/collaboratori/${selectedItem.collaborator_id}`} className="btn-secondary">
                    Apri scheda
                  </Link>
                ) : null}
              </div>

              {selectedItem ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Saldo</p>
                    <p className={`mt-2 text-2xl font-semibold ${selectedItem.balance_days < 0 ? "text-red-700" : "text-emerald-700"}`}>{selectedItem.balance_days}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Validazioni pendenti</p>
                    <p className="mt-2 text-2xl font-semibold text-amber-900">{selectedItem.pending_validation_count}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Rettifiche in attesa</p>
                    <p className="mt-2 text-2xl font-semibold text-orange-900">{selectedItem.pending_adjustment_count}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Ultimo workflow HR</p>
                    <p className="mt-2 text-base font-semibold text-gray-900">{selectedItem.last_adjustment_status ? adjustmentStatusLabel(selectedItem.last_adjustment_status) : "—"}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Ultimo maturato</p>
                    <p className="mt-2 text-base font-semibold text-gray-900">{formatDateLabel(selectedItem.last_matured_date)}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Ultimo fruito</p>
                    <p className="mt-2 text-base font-semibold text-gray-900">{formatDateLabel(selectedItem.last_used_date)}</p>
                  </div>
                </div>
              ) : (
                <EmptyState icon={CheckIcon} title="Nessun collaboratore selezionato" description="Seleziona una riga dalla tabella per aprire il monitoraggio puntuale del saldo recuperi." />
              )}
            </article>

            <article className="panel-card">
              <div className="mb-4">
                <p className="section-title">Rettifica HR</p>
                <p className="section-copy">Usa questo form per carichi, scarichi o correzioni manuali. Ogni modifica entra in workflow e resta fuori saldo finché non viene approvata.</p>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block text-sm font-medium text-gray-700">
                  Data
                  <input className="form-control mt-1" type="date" value={form.adjustmentDate} onChange={(event) => setForm((current) => ({ ...current, adjustmentDate: event.target.value }))} />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Tipo
                  <select className="form-control mt-1" value={form.kind} onChange={(event) => setForm((current) => ({ ...current, kind: event.target.value as AdjustmentFormState["kind"] }))}>
                    <option value="correction">Correzione</option>
                    <option value="credit">Carico</option>
                    <option value="debit">Scarico</option>
                  </select>
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Delta giorni
                  <input className="form-control mt-1" value={form.deltaDays} onChange={(event) => setForm((current) => ({ ...current, deltaDays: event.target.value }))} placeholder="Es. 1 o -1" />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Motivo
                  <input className="form-control mt-1" value={form.reason} onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))} placeholder="Es. Allineamento verbale HR" />
                </label>
                <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                  Nota
                  <textarea className="form-control mt-1 min-h-24" value={form.note} onChange={(event) => setForm((current) => ({ ...current, note: event.target.value }))} />
                </label>
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <button className="btn-primary" type="button" disabled={saving || !selectedCollaboratorId} onClick={() => void handleSubmit()}>
                  {saving ? "Salvataggio..." : form.id ? "Aggiorna rettifica" : "Crea rettifica"}
                </button>
                {form.id ? (
                  <button className="btn-secondary" type="button" onClick={() => setForm(EMPTY_FORM)}>
                    Annulla modifica
                  </button>
                ) : null}
              </div>
            </article>

            <article className="panel-card">
              <div className="mb-4">
                <p className="section-title">Cronologia movimenti</p>
                <p className="section-copy">Movimenti derivati dai cartellini e rettifiche manuali nel periodo selezionato.</p>
              </div>
              {detailLoading ? (
                <p className="text-sm text-gray-500">Caricamento dettaglio...</p>
              ) : !selectedItem ? (
                <p className="text-sm text-gray-500">Seleziona un collaboratore per vedere la cronologia.</p>
              ) : (
                <div className="space-y-3">
                  {records.map((record) => (
                    <div key={record.id} className={`rounded-2xl border px-4 py-3 ${activityTone(record)}`}>
                      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                          <p className="font-medium">{record.work_date} · {activityLabel(record)}</p>
                          <p className="text-xs opacity-80">{record.request_description ?? record.detail_status ?? record.stato ?? "Movimento da cartellino giornaliero"}</p>
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs">
                          {record.grants_recovery_day ? <span className="rounded-full bg-white/70 px-2.5 py-1">credito {record.recovery_day_credit}</span> : null}
                          {record.uses_recovery_day ? <span className="rounded-full bg-white/70 px-2.5 py-1">debito {record.recovery_day_debit}</span> : null}
                          <span className="rounded-full bg-white/70 px-2.5 py-1">{record.validation_status === "validated" ? "validata" : "da validare"}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {adjustments.map((item) => (
                    <div key={item.id} className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3">
                      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                          <p className="font-medium text-sky-950">{item.adjustment_date} · rettifica HR {item.delta_days > 0 ? `+${item.delta_days}` : item.delta_days}</p>
                          <p className="text-xs text-sky-800">
                            {item.reason}
                            {item.note ? ` · ${item.note}` : ""}
                            {item.approval_note ? ` · revisione: ${item.approval_note}` : ""}
                          </p>
                          <p className="mt-1 text-[11px] text-sky-700">
                            creata da {item.created_by_label ?? "n/d"} il {formatDateTimeLabel(item.created_at)}
                            {item.updated_at !== item.created_at ? ` · aggiornata da ${item.updated_by_label ?? "n/d"} il ${formatDateTimeLabel(item.updated_at)}` : ""}
                            {item.reviewed_at ? ` · revisionata da ${item.reviewed_by_label ?? "n/d"} il ${formatDateTimeLabel(item.reviewed_at)}` : ""}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <span className={`rounded-full px-2.5 py-2 text-xs font-medium ${adjustmentStatusTone(item.approval_status)}`}>{adjustmentStatusLabel(item.approval_status)}</span>
                          {item.approval_status !== "approved" ? (
                            <button className="btn-secondary" type="button" disabled={saving} onClick={() => void handleReview(item.id, "approved")}>
                              Approva
                            </button>
                          ) : null}
                          {item.approval_status !== "rejected" ? (
                            <button className="btn-secondary" type="button" disabled={saving} onClick={() => void handleReview(item.id, "rejected")}>
                              Respingi
                            </button>
                          ) : null}
                          <button
                            className="btn-secondary"
                            type="button"
                            onClick={() =>
                              setForm({
                                id: item.id,
                                adjustmentDate: item.adjustment_date,
                                deltaDays: String(item.delta_days),
                                kind: item.kind,
                                reason: item.reason,
                                note: item.note ?? "",
                              })
                            }
                          >
                            Modifica
                          </button>
                          <button
                            className="rounded-2xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50"
                            type="button"
                            disabled={deletingId === item.id}
                            onClick={() => void handleDelete(item.id)}
                          >
                            {deletingId === item.id ? "Eliminazione..." : "Elimina"}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                  {records.length === 0 && adjustments.length === 0 ? (
                    <p className="text-sm text-gray-500">Nessun movimento o rettifica nel periodo selezionato.</p>
                  ) : null}
                </div>
              )}
            </article>
          </div>
        </div>
      </div>
    </ProtectedPage>
  );
}
