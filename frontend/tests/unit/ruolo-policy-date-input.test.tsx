import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { PolicyDateInput, formatPolicyDate } from "@/app/ruolo/tributi/policy-date-input";

function Form() {
  const [value, setValue] = useState("");
  return <form><PolicyDateInput label="Scadenza" value={value} onChange={setValue} /><button type="button" onClick={() => setValue("")}>Azzera</button></form>;
}

describe("Italian policy dates", () => {
  test.each([null, undefined, ""])("represents an absent summary date %s", (value) => {
    expect(formatPolicyDate(value)).toBe("-");
  });

  test("displays ISO dates with a four-digit year and emits ISO after Italian input", () => {
    const change = vi.fn();
    render(<PolicyDateInput label="Scadenza" value="2026-07-31" onChange={change} />);
    const field = screen.getByRole("textbox", { name: "Scadenza" });
    expect(field).toHaveValue("31/07/2026");
    fireEvent.change(field, { target: { value: "05/08/2026" } });
    expect(change).toHaveBeenCalledWith("2026-08-05");
  });

  test.each(["31/02/2026", "29/02/2025", "01/13/2026", "01/01/0000", "12/03/26", "15/", "03/31/2026"])("rejects invalid or incomplete input %s", (value) => {
    render(<Form />);
    const field = screen.getByRole("textbox", { name: "Scadenza" });
    fireEvent.change(field, { target: { value } });
    expect(field).toHaveValue(value);
    expect(field).toBeInvalid();
    expect(field.closest("form")!.checkValidity()).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Azzera" }));
    expect(field).toHaveValue("");
    expect(field).toBeValid();
  });

  test("accepts a leap day and synchronizes the calendar and clearing", () => {
    render(<Form />);
    const field = screen.getByRole("textbox", { name: "Scadenza" });
    const calendar = screen.getByLabelText("Calendario Scadenza");
    expect(field).toHaveAttribute("placeholder", "gg/mm/aaaa");
    fireEvent.change(field, { target: { value: "29/02/2024" } });
    expect(field).toBeValid();
    expect(calendar).toHaveValue("2024-02-29");
    fireEvent.change(calendar, { target: { value: "2026-11-15" } });
    expect(field).toHaveValue("15/11/2026");
    fireEvent.change(calendar, { target: { value: "" } });
    expect(field).toHaveValue("");
    expect(field).toBeValid();
  });
});
