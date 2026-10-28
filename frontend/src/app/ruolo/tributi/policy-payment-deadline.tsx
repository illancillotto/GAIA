import type { RuoloTributiCalculationPolicyResponse } from "@/types/ruolo";
import {
  calculationPolicyAnnualityYears,
  optionalDate,
  type CalculationPolicyFormState,
} from "./calculation-policy-form";
import { formatPolicyDate, PolicyDateInput } from "./policy-date-input";

export function paymentDeadlineForm(policy: RuoloTributiCalculationPolicyResponse) {
  const date = policy.payment_due_date ?? "";
  const years = calculationPolicyAnnualityYears(policy.year_from, policy.year_to);
  return {
    payment_deadline_mode: policy.payment_deadline_mode ?? "fixed_date",
    payment_due_date: date,
    payment_due_dates_by_year: Object.fromEntries(years.map((year) => [String(year), date])),
  };
}

export function paymentDeadlineOptions(form: CalculationPolicyFormState, date: string | undefined) {
  return {
    payment_deadline_mode: form.payment_deadline_mode,
    payment_due_date: optionalDate(date),
  };
}

export function formatPaymentDeadline(policy: RuoloTributiCalculationPolicyResponse) {
  return policy.payment_deadline_mode === "notification_60_days"
    ? `60 giorni dalla data di notifica; scadenza bollettino ${formatPolicyDate(policy.payment_due_date)}`
    : formatPolicyDate(policy.payment_due_date);
}

export function PolicyPaymentDeadlineFields({ form, onChange, years }: {
  form: CalculationPolicyFormState;
  onChange: (value: CalculationPolicyFormState) => void;
  years: number[];
}) {
  return <>
    <label className="grid gap-1 text-sm font-medium text-gray-700">
      Scadenza pagamento avviso
      <select aria-label="Scadenza pagamento avviso" value={form.payment_deadline_mode} onChange={(event) => onChange({ ...form, payment_deadline_mode: event.target.value as CalculationPolicyFormState["payment_deadline_mode"] })} className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-normal">
        <option value="fixed_date">Data fissa</option>
        <option value="notification_60_days">Entro 60 giorni dalla data di notifica</option>
      </select>
    </label>
    {form.payment_deadline_mode === "notification_60_days" ? (
      <p className="text-xs text-gray-600">Il termine decorre dalla notifica. Se cade di sabato o in un giorno festivo, la scadenza è spostata al primo giorno lavorativo successivo.</p>
    ) : null}
    <>
      {years.length > 1 ? years.map((year) => (
        <PolicyDateInput key={year} label={`Pagamento avviso entro ${year}`} value={form.payment_due_dates_by_year[String(year)] ?? ""} onChange={(value) => onChange({ ...form, payment_due_dates_by_year: { ...form.payment_due_dates_by_year, [year]: value } })} />
      )) : (
        <PolicyDateInput label="Pagamento avviso entro" value={form.payment_due_date} onChange={(value) => onChange({ ...form, payment_due_date: value })} />
      )}
      <p className="text-xs text-gray-600">Con il termine a 60 giorni, per stampare il bollettino è obbligatoria una data fissa nelle Regole ruolo. Il termine di notifica dell&apos;avviso resta invariato.</p>
    </>
  </>;
}
