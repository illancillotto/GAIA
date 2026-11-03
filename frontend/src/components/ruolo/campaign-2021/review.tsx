"use client";

import { type FormEvent, useState } from "react";
import { approve, preview, type Approval, type CampaignReport, type CampaignRow } from "./client";

export function CampaignReview({ token, report, row }: { token: string; report: CampaignReport & { id: string }; row: CampaignRow }) {
  const [approval, setApproval] = useState<Approval | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [source, setSource] = useState("");
  const [fee, setFee] = useState("");
  const selectedTotal = source === "excel" ? row.amounts.total : row.current.engine?.saldo_amount;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const fields = new FormData(event.currentTarget);
    try {
      const result = await approve(token, report.id, {
        report_sha256: report.report_sha256, row_number: row.row,
        amount_source: String(fields.get("source")), notification_fee: String(fields.get("fee")),
        channel: String(fields.get("channel")), fee_evidence: String(fields.get("fee_evidence")),
        reason: String(fields.get("reason")), confirmed: true,
        resolutions: Object.fromEntries(row.reconciliation.reviews.map((key) => [key, String(fields.get(key))])),
      });
      setApproval(result);
    } catch (err) { setError(err instanceof Error ? err.message : "Approvazione non riuscita"); }
    finally { setBusy(false); }
  }
  async function showPreview() {
    setBusy(true); setError("");
    try {
      const blob = await preview(token, approval!.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a"); link.href = url; link.download = `BOZZA-2021-${row.number}.pdf`; link.click(); URL.revokeObjectURL(url);
    } catch (err) { setError(err instanceof Error ? err.message : "Anteprima non riuscita"); }
    finally { setBusy(false); }
  }
  return <section className="rounded-xl border bg-white p-4" aria-label={`Revisione ${row.number}`}>
    <h3 className="font-semibold">Verifica avviso {row.number} — {row.name}</h3>
    <p>Totale Excel senza spese: € {row.amounts.total}. Saldo GAIA: € {row.current.engine?.saldo_amount}.</p>
    <p>Differenza contabile F-J: € {row.amounts.difference}. La differenza non equivale a un incasso verificato.</p>
    {source && fee && <p role="status">Totale approvato prima delle spese: € {Number(selectedTotal).toFixed(2)}. Spese: € {fee}. Totale PDF: € {(Number(selectedTotal) + Number(fee)).toFixed(2)}.</p>}
    {error && <p role="alert">{error}</p>}
    {approval ? <div role="status"><p>Snapshot contabile approvato da operatore {approval.actor_id} il {approval.approved_at}. Nessun invio o notifica registrati.</p>
      <button type="button" disabled={busy} onClick={() => void showPreview()} className="btn-primary">Crea anteprima PDF</button></div>
      : <form onSubmit={(event) => void submit(event)} className="mt-4 grid gap-3 sm:grid-cols-2">
        <label>Importi da approvare<select name="source" required value={source} onChange={(event) => setSource(event.target.value)}><option value="" disabled>Scegli la fonte</option><option value="excel">Excel alla data di riferimento</option><option value="gaia">GAIA alla data di acquisizione</option></select></label>
        <label>Spese da aggiungere<select name="fee" required value={fee} onChange={(event) => setFee(event.target.value)}><option value="" disabled>Verifica la debenza</option><option value="0.00">€ 0,00</option><option value="11.55">€ 11,55</option></select></label>
        <label>Canale valutato<select name="channel" required defaultValue=""><option value="" disabled>Scegli il canale</option><option value="nessuno">Nessuno</option><option value="pec">PEC</option><option value="raccomandata">Raccomandata</option></select></label>
        <label>Riferimento verifica spese<input name="fee_evidence" required maxLength={2000} /></label>
        {row.reconciliation.reviews.map((key) => <label key={key}>Riferimento verifica: {key}<input name={key} required maxLength={2000} /></label>)}
        <label>Motivazione contabile e amministrativa<textarea name="reason" required maxLength={2000} /></label>
        <label><input type="checkbox" required />Confermo la verifica dei dati, delle differenze e delle spese indicate.</label>
        <button type="submit" className="btn-primary" disabled={busy}>Approva snapshot contabile</button>
      </form>}
  </section>;
}
