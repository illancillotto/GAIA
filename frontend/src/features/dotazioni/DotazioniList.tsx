"use client";

import { useCallback, useState } from "react";
import { dotazioniApi } from "./api";
import { AssetForm } from "./AssetForm";
import { AssetTable } from "./AssetTable";
import { useResource } from "./use-resource";
import { statusLabel } from "./presentation";

export function DotazioniList() {
  const [filters, setFilters] = useState({ search: "", asset_type: "", status: "", org_unit_id: "", holder_user_id: "", active: "true" });
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [creating, setCreating] = useState(false);
  const metadata = useResource(useCallback(() => dotazioniApi.lookups(), []));
  const assets = useResource(useCallback(() => {
    const params = new URLSearchParams({ page: String(page), page_size: "25" });
    Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); });
    return dotazioniApi.list(params);
  }, [filters, page]), revision);
  function filter(key: keyof typeof filters, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
    setPage(1);
  }
  if (metadata.loading) return <p>Caricamento permessi…</p>;
  if (metadata.error) return <p role="alert">{metadata.error}</p>;
  const lookups = metadata.data!;
  if (!lookups.permissions.includes("dotazioni.view")) return <p>Non sei autorizzato a consultare le dotazioni.</p>;
  return <div className="space-y-4">
    <p>Beni del Consorzio: assegnazione organizzativa e custodia temporanea sono distinte.</p>
    <div className="flex flex-wrap gap-3">
      <button aria-pressed={filters.status === ""} onClick={() => filter("status", "")}>Tutti</button>
      <button aria-pressed={filters.status === "in_use"} onClick={() => filter("status", "in_use")}>In custodia</button>
      <button aria-pressed={filters.status === "available"} onClick={() => filter("status", "available")}>Disponibili</button>
      {lookups.permissions.includes("dotazioni.manage") && <button onClick={() => setCreating(true)}>Nuova dotazione</button>}
    </div>
    {creating && <AssetForm lookups={lookups} canAssign={lookups.permissions.includes("dotazioni.assign")} onCancel={() => setCreating(false)} onSave={async (input) => {
      await dotazioniApi.create(input); setCreating(false); setRevision((current) => current + 1);
    }} />}
    <div className="grid gap-3 md:grid-cols-3">
      <label>Cerca<input className="block w-full rounded border p-2" value={filters.search} onChange={(event) => filter("search", event.target.value)} /></label>
      <label>Tipologia<input className="block w-full rounded border p-2" value={filters.asset_type} onChange={(event) => filter("asset_type", event.target.value)} placeholder="phone, radio, tool…" /></label>
      <label>Stato<select className="block w-full rounded border p-2" value={filters.status} onChange={(event) => filter("status", event.target.value)}>
        <option value="">Tutti</option>{["available", "in_use", "maintenance", "lost", "damaged", "retired"].map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}
      </select></label>
      <label>Unità / squadra<select className="block w-full rounded border p-2" value={filters.org_unit_id} onChange={(event) => filter("org_unit_id", event.target.value)}>
        <option value="">Tutte</option>{lookups.org_units.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select></label>
      <label>Custode<select className="block w-full rounded border p-2" value={filters.holder_user_id} onChange={(event) => filter("holder_user_id", event.target.value)}>
        <option value="">Tutti</option>{lookups.users.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select></label>
      <label>Attivi<select className="block w-full rounded border p-2" value={filters.active} onChange={(event) => filter("active", event.target.value)}>
        <option value="true">Sì</option><option value="false">No</option><option value="">Tutti</option>
      </select></label>
    </div>
    {assets.error && <p role="alert">{assets.error}</p>}
    {assets.loading && <p>Caricamento dotazioni…</p>}
    {filters.org_unit_id && <h2 className="text-lg font-semibold">Dotazioni dell’unità / squadra selezionata</h2>}
    {assets.data && <><AssetTable assets={assets.data.items} /><p role="status">{assets.data.total} dotazioni · pagina {page}</p>
      <button disabled={page === 1} onClick={() => setPage((current) => current - 1)}>Precedente</button>{" "}
      <button disabled={page * 25 >= assets.data.total} onClick={() => setPage((current) => current + 1)}>Successiva</button>
    </>}
  </div>;
}
