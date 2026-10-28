import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { EMPTY_CALCULATION_POLICY_FORM, type CalculationPolicyFormState } from "@/app/ruolo/tributi/calculation-policy-form";
import { PolicyNoticePrintFields, policyFormWithNoticePrint, policyPayloadWithNoticePrint, annualityPayloadWithNoticePrint, formatPolicyNoticePrint } from "@/app/ruolo/tributi/policy-notice-print";
import type { RuoloTributiCalculationPolicyResponse } from "@/types/ruolo";

const policy: RuoloTributiCalculationPolicyResponse = {
  id: "policy", name: "Regola", year_from: 2024, year_to: 2025,
  bonario_due_date: null, surcharge_rate_percent: 0, surcharge_from: null,
  euribor_6m_rate_percent: 0, euribor_source_url: null, euribor_reference_period: null,
  euribor_fetched_at: null, interest_rate_percent: 0, effective_interest_rate_percent: 0,
  interest_from: null, interest_start_mode: "fixed_date", bollettino_causale: "010",
  bollettino_esercizio: "2626", print_bollettino: true, payment_due_date: "2026-11-30",
  is_active: true, notes: null, updated_by: null, created_at: "", updated_at: "",
};

function Form({ initial, years }: { initial: CalculationPolicyFormState; years: number[] }) {
  const [form, setForm] = useState(initial);
  return <PolicyNoticePrintFields form={form} onChange={setForm} years={years} />;
}

describe("payment due within sixty days of notification", () => {
  test("restores a legacy notification rule without a slip date for correction", () => {
    const legacy = { ...policy, payment_deadline_mode: "notification_60_days" as const, payment_due_date: null };
    const form = policyFormWithNoticePrint(legacy);
    expect(form.payment_due_date).toBe("");
    expect(policyPayloadWithNoticePrint(form).payment_due_date).toBeNull();
    expect(annualityPayloadWithNoticePrint(form, 2024).payment_due_date).toBeNull();
    expect(formatPolicyNoticePrint(legacy)).toContain("scadenza bollettino -");
    render(<Form initial={form} years={[2024, 2025]} />);
    expect(screen.getByLabelText("Pagamento avviso entro 2024")).toHaveValue("");
    expect(screen.getByLabelText("Pagamento avviso entro 2025")).toHaveValue("");
    expect(screen.getByText(/è obbligatoria una data fissa/)).toBeInTheDocument();
  });

  test("restores saved mode, serializes it for single and annual rules, and keeps the fixed slip date", () => {
    const form = policyFormWithNoticePrint({ ...policy, payment_deadline_mode: "notification_60_days" });
    expect(form.payment_deadline_mode).toBe("notification_60_days");
    expect(policyPayloadWithNoticePrint(form)).toMatchObject({ payment_deadline_mode: "notification_60_days", payment_due_date: "2026-11-30" });
    expect(annualityPayloadWithNoticePrint(form, 2024)).toMatchObject({ payment_deadline_mode: "notification_60_days", payment_due_date: "2026-11-30" });
    expect(formatPolicyNoticePrint({ ...policy, payment_deadline_mode: "notification_60_days" })).toContain("pagamento avviso entro 60 giorni dalla data di notifica");
    const old = policyFormWithNoticePrint(policy);
    expect(old.payment_deadline_mode).toBe("fixed_date");
    expect(policyPayloadWithNoticePrint(old).payment_due_date).toBe("2026-11-30");
    expect(annualityPayloadWithNoticePrint(old, 2025).payment_due_date).toBe("2026-11-30");
    expect(annualityPayloadWithNoticePrint(old, 2030).payment_due_date).toBeNull();
    expect(formatPolicyNoticePrint(policy)).toContain("pagamento avviso entro 30/11/2026");
  });

  test("keeps a date available for the slip when switching to notification terms", () => {
    render(<Form initial={{ ...EMPTY_CALCULATION_POLICY_FORM, payment_due_date: "2026-11-30" }} years={[2021]} />);
    const mode = screen.getByLabelText("Scadenza pagamento avviso");
    expect(screen.getByLabelText("Pagamento avviso entro")).toHaveValue("30/11/2026");
    fireEvent.change(mode, { target: { value: "notification_60_days" } });
    expect(screen.getByLabelText("Pagamento avviso entro")).toHaveValue("30/11/2026");
    expect(screen.getByText(/è obbligatoria una data fissa/)).toBeInTheDocument();
    expect(screen.getByText(/Il termine decorre dalla notifica/)).toHaveTextContent("primo giorno lavorativo successivo");
    fireEvent.change(mode, { target: { value: "fixed_date" } });
    fireEvent.change(screen.getByLabelText("Pagamento avviso entro"), { target: { value: "10/12/2026" } });
    expect(screen.getByLabelText("Pagamento avviso entro")).toHaveValue("10/12/2026");
  });

  test("allows individual annual fixed dates and restores their controls after changing mode", () => {
    render(<Form initial={{ ...EMPTY_CALCULATION_POLICY_FORM, payment_due_dates_by_year: { "2024": "2026-11-30" } }} years={[2024, 2025]} />);
    expect(screen.getByLabelText("Pagamento avviso entro 2025")).toHaveValue("");
    fireEvent.change(screen.getByLabelText("Pagamento avviso entro 2025"), { target: { value: "10/12/2026" } });
    expect(screen.getByLabelText("Pagamento avviso entro 2025")).toHaveValue("10/12/2026");
    fireEvent.change(screen.getByLabelText("Scadenza pagamento avviso"), { target: { value: "notification_60_days" } });
    expect(screen.getByLabelText("Pagamento avviso entro 2024")).toHaveValue("30/11/2026");
    fireEvent.change(screen.getByLabelText("Scadenza pagamento avviso"), { target: { value: "fixed_date" } });
    expect(screen.getByLabelText("Pagamento avviso entro 2024")).toHaveValue("30/11/2026");
    expect(screen.getByLabelText("Pagamento avviso entro 2025")).toHaveValue("10/12/2026");
  });
});
