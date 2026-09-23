import { act, fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/presenze/giornaliera-individuale/page";
import { MonthlySheetTable } from "@/app/presenze/giornaliera-individuale/table";
import { buildMonthlySheet } from "@/lib/presenze-monthly-sheet";
import { presenzeNavigationSections } from "@/components/layout/presenze-navigation";

const mocks = vi.hoisted(() => ({ people: vi.fn(), records: vi.fn(), token: vi.fn() }));
vi.mock("@/components/app/protected-page", () => ({ ProtectedPage: ({ children }: { children: React.ReactNode }) => <main>{children}</main> }));
vi.mock("@/lib/api", () => ({ listAllPresenzeCollaborators: mocks.people, listPresenzeDailyRecords: mocks.records }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
const person = { id: "one", name: "Persona prova", employee_code: "135", contract_kind: "operaio" };
const data = { total: 1, items: [{ work_date: "2026-08-03", ordinary_minutes: 420, effective_extra_minutes: 40 }] };
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (error: unknown) => void; const promise = new Promise<T>((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
afterEach(cleanup);
beforeEach(() => { vi.resetAllMocks(); mocks.token.mockReturnValue("token"); mocks.people.mockResolvedValue([person]); mocks.records.mockResolvedValue({ total: 0, items: [] }); });

describe("monthly page", () => {
  it("renders the navigation, month, employee, matrix, refresh and print", async () => {
    expect(presenzeNavigationSections[1].items.some(item => item.href === "/presenze/giornaliera-individuale")).toBe(true);
    const print = vi.spyOn(window, "print").mockImplementation(() => {});
    render(<Page />);
    await screen.findByRole("table");
    mocks.records.mockResolvedValue(data);
    fireEvent.change(screen.getByLabelText("Mese"), { target: { value: "2026-08" } });
    await screen.findAllByText("7:40");
    expect(mocks.records).toHaveBeenLastCalledWith("token", expect.objectContaining({ collaboratorId: "one", dateFrom: "2026-08-01", dateTo: "2026-08-31", includePunches: true }));
    fireEvent.click(screen.getByText("Stampa / PDF")); expect(print).toHaveBeenCalled();
    fireEvent.click(screen.getByText("Aggiorna")); await screen.findByRole("table");
    fireEvent.change(screen.getByLabelText("Dipendente"), { target: { value: "" } });
    await waitFor(() => expect(screen.queryByRole("table")).toBeNull());
    fireEvent.change(screen.getByLabelText("Mese"), { target: { value: "" } });
  });
  it("shows empty, unauthenticated, and directory failure states", async () => {
    mocks.token.mockReturnValue(null); const a = render(<Page />);
    expect(mocks.people).not.toHaveBeenCalled(); a.unmount();
    mocks.token.mockReturnValue("token"); mocks.people.mockResolvedValue([]);
    const b = render(<Page />); await waitFor(() => expect(mocks.people).toHaveBeenCalled());
    expect(screen.getByText("Nessun dipendente disponibile.")).toBeInTheDocument(); b.unmount();
    mocks.people.mockRejectedValue(new Error("offline")); render(<Page />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Impossibile caricare i dipendenti.");
  });
  it("rejects truncated results and presents both error forms", async () => {
    mocks.records.mockResolvedValue({ total: 10, items: [] }); const a = render(<Page />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Dati mensili incompleti"); a.unmount();
    mocks.records.mockRejectedValue("offline"); render(<Page />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Caricamento non riuscito");
  });
  it("ignores stale month responses, errors and directory completion after unmount", async () => {
    const pending = deferred<typeof data>(); mocks.records.mockReturnValueOnce(pending.promise);
    const a = render(<Page />); await waitFor(() => expect(mocks.records).toHaveBeenCalled());
    fireEvent.change(screen.getByLabelText("Mese"), { target: { value: "2026-08" } });
    await screen.findByRole("table"); await act(async () => pending.resolve(data)); a.unmount();
    const failed = deferred<typeof data>(); mocks.records.mockReturnValueOnce(failed.promise);
    const b = render(<Page />); await waitFor(() => expect(screen.getByRole("status")).toBeInTheDocument());
    b.unmount(); await act(async () => failed.reject(new Error("old")));
    for (const fail of [false, true]) {
      const directory = deferred<typeof person[]>(); mocks.people.mockReturnValueOnce(directory.promise);
      const c = render(<Page />); c.unmount();
      await act(async () => { if (fail) directory.reject("old"); else directory.resolve([person]); });
    }
  });
  it("renders present and missing dates, weekend shading and safe employee text", () => {
    render(<MonthlySheetTable report={buildMonthlySheet("2026-08", data.items)} name="<script>" code="135" />);
    expect(screen.getByRole("heading")).toHaveTextContent("<script>");
    expect(screen.getAllByTitle("2026-08-01 · Dati non disponibili")[0]).toHaveClass("bg-slate-200");
    expect(screen.getAllByTitle("2026-08-03")[0]).toHaveTextContent("7:00");
  });
});
