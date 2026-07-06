import type {
  PresenzeCollaborator,
  PresenzeCollaboratorScheduleAssignment,
  PresenzeDailyRecord,
  PresenzeScheduleTemplate,
} from "@/types/api";

const NON_ASSIGNABLE_INAZ_TEMPLATE_CODES = new Set([
  "OPE0613",
  "OP_5.3_12.3",
  "OSAB5.3_12.3",
]);

export type GaiaProfileCode = "GAIA_OPERAI" | "GAIA_IMPIEGATI" | "";

export function currentMonthBounds(): { start: string; end: string } {
  const now = new Date();
  const start = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
  const end = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()).padStart(2, "0")}`;
  return { start, end };
}

export function monthBoundsFromDate(isoDate: string): {
  start: string;
  end: string;
} {
  const [year, month] = isoDate.split("-").map(Number);
  const start = `${year}-${String(month).padStart(2, "0")}-01`;
  const end = `${year}-${String(month).padStart(2, "0")}-${String(new Date(year, month, 0).getDate()).padStart(2, "0")}`;
  return { start, end };
}

export function shiftMonthBounds(
  isoDate: string,
  delta: number,
): { start: string; end: string } {
  const [year, month] = isoDate.split("-").map(Number);
  const shifted = new Date(year, month - 1 + delta, 1);
  return monthBoundsFromDate(
    `${shifted.getFullYear()}-${String(shifted.getMonth() + 1).padStart(2, "0")}-01`,
  );
}

export function formatMonthRangeLabel(isoDate: string): string {
  return new Intl.DateTimeFormat("it-IT", {
    month: "long",
    year: "numeric",
  }).format(new Date(`${isoDate}T00:00:00`));
}

export function formatHours(minutes: number | null): string {
  if (minutes == null) return "—";
  return `${(minutes / 60).toFixed(2)} h`;
}

export function formatStandardDailyMinutes(
  minutes: number | null | undefined,
): string {
  if (minutes == null) return "—";
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return `${hours}:${String(remainder).padStart(2, "0")}`;
}

export function formatContractKind(
  value: PresenzeCollaborator["contract_kind"] | null | undefined,
): string {
  if (!value) return "—";
  const labels: Record<
    NonNullable<PresenzeCollaborator["contract_kind"]>,
    string
  > = {
    operaio: "Operaio",
    impiegato: "Impiegato",
    quadro: "Quadro",
    altro: "Altro",
  };
  return labels[value] ?? value;
}

export function formatOperaiGroup(
  value: PresenzeCollaborator["operai_group"] | null | undefined,
): string {
  if (value === "agrario") return "Agrario";
  if (value === "catasto_magazzino") return "Catasto / magazzino";
  return "Non impostato";
}

export function operaiGroupBadgeVariant(
  value: PresenzeCollaborator["operai_group"] | null | undefined,
): "success" | "info" | "neutral" {
  if (value === "agrario") return "success";
  if (value === "catasto_magazzino") return "info";
  return "neutral";
}

export function uniqueTemplateInazCodes(
  template: PresenzeCollaboratorScheduleAssignment["template"],
): string[] {
  if (!template) return [];
  return Array.from(
    new Set(
      (template.rules ?? [])
        .map((rule) => rule.ordinary_label?.trim())
        .filter((value): value is string => Boolean(value)),
    ),
  ).sort((left, right) => left.localeCompare(right));
}

export function templateDisplayTitle(
  template:
    | PresenzeCollaboratorScheduleAssignment["template"]
    | null
    | undefined,
): string {
  if (!template) return "Template non disponibile";
  return template.label?.trim() || template.code || `Template #${template.id}`;
}

export function isAssignableGaiaTemplate(
  template: PresenzeScheduleTemplate,
): boolean {
  return !NON_ASSIGNABLE_INAZ_TEMPLATE_CODES.has(
    template.code.trim().toUpperCase(),
  );
}

export function inferGaiaProfileCode(
  collaborator: PresenzeCollaborator | null | undefined,
): GaiaProfileCode {
  if (collaborator?.operai_group) return "GAIA_OPERAI";
  if (!collaborator?.contract_kind) return "";
  if (collaborator.contract_kind === "operaio") return "GAIA_OPERAI";
  if (
    collaborator.contract_kind === "impiegato" ||
    collaborator.contract_kind === "quadro" ||
    collaborator.contract_kind === "altro"
  )
    return "GAIA_IMPIEGATI";
  return "";
}

export function formatAbsenceCause(cause: string | null | undefined): string {
  if (!cause) return "—";
  const labels: Record<string, string> = {
    ferie: "Ferie",
    permesso: "Permesso",
    malattia: "Malattia",
    riposo: "Riposo",
    festivita: "Festivita",
    banca_ore: "Banca ore",
    assenza_da_giustificare: "Assenza da giustificare",
  };
  return labels[cause] ?? cause.replaceAll("_", " ");
}

export function formatRequestDescription(
  value: string | null | undefined,
): string {
  if (!value) return "—";
  if (value.includes(" - ")) {
    const [, right] = value.split(" - ", 2);
    if (right?.trim()) return right.trim();
  }
  return value;
}

export function recoveryBadgeLabel(record: PresenzeDailyRecord): string | null {
  if (record.grants_recovery_day)
    return `Recupero +${record.recovery_day_credit}`;
  if (record.uses_recovery_day) return `Recupero -${record.recovery_day_debit}`;
  if (record.holiday_kind === "ordinary") return "Festivita ordinaria";
  if (record.holiday_kind === "working_override") return "Override lavorativo";
  return null;
}

export function requestBadgeLabel(record: PresenzeDailyRecord): string | null {
  if (record.resolved_absence_cause) {
    return formatAbsenceCause(record.resolved_absence_cause);
  }
  if (record.request_description) {
    return formatRequestDescription(record.request_description);
  }
  return null;
}

export function formatDetailEntries(
  values: Record<string, string>,
): Array<[string, string]> {
  return Object.entries(values);
}

export function firstDetailPreview(
  items: Array<Record<string, string>>,
): string | null {
  for (const item of items) {
    for (const value of Object.values(item)) {
      if (typeof value === "string" && value.trim()) {
        return value.trim();
      }
    }
  }
  return null;
}

export function sectionSummaryLabel(
  title: string,
  options?: { count?: number; preview?: string | null; status?: string | null },
): string {
  const countLabel =
    typeof options?.count === "number" && options.count > 0
      ? `${options.count} ${options.count === 1 ? "voce" : "voci"}`
      : null;
  const parts = [options?.status, options?.preview, countLabel].filter(Boolean);
  return parts.length > 0 ? `${title} (${parts.join(" · ")})` : title;
}
