"use client";

import { type ShiftWorkerType } from "@/lib/api/presenze-shift-workers";
import { useShiftWorkerAssignment } from "./use-shift-worker-assignment";
import type { PresenzeDailyRecord } from "@/types/api";

type Props = { record: PresenzeDailyRecord; disabled: boolean; onSaved: (record: PresenzeDailyRecord) => void };
export function ShiftWorkerControl({ record, disabled, onSaved }: Props) {
  const { kind, setKind, from, setFrom, to, setTo, error, saving, first, last, locked, save } = useShiftWorkerAssignment(record, disabled, onSaved);
  return <fieldset className="rounded border p-2 text-sm" disabled={disabled || saving || locked}>
    <legend>Turnista</legend>
    <p>Teorico di 7 ore; buono pasto con almeno 7 ore ordinarie effettive dal 26/08/2026. Orari dalle timbrature INAZ.</p>
    {locked && <p>Assegnazione gestita da GATE: modificarla da GATE.</p>}
    <label>Tipologia <select aria-label="Tipologia turnista" value={kind} onChange={event => setKind(event.target.value as ShiftWorkerType)}>
      <option value="none">Non turnista</option><option value="acquaiolo">Acquaiolo</option><option value="telecontrollo">Telecontrollo</option>
    </select></label>
    <label>Dal <input aria-label="Turnista dal" type="date" min={first} max={last} value={from} onChange={event => setFrom(event.target.value)} /></label>
    <label>Al <input aria-label="Turnista al" type="date" min={first} max={last} value={to} onChange={event => setTo(event.target.value)} /></label>
    <button type="button" onClick={() => { setFrom(first); setTo(last); }}>Tutto il mese</button>
    <button type="button" onClick={() => void save()}>Salva turnista</button>
    {saving && <p role="status">Salvataggio…</p>}{error && <p role="alert">{error}</p>}
  </fieldset>;
}
