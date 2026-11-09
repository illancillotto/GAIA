import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/operazioni/operatori/page";

const mocks = vi.hoisted(() => ({
  role: "admin", operators: vi.fn(), areas: vi.fn(), detail: vi.fn(), unlinked: vi.fn(), save: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams("operatorId=wc-1") }));
vi.mock("@/components/operazioni/operazioni-module-page", () => ({
  OperazioniModulePage: ({ children }: { children: (value: unknown) => React.ReactNode }) => <main>{children({ currentUser: { role: mocks.role } })}</main>,
}));
vi.mock("@/features/operazioni/api/client", () => ({
  getOperators: mocks.operators, getAreas: mocks.areas, getOperatorDetail: mocks.detail,
  getUnlinkedOperators: mocks.unlinked, updateGateMobileConsolePermissions: mocks.save,
  autoLinkGaiaOperators: vi.fn(), bulkImportOperatorsAsGaiaUsers: vi.fn(), inviteOperator: vi.fn(),
}));

const operator = { id: "wc-1", wc_id: 100, username: "synthetic", email: "hr@example.test", first_name: "Synthetic", last_name: "HR",
  role: "operator", enabled: true, gaia_user_id: 77, gate_mobile_console_enabled: true, gate_mobile_console_role: "viewer",
  current_fuel_cards: [], created_at: "2026-10-01", updated_at: "2026-10-01" };

beforeEach(() => {
  vi.resetAllMocks(); mocks.role = "admin";
  mocks.operators.mockResolvedValue({ items: [operator], total: 1 });
  mocks.areas.mockResolvedValue({ items: [], total: 0 });
  mocks.unlinked.mockResolvedValue({ items: [], total: 0 });
  mocks.detail.mockResolvedValue({ operator, stats: { fuel_cards_count: 0, total_liters: "0", total_km_travelled: "0", usage_sessions_count: 0 },
    current_fuel_cards: [], recent_fuel_logs: [], recent_usage_sessions: [] });
  mocks.save.mockImplementation(async (_id, data) => ({ ...operator, gate_mobile_console_enabled: data.enabled, gate_mobile_console_role: data.role }));
});

describe("HR console permission assignment", () => {
  it("offers HR in the real operator dialog, saves the role, and refreshes the displayed assignment", async () => {
    render(<Page />);
    const select = await screen.findByRole("combobox", { name: "Ruolo console" });
    await waitFor(() => expect(select).toBeEnabled());
    expect(screen.getByRole("option", { name: "Risorse umane · tutte le aree" })).toHaveValue("hr_manager");
    fireEvent.change(select, { target: { value: "hr_manager" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva permessi console" }));
    await waitFor(() => expect(mocks.save).toHaveBeenCalledWith("wc-1", { enabled: true, role: "hr_manager" }));
    expect(await screen.findByText("Abilitato · Risorse umane · tutte le aree")).toBeVisible();
    expect(select).toHaveValue("hr_manager");
  });

  it("keeps the selected HR role after a save failure and lets an admin disable access", async () => {
    mocks.save.mockRejectedValueOnce(new Error("Synthetic save unavailable"));
    render(<Page />);
    const select = await screen.findByRole("combobox", { name: "Ruolo console" });
    await waitFor(() => expect(select).toBeEnabled());
    fireEvent.change(select, { target: { value: "hr_manager" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva permessi console" }));
    expect(await screen.findByText("Synthetic save unavailable")).toBeVisible();
    expect(select).toHaveValue("hr_manager");
    fireEvent.click(screen.getByRole("checkbox"));
    expect(select).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Salva permessi console" }));
    await waitFor(() => expect(mocks.save).toHaveBeenLastCalledWith("wc-1", { enabled: false, role: null }));
    await waitFor(() => expect(screen.queryByText("Synthetic save unavailable")).toBeNull());
  });

  it("does not grant an HR user administration of other operators", async () => {
    mocks.role = "hr_manager";
    render(<Page />);
    await waitFor(() => expect(mocks.operators).toHaveBeenCalled());
    expect(screen.queryByRole("combobox", { name: "Ruolo console" })).toBeNull();
    expect(mocks.detail).not.toHaveBeenCalled(); expect(mocks.save).not.toHaveBeenCalled();
  });
});
