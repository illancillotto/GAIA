import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { CreateUnitModal, ReplaceImportConfirmModal, AddOverrideModal } from "@/features/organigramma/organigramma-workspace";
import type { ApplicationUser, OrgUnitTreeNode } from "@/types/api";

const parent: OrgUnitTreeNode = {
  id: "parent", nome: "Direzione", tipo: "direzione", parent_id: null,
  canvas_x: 0, canvas_y: 0, source: "manuale", wc_area_id: null, legacy_team_id: null,
  is_active: true, sort_order: 0, person_count: 0, child_count: 0, children: [],
};
const user = { id: 1, full_name: null, username: "operatore" } as ApplicationUser;

describe("unit creation modal", () => {
  test.each([new Error("Creazione rifiutata"), "errore remoto"])("allows retry after its callback rejects (%s)", async (failure) => {
    const create = vi.fn().mockRejectedValueOnce(failure).mockResolvedValue(undefined);
    render(<CreateUnitModal units={[parent]} unassignedUsers={[user]} defaultParentId="parent" defaultType="settore" onClose={vi.fn()} onCreate={create} />);
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: " Nuovo settore " } });
    fireEvent.change(screen.getByLabelText("Responsabile iniziale"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea unità" }));
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Errore di creazione")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Crea unità" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Crea unità" }));
    await waitFor(() => expect(create).toHaveBeenCalledTimes(2));
    expect(create).toHaveBeenLastCalledWith({ nome: "Nuovo settore", tipo: "settore", parent_id: "parent", source: "manuale", is_active: true }, 1);
  });

  test("validates input and updates defaults when props change", () => {
    const create = vi.fn();
    const close = vi.fn();
    const props = { units: [parent], unassignedUsers: [user], defaultParentId: null, defaultType: "settore" as const, onClose: close, onCreate: create };
    const rendered = render(<CreateUnitModal {...props} />);
    fireEvent.click(screen.getByRole("button", { name: "Crea unità" }));
    expect(screen.getByText("Inserisci il nome della nuova unità.")).toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
    rendered.rerender(<CreateUnitModal {...props} defaultParentId="parent" defaultType="reparto" />);
    expect(screen.getByLabelText("Tipo")).toHaveValue("reparto");
    expect(screen.getByLabelText("Unità padre")).toHaveValue("parent");
    fireEvent.change(screen.getByLabelText("Tipo"), { target: { value: "squadra" } });
    fireEvent.change(screen.getByLabelText("Unità padre"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Responsabile iniziale"), { target: { value: "1" } });
    fireEvent.change(screen.getByLabelText("Responsabile iniziale"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));
    expect(close).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("dialog").firstElementChild!);
    expect(close).toHaveBeenCalledTimes(2);
  });

  test("creates a root without a responsible person", async () => {
    const create = vi.fn().mockResolvedValue(undefined);
    render(<CreateUnitModal units={[]} unassignedUsers={[]} defaultParentId={null} defaultType="direzione" onClose={vi.fn()} onCreate={create} />);
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Radice" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea unità" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith({ nome: "Radice", tipo: "direzione", parent_id: null, source: "manuale", is_active: true }, null));
  });

  test("preserves validation when the default parent is absent from the catalog", async () => {
    const create = vi.fn().mockResolvedValue(undefined);
    render(<CreateUnitModal units={[parent]} unassignedUsers={[]} defaultParentId="missing" defaultType="settore" onClose={vi.fn()} onCreate={create} />);
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Settore" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea unità" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith({ nome: "Settore", tipo: "settore", parent_id: "missing", source: "manuale", is_active: true }, null));
  });

});

describe("replacement confirmation modal", () => {
  test("handles absent summary and filename, closes and applies the confirmation phrase", () => {
    const close = vi.fn();
    const confirm = vi.fn();
    const change = vi.fn();
    const props = { entityLabel: "struttura", filename: null, summary: null, confirmText: "", busy: false, onChangeConfirmText: change, onClose: close, onConfirm: confirm };
    const rendered = render(<ReplaceImportConfirmModal {...props} />);
    expect(screen.queryByText(/File selezionato/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Conferma replace" })).toBeDisabled();
    fireEvent.change(screen.getByPlaceholderText("SOSTITUISCI"), { target: { value: "SOSTITUISCI" } });
    expect(change).toHaveBeenCalledWith("SOSTITUISCI");
    rendered.rerender(<ReplaceImportConfirmModal {...props} confirmText="SOSTITUISCI" />);
    fireEvent.click(screen.getByRole("button", { name: "Conferma replace" }));
    expect(confirm).toHaveBeenCalledTimes(1);
    rendered.rerender(<ReplaceImportConfirmModal {...props} confirmText="SOSTITUISCI" busy />);
    expect(screen.getByRole("button", { name: "Import..." })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));
    fireEvent.click(screen.getByRole("dialog").firstElementChild!);
    expect(close).toHaveBeenCalledTimes(2);
  });
});

describe("override creation modal", () => {
  test("uses usernames when full names are absent for viewer and user target", () => {
    render(<AddOverrideModal users={[user]} units={[parent]} onClose={vi.fn()} onCreate={vi.fn()} />);
    expect(screen.getByLabelText("Viewer (utente)")).toHaveTextContent("operatore");
    fireEvent.change(screen.getByLabelText("Tipo target"), { target: { value: "user" } });
    expect(screen.getByLabelText("Target")).toHaveTextContent("operatore");
  });
  test("allows empty catalogs and cancels without creating an override", () => {
    const create = vi.fn();
    const close = vi.fn();
    render(<AddOverrideModal users={[]} units={[]} onClose={close} onCreate={create} />);
    fireEvent.click(screen.getByRole("button", { name: "Crea eccezione" }));
    expect(create).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));
    fireEvent.click(screen.getByRole("dialog").firstElementChild!);
    expect(close).toHaveBeenCalledTimes(2);
  });
});
