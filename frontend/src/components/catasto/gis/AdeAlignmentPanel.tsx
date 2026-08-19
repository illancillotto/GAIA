import Link from "next/link";

import type { AdeAlignmentReportResponse, AdeWfsRunStatusResponse } from "@/types/gis";

const ADE_RUN_STATUS_LABELS: Record<string, string> = {
  queued: "In coda",
  running: "In corso",
  processing: "In esecuzione",
  completed: "Completato",
  failed: "Fallito",
};

const ADE_RUN_PHASE_LABELS: Record<string, string> = {
  queued: "In coda",
  fetching: "Download tile",
  fetch_tiles: "Download tile",
  fetching_features: "Scarico feature",
  parse_features: "Parsing feature",
  reconcile: "Riconciliazione",
  persisting: "Persistenza",
  persist: "Persistenza",
  completed: "Completato",
  failed: "Fallito",
};

type AdeAlignmentPanelProps = {
  isDark: boolean;
  adeRunStatus: AdeWfsRunStatusResponse | null;
  adeReport: AdeAlignmentReportResponse | null;
};

type AdeThemeProps = {
  isDark: boolean;
};

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  try {
    return new Intl.DateTimeFormat("it-IT", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function formatMeters(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "-";
  return `${value.toLocaleString("it-IT", { maximumFractionDigits: 1 })} m`;
}

function runStatusBadgeClass(status: string) {
  if (status === "completed") return "bg-emerald-50 text-emerald-700";
  if (status === "failed") return "bg-rose-50 text-rose-700";
  return "bg-amber-50 text-amber-700";
}

function AdeAlignmentHeader({ isDark }: AdeThemeProps) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className={`text-[10px] font-semibold uppercase tracking-widest ${isDark ? "text-amber-200" : "text-amber-700"}`}>
          Stato allineamento AdE
        </p>
        <p className={`mt-1 text-xs leading-5 ${isDark ? "text-white/60" : "text-slate-600"}`}>
          Il workflow operativo di run, monitor e apply è stato spostato in `Elaborazioni`. Nel GIS restano l&apos;ultimo stato disponibile, il report differenze e la preview cartografica.
        </p>
      </div>
      <Link
        href="/elaborazioni/ade-alignment"
        className={`inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold transition ${
          isDark ? "bg-white text-slate-900 hover:bg-amber-50" : "bg-slate-950 text-white hover:bg-slate-800"
        }`}
      >
        <span className="material-symbols-outlined text-[16px]">open_in_new</span>
        Apri workspace
      </Link>
    </div>
  );
}

