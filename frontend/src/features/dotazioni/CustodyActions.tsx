"use client";

import { useState } from "react";
import { dotazioniApi } from "./api";
import type { Asset, Lookup } from "./types";

export function CustodyActions({ asset, operators, onChange }: { asset: Asset; operators: Lookup[]; onChange: () => void }) {
  const [holder, setHolder] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function act(action: "take" | "return" | "transfer") {
    setBusy(true); setError("");
    const body: { notes: string; holder_user_id?: number } = { notes };
    if (action !== "return" && holder) body.holder_user_id = Number(holder);
    try { await dotazioniApi.custody(asset.id, action, body); onChange(); }
    catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  }
  if (asset.vehicle_id) return <p>La gestione operativa del mezzo resta in Operazioni; non viene aperta una custodia parallela.</p>;
  return <section className="space-y-3 rounded border bg-white p-4" aria-busy={busy}>
    <h2 className="font-semibold">Custodia</h2>
    <label className="grid gap-1">Operatore destinatario<select disabled={busy} className="w-full rounded border p-2" value={holder} onChange={(event) => setHolder(event.target.value)}>
      <option value="">Me stesso (presa in consegna)</option>
      {operators.map((operator) => <option key={operator.id} value={operator.id}>{operator.name}</option>)}
    </select></label>
    <label className="grid gap-1">Note<input disabled={busy} className="w-full rounded border p-2" value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
    {asset.current_custody ? <div className="flex flex-wrap gap-3">
      <button className="min-h-11 rounded border px-4 py-2 disabled:opacity-50" disabled={busy} onClick={() => void act("return")}>Restituisci</button>
      <button className="min-h-11 rounded bg-green-800 px-4 py-2 text-white disabled:opacity-50" disabled={busy || !holder || Number(holder) === asset.current_custody.holder_user_id} onClick={() => void act("transfer")}>Passa a…</button>
    </div> : <button className="min-h-11 rounded bg-green-800 px-4 py-2 text-white disabled:opacity-50" disabled={busy || !asset.is_active || asset.status !== "available"} onClick={() => void act("take")}>Prendi in consegna</button>}
    {busy && <p role="status">Registrazione in corso…</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
