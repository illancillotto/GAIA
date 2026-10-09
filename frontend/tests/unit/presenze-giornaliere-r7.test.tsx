import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import PresenzeGiornalierePage from "@/app/presenze/giornaliere/page";
import type { PresenzeDailyRecord } from "@/types/api";
import { anomalyPanelComparisons, anomalyPanelCounts, buildAnomalyDayGroups, buildAnomalyCollaboratorGroups } from "@/app/presenze/giornaliere/anomaly-panel-model";
import type { MonthAnomalyRecord } from "@/app/presenze/giornaliere/anomaly-panel-model";

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
vi.mock("@/components/presenze/inaz-sync-control", () => ({ InazSyncControl: () => null }));
vi.mock("@/components/presenze/whatsapp-reminder-alert", () => ({ WhatsAppReminderAlert: () => null }));
vi.mock("@/components/presenze/shift-worker-badge", () => ({ ShiftWorkerBadge: () => null }));

function record(id: string, collaboratorId: string, day: string, status = "blocking", missing = 0): PresenzeDailyRecord {
  return {
    id, collaborator_id: collaboratorId, work_date: `2026-05-${day}`, owner_user_id: 77,
    operational_status: status, operational_missing_minutes: missing,
    operational_expected_minutes: 420, operational_worked_minutes: 420,
    operational_mpe_minutes: 0, operational_formula_code: null, operational_notes: [id],
    ordinary_minutes: 420, teo_minutes: 420, absence_minutes: 0, justified_minutes: 0,
    effective_extra_minutes: 0, effective_straordinario_minutes: 0, effective_mpe_minutes: 0,
    straordinario_minutes: 0, mpe_minutes: 0, km_value: null, trasferta_minutes: null,
    trasferta_montano: false, reperibilita_unit: "none", reperibilita_quantity: null,
    detail_requests: [], detail_anomalies: [], detail_punch_rows: [], punches: [],
    detail_day_summary: {}, detail_day_totals: {}, raw_payload_json: {},
    request_description: null, request_status: null, resolved_absence_cause: null,
    validation_status: "pending", detail_status: "Regolare", stato: "Regolare", special_day: false,
  } as PresenzeDailyRecord;
}

let token = 0;
beforeEach(() => {
  vi.clearAllMocks();
  api.getStoredAccessToken.mockReturnValue(`r7-${++token}`);
  api.getCurrentUser.mockResolvedValue({ id: 12, role: "viewer" });
  api.getPresenzeAccessContext.mockResolvedValue({ can_view_all_data: true, is_supervisor: false });
  api.listAllPresenzeCollaborators.mockResolvedValue([
    { id: "alpha", name: "ALPHA", is_active: true },
    { id: "zulu", name: "ZULU", is_active: true },
    { id: "empty", name: "", is_active: true },
  ]);
  api.getPresenzeDailyRecord.mockImplementation((_token: string, id: string) => Promise.resolve(record(id, "alpha", "18")));
});

async function panel(records: PresenzeDailyRecord[]) {
  api.listPresenzeDailyMatrixRecords.mockResolvedValue({ items: records, total: records.length, page: 1, page_size: 5000 });
  render(<PresenzeGiornalierePage />);
  fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
  fireEvent.click(await screen.findByRole("button", { name: `Vedi anomalie mese (${records.length})` }));
  return screen.getByText("Anomalie del mese").closest("div.rounded-3xl") as HTMLElement;
}

function sections(element: HTMLElement) {
  return Array.from(element.querySelectorAll("section"));
}

function reasons(element: HTMLElement) {
  return within(element).getAllByRole("button").filter((button) => button.textContent?.includes("Apri"))
    .map((button) => button.querySelector("p.mt-3")?.textContent);
}

