import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ShiftWorkerBadge } from "@/components/presenze/shift-worker-badge";
import { ShiftWorkerControl } from "@/components/presenze/shift-worker-control";
import { assignPresenzeShiftWorker } from "@/lib/api/presenze-shift-workers";
import type { PresenzeDailyRecord } from "@/types/api";
const m = vi.hoisted(() => ({ token: vi.fn(), request: vi.fn() }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: m.token }));
vi.mock("@/lib/api/core", () => ({ request: m.request }));
const record = { id: "one", work_date: "2026-10-03", shift_worker_type: "none" } as PresenzeDailyRecord;
beforeEach(() => { vi.resetAllMocks(); m.token.mockReturnValue("token"); m.request.mockResolvedValue(record); });
afterEach(cleanup);
it("sends an encoded range assignment to GAIA", async () => {
 const data = { shift_worker_type: "acquaiolo" as const, date_from: "2026-10-01", date_to: "2026-10-31" };
 await assignPresenzeShiftWorker("token", "id/with space", data);
 expect(m.request).toHaveBeenCalledWith("/presenze/giornaliere/id%2Fwith%20space/turnista", { method: "POST", headers: { Authorization: "Bearer token" }, body: JSON.stringify(data) });
});
it("saves the full month and prevents duplicate submissions", async () => {
 let resolve!: (value: PresenzeDailyRecord) => void;
 m.request.mockReturnValue(new Promise<PresenzeDailyRecord>(r => { resolve = r; }));
 const saved = vi.fn(); render(<ShiftWorkerControl record={record} disabled={false} onSaved={saved} />);
 fireEvent.change(screen.getByLabelText("Tipologia turnista"), { target: { value: "telecontrollo" } });
 fireEvent.click(screen.getByText("Tutto il mese")); fireEvent.click(screen.getByText("Salva turnista")); fireEvent.click(screen.getByText("Salva turnista"));
 expect(m.request).toHaveBeenCalledOnce();
 expect(JSON.parse(m.request.mock.calls[0][1].body)).toEqual({ shift_worker_type: "telecontrollo", date_from: "2026-10-01", date_to: "2026-10-31" });
 expect(screen.getByRole("status")).toHaveTextContent("Salvataggio");
 await act(async () => resolve(record)); expect(saved).toHaveBeenCalledWith(record);
});
it("keeps GATE authoritative and disables viewers", () => {
 const view = render(<ShiftWorkerControl record={{ ...record, shift_worker_source: "gate" }} disabled={false} onSaved={vi.fn()} />);
 expect(screen.getByText(/gestita da GATE/)).toBeInTheDocument(); expect(screen.getByText("Salva turnista")).toBeDisabled();
 view.rerender(<ShiftWorkerControl record={record} disabled onSaved={vi.fn()} />); expect(screen.getByLabelText("Tipologia turnista")).toBeDisabled();
});
it("validates ordered same-month dates", () => {
 render(<ShiftWorkerControl record={record} disabled={false} onSaved={vi.fn()} />);
 fireEvent.change(screen.getByLabelText("Turnista dal"), { target: { value: "2026-10-10" } });
 fireEvent.click(screen.getByText("Salva turnista")); expect(screen.getByRole("alert")).toHaveTextContent("intervallo ordinato");
 fireEvent.change(screen.getByLabelText("Turnista al"), { target: { value: "2026-11-10" } });
 fireEvent.click(screen.getByText("Salva turnista")); expect(m.request).not.toHaveBeenCalled();
});
it("handles missing sessions and failures", async () => {
 m.token.mockReturnValue(null); render(<ShiftWorkerControl record={record} disabled={false} onSaved={vi.fn()} />);
 fireEvent.click(screen.getByText("Salva turnista")); expect(m.request).not.toHaveBeenCalled();
 m.token.mockReturnValue("token"); m.request.mockRejectedValue(new Error("Offline"));
 fireEvent.click(screen.getByText("Salva turnista")); expect(await screen.findByRole("alert")).toHaveTextContent("Offline");
 m.request.mockRejectedValue("fail"); fireEvent.click(screen.getByText("Salva turnista"));
 await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Assegnazione non salvata"));
});

it("shows a T badge with the selected type only on shift days", () => {
 const view = render(<ShiftWorkerBadge record={record} />); expect(screen.queryByText("T")).toBeNull();
 view.rerender(<ShiftWorkerBadge record={{...record, shift_worker_type: "acquaiolo"}} />); expect(screen.getByText("T")).toHaveAttribute("title", "Turnista acquaiolo");
 view.rerender(<ShiftWorkerBadge record={{...record, shift_worker_type: "telecontrollo"}} />); expect(screen.getByText("T")).toHaveAttribute("title", "Turnista telecontrollo");
 view.rerender(<ShiftWorkerBadge record={{...record, shift_worker_type: "tecnico_turnista"}} />); expect(screen.getByText("T")).toHaveAttribute("title", "Tecnico/Turnista");
});
it("defaults records from an older snapshot to non-turnista", () => {
 render(<ShiftWorkerControl record={{id: "old", work_date: "2026-10-03"} as PresenzeDailyRecord} disabled={false} onSaved={vi.fn()} />);
 expect(screen.getByLabelText("Tipologia turnista")).toHaveValue("none");
});
