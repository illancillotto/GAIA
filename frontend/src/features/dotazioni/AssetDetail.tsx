"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { dotazioniApi } from "./api";
import { AssetForm } from "./AssetForm";
import { AssetSummary } from "./AssetSummary";
import { CustodyActions } from "./CustodyActions";
import { CustodyHistory } from "./CustodyHistory";
import { useResource } from "./use-resource";
import type { AssetInput } from "./types";

export function AssetDetail({ id, code }: { id?: string; code?: string }) {
  const [revision, setRevision] = useState(0);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const resource = useResource(useCallback(() => Promise.all([
    code === undefined ? dotazioniApi.asset(id!) : dotazioniApi.byCode(code),
    dotazioniApi.lookups(),
  ]), [id, code]), revision);
  function refresh() { setRevision((current) => current + 1); }
  async function disable(assetId: string) {
    setBusy(true); setError("");
    try { await dotazioniApi.update(assetId, { is_active: false }); refresh(); }
    catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  }
  if (resource.loading) return <p>Caricamento dotazione…</p>;
  if (resource.error) return <p role="alert">{resource.error}</p>;
  const [asset, lookups] = resource.data!;
  if (!lookups.permissions.includes("dotazioni.view")) return <p>Non sei autorizzato a consultare le dotazioni.</p>;
  return <div className="space-y-5">
    <Link href="/dotazioni" className="text-green-800 underline">Tutte le dotazioni</Link>
    <AssetSummary asset={asset} />
    {lookups.permissions.includes("dotazioni.custody") && <CustodyActions asset={asset} operators={lookups.users} onChange={refresh} />}
    {lookups.permissions.includes("dotazioni.manage") && <div className="flex gap-4">
      <button onClick={() => setEditing(true)}>Modifica dotazione</button>
      <button disabled={busy || !asset.is_active || !!asset.current_custody} onClick={() => void disable(asset.id)}>Disattiva dotazione</button>
    </div>}
    {error && <p role="alert">{error}</p>}
    {editing && <AssetForm asset={asset} lookups={lookups} canAssign={lookups.permissions.includes("dotazioni.assign")} onCancel={() => setEditing(false)} onSave={async (input) => {
      const changes: Partial<AssetInput> = { ...input };
      delete changes.asset_code;
      await dotazioniApi.update(asset.id, changes); setEditing(false); refresh();
    }} />}
    {lookups.permissions.includes("dotazioni.history") && <CustodyHistory id={asset.id} revision={revision} />}
  </div>;
}
