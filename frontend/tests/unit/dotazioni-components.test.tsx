import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { AssetForm } from "@/features/dotazioni/AssetForm";
import { AssetTable } from "@/features/dotazioni/AssetTable";
import { useResource } from "@/features/dotazioni/use-resource";
import type { Asset, Lookups } from "@/features/dotazioni/types";

export const fixtureAsset: Asset = {
  id: "asset-1", asset_code: "TEL-01", asset_type: "phone", name: "Telefono",
  description: null, brand: null, model: null, serial_number: null, imei: null,
  phone_number: null, mac_address: null, notes: null, status: "available",
  effective_status: "available", is_active: true, assigned_org_unit_id: null,
  assigned_org_unit_name: null, network_device_id: null, vehicle_id: null,
  plate_number: null, vehicle_status: null, current_custody: null,
};
const lookups: Lookups = { users: [], permissions: [], org_units: [{ id: "org-1", name: "Squadra Nord" }], network_devices: [{ id: 3, name: "Rete" }], vehicles: [{ id: "vehicle-1", name: "Mezzo" }] };

describe("Dotazioni asset form", () => {
  test("creates an asset with canonical relation types and invokes cancel", async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const cancel = vi.fn();
    render(<AssetForm lookups={lookups} canAssign onSave={save} onCancel={cancel} />);
    fireEvent.change(screen.getByLabelText("Codice"), { target: { value: "TEL-02" } });
    fireEvent.change(screen.getByLabelText("Tipologia"), { target: { value: "phone" } });
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Samsung" } });
    fireEvent.change(screen.getByLabelText("Unità organizzativa"), { target: { value: "org-1" } });
    fireEvent.change(screen.getByLabelText("Dispositivo Network"), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText("Veicolo"), { target: { value: "vehicle-1" } });
    fireEvent.click(screen.getByText("Salva"));
    await waitFor(() => expect(save).toHaveBeenCalledWith(expect.objectContaining({ asset_code: "TEL-02", asset_type: "phone", name: "Samsung", assigned_org_unit_id: "org-1", network_device_id: 3, vehicle_id: "vehicle-1", status: "available" })));
    await waitFor(() => expect(screen.getByText("Salva")).toBeEnabled());
    fireEvent.click(screen.getByText("Annulla"));
    expect(cancel).toHaveBeenCalledOnce();
  });
  test("edits existing values, disables reassignment and displays save errors", async () => {
    const save = vi.fn().mockRejectedValue(new Error("Permesso negato"));
    render(<AssetForm asset={{ ...fixtureAsset, brand: "Samsung", assigned_org_unit_id: "org-1" }} lookups={lookups} canAssign={false} onSave={save} onCancel={vi.fn()} />);
    expect(screen.getByText("Modifica dotazione")).toBeInTheDocument();
    expect(screen.getByLabelText("Marca")).toHaveValue("Samsung");
    expect(screen.getByLabelText("Unità organizzativa")).toBeDisabled();
    fireEvent.click(screen.getByText("Salva"));
    await screen.findByRole("alert");
    expect(screen.getByRole("alert")).toHaveTextContent("Permesso negato");
    expect(save.mock.calls[0][0]).not.toHaveProperty("assigned_org_unit_id");
    expect(save.mock.calls[0][0]).toMatchObject({ network_device_id: null, vehicle_id: null });
  });
  test("submits empty relation selections as null", async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    render(<AssetForm asset={fixtureAsset} lookups={lookups} canAssign onSave={save} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByText("Salva"));
    await waitFor(() => expect(save).toHaveBeenCalledWith(expect.objectContaining({ assigned_org_unit_id: null })));
  });
});

describe("Dotazioni table", () => {
  test("shows empty results", () => {
    render(<AssetTable assets={[]} />);
    expect(screen.getByText("Nessuna dotazione trovata.")).toBeInTheDocument();
  });
  test("renders both available assets and physical custody without deriving ownership", () => {
    render(<AssetTable assets={[fixtureAsset, { ...fixtureAsset, id: "asset-2", asset_code: "RAD-01", is_active: false, assigned_org_unit_name: "Nord", current_custody: { id: "custody", holder_user_id: 7, holder_name: "Mario Rossi", taken_at: "2026-10-01T07:15:00Z", returned_at: null, handover_from_user_id: null, notes: null, return_notes: null } }]} />);
    expect(screen.getByRole("link", { name: "TEL-01 · Telefono" })).toHaveAttribute("href", "/dotazioni/assets/asset-1");
    expect(screen.getByText("Mario Rossi")).toBeInTheDocument();
    expect(screen.getByText("01/10/2026, 09:15")).toBeInTheDocument();
    expect(screen.getByText("Disattivato")).toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(3);
  });
});

describe("Dotazioni asynchronous resources", () => {
  test("loads values and resets when the loader changes", async () => {
    const first = vi.fn().mockResolvedValue("first");
    const second = vi.fn().mockRejectedValue(new Error("Unavailable"));
    const { result, rerender } = renderHook(({ loader }) => useResource(loader), { initialProps: { loader: first } });
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.data).toBe("first"));
    rerender({ loader: second });
    await waitFor(() => expect(result.current.error).toBe("Unavailable"));
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
  });
  test.each([false, true])("ignores pending completions after unmount (failure=%s)", async (fails) => {
    let resolve!: (value: string) => void;
    let reject!: (reason: Error) => void;
    const promise = new Promise<string>((accept, fail) => { resolve = accept; reject = fail; });
    const { unmount } = renderHook(() => useResource(() => promise));
    unmount();
    await act(async () => {
      if (fails) reject(new Error("late failure")); else resolve("late success");
      await promise.catch(() => undefined);
    });
  });
});
