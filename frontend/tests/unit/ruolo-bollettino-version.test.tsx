import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { EMPTY_CALCULATION_POLICY_FORM } from "@/app/ruolo/tributi/calculation-policy-form";
import { PolicyBollettinoFields } from "@/app/ruolo/tributi/policy-bollettino-fields";
import {
  annualityPayloadWithNoticePrint,
  formatPolicyNoticePrint,
  policyFormWithNoticePrint,
  policyPayloadWithNoticePrint,
} from "@/app/ruolo/tributi/policy-notice-print";
import type { RuoloTributiCalculationPolicyResponse } from "@/types/ruolo";

const policy: RuoloTributiCalculationPolicyResponse = {
  id: "policy", name: "Regola", year_from: 2026, year_to: 2026,
  bonario_due_date: null, surcharge_rate_percent: 0, surcharge_from: null,
  euribor_6m_rate_percent: 0, euribor_source_url: null, euribor_reference_period: null,
  euribor_fetched_at: null, interest_rate_percent: 0, effective_interest_rate_percent: 0,
  interest_from: null, interest_start_mode: "fixed_date", bollettino_causale: "010",
  bollettino_esercizio: "2626", bollettino_version: "v2", print_bollettino: true,
  is_active: true, notes: null, updated_by: null, created_at: "", updated_at: "",
};

describe("saved postal slip layout", () => {
  test("defaults to v1 and lets the user choose either layout", () => {
    const onChange = vi.fn();
    const form = { ...EMPTY_CALCULATION_POLICY_FORM };
    const view = render(<PolicyBollettinoFields form={form} onChange={onChange} />);
    expect(screen.getByLabelText("Versione bollettino")).toHaveValue("v1");
    fireEvent.change(screen.getByLabelText("Versione bollettino"), { target: { value: "v2" } });
    expect(onChange).toHaveBeenLastCalledWith({ ...form, bollettino_version: "v2" });
    view.rerender(<PolicyBollettinoFields form={{ ...form, bollettino_version: "v2" }} onChange={onChange} />);
    expect(screen.getByLabelText("Versione bollettino")).toHaveValue("v2");
    fireEvent.change(screen.getByLabelText("Versione bollettino"), { target: { value: "v1" } });
    expect(onChange).toHaveBeenLastCalledWith({ ...form, bollettino_version: "v1" });
  });

  test("restores v2 on edit and preserves it in single-year and annuality payloads", () => {
    const form = policyFormWithNoticePrint(policy);
    expect(form.bollettino_version).toBe("v2");
    expect(policyPayloadWithNoticePrint(form).bollettino_version).toBe("v2");
    expect(annualityPayloadWithNoticePrint(form, 2026).bollettino_version).toBe("v2");
    expect(formatPolicyNoticePrint(policy)).toContain("versione 2");
    expect(policyFormWithNoticePrint({ ...policy, bollettino_version: undefined }).bollettino_version).toBe("v1");
    expect(formatPolicyNoticePrint({ ...policy, bollettino_version: undefined })).toContain("versione 1");
  });
});
