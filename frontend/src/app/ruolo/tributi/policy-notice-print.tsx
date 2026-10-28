import type {
  RuoloTributiCalculationPolicyResponse,
  RuoloTributiCalculationPolicyUpsertRequest,
} from "@/types/ruolo";
import {
  annualityPolicyPayload,
  calculationPolicyFormFromPolicy,
  calculationPolicyPayload,
  formatPolicyBollettino,
  type CalculationPolicyFormState,
} from "./calculation-policy-form";
import { PolicyBollettinoFields } from "./policy-bollettino-fields";
import { formatPaymentDeadline, paymentDeadlineForm, paymentDeadlineOptions, PolicyPaymentDeadlineFields } from "./policy-payment-deadline";
import { formatNoticeLayout, noticeLayoutOptions } from "./policy-notice-numbering";

// Notice print options of a rule: TD 896 slip and the "QUANTO E QUANDO PAGARE" payment date.

function bollettinoPrintOptions(policy: Pick<RuoloTributiCalculationPolicyResponse, "print_bollettino" | "bollettino_version" | "notice_number_source">) {
  return {
    print_bollettino: policy.print_bollettino !== false,
    ...noticeLayoutOptions(policy),
  };
}

export function policyFormWithNoticePrint(policy: RuoloTributiCalculationPolicyResponse): CalculationPolicyFormState {
  return {
    ...calculationPolicyFormFromPolicy(policy),
    ...bollettinoPrintOptions(policy),
    ...paymentDeadlineForm(policy),
  };
}

export function policyPayloadWithNoticePrint(form: CalculationPolicyFormState): RuoloTributiCalculationPolicyUpsertRequest {
  return {
    ...calculationPolicyPayload(form),
    ...bollettinoPrintOptions(form),
    ...paymentDeadlineOptions(form, form.payment_due_date),
  };
}

export function annualityPayloadWithNoticePrint(form: CalculationPolicyFormState, year: number): RuoloTributiCalculationPolicyUpsertRequest {
  return {
    ...annualityPolicyPayload(form, year),
    ...bollettinoPrintOptions(form),
    ...paymentDeadlineOptions(form, form.payment_due_dates_by_year[String(year)]),
  };
}

export function formatPolicyNoticePrint(policy: RuoloTributiCalculationPolicyResponse): string {
  const bollettino = policy.print_bollettino === false ? "Bollettino: non stampato" : formatPolicyBollettino(policy);
  return `${bollettino} · ${formatNoticeLayout(policy)} · pagamento avviso entro ${formatPaymentDeadline(policy)}`;
}

export function PolicyNoticePrintFields({ form, onChange, years }: {
  form: CalculationPolicyFormState;
  onChange: (value: CalculationPolicyFormState) => void;
  years: number[];
}) {
  return (
    <div className="grid gap-2 rounded-xl border border-amber-100 bg-amber-50/60 p-3">
      <label className="flex items-center gap-2 text-sm text-gray-700">
        <input type="checkbox" aria-label="Stampa bollettino postale" checked={form.print_bollettino} onChange={(event) => onChange({ ...form, print_bollettino: event.target.checked })} />
        Stampa bollettino postale
      </label>
      <p className="text-xs text-gray-600">Senza bollettino l&apos;avviso indica solo bonifico e pagoPA. Con piu annualita il bollettino si stampa solo se tutte le regole lo prevedono.</p>
      <PolicyBollettinoFields form={form} onChange={onChange} />
      <PolicyPaymentDeadlineFields form={form} onChange={onChange} years={years} />
    </div>
  );
}
