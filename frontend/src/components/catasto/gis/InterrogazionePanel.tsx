"use client";

import type { InterrogazioneState, InterrogazioneViewSource } from "@/components/catasto/gis/use-interrogazione";
import SchedaTerritorialeActions from "@/components/catasto/gis/SchedaTerritorialeActions";
import type { CurrentUser } from "@/types/api";

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

type InterrogazionePanelProps = InterrogazioneState & {
  scheda: {
    token: string | null;
    particellaId: string | null;
    currentUser: Pick<CurrentUser, "enabled_modules" | "role"> | null;
  };
};

export default function InterrogazionePanel(state: InterrogazionePanelProps) {
  if (!state.point) return null;
  const loading = [...state.gaia, ...state.catastoUfficiale, ...state.territorio]
    .some((source) => source.status === "loading");
  return (
    <details aria-label="Dati territoriali sul punto" className="mt-3 rounded-2xl border border-emerald-900/15 bg-[#f4f8f1]/90 p-3">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-xs font-bold text-emerald-950">
        <span className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="material-symbols-outlined text-[18px]">location_searching</span>
          Dati territoriali sul punto
        </span>
        <span className="rounded-full bg-white/80 px-2 py-1 text-[10px] uppercase tracking-wide text-emerald-700">
          {loading ? "Caricamento" : "Disponibili"}
        </span>
      </summary>
      <div className="mt-3 space-y-3 border-t border-emerald-900/10 pt-3">
        <p className="text-xs text-slate-500">Punto {state.point.lat.toFixed(6)}, {state.point.lon.toFixed(6)}</p>
        <section aria-label="GAIA" className="rounded-xl border border-emerald-900/15 bg-[#eef4ea] p-3"><h3 className="font-bold text-emerald-950">GAIA</h3><Sources items={state.gaia} /></section>
        <details className="rounded-xl border border-stone-200 bg-stone-50 p-3"><summary className="cursor-pointer font-bold text-slate-900">Catasto ufficiale</summary><Sources items={state.catastoUfficiale} /></details>
        <details className="rounded-xl border border-stone-200 bg-stone-50 p-3"><summary className="cursor-pointer font-bold text-slate-900">Territorio</summary><TerritorioSources items={state.territorio} /></details>
        <SchedaTerritorialeActions {...state.scheda} />
      </div>
    </details>
  );
}
