/** Archive credentials supplement the message without revising its attached notice. */
export function PortalAccessNote({ source }: { source: string }) {
  return source === "archive" ? <p className="text-sm text-slate-600">Codice utenza e PIN ICATASTO recuperati dall’archivio GAIA per questo contribuente. Disponibili per il blocco ICATASTO del messaggio; il PDF allegato resta invariato.</p> : null;
}
