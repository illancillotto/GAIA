"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { ParcelHistoryCadastre } from "./parcel-history-cadastre";
import { ParcelHistoryTaxes } from "./parcel-history-taxes";
import { useParcelHistory } from "./use-parcel-history";
import type { ParcelHistory, ParcelHistoryPage } from "@/types/parcel-history";

export function historyLink(params: URLSearchParams, changes: Record<string, string | null>) {
  const query = new URLSearchParams(params);
  query.set("vista", "storia");
  for (const [key, value] of Object.entries(changes)) {
    if (value === null) query.delete(key); else query.set(key, value);
  }
  return `/ruolo/particelle?${query}`;
}

function HistorySearch() {
  const params = useSearchParams();
  const router = useRouter();
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = new URLSearchParams({ vista: "storia" });
    for (const [name, value] of new FormData(event.currentTarget)) {
      if (String(value).trim()) query.set(name, String(value).trim());
    }
    router.push(`/ruolo/particelle?${query}`);
  }
  return <form onSubmit={submit} className="grid gap-3 rounded-2xl border bg-white p-4 sm:grid-cols-2 xl:grid-cols-[2fr_1fr_1fr_2fr_auto]">
    {[["comune", "Comune", "Es. Oristano"], ["foglio", "Foglio", "Es. 12"], ["particella", "Particella", "Es. 100"], ["search", "Contribuente o avviso", "Nome, codice fiscale o numero avviso"]].map(([name, label, placeholder]) => <label key={name} className="min-w-0 text-sm font-medium">{label}<input key={params.get(name) || ""} name={name} defaultValue={params.get(name) || ""} maxLength={name === "foglio" ? 10 : name === "particella" ? 20 : 100} className="mt-1 w-full rounded-lg border p-2.5 font-normal" placeholder={placeholder} /></label>)}
    <button className="btn-primary self-end">Cerca particella</button>
    <p className="text-xs text-slate-500 sm:col-span-2 xl:col-span-5">Cerca per riferimento catastale oppure per contribuente: apri una particella per vedere tutti gli anni disponibili. <Link href="/ruolo/particelle?vista=storia" className="underline">Azzera filtri</Link></p>
  </form>;
}

function HistoryResults({ result }: { result: ParcelHistoryPage }) {
  const params = useSearchParams();
  return <section aria-label="Risultati particelle" className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-semibold">{result.total} particelle trovate</h2><p className="text-sm text-slate-500">Pagina {result.page} di {Math.max(1, Math.ceil(result.total / result.page_size))}</p></div>
    {result.items.length ? <ul className="grid gap-3 lg:grid-cols-2">{result.items.map(row => <li key={row.id}><Link href={historyLink(params, { storia: row.id })} className="group flex h-full items-center justify-between gap-4 rounded-xl border bg-white p-5 transition hover:border-emerald-500 hover:shadow-sm focus-visible:outline-emerald-700">
      <div className="min-w-0"><h3 className="break-words font-semibold text-slate-900">{row.comune || "Comune non indicato"}</h3><p className="mt-1 text-sm">Foglio {row.foglio} · Particella {row.particella}{row.subalterno && ` · Sub ${row.subalterno}`}</p><p className="mt-3 text-xs text-slate-500">Prima / ultima presenza: {row.first_year} – {row.last_year} · {row.years_count} annualità</p></div><span className="shrink-0 text-sm font-semibold text-emerald-800">Apri storia →</span>
    </Link></li>)}</ul> : <div className="rounded-xl border border-dashed bg-white p-8 text-center"><h3 className="font-semibold">Nessuna particella trovata</h3><p className="mt-2 text-sm text-slate-600">Verifica comune, foglio e particella o rimuovi alcuni filtri. L’assenza dai dati importati non dimostra una cessazione.</p></div>}
    <nav aria-label="Pagine dei risultati" className="flex items-center justify-between">{result.page > 1 ? <Link className="btn-secondary" href={historyLink(params, { page: String(result.page - 1) })}>Precedente</Link> : <span />}
      {result.page * result.page_size < result.total && <Link className="btn-secondary" href={historyLink(params, { page: String(result.page + 1) })}>Successiva</Link>}</nav>
  </section>;
}

