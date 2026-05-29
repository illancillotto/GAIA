"use client";

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import { getCurrentUser, getInazCollaboratorCalendar, getInazCollaboratorSummary, listApplicationUsers, listInazCollaborators, mapInazCollaboratorApplicationUser } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { ApplicationUser, CurrentUser, InazCollaborator, InazDailyRecord, InazEventSummary } from "@/types/api";

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

export default function InazCollaboratoreDetailPage() {
  const params = useParams();
  const collaboratorId = params.id as string;
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [users, setUsers] = useState<ApplicationUser[]>([]);
  const [collaborator, setCollaborator] = useState<InazCollaborator | null>(null);
  const [records, setRecords] = useState<InazDailyRecord[]>([]);
  const [summary, setSummary] = useState<InazEventSummary[]>([]);
  const [tab, setTab] = useState<TabKey>("calendar");
  const [dateFrom, setDateFrom] = useState(currentMonthBounds().start);
  const [dateTo, setDateTo] = useState(currentMonthBounds().end);
  const [mappingValue, setMappingValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || !collaboratorId) return;
    getCurrentUser(token)
      .then((sessionUser) =>
        Promise.all([
          Promise.resolve(sessionUser),
          sessionUser.role === "admin" || sessionUser.role === "super_admin"
            ? listApplicationUsers(token)
            : Promise.resolve({ items: [], total: 0 }),
          listInazCollaborators(token, { page: 1, pageSize: 200 }),
          getInazCollaboratorCalendar(token, collaboratorId, dateFrom, dateTo),
          getInazCollaboratorSummary(token, collaboratorId, dateFrom, dateTo),
        ]),
      )
      .then(([sessionUser, usersResponse, collaboratorsResponse, calendarResponse, summaryResponse]) => {
        setCurrentUser(sessionUser);
        setUsers(usersResponse.items);
        setCollaborator(
          collaboratorsResponse.items.find((item) => item.id === collaboratorId) ?? calendarResponse.collaborator,
        );
        setRecords(calendarResponse.items);
        setSummary(summaryResponse.items);
        setMappingValue(String((collaboratorsResponse.items.find((item) => item.id === collaboratorId) ?? calendarResponse.collaborator).application_user_id ?? ""));
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento dettaglio collaboratore"));
  }, [collaboratorId, dateFrom, dateTo]);

  const totalOrdinary = useMemo(() => records.reduce((sum, item) => sum + (item.ordinary_minutes ?? 0), 0), [records]);
  const totalAbsence = useMemo(() => records.reduce((sum, item) => sum + (item.absence_minutes ?? 0), 0), [records]);
  const canEdit = currentUser?.role === "admin" || currentUser?.role === "super_admin";

  async function handleSaveMapping() {
    const token = getStoredAccessToken();
    if (!token || !collaborator) return;
    try {
      const updated = await mapInazCollaboratorApplicationUser(token, collaborator.id, mappingValue ? Number(mappingValue) : null);
      setCollaborator(updated);
    } catch (mapError) {
      setError(mapError instanceof Error ? mapError.message : "Errore salvataggio mapping");
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
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Voci riepilogo</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{summary.length}</p>
                </div>
              </div>
            </article>

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
                      <select className="form-control mt-1" value={mappingValue} onChange={(event) => setMappingValue(event.target.value)}>
                        <option value="">Nessun mapping</option>
                        {users.map((user) => (
                          <option key={user.id} value={user.id}>
                            {user.username} · {user.email}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button className="btn-primary mt-3 w-full" type="button" onClick={() => void handleSaveMapping()}>
                      Salva mapping
                    </button>
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
                          <p className="text-xs text-gray-500">Codice orario {record.schedule_code ?? "—"} · Stato {record.stato ?? "—"}</p>
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs">
                          <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">Ord. {formatHours(record.ordinary_minutes)}</span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">Ass. {formatHours(record.absence_minutes)}</span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">Straord. {formatHours(record.straordinario_minutes)}</span>
                        </div>
                      </div>
                      <div className="mt-3 grid gap-2 md:grid-cols-3">
                        {record.punches.map((punch) => (
                          <div key={punch.id} className="rounded-xl border border-white bg-white px-3 py-2 text-sm text-gray-700">
                            Timbratura {punch.sequence}: {punch.entry_time ?? "—"} / {punch.exit_time ?? "—"}
                          </div>
                        ))}
                      </div>
                      {record.evidenze ? <p className="mt-3 text-sm text-gray-600">Evidenze: {record.evidenze}</p> : null}
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
