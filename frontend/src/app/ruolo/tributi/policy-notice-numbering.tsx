import type { RuoloTributiCalculationPolicyResponse } from "@/types/ruolo";
import type { CalculationPolicyFormState } from "./calculation-policy-form";

// Notice numbering of a rule: a new GAIA number per taxpayer, or the existing inCASS avviso number.

type NoticeLayout = Pick<RuoloTributiCalculationPolicyResponse, "bollettino_version" | "notice_number_source">;
type Props = {
  form: CalculationPolicyFormState;
  onChange: (value: CalculationPolicyFormState) => void;
};

export function noticeLayoutOptions(policy: NoticeLayout) {
  return {
    bollettino_version: policy.bollettino_version ?? "v1",
    notice_number_source: policy.notice_number_source ?? "gaia",
  };
}

export function formatNoticeLayout(policy: NoticeLayout): string {
  const options = noticeLayoutOptions(policy);
  const numbering = options.notice_number_source === "incass" ? " · numero avviso inCASS (anche causale)" : "";
  return `versione ${options.bollettino_version.slice(1)}${numbering}`;
}

export function NoticeNumberSourceField({ form, onChange }: Props) {
  return (
    <label className="grid gap-1 text-xs font-semibold text-gray-600 sm:col-span-2">
      Numero avviso
      <select aria-label="Numero avviso" value={form.notice_number_source} onChange={(event) => onChange({ ...form, notice_number_source: event.target.value as "gaia" | "incass" })} className="rounded-xl border border-gray-200 px-3 py-2 text-sm font-normal outline-none focus:border-amber-400">
        <option value="gaia">Nuovo numero GAIA - un avviso per contribuente</option>
        <option value="incass">Numero avviso inCASS esistente - un avviso per ogni avviso inCASS</option>
      </select>
      <span className="font-normal">Con il numero inCASS non si genera un nuovo numero: il bollettino usa il numero dell&apos;avviso inCASS come codice cliente e come causale.</span>
    </label>
  );
}

export function IncassCausaleNote() {
  return (
    <p className="grid gap-1 text-xs font-semibold text-gray-600">
      Causale bollettino
      <span className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-normal">Numero avviso inCASS</span>
    </p>
  );
}
