import Link from "next/link";
import type { Asset } from "./types";
import { custodyDate, statusLabel, typeLabel } from "./presentation";

const detailFields = [
  ["asset_type", "Tipo"], ["brand", "Marca"], ["model", "Modello"],
  ["serial_number", "Seriale"], ["imei", "IMEI"], ["phone_number", "Telefono"],
  ["mac_address", "MAC"], ["plate_number", "Targa"],
  ["description", "Descrizione"], ["notes", "Note"],
] as const;

export function AssetSummary({ asset }: { asset: Asset }) {
  return <section className="space-y-4">
    <h1 className="break-words text-2xl font-semibold">{asset.asset_code} · {asset.name}</h1>
    <p>Bene del Consorzio · {asset.is_active ? statusLabel(asset.effective_status) : "Disattivato"}</p>
    <p>Unità / squadra: {asset.assigned_org_unit_name ?? "Non assegnata"}</p>
    <p>Custode corrente: {asset.current_custody?.holder_name ?? "Nessuno"}</p>
    {asset.current_custody && <p>Dalle: {custodyDate(asset.current_custody.taken_at)} (ora italiana)</p>}
    <details className="rounded border p-3">
      <summary className="cursor-pointer font-medium">Caratteristiche e note</summary>
      <dl className="mt-3 grid gap-3 md:grid-cols-3">{detailFields.map(([key, label]) => <div key={key}><dt className="text-gray-500">{label}</dt><dd className="break-words">{key === "asset_type" ? typeLabel(asset.asset_type) : asset[key] ?? "—"}</dd></div>)}</dl>
    </details>
    <div className="flex flex-wrap gap-4">
      {asset.network_device_id && <Link href={`/network/devices/${asset.network_device_id}`} className="underline">Scheda Network</Link>}
      {asset.vehicle_id && <Link href={`/operazioni/mezzi/${asset.vehicle_id}`} className="underline">Mezzo in Operazioni · {asset.plate_number}</Link>}
      <Link href={`/dotazioni/by-code/${encodeURIComponent(asset.asset_code)}`} className="underline">Link stabile per QR</Link>
    </div>
  </section>;
}
