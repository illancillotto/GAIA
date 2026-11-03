"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSessionBootstrap } from "@/lib/use-session-bootstrap";
import { analyze, detail, history, retain, type CampaignHistory, type CampaignReport, type CampaignRow } from "./client";
import { CampaignReview } from "./review";

type Filters = { query: string; digital: string; kind: string; state: string; min: string; max: string };
export function matches(row: CampaignRow, filters: Filters): boolean {
  const text = `${row.number} ${row.name} ${row.tax_code}`.toUpperCase();
  return text.includes(filters.query.trim().toUpperCase())
    && (!filters.digital || String(row.digital) === filters.digital)
    && (!filters.kind || row.reconciliation.kind === filters.kind)
    && (!filters.state || (row.reconciliation.blockers.length > 0 ? "blocked" : "review") === filters.state)
    && (!filters.min || Number(row.amounts.total) >= Number(filters.min))
    && (!filters.max || Number(row.amounts.total) <= Number(filters.max));
}

export function CampaignTable({ report, token, canEdit }: { report: CampaignReport; token: string; canEdit: boolean }) {
  const [filters, setFilters] = useState<Filters>({ query: "", digital: "", kind: "", state: "", min: "", max: "" });
  const [selected, setSelected] = useState<CampaignRow | null>(null);
  const filtered = report.rows.filter((row) => matches(row, filters));
  function filter(key: keyof Filters, value: string) { setFilters((current) => ({ ...current, [key]: value })); }
  return <section className="space-y-3">
    <div className="flex flex-wrap gap-3">
      <label>Cerca numero o destinatario<input value={filters.query} onChange={(e) => filter("query", e.target.value)} /></label>
      <label>Digitale<select value={filters.digital} onChange={(e) => filter("digital", e.target.value)}><option value="">Tutti</option><option value="true">Sì</option><option value="false">No</option></select></label>
      <label>Tipo<select value={filters.kind} onChange={(e) => filter("kind", e.target.value)}><option value="">Tutti</option>{[...new Set(report.rows.map((r) => r.reconciliation.kind))].map((kind) => <option key={kind}>{kind}</option>)}</select></label>
      <label>Esito<select value={filters.state} onChange={(e) => filter("state", e.target.value)}><option value="">Tutti</option><option value="blocked">Bloccate</option><option value="review">Da approvare</option></select></label>
      <label>Totale minimo<input type="number" step="0.01" value={filters.min} onChange={(e) => filter("min", e.target.value)} /></label>
      <label>Totale massimo<input type="number" step="0.01" value={filters.max} onChange={(e) => filter("max", e.target.value)} /></label>
    </div>
    <p>{filtered.length} di {report.rows.length} posizioni. {report.rows.filter((r) => r.reconciliation.blockers.length > 0).length} bloccate.</p>
    <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr>{["Avviso", "Destinatario", "Tipo", "Residuo Excel", "Residuo inCASS", "Totale Excel senza spese", "Scarti Excel-GAIA", "Verifiche", "Azione"].map((h) => <th key={h} className="p-2 text-left">{h}</th>)}</tr></thead><tbody>
      {filtered.map((row) => <tr key={row.row} className="border-t align-top"><td className="p-2">{row.number}</td><td className="p-2"><span>{row.name}</span><br />{row.tax_code}</td><td className="p-2">{row.reconciliation.kind}</td><td>{row.amounts.residual}</td><td>{row.current.accounting?.importo_residuo ?? "Da verificare"}</td><td>{row.amounts.total}</td>
        <td>{Object.entries(row.reconciliation.deltas).filter(([, v]) => v !== "0.00").map(([k, v]) => <p key={k}>{k}: {v}</p>)}</td>
        <td>{[...row.reconciliation.blockers, ...row.reconciliation.reviews].map((key) => <p key={key}>{key}</p>)}</td>
        <td>{canEdit && report.id && <button type="button" className="btn-secondary" disabled={row.reconciliation.blockers.length > 0} onClick={() => setSelected(row)}>Verifica e approva {row.number}</button>}</td></tr>)}
    </tbody></table></div>
    {selected && report.id && <CampaignReview key={selected.row} token={token} report={{ ...report, id: report.id }} row={selected} />}
  </section>;
}

export function CampaignContent({ token, canEdit }: { token: string; canEdit: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [report, setReport] = useState<CampaignReport | null>(null);
  const [previous, setPrevious] = useState<CampaignHistory[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { let active = true; history(token).then((value) => { if (active) setPrevious(value); }).catch(() => { if (active) setError("Storico non disponibile"); }); return () => { active = false; }; }, [token]);
  async function perform(work: () => Promise<CampaignReport>) {
    setBusy(true); setError("");
    try { setReport(await work()); } catch (err) { setError(err instanceof Error ? err.message : "Operazione non riuscita"); }
    finally { setBusy(false); }
  }
  return <div className="space-y-5">
    <p>Importazione del perimetro, verifica delle differenze e anteprime da snapshot contabile approvato. Generazione, conferma, invio e notifica sono passaggi separati.</p>
    <Link className="btn-secondary" href="/ruolo/tributi">Torna ai tributi</Link>
    <Link className="btn-secondary" href="/ruolo/tributi/registro-avvisi">Apri storico e verifiche STEP</Link>
    {error && <p role="alert">{error}</p>}
    <div className="flex flex-wrap items-end gap-3">
      <label>File Excel 2021<input type="file" accept=".xlsx" disabled={busy} onChange={(e) => { setFile(e.target.files?.[0] ?? null); setReport(null); }} /></label>
      <button className="btn-primary" disabled={busy || !file} onClick={() => void perform(() => analyze(token, file!))}>Analizza senza importare</button>
      {canEdit && file && report && !report.id && <button className="btn-secondary" disabled={busy} onClick={() => void perform(() => retain(token, file, report.report_sha256))}>Conserva lo snapshot verificato</button>}
    </div>
    {busy && <p role="status">Verifica in corso...</p>}
    <nav aria-label="Snapshot precedenti" className="flex flex-wrap gap-2">{previous.map((item) => <button className="btn-secondary" key={item.id} disabled={busy} onClick={() => void perform(() => detail(token, item.id))}>{item.filename} — {item.created_at}</button>)}</nav>
    {report && <><section className="rounded-xl border bg-white p-4"><h2 className="text-xl font-semibold">Confronto avvisi 2021</h2>
      <p>{report.summary.rows} avvisi: {report.summary.ordinary} ordinari, {report.summary.digital} digitali. Totale Excel € {report.summary.total}, prima delle spese.</p>
      <p>Riferimento Excel: {report.summary.parameters.end}. Acquisizione GAIA/inCASS: {report.acquired_at}.</p>
      {report.summary.warnings.map((warning) => <p key={warning}>{warning}</p>)}<p className="break-all text-xs">SHA-256 Excel: {report.file_sha256}</p>
    </section><CampaignTable key={report.report_sha256} report={report} token={token} canEdit={canEdit} /></>}
  </div>;
}

export function CampaignWorkspace() {
  const session = useSessionBootstrap();
  if (session.status !== "ready" || !session.token || !session.currentUser) return <p role="status">Verifica accesso...</p>;
  const hasModule = session.currentUser.role === "super_admin" || session.currentUser.enabled_modules.includes("ruolo");
  if (!hasModule || !session.grantedSectionKeys.includes("ruolo.tributi.view")) return <p role="alert">Accesso non autorizzato.</p>;
  return <CampaignContent key={session.token} token={session.token} canEdit={session.grantedSectionKeys.includes("ruolo.tributi.manage_status")} />;
}