describe("R7 original anomaly-panel characterization", () => {
  test("keeps collaborator anomaly-count then total then label order and filters", async () => {
    const root = await panel([
      record("zulu-first", "zulu", "19"), record("alpha-analysis", "alpha", "19", "in_analysis"),
      record("alpha-first", "alpha", "18"), record("zulu-analysis", "zulu", "18", "in_analysis"),
      record("empty-first", "empty", "18"), record("missing-first", "missing", "18"),
    ]);
    fireEvent.click(within(root).getByRole("button", { name: "Collaboratore", exact: true }));
    expect(sections(root).map((group) => group.querySelector("p")?.textContent)).toEqual(["ALPHA", "ZULU", "", "missing"]);
    expect(sections(root).map(reasons)).toEqual([["alpha-first", "alpha-analysis"], ["zulu-first", "zulu-analysis"], ["empty-first"], ["missing-first"]]);
    expect(within(root).getByRole("button", { name: "Correggere subito (4)" })).toBeInTheDocument();
    expect(within(root).getByRole("button", { name: "Da verificare (2)" })).toBeInTheDocument();
    fireEvent.click(within(root).getByRole("button", { name: "Da verificare (2)" }));
    expect(sections(root).map(reasons)).toEqual([["alpha-analysis"], ["zulu-analysis"]]);
    fireEvent.click(within(root).getByRole("button", { name: "Apri la prima giornata critica" }));
    await waitFor(() => expect(api.getPresenzeDailyRecord).toHaveBeenCalledWith(expect.any(String), "zulu-analysis"));
  });

  test("keeps day order independent of priority and priority then empty/missing names inside each day", async () => {
    const root = await panel([
      record("later-large", "alpha", "19", "blocking", 200),
      record("zulu", "zulu", "18"), record("missing", "missing", "18"),
      record("empty", "empty", "18"), record("alpha", "alpha", "18"),
      record("day-analysis", "alpha", "18", "in_analysis"),
    ]);
    fireEvent.click(within(root).getByRole("button", { name: "Giorno", exact: true }));
    expect(sections(root).map((group) => group.querySelector("p")?.textContent)).toEqual(["2026-05-18 · lunedì", "2026-05-19 · martedì"]);
    expect(sections(root).map(reasons)).toEqual([["missing", "empty", "alpha", "zulu", "day-analysis"], ["later-large"]]);
    expect(within(sections(root)[0]).getByText("4 bloccanti")).toBeInTheDocument();
    expect(within(sections(root)[0]).getByText("1 da verificare")).toBeInTheDocument();
    fireEvent.click(within(root).getByRole("button", { name: "Apri la prima giornata critica" }));
    await waitFor(() => expect(api.getPresenzeDailyRecord).toHaveBeenCalledWith(expect.any(String), "later-large"));
  });

  test.each([NaN, undefined])("retains stable source order when missing minutes is %s", async (missing) => {
    const first = record("nan-zulu", "zulu", "18");
    first.operational_missing_minutes = missing as number;
    const second = record("nan-alpha", "alpha", "18");
    second.operational_missing_minutes = missing as number;
    const root = await panel([first, second]);
    fireEvent.click(within(root).getByRole("button", { name: "Giorno", exact: true }));
    expect(reasons(sections(root)[0])).toEqual(["nan-zulu", "nan-alpha"]);
    fireEvent.click(within(root).getByRole("button", { name: "Apri la prima giornata critica" }));
    await waitFor(() => expect(api.getPresenzeDailyRecord).toHaveBeenCalledWith(expect.any(String), "nan-zulu"));
  });
});

describe("R7 anomaly-panel pure model", () => {
  function item(id: string, collaboratorId = "alpha", day = "18", kind: MonthAnomalyRecord["kind"] = "anomaly", missing = 0): MonthAnomalyRecord {
    return { record: record(id, collaboratorId, day, kind === "anomaly" ? "blocking" : "in_analysis", missing), kind, reason: id };
  }

  test("keeps empty collections empty and does not invent counts", () => {
    expect(buildAnomalyDayGroups([], new Map())).toEqual([]);
    expect(buildAnomalyCollaboratorGroups([], new Map())).toEqual([]);
    expect(anomalyPanelCounts([])).toEqual({ anomaly: 0, analysis: 0 });
    expect(anomalyPanelCounts([{ ...item("unknown"), kind: "other" } as unknown as MonthAnomalyRecord])).toEqual({ anomaly: 0, analysis: 0 });
  });

  test("retains duplicate identities and stable tie order without mutating frozen inputs", () => {
    const first = Object.freeze(item("first"));
    const second = Object.freeze(item("second"));
    Object.freeze(first.record);
    Object.freeze(second.record);
    const source = Object.freeze([first, second, first, item("analysis", "alpha", "17", "analysis")]);
    const days = buildAnomalyDayGroups(source, new Map());
    expect(days.map(({ iso }) => iso)).toEqual(["2026-05-17", "2026-05-18"]);
    expect(days[1]).toMatchObject({ anomalyCount: 3, analysisCount: 0 });
    expect(days[1].items).toEqual([first, second, first]);
    expect(days[1].items[0]).toBe(first);
    expect(days[1].items[2]).toBe(first);
    const groups = buildAnomalyCollaboratorGroups(source, new Map());
    expect(groups[0]).toMatchObject({ collaboratorId: "alpha", collaboratorName: "alpha", anomalyCount: 3, analysisCount: 1 });
    expect(groups[0].items).toEqual([first, second, first, source[3]]);
    expect(source).toEqual([first, second, first, source[3]]);
    expect(days[1].items).not.toBe(source);
    expect(groups[0].items).not.toBe(days[1].items);
  });

  test.each([NaN, undefined, Infinity, -Infinity])("priority %s returns NaN without consulting downstream names or dates", (missing) => {
    const first = item("first", "zulu");
    const second = item("second", "alpha");
    first.record.operational_missing_minutes = missing as number;
    second.record.operational_missing_minutes = missing as number;
    const collaborators = new Map();
    const lookup = vi.spyOn(collaborators, "get");
    const comparisons = anomalyPanelComparisons(collaborators);
    expect(comparisons.month(first, second)).toBeNaN();
    expect(comparisons.day(first, second)).toBeNaN();
    expect(comparisons.collaborator(first, second)).toBeNaN();
    expect(lookup).not.toHaveBeenCalled();
  });

  test("preserves finite priority, date then name and null arithmetic rather than truthy fallback", () => {
    const comparisons = anomalyPanelComparisons(new Map());
    const first = item("first", "missing", "19");
    const second = item("second", "absent", "18");
    first.record.operational_missing_minutes = null as unknown as number;
    expect(comparisons.month(first, second)).toBeGreaterThan(0);
    expect(comparisons.day(first, second)).toBe(0);
    expect(comparisons.collaborator(first, second)).toBeGreaterThan(0);
    second.record.operational_missing_minutes = 2;
    expect(comparisons.month(first, second)).toBe(2);
    expect(comparisons.day(first, second)).toBe(2);
    expect(comparisons.collaborator(first, second)).toBe(2);
  });
});
