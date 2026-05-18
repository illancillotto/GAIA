import { fireEvent, render, screen } from "@testing-library/react";

import { CatastoFilePicker } from "@/components/catasto/file-picker";

describe("CatastoFilePicker", () => {
  test("renders empty state label", () => {
    render(
      <CatastoFilePicker
        id="file-picker"
        label="File Excel"
        accept=".xlsx"
        file={null}
        onChange={() => undefined}
      />,
    );

    expect(screen.getByText("File Excel")).toBeInTheDocument();
    expect(screen.getByText("Nessun file selezionato")).toBeInTheDocument();
  });

  test("calls onChange with selected file in single mode", () => {
    const onChange = vi.fn();

    render(
      <CatastoFilePicker
        id="file-picker"
        label="File Excel"
        accept=".xlsx"
        file={null}
        onChange={onChange}
      />,
    );

    const input = document.getElementById("file-picker");
    const file = new File(["demo"], "D01-Sinis 2025.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    fireEvent.change(input, { target: { files: [file] } });

    expect(onChange).toHaveBeenCalledWith(file);
  });

  test("calls onChangeFiles in multiple mode", () => {
    const onChange = vi.fn();
    const onChangeFiles = vi.fn();

    render(
      <CatastoFilePicker
        id="file-picker"
        label="File Excel"
        accept=".xlsx"
        files={[]}
        onChange={onChange}
        onChangeFiles={onChangeFiles}
        multiple
      />,
    );

    const input = document.getElementById("file-picker");
    const fileA = new File(["a"], "D01-Sinis 2025.xlsx", { type: "application/vnd.ms-excel" });
    const fileB = new File(["b"], "D02-Terralba 2025.xlsx", { type: "application/vnd.ms-excel" });

    fireEvent.change(input, { target: { files: [fileA, fileB] } });

    expect(onChangeFiles).toHaveBeenCalledWith([fileA, fileB]);
    expect(onChange).toHaveBeenCalledWith(fileA);
  });
});
