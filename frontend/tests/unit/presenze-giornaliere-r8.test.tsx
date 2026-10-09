import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import PresenzeGiornalierePage from "@/app/presenze/giornaliere/page";
import type { PresenzeDailyRecord } from "@/types/api";

const api = vi.hoisted(() => ({
  getCurrentUser: vi.fn(), getPresenzeAccessContext: vi.fn(),
  listAllPresenzeCollaborators: vi.fn(), listPresenzeDailyMatrixRecords: vi.fn(),
  getPresenzeDailyRecord: vi.fn(), getStoredAccessToken: vi.fn(),
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: api.getStoredAccessToken }));
vi.mock("@/lib/api", () => ({
  ...api, ApiError: class ApiError extends Error {}, getPresenzeSyncJob: vi.fn(),
  updatePresenzeDailyRecord: vi.fn(), refreshPresenzeDailyRecordFromInaz: vi.fn(),
  updatePresenzeCollaboratorContractProfile: vi.fn(),
}));
vi.mock("@/components/app/protected-page", () => ({ ProtectedPage: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
vi.mock("@/components/ui/badge", () => ({ Badge: ({ children, variant }: { children: React.ReactNode; variant: string }) => <span data-variant={variant}>{children}</span> }));
vi.mock("@/components/presenze/inaz-sync-control", () => ({ InazSyncControl: () => null }));
vi.mock("@/components/presenze/whatsapp-reminder-alert", () => ({ WhatsAppReminderAlert: () => null }));
vi.mock("@/components/presenze/shift-worker-badge", () => ({ ShiftWorkerBadge: () => null }));

function record(overrides: Partial<PresenzeDailyRecord> = {}): PresenzeDailyRecord {
  return {
    id: "r8-record", collaborator_id: "r8-person", work_date: "2026-05-18", owner_user_id: 77,
    operational_status: "ok", operational_missing_minutes: 0,
    operational_expected_minutes: 420, operational_worked_minutes: 420,
    operational_mpe_minutes: 0, operational_formula_code: null, operational_notes: [],
    ordinary_minutes: 420, teo_minutes: 390, absence_minutes: 0, justified_minutes: 0,
    effective_extra_minutes: 0, effective_straordinario_minutes: 0, effective_mpe_minutes: 0,
    straordinario_minutes: 0, mpe_minutes: 0, km_value: null, trasferta_minutes: null,
    trasferta_montano: false, reperibilita_unit: "none", reperibilita_quantity: null,
    detail_requests: [], detail_anomalies: [], detail_punch_rows: [], punches: [],
    detail_day_summary: {}, detail_day_totals: {}, raw_payload_json: {},
    request_description: null, request_status: null, request_authorized_by: null,
    resolved_absence_cause: null, validation_status: "pending",
    detail_status: "Regolare", stato: "Regolare", special_day: false,
    ...overrides,
  } as PresenzeDailyRecord;
}

let token = 0;
beforeEach(() => {
  vi.clearAllMocks();
  api.getStoredAccessToken.mockReturnValue(`r8-token-${++token}`);
  api.getCurrentUser.mockResolvedValue({ id: 12, role: "viewer" });
  api.getPresenzeAccessContext.mockResolvedValue({ can_view_all_data: true, is_supervisor: false });
  api.listAllPresenzeCollaborators.mockResolvedValue([{
    id: "r8-person", name: "R8 COLLABORATORE", employee_code: "R8", is_active: true,
  }]);
});

async function matrix(item: PresenzeDailyRecord): Promise<HTMLButtonElement> {
  api.listPresenzeDailyMatrixRecords.mockResolvedValue({ items: [item], total: 1, page: 1, page_size: 5000 });
  api.getPresenzeDailyRecord.mockResolvedValue(item);
  render(<PresenzeGiornalierePage />);
  fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
  const heading = await screen.findByRole("button", { name: "R8 COLLABORATORE", exact: true });
  return within(heading.closest("tr")!).getAllByRole("button")[1] as HTMLButtonElement;
}

describe("R8 original daily-record label policy", () => {
  test.each([
    ["ordered status perm", { operational_status: "blocking", detail_status: " RICH MALATT ANOM FER PERM " }, "Perm", " "],
    ["ordered status fer", { operational_status: "blocking", detail_status: "rich malatt anom fer" }, "Fer", " "],
    ["ordered status anomaly", { operational_status: "blocking", detail_status: "rich malatt anom" }, "Anom", " "],
    ["ordered status sickness", { operational_status: "blocking", detail_status: "rich malatt" }, "Mal", " "],
    ["ordered status request", { operational_status: "blocking", detail_status: "Richiesta" }, "Rich", " "],
    ["short status", { operational_status: "blocking", detail_status: " XYZ " }, "xyz", " "],
    ["long status", { operational_status: "blocking", detail_status: " ABCDEF " }, "abcd", " "],
    ["empty detail suppresses stato", { operational_status: "blocking", detail_status: "", stato: "Permesso" }, "Anom", " "],
    ["null detail uses stato", { operational_status: "blocking", detail_status: null, stato: "Permesso" }, "Perm", " "],
    ["absence ignored generic status", { ordinary_minutes: 0, absence_minutes: 90, detail_status: "Giornata regolare" }, "1.5", "1.5h"],
    ["absence uses zero, not justified fallback", { resolved_absence_cause: "ferie", absence_minutes: 0, justified_minutes: 60 }, "Fer", " "],
    ["analysis known cause beats request", { operational_status: "in_analysis", resolved_absence_cause: "permesso", request_description: "Ferie" }, "Perm", " "],
    ["analysis unknown cause no request", { operational_status: "in_analysis", resolved_absence_cause: "constructor" }, "Anom", " "],
    ["analysis inherited cause no request", { operational_status: "in_analysis", resolved_absence_cause: "__proto__" }, "Anom", " "],
    ["analysis inherited string no request", { operational_status: "in_analysis", resolved_absence_cause: "toString" }, "Anom", " "],
    ["analysis unknown cause request", { operational_status: "in_analysis", resolved_absence_cause: "custom", request_description: " " }, "Rich", " "],
    ["analysis missing beats absence and request", { operational_status: "in_analysis", operational_missing_minutes: 60, absence_minutes: 120, detail_requests: [{}] }, "Rich", "-1h"],
    ["analysis absence beats request", { operational_status: "in_analysis", operational_missing_minutes: NaN, absence_minutes: 120, detail_requests: [{}] }, "Rich", "2h"],
    ["analysis request fallback", { operational_status: "in_analysis", operational_missing_minutes: -1, detail_requests: [{}] }, "Rich", "Rich."],
    ["analysis NaN absence no request", { operational_status: "in_analysis", absence_minutes: NaN }, "Anom", " "],
    ["unworked holiday suppresses extras", { special_day: true, ordinary_minutes: 0, operational_worked_minutes: 0, effective_extra_minutes: 60, trasferta_minutes: 30, km_value: 20, detail_requests: [{}] }, "Fest", " "],
    ["holiday worked by punch uses theoretical fallback", { special_day: true, ordinary_minutes: 0, operational_worked_minutes: 0, punches: [{ exit_time: "12:00" }] }, "6.5", " "],
    ["worked NaN effective ordinary uses theo", { operational_formula_code: "R8", operational_worked_minutes: NaN }, "6.5", " "],
    ["worked zero effective ordinary uses theo", { operational_formula_code: "R8", operational_worked_minutes: 0 }, "6.5", " "],
    ["worked negative ordinary remains negative", { operational_formula_code: "R8", operational_worked_minutes: -60 }, "-1", " "],
    ["authorization beats operational supplements", { request_status: "ACC", request_description: "E", effective_extra_minutes: 60, trasferta_minutes: 30, km_value: 20, detail_requests: [{}] }, "7", "Valid."],
    ["extra beats travel km request", { effective_extra_minutes: 60, trasferta_minutes: 30, km_value: 20, detail_requests: [{}] }, "7", "+1h"],
    ["null extra reads raw effective sums", { effective_extra_minutes: null, effective_straordinario_minutes: 30, effective_mpe_minutes: 30 }, "7", "+1h"],
    ["zero extra retains override and travel precedence", { effective_extra_minutes: 0, straordinario_minutes: 120, trasferta_minutes: 30, km_value: 20, detail_requests: [{}] }, "7", "T 0.5h"],
    ["NaN extra falls through to km", { effective_extra_minutes: NaN, km_value: 20, detail_requests: [{}] }, "7", "KM 20"],
    ["negative extra and zero km fall through to request", { effective_extra_minutes: -60, km_value: 0, detail_requests: [{}] }, "7", "Rich."],
    ["description alone does not become worked secondary", { request_description: "Richiesta" }, "7", " "],
  ] as Array<[string, Partial<PresenzeDailyRecord>, string, string]>)("retains %s", async (_label, overrides, primary, secondary) => {
    const cell = await matrix(record(overrides));
    expect(cell.children[0].textContent).toBe(primary);
    expect(cell.children[1].textContent).toBe(secondary);
    expect(cell.title).toMatch(/^2026-05-18 · /);
  });

  test.each([
    ["regolare overrides blocking", { operational_status: "blocking", detail_status: " GIORNATA REGOLARE " }, "success"],
    ["empty detail suppresses regolare stato", { operational_status: "blocking", detail_status: "", stato: "Regolare" }, "danger"],
    ["absence is neutral", { ordinary_minutes: 0, absence_minutes: 60, detail_status: "Assenza" }, "neutral"],
    ["unknown status and resting record", { ordinary_minutes: 0, detail_status: "constructor", operational_status: "unknown" }, "neutral"],
    ["special is warning", { special_day: true, detail_status: "Festivita" }, "warning"],
  ] as Array<[string, Partial<PresenzeDailyRecord>, string]>)("preserves detail badge %s", async (_label, overrides, variant) => {
    const item = record(overrides);
    fireEvent.click(await matrix(item));
    const detail = (await screen.findByText("Rettifiche operative")).closest(".fixed") as HTMLElement;
    const status = detail.querySelector("[data-variant]");
    expect(status?.textContent).toBe(item.detail_status ?? item.stato ?? "n/d");
    expect(status).toHaveAttribute("data-variant", variant);
  });

  test.each([
    ["blocking", "Da sistemare", "danger"],
    ["in_analysis", "In analisi", "warning"],
    ["ok", "Quadrata", "success"],
    ["unknown", "Quadrata", "success"],
    ["constructor", "Quadrata", "success"],
    ["__proto__", "Quadrata", "success"],
    ["toString", "Quadrata", "success"],
  ])("preserves formula vocabulary for %s", async (status, label, variant) => {
    fireEvent.click(await matrix(record({ operational_formula_code: "R8-FORMULA", operational_status: status as PresenzeDailyRecord["operational_status"] })));
    const detail = (await screen.findByText("Rettifiche operative")).closest(".fixed") as HTMLElement;
    const formula = within(detail).getByText("Formula GAIA").closest("div.rounded-xl") as HTMLElement;
    expect(within(formula).getByText(label, { exact: true })).toHaveAttribute("data-variant", variant);
  });
});
