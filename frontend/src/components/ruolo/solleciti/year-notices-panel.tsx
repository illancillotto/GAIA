"use client";

import { useEffect, useRef, useState } from "react";

import { errorMessage } from "@/components/ruolo/poste-dispatch/labels";
import { regenerateReminderItem } from "@/lib/ruolo-regeneration-api";
import { generateYearNotices, getYearStatus, type YearStatus } from "@/lib/ruolo-year-notices-api";

const FIRST_YEAR = 2021;
// Few notices per request: each PDF takes a few seconds and the page shows progress in between.
const NOTICES_PER_STEP = 5;

type Problem = { label: string; detail: string };
type Run = { total: number; done: number; problems: Problem[]; running: boolean };
type Step = { size: number; work: () => Promise<Problem[]> };

function years(): number[] {
  const last = new Date().getFullYear();
  return Array.from({ length: last - FIRST_YEAR + 1 }, (_, index) => FIRST_YEAR + index);
}

async function safely(label: string, work: () => Promise<Problem[]>): Promise<Problem[]> {
  try {
    return await work();
  } catch (err) {
    return [{ label, detail: errorMessage(err, "Richiesta non riuscita") }];
  }
}

// Failed PDFs are retried one by one; missing ones are made a few at a time.
function steps(token: string, status: YearStatus): Step[] {
  const retries = status.failed.map((notice): Step => ({
    size: 1,
    work: () => safely(notice.label, async () => {
      const result = await regenerateReminderItem(token, notice.item_id, "template");
      return result.outcome === "regenerated" ? [] : [{ label: notice.label, detail: result.detail ?? "PDF non creato" }];
    }),
  }));
  const groups: Step[] = [];
  for (let start = 0; start < status.missing.length; start += NOTICES_PER_STEP) {
    const group = status.missing.slice(start, start + NOTICES_PER_STEP);
    groups.push({
      size: group.length,
      work: () => safely(group.map((notice) => notice.label).join(", "), async () =>
        (await generateYearNotices(token, status.year, group.flatMap((notice) => notice.avviso_ids))).problems),
    });
  }
  return [...retries, ...groups];
}

export function useYearNotices(token: string, onFinished: () => void) {
  const stopped = useRef(false);
  const [year, setYear] = useState(FIRST_YEAR);
  const [status, setStatus] = useState<YearStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setStatus(null);
    setError(null);
    getYearStatus(token, year)
      .then((value) => { if (!cancelled) setStatus(value); })
      .catch((err) => { if (!cancelled) setError(errorMessage(err, "Conteggio degli avvisi non riuscito")); });
    return () => { cancelled = true; };
  }, [token, year, version]);

  async function start(status: YearStatus) {
    stopped.current = false;
    const work = steps(token, status);
    let state: Run = { total: status.failed.length + status.missing.length, done: 0, problems: [], running: true };
    setRun(state);
    for (const step of work) {
      if (stopped.current) break;
      const problems = await step.work();
      state = { ...state, done: state.done + step.size, problems: [...state.problems, ...problems] };
      setRun(state);
    }
    setRun({ ...state, running: false });
    setVersion((value) => value + 1);
    onFinished();
  }

  function choose(value: number) {
    setRun(null);
    setYear(value);
  }

  return { year, choose, status, error, run, start, stop: () => { stopped.current = true; } };
}

type Notices = ReturnType<typeof useYearNotices>;

export function YearNoticesPanel({ token, onFinished }: { token: string; onFinished: () => void }) {
  const notices = useYearNotices(token, onFinished);
  const running = notices.run?.running ?? false;
  return <section aria-label="Avvisi da sollecitare" className="rounded-2xl border-2 border-[#9ab69c] bg-[#f6faf5] p-5 text-slate-800">
    <div className="flex flex-wrap items-center gap-3">
      <h2 className="text-lg font-semibold text-slate-900">Avvisi da sollecitare</h2>
      <label className="flex items-center gap-2 text-base">Anno
        <select className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-base" value={notices.year} disabled={running} onChange={(event) => notices.choose(Number(event.target.value))}>
          {years().map((value) => <option key={value} value={value}>{value}</option>)}
        </select>
      </label>
    </div>
    {notices.error && <p role="alert" className="mt-3 text-rose-800">{notices.error}</p>}
    {!notices.status && !notices.error && <p className="mt-3">Conteggio degli avvisi del {notices.year}...</p>}
    {notices.status && <YearSummary notices={notices} status={notices.status} running={running} />}
  </section>;
}

function YearSummary({ notices, status, running }: { notices: Notices; status: YearStatus; running: boolean }) {
  const todo = status.failed.length + status.missing.length;
  return <div className="mt-3 space-y-3 text-base">
    <ul className="grid gap-2 sm:grid-cols-3">
      <li className="rounded-xl bg-white px-4 py-3"><span className="block text-2xl font-semibold text-emerald-800">{status.ready}</span>PDF pronti</li>
      <li className="rounded-xl bg-white px-4 py-3"><span className="block text-2xl font-semibold text-rose-800">{status.failed.length}</span>PDF non riusciti, da riprovare</li>
      <li className="rounded-xl bg-white px-4 py-3"><span className="block text-2xl font-semibold text-slate-900">{status.missing.length}</span>PDF ancora da creare</li>
    </ul>
    <p className="text-sm text-slate-600">{status.total} avvisi del {status.year} da sollecitare con le regole GAIA. I PDF già pronti non vengono rifatti.</p>
    {todo === 0 && !notices.run && <p className="font-semibold text-emerald-800">Tutti i PDF del {status.year} sono pronti.</p>}
    {todo > 0 && !running && <button type="button" className="btn-primary px-6 py-3 text-base" onClick={() => void notices.start(status)}>{todo === 1 ? "Crea il PDF mancante" : `Crea i ${todo} PDF mancanti`}</button>}
    {notices.run && <YearRun run={notices.run} stop={notices.stop} />}
  </div>;
}

function YearRun({ run, stop }: { run: Run; stop: () => void }) {
  const percent = Math.round((run.done / run.total) * 100);
  return <div role="status" className="space-y-2">
    <div className="h-3 overflow-hidden rounded-full bg-white" aria-hidden="true"><div className="h-full bg-[#1d4e35]" style={{ width: `${percent}%` }} /></div>
    <div className="flex flex-wrap items-center gap-3">
      <p className="font-semibold">{run.running ? `Sto creando i PDF: ${run.done} di ${run.total}. Lascia la pagina aperta.` : run.done < run.total ? `Fermato: ${run.done} di ${run.total}.` : `Finito: ${run.done} di ${run.total}.`}</p>
      {run.running && <button type="button" className="btn-secondary" onClick={stop}>Ferma</button>}
    </div>
    {run.problems.length > 0 && <div className="rounded-xl bg-rose-50 px-4 py-3 text-rose-900">
      <p className="font-semibold">Questi avvisi non hanno il PDF ({run.problems.length}):</p>
      <ul className="mt-1 max-h-60 space-y-1 overflow-y-auto">{run.problems.map((problem, index) => <li key={index}><span className="font-semibold">{problem.label}</span>: {problem.detail}</li>)}</ul>
    </div>}
  </div>;
}
