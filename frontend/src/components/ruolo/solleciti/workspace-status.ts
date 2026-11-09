import type { WorkspaceStage } from "@/lib/ruolo-solleciti-workspace-api";

export const STAGES: Record<WorkspaceStage, string> = {
  available: "Da preparare", processing: "In lavorazione", draft: "Caricato su Poste",
  sent: "Spedito", review: "Da verificare", conflict: "Conflitto",
};

export const STAGE_TONES: Record<WorkspaceStage, string> = {
  available: "border-slate-200 bg-slate-50 text-slate-700",
  processing: "border-blue-200 bg-blue-50 text-blue-900",
  draft: "border-sky-200 bg-sky-50 text-sky-900",
  sent: "border-emerald-200 bg-emerald-50 text-emerald-900",
  review: "border-amber-200 bg-amber-50 text-amber-900",
  conflict: "border-rose-200 bg-rose-50 text-rose-900",
};
