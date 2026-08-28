"use client";

import type { InterrogazioneState, InterrogazioneViewSource } from "@/components/catasto/gis/use-interrogazione";
import type { SchedaTerritorialeState } from "@/components/catasto/gis/use-scheda-territoriale";

const STATUS_LABELS = {
  loading: "In caricamento",
  ok: "Risultato disponibile",
  empty: "Nessun risultato",
  failed: "Sorgente non raggiungibile",
  skipped: "Non interrogabile",
} as const;

function SourceBlock({ source }: { source: InterrogazioneViewSource }) {
  return (
    <article className="rounded-xl border border-stone-200 bg-white p-3">
      <div className="flex items-start justify-between gap-3">
        <h4 className="text-sm font-bold text-slate-900">{source.title}</h4>
        <span data-status={source.status} className="rounded-full bg-stone-100 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-stone-700">
          {STATUS_LABELS[source.status]}
        </span>
      </div>
      {source.message ? <p className="mt-2 text-xs text-slate-600">{source.message}</p> : null}
      {source.status === "ok" ? (
        <div className="mt-2 space-y-2">
          {source.data.map((row, index) => (
            <dl key={index} className="grid grid-cols-[minmax(7rem,auto)_1fr] gap-x-3 gap-y-1 rounded-lg bg-[#f5f7f2] p-2 text-xs">
              {Object.entries(row).map(([key, value]) => (
                <div className="contents" key={key}>
                  <dt className="font-semibold text-slate-500">{key.replaceAll("_", " ")}</dt>
                  <dd className="break-words text-slate-800">{value == null ? "-" : String(value)}</dd>
                </div>
              ))}
            </dl>
          ))}
        </div>
      ) : null}
      {source.attribution ? <p className="mt-3 border-t border-stone-100 pt-2 text-[10px] leading-4 text-slate-500">{source.attribution}</p> : null}
    </article>
  );
}

function Sources({ items }: { items: InterrogazioneViewSource[] }) {
  if (!items.length) return <p className="text-sm text-slate-600">Nessuna sorgente disponibile.</p>;
  return <div className="mt-3 space-y-2">{items.map((source) => <SourceBlock key={source.source_id} source={source} />)}</div>;
}

function TerritorioSources({ items }: { items: InterrogazioneViewSource[] }) {
  const themes = [...new Set(items.map((source) => source.theme ?? "altro"))];
  return (
    <div className="mt-3 space-y-3">
      {themes.map((theme) => {
        const sources = items.filter((source) => (source.theme ?? "altro") === theme);
        const label = sources[0].themeLabel ?? theme;
        return (
          <section key={theme} aria-label={label}>
            <h4 className="text-xs font-bold uppercase tracking-[0.12em] text-emerald-800">{label}</h4>
            <Sources items={sources} />
          </section>
        );
      })}
      {!items.length ? <p className="text-sm text-slate-600">Nessuna sorgente disponibile.</p> : null}
    </div>
  );
}

export default function InterrogazionePanel(state: InterrogazioneState & { scheda: SchedaTerritorialeState }) {
  if (!state.open) {
    return <button type="button" className="absolute bottom-4 right-4 z-20 rounded-full bg-[#173f32] px-5 py-3 text-sm font-bold text-white shadow-xl" onClick={state.arm}>Interroga punto</button>;
  }
  return (
    <aside aria-label="Interrogazione territoriale" className="absolute bottom-3 right-3 top-3 z-30 flex w-[min(28rem,calc(100%-1.5rem))] flex-col rounded-2xl border border-emerald-950/15 bg-[#fffdf6]/95 shadow-2xl backdrop-blur">
      <header className="flex items-start justify-between border-b border-stone-200 p-4">
        <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-800">Istruttoria territoriale</p><h2 className="text-lg font-bold text-slate-900">Cosa insiste sul punto</h2></div>
        <button type="button" className="text-sm font-semibold text-slate-600" onClick={state.close}>Chiudi</button>
      </header>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {state.armed ? <p className="rounded-xl bg-amber-50 p-3 text-sm font-semibold text-amber-900">Clicca un punto sulla mappa per avviare l&apos;interrogazione.</p> : null}
        {state.point ? <p className="text-xs text-slate-500">Punto {state.point.lat.toFixed(6)}, {state.point.lon.toFixed(6)}</p> : null}
        <section aria-label="GAIA" className="rounded-xl border border-emerald-900/15 bg-[#eef4ea] p-3"><h3 className="font-bold text-emerald-950">GAIA</h3><Sources items={state.gaia} /></section>
        <details open className="rounded-xl border border-stone-200 bg-stone-50 p-3"><summary className="cursor-pointer font-bold text-slate-900">Catasto ufficiale</summary><Sources items={state.catastoUfficiale} /></details>
        <details open className="rounded-xl border border-stone-200 bg-stone-50 p-3"><summary className="cursor-pointer font-bold text-slate-900">Territorio</summary><TerritorioSources items={state.territorio} /></details>
        {state.scheda.error ? <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-800">{state.scheda.error}</p> : null}
        {state.scheda.downloadUrl ? (
          <a href={state.scheda.downloadUrl} download className="block w-full rounded-xl bg-emerald-800 px-4 py-3 text-center text-sm font-bold text-white">Scarica scheda territoriale PDF</a>
        ) : (
          <button type="button" disabled={!state.scheda.parcelId || ["queued", "processing"].includes(state.scheda.sheet?.status ?? "")} onClick={state.scheda.generate} className="w-full rounded-xl bg-emerald-800 px-4 py-3 text-sm font-bold text-white disabled:bg-stone-200 disabled:text-stone-500">
            {state.scheda.sheet?.status === "queued" ? "Scheda in coda..." : state.scheda.sheet?.status === "processing" ? "Generazione scheda..." : "Genera scheda territoriale"}
          </button>
        )}
      </div>
    </aside>
  );
}
