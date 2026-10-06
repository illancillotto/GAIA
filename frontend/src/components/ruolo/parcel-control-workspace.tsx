"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";

import { useAppShellContext } from "@/components/layout/app-shell-context";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { ParcelControlDetail } from "@/components/ruolo/parcel-control-detail";
import { CONTROL_LABELS, ParcelControlTable } from "@/components/ruolo/parcel-control-table";
import { getStoredAccessToken } from "@/lib/auth";
import { controlCommand, parcelControlRequest } from "@/lib/parcel-control-api";
import type { ControlCase, ControlPage, ControlProposal, ControlRow, ControlView } from "@/types/parcel-control";

const VIEWS = { all: "Storico 2011–2025", missing: "Non rilevate nel 2025", cf: "CF anomali",
  cases: "Pratiche aperte", visure: "Pratiche con visure", recovered: "Particelle recuperate",
  proposals: "Proposte", closed: "Concluse / escluse", annuale: "Consultazione annuale" };

export function ParcelControlWorkspace({ annualView }: { annualView: ReactNode }) {
  const params = useSearchParams();
  const explicit = params.get("vista");
  const legacy = ["anno", "comune", "foglio", "particella", "match_status", "match_reason", "unmatched_only"].some(key => params.has(key));
  const view = explicit || (legacy ? "annuale" : "all");
  return <div className="space-y-5">
    <nav aria-label="Viste particelle" className="flex flex-wrap gap-2">{Object.entries(VIEWS).map(([key, label]) =>
      <Link key={key} href={`/ruolo/particelle?vista=${key}`} aria-current={view === key ? "page" : undefined} className="btn-secondary">{label}</Link>)}</nav>
    {view === "annuale" ? annualView : <ControlContent view={view as ControlView} />}
  </div>;
}

