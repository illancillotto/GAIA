import type {
  RuoloTributiCalculationPolicyResponse,
  RuoloTributiCalculationPolicyUpsertRequest,
} from "@/types/ruolo";
import {
  annualityPolicyPayload,
  calculationPolicyAnnualityYears,
  calculationPolicyFormFromPolicy,
  calculationPolicyPayload,
  formatPolicyBollettino,
  optionalDate,
  type CalculationPolicyFormState,
} from "./calculation-policy-form";
import { PolicyBollettinoFields } from "./policy-bollettino-fields";
import { formatPolicyDate, PolicyDateInput } from "./policy-date-input";

// Notice print options of a rule: TD 896 slip and the "QUANTO E QUANDO PAGARE" payment date.

function bollettinoPrintOptions(policy: Pick<RuoloTributiCalculationPolicyResponse, "print_bollettino" | "bollettino_version">) {
  return {
    print_bollettino: policy.print_bollettino !== false,
    bollettino_version: policy.bollettino_version ?? "v1",
  };
}

export function policyFormWithNoticePrint(policy: RuoloTributiCalculationPolicyResponse): CalculationPolicyFormState {
  const paymentDueDate = policy.payment_due_date ?? "";
  const years = calculationPolicyAnnualityYears(policy.year_from, policy.year_to);
  return {
    ...calculationPolicyFormFromPolicy(policy),
    ...bollettinoPrintOptions(policy),
    payment_due_date: paymentDueDate,
    payment_due_dates_by_year: Object.fromEntries(years.map((year) => [String(year), paymentDueDate])),
  };
}

export function policyPayloadWithNoticePrint(form: CalculationPolicyFormState): RuoloTributiCalculationPolicyUpsertRequest {
  return {
    ...calculationPolicyPayload(form),
    ...bollettinoPrintOptions(form),
    payment_due_date: optionalDate(form.payment_due_date),
  };
}

export function annualityPayloadWithNoticePrint(form: CalculationPolicyFormState, year: number): RuoloTributiCalculationPolicyUpsertRequest {
  return {
    ...annualityPolicyPayload(form, year),
    ...bollettinoPrintOptions(form),
    payment_due_date: optionalDate(form.payment_due_dates_by_year[String(year)]),
  };
}

export function formatPolicyNoticePrint(policy: RuoloTributiCalculationPolicyResponse): string {
  const bollettino = policy.print_bollettino === false ? "Bollettino: non stampato" : formatPolicyBollettino(policy);
  return `${bollettino} · versione ${bollettinoPrintOptions(policy).bollettino_version.slice(1)} · pagamento avviso entro ${formatPolicyDate(policy.payment_due_date)}`;
}

export function PolicyNoticePrintFields({ form, onChange, years }: {
  form: CalculationPolicyFormState;
  onChange: (value: CalculationPolicyFormState) => void;
  years: number[];
}) {
  const annual = years.length > 1;
  return (
    <div className="grid gap-2 rounded-xl border border-amber-100 bg-amber-50/60 p-3">
      <label className="flex items-center gap-2 text-sm text-gray-700">
        <input type="checkbox" aria-label="Stampa bollettino postale" checked={form.print_bollettino} onChange={(event) => onChange({ ...form, print_bollettino: event.target.checked })} />
        Stampa bollettino postale
      </label>
      <p className="text-xs text-gray-600">Senza bollettino l&apos;avviso indica solo bonifico e pagoPA. Con piu annualita il bollettino si stampa solo se tutte le regole lo prevedono.</p>
      <PolicyBollettinoFields form={form} onChange={onChange} />
      {annual ? years.map((year) => (
        <PolicyDateInput key={year} label={`Pagamento avviso entro ${year}`} value={form.payment_due_dates_by_year[String(year)] ?? ""} onChange={(value) => onChange({ ...form, payment_due_dates_by_year: { ...form.payment_due_dates_by_year, [year]: value } })} />
      )) : (
        <PolicyDateInput label="Pagamento avviso entro" value={form.payment_due_date} onChange={(value) => onChange({ ...form, payment_due_date: value })} />
      )}
      <p className="text-xs text-gray-600">Data di &quot;Quanto e quando pagare&quot; e scadenza del bollettino; vuota: 30 giorni dalla generazione.</p>
    </div>
  );
}
