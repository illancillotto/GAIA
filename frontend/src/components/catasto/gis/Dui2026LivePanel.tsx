import type { Dui2026LayerResponse } from "@/types/gis";

type Dui2026LivePanelProps = {
  data: Dui2026LayerResponse | null;
  loading: boolean;
  error: string | null;
  visible: boolean;
  onToggleVisible: () => void;
};

export function Dui2026LivePanel({ data, loading, error, visible, onToggleVisible }: Dui2026LivePanelProps) {
  return (
    <section className="rounded-2xl border border-cyan-100 bg-cyan-50/40 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-cyan-700">Layer live NAS</p>
          <h3 className="mt-1 text-sm font-semibold text-slate-900">DUI 2026</h3>
          <p className="mt-1 text-[11px] leading-4 text-slate-500">
            Ultimo backup letto dal NAS e marcato rispetto alle domande presenti nel ruolo 2025.
          </p>
        </div>
        <button
          type="button"
          onClick={onToggleVisible}
          disabled={!data || loading}
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition ${
            visible
              ? "border-cyan-200 bg-cyan-100 text-cyan-800"
              : "border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:text-gray-800"
          } ${!data || loading ? "cursor-not-allowed opacity-60" : ""}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${visible ? "bg-cyan-500" : "bg-gray-300"}`} />
          {visible ? "Visibile" : "Nascosto"}
        </button>
      </div>

      {loading ? (
        <p className="mt-3 text-xs text-slate-500">Caricamento layer DUI 2026 dal NAS…</p>
      ) : null}

      {!loading && error ? (
        <p className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">{error}</p>
      ) : null}

      {!loading && !error && data ? (
        <>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center text-[11px]">
            <div className="rounded-xl bg-white/90 px-2 py-2">
              <div className="font-semibold text-slate-800">{data.stats.total_polygons.toLocaleString("it-IT")}</div>
              <div className="text-slate-500">poligoni</div>
            </div>
            <div className="rounded-xl bg-emerald-50 px-2 py-2">
              <div className="font-semibold text-emerald-700">{data.stats.in_ruolo_2025.toLocaleString("it-IT")}</div>
              <div className="text-emerald-700/70">in ruolo 2025</div>
            </div>
            <div className="rounded-xl bg-amber-50 px-2 py-2">
              <div className="font-semibold text-amber-700">{data.stats.not_in_ruolo_2025.toLocaleString("it-IT")}</div>
              <div className="text-amber-700/70">fuori ruolo</div>
            </div>
          </div>
          <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-600">
            <span className="rounded-full bg-white/80 px-2.5 py-1">Contatore: {data.stats.with_contatore.toLocaleString("it-IT")}</span>
            <span className="rounded-full bg-white/80 px-2.5 py-1">Senza contatore: {data.stats.without_contatore.toLocaleString("it-IT")}</span>
            <span className="rounded-full bg-white/80 px-2.5 py-1">Telerilev.: {data.stats.with_telerilev.toLocaleString("it-IT")}</span>
          </div>
          <p className="mt-2 text-[11px] text-slate-500">
            Snapshot <span className="font-medium text-slate-700">{data.source_date}</span> · file{" "}
            <span className="font-medium text-slate-700">{data.source_filename}</span>
          </p>
          <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-500">
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-[#0F766E]" />
              in ruolo 2025
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-[#D97706]" />
              non presente a ruolo 2025
            </span>
          </div>
        </>
      ) : null}
    </section>
  );
}
