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

  test("renders selected file, hint and disabled state", () => {
    const file = new File(["demo"], "letture.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    render(
      <CatastoFilePicker
        id="file-picker"
        label="File Excel"
        accept=".xlsx"
        file={file}
        onChange={() => undefined}
        hint="Formato XLSX"
        buttonLabel="Carica"
        disabled
      />,
    );

    expect(screen.getByText("Carica")).toBeInTheDocument();
    expect(screen.getByText("letture.xlsx")).toBeInTheDocument();
    expect(screen.getByText("Formato XLSX")).toBeInTheDocument();
    expect(document.getElementById("file-picker")).toBeDisabled();
  });

  test("renders multi-file selected label", () => {
    const fileA = new File(["a"], "D01-Sinis 2025.xlsx", { type: "application/vnd.ms-excel" });
    const fileB = new File(["b"], "D02-Terralba 2025.xlsx", { type: "application/vnd.ms-excel" });

    render(
      <CatastoFilePicker
        id="file-picker"
        label="File Excel"
        accept=".xlsx"
        files={[fileA, fileB]}
        onChange={() => undefined}
        multiple
      />,
    );

    expect(screen.getByText("2 file selezionati")).toBeInTheDocument();
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

  test("calls onChange with null when single selection is cleared", () => {
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

    fireEvent.change(document.getElementById("file-picker"), { target: { files: [] } });

    expect(onChange).toHaveBeenCalledWith(null);
  });

  test("handles file input change events without a FileList", () => {
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

    fireEvent.change(document.getElementById("file-picker"), { target: { files: null } });

    expect(onChange).toHaveBeenCalledWith(null);
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

  test("supports multiple mode without an onChangeFiles callback", () => {
    const onChange = vi.fn();

    render(
      <CatastoFilePicker
        id="file-picker"
        label="File Excel"
        accept=".xlsx"
        files={[]}
        onChange={onChange}
        multiple
      />,
    );

    fireEvent.change(document.getElementById("file-picker"), { target: { files: [] } });

    expect(onChange).toHaveBeenCalledWith(null);
  });
});
