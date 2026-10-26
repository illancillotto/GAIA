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
  id: "policy", name: "2021", year_from: 2021, year_to: 2021,
  bonario_due_date: null, surcharge_rate_percent: 0, surcharge_from: null,
  euribor_6m_rate_percent: 0, euribor_source_url: null, euribor_reference_period: null,
  euribor_fetched_at: null, interest_rate_percent: 0, effective_interest_rate_percent: 0,
  interest_from: null, interest_start_mode: "fixed_date", bollettino_causale: null,
  bollettino_esercizio: "2021", bollettino_version: "v2", notice_number_source: "incass",
  print_bollettino: true, is_active: true, notes: null, updated_by: null, created_at: "", updated_at: "",
};

describe("notice number source of a rule", () => {
  test("defaults to GAIA numbers and switches the causale to the inCASS avviso", () => {
    const onChange = vi.fn();
    const form = { ...EMPTY_CALCULATION_POLICY_FORM };
    const view = render(<PolicyBollettinoFields form={form} onChange={onChange} />);
    expect(screen.getByLabelText("Numero avviso")).toHaveValue("gaia");
    expect(screen.getByLabelText("Causale bollettino")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Numero avviso"), { target: { value: "incass" } });
    expect(onChange).toHaveBeenLastCalledWith({ ...form, notice_number_source: "incass" });
    view.rerender(<PolicyBollettinoFields form={{ ...form, notice_number_source: "incass" }} onChange={onChange} />);
    expect(screen.queryByLabelText("Causale bollettino")).not.toBeInTheDocument();
    expect(screen.getByText("Numero avviso inCASS")).toBeInTheDocument();
  });

  test("restores and saves the inCASS choice in single-year and annuality payloads", () => {
    const form = policyFormWithNoticePrint(policy);
    expect(form.notice_number_source).toBe("incass");
    expect(policyPayloadWithNoticePrint(form).notice_number_source).toBe("incass");
    expect(annualityPayloadWithNoticePrint(form, 2021).notice_number_source).toBe("incass");
    expect(formatPolicyNoticePrint(policy)).toContain("numero avviso inCASS");
    const legacy = { ...policy, notice_number_source: undefined };
    expect(policyFormWithNoticePrint(legacy).notice_number_source).toBe("gaia");
    expect(formatPolicyNoticePrint(legacy)).not.toContain("inCASS");
  });
});
