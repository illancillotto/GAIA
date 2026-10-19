import type { ReactNode } from "react";
import type { RuoloTributiCalculationPolicyResponse } from "@/types/ruolo";
import {
  groupCalculationPolicies,
  type AnnualityRuleOptions,
  type CalculationPolicyFormState,
  type PolicyChargeMode,
} from "./calculation-policy-form";

type FormProps = {
  form: CalculationPolicyFormState;
  onChange: (form: CalculationPolicyFormState) => void;
};

export function PolicyRuleOptions({ value, onChange, suffix = "" }: {
  value: AnnualityRuleOptions;
  onChange: (change: Partial<AnnualityRuleOptions>) => void;
  suffix?: string;
}) {
  return (
    <div className="grid gap-2 rounded-xl border border-amber-100 bg-amber-50/60 p-3">
      <label className="grid gap-1 text-xs font-semibold text-gray-700">
        Componenti da applicare{suffix}
        <select aria-label={`Componenti da applicare${suffix}`} value={value.charge_mode} onChange={(event) => onChange({ charge_mode: event.target.value as PolicyChargeMode })} className="rounded-xl border border-gray-200 bg-white px-3 py-2">
          <option value="both">Maggiorazione e interessi</option>
          <option value="surcharge">Solo maggiorazione</option>
          <option value="interest">Solo interessi</option>
          <option value="none">Nessuno</option>
        </select>
      </label>
      <label className="flex items-center gap-2 text-sm text-gray-700">
        <input type="checkbox" aria-label={`Solo avvisi non notificati${suffix}`} checked={value.only_unnotified} onChange={(event) => onChange({ only_unnotified: event.target.checked })} />
        Solo avvisi non notificati{suffix}
      </label>
      <p className="text-xs text-gray-600">Esclude gli avvisi con consegna PEC o ricezione raccomandata documentata in GAIA. La sola accettazione PEC non basta. Le componenti escluse sono salvate con tasso zero.</p>
    </div>
  );
}

export function AnnualityPolicyFields({ form, onChange, years }: FormProps & { years: number[] }) {
  return (
    <div className="rounded-2xl border border-amber-100 bg-amber-50/70 p-3">
      <p className="text-xs font-semibold text-amber-900">Date per annualita</p>
      <p className="text-xs text-gray-600">Ogni anno eredita i valori comuni finche non li personalizzi.</p>
      <div className="mt-2 grid gap-2">
        {years.map((year) => <AnnualityRuleEditor key={year} form={form} onChange={onChange} year={year} />)}
      </div>
    </div>
  );
}

function AnnualityRuleEditor({ form, onChange, year }: FormProps & { year: number }) {
  const options = { ...form, ...form.rules_by_year[String(year)] };
  const update = (change: Partial<AnnualityRuleOptions>) => onChange({
    ...form,
    rules_by_year: { ...form.rules_by_year, [year]: { ...form.rules_by_year[String(year)], ...change } },
  });
  return (
    <fieldset className="grid gap-2 rounded-2xl border border-amber-100 bg-white p-3">
      <legend className="text-xs font-semibold text-amber-900">Annualita {year}</legend>
      <PolicyRuleOptions value={options} onChange={update} suffix={` ${year}`} />
      {([
        ["surcharge_rate_percent", "% maggiorazione ruolo"],
        ["euribor_6m_rate_percent", "% Euribor medio 6 mesi"],
        ["interest_rate_percent", "% tasso da delibera"],
      ] as const).map(([field, label]) => (
        <label key={field} className="grid gap-1 text-xs font-semibold text-gray-600">
          {label} {year}
          <input aria-label={`${label} ${year}`} value={options[field]} onChange={(event) => update({ [field]: event.target.value })} inputMode="decimal" className="rounded-xl border border-gray-200 px-3 py-2" />
        </label>
      ))}
      {([
        ["bonario_due_dates_by_year", "Scadenza pagamento bonario"],
        ["interest_from_by_year", "Fallback/minimo interessi"],
      ] as const).map(([field, label]) => (
        <label key={field} className="grid gap-1 text-xs font-semibold text-gray-600">
          {label} {year}
          <input aria-label={`${label} ${year}`} type="date" value={form[field][String(year)] ?? ""} onChange={(event) => onChange({ ...form, [field]: { ...form[field], [year]: event.target.value } })} className="rounded-xl border border-gray-200 px-3 py-2" />
        </label>
      ))}
      <label className="grid gap-1 text-xs font-semibold text-gray-600">
        Decorrenza interessi {year}
        <select aria-label={`Decorrenza interessi ${year}`} value={options.interest_start_mode} onChange={(event) => update({ interest_start_mode: event.target.value as AnnualityRuleOptions["interest_start_mode"] })} className="rounded-xl border border-gray-200 px-3 py-2">
          <option value="notification_date">Da invio PEC/ricezione raccomandata</option>
          <option value="fixed_date">Da data fissa policy</option>
        </select>
      </label>
    </fieldset>
  );
}

export function CalculationPolicyBlocks({ policies, renderRule }: {
  policies: RuoloTributiCalculationPolicyResponse[];
  renderRule: (policy: RuoloTributiCalculationPolicyResponse) => ReactNode;
}) {
  return groupCalculationPolicies(policies).map((block) => (
    <section key={block.name} aria-label={`Blocco ${block.name}`} className="space-y-3 rounded-2xl border border-amber-200 bg-amber-50/50 p-3">
      <h3 className="font-semibold text-amber-950">Blocco: {block.name}</h3>
      {block.rules.map(renderRule)}
    </section>
  ));
}

export function PolicyNotificationScope({ policy }: { policy: RuoloTributiCalculationPolicyResponse }) {
  return <p className="mt-1 text-xs font-semibold text-amber-900">{policy.only_unnotified ? "Solo avvisi non notificati" : "Tutti gli avvisi"}</p>;
}
