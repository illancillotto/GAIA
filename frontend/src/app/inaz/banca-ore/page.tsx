"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { EmptyState } from "@/components/ui/empty-state";
import { CheckIcon, DocumentIcon } from "@/components/ui/icons";
import {
  createPresenzeBankHoursAdjustment,
  deletePresenzeBankHoursAdjustment,
  getPresenzeBankHoursCollaboratorDetail,
  getPresenzeBankHoursDashboard,
  reviewPresenzeBankHoursAdjustment,
  updatePresenzeBankHoursAdjustment,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { getPresenzeCompanyLabel } from "@/lib/inaz-display";
import type {
  PresenzeBankHoursAdjustment,
  PresenzeBankHoursCollaboratorDetailResponse,
  PresenzeBankHoursDashboardResponse,
  PresenzeCollaborator,
} from "@/types/api";

type AdjustmentFormState = {
  id: string | null;
  adjustmentDate: string;
  kind: "credit" | "debit" | "liquidation" | "correction";
  deltaHours: string;
  reason: string;
  note: string;
};

const EMPTY_FORM: AdjustmentFormState = {
  id: null,
  adjustmentDate: "",
  kind: "correction",
  deltaHours: "",
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

function formatMinutes(value: number | null | undefined): string {
  if (value == null) return "0h";
  const sign = value < 0 ? "-" : "";
  const absolute = Math.abs(value);
  const hours = Math.floor(absolute / 60);
  const minutes = absolute % 60;
  return `${sign}${hours}h${minutes === 0 ? "" : ` ${String(minutes).padStart(2, "0")}m`}`;
}

function formatStandardDailyMinutes(minutes: number | null | undefined): string {
  if (minutes == null) return "—";
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return `${hours}:${String(remainder).padStart(2, "0")}`;
}

function formatContractKind(value: PresenzeCollaborator["contract_kind"] | null | undefined): string {
  if (!value) return "Profilo non definito";
  const labels: Record<NonNullable<PresenzeCollaborator["contract_kind"]>, string> = {
    operaio: "Operaio",
    impiegato: "Impiegato",
    quadro: "Quadro",
    altro: "Altro",
  };
  return labels[value] ?? value;
}

function formatStandardDays(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(2)} gg`;
}

function contractProfileSourceLabel(value: PresenzeBankHoursDashboardResponse["items"][number]["contract_profile_source"] | PresenzeBankHoursCollaboratorDetailResponse["contract_profile_source"]): string {
  if (value === "explicit") return "profilo manuale";
  if (value === "derived") return "profilo derivato";
  return "profilo mancante";
}

function buildSuggestedLiquidationReason(detail: PresenzeBankHoursCollaboratorDetailResponse): string {
  const label = detail.date_from && detail.date_to
    ? `Liquidazione guidata ${detail.date_from} / ${detail.date_to}`
    : "Liquidazione guidata banca ore";
  return label;
}

function adjustmentStatusTone(status: PresenzeBankHoursAdjustment["approval_status"]): string {
  if (status === "approved") return "bg-emerald-100 text-emerald-800";
  if (status === "rejected") return "bg-rose-100 text-rose-800";
  return "bg-amber-100 text-amber-800";
}

function adjustmentStatusLabel(status: PresenzeBankHoursAdjustment["approval_status"]): string {
  if (status === "approved") return "Approvata";
  if (status === "rejected") return "Respinta";
  return "In attesa";
}

function adjustmentKindLabel(kind: AdjustmentFormState["kind"]): string {
  if (kind === "credit") return "Carico";
  if (kind === "debit") return "Scarico";
  if (kind === "liquidation") return "Liquidazione";
  return "Correzione";
}

function parseDeltaMinutes(kind: AdjustmentFormState["kind"], value: string): number | null {
  const normalized = value.replace(",", ".").trim();
  if (!normalized) return null;
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed) || parsed === 0) return null;
  const minutes = Math.round(parsed * 60);
  if (kind === "credit") return Math.abs(minutes);
  if (kind === "debit" || kind === "liquidation") return -Math.abs(minutes);
  return minutes;
}

export default function PresenzeBankHoursPage() {
  const initialBounds = currentYearBounds();
  const [dashboard, setDashboard] = useState<PresenzeBankHoursDashboardResponse | null>(null);
  const [detail, setDetail] = useState<PresenzeBankHoursCollaboratorDetailResponse | null>(null);
  const [dateFrom, setDateFrom] = useState(initialBounds.start);
  const [dateTo, setDateTo] = useState(initialBounds.end);
  const [searchTerm, setSearchTerm] = useState("");
  const [negativeOnly, setNegativeOnly] = useState(false);
  const [pendingAdjustmentsOnly, setPendingAdjustmentsOnly] = useState(false);
  const [manualAdjustmentsOnly, setManualAdjustmentsOnly] = useState(false);
  const [selectedCollaboratorId, setSelectedCollaboratorId] = useState<string>("");
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
      const nextDashboard = await getPresenzeBankHoursDashboard(token, {
        dateFrom,
        dateTo,
        q: searchTerm.trim() || undefined,
        negativeOnly,
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
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento dashboard banca ore");
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, manualAdjustmentsOnly, negativeOnly, pendingAdjustmentsOnly, searchTerm]);

  const loadDetail = useCallback(async (collaboratorId: string) => {
    const token = getStoredAccessToken();
    if (!token || !collaboratorId) return;
    setDetailLoading(true);
    try {
      const response = await getPresenzeBankHoursCollaboratorDetail(token, collaboratorId, { dateFrom, dateTo });
      setDetail(response);
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : "Errore caricamento dettaglio banca ore");
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
      setDetail(null);
      return;
    }
    void loadDetail(selectedCollaboratorId);
  }, [loadDetail, selectedCollaboratorId]);

  async function handleSubmit() {
    const token = getStoredAccessToken();
    if (!token || !selectedCollaboratorId) return;
    const deltaMinutes = parseDeltaMinutes(form.kind, form.deltaHours);
    if (!form.adjustmentDate || !form.reason.trim() || deltaMinutes == null) {
      setError("Compila data, tipo, delta ore e motivo.");
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const payload = {
        adjustment_date: form.adjustmentDate,
        delta_minutes: deltaMinutes,
        kind: form.kind,
        reason: form.reason.trim(),
        note: form.note.trim() || null,
      };
      if (form.id == null) {
        await createPresenzeBankHoursAdjustment(token, { collaborator_id: selectedCollaboratorId, ...payload });
        setSuccess("Rettifica banca ore creata.");
      } else {
        await updatePresenzeBankHoursAdjustment(token, form.id, payload);
        setSuccess("Rettifica banca ore aggiornata.");
      }
      setForm(EMPTY_FORM);
      await Promise.all([loadDashboard(), loadDetail(selectedCollaboratorId)]);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Errore salvataggio rettifica banca ore");
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
      await reviewPresenzeBankHoursAdjustment(token, adjustmentId, {
        approval_status: approvalStatus,
        approval_note: approvalStatus === "approved" ? "Verificata da HR." : "Da rivedere da HR.",
      });
      setSuccess(approvalStatus === "approved" ? "Rettifica approvata." : "Rettifica respinta.");
      await Promise.all([loadDashboard(), loadDetail(selectedCollaboratorId)]);
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "Errore revisione rettifica banca ore");
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
      await deletePresenzeBankHoursAdjustment(token, adjustmentId);
      if (form.id === adjustmentId) {
        setForm(EMPTY_FORM);
      }
      setSuccess("Rettifica eliminata.");
      await Promise.all([loadDashboard(), loadDetail(selectedCollaboratorId)]);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione rettifica banca ore");
    } finally {
      setDeletingId(null);
    }
  }

  function applyLiquidationGuidance() {
    if (!detail) return;
    const suggestedMinutes = detail.liquidation_guidance.suggested_minutes;
    if (suggestedMinutes <= 0) {
      setError("Nel periodo selezionato non risultano minuti liquidabili da precompilare.");
      return;
    }
    setError(null);
    setSuccess("Liquidazione guidata caricata nel form.");
    setForm((current) => ({
      ...current,
      id: null,
      adjustmentDate: dateTo,
      kind: "liquidation",
      deltaHours: String(suggestedMinutes / 60),
      reason: buildSuggestedLiquidationReason(detail),
      note: detail.liquidation_guidance.notes.join(" "),
    }));
  }

  return (
    <ProtectedPage
      title="Banca Ore"
      description="Cruscotto HR per saldo importato, liquidazioni e rettifiche manuali della banca ore."
      breadcrumb="Giornaliere"
      requiredModule="inaz"
      requiredRoles={["hr_manager", "admin", "super_admin"]}
    >
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <article className="panel-card space-y-5 overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(13,148,136,0.12),_transparent_38%),radial-gradient(circle_at_top_right,_rgba(251,191,36,0.14),_transparent_34%),#ffffff]">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="section-title">Controllo banca ore</p>
              <p className="section-copy">Saldo importato dai riepiloghi INAZ, piu workflow GAIA per carichi, scarichi, liquidazioni e correzioni HR.</p>
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

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <div className="rounded-2xl border border-teal-100 bg-teal-50/80 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-teal-700">Saldo importato</p>
              <p className="mt-2 text-2xl font-semibold text-teal-950">{formatMinutes(dashboard?.imported_balance_total_minutes)}</p>
            </div>
            <div className="rounded-2xl border border-sky-100 bg-sky-50/80 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-sky-700">Rettifiche approvate</p>
              <p className="mt-2 text-2xl font-semibold text-sky-950">{formatMinutes(dashboard?.approved_adjustment_total_minutes)}</p>
            </div>
            <div className="rounded-2xl border border-emerald-100 bg-emerald-50/80 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-emerald-700">Saldo effettivo</p>
              <p className="mt-2 text-2xl font-semibold text-emerald-950">{formatMinutes(dashboard?.effective_balance_total_minutes)}</p>
            </div>
            <div className="rounded-2xl border border-amber-100 bg-amber-50/80 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-amber-700">Liquidato</p>
              <p className="mt-2 text-2xl font-semibold text-amber-950">{formatMinutes(dashboard?.liquidation_total_minutes)}</p>
            </div>
            <div className="rounded-2xl border border-rose-100 bg-rose-50/80 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-rose-700">Workflow critico</p>
              <p className="mt-2 text-2xl font-semibold text-rose-950">{dashboard?.pending_adjustments_total ?? 0} in attesa · {dashboard?.negative_balance_total ?? 0} negativi</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${negativeOnly ? "bg-rose-600 text-white" : "bg-rose-50 text-rose-700"}`} type="button" onClick={() => setNegativeOnly((current) => !current)}>
              Solo saldi negativi
            </button>
            <button className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${pendingAdjustmentsOnly ? "bg-amber-600 text-white" : "bg-amber-50 text-amber-700"}`} type="button" onClick={() => setPendingAdjustmentsOnly((current) => !current)}>
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
              <p className="section-title">Saldo per collaboratore</p>
              <p className="section-copy">Apri una riga per vedere l’ultimo snapshot INAZ, il saldo effettivo e il workflow manuale GAIA.</p>
            </div>
            {loading ? (
              <p className="text-sm text-gray-500">Caricamento dashboard banca ore...</p>
            ) : !dashboard || dashboard.items.length === 0 ? (
              <EmptyState icon={DocumentIcon} title="Nessun saldo banca ore" description="Nel periodo selezionato non risultano snapshot banca ore o rettifiche manuali." />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-[0.14em] text-gray-500">
                      <th className="py-3 pr-4">Collaboratore</th>
                      <th className="py-3 pr-4">Importato</th>
                      <th className="py-3 pr-4">Rettifiche</th>
                      <th className="py-3 pr-4">Effettivo</th>
                      <th className="py-3 pr-4">Liquidato</th>
                      <th className="py-3">Workflow</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {dashboard.items.map((item) => {
                      const isSelected = item.collaborator_id === selectedCollaboratorId;
                      return (
                        <tr
                          key={item.collaborator_id}
                          onClick={() => setSelectedCollaboratorId(item.collaborator_id)}
                          className={`cursor-pointer transition ${isSelected ? "bg-[#eef9f7]" : "hover:bg-gray-50"}`}
                        >
                          <td className="py-3 pr-4">
                            <p className="font-medium text-gray-900">{item.collaborator_name}</p>
                            <p className="text-xs text-gray-500">{item.employee_code} · {getPresenzeCompanyLabel(null, item.company_code, "Globale")}</p>
                            <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                              <span className="rounded-full bg-gray-100 px-2.5 py-1 text-gray-700">{formatContractKind(item.contract_kind)}</span>
                              <span className="rounded-full bg-cyan-50 px-2.5 py-1 text-cyan-700">Std {formatStandardDailyMinutes(item.standard_daily_minutes)}</span>
                              <span className={`rounded-full px-2.5 py-1 ${item.contract_profile_source === "missing" ? "bg-rose-50 text-rose-700" : "bg-emerald-50 text-emerald-700"}`}>
                                {contractProfileSourceLabel(item.contract_profile_source)}
                              </span>
                            </div>
                          </td>
                          <td className="py-3 pr-4 text-teal-800">{formatMinutes(item.imported_balance_minutes)}</td>
                          <td className="py-3 pr-4 text-sky-800">{formatMinutes(item.approved_adjustment_minutes)}</td>
                          <td className={`py-3 pr-4 font-semibold ${item.effective_balance_minutes < 0 ? "text-rose-700" : "text-emerald-700"}`}>{formatMinutes(item.effective_balance_minutes)}</td>
                          <td className="py-3 pr-4 text-amber-800">{formatMinutes(item.liquidation_minutes_total)}</td>
                          <td className="py-3">
                            {item.pending_adjustment_count > 0 ? (
                              <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">{item.pending_adjustment_count} in attesa</span>
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
                  <p className="section-title">{detail?.collaborator.name ?? "Seleziona un collaboratore"}</p>
                  <p className="section-copy">
                    {detail ? `${detail.collaborator.employee_code} · ${getPresenzeCompanyLabel(detail.collaborator.company_label, detail.collaborator.company_code, "Globale")}` : "Apri una riga per vedere snapshot giornaliere, saldo disponibile e workflow manuale."}
                  </p>
                </div>
                {detail ? (
                  <Link href={`/presenze/collaboratori/${detail.collaborator.id}`} className="btn-secondary">
                    Apri scheda
                  </Link>
                ) : null}
              </div>

              {detailLoading ? (
                <p className="text-sm text-gray-500">Caricamento dettaglio banca ore...</p>
              ) : !detail ? (
                <EmptyState icon={CheckIcon} title="Nessun collaboratore selezionato" description="Seleziona una riga dalla tabella per aprire il monitoraggio puntuale della banca ore." />
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-teal-100 bg-teal-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-teal-700">Saldo importato INAZ</p>
                    <p className="mt-2 text-2xl font-semibold text-teal-950">{formatMinutes(detail.imported_balance_minutes)}</p>
                  </div>
                  <div className="rounded-2xl border border-sky-100 bg-sky-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-sky-700">Rettifiche approvate</p>
                    <p className="mt-2 text-2xl font-semibold text-sky-950">{formatMinutes(detail.approved_adjustment_minutes)}</p>
                  </div>
                  <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-emerald-700">Saldo effettivo</p>
                    <p className={`mt-2 text-2xl font-semibold ${detail.effective_balance_minutes < 0 ? "text-rose-700" : "text-emerald-950"}`}>{formatMinutes(detail.effective_balance_minutes)}</p>
                  </div>
                  <div className="rounded-2xl border border-amber-100 bg-amber-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-amber-700">Disponibile a scarico</p>
                    <p className="mt-2 text-2xl font-semibold text-amber-950">{formatMinutes(detail.available_debit_minutes)}</p>
                    <p className="mt-2 text-xs text-amber-800">Equivalente standard: {formatStandardDays(detail.available_debit_days)}</p>
                  </div>
                </div>
              )}
            </article>

            <article className="panel-card">
              <div className="mb-4">
                <p className="section-title">Rettifica / liquidazione</p>
                <p className="section-copy">Gli scarichi e le liquidazioni non possono andare oltre il saldo disponibile alla data del movimento. Le modifiche entrano in saldo solo dopo approvazione HR.</p>
              </div>
              {detail ? (
                <div className="mb-4 grid gap-3 rounded-2xl border border-gray-100 bg-gray-50 p-4 md:grid-cols-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.14em] text-gray-400">Profilo contrattuale</p>
                    <p className="mt-1 text-sm font-semibold text-gray-900">{formatContractKind(detail.collaborator.contract_kind)}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.14em] text-gray-400">Orario standard</p>
                    <p className="mt-1 text-sm font-semibold text-gray-900">{formatStandardDailyMinutes(detail.collaborator.standard_daily_minutes)}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.14em] text-gray-400">Qualita profilo</p>
                    <p className={`mt-1 text-sm font-semibold ${detail.contract_profile_source === "missing" ? "text-rose-700" : "text-emerald-700"}`}>
                      {contractProfileSourceLabel(detail.contract_profile_source)}
                    </p>
                  </div>
                </div>
              ) : null}
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block text-sm font-medium text-gray-700">
                  Data
                  <input className="form-control mt-1" type="date" value={form.adjustmentDate} onChange={(event) => setForm((current) => ({ ...current, adjustmentDate: event.target.value }))} />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Tipo
                  <select className="form-control mt-1" value={form.kind} onChange={(event) => setForm((current) => ({ ...current, kind: event.target.value as AdjustmentFormState["kind"] }))}>
                    <option value="credit">Carico</option>
                    <option value="debit">Scarico</option>
                    <option value="liquidation">Liquidazione</option>
                    <option value="correction">Correzione</option>
                  </select>
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Ore
                  <input className="form-control mt-1" value={form.deltaHours} onChange={(event) => setForm((current) => ({ ...current, deltaHours: event.target.value }))} placeholder="Es. 3.5 oppure -1.25 per correzione" />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Motivo
                  <input className="form-control mt-1" value={form.reason} onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))} placeholder="Es. Liquidazione straordinario aprile" />
                </label>
                <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                  Nota
                  <textarea className="form-control mt-1 min-h-24" value={form.note} onChange={(event) => setForm((current) => ({ ...current, note: event.target.value }))} />
                </label>
              </div>
              <div className="mt-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-600">
                Tipo attivo: <span className="font-medium text-gray-900">{adjustmentKindLabel(form.kind)}</span>
                {detail ? <span className="ml-3">Disponibile: <span className="font-medium text-gray-900">{formatMinutes(detail.available_debit_minutes)}</span></span> : null}
                {detail ? <span className="ml-3">Giorni equivalenti: <span className="font-medium text-gray-900">{formatStandardDays(detail.available_debit_days)}</span></span> : null}
              </div>
              {detail ? (
                <div className={`mt-3 rounded-2xl border px-4 py-3 text-sm ${detail.liquidation_guidance.requires_profile_review ? "border-amber-200 bg-amber-50 text-amber-800" : "border-sky-100 bg-sky-50 text-sky-800"}`}>
                  <p className="font-medium">Liquidazione guidata</p>
                  <p className="mt-1">
                    Candidato da straordinario: <span className="font-semibold">{formatMinutes(detail.liquidation_guidance.candidate_minutes_from_overtime)}</span>
                    {" · "}
                    Proposta: <span className="font-semibold">{formatMinutes(detail.liquidation_guidance.suggested_minutes)}</span>
                    {" · "}
                    Giorni standard: <span className="font-semibold">{formatStandardDays(detail.liquidation_guidance.suggested_days)}</span>
                  </p>
                  <p className="mt-2 text-xs">
                    Bucket inclusi: <span className="font-semibold">{detail.liquidation_guidance.included_overtime_buckets.join(", ") || "nessuno"}</span>
                    {" · "}
                    Profilo derivato liquidabile: <span className="font-semibold">{detail.liquidation_guidance.allow_derived_profile ? "si" : "no"}</span>
                    {" · "}
                    Soglia minima: <span className="font-semibold">{formatMinutes(detail.liquidation_guidance.min_suggested_minutes)}</span>
                  </p>
                  <div className="mt-3 grid gap-3 md:grid-cols-3">
                    <div className="rounded-xl bg-white/70 px-3 py-2">
                      <p className="text-[11px] uppercase tracking-[0.14em]">Liquidabile</p>
                      <p className="mt-1 font-semibold">{formatMinutes(detail.liquidation_guidance.liquidable_minutes)}</p>
                    </div>
                    <div className="rounded-xl bg-white/70 px-3 py-2">
                      <p className="text-[11px] uppercase tracking-[0.14em]">Resta in banca ore</p>
                      <p className="mt-1 font-semibold">{formatMinutes(detail.liquidation_guidance.keep_in_bank_minutes)}</p>
                    </div>
                    <div className="rounded-xl bg-white/70 px-3 py-2">
                      <p className="text-[11px] uppercase tracking-[0.14em]">Da revisione HR</p>
                      <p className="mt-1 font-semibold">{formatMinutes(detail.liquidation_guidance.review_minutes)}</p>
                    </div>
                  </div>
                  {detail.liquidation_guidance.notes.map((note) => (
                    <p key={note} className="mt-1">{note}</p>
                  ))}
                </div>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-3">
                <button className="btn-primary" type="button" disabled={saving || !selectedCollaboratorId} onClick={() => void handleSubmit()}>
                  {saving ? "Salvataggio..." : form.id ? "Aggiorna movimento" : "Crea movimento"}
                </button>
                {detail ? (
                  <button className="btn-secondary" type="button" disabled={saving || detail.liquidation_guidance.suggested_minutes <= 0} onClick={applyLiquidationGuidance}>
                    Proponi liquidazione
                  </button>
                ) : null}
                {form.id ? (
                  <button className="btn-secondary" type="button" onClick={() => setForm(EMPTY_FORM)}>
                    Annulla modifica
                  </button>
                ) : null}
              </div>
            </article>

            <article className="panel-card">
              <div className="mb-4">
                <p className="section-title">Quadro CCNL periodo</p>
                <p className="section-copy">Contesto contrattuale del periodo selezionato: notturno, festivo, straordinario e soglia mensile Art. 82.</p>
              </div>
              {!detail ? (
                <p className="text-sm text-gray-500">Seleziona un collaboratore per vedere il riepilogo CCNL del periodo.</p>
              ) : (
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Notturno totale</p>
                      <p className="mt-2 text-2xl font-semibold text-slate-950">{formatMinutes(detail.compensation_summary.night_minutes_total)}</p>
                    </div>
                    <div className="rounded-2xl border border-indigo-100 bg-indigo-50 p-4">
                      <p className="text-xs uppercase tracking-[0.16em] text-indigo-600">Straord. diurno</p>
                      <p className="mt-2 text-2xl font-semibold text-indigo-950">{formatMinutes(detail.compensation_summary.overtime_day_minutes_total)}</p>
                    </div>
                    <div className="rounded-2xl border border-fuchsia-100 bg-fuchsia-50 p-4">
                      <p className="text-xs uppercase tracking-[0.16em] text-fuchsia-600">Straord. notturno</p>
                      <p className="mt-2 text-2xl font-semibold text-fuchsia-950">{formatMinutes(detail.compensation_summary.overtime_night_minutes_total)}</p>
                    </div>
                    <div className="rounded-2xl border border-orange-100 bg-orange-50 p-4">
                      <p className="text-xs uppercase tracking-[0.16em] text-orange-600">Straord. fest. nott.</p>
                      <p className="mt-2 text-2xl font-semibold text-orange-950">{formatMinutes(detail.compensation_summary.overtime_festive_night_minutes_total)}</p>
                    </div>
                  </div>
                  <div className="grid gap-3 rounded-2xl border border-gray-100 bg-gray-50 p-4 md:grid-cols-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.14em] text-gray-400">Notti nel periodo</p>
                      <p className="mt-1 text-sm font-semibold text-gray-900">{detail.compensation_summary.night_shift_days_total}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.14em] text-gray-400">Picco mensile notti</p>
                      <p className="mt-1 text-sm font-semibold text-gray-900">{detail.compensation_summary.max_monthly_night_shift_count}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.14em] text-gray-400">Bonus Art. 82</p>
                      <p className={`mt-1 text-sm font-semibold ${detail.compensation_summary.ordinary_night_bonus_threshold_met ? "text-emerald-700" : "text-amber-700"}`}>
                        {detail.compensation_summary.ordinary_night_bonus_rate ? `${detail.compensation_summary.ordinary_night_bonus_rate}%` : "non applicabile"}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </article>

            <article className="panel-card">
              <div className="mb-4">
                <p className="section-title">Timeline banca ore</p>
                <p className="section-copy">Snapshot mensili importati da INAZ e workflow rettifiche nello stesso intervallo.</p>
              </div>
              {detailLoading ? (
                <p className="text-sm text-gray-500">Caricamento timeline...</p>
              ) : !detail ? (
                <p className="text-sm text-gray-500">Seleziona un collaboratore per vedere snapshot e rettifiche.</p>
              ) : (
                <div className="space-y-4">
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="mb-3 text-xs uppercase tracking-[0.16em] text-gray-400">Snapshot INAZ</p>
                    {detail.snapshots.length === 0 ? (
                      <p className="text-sm text-gray-500">Nessuno snapshot banca ore nel periodo selezionato.</p>
                    ) : (
                      <div className="space-y-3">
                        {detail.snapshots.map((item) => (
                          <div key={`${item.period_start}-${item.period_end}`} className="rounded-2xl border border-white bg-white px-4 py-3">
                            <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                              <div>
                                <p className="font-medium text-gray-900">{formatDateLabel(item.period_start)} → {formatDateLabel(item.period_end)}</p>
                                <p className="text-xs text-gray-500">{item.description}</p>
                              </div>
                              <div className="flex flex-wrap gap-2 text-xs text-gray-700">
                                <span className="rounded-full bg-teal-50 px-2.5 py-1">Prec. {formatMinutes(item.residuo_prec_minutes)}</span>
                                <span className="rounded-full bg-emerald-50 px-2.5 py-1">Maturato {formatMinutes(item.spettante_minutes)}</span>
                                <span className="rounded-full bg-amber-50 px-2.5 py-1">Fruito {formatMinutes(item.fruito_minutes)}</span>
                                <span className="rounded-full bg-sky-50 px-2.5 py-1">Saldo {formatMinutes(item.saldo_totale_minutes)}</span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="mb-3 text-xs uppercase tracking-[0.16em] text-gray-400">Workflow manuale</p>
                    {detail.adjustments.length === 0 ? (
                      <p className="text-sm text-gray-500">Nessuna rettifica o liquidazione nel periodo selezionato.</p>
                    ) : (
                      <div className="space-y-3">
                        {detail.adjustments.map((item) => (
                          <div key={item.id} className="rounded-2xl border border-white bg-white px-4 py-3">
                            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                              <div>
                                <p className="font-medium text-gray-900">{item.adjustment_date} · {adjustmentKindLabel(item.kind)}</p>
                                <p className={`mt-1 text-sm font-semibold ${item.delta_minutes < 0 ? "text-rose-700" : "text-emerald-700"}`}>{formatMinutes(item.delta_minutes)}</p>
                                <p className="mt-1 text-sm text-gray-600">{item.reason}</p>
                                {item.note ? <p className="mt-1 text-sm text-gray-500">{item.note}</p> : null}
                                <p className="mt-2 text-xs text-gray-400">Creata da {item.created_by_label ?? "sistema"} · {formatDateTimeLabel(item.created_at)}</p>
                              </div>
                              <div className="flex flex-wrap gap-2">
                                <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${adjustmentStatusTone(item.approval_status)}`}>{adjustmentStatusLabel(item.approval_status)}</span>
                                <button
                                  className="btn-secondary text-xs"
                                  type="button"
                                  onClick={() =>
                                    setForm({
                                      id: item.id,
                                      adjustmentDate: item.adjustment_date,
                                      kind: item.kind,
                                      deltaHours: String(item.delta_minutes / 60),
                                      reason: item.reason,
                                      note: item.note ?? "",
                                    })
                                  }
                                >
                                  Modifica
                                </button>
                                {item.approval_status === "pending" ? (
                                  <>
                                    <button className="btn-secondary text-xs" type="button" disabled={saving} onClick={() => void handleReview(item.id, "approved")}>
                                      Approva
                                    </button>
                                    <button className="btn-secondary text-xs" type="button" disabled={saving} onClick={() => void handleReview(item.id, "rejected")}>
                                      Respinge
                                    </button>
                                  </>
                                ) : null}
                                <button className="btn-secondary text-xs" type="button" disabled={deletingId === item.id} onClick={() => void handleDelete(item.id)}>
                                  {deletingId === item.id ? "Eliminazione..." : "Elimina"}
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </article>
          </div>
        </div>
      </div>
    </ProtectedPage>
  );
}
