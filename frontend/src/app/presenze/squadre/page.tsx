"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  createGatePresenzeTeam,
  createGatePresenzeTeamMembership,
  createGatePresenzeTeamSupervisor,
  listAllPresenzeCollaborators,
  listGatePresenzeTeams,
  listPresenzeApplicationUsers,
  updateGatePresenzeTeam,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { ApplicationUser, GatePresenzeTeam, PresenzeCollaborator } from "@/types/api";

type TeamFormState = {
  name: string;
  code: string;
};

function userLabel(user: ApplicationUser): string {
  return user.full_name || user.username;
}

function collaboratorLabel(collaborator: PresenzeCollaborator): string {
  return `${collaborator.name} · ${collaborator.employee_code}`;
}

function replaceTeam(teams: GatePresenzeTeam[], updatedTeam: GatePresenzeTeam): GatePresenzeTeam[] {
  return teams.map((team) => (team.id === updatedTeam.id ? updatedTeam : team));
}

export default function PresenzeSquadrePage() {
  const [teams, setTeams] = useState<GatePresenzeTeam[]>([]);
  const [collaborators, setCollaborators] = useState<PresenzeCollaborator[]>([]);
  const [users, setUsers] = useState<ApplicationUser[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState("");
  const [teamForm, setTeamForm] = useState<TeamFormState>({ name: "", code: "" });
  const [selectedCollaboratorId, setSelectedCollaboratorId] = useState("");
  const [selectedSupervisorId, setSelectedSupervisorId] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedTeam = useMemo(() => teams.find((team) => team.id === selectedTeamId) ?? teams[0] ?? null, [selectedTeamId, teams]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    Promise.all([listGatePresenzeTeams(token), listAllPresenzeCollaborators(token), listPresenzeApplicationUsers(token)])
      .then(([teamRows, collaboratorRows, userRows]) => {
        setTeams(teamRows);
        setCollaborators(collaboratorRows);
        setUsers(userRows);
        setSelectedTeamId(teamRows[0]?.id ?? "");
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento squadre Presenze"));
  }, []);

  async function handleCreateTeam(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getStoredAccessToken();
    if (!token) return;
    const formData = new FormData(event.currentTarget);
    const name = (formData.get("team_name") as string).trim();
    const code = (formData.get("team_code") as string).trim();
    if (!name) {
      setError("Inserisci un nome squadra.");
      return;
    }
    try {
      const created = await createGatePresenzeTeam(token, {
        name,
        code: code || null,
        scope: "presenze",
        active: true,
      });
      setTeams((current) => [...current, created]);
      setSelectedTeamId(created.id);
      setTeamForm({ name: "", code: "" });
      setError(null);
      setFeedback("Squadra creata.");
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Errore creazione squadra.");
    }
  }

  async function handleToggleTeamActive(team: GatePresenzeTeam) {
    const token = getStoredAccessToken();
    if (!token) return;
    const updated = await updateGatePresenzeTeam(token, team.id, { active: !team.active });
    setTeams((current) => replaceTeam(current, updated));
    setFeedback(updated.active ? "Squadra riattivata." : "Squadra disattivata.");
  }

  async function handleAddMembership() {
    const token = getStoredAccessToken();
    if (!token || !selectedTeam || !selectedCollaboratorId) return;
    await createGatePresenzeTeamMembership(token, selectedTeam.id, {
      collaborator_id: selectedCollaboratorId,
      role: "member",
    });
    const refreshedTeams = await listGatePresenzeTeams(token);
    setTeams(refreshedTeams);
    setSelectedTeamId(selectedTeam.id);
    setSelectedCollaboratorId("");
    setFeedback("Collaboratore aggiunto alla squadra.");
  }

  async function handleAddSupervisor() {
    const token = getStoredAccessToken();
    if (!token || !selectedTeam || !selectedSupervisorId) return;
    await createGatePresenzeTeamSupervisor(token, selectedTeam.id, {
      application_user_id: Number(selectedSupervisorId),
      permission_scope: "validate",
    });
    const refreshedTeams = await listGatePresenzeTeams(token);
    setTeams(refreshedTeams);
    setSelectedTeamId(selectedTeam.id);
    setSelectedSupervisorId("");
    setFeedback("Responsabile assegnato alla squadra.");
  }

  return (
    <ProtectedPage
      title="Squadre Presenze"
      description="Gestione squadre operative usate da GATE Console Mobile per giornaliere, anomalie ed export."
      breadcrumb="Squadre"
      requiredModule="presenze"
    >
      <div className="space-y-6">
        <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <form className="grid gap-3 md:grid-cols-[1fr_180px_auto]" onSubmit={handleCreateTeam}>
            <label className="text-sm font-semibold text-slate-700">
              Nome squadra
              <input
                className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                name="team_name"
                value={teamForm.name}
                onChange={(event) => setTeamForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Es. Squadra Nord"
              />
            </label>
            <label className="text-sm font-semibold text-slate-700">
              Codice
              <input
                className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                name="team_code"
                value={teamForm.code}
                onChange={(event) => setTeamForm((current) => ({ ...current, code: event.target.value }))}
                placeholder="NORD"
              />
            </label>
            <button className="btn-primary self-end" type="submit">
              Crea squadra
            </button>
          </form>
          {feedback ? <p className="mt-3 text-sm font-medium text-emerald-700">{feedback}</p> : null}
          {error ? <p className="mt-3 text-sm font-medium text-red-700">{error}</p> : null}
        </section>

        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          <aside className="space-y-3">
            {teams.map((team) => (
              <button
                key={team.id}
                className={`w-full rounded-2xl border p-4 text-left shadow-sm ${selectedTeam?.id === team.id ? "border-emerald-400 bg-emerald-50" : "border-slate-200 bg-white"}`}
                type="button"
                onClick={() => setSelectedTeamId(team.id)}
              >
                <span className="block font-semibold text-slate-950">{team.name}</span>
                <span className="mt-1 block text-xs text-slate-500">{team.code || "Senza codice"} · {team.active ? "Attiva" : "Disattiva"}</span>
                <span className="mt-2 block text-xs text-slate-500">
                  {team.memberships.length} collaboratori · {team.supervisors.length} responsabili
                </span>
              </button>
            ))}
          </aside>

          <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            {selectedTeam ? (
              <div className="space-y-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">Squadra selezionata</p>
                    <h2 className="mt-1 text-2xl font-semibold text-slate-950">{selectedTeam.name}</h2>
                    <p className="mt-1 text-sm text-slate-500">Codice {selectedTeam.code || "n/d"} · Scope {selectedTeam.scope}</p>
                  </div>
                  <button className="btn-secondary" type="button" onClick={() => handleToggleTeamActive(selectedTeam)}>
                    {selectedTeam.active ? "Disattiva" : "Riattiva"}
                  </button>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-slate-100 p-4">
                    <h3 className="font-semibold text-slate-900">Aggiungi collaboratore</h3>
                    <select
                      className="mt-3 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                      value={selectedCollaboratorId}
                      onChange={(event) => setSelectedCollaboratorId(event.target.value)}
                    >
                      <option value="">Seleziona collaboratore</option>
                      {collaborators.map((collaborator) => (
                        <option key={collaborator.id} value={collaborator.id}>
                          {collaboratorLabel(collaborator)}
                        </option>
                      ))}
                    </select>
                    <button className="btn-primary mt-3" type="button" onClick={handleAddMembership}>
                      Aggiungi
                    </button>
                  </div>

                  <div className="rounded-2xl border border-slate-100 p-4">
                    <h3 className="font-semibold text-slate-900">Assegna responsabile</h3>
                    <select
                      className="mt-3 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                      value={selectedSupervisorId}
                      onChange={(event) => setSelectedSupervisorId(event.target.value)}
                    >
                      <option value="">Seleziona utente Presenze</option>
                      {users.map((user) => (
                        <option key={user.id} value={user.id}>
                          {userLabel(user)}
                        </option>
                      ))}
                    </select>
                    <button className="btn-primary mt-3" type="button" onClick={handleAddSupervisor}>
                      Assegna
                    </button>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <h3 className="font-semibold text-slate-900">Collaboratori</h3>
                    <div className="mt-3 space-y-2">
                      {selectedTeam.memberships.map((membership) => (
                        <div key={membership.id} className="rounded-xl bg-slate-50 px-3 py-2 text-sm">
                          <span className="font-medium">{membership.collaborator_name || membership.collaborator_id}</span>
                          <span className="block text-xs text-slate-500">Matricola {membership.employee_code || "n/d"} · ruolo {membership.role}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900">Responsabili</h3>
                    <div className="mt-3 space-y-2">
                      {selectedTeam.supervisors.map((supervisor) => (
                        <div key={supervisor.id} className="rounded-xl bg-slate-50 px-3 py-2 text-sm">
                          <span className="font-medium">{supervisor.user_label || supervisor.username || supervisor.application_user_id}</span>
                          <span className="block text-xs text-slate-500">Permesso {supervisor.permission_scope}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">Crea una squadra per iniziare ad assegnare collaboratori e responsabili.</p>
            )}
          </section>
        </div>
      </div>
    </ProtectedPage>
  );
}
