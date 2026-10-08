import { getPresenzeCompanyLabel } from "@/lib/presenze-display";
import type { PresenzeCollaborator } from "@/types/api";

export type DayFocusFilter = {
  iso: string;
  kind: "anomalies" | "requests";
} | null;

export type ProfileFilterKey =
  | "impiegati"
  | "operai_agrario"
  | "operai_catasto_magazzino"
  | "operai_da_classificare"
  | "non_impostato";

type OperationalTotals = {
  km: number;
  trasferta: number;
  straordinario: number;
  reperibilita: number;
};

type CollaboratorRowSelection = {
  collaborators: PresenzeCollaborator[];
  presentIds: Set<string>;
  collaboratorSchedule: Map<string, { code: string; label: string }>;
  anomalyCollaboratorIds: Set<string>;
  dayAnomalyCollaboratorIds: Map<string, Set<string>>;
  dayRequestCollaboratorIds: Map<string, Set<string>>;
  monthTotals: Map<string, OperationalTotals>;
  filters: {
    search: string;
    schedule: string;
    profile: ProfileFilterKey | "";
    anomalies: boolean;
    dayFocus: DayFocusFilter;
    km: boolean;
    trasferta: boolean;
    straordinario: boolean;
    reperibilita: boolean;
  };
};

export function collaboratorProfileFilterKey(collaborator: PresenzeCollaborator): ProfileFilterKey {
  if (collaborator.contract_kind === "impiegato") return "impiegati";
  if (collaborator.contract_kind === "operaio") {
    if (collaborator.operai_group === "agrario") return "operai_agrario";
    if (collaborator.operai_group === "catasto_magazzino") return "operai_catasto_magazzino";
    return "operai_da_classificare";
  }
  return "non_impostato";
}

export function selectMonthlyCollaboratorRows(selection: CollaboratorRowSelection): PresenzeCollaborator[] {
  const { collaborators, presentIds, collaboratorSchedule, anomalyCollaboratorIds,
    dayAnomalyCollaboratorIds, dayRequestCollaboratorIds, monthTotals, filters } = selection;
  const normalizedSearch = filters.search.trim().toLowerCase();
  const operationalKeys: Array<keyof OperationalTotals> = ["km", "trasferta", "straordinario", "reperibilita"];
  const activeOperationalKeys = operationalKeys.filter((key) => filters[key]);
  return collaborators
    .filter((collaborator) => presentIds.has(collaborator.id))
    .filter((collaborator) => !filters.schedule || collaboratorSchedule.get(collaborator.id)?.code === filters.schedule)
    .filter((collaborator) => !filters.profile || collaboratorProfileFilterKey(collaborator) === filters.profile)
    .filter((collaborator) => !filters.anomalies || anomalyCollaboratorIds.has(collaborator.id))
    .filter((collaborator) => {
      if (!filters.dayFocus) return true;
      const source = filters.dayFocus.kind === "anomalies"
        ? dayAnomalyCollaboratorIds.get(filters.dayFocus.iso)
        : dayRequestCollaboratorIds.get(filters.dayFocus.iso);
      return source?.has(collaborator.id) ?? false;
    })
    .filter((collaborator) => {
      const totals = monthTotals.get(collaborator.id)!;
      return activeOperationalKeys.every((key) => !(totals[key] <= 0));
    })
    .filter((collaborator) => {
      const company = getPresenzeCompanyLabel(collaborator.company_label, collaborator.company_code, "");
      return !normalizedSearch || [collaborator.name, collaborator.employee_code, company].some((value) =>
        value.toLowerCase().includes(normalizedSearch),
      );
    })
    .sort((first, second) => first.name.localeCompare(second.name));
}
