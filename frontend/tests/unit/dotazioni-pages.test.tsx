import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { DotazioniList } from "@/features/dotazioni/DotazioniList";
import { AssetDetail } from "@/features/dotazioni/AssetDetail";
import DotazioniPage from "@/app/dotazioni/page";
import DotazionePage from "@/app/dotazioni/assets/[id]/page";
import DotazioneCodePage from "@/app/dotazioni/by-code/[code]/page";
import type { Asset, Lookups } from "@/features/dotazioni/types";

const mocks = vi.hoisted(() => ({ list: vi.fn(), lookups: vi.fn(), asset: vi.fn(), byCode: vi.fn(), update: vi.fn(), create: vi.fn(), history: vi.fn(), custody: vi.fn() }));
vi.mock("@/features/dotazioni/api", () => ({ dotazioniApi: mocks }));
vi.mock("next/navigation", () => ({ useParams: () => ({ id: "asset-1", code: "TEL/01" }) }));
vi.mock("@/components/app/protected-page", () => ({ ProtectedPage: ({ children, requiredModule, requiredSection }: { children: ReactNode; requiredModule: string; requiredSection: string }) => <main data-module={requiredModule} data-section={requiredSection}>{children}</main> }));
const asset: Asset = { id: "asset-1", asset_code: "TEL/01", asset_type: "phone", name: "Telefono", description: null, brand: "Samsung", model: null, serial_number: null, imei: null, phone_number: null, mac_address: null, notes: null, status: "available", effective_status: "available", is_active: true, assigned_org_unit_id: null, assigned_org_unit_name: null, network_device_id: null, vehicle_id: null, plate_number: null, vehicle_status: null, current_custody: null };
const lookups: Lookups = { users: [{ id: 7, name: "Mario" }], org_units: [{ id: "org-1", name: "Nord" }], network_devices: [], vehicles: [], permissions: ["dotazioni.view", "dotazioni.manage", "dotazioni.assign", "dotazioni.custody", "dotazioni.history"] };
beforeEach(() => {
  vi.clearAllMocks();
  mocks.lookups.mockResolvedValue(lookups);
  mocks.list.mockResolvedValue({ items: [asset], total: 26 });
  mocks.asset.mockResolvedValue(asset);
  mocks.byCode.mockResolvedValue(asset);
  mocks.update.mockResolvedValue(asset);
  mocks.create.mockResolvedValue(asset);
  mocks.custody.mockResolvedValue(asset);
  mocks.history.mockResolvedValue({ items: [], total: 0 });
});

