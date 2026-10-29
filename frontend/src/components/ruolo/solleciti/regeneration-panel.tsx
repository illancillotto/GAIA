"use client";

import { useRef, useState } from "react";

import { errorMessage } from "@/components/ruolo/poste-dispatch/labels";
import {
  listRegenerationTargets,
  regenerateReminderItem,
  type RegenerationMode,
  type RegenerationTarget,
} from "@/lib/ruolo-regeneration-api";

type Scope = "all" | "batch";
type Problem = { id: string; name: string; outcome: "skipped" | "failed"; detail: string };
type Progress = { total: number; done: number; regenerated: number; excluded: number; problems: Problem[] };

const MODES: { key: RegenerationMode; label: string; hint: string }[] = [
  { key: "template", label: "Solo template", hint: "Stessi dati salvati alla generazione, layout attuale." },
  { key: "recompute", label: "Ricalcola dati e regole", hint: "Importi e regole di oggi, stesso numero avviso. Le posizioni saldate o cambiate vengono saltate." },
];

async function regenerateOne(token: string, target: RegenerationTarget, mode: RegenerationMode): Promise<Problem | null> {
  const name = target.display_name || target.codice_fiscale;
  try {
    const result = await regenerateReminderItem(token, target.item_id, mode);
    if (result.outcome === "regenerated") return null;
    return { id: target.item_id, name, outcome: result.outcome, detail: result.detail ?? "" };
  } catch (err) {
    return { id: target.item_id, name, outcome: "failed", detail: errorMessage(err, "Rigenerazione non riuscita") };
  }
}

function advance(state: Progress, problem: Problem | null): Progress {
  if (!problem) return { ...state, done: state.done + 1, regenerated: state.regenerated + 1 };
  return { ...state, done: state.done + 1, problems: [...state.problems, problem] };
}

// One sollecito per request, in order: the page shows progress and can stop between two PDFs.
export function useRegeneration(token: string, onFinished: () => void) {
  const stopped = useRef(false);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function start(batchId: string | null, mode: RegenerationMode) {
    stopped.current = false;
    setRunning(true);
    setError(null);
    try {
      const targets = await listRegenerationTargets(token, batchId);
      let state: Progress = { total: targets.items.length, done: 0, regenerated: 0, excluded: targets.excluded_drafts, problems: [] };
      setProgress(state);
      for (const target of targets.items) {
        if (stopped.current) break;
        state = advance(state, await regenerateOne(token, target, mode));
        setProgress(state);
      }
      onFinished();
    } catch (err) {
      setError(errorMessage(err, "Elenco dei solleciti non caricato"));
    } finally {
      setRunning(false);
    }
  }

  return { running, progress, error, start, stop: () => { stopped.current = true; } };
}

function reportTitle(progress: Progress, running: boolean): string {
  if (running) return "In corso";
  return progress.done < progress.total ? "Fermata" : "Completata";
}

function RegenerationReport({ progress, running }: { progress: Progress; running: boolean }) {
  const skipped = progress.problems.filter((problem) => problem.outcome === "skipped").length;
  return <div role="status" className="mt-3 space-y-2">
    <p className="font-semibold">{reportTitle(progress, running)}: {progress.done} di {progress.total} · rigenerati {progress.regenerated} · saltati {skipped} · errori {progress.problems.length - skipped}</p>
    {progress.excluded > 0 && <p>Bozze 2022/2023 escluse: {progress.excluded}.</p>}
    {progress.problems.length > 0 && <ul className="max-h-60 space-y-1 overflow-y-auto">
      {progress.problems.map((problem) => <li key={problem.id}><span className="font-semibold">{problem.name}</span> - {problem.outcome === "failed" ? "errore" : "saltato"}: {problem.detail}</li>)}
    </ul>}
  </div>;
}

type Props = { token: string; batchId: string | null; onFinished: () => void };

export function RegenerationPanel({ token, batchId, onFinished }: Props) {
  const [open, setOpen] = useState(false);
  const regeneration = useRegeneration(token, onFinished);
  return <section aria-label="Rigenera PDF" className="rounded-2xl border border-[#d8dfd3] bg-white px-5 py-3 text-sm text-slate-700">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="font-semibold text-slate-900">Rigenera PDF</h2>
        <p className="text-xs text-slate-500">Dopo modifiche al template o alle regole del ruolo.</p>
      </div>
      <button type="button" className="btn-secondary" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? "Nascondi opzioni" : "Mostra opzioni"}</button>
    </div>
    {open && <RegenerationOptions batchId={batchId} regeneration={regeneration} />}
    {regeneration.error && <p role="alert" className="mt-2 text-rose-800">{regeneration.error}</p>}
    {regeneration.progress && <RegenerationReport progress={regeneration.progress} running={regeneration.running} />}
  </section>;
}

function RegenerationOptions({ batchId, regeneration }: { batchId: string | null; regeneration: ReturnType<typeof useRegeneration> }) {
  const [scope, setScope] = useState<Scope>("all");
  const [mode, setMode] = useState<RegenerationMode>("template");
  const missingBatch = scope === "batch" && !batchId;
  return <div className="mt-3 border-t border-slate-100 pt-3">
    <p className="rounded-xl bg-amber-50 px-3 py-2 text-amber-950">Rigenera anche i solleciti già caricati su Poste o spediti e sovrascrive le copie sul NAS; le bozze 2022/2023 restano escluse. Lasciare la pagina aperta fino alla fine.</p>
    <div className="mt-3 grid gap-4 md:grid-cols-[auto_1fr]">
      <fieldset className="space-y-1" disabled={regeneration.running}>
        <legend className="font-medium text-slate-900">Quali solleciti</legend>
        <label className="flex items-center gap-2"><input type="radio" name="regeneration-scope" checked={scope === "all"} onChange={() => setScope("all")} />Tutti i lotti</label>
        <label className="flex items-center gap-2"><input type="radio" name="regeneration-scope" checked={scope === "batch"} onChange={() => setScope("batch")} />Solo il lotto selezionato</label>
      </fieldset>
      <fieldset className="space-y-1" disabled={regeneration.running}>
        <legend className="font-medium text-slate-900">Con quali dati</legend>
        {MODES.map((entry) => <label key={entry.key} className="flex items-start gap-2"><input type="radio" className="mt-1" name="regeneration-mode" checked={mode === entry.key} onChange={() => setMode(entry.key)} /><span><span className="font-semibold">{entry.label}</span> - {entry.hint}</span></label>)}
      </fieldset>
    </div>
    <div className="mt-3 flex flex-wrap items-center gap-3">
      {regeneration.running
        ? <button type="button" className="btn-secondary" onClick={regeneration.stop}>Ferma</button>
        : <button type="button" className="btn-primary" disabled={missingBatch} onClick={() => void regeneration.start(scope === "batch" ? batchId : null, mode)}>Rigenera PDF</button>}
      {missingBatch && <p>Seleziona prima un lotto.</p>}
    </div>
  </div>;
}
