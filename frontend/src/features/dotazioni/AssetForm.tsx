"use client";

import { useState, type FormEvent } from "react";
import type { Asset, AssetInput, Lookups } from "./types";
import { statusLabel } from "./presentation";

const fields = [
  ["asset_code", "Codice"], ["asset_type", "Tipologia"], ["name", "Nome"],
  ["description", "Descrizione"], ["brand", "Marca"], ["model", "Modello"],
  ["serial_number", "Seriale"], ["imei", "IMEI"], ["phone_number", "Telefono"],
  ["mac_address", "MAC"], ["notes", "Note"],
] as const;
const relations = [
  ["assigned_org_unit_id", "Unità organizzativa", "org_units"],
  ["network_device_id", "Dispositivo Network", "network_devices"],
  ["vehicle_id", "Veicolo", "vehicles"],
] as const;

function assetInput(form: HTMLFormElement, canAssign: boolean): AssetInput {
  const values = Object.fromEntries(new FormData(form));
  const input = { ...values } as unknown as AssetInput;
  input.network_device_id = values.network_device_id ? Number(values.network_device_id) : null;
  input.vehicle_id = values.vehicle_id ? String(values.vehicle_id) : null;
  if (canAssign) input.assigned_org_unit_id = values.assigned_org_unit_id ? String(values.assigned_org_unit_id) : null;
  else delete input.assigned_org_unit_id;
  return input;
}

export function AssetForm({ asset, lookups, canAssign, onSave, onCancel }: {
  asset?: Asset; lookups: Lookups; canAssign: boolean;
  onSave: (input: AssetInput) => Promise<void>; onCancel: () => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = assetInput(event.currentTarget, canAssign);
    setSaving(true);
    setError("");
    try { await onSave(input); } catch (failure) { setError((failure as Error).message); }
    finally { setSaving(false); }
  }
  return <form onSubmit={submit} className="space-y-3 rounded border bg-white p-4">
    <h2 className="text-lg font-semibold">{asset ? "Modifica dotazione" : "Nuova dotazione"}</h2>
    <div className="grid gap-3 md:grid-cols-2">
      {fields.map(([key, label], index) => <label key={key} className="grid gap-1">{label}
        <input name={key} defaultValue={asset?.[key] ?? ""} required={index < 3} readOnly={key === "asset_code" && !!asset} className="rounded border p-2" />
      </label>)}
      {relations.map(([key, label, lookup]) => <label key={key} className="grid gap-1">{label}
        <select name={key} defaultValue={asset?.[key] ?? ""} disabled={key === "assigned_org_unit_id" && !canAssign} className="rounded border p-2">
          <option value="">Nessuno</option>
          {lookups[lookup].map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
      </label>)}
      <label className="grid gap-1">Stato amministrativo<select name="status" defaultValue={asset?.status ?? "available"} className="rounded border p-2">
        {["available", "maintenance", "damaged", "lost", "retired"].map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}
      </select></label>
    </div>
    {error && <p role="alert">{error}</p>}
    <button disabled={saving} className="rounded bg-green-800 px-4 py-2 text-white">Salva</button>{" "}
    <button type="button" onClick={onCancel} disabled={saving}>Annulla</button>
  </form>;
}