describe("Dotazioni list", () => {
  test("provides filtering, pagination and create/cancel operations", async () => {
    render(<DotazioniList />);
    expect(screen.getByText("Caricamento permessi…")).toBeInTheDocument();
    await screen.findByText("TEL/01 · Telefono");
    fireEvent.click(screen.getByText("Successiva"));
    await screen.findByText("26 dotazioni · pagina 2");
    fireEvent.click(screen.getByText("Precedente"));
    await screen.findByText("26 dotazioni · pagina 1");
    const fields = [["Cerca", "TEL"], ["Tipologia", "phone"], ["Stato", "maintenance"], ["Unità / squadra", "org-1"], ["Custode", "7"], ["Attivi", "false"]];
    for (const [label, value] of fields) fireEvent.change(screen.getByLabelText(label), { target: { value } });
    await waitFor(() => expect(mocks.list.mock.calls.at(-1)?.[0].get("holder_user_id")).toBe("7"));
    expect(Object.fromEntries(mocks.list.mock.calls.at(-1)?.[0])).toMatchObject({ search: "TEL", asset_type: "phone", status: "maintenance", org_unit_id: "org-1", holder_user_id: "7", active: "false" });
    expect(screen.getByRole("heading", { name: "Dotazioni dell’unità / squadra selezionata" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "In manutenzione" })).toHaveValue("maintenance");
    fireEvent.change(screen.getByLabelText("Attivi"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "In custodia" }));
    await waitFor(() => expect(mocks.list.mock.calls.at(-1)?.[0].get("status")).toBe("in_use"));
    expect(screen.getByRole("button", { name: "In custodia" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Disponibili" }));
    await waitFor(() => expect(mocks.list.mock.calls.at(-1)?.[0].get("status")).toBe("available"));
    fireEvent.click(screen.getByRole("button", { name: "Tutti" }));
    await waitFor(() => expect(mocks.list.mock.calls.at(-1)?.[0].has("status")).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: "Nuova dotazione" }));
    fireEvent.click(screen.getByText("Annulla"));
    expect(screen.queryByText("Salva")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Nuova dotazione" }));
    for (const [label, value] of [["Codice", "RAD-01"], ["Tipologia", "radio"], ["Nome", "Radio"]]) fireEvent.change(screen.getAllByLabelText(label)[0], { target: { value } });
    fireEvent.click(screen.getByText("Salva"));
    await waitFor(() => expect(mocks.create).toHaveBeenCalledWith(expect.objectContaining({ asset_code: "RAD-01" })));
    await waitFor(() => expect(screen.queryByText("Salva")).not.toBeInTheDocument());
  });
  test("restricts administrative actions to permissions", async () => {
    mocks.lookups.mockResolvedValue({ ...lookups, permissions: ["dotazioni.view"] });
    render(<DotazioniList />);
    await screen.findByText("TEL/01 · Telefono");
    expect(screen.queryByRole("button", { name: "Nuova dotazione" })).not.toBeInTheDocument();
  });
  test("fails closed without view permission", async () => {
    mocks.lookups.mockResolvedValue({ ...lookups, permissions: [] });
    render(<DotazioniList />);
    await screen.findByText("Non sei autorizzato a consultare le dotazioni.");
  });
  test("reports metadata failures", async () => {
    mocks.lookups.mockRejectedValue(new Error("Metadati negati"));
    render(<DotazioniList />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Metadati negati");
  });
  test("reports asset failures and asynchronous loading", async () => {
    mocks.list.mockReturnValue(new Promise(() => undefined));
    const { unmount } = render(<DotazioniList />);
    await screen.findByText("Caricamento dotazioni…");
    unmount();
    mocks.list.mockRejectedValue(new Error("Lista negata"));
    render(<DotazioniList />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Lista negata");
  });
});

describe("asset detail", () => {
  test("renders details and permits editing and disabling", async () => {
    render(<AssetDetail id="asset-1" />);
    expect(screen.getByText("Caricamento dotazione…")).toBeInTheDocument();
    await screen.findByText("TEL/01 · Telefono");
    expect(screen.getByText("Custode corrente: Nessuno")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Link stabile per QR" })).toHaveAttribute("href", "/dotazioni/by-code/TEL%2F01");
    fireEvent.click(screen.getByText("Modifica dotazione"));
    fireEvent.click(screen.getByText("Annulla"));
    fireEvent.click(screen.getByText("Modifica dotazione"));
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Telefono aggiornato" } });
    fireEvent.click(screen.getByText("Salva"));
    await waitFor(() => expect(mocks.update).toHaveBeenCalledWith("asset-1", expect.objectContaining({ name: "Telefono aggiornato" })));
    expect(mocks.update.mock.calls.at(-1)?.[1]).not.toHaveProperty("asset_code");
    await waitFor(() => expect(screen.queryByText("Salva")).not.toBeInTheDocument());
    fireEvent.click(screen.getByText("Disattiva dotazione"));
    await waitFor(() => expect(mocks.update).toHaveBeenCalledWith("asset-1", { is_active: false }));
    await screen.findByText("TEL/01 · Telefono");
  });
  test("reports disable failures", async () => {
    mocks.update.mockRejectedValue(new Error("Disattivazione negata"));
    render(<AssetDetail id="asset-1" />);
    await screen.findByText("TEL/01 · Telefono");
    fireEvent.click(screen.getByText("Disattiva dotazione"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Disattivazione negata");
  });
  test("renders linked vehicle and network without creating vehicle custody", async () => {
    mocks.byCode.mockResolvedValue({ ...asset, is_active: false, network_device_id: 9, vehicle_id: "vehicle-1", plate_number: "AB123CD", current_custody: { id: "custody", holder_user_id: 7, holder_name: "Mario", taken_at: "07:15" } });
    render(<AssetDetail code="TEL/01" />);
    await screen.findByText("Bene del Consorzio · Disattivato");
    expect(mocks.byCode).toHaveBeenCalledWith("TEL/01");
    expect(screen.getByText("Dalle: Data non disponibile (ora italiana)")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Scheda Network" })).toHaveAttribute("href", "/network/devices/9");
    expect(screen.getByRole("link", { name: "Mezzo in Operazioni · AB123CD" })).toHaveAttribute("href", "/operazioni/mezzi/vehicle-1");
    expect(screen.getByText("Disattiva dotazione")).toBeDisabled();
  });
  test("hides custody, management and history without permission", async () => {
    mocks.lookups.mockResolvedValue({ ...lookups, permissions: ["dotazioni.view"] });
    render(<AssetDetail id="asset-1" />);
    await screen.findByText("TEL/01 · Telefono");
    expect(screen.queryByText("Prendi in consegna")).not.toBeInTheDocument();
    expect(screen.queryByText("Modifica dotazione")).not.toBeInTheDocument();
    expect(screen.queryByText("Storico custodie")).not.toBeInTheDocument();
  });
  test("fails closed without view permission", async () => {
    mocks.lookups.mockResolvedValue({ ...lookups, permissions: [] });
    render(<AssetDetail id="asset-1" />);
    await screen.findByText("Non sei autorizzato a consultare le dotazioni.");
  });
  test("reports lookup errors", async () => {
    mocks.asset.mockRejectedValue(new Error("Dotazione non trovata"));
    render(<AssetDetail id="missing" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Dotazione non trovata");
  });
});

describe("protected routes", () => {
  test.each([DotazioniPage, DotazionePage, DotazioneCodePage])("uses the Dotazioni authorization boundary", async (Page) => {
    render(<Page />);
    await screen.findByText("TEL/01 · Telefono");
    expect(screen.getByRole("main")).toHaveAttribute("data-module", "dotazioni");
    expect(screen.getByRole("main")).toHaveAttribute("data-section", "dotazioni.view");
  });
});
