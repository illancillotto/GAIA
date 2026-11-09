"use client";

import { useTeamOrganization } from "./use-team-organization";
import type { GatePresenzeTeam } from "@/types/api";

export function TeamOrganizationHeader({ team, onToggle }: { team: GatePresenzeTeam; onToggle: (team: GatePresenzeTeam) => Promise<void> }) {
  return <>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">Squadra selezionata</p>
        <h2 className="mt-1 text-2xl font-semibold text-slate-950">{team.name}</h2>
        <p className="mt-1 text-sm text-slate-500">Codice {team.code || "n/d"} · Area {team.personnel_area}</p>
      </div>
      <button className="btn-secondary" type="button" onClick={() => onToggle(team)}>{team.active ? "Disattiva" : "Riattiva"}</button>
    </div>
    <TeamOrganizationEditor key={team.id} teamId={team.id} />
  </>;
}

export function TeamOrganizationEditor({ teamId }: { teamId: string }) {
  const { directory, selected, setSelected, saved, loading, saving, error, notice, save,
    unavailable, refresh } = useTeamOrganization(teamId);

  const missingUnit = saved && directory && !directory.units.some(unit => unit.unit_id === saved);
  return <section className="rounded-2xl border border-slate-200 p-4" aria-label="Organigramma della squadra" aria-busy={loading || saving}>
    <h3 className="font-semibold">Collegamento all’organigramma</h3>
    <p className="text-sm text-slate-500">Settore, reparto e incarichi provengono da GAIA. Seleziona l’unità esplicita; i nomi non vengono abbinati automaticamente.</p>
    <label className="mt-3 block text-sm">Unità organizzativa
      <select className="mt-1 w-full rounded-xl border px-3 py-2" value={selected} disabled={unavailable} onChange={event => setSelected(event.target.value)}>
        <option value="">Da collegare</option>
        {missingUnit ? <option value={String(saved)} disabled>Unità collegata non disponibile</option> : null}
        {directory?.units.map(unit => <option key={unit.unit_id} value={unit.unit_id}>{unit.path.map(node => node.name).join(" / ")}</option>)}
      </select>
    </label>
    <div className="mt-3 flex gap-2">
      <button className="btn-primary" type="button" disabled={unavailable || selected === (saved ?? "")} onClick={() => void save()}>Salva collegamento</button>
      <button className="btn-secondary" type="button" disabled={loading || saving} onClick={refresh}>Aggiorna organigramma</button>
    </div>
    {loading ? <p role="status">Caricamento organigramma…</p> : null}
    {notice ? <p role="status">{notice}</p> : null}
    {error ? <p role="alert">{error}</p> : null}
  </section>;
}