function HistoryDetail({ history }: { history: ParcelHistory }) {
  const params = useSearchParams();
  const [tab, setTab] = useState("taxes");
  const reference = history.reference;
  return <div className="space-y-5">
    <Link className="inline-flex text-sm font-medium text-emerald-800 underline" href={historyLink(params, { storia: null })}>← Torna ai risultati</Link>
    <header className="rounded-2xl border bg-white p-5 sm:p-6"><p className="text-sm text-slate-500">Storia della particella</p><h2 className="mt-1 text-xl font-semibold">{reference.comune_nome} · Foglio {reference.foglio} · Particella {reference.particella}</h2>
      <p className="mt-2 text-sm text-slate-600">Codice comune: {reference.comune_codice || "non indicato"} · Sezione: {reference.sezione || "non indicata"} · Subalterno: {reference.subalterno || "non indicato"}</p>
      {history.identity_incomplete && <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Identificativo incompleto. Questa riga resta separata dalle altre particelle: completa la verifica prima di collegare documenti.</p>}
      <dl className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl bg-emerald-50 p-4"><dt className="text-xs text-emerald-800">Prima presenza nei dati</dt><dd className="mt-1 text-xl font-semibold">{history.first_year}</dd></div>
        <div className="rounded-xl bg-slate-50 p-4"><dt className="text-xs text-slate-600">Ultima presenza nei dati</dt><dd className="mt-1 text-xl font-semibold">{history.last_year}</dd></div>
        <div className="rounded-xl bg-slate-50 p-4"><dt className="text-xs text-slate-600">Cessazione tributaria</dt><dd className="mt-1 font-semibold">Non documentata</dd></div>
      </dl>
      <p className="mt-3 text-xs text-slate-500">La prima presenza disponibile non certifica la data di registrazione; l’ultima non certifica la cessazione.</p>
    </header>
    <HistoryTabs tab={tab} select={setTab} />
    <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>{tab === "taxes" ? <ParcelHistoryTaxes history={history} /> : <ParcelHistoryCadastre history={history} />}</div>
  </div>;
}

function HistoryTabs({ tab, select }: { tab: string; select: (tab: string) => void }) {
  const next: Record<string, string> = { ArrowRight: tab === "taxes" ? "cadastre" : "taxes", ArrowLeft: tab === "taxes" ? "cadastre" : "taxes", Home: "taxes", End: "cadastre" };
  return <div role="tablist" aria-label="Storia da consultare" className="flex flex-wrap gap-2 rounded-xl bg-slate-100 p-1.5">{[["taxes", "Tributi nel tempo"], ["cadastre", "Proprietà catastale"]].map(([value, label]) => <button key={value} id={`tab-${value}`} type="button" role="tab" tabIndex={tab === value ? 0 : -1} aria-selected={tab === value} aria-controls={`panel-${value}`} onClick={() => select(value)} onKeyDown={event => {
    const target = next[event.key];
    if (!target) return;
    event.preventDefault(); select(target);
    event.currentTarget.parentElement!.querySelector<HTMLButtonElement>(`#tab-${target}`)!.focus();
  }} className={`rounded-lg px-4 py-3 text-sm font-semibold ${tab === value ? "bg-white text-emerald-900 shadow-sm" : "text-slate-600 hover:bg-white/60"}`}>{label}</button>)}</div>;
}

export function ParcelHistoryWorkspace() {
  const { data, loading, error, selected, retry } = useParcelHistory();
  return <RuoloModulePage title="La storia delle particelle" description="Segui una particella nel tempo: contribuenti, tributi e passaggi di proprietà documentati." requiredSection="ruolo.avvisi">
    <div className="space-y-6">
      <nav aria-label="Consultazione particelle" className="flex flex-wrap gap-2"><Link className="btn-primary" aria-current="page" href="/ruolo/particelle?vista=storia">Storia delle particelle</Link><Link className="btn-secondary" href="/ruolo/particelle?vista=annuale">Consultazione annuale</Link><Link className="btn-secondary" href="/ruolo/particelle?vista=all">Controlli e recupero posizioni</Link></nav>
      {!selected && <HistorySearch />}
      {loading && <p role="status" className="rounded-xl border bg-white p-6 text-slate-600">Caricamento della storia…</p>}
      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-5"><p>{error}</p><button type="button" onClick={retry} className="btn-secondary mt-3">Riprova</button>{selected && <Link className="ml-3 underline" href="/ruolo/particelle?vista=storia">Torna alla ricerca</Link>}</div>}
      {!loading && data && (selected ? <HistoryDetail key={selected} history={data as ParcelHistory} /> : <HistoryResults result={data as ParcelHistoryPage} />)}
    </div>
  </RuoloModulePage>;
}