function useControlWorkspace(view: ControlView) {
  const router = useRouter();
  const params = useSearchParams();
  const [result, setResult] = useState<ControlPage | null>(null);
  const [proposalRows, setProposalRows] = useState<ControlProposal[]>([]);
  const [practice, setPractice] = useState<ControlCase | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const caseId = params.get("pratica");
  const page = Math.max(1, Number(params.get("pagina") || 1));
  const search = params.get("ricerca") || "";

  useEffect(() => {
    let active = true;
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(true);
    setError("");
    const path = caseId ? `/pratiche/${caseId}` : controlQuery(view, page, search);
    parcelControlRequest<ControlCase | ControlPage>(token, path).then(value => {
      if (!active) return;
      if (caseId) setPractice(value as ControlCase);
      else {
        setPractice(null);
        setResult(value as ControlPage);
        if (view === "proposals") setProposalRows((value as unknown as { items: ControlProposal[] }).items);
      }
    }).catch(reason => { if (active) setError(String(reason.message)); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [caseId, view, page, search, revision]);

  async function execute(path: string, reason: string, data: Record<string, unknown>) {
    const token = getStoredAccessToken();
    if (!token) { setError("Accesso richiesto"); return; }
    setBusy(true);
    setError("");
    try {
      const value = await parcelControlRequest<ControlCase>(token, path, controlCommand(reason, data, practice?.version));
      if (value.id) {
        setPractice(value);
        router.push(`/ruolo/particelle?vista=cases&pratica=${value.id}`);
      } else {
        setRevision(previous => previous + 1);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Operazione non riuscita");
    } finally { setBusy(false); }
  }

  function searchRows(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = new FormData(event.currentTarget).get("ricerca") as string;
    router.push(`/ruolo/particelle?vista=${view}&ricerca=${encodeURIComponent(query)}`);
  }

  function open(item: ControlRow) {
    void execute(`/${item.id}/pratica`, "Apertura istruttoria di controllo particella", {});
  }

  return { result, proposalRows, practice, busy, error, search, page, searchRows, open, execute,
    refresh: () => setRevision(previous => previous + 1) };
}

function controlQuery(view: ControlView, page: number, search: string) {
  return `${view === "cf" ? "/avvisi" : ""}?view=${view}&page=${page}&search=${encodeURIComponent(search)}`;
}

function ControlContent({ view }: { view: ControlView }) {
  const { currentUser, grantedSectionKeys } = useAppShellContext();
  const editable = currentUser?.role === "super_admin" || grantedSectionKeys.includes("ruolo.tributi.manage_status");
  const { result, proposalRows, practice, busy, error, search, page, searchRows, open, execute, refresh } = useControlWorkspace(view);

  return <RuoloModulePage title="Particelle — storico e recupero posizioni" description="Controllo persistente dello storico 2011–2025. Ruolo corrente: 2025." requiredSection="ruolo.avvisi">
    <div className="space-y-5">
      <p className="rounded-xl bg-amber-50 p-4">Un&apos;assenza non dimostra un&apos;omissione. Catasto, titolarità e territorio richiedono verifiche separate.</p>
      {error && <p role="alert" className="text-red-700">{error}</p>}
      {busy && <p role="status">Elaborazione in corso…</p>}
      {practice ? <>
        <Link href="/ruolo/particelle?vista=cases">Torna alle pratiche</Link>
        <button className="btn-secondary" disabled={busy} onClick={refresh}>Aggiorna esiti</button>
        <ParcelControlDetail practice={practice} busy={busy} editable={editable} save={(action, data, reason) => execute(`/pratiche/${practice.id}/${action}`, reason, data)} />
      </> : <ControlList {...{ searchRows, search, editable, busy, execute, result, view, proposalRows, open, page }} />}
    </div>
  </RuoloModulePage>;
}

function ControlList({ searchRows, search, editable, busy, execute, result, view, proposalRows, open, page }: {
  searchRows: (event: FormEvent<HTMLFormElement>) => void; search: string; editable: boolean; busy: boolean;
  execute: (path: string, reason: string, data: Record<string, unknown>) => Promise<void>;
  result: ControlPage | null; view: ControlView; proposalRows: ControlProposal[];
  open: (item: ControlRow) => void; page: number;
}) {
  return <>
    <form onSubmit={searchRows} className="flex gap-2"><input aria-label="Cerca particella" name="ricerca" defaultValue={search} className="form-control" /><button className="btn-secondary">Cerca</button></form>
    {editable && <button disabled={busy} className="btn-primary" onClick={() => void execute("/analisi", "Aggiornamento indice storico delle particelle", {})}>Aggiorna analisi dello storico</button>}
    <p>{result?.total || 0} risultati complessivi · Analisi: {result?.refreshed_at || "non ancora eseguita"}</p>
    <p>Le annualità senza attestazione di completezza mostrano “Non verificabile”.</p>
    {result?.sources_changed && <p className="rounded-xl bg-amber-50 p-3">Le fonti sono cambiate: aggiorna l&apos;analisi prima di valutare le assenze.</p>}
    {view === "proposals" ? proposalRows.map(proposal => <p key={proposal.id}><Link href={`/ruolo/particelle?vista=cases&pratica=${proposal.case_id}`}>{proposal.label} · {proposal.year} · {CONTROL_LABELS[proposal.status]}</Link></p>)
      : view === "cf" ? <NoticeAnomalies page={result} busy={busy || !editable} execute={execute} />
        : <ParcelControlTable items={result?.items || []} open={open} busy={busy || !editable} />}
    <div className="flex gap-3"><Link href={`/ruolo/particelle?vista=${view}&pagina=${Math.max(1, page - 1)}&ricerca=${encodeURIComponent(search)}`}>Precedente</Link>
      <span>Pagina {page}</span>{page * 50 < (result?.total || 0) && <Link href={`/ruolo/particelle?vista=${view}&pagina=${page + 1}&ricerca=${encodeURIComponent(search)}`}>Successiva</Link>}</div>
    {editable && <CoverageForm busy={busy} save={execute} />}
  </>;
}

function NoticeAnomalies({ page, busy, execute }: { page: ControlPage | null; busy: boolean;
  execute: (path: string, reason: string, data: Record<string, unknown>) => Promise<void> }) {
  return <section className="rounded-xl border bg-white p-4"><h2>Avvisi con codice fiscale anomalo</h2>
    <p>Sono inclusi anche gli avvisi senza dettaglio delle particelle.</p>
    {(page?.notices || []).map(notice => <div key={notice.id} className="mt-3 border-t pt-3">
      <Link href={`/ruolo/avvisi/${notice.id}`}>{notice.codice_cnc} · {notice.year}</Link>
      <p>{notice.name} · CF {notice.tax_code.original || "mancante"} · {CONTROL_LABELS[notice.tax_code.anomaly]}</p>
      <button className="btn-secondary" disabled={busy} onClick={() => void execute(`/avvisi/${notice.id}/pratica`, "Apertura istruttoria da avviso con codice fiscale anomalo", {})}>Apri pratica dell&apos;avviso</button>
    </div>)}
  </section>;
}

function CoverageForm({ busy, save }: { busy: boolean; save: (path: string, reason: string, data: Record<string, unknown>) => Promise<void> }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>;
    void save(`/annualita/${values.year}/certificazione`, values.reason, { source: values.source });
  }
  return <details className="rounded-xl border bg-white p-4"><summary>Attesta completezza di un&apos;annualità</summary>
    <p>Attestare solo dopo aver verificato la copertura dell&apos;intero ruolo e il dettaglio delle particelle.</p>
    <form onSubmit={submit} className="mt-3 grid gap-3 md:grid-cols-2">
      <label>Annualità<input name="year" type="number" min="2011" max="2025" defaultValue="2025" required className="form-control" /></label>
      <label>Fonte e versione verificata<input name="source" required className="form-control" /></label>
      <label>Motivazione<input name="reason" required minLength={3} className="form-control" /></label>
      <button disabled={busy} className="btn-secondary">Registra attestazione</button>
    </form>
  </details>;
}
