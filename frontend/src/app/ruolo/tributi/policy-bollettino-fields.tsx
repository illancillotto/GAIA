import type { CalculationPolicyFormState } from "./calculation-policy-form";


type Props = {
  form: CalculationPolicyFormState;
  onChange: (value: CalculationPolicyFormState) => void;
};

export function PolicyBollettinoFields({ form, onChange }: Props) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      <label className="grid gap-1 text-xs font-semibold text-gray-600">
        Causale bollettino
        <input aria-label="Causale bollettino" value={form.bollettino_causale} onChange={(event) => onChange({ ...form, bollettino_causale: digits(event.target.value, 3) })} inputMode="numeric" maxLength={3} placeholder="es. 425" className="rounded-xl border border-gray-200 px-3 py-2 text-sm font-normal outline-none focus:border-amber-400" />
      </label>
      <label className="grid gap-1 text-xs font-semibold text-gray-600">
        Esercizio bollettino
        <input aria-label="Esercizio bollettino" value={form.bollettino_esercizio} onChange={(event) => onChange({ ...form, bollettino_esercizio: digits(event.target.value, 4) })} inputMode="numeric" maxLength={4} placeholder="es. 2525" className="rounded-xl border border-gray-200 px-3 py-2 text-sm font-normal outline-none focus:border-amber-400" />
      </label>
    </div>
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
