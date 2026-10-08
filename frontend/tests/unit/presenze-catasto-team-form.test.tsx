import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { TeamFormFields, type TeamFormState } from "@/app/presenze/squadre/team-form-fields";

function Form() {
  const [value, setValue] = useState<TeamFormState>({ name: "", code: "", personnelArea: "AGRARIO" });
  return <><TeamFormFields value={value} setValue={setValue} /><output>{JSON.stringify(value)}</output></>;
}

describe("Catasto team classification", () => {
  it("retains names and codes while selecting Catasto as its own area", () => {
    render(<Form />);
    fireEvent.change(screen.getByPlaceholderText("Es. Squadra Nord"), { target: { value: "Catasto" } });
    fireEvent.change(screen.getByPlaceholderText("NORD"), { target: { value: "CAT" } });
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "CATASTO" } });
    expect(screen.getByRole("combobox")).toHaveValue("CATASTO");
    expect(screen.getByRole("status")).toHaveTextContent('"name":"Catasto","code":"CAT","personnelArea":"CATASTO"');
  });
});
