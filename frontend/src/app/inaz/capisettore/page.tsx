"use client";

import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  getCurrentUser,
  listAllInazCollaborators,
  listInazApplicationUsers,
  listInazSupervisorAssignments,
  updateInazSupervisorAssignment,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { ApplicationUser, CurrentUser, InazCollaborator, InazSupervisorAssignment } from "@/types/api";

function displayUser(user: ApplicationUser): string {
  return user.full_name?.trim() || user.username;
}

export default function InazCapisettorePage() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [users, setUsers] = useState<ApplicationUser[]>([]);
  const [collaborators, setCollaborators] = useState<InazCollaborator[]>([]);
  const [assignments, setAssignments] = useState<InazSupervisorAssignment[]>([]);
  const [search, setSearch] = useState("");
  const [savingCollaboratorId, setSavingCollaboratorId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function loadPage() {
    const token = getStoredAccessToken();
    if (!token) return;
    const [sessionUser, userItems, collaboratorItems, assignmentItems] = await Promise.all([
      getCurrentUser(token),
      listInazApplicationUsers(token),
      listAllInazCollaborators(token),
      listInazSupervisorAssignments(token),
    ]);
    setCurrentUser(sessionUser);
    setUsers(userItems);
    setCollaborators(collaboratorItems);
    setAssignments(assignmentItems);
  }

  useEffect(() => {
    void loadPage().catch((loadError) => {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento capisettore Inaz");
    });
  }, []);

  const assignmentMap = useMemo(() => new Map(assignments.map((item) => [item.collaborator_id, item])), [assignments]);
  const supervisors = useMemo(
    () =>
      users
        .filter((user) => user.is_active && user.module_inaz && user.role !== "operator")
        .sort((left, right) => displayUser(left).localeCompare(displayUser(right), "it")),
    [users],
  );
  const supervisorCountMap = useMemo(() => {
    const map = new Map<number, number>();
    for (const assignment of assignments) {
      map.set(assignment.supervisor_user_id, (map.get(assignment.supervisor_user_id) ?? 0) + 1);
    }
    return map;
  }, [assignments]);
  const filteredCollaborators = useMemo(() => {
    const term = search.trim().toLowerCase();
    return collaborators
      .filter((collaborator) => {
        if (!term) return true;
        const supervisor = assignmentMap.get(collaborator.id)?.supervisor;
        return [
          collaborator.name,
          collaborator.employee_code,
          collaborator.company_label ?? collaborator.company_code ?? "",
          supervisor?.full_name ?? supervisor?.username ?? "",
        ].some((value) => value.toLowerCase().includes(term));
      })
      .sort((left, right) => left.name.localeCompare(right.name, "it"));
  }, [assignmentMap, collaborators, search]);

  async function handleAssign(collaboratorId: string, rawSupervisorId: string) {
    const token = getStoredAccessToken();
    if (!token) return;
    setSavingCollaboratorId(collaboratorId);
    setError(null);
    setSuccess(null);
    try {
      await updateInazSupervisorAssignment(token, collaboratorId, rawSupervisorId ? Number(rawSupervisorId) : null);
      const nextAssignments = await listInazSupervisorAssignments(token);
      setAssignments(nextAssignments);
      setSuccess(rawSupervisorId ? "Caposettore assegnato." : "Assegnazione caposettore rimossa.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore aggiornamento assegnazione caposettore");
    } finally {
      setSavingCollaboratorId(null);
    }
  }

  return (
    <ProtectedPage
      title="Capisettore Inaz"
      description="Nomina dei responsabili di settore e assegnazione degli operai per la validazione delle giornaliere."
      breadcrumb="Inaz"
      requiredModule="inaz"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <article className="panel-card">
          <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
            <label className="block text-sm font-medium text-gray-700">
              Cerca operaio o caposettore
              <input
                className="form-control mt-1"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Nome, matricola, azienda o caposettore"
              />
            </label>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-700">
              {currentUser ? `Sessione: ${currentUser.username}` : "Caricamento sessione"}
            </div>
          </div>
        </article>

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Responsabili disponibili</p>
            <p className="section-copy">Sono selezionabili solo utenti attivi con modulo Inaz abilitato.</p>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {supervisors.map((user) => (
              <div key={user.id} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-sm font-semibold text-gray-900">{displayUser(user)}</p>
                <p className="mt-1 text-xs text-gray-500">{user.username} · {user.role}</p>
                <p className="mt-2 text-sm text-gray-700">{supervisorCountMap.get(user.id) ?? 0} operai assegnati</p>
              </div>
            ))}
          </div>
        </article>

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Assegnazione operai</p>
            <p className="section-copy">Ogni collaboratore può avere un solo caposettore responsabile della validazione delle giornaliere.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-[0.14em] text-gray-500">
                  <th className="py-3 pr-4">Operaio</th>
                  <th className="py-3 pr-4">Matricola</th>
                  <th className="py-3 pr-4">Azienda</th>
                  <th className="py-3 pr-4">Caposettore</th>
                  <th className="py-3">Azione</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredCollaborators.map((collaborator) => {
                  const assignment = assignmentMap.get(collaborator.id) ?? null;
                  return (
                    <tr key={collaborator.id}>
                      <td className="py-3 pr-4 font-medium text-gray-900">{collaborator.name}</td>
                      <td className="py-3 pr-4">{collaborator.employee_code}</td>
                      <td className="py-3 pr-4">{collaborator.company_label ?? collaborator.company_code ?? "—"}</td>
                      <td className="py-3 pr-4">
                        <select
                          className="form-control"
                          value={assignment ? String(assignment.supervisor_user_id) : ""}
                          onChange={(event) => void handleAssign(collaborator.id, event.target.value)}
                          disabled={savingCollaboratorId === collaborator.id}
                        >
                          <option value="">Nessun caposettore</option>
                          {supervisors.map((user) => (
                            <option key={user.id} value={user.id}>
                              {displayUser(user)} · {user.username}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-3 text-gray-500">
                        {savingCollaboratorId === collaborator.id
                          ? "Salvataggio..."
                          : assignment?.supervisor
                            ? `Assegnato a ${assignment.supervisor.full_name || assignment.supervisor.username}`
                            : "Non assegnato"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </article>
      </div>
    </ProtectedPage>
  );
}
