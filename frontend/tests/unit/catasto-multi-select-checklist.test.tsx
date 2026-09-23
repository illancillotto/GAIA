import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, test, vi } from "vitest";

import { MultiSelectChecklist } from "@/components/catasto/anagrafica/MultiSelectChecklist";

const options = [
  { value: "01", label: "01 · Sinis" },
  { value: "02", label: "02 · Arborea" },
  { value: "03", label: "03 · Oristano" },
];

function Harness({ initial = [] }: { initial?: string[] }) {
  const [selected, setSelected] = useState<string[]>(initial);
  return <MultiSelectChecklist label="Distretti" options={options} selected={selected} onChange={setSelected} />;
}

describe("MultiSelectChecklist", () => {
  test("toggles options on and off and shows the selection counter", () => {
    render(<Harness />);

    fireEvent.click(screen.getByRole("checkbox", { name: /Sinis/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Oristano/ }));
    expect(screen.getByText(/\(2 selezionati\)/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: /Sinis/ }));
    expect(screen.getByRole("checkbox", { name: /Sinis/ })).not.toBeChecked();
    expect(screen.getByText(/\(1 selezionati\)/)).toBeInTheDocument();
  });

  test("selects all and clears all options keeping the original order", () => {
    const onChange = vi.fn();
    render(<MultiSelectChecklist label="Distretti" options={options} selected={["03"]} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Seleziona tutti" }));
    expect(onChange).toHaveBeenLastCalledWith(["01", "02", "03"]);

    fireEvent.click(screen.getByRole("button", { name: "Deseleziona" }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });

  test("filter limits select-all and clear to the visible options", () => {
    const onChange = vi.fn();
    render(<MultiSelectChecklist label="Distretti" options={options} selected={["01"]} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText("Filtra distretti"), { target: { value: "ARBO" } });
    expect(screen.queryByRole("checkbox", { name: /Sinis/ })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Seleziona tutti" }));
    expect(onChange).toHaveBeenLastCalledWith(["01", "02"]);

    fireEvent.click(screen.getByRole("button", { name: "Deseleziona" }));
    expect(onChange).toHaveBeenLastCalledWith(["01"]);
  });

  test("shows a message when the filter matches nothing", () => {
    render(<Harness />);

    fireEvent.change(screen.getByLabelText("Filtra distretti"), { target: { value: "zzz" } });
    expect(screen.getByText("Nessun risultato per il filtro.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Seleziona tutti" })).toBeDisabled();
  });

  test("shows the empty message when there are no options", () => {
    render(
      <MultiSelectChecklist label="Comuni" options={[]} selected={[]} onChange={vi.fn()} emptyMessage="Nessun comune." disabled />,
    );

    expect(screen.getByText("Nessun comune.")).toBeInTheDocument();
    expect(screen.getByLabelText("Filtra comuni")).toBeDisabled();
  });

  test("uses the default empty message", () => {
    render(<MultiSelectChecklist label="Comuni" options={[]} selected={[]} onChange={vi.fn()} />);

    expect(screen.getByText("Nessuna opzione disponibile.")).toBeInTheDocument();
  });
});
