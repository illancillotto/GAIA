import Link from "next/link";
import type { Asset } from "./types";
import { custodyDate, statusLabel, typeLabel } from "./presentation";

export function AssetTable({ assets }: { assets: Asset[] }) {
  return <div className="overflow-x-auto rounded border" role="region" aria-label="Elenco dotazioni" tabIndex={0}><table className="w-full min-w-[640px] text-left [&_td]:p-2">
    <thead><tr>{["Dotazione", "Tipo", "Unità", "Custode", "Da", "Stato"].map((label) => <th key={label} scope="col" className="p-2">{label}</th>)}</tr></thead>
    <tbody>{assets.map((asset) => <tr key={asset.id} className="border-t">
      <td className="p-2"><Link className="text-green-800 underline" href={`/dotazioni/assets/${asset.id}`}>{asset.asset_code} · {asset.name}</Link></td>
      <td>{typeLabel(asset.asset_type)}</td><td>{asset.assigned_org_unit_name ?? "—"}</td>
      <td>{asset.current_custody?.holder_name ?? "—"}</td><td className="whitespace-nowrap">{custodyDate(asset.current_custody?.taken_at ?? null)}</td>
      <td>{asset.is_active ? statusLabel(asset.effective_status) : "Disattivato"}</td>
    </tr>)}</tbody>
  </table>{assets.length === 0 && <p className="p-4">Nessuna dotazione trovata.</p>}</div>;
}
