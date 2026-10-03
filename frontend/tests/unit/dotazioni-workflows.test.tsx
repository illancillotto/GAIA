import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { CustodyActions } from "@/features/dotazioni/CustodyActions";
import { CustodyHistory, custodyDuration } from "@/features/dotazioni/CustodyHistory";
import { OperatorAssets } from "@/features/dotazioni/OperatorAssets";
import type { Asset, Custody } from "@/features/dotazioni/types";

const mocks = vi.hoisted(() => ({ custody: vi.fn(), history: vi.fn(), operatorAssets: vi.fn() }));
vi.mock("@/features/dotazioni/api", () => ({ dotazioniApi: mocks }));
const custody: Custody = { id: "custody", holder_user_id: 7, holder_name: "Mario Rossi", taken_at: "2026-10-01T07:15:00Z", returned_at: null, handover_from_user_id: null, notes: null, return_notes: null };
const asset = { id: "asset", asset_code: "TEL-01", asset_type: "phone", name: "Telefono", status: "available", effective_status: "available", is_active: true, vehicle_id: null, current_custody: null } as Asset;
const operators = [{ id: 7, name: "Mario" }, { id: 8, name: "Antonio" }];

beforeEach(() => {
  vi.clearAllMocks();
  mocks.custody.mockResolvedValue(asset);
  mocks.history.mockResolvedValue({ items: [], total: 0 });
  mocks.operatorAssets.mockResolvedValue({ items: [asset], total: 1 });
});

describe("physical custody operations", () => {
  test("takes for self or selected operator and preserves notes", async () => {
    const changed = vi.fn();
    render(<CustodyActions asset={asset} operators={operators} onChange={changed} />);
    fireEvent.click(screen.getByText("Prendi in consegna"));
    await waitFor(() => expect(changed).toHaveBeenCalledOnce());
    expect(mocks.custody).toHaveBeenLastCalledWith("asset", "take", { notes: "" });
    fireEvent.change(screen.getByLabelText("Operatore destinatario"), { target: { value: "8" } });
    fireEvent.change(screen.getByLabelText("Note"), { target: { value: "Consegna turno" } });
    fireEvent.click(screen.getByText("Prendi in consegna"));
    await waitFor(() => expect(mocks.custody).toHaveBeenLastCalledWith("asset", "take", { holder_user_id: 8, notes: "Consegna turno" }));
  });
  test("prevents transferring to self and returns without a destination", async () => {
    render(<CustodyActions asset={{ ...asset, current_custody: custody }} operators={operators} onChange={vi.fn()} />);
    expect(screen.getByText("Passa a…")).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Operatore destinatario"), { target: { value: "7" } });
    expect(screen.getByText("Passa a…")).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Operatore destinatario"), { target: { value: "8" } });
    fireEvent.click(screen.getByText("Passa a…"));
    await waitFor(() => expect(mocks.custody).toHaveBeenCalledWith("asset", "transfer", { holder_user_id: 8, notes: "" }));
    await waitFor(() => expect(screen.getByText("Restituisci")).toBeEnabled());
    fireEvent.click(screen.getByText("Restituisci"));
    await waitFor(() => expect(mocks.custody).toHaveBeenCalledWith("asset", "return", { notes: "" }));
  });
  test("reports backend conflicts", async () => {
    mocks.custody.mockRejectedValue(new Error("Asset già in custodia"));
    render(<CustodyActions asset={asset} operators={operators} onChange={vi.fn()} />);
    fireEvent.click(screen.getByText("Prendi in consegna"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Asset già in custodia");
  });
  test.each([{ ...asset, is_active: false }, { ...asset, status: "maintenance" }])("does not offer taking unavailable assets", (unavailable) => {
    render(<CustodyActions asset={unavailable} operators={operators} onChange={vi.fn()} />);
    expect(screen.getByText("Prendi in consegna")).toBeDisabled();
  });
  test("leaves vehicle operations in Operazioni", () => {
    render(<CustodyActions asset={{ ...asset, vehicle_id: "vehicle" }} operators={operators} onChange={vi.fn()} />);
    expect(screen.getByText(/non viene aperta una custodia parallela/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});

describe("custody history", () => {
  test("formats active and completed durations", () => {
    expect(custodyDuration(custody.taken_at, null)).toBe("In corso");
    expect(custodyDuration(custody.taken_at, "2026-10-01T14:10:00Z")).toBe("6h 55m");
    expect(custodyDuration(custody.taken_at, "2026-10-01T07:00:00Z")).toBe("0h 0m");
  });
  test("renders history and navigates paginated results", async () => {
    mocks.history.mockResolvedValue({ items: [custody, { ...custody, id: "closed", holder_name: "Antonio", returned_at: "2026-10-01T14:10:00Z", handover_from_user_id: 8, handover_from_name: "Mario", notes: "Cambio", return_notes: "Rientro" }], total: 26 });
    render(<CustodyHistory id="asset" revision={0} />);
    expect(screen.getByText("Caricamento storico…")).toBeInTheDocument();
    await screen.findByText("Mario Rossi");
    expect(screen.getByText("6h 55m")).toBeInTheDocument();
    expect(screen.getByText("Cambio")).toBeInTheDocument();
    expect(screen.getByText("Rientro")).toBeInTheDocument();
    expect(screen.getByText("Mario")).toBeInTheDocument();
    expect(screen.queryByText("8")).not.toBeInTheDocument();
    expect(screen.getAllByText("01/10/2026, 09:15")).toHaveLength(2);
    fireEvent.click(screen.getByText("Successiva"));
    await waitFor(() => expect(mocks.history).toHaveBeenLastCalledWith("asset", 2));
    await screen.findByText("26 custodie · pagina 2");
    fireEvent.click(screen.getByText("Precedente"));
    await waitFor(() => expect(mocks.history).toHaveBeenLastCalledWith("asset", 1));
  });
  test("reports inaccessible history", async () => {
    mocks.history.mockRejectedValue(new Error("Storico negato"));
    render(<CustodyHistory id="asset" revision={0} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Storico negato");
  });
  test("explains empty history", async () => {
    render(<CustodyHistory id="asset" revision={0} />);
    expect(await screen.findByText("Nessuna custodia registrata.")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Storico custodie" })).toHaveAttribute("tabindex", "0");
  });
});

describe("operator custody integration", () => {
  test("fails closed when canonical identity is missing", async () => {
    render(<OperatorAssets userId={null} />);
    expect(screen.getByText(/Identità GAIA non collegata/)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Caricamento dotazioni…")).not.toBeInTheDocument());
    expect(mocks.operatorAssets).not.toHaveBeenCalled();
  });
  test("loads custody only from canonical GAIA identity", async () => {
    render(<OperatorAssets userId={7} />);
    await screen.findByText("TEL-01 · Telefono");
    expect(mocks.operatorAssets).toHaveBeenCalledWith(7);
    expect(screen.getByText("1 dotazioni")).toBeInTheDocument();
  });
  test("reports API permission failures", async () => {
    mocks.operatorAssets.mockRejectedValue(new Error("Dotazioni negate"));
    render(<OperatorAssets userId={7} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Dotazioni negate");
  });
});
