"use client";

import { useCallback, useState } from "react";
import { dotazioniApi } from "./api";
import { useResource } from "./use-resource";
import { custodyDate } from "./presentation";

export function custodyDuration(taken: string, returned: string | null): string {
  if (!returned) return "In corso";
  const minutes = Math.max(0, Math.floor((Date.parse(returned) - Date.parse(taken)) / 60000));
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

export function CustodyHistory({ id, revision }: { id: string; revision: number }) {
  const [page, setPage] = useState(1);
  const history = useResource(useCallback(() => dotazioniApi.history(id, page), [id, page]), revision);
  return <section className="space-y-2"><h2 className="font-semibold">Storico custodie</h2>
    {history.loading && <p>Caricamento storico…</p>}
    {history.error && <p role="alert">{history.error}</p>}
    {history.data && <><p className="text-sm text-gray-600">Date e orari italiani. Lo storico delle custodie è conservato anche dopo la restituzione.</p><div className="overflow-x-auto rounded border" role="region" aria-label="Storico custodie" tabIndex={0}><table className="w-full min-w-[760px] text-left [&_td]:p-2"><thead><tr>
      {["Operatore", "Preso", "Restituito", "Durata", "Passaggio da", "Note", "Note restituzione"].map((label) => <th key={label} scope="col" className="p-2">{label}</th>)}
    </tr></thead><tbody>{history.data.items.map((item) => <tr key={item.id} className="border-t">
      <td className="p-2">{item.holder_name}</td><td className="whitespace-nowrap">{custodyDate(item.taken_at)}</td><td className="whitespace-nowrap">{custodyDate(item.returned_at)}</td>
      <td className="whitespace-nowrap font-medium">{custodyDuration(item.taken_at, item.returned_at)}</td><td>{item.handover_from_name ?? "—"}</td>
      <td>{item.notes ?? "—"}</td><td>{item.return_notes ?? "—"}</td>
    </tr>)}</tbody></table></div>
      {history.data.total === 0 && <p>Nessuna custodia registrata.</p>}
      <p role="status">{history.data.total} custodie · pagina {page}</p>
      <button disabled={page === 1} onClick={() => setPage((current) => current - 1)}>Precedente</button>{" "}
      <button disabled={page * 25 >= history.data.total} onClick={() => setPage((current) => current + 1)}>Successiva</button>
    </>}
  </section>;
}
