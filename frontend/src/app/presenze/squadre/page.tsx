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

type SupervisorCandidate = {
  collaboratorId: string;
  label: string;
  employeeCode: string;
  applicationUserId: number | null;
  userLabel: string | null;
};

function userLabel(user: ApplicationUser): string {
  return user.full_name || user.username;
}

function visibleResultsCount(query: string, total: number): number {
  return normalizeSearch(query) ? total : Math.min(total, 6);
}

function normalizeSearch(value: string): string {
  return value.trim().toLowerCase();
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
  const [teamSearch, setTeamSearch] = useState("");
  const [collaboratorSearch, setCollaboratorSearch] = useState("");
  const [supervisorSearch, setSupervisorSearch] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedTeam = useMemo(() => teams.find((team) => team.id === selectedTeamId) ?? teams[0] ?? null, [selectedTeamId, teams]);
  const usersById = useMemo(() => new Map(users.map((user) => [user.id, user])), [users]);
  const filteredTeams = useMemo(() => {
    const query = normalizeSearch(teamSearch);
    if (!query) return teams;
    return teams.filter((team) => [team.name, team.code ?? ""].some((value) => value.toLowerCase().includes(query)));
  }, [teamSearch, teams]);
  const filteredCollaborators = useMemo(() => {
    const query = normalizeSearch(collaboratorSearch);
    if (!query) return collaborators;
    return collaborators.filter((collaborator) => [collaborator.name, collaborator.employee_code].some((value) => value.toLowerCase().includes(query)));
  }, [collaboratorSearch, collaborators]);
  const visibleCollaborators = useMemo(
    () => filteredCollaborators.slice(0, visibleResultsCount(collaboratorSearch, filteredCollaborators.length)),
    [collaboratorSearch, filteredCollaborators],
  );
  const supervisorCandidates = useMemo<SupervisorCandidate[]>(() => {
    return collaborators.map((collaborator) => {
      const user = collaborator.application_user_id ? usersById.get(collaborator.application_user_id) ?? null : null;
      return {
        collaboratorId: collaborator.id,
        label: collaborator.name,
        employeeCode: collaborator.employee_code,
        applicationUserId: collaborator.application_user_id,
        userLabel: user ? userLabel(user) : null,
      };
    });
  }, [collaborators, usersById]);
  const filteredSupervisorCandidates = useMemo(() => {
    const query = normalizeSearch(supervisorSearch);
    if (!query) return supervisorCandidates;
    return supervisorCandidates.filter((candidate) =>
      [candidate.label, candidate.employeeCode, candidate.userLabel ?? ""].some((value) => value.toLowerCase().includes(query)),
    );
  }, [supervisorCandidates, supervisorSearch]);
  const visibleSupervisorCandidates = useMemo(
    () => filteredSupervisorCandidates.slice(0, visibleResultsCount(supervisorSearch, filteredSupervisorCandidates.length)),
    [filteredSupervisorCandidates, supervisorSearch],
  );

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
    try {
      const updated = await updateGatePresenzeTeam(token, team.id, { active: !team.active });
      setTeams((current) => replaceTeam(current, updated));
      setError(null);
      setFeedback(updated.active ? "Squadra riattivata." : "Squadra disattivata.");
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "Errore aggiornamento squadra.");
    }
  }

  async function handleAddMembership(collaboratorId: string) {
    const token = getStoredAccessToken();
    if (!token || !selectedTeam || !collaboratorId) return;
    try {
      await createGatePresenzeTeamMembership(token, selectedTeam.id, {
        collaborator_id: collaboratorId,
        role: "member",
      });
      const refreshedTeams = await listGatePresenzeTeams(token);
      setTeams(refreshedTeams);
      setSelectedTeamId(selectedTeam.id);
      setError(null);
      setFeedback("Collaboratore aggiunto alla squadra.");
    } catch (membershipError) {
      setError(membershipError instanceof Error ? membershipError.message : "Errore aggiunta collaboratore.");
    }
  }

  async function handleAddSupervisor(collaboratorId: string) {
    const token = getStoredAccessToken();
    if (!token || !selectedTeam || !collaboratorId) return;
    const selectedSupervisor = supervisorCandidates.find((candidate) => candidate.collaboratorId === collaboratorId);
    if (!selectedSupervisor?.applicationUserId) {
      setError("Il collaboratore selezionato non e collegato a un utente GAIA/GATE. Collega prima il profilo utente.");
      return;
    }
    try {
      await createGatePresenzeTeamSupervisor(token, selectedTeam.id, {
        application_user_id: selectedSupervisor.applicationUserId,
        permission_scope: "validate",
      });
      const refreshedTeams = await listGatePresenzeTeams(token);
      setTeams(refreshedTeams);
      setSelectedTeamId(selectedTeam.id);
      setError(null);
      setFeedback("Responsabile assegnato alla squadra.");
    } catch (supervisorError) {
      setError(supervisorError instanceof Error ? supervisorError.message : "Errore assegnazione responsabile.");
    }
  }

  return (
    <ProtectedPage
      title="Squadre Presenze"
      description="Gestione squadre operative usate da GATE Console Mobile per giornaliere, anomalie ed export."
      breadcrumb="Squadre"
      requiredModule="presenze"
    >
      <div className="space-y-6">
        <section className="overflow-hidden rounded-[2rem] border border-emerald-100 bg-gradient-to-br from-emerald-50 via-white to-stone-50 shadow-sm">
          <div className="grid gap-5 p-5 lg:grid-cols-[1fr_320px]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">Organizzazione GATE</p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-950">Crea e assegna squadre operative</h2>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">
                Cerca rapidamente personale importato dalle giornaliere, assegna i collaboratori alla squadra e scegli i responsabili abilitati alla verifica.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2 rounded-2xl border border-white/70 bg-white/75 p-3 text-center shadow-sm">
              <div>
                <span className="block text-2xl font-semibold text-slate-950">{teams.length}</span>
                <span className="text-[11px] uppercase tracking-widest text-slate-500">Squadre</span>
              </div>
              <div>
                <span className="block text-2xl font-semibold text-slate-950">{collaborators.length}</span>
                <span className="text-[11px] uppercase tracking-widest text-slate-500">Persone</span>
              </div>
              <div>
                <span className="block text-2xl font-semibold text-slate-950">{supervisorCandidates.filter((candidate) => candidate.applicationUserId).length}</span>
                <span className="text-[11px] uppercase tracking-widest text-slate-500">Abilitati</span>
              </div>
            </div>
          </div>

          <form className="grid gap-3 border-t border-emerald-100 bg-white/80 p-5 md:grid-cols-[1fr_180px_auto]" onSubmit={handleCreateTeam}>
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
          {feedback ? <p className="px-5 pb-2 text-sm font-medium text-emerald-700">{feedback}</p> : null}
          {error ? <p className="px-5 pb-2 text-sm font-medium text-red-700">{error}</p> : null}
        </section>

        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          <aside className="space-y-3 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
            <div>
              <label className="text-xs font-semibold uppercase tracking-widest text-slate-400" htmlFor="team_search">
                Cerca squadra
              </label>
              <div className="mt-2 flex overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                <input
                  id="team_search"
                  className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm outline-none"
                  value={teamSearch}
                  onChange={(event) => setTeamSearch(event.target.value)}
                  placeholder="Nome o codice"
                />
                {teamSearch ? (
                  <button className="px-3 text-sm font-semibold text-slate-500" type="button" onClick={() => setTeamSearch("")}>
                    X
                  </button>
                ) : null}
              </div>
            </div>
            {filteredTeams.map((team) => (
              <button
                key={team.id}
                className={`w-full rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 hover:shadow-md ${selectedTeam?.id === team.id ? "border-emerald-400 bg-emerald-50" : "border-slate-200 bg-white"}`}
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
            {filteredTeams.length === 0 ? <p className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-500">Nessuna squadra trovata.</p> : null}
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

                <div className="grid gap-4 xl:grid-cols-2">
                  <div className="rounded-[1.75rem] border border-slate-100 bg-slate-50/60 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-semibold text-slate-900">Aggiungi collaboratore</h3>
                        <p className="text-xs text-slate-500">Digita e seleziona direttamente il risultato.</p>
                      </div>
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">{filteredCollaborators.length}</span>
                    </div>
                    <label className="mt-3 block">
                      <span className="sr-only">Cerca collaboratore o matricola</span>
                      <input
                        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm outline-none transition focus:border-emerald-400"
                        type="search"
                        value={collaboratorSearch}
                        onChange={(event) => setCollaboratorSearch(event.target.value)}
                        placeholder="Cerca collaboratore o matricola"
                      />
                    </label>
                    <div className="mt-3 space-y-2">
                      {visibleCollaborators.length === 0 ? (
                        <p className="rounded-2xl bg-white px-4 py-3 text-sm text-slate-500">Nessun collaboratore trovato.</p>
                      ) : (
                        visibleCollaborators.map((collaborator) => (
                          <button
                            key={collaborator.id}
                            className="flex w-full items-center justify-between gap-3 rounded-2xl border border-white bg-white px-4 py-3 text-left shadow-sm transition hover:border-emerald-200 hover:bg-emerald-50"
                            type="button"
                            onClick={() => handleAddMembership(collaborator.id)}
                          >
                            <span>
                              <span className="block text-sm font-semibold text-slate-950">{collaborator.name}</span>
                              <span className="mt-0.5 block text-xs text-slate-500">Matricola {collaborator.employee_code} · {collaborator.contract_kind ?? "contratto n/d"}</span>
                            </span>
                            <span className="rounded-full bg-emerald-700 px-3 py-1 text-xs font-semibold text-white">Aggiungi</span>
                          </button>
                        ))
                      )}
                      {filteredCollaborators.length > visibleCollaborators.length ? (
                        <p className="px-1 text-xs text-slate-500">Mostrati i primi {visibleCollaborators.length}. Raffina la ricerca per altri risultati.</p>
                      ) : null}
                    </div>
                  </div>

                  <div className="rounded-[1.75rem] border border-emerald-100 bg-emerald-50/50 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-semibold text-slate-900">Assegna responsabile</h3>
                        <p className="text-xs text-slate-500">Personale dalle giornaliere, con stato profilo GAIA/GATE.</p>
                      </div>
                      <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">
                        {filteredSupervisorCandidates.length}
                      </span>
                    </div>
                    <label className="mt-3 block">
                      <span className="sr-only">Cerca responsabile, matricola o utente</span>
                      <input
                        className="w-full rounded-2xl border border-emerald-100 bg-white px-4 py-3 text-sm shadow-sm outline-none transition focus:border-emerald-400"
                        type="search"
                        value={supervisorSearch}
                        onChange={(event) => setSupervisorSearch(event.target.value)}
                        placeholder="Cerca responsabile, matricola o utente"
                      />
                    </label>
                    <div className="mt-3 space-y-2">
                      {visibleSupervisorCandidates.length === 0 ? (
                        <p className="rounded-2xl bg-white px-4 py-3 text-sm text-slate-500">Nessun responsabile trovato.</p>
                      ) : (
                        visibleSupervisorCandidates.map((candidate) => (
                          <button
                            key={candidate.collaboratorId}
                            className="flex w-full items-center justify-between gap-3 rounded-2xl border border-white bg-white px-4 py-3 text-left shadow-sm transition hover:border-emerald-300 hover:bg-white"
                            type="button"
                            onClick={() => handleAddSupervisor(candidate.collaboratorId)}
                          >
                            <span>
                              <span className="block text-sm font-semibold text-slate-950">{candidate.label}</span>
                              <span className="mt-0.5 block text-xs text-slate-500">Matricola {candidate.employeeCode} · {candidate.userLabel ?? "profilo utente mancante"}</span>
                            </span>
                            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${candidate.applicationUserId ? "bg-emerald-700 text-white" : "bg-amber-100 text-amber-800"}`}>
                              {candidate.applicationUserId ? "Assegna" : "Da collegare"}
                            </span>
                          </button>
                        ))
                      )}
                      {filteredSupervisorCandidates.length > visibleSupervisorCandidates.length ? (
                        <p className="px-1 text-xs text-slate-500">Mostrati i primi {visibleSupervisorCandidates.length}. Raffina la ricerca per altri risultati.</p>
                      ) : null}
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-slate-100 p-4">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-slate-900">Collaboratori assegnati</h3>
                      <span className="text-xs font-semibold text-slate-400">{selectedTeam.memberships.length}</span>
                    </div>
                    <div className="mt-3 space-y-2">
                      {selectedTeam.memberships.length === 0 ? (
                        <p className="rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-500">Nessun collaboratore assegnato.</p>
                      ) : (
                        selectedTeam.memberships.map((membership) => (
                          <div key={membership.id} className="rounded-xl bg-slate-50 px-3 py-2 text-sm">
                            <span className="font-medium">{membership.collaborator_name || membership.collaborator_id}</span>
                            <span className="block text-xs text-slate-500">Matricola {membership.employee_code || "n/d"} · ruolo {membership.role}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-slate-100 p-4">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-slate-900">Responsabili assegnati</h3>
                      <span className="text-xs font-semibold text-slate-400">{selectedTeam.supervisors.length}</span>
                    </div>
                    <div className="mt-3 space-y-2">
                      {selectedTeam.supervisors.length === 0 ? (
                        <p className="rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-500">Nessun responsabile assegnato.</p>
                      ) : (
                        selectedTeam.supervisors.map((supervisor) => (
                          <div key={supervisor.id} className="rounded-xl bg-slate-50 px-3 py-2 text-sm">
                            <span className="font-medium">{supervisor.user_label || supervisor.username || supervisor.application_user_id}</span>
                            <span className="block text-xs text-slate-500">Permesso {supervisor.permission_scope}</span>
                          </div>
                        ))
                      )}
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
