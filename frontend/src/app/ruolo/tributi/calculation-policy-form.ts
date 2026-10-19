import type {
  RuoloTributiCalculationPolicyResponse,
  RuoloTributiCalculationPolicyUpsertRequest,
} from "@/types/ruolo";

export type PolicyChargeMode = "both" | "surcharge" | "interest" | "none";
export type AnnualityRuleOptions = {
  charge_mode: PolicyChargeMode;
  only_unnotified: boolean;
  surcharge_rate_percent: string;
  euribor_6m_rate_percent: string;
  interest_rate_percent: string;
  interest_start_mode: RuoloTributiCalculationPolicyResponse["interest_start_mode"];
};

export const EMPTY_CALCULATION_POLICY_FORM = {
  name: "",
  charge_mode: "both" as PolicyChargeMode,
  only_unnotified: false,
  rules_by_year: {} as Record<string, Partial<AnnualityRuleOptions>>,
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
  return {
    name: policy.name,
    ...policyOptionsFromPolicy(policy),
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
    interest_from_by_year: Object.fromEntries(years.map((year) => [String(year), [policy.interest_from].join("")])),
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
    ...policyChargesPayload(form),
    surcharge_from: null,
    euribor_source_url: form.euribor_source_url || null,
    euribor_reference_period: form.euribor_reference_period || null,
    euribor_fetched_at: form.euribor_fetched_at || null,
    interest_from: optionalDate(form.interest_from),
    interest_start_mode: form.interest_start_mode,
    bollettino_causale: form.bollettino_causale || null,
    bollettino_esercizio: form.bollettino_esercizio || null,
    is_active: form.is_active,
    notes: form.notes.trim() || null,
  };
}

function policyOptionsFromPolicy(policy: RuoloTributiCalculationPolicyResponse) {
  return {
    charge_mode: policyChargeMode(policy),
    only_unnotified: Boolean(policy.only_unnotified),
    rules_by_year: {},
  };
}

function policyChargesPayload(form: CalculationPolicyFormState) {
  return {
    only_unnotified: form.only_unnotified,
    surcharge_rate_percent: chargeRate(form.surcharge_rate_percent, form.charge_mode, "surcharge"),
    euribor_6m_rate_percent: chargeRate(form.euribor_6m_rate_percent, form.charge_mode, "interest"),
    interest_rate_percent: chargeRate(form.interest_rate_percent, form.charge_mode, "interest"),
  };
}

function chargeRate(value: string, mode: PolicyChargeMode, component: PolicyChargeMode): number {
  return mode === "both" || mode === component ? parseOptionalPercent(value) : 0;
}

export function policyChargeMode(policy: RuoloTributiCalculationPolicyResponse): PolicyChargeMode {
  const surcharge = policy.surcharge_rate_percent > 0;
  const interest = (policy.euribor_6m_rate_percent ?? 0) + (policy.interest_rate_percent ?? 0) > 0;
  if (surcharge && interest) return "both";
  if (surcharge) return "surcharge";
  return interest ? "interest" : "none";
}

export function annualityPolicyPayload(form: CalculationPolicyFormState, year: number): RuoloTributiCalculationPolicyUpsertRequest {
  return calculationPolicyPayload({
    ...form,
    ...form.rules_by_year[String(year)],
    ...annualityEuriborSource(form, year),
    name: policyNameForAnnuality(form.name.trim(), year),
    year_from: String(year),
    year_to: String(year),
    bonario_due_date: form.bonario_due_dates_by_year[String(year)] ?? "",
    interest_from: form.interest_from_by_year[String(year)] ?? "",
  });
}

function annualityEuriborSource(form: CalculationPolicyFormState, year: number) {
  if (form.rules_by_year[String(year)]?.euribor_6m_rate_percent === undefined) return {};
  return { euribor_source_url: "", euribor_reference_period: "", euribor_fetched_at: "" };
}

export function policyBlockName(policy: RuoloTributiCalculationPolicyResponse): string {
  const name = policy.name.trim();
  const suffix = String(policy.year_from);
  if (policy.year_from != null && policy.year_from === policy.year_to && name.endsWith(suffix)) {
    return name.slice(0, -suffix.length).trim();
  }
  return name;
}

export function groupCalculationPolicies(policies: RuoloTributiCalculationPolicyResponse[]) {
  const blocks = new Map<string, RuoloTributiCalculationPolicyResponse[]>();
  for (const policy of policies) {
    const name = policyBlockName(policy);
    const rules = blocks.get(name) ?? [];
    rules.push(policy);
    blocks.set(name, rules);
  }
  return Array.from(blocks, ([name, rules]) => ({ name, rules }));
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