function AdeRunStatusCard({ isDark, adeRunStatus }: AdeThemeProps & { adeRunStatus: AdeWfsRunStatusResponse | null }) {
  return (
    <div className={`mt-3 rounded-xl border px-3 py-2 text-xs ${isDark ? "border-white/15 bg-white/5 text-white/70" : "border-amber-100 bg-white/70 text-slate-600"}`}>
      {adeRunStatus ? (
        <>
          <div className="flex items-center justify-between gap-2">
            <div className="font-semibold text-slate-900">Run {adeRunStatus.run_id.slice(0, 8)}</div>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${runStatusBadgeClass(adeRunStatus.status)}`}>
              {ADE_RUN_STATUS_LABELS[adeRunStatus.status] ?? adeRunStatus.status}
            </span>
          </div>
          <div className="mt-1">
            {adeRunStatus.tiles_completed.toLocaleString("it-IT")} / {adeRunStatus.tiles.toLocaleString("it-IT")} tile · {adeRunStatus.features.toLocaleString("it-IT")} feature · {adeRunStatus.with_geometry.toLocaleString("it-IT")} con geometria
          </div>
          <div className="mt-1 text-[11px]">
            {ADE_RUN_PHASE_LABELS[adeRunStatus.progress_phase] ?? adeRunStatus.progress_phase} · {adeRunStatus.progress_percent.toLocaleString("it-IT", { maximumFractionDigits: 1 })}% · Avvio {formatDateTime(adeRunStatus.started_at)} · fine {formatDateTime(adeRunStatus.completed_at)}
          </div>
          {adeRunStatus.progress_message ? <div className="mt-2 text-[11px]">{adeRunStatus.progress_message}</div> : null}
          {adeRunStatus.error ? <div className="mt-2 text-rose-700">{adeRunStatus.error}</div> : null}
        </>
      ) : (
        <div>Nessun run AdE disponibile. Avvia il comprensorio dal workspace elaborazioni.</div>
      )}
    </div>
  );
}

function AdeReportCounters({ report }: { report: AdeAlignmentReportResponse }) {
  return (
    <div className="grid grid-cols-2 gap-2 text-center text-[11px]">
      <div className="rounded-xl bg-emerald-50 px-2 py-2">
        <div className="font-semibold text-emerald-700">{report.counters.allineate.toLocaleString("it-IT")}</div>
        <div className="text-emerald-900/50">allineate</div>
      </div>
      <div className="rounded-xl bg-amber-50 px-2 py-2">
        <div className="font-semibold text-amber-700">{report.counters.nuove_in_ade.toLocaleString("it-IT")}</div>
        <div className="text-amber-900/50">nuove AdE</div>
      </div>
      <div className="rounded-xl bg-rose-50 px-2 py-2">
        <div className="font-semibold text-rose-700">{report.counters.geometrie_variate.toLocaleString("it-IT")}</div>
        <div className="text-rose-900/50">geometrie variate</div>
      </div>
      <div className="rounded-xl bg-slate-100 px-2 py-2">
        <div className="font-semibold text-slate-700">{report.counters.mancanti_in_ade.toLocaleString("it-IT")}</div>
        <div className="text-slate-500">mancanti AdE</div>
      </div>
    </div>
  );
}

function AdeReportSamples({ report }: { report: AdeAlignmentReportResponse }) {
  if (report.samples.length === 0) return null;

  return (
    <div className="max-h-40 space-y-1.5 overflow-y-auto pr-1">
      {report.samples.slice(0, 8).map((item, index) => (
        <div key={`${item.category}-${item.national_cadastral_reference ?? index}`} className="rounded-xl border border-amber-100 bg-white px-3 py-2 text-xs">
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-slate-800">{item.national_cadastral_reference ?? `${item.foglio}/${item.particella}`}</span>
            <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">{item.category}</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-500">
            {item.codice_catastale ?? "-"} · Fg. {item.foglio ?? "-"} · Part. {item.particella ?? "-"}
            {item.distance_m != null ? ` · ${formatMeters(item.distance_m)}` : ""}
          </div>
        </div>
      ))}
    </div>
  );
}

function AdeReportSummary({ report }: { report: AdeAlignmentReportResponse | null }) {
  if (!report) return null;

  return (
    <div className="mt-3 space-y-3">
      <AdeReportCounters report={report} />
      <div className="rounded-xl border border-white bg-white/80 px-3 py-2 text-[11px] text-slate-500">
        Completato: {formatDateTime(report.completed_at)} · soglia geometria {report.geometry_threshold_m} m
      </div>
      {report.geojson && report.geojson.features.length > 0 ? (
        <div className="rounded-xl border border-amber-100 bg-white px-3 py-2 text-[11px] text-slate-600">
          Preview in mappa: giallo nuove AdE, rosso geometrie AdE variate, blu geometrie GAIA correnti, grigio mancanti AdE.
        </div>
      ) : null}
      <AdeReportSamples report={report} />
    </div>
  );
}

export default function AdeAlignmentPanel({ isDark, adeRunStatus, adeReport }: AdeAlignmentPanelProps) {
  return (
    <div className={`rounded-2xl border p-3 ${isDark ? "border-white/15 bg-white/10" : "border-amber-100 bg-amber-50/40"}`}>
      <AdeAlignmentHeader isDark={isDark} />
      <AdeRunStatusCard isDark={isDark} adeRunStatus={adeRunStatus} />
      <AdeReportSummary report={adeReport} />
    </div>
  );
}
