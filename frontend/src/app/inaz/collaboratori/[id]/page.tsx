"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import {
  createInazCollaboratorScheduleAssignment,
  deleteInazScheduleAssignment,
  getCurrentUser,
  getInazCollaboratorCalendar,
  getInazCollaboratorSummary,
  listAllApplicationUsers,
  listAllInazCollaborators,
  listInazCollaboratorScheduleAssignments,
  listInazScheduleTemplates,
  mapInazCollaboratorApplicationUser,
  updateInazDailyRecord,
} from "@/lib/api";
import {
  notifyInazCollaboratorDetailUpdated,
  scoreInazCollaboratorUserMatch,
  usersForInazCollaboratorMappingSorted,
} from "@/lib/inaz-collaborator-mapping";
import { getStoredAccessToken } from "@/lib/auth";
import type { ApplicationUser, CurrentUser, InazCollaborator, InazCollaboratorScheduleAssignment, InazDailyRecord, InazEventSummary, InazScheduleTemplate } from "@/types/api";

type TabKey = "calendar" | "summary";

function currentMonthBounds(): { start: string; end: string } {
  const now = new Date();
  const start = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
  const end = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()).padStart(2, "0")}`;
  return { start, end };
}

function formatHours(minutes: number | null): string {
  if (minutes == null) return "—";
  return `${(minutes / 60).toFixed(2)} h`;
}

function formatAbsenceCause(cause: string | null | undefined): string {
  if (!cause) return "—";
  const labels: Record<string, string> = {
    ferie: "Ferie",
    permesso: "Permesso",
    malattia: "Malattia",
    riposo: "Riposo",
    festivita: "Festivita",
    banca_ore: "Banca ore",
    assenza_da_giustificare: "Assenza da giustificare",
  };
  return labels[cause] ?? cause.replaceAll("_", " ");
}

function formatRequestDescription(value: string | null | undefined): string {
  if (!value) return "—";
  if (value.includes(" - ")) {
    const [, right] = value.split(" - ", 2);
    if (right?.trim()) return right.trim();
  }
  return value;
}

function requestBadgeLabel(record: InazDailyRecord): string | null {
  if (record.resolved_absence_cause) {
    return formatAbsenceCause(record.resolved_absence_cause);
  }
  if (record.request_description) {
    return formatRequestDescription(record.request_description);
  }
  return null;
}

function formatPunchTerminalLabel(value: string | null | undefined): string | null {
  if (!value) return null;
  if (value.includes("-")) {
    const [, right] = value.split("-", 2);
    if (right?.trim()) return right.trim();
  }
  return value;
}

function formatDetailEntries(values: Record<string, string>): Array<[string, string]> {
  return Object.entries(values);
}

export default function InazCollaboratoreDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const collaboratorId = params.id as string;
  const isEmbedded = searchParams.get("embedded") === "1";
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [users, setUsers] = useState<ApplicationUser[]>([]);
  const [allCollaborators, setAllCollaborators] = useState<InazCollaborator[]>([]);
  const [collaborator, setCollaborator] = useState<InazCollaborator | null>(null);
  const [records, setRecords] = useState<InazDailyRecord[]>([]);
  const [summary, setSummary] = useState<InazEventSummary[]>([]);
  const [templates, setTemplates] = useState<InazScheduleTemplate[]>([]);
  const [assignments, setAssignments] = useState<InazCollaboratorScheduleAssignment[]>([]);
  const [tab, setTab] = useState<TabKey>("calendar");
  const [dateFrom, setDateFrom] = useState(currentMonthBounds().start);
  const [dateTo, setDateTo] = useState(currentMonthBounds().end);
  const [mappingValue, setMappingValue] = useState("");
  const [assignmentTemplateId, setAssignmentTemplateId] = useState("");
  const [assignmentValidFrom, setAssignmentValidFrom] = useState("");
  const [assignmentValidTo, setAssignmentValidTo] = useState("");
  const [assignmentNotes, setAssignmentNotes] = useState("");
  const [dailyOverrides, setDailyOverrides] = useState<Record<string, { km_value: string; override_straordinario_minutes: string; override_mpe_minutes: string; manual_note: string }>>({});
  const [error, setError] = useState<string | null>(null);
  const [mappingNotice, setMappingNotice] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const [savingMapping, setSavingMapping] = useState(false);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || !collaboratorId) return;
    getCurrentUser(token)
      .then((sessionUser) =>
        Promise.all([
          Promise.resolve(sessionUser),
          sessionUser.role === "admin" || sessionUser.role === "super_admin"
            ? listAllApplicationUsers(token)
            : Promise.resolve([]),
          listAllInazCollaborators(token),
          getInazCollaboratorCalendar(token, collaboratorId, dateFrom, dateTo),
          getInazCollaboratorSummary(token, collaboratorId, dateFrom, dateTo),
          sessionUser.role === "admin" || sessionUser.role === "super_admin"
            ? listInazScheduleTemplates(token)
            : Promise.resolve([]),
          sessionUser.role === "admin" || sessionUser.role === "super_admin"
            ? listInazCollaboratorScheduleAssignments(token, collaboratorId)
            : Promise.resolve([]),
        ]),
      )
      .then(([sessionUser, userItems, collaboratorItems, calendarResponse, summaryResponse, templatesResponse, assignmentsResponse]) => {
        setCurrentUser(sessionUser);
        setUsers(userItems);
        setAllCollaborators(collaboratorItems);
        setCollaborator(
          collaboratorItems.find((item) => item.id === collaboratorId) ?? calendarResponse.collaborator,
        );
        setRecords(calendarResponse.items);
        setSummary(summaryResponse.items);
        setTemplates(templatesResponse);
        setAssignments(assignmentsResponse);
        setMappingValue(String((collaboratorItems.find((item) => item.id === collaboratorId) ?? calendarResponse.collaborator).application_user_id ?? ""));
        setDailyOverrides(
          Object.fromEntries(
            calendarResponse.items.map((record) => [
              record.id,
              {
                km_value: record.km_value != null ? String(record.km_value) : "",
                override_straordinario_minutes:
                  record.override_straordinario_minutes != null ? String(record.override_straordinario_minutes) : "",
                override_mpe_minutes: record.override_mpe_minutes != null ? String(record.override_mpe_minutes) : "",
                manual_note: record.manual_note ?? "",
              },
            ]),
          ),
        );
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento dettaglio collaboratore"));
  }, [collaboratorId, dateFrom, dateTo]);

  const totalOrdinary = useMemo(() => records.reduce((sum, item) => sum + (item.ordinary_minutes ?? 0), 0), [records]);
  const totalAbsence = useMemo(() => records.reduce((sum, item) => sum + (item.absence_minutes ?? 0), 0), [records]);
  const totalExtra = useMemo(() => records.reduce((sum, item) => sum + (item.straordinario_minutes ?? 0) + (item.mpe_minutes ?? 0), 0), [records]);
  const canEdit = currentUser?.role === "admin" || currentUser?.role === "super_admin";
  const mappingUsers = useMemo(
    () =>
      collaborator ? usersForInazCollaboratorMappingSorted(collaborator, users, allCollaborators, collaboratorId) : [],
    [collaborator, users, allCollaborators, collaboratorId],
  );
  const suggestedMapping = useMemo(() => {
    if (!collaborator || mappingUsers.length === 0) return null;
    let bestUser: ApplicationUser | null = null;
    let bestScore = 0;
    for (const user of mappingUsers) {
      const score = scoreInazCollaboratorUserMatch(collaborator, user);
      if (score > bestScore) {
        bestScore = score;
        bestUser = user;
      }
    }
    if (!bestUser || bestScore < 70) return null;
    return {
      user: bestUser,
      confidence: bestScore >= 120 ? "alta" : "media",
    };
  }, [collaborator, mappingUsers]);

  useEffect(() => {
    if (!collaborator || collaborator.application_user_id != null) {
      return;
    }
    if (!mappingValue && suggestedMapping) {
      setMappingValue(String(suggestedMapping.user.id));
    }
  }, [collaborator, suggestedMapping, mappingValue]);

  async function handleSaveMapping() {
    const token = getStoredAccessToken();
    if (!collaborator) {
      setMappingNotice({ tone: "error", message: "Collaboratore non caricato. Ricarica la pagina." });
      return;
    }
    if (!token) {
      setMappingNotice({ tone: "error", message: "Sessione scaduta. Effettua di nuovo l'accesso." });
      return;
    }

    const trimmedValue = mappingValue.trim();
    const nextUserId = trimmedValue === "" ? null : Number(trimmedValue);
    if (trimmedValue !== "" && !Number.isFinite(nextUserId)) {
      setMappingNotice({ tone: "error", message: "Seleziona un utente GAIA valido." });
      return;
    }

    const currentValue = collaborator.application_user_id == null ? "" : String(collaborator.application_user_id);
    if (trimmedValue === currentValue) {
      setMappingNotice({ tone: "success", message: "Mapping già salvato." });
      return;
    }

    setSavingMapping(true);
    setMappingNotice(null);
    setError(null);
    try {
      const updated = await mapInazCollaboratorApplicationUser(token, collaborator.id, nextUserId);
      setCollaborator(updated);
      setAllCollaborators((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setMappingValue(String(updated.application_user_id ?? ""));
      setMappingNotice({
        tone: "success",
        message: updated.application_user_id
          ? "Mapping GAIA salvato correttamente."
          : "Mapping GAIA rimosso correttamente.",
      });
      if (isEmbedded) {
        notifyInazCollaboratorDetailUpdated();
      }
    } catch (mapError) {
      const message = mapError instanceof Error ? mapError.message : "Errore salvataggio mapping";
      setMappingNotice({ tone: "error", message });
      setError(message);
    } finally {
      setSavingMapping(false);
    }
  }

  async function handleSaveDailyOverride(recordId: string) {
    const token = getStoredAccessToken();
    if (!token) return;
    const form = dailyOverrides[recordId];
    if (!form) return;
    try {
      const updated = await updateInazDailyRecord(token, recordId, {
        km_value: form.km_value ? Number(form.km_value) : null,
        override_straordinario_minutes: form.override_straordinario_minutes ? Number(form.override_straordinario_minutes) : null,
        override_mpe_minutes: form.override_mpe_minutes ? Number(form.override_mpe_minutes) : null,
        manual_note: form.manual_note.trim() || null,
      });
      setRecords((current) => current.map((item) => (item.id === recordId ? updated : item)));
      if (isEmbedded) {
        notifyInazCollaboratorDetailUpdated();
      }
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "Errore salvataggio rettifica giornaliera");
    }
  }

  async function handleCreateAssignment() {
    const token = getStoredAccessToken();
    if (!token || !collaboratorId || !assignmentTemplateId) return;
    try {
      const created = await createInazCollaboratorScheduleAssignment(token, collaboratorId, {
        template_id: Number(assignmentTemplateId),
        valid_from: assignmentValidFrom || null,
        valid_to: assignmentValidTo || null,
        notes: assignmentNotes.trim() || null,
      });
      setAssignments((current) => [created, ...current]);
      setAssignmentTemplateId("");
      setAssignmentValidFrom("");
      setAssignmentValidTo("");
      setAssignmentNotes("");
      if (isEmbedded) {
        notifyInazCollaboratorDetailUpdated();
      }
    } catch (assignmentError) {
      setError(assignmentError instanceof Error ? assignmentError.message : "Errore creazione assegnazione");
    }
  }

  async function handleDeleteAssignment(assignmentId: number) {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      await deleteInazScheduleAssignment(token, assignmentId);
      setAssignments((current) => current.filter((item) => item.id !== assignmentId));
      if (isEmbedded) {
        notifyInazCollaboratorDetailUpdated();
      }
    } catch (assignmentError) {
      setError(assignmentError instanceof Error ? assignmentError.message : "Errore eliminazione assegnazione");
    }
  }

  return (
    <ProtectedPage title="Dettaglio collaboratore Inaz" description="Calendario giornaliero e riepilogo eventi." breadcrumb="Inaz" requiredModule="inaz">
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {collaborator ? (
          <>
            <article className="panel-card">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="section-title">{collaborator.name}</p>
                  <p className="section-copy">
                    Matricola {collaborator.employee_code} · Azienda {collaborator.company_label ?? collaborator.company_code ?? "n/d"} · Nascita {collaborator.birth_date ?? "n/d"}
                  </p>
                </div>
                <Badge variant={collaborator.application_user_id ? "success" : "warning"}>
                  {collaborator.application_user_id ? "Mappato a GAIA" : "Da mappare"}
                </Badge>
              </div>

              <div className="mt-6 grid gap-4 lg:grid-cols-4">
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Giornaliere</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{records.length}</p>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Ore ordinarie</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{formatHours(totalOrdinary)}</p>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Ore assenza</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{formatHours(totalAbsence)}</p>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Ore extra</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{formatHours(totalExtra)}</p>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Voci riepilogo</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{summary.length}</p>
                </div>
              </div>
            </article>

            {canEdit ? (
              <article className="panel-card">
                <div className="mb-4">
                  <p className="section-title">Template orari assegnati</p>
                  <p className="section-copy">Assegna il template di lavoro del collaboratore e gestisci la validita nel tempo.</p>
                </div>
                <div className="grid gap-4 lg:grid-cols-[1.2fr_repeat(2,180px)_1fr_auto]">
                  <label className="block text-sm font-medium text-gray-700">
                    Template
                    <select className="form-control mt-1" value={assignmentTemplateId} onChange={(event) => setAssignmentTemplateId(event.target.value)}>
                      <option value="">Seleziona template</option>
                      {templates.map((template) => (
                        <option key={template.id} value={template.id}>
                          {template.code} · {template.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm font-medium text-gray-700">
                    Dal
                    <input className="form-control mt-1" type="date" value={assignmentValidFrom} onChange={(event) => setAssignmentValidFrom(event.target.value)} />
                  </label>
                  <label className="block text-sm font-medium text-gray-700">
                    Al
                    <input className="form-control mt-1" type="date" value={assignmentValidTo} onChange={(event) => setAssignmentValidTo(event.target.value)} />
                  </label>
                  <label className="block text-sm font-medium text-gray-700">
                    Note
                    <input className="form-control mt-1" value={assignmentNotes} onChange={(event) => setAssignmentNotes(event.target.value)} />
                  </label>
                  <div className="flex items-end">
                    <button className="btn-primary w-full" type="button" onClick={() => void handleCreateAssignment()}>
                      Aggiungi
                    </button>
                  </div>
                </div>
                <div className="mt-4 space-y-3">
                  {assignments.map((assignment) => (
                    <div key={assignment.id} className="flex flex-col gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
                      <div>
                        <p className="font-medium text-gray-900">{assignment.template?.code ?? `Template #${assignment.template_id}`} · {assignment.template?.label ?? "n/d"}</p>
                        <p className="text-xs text-gray-500">
                          Validita {assignment.valid_from ?? "subito"} / {assignment.valid_to ?? "aperta"}{assignment.notes ? ` · ${assignment.notes}` : ""}
                        </p>
                      </div>
                      <button className="btn-secondary" type="button" onClick={() => void handleDeleteAssignment(assignment.id)}>
                        Elimina
                      </button>
                    </div>
                  ))}
                  {assignments.length === 0 ? <p className="text-sm text-gray-500">Nessuna assegnazione template presente.</p> : null}
                </div>
              </article>
            ) : null}

            <article className="panel-card">
              <div className="grid gap-4 lg:grid-cols-[1fr_1fr_auto]">
                <label className="block text-sm font-medium text-gray-700">
                  Dal
                  <input className="form-control mt-1" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
                </label>
                <label className="block text-sm font-medium text-gray-700">
                  Al
                  <input className="form-control mt-1" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
                </label>
                {canEdit ? (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Mapping GAIA
                      {suggestedMapping ? (
                        <span className="mt-1 block text-xs text-emerald-700">
                          Suggerito: {suggestedMapping.user.full_name?.trim() || suggestedMapping.user.username} ({suggestedMapping.confidence})
                        </span>
                      ) : null}
                      <select
                        className="form-control mt-1"
                        value={mappingValue}
                        onChange={(event) => {
                          setMappingValue(event.target.value);
                          setMappingNotice(null);
                        }}
                      >
                        <option value="">Nessun mapping</option>
                        {mappingUsers.map((user) => (
                          <option key={user.id} value={user.id}>
                            {user.username} · {user.email}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button
                      className="btn-primary mt-3 w-full disabled:cursor-not-allowed disabled:opacity-60"
                      type="button"
                      disabled={savingMapping}
                      onClick={() => void handleSaveMapping()}
                    >
                      {savingMapping ? "Salvataggio..." : "Salva mapping"}
                    </button>
                    {mappingNotice ? (
                      <p
                        className={`mt-2 text-sm ${mappingNotice.tone === "success" ? "text-emerald-700" : "text-red-700"}`}
                        role={mappingNotice.tone === "success" ? "status" : "alert"}
                      >
                        {mappingNotice.message}
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </article>

            <article className="panel-card">
              <div className="mb-4 flex gap-2">
                <button className={tab === "calendar" ? "btn-primary" : "btn-secondary"} type="button" onClick={() => setTab("calendar")}>
                  Cartellino
                </button>
                <button className={tab === "summary" ? "btn-primary" : "btn-secondary"} type="button" onClick={() => setTab("summary")}>
                  Riepilogo eventi
                </button>
              </div>

              {tab === "calendar" ? (
                <div className="space-y-3">
                  {records.map((record) => (
                    <div key={record.id} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                          <p className="font-medium text-gray-900">{record.work_date}</p>
                          <p className="text-xs text-gray-500">
                            Orario {record.detail_programmed_schedule ?? record.schedule_code ?? "—"} · Stato {record.detail_status ?? record.stato ?? "—"}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs">
                          <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">Ord. {formatHours(record.ordinary_minutes)}</span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">Ass. {formatHours(record.absence_minutes)}</span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">Straord. {formatHours(record.straordinario_minutes)}</span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">MPE {formatHours(record.mpe_minutes)}</span>
                          {requestBadgeLabel(record) ? <span className="rounded-full bg-sky-100 px-2.5 py-1 text-sky-800">{requestBadgeLabel(record)}</span> : null}
                          {record.special_day ? <span className="rounded-full bg-amber-100 px-2.5 py-1 text-amber-800">Giorno speciale</span> : null}
                        </div>
                      </div>
                      <div className="mt-3 grid gap-3 md:grid-cols-4">
                        <div className="rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                          <span className="font-medium text-gray-900">Fasce:</span> {record.detail_time_slots ?? "—"}
                        </div>
                        <div className="rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                          <span className="font-medium text-gray-900">Tipo:</span> {record.detail_schedule_type ?? "—"}
                        </div>
                        <div className="rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                          <span className="font-medium text-gray-900">Ore teoriche:</span> {record.detail_theoretical_hours ?? formatHours(record.teo_minutes)}
                        </div>
                        <div className="rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                          <span className="font-medium text-gray-900">Ore assenza:</span> {record.detail_absence_hours ?? formatHours(record.absence_minutes)}
                        </div>
                      </div>
                      {(record.request_description || record.resolved_absence_cause || record.request_status) ? (
                        <div className="mt-3 grid gap-3 md:grid-cols-4">
                          <div className="rounded-xl border border-sky-100 bg-sky-50 px-3 py-2 text-sm text-sky-900">
                            <span className="font-medium text-sky-950">Causale:</span> {formatAbsenceCause(record.resolved_absence_cause)}
                          </div>
                          <div className="rounded-xl border border-sky-100 bg-sky-50 px-3 py-2 text-sm text-sky-900 md:col-span-2">
                            <span className="font-medium text-sky-950">Richiesta:</span> {formatRequestDescription(record.request_description)}
                          </div>
                          <div className="rounded-xl border border-sky-100 bg-sky-50 px-3 py-2 text-sm text-sky-900">
                            <span className="font-medium text-sky-950">Stato:</span> {record.request_status ?? "—"}
                          </div>
                        </div>
                      ) : null}
                      <div className="mt-3 grid gap-2 md:grid-cols-3">
                        {record.punches.map((punch) => (
                          <div key={punch.id} className="rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                            Timbratura {punch.sequence}: {punch.entry_time ?? "—"} / {punch.exit_time ?? "—"}
                          </div>
                        ))}
                      </div>
                      {record.evidenze ? <p className="mt-3 text-sm text-gray-600">Evidenze: {record.evidenze}</p> : null}
                      {(formatDetailEntries(record.detail_day_summary).length > 0 || formatDetailEntries(record.detail_day_totals).length > 0) ? (
                        <div className="mt-3 grid gap-3 xl:grid-cols-2">
                          <div className="rounded-xl border border-white bg-white px-3 py-3 text-sm text-gray-700">
                            <p className="mb-2 font-medium text-gray-900">Riepilogo giornata</p>
                            <div className="space-y-1">
                              {formatDetailEntries(record.detail_day_summary).length > 0 ? (
                                formatDetailEntries(record.detail_day_summary).map(([label, value]) => (
                                  <div key={label} className="flex items-center justify-between gap-3">
                                    <span>{label}</span>
                                    <span className="font-medium text-gray-900">{value}</span>
                                  </div>
                                ))
                              ) : (
                                <p className="text-gray-500">Nessun riepilogo disponibile.</p>
                              )}
                            </div>
                          </div>
                          <div className="rounded-xl border border-white bg-white px-3 py-3 text-sm text-gray-700">
                            <p className="mb-2 font-medium text-gray-900">Totali giornata</p>
                            <div className="space-y-1">
                              {formatDetailEntries(record.detail_day_totals).length > 0 ? (
                                formatDetailEntries(record.detail_day_totals).map(([label, value]) => (
                                  <div key={label} className="flex items-center justify-between gap-3">
                                    <span>{label}</span>
                                    <span className="font-medium text-gray-900">{value}</span>
                                  </div>
                                ))
                              ) : (
                                <p className="text-gray-500">Nessun totale disponibile.</p>
                              )}
                            </div>
                          </div>
                        </div>
                      ) : null}
                      {(record.detail_requests.length > 0 || record.detail_anomalies.length > 0 || record.detail_error) ? (
                        <div className="mt-3 grid gap-3 xl:grid-cols-2">
                          <div className="rounded-xl border border-white bg-white px-3 py-3 text-sm text-gray-700">
                            <p className="mb-2 font-medium text-gray-900">Richieste</p>
                            <div className="space-y-2">
                              {record.detail_requests.length > 0 ? (
                                record.detail_requests.map((request, index) => (
                                  <div key={`${record.id}-request-${index}`}>
                                    {Object.entries(request).map(([label, value]) => (
                                      <p key={label}>
                                        <span className="font-medium text-gray-900">{label}:</span> {value}
                                      </p>
                                    ))}
                                  </div>
                                ))
                              ) : (
                                <p className="text-gray-500">Nessuna richiesta.</p>
                              )}
                            </div>
                          </div>
                          <div className="rounded-xl border border-white bg-white px-3 py-3 text-sm text-gray-700">
                            <p className="mb-2 font-medium text-gray-900">Anomalie</p>
                            <div className="space-y-2">
                              {record.detail_anomalies.length > 0 ? (
                                record.detail_anomalies.map((anomaly, index) => (
                                  <div key={`${record.id}-anomaly-${index}`}>
                                    {Object.entries(anomaly).map(([label, value]) => (
                                      <p key={label}>
                                        <span className="font-medium text-gray-900">{label}:</span> {value}
                                      </p>
                                    ))}
                                  </div>
                                ))
                              ) : record.detail_error ? (
                                <p className="text-red-600">{record.detail_error}</p>
                              ) : (
                                <p className="text-gray-500">Nessuna anomalia.</p>
                              )}
                            </div>
                          </div>
                        </div>
                      ) : null}
                      {canEdit ? (
                        <div className="mt-3 rounded-xl border border-gray-100 bg-white px-3 py-3">
                          <p className="mb-3 font-medium text-gray-900">Rettifiche operative</p>
                          <div className="grid gap-3 lg:grid-cols-4">
                            <label className="block text-sm font-medium text-gray-700">
                              KM
                              <input
                                className="form-control mt-1"
                                value={dailyOverrides[record.id]?.km_value ?? ""}
                                onChange={(event) =>
                                  setDailyOverrides((current) => ({
                                    ...current,
                                    [record.id]: { ...current[record.id], km_value: event.target.value },
                                  }))
                                }
                              />
                            </label>
                            <label className="block text-sm font-medium text-gray-700">
                              Straordinario override
                              <input
                                className="form-control mt-1"
                                value={dailyOverrides[record.id]?.override_straordinario_minutes ?? ""}
                                onChange={(event) =>
                                  setDailyOverrides((current) => ({
                                    ...current,
                                    [record.id]: { ...current[record.id], override_straordinario_minutes: event.target.value },
                                  }))
                                }
                              />
                            </label>
                            <label className="block text-sm font-medium text-gray-700">
                              MPE override
                              <input
                                className="form-control mt-1"
                                value={dailyOverrides[record.id]?.override_mpe_minutes ?? ""}
                                onChange={(event) =>
                                  setDailyOverrides((current) => ({
                                    ...current,
                                    [record.id]: { ...current[record.id], override_mpe_minutes: event.target.value },
                                  }))
                                }
                              />
                            </label>
                            <label className="block text-sm font-medium text-gray-700">
                              Note
                              <input
                                className="form-control mt-1"
                                value={dailyOverrides[record.id]?.manual_note ?? ""}
                                onChange={(event) =>
                                  setDailyOverrides((current) => ({
                                    ...current,
                                    [record.id]: { ...current[record.id], manual_note: event.target.value },
                                  }))
                                }
                              />
                            </label>
                          </div>
                          <div className="mt-3 flex flex-wrap items-center gap-3">
                            <span className="text-xs text-gray-500">
                              Effettivo extra: {formatHours(record.effective_extra_minutes)}
                            </span>
                            <button className="btn-primary" type="button" onClick={() => void handleSaveDailyOverride(record.id)}>
                              Salva rettifiche
                            </button>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ))}
                  {records.length === 0 ? <p className="text-sm text-gray-500">Nessuna giornaliera nel periodo selezionato.</p> : null}
                </div>
              ) : (
                <div className="space-y-3">
                  {summary.map((item) => (
                    <div key={item.id} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                          <p className="font-medium text-gray-900">{item.description}</p>
                          <p className="text-xs text-gray-500">
                            Codice {item.event_code ?? "—"} · Validita {item.valid_from ?? "—"} / {item.valid_to ?? "—"}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs">
                          <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">Spettante {formatHours(item.spettante_minutes)}</span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">Fruito {formatHours(item.fruito_minutes)}</span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">Saldo {formatHours(item.saldo_minutes)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {summary.length === 0 ? <p className="text-sm text-gray-500">Nessun riepilogo eventi nel periodo selezionato.</p> : null}
                </div>
              )}
            </article>
          </>
        ) : (
          <p className="text-sm text-gray-500">Caricamento dettaglio collaboratore...</p>
        )}
      </div>
    </ProtectedPage>
  );
}
