import type {
  RuoloTributiCalculationPolicyResponse,
  RuoloTributiCalculationPolicyUpsertRequest,
} from "@/types/ruolo";


export const EMPTY_CALCULATION_POLICY_FORM = {
  name: "",
  year_from: "",
  year_to: "",
  bonario_due_date: "",
  bonario_due_dates_by_year: {} as Record<string, string>,
  surcharge_rate_percent: "",
  euribor_6m_rate_percent: "",
  euribor_source_url: "",
  euribor_reference_period: "",
  euribor_fetched_at: "",
  interest_rate_percent: "",
  interest_from: "",
  interest_from_by_year: {} as Record<string, string>,
  interest_start_mode: "notification_date" as RuoloTributiCalculationPolicyResponse["interest_start_mode"],
  bollettino_causale: "",
  bollettino_esercizio: "",
  is_active: true,
  notes: "",
};

export type CalculationPolicyFormState = typeof EMPTY_CALCULATION_POLICY_FORM;

export function calculationPolicyFormFromPolicy(policy: RuoloTributiCalculationPolicyResponse): CalculationPolicyFormState {
  const years = calculationPolicyAnnualityYears(policy.year_from, policy.year_to);
  const bonarioDueDate = policyBonarioDueDate(policy);
  const interestFrom = policy.interest_from ?? "";
  return {
    name: policy.name,
    year_from: [policy.year_from].join(""),
    year_to: [policy.year_to].join(""),
    bonario_due_date: bonarioDueDate,
    bonario_due_dates_by_year: Object.fromEntries(years.map((year) => [String(year), bonarioDueDate])),
    surcharge_rate_percent: [policy.surcharge_rate_percent].join(""),
    euribor_6m_rate_percent: [policy.euribor_6m_rate_percent].join(""),
    euribor_source_url: policy.euribor_source_url ?? "",
    euribor_reference_period: policy.euribor_reference_period ?? "",
    euribor_fetched_at: policy.euribor_fetched_at ?? "",
    interest_rate_percent: [policy.interest_rate_percent].join(""),
    interest_from: [policy.interest_from].join(""),
    interest_from_by_year: Object.fromEntries(years.map((year) => [String(year), interestFrom])),
    interest_start_mode: policy.interest_start_mode,
    bollettino_causale: policy.bollettino_causale ?? "",
    bollettino_esercizio: policy.bollettino_esercizio ?? "",
    is_active: policy.is_active,
    notes: [policy.notes].join(""),
  };
}

export function calculationPolicyPayload(form: CalculationPolicyFormState): RuoloTributiCalculationPolicyUpsertRequest {
  return {
    name: form.name.trim(),
    year_from: parseOptionalYear(form.year_from),
    year_to: parseOptionalYear(form.year_to),
    bonario_due_date: optionalDate(form.bonario_due_date),
    surcharge_rate_percent: parseOptionalPercent(form.surcharge_rate_percent),
    surcharge_from: null,
    euribor_6m_rate_percent: parseOptionalPercent(form.euribor_6m_rate_percent),
    euribor_source_url: form.euribor_source_url || null,
    euribor_reference_period: form.euribor_reference_period || null,
    euribor_fetched_at: form.euribor_fetched_at || null,
    interest_rate_percent: parseOptionalPercent(form.interest_rate_percent),
    interest_from: optionalDate(form.interest_from),
    interest_start_mode: form.interest_start_mode,
    bollettino_causale: form.bollettino_causale || null,
    bollettino_esercizio: form.bollettino_esercizio || null,
    is_active: form.is_active,
    notes: form.notes.trim() || null,
  };
}

export function formatPolicyBollettino(policy: RuoloTributiCalculationPolicyResponse): string {
  const causale = policy.bollettino_causale ?? "automatica";
  const esercizio = policy.bollettino_esercizio ?? "automatico";
  return `Bollettino: causale ${causale} · esercizio ${esercizio}`;
}

export function parseOptionalYear(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isInteger(parsed) ? parsed : null;
}

export function optionalDate(value: string | undefined): string | null {
  return value || null;
}

export function calculationPolicyAnnualityYears(yearFrom: number | null | undefined, yearTo: number | null | undefined): number[] {
  if (yearFrom == null || yearTo == null || yearFrom > yearTo) return [];
  return Array.from({ length: yearTo - yearFrom + 1 }, (_value, index) => yearFrom + index);
}

export function policyNameForAnnuality(name: string, year: number): string {
  return `${name} ${year}`;
}

export function policyBonarioDueDate(policy: RuoloTributiCalculationPolicyResponse): string {
  return policy.bonario_due_date ?? previousIsoDate(policy.surcharge_from);
}

function parseOptionalPercent(value: string): number {
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function previousIsoDate(value: string | null | undefined): string {
  if (!value) return "";
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return "";
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCDate(date.getUTCDate() - 1);
  return date.toISOString().slice(0, 10);
}
