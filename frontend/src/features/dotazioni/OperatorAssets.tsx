"use client";

import { useCallback } from "react";
import { dotazioniApi } from "./api";
import { AssetTable } from "./AssetTable";
import { useResource } from "./use-resource";

export function OperatorAssets({ userId }: { userId: number | null }) {
  const resource = useResource(useCallback(() => userId === null
    ? Promise.resolve({ items: [], total: 0 }) : dotazioniApi.operatorAssets(userId), [userId]));
  return <section className="space-y-3 rounded border bg-white p-4"><h2 className="font-semibold">Dotazioni in custodia</h2>
    {userId === null && <p>Identità GAIA non collegata: custodie non consultabili.</p>}
    {resource.loading && <p>Caricamento dotazioni…</p>}
    {resource.error && <p role="alert">{resource.error}</p>}
    {userId !== null && resource.data && <><AssetTable assets={resource.data.items} /><p>{resource.data.total} dotazioni</p></>}
  </section>;
}
