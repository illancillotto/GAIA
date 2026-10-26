import type { CalculationPolicyFormState } from "./calculation-policy-form";
import { IncassCausaleNote, NoticeNumberSourceField } from "./policy-notice-numbering";


type Props = {
  form: CalculationPolicyFormState;
  onChange: (value: CalculationPolicyFormState) => void;
};

export function PolicyBollettinoFields({ form, onChange }: Props) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      <BollettinoVersionField form={form} onChange={onChange} /><NoticeNumberSourceField form={form} onChange={onChange} />
      <BollettinoCausaleField form={form} onChange={onChange} />
      <BollettinoCodeField label="Esercizio bollettino" value={form.bollettino_esercizio} length={4} placeholder="es. 2525" onChange={(value) => onChange({ ...form, bollettino_esercizio: value })} />
    </div>
  );
}

function BollettinoCausaleField({ form, onChange }: Props) {
  if (form.notice_number_source === "incass") return <IncassCausaleNote />;
  return <BollettinoCodeField label="Causale bollettino" value={form.bollettino_causale} length={3} placeholder="es. 425" onChange={(value) => onChange({ ...form, bollettino_causale: value })} />;
}

function BollettinoVersionField({ form, onChange }: Props) {
  return (
    <label className="grid gap-1 text-xs font-semibold text-gray-600 sm:col-span-2">
      Versione bollettino
      <select aria-label="Versione bollettino" value={form.bollettino_version} onChange={(event) => onChange({ ...form, bollettino_version: event.target.value as "v1" | "v2" })} className="rounded-xl border border-gray-200 px-3 py-2 text-sm font-normal outline-none focus:border-amber-400">
        <option value="v1">Versione 1 - modello attuale</option>
        <option value="v2">Versione 2 - modello Poste</option>
      </select>
      <span className="font-normal">Per avvisi con più annualità si usa la versione della regola dell&apos;anno più recente.</span>
    </label>
  );
}

function BollettinoCodeField({ label, value, length, placeholder, onChange }: {
  label: string; value: string; length: number; placeholder: string; onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-1 text-xs font-semibold text-gray-600">
      {label}
      <input aria-label={label} value={value} onChange={(event) => onChange(digits(event.target.value, length))} inputMode="numeric" maxLength={length} placeholder={placeholder} className="rounded-xl border border-gray-200 px-3 py-2 text-sm font-normal outline-none focus:border-amber-400" />
    </label>
  );
}

export function PolicyAnnualityCard({
  label,
  bonarioDueDate,
  surchargeFrom,
  interestFrom,
  bollettino,
}: {
  label: string;
  bonarioDueDate: string;
  surchargeFrom: string;
  interestFrom: string;
  bollettino: string;
}) {
  return (
    <p className="rounded-2xl border border-amber-100 bg-amber-50/60 px-3 py-2 leading-5">
      <span className="font-semibold text-amber-900">{label}</span>
      <span className="block">Scadenza bonaria {bonarioDueDate}</span>
      <span className="block">Maggiorazione dal {surchargeFrom}</span>
      <span className="block">Fallback/minimo interessi {interestFrom}</span>
      <span className="block">{bollettino}</span>
    </p>
  );
}

function digits(value: string, maxLength: number): string {
  return value.replace(/\D/g, "").slice(0, maxLength);
}
