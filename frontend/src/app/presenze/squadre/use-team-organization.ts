"use client";

import { useEffect, useState } from "react";
import { getStoredAccessToken } from "@/lib/auth";
import { getTeamOrganizationDirectory, saveTeamOrganization, type TeamOrganizationDirectory } from "@/lib/api/presenze-team-organization";

export function useTeamOrganization(teamId: string) {
  const [directory, setDirectory] = useState<TeamOrganizationDirectory | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [selected, setSelected] = useState("");
  const [phase, setPhase] = useState<"loading" | "ready" | "saving">("loading");
  const [reload, setReload] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    setPhase("loading"); setDirectory(null); setError(null); setNotice("");
    const token = getStoredAccessToken();
    if (!token) { setError("Sessione scaduta. Accedi nuovamente."); setPhase("ready"); return; }
    getTeamOrganizationDirectory(token).then(data => {
      if (!active) return;
      const previous = data.teams.find(team => team.team_id === teamId)?.org_unit_id ?? null;
      setDirectory(data); setSaved(previous); setSelected(previous ?? "");
    }).catch(reason => {
      if (active) setError(reason instanceof Error ? reason.message : "Organigramma non disponibile.");
    }).finally(() => { if (active) setPhase("ready"); });
    return () => { active = false; };
  }, [teamId, reload]);

  async function save() {
    const token = getStoredAccessToken();
    if (!token) { setError("Sessione scaduta. Accedi nuovamente."); return; }
    setPhase("saving"); setError(null); setNotice("");
    try {
      const result = await saveTeamOrganization(token, teamId, selected || null, saved);
      setSaved(result.org_unit_id); setSelected(result.org_unit_id ?? "");
      setNotice("Collegamento salvato. Sarà visibile in GATE dopo la sincronizzazione squadre.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Collegamento non salvato. Aggiorna e riprova.");
    } finally { setPhase("ready"); }
  }

  return { directory, saved, selected, setSelected, loading: phase === "loading", saving: phase === "saving", error, notice, save,
    unavailable: phase !== "ready" || !directory,
    refresh: () => setReload(value => value + 1) };
}
