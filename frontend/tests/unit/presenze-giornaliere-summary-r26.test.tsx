import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import PresenzeGiornalierePage from "@/app/presenze/giornaliere/page";
import type { PresenzeDailyRecord } from "@/types/api";

const api = vi.hoisted(() => ({
  getCurrentUser: vi.fn(), getPresenzeAccessContext: vi.fn(),
  listAllPresenzeCollaborators: vi.fn(), listPresenzeDailyMatrixRecords: vi.fn(),
  getPresenzeDailyRecord: vi.fn(), getStoredAccessToken: vi.fn(), updatePresenzeDailyRecord: vi.fn(),
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: api.getStoredAccessToken }));
vi.mock("@/lib/api", () => ({
  ...api, ApiError: class ApiError extends Error {}, getPresenzeSyncJob: vi.fn(),
  refreshPresenzeDailyRecordFromInaz: vi.fn(), updatePresenzeCollaboratorContractProfile: vi.fn(),
}));
vi.mock("@/components/app/protected-page", () => ({ ProtectedPage: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
vi.mock("@/components/presenze/inaz-sync-control", () => ({ InazSyncControl: () => null }));
vi.mock("@/components/presenze/whatsapp-reminder-alert", () => ({ WhatsAppReminderAlert: () => null }));
vi.mock("@/components/presenze/shift-worker-badge", () => ({ ShiftWorkerBadge: () => null }));
vi.mock("@/components/presenze/daily-operational-controls", () => ({ DailyOperationalControls: () => null }));

function record(overrides: Partial<PresenzeDailyRecord> = {}): PresenzeDailyRecord {
  return {
    id: "r26-first", collaborator_id: "r26-person", work_date: "2026-05-18", owner_user_id: 12,
    operational_status: "ok", operational_missing_minutes: 0,
    operational_expected_minutes: 420, operational_worked_minutes: 420,
    operational_mpe_minutes: 0, operational_formula_code: null, operational_notes: [],
    ordinary_minutes: 420, teo_minutes: 390, absence_minutes: 0, justified_minutes: 0,
    effective_extra_minutes: 0, effective_straordinario_minutes: 0, effective_mpe_minutes: 0,
    straordinario_minutes: 0, mpe_minutes: 0, km_value: 2, trasferta_minutes: null,
    trasferta_montano: false, reperibilita_unit: "none", reperibilita_quantity: null,
    override_straordinario_minutes: null, override_mpe_minutes: null, manual_note: null,
    detail_requests: [], detail_anomalies: [], detail_punch_rows: [], punches: [],
    detail_day_summary: {}, detail_day_totals: {}, raw_payload_json: {},
    request_description: null, request_status: null, request_authorized_by: null,
    resolved_absence_cause: null, validation_status: "pending", validation_note: null,
    detail_status: "Regolare", stato: "Regolare", special_day: false,
    ...overrides,
  } as PresenzeDailyRecord;
}

type ExpectedRow = {
  label: string;
  value: string;
  kind: "extra" | "saturday" | "absence";
  labelTone: string;
  valueTone: string;
};

const extra: ExpectedRow = { label: "Extra", value: "1.5h", kind: "extra", labelTone: "text-emerald-700", valueTone: "text-emerald-800" };
const saturday: ExpectedRow = { label: "Sabati mese", value: "3° lav", kind: "saturday", labelTone: "text-violet-700", valueTone: "text-violet-800" };
const permesso: ExpectedRow = { label: "Permesso", value: "1h", kind: "absence", labelTone: "text-sky-700", valueTone: "text-sky-800" };

let tokenSeed = 0;
beforeEach(() => {
  vi.resetAllMocks();
  api.getStoredAccessToken.mockReturnValue(`r26-token-${++tokenSeed}`);
  api.getCurrentUser.mockResolvedValue({ id: 12, role: "viewer" });
  api.getPresenzeAccessContext.mockResolvedValue({ can_view_all_data: true, is_supervisor: false });
  api.listAllPresenzeCollaborators.mockResolvedValue([{
    id: "r26-person", name: "R26 COLLABORATORE", employee_code: "R26", is_active: true,
  }]);
});

async function workspace(items: PresenzeDailyRecord[]) {
  api.listPresenzeDailyMatrixRecords.mockResolvedValue({ items, total: items.length, page: 1, page_size: 5000 });
  api.getPresenzeDailyRecord.mockImplementation((_token: string, id: string) => Promise.resolve(items.find((item) => item.id === id)));
  render(<PresenzeGiornalierePage />);
  fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
  await screen.findByRole("button", { name: "R26 COLLABORATORE" });
}

function heading() {
  return screen.getByRole("button", { name: "R26 COLLABORATORE" });
}

function assertGridSummary(rows: ExpectedRow[]) {
  const cell = heading().closest("th")!;
  const wrapper = cell.querySelector("div.overflow-hidden.rounded-lg");
  if (rows.length === 0) {
    expect(wrapper).toBeNull();
    return;
  }
  expect(wrapper).toHaveAttribute("class", "mt-2 overflow-hidden rounded-lg border border-slate-200 bg-white/80 text-[10px]");
  const grid = wrapper!.children[0];
  expect(grid).toHaveAttribute("class", "grid grid-cols-[minmax(0,1fr)_5.75rem]");
  const cells = Array.from(grid.children).flatMap((child) => child.classList.contains("contents") ? Array.from(child.children) : [child]);
  expect(cells.map((child) => child.textContent)).toEqual(rows.flatMap((row) => [row.label, row.value]));
  for (const [index, row] of rows.entries()) {
    const label = cells[index * 2];
    const value = cells[index * 2 + 1];
    if (row.kind === "extra") {
      expect(label).toHaveAttribute("class", "border-b border-slate-100 px-2 py-1.5 font-medium text-emerald-700");
      expect(value).toHaveAttribute("class", "border-b border-l border-slate-100 px-2 py-1.5 text-right font-semibold text-emerald-700");
    } else {
      const border = row.kind === "saturday"
        ? rows.some((entry) => entry.kind === "extra" || entry.kind === "absence")
        : index < rows.length - 1;
      const prefix = border ? "border-b border-slate-100" : "";
      expect(label).toHaveAttribute("class", `${prefix} px-2 py-1.5 font-medium ${row.labelTone}`);
      expect(value).toHaveAttribute("class", `${prefix} border-l border-slate-100 px-2 py-1.5 text-right font-semibold ${row.valueTone}`);
      if (row.kind === "absence") expect(label.parentElement).toHaveAttribute("class", "contents");
    }
  }
}

function assertModalSummary(rows: ExpectedRow[]) {
  const title = screen.queryByText("Riepilogo operativo mese");
  if (rows.length === 0) {
    expect(title).not.toBeInTheDocument();
    return;
  }
  expect(title).toHaveAttribute("class", "mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400");
  expect(title!.parentElement).toHaveAttribute("class", "border-t border-gray-100 px-6 py-4");
  const grid = title!.nextElementSibling!;
  expect(grid).toHaveAttribute("class", "grid gap-2 sm:grid-cols-2 lg:grid-cols-3");
  const cards = Array.from(grid.children);
  expect(cards).toHaveLength(rows.length);
  expect(cards.map((card) => Array.from(card.children).map((child) => child.textContent))).toEqual(rows.map((row) => [row.label, row.value]));
  for (const [index, row] of rows.entries()) {
    const card = cards[index];
    const wrapperClasses = {
      extra: "flex items-center justify-between rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs",
      saturday: "flex items-center justify-between gap-3 rounded-xl border border-violet-100 bg-violet-50 px-3 py-2 text-xs",
      absence: "flex items-center justify-between rounded-xl border border-slate-100 bg-white px-3 py-2 text-xs shadow-sm",
    };
    expect(card).toHaveAttribute("class", wrapperClasses[row.kind]);
    expect(card.children[0]).toHaveAttribute("class", `font-medium ${row.labelTone}`);
    expect(card.children[1]).toHaveAttribute("class", `${row.kind === "saturday" ? "text-right " : ""}font-semibold ${row.valueTone}`);
  }
}

async function assertBothSummaries(rows: ExpectedRow[]) {
  assertGridSummary(rows);
  fireEvent.click(heading());
  await screen.findByRole("button", { name: "Chiudi ✕" });
  assertModalSummary(rows);
}

describe("R26 original monthly operational summary presentation", () => {
  test.each([
    ["none", false, false, false],
    ["extra only", true, false, false],
    ["Saturday only", false, true, false],
    ["absence only", false, false, true],
    ["extra and Saturday", true, true, false],
    ["extra and absence", true, false, true],
    ["Saturday and absence", false, true, true],
    ["all", true, true, true],
  ] as Array<[string, boolean, boolean, boolean]>)("retains exact two-layout DOM for %s", async (_name, hasExtra, hasSaturday, hasAbsence) => {
    const items = [record({
      effective_extra_minutes: hasExtra ? 90 : 0,
      resolved_absence_cause: hasAbsence ? "permesso" : null,
      absence_minutes: hasAbsence ? 60 : 0,
    })];
    if (hasSaturday) items.push(record({ id: "r26-saturday", work_date: "2026-05-16" }));
    await workspace(items);
    const expected: ExpectedRow[] = [];
    if (hasExtra) expected.push(extra);
    if (hasSaturday) expected.push(saturday);
    if (hasAbsence) expected.push(permesso);
    await assertBothSummaries(expected);
    expect(api.updatePresenzeDailyRecord).not.toHaveBeenCalled();
  });

  test.each([
    ["ferie", "Ferie", "text-amber-700", "text-amber-800"],
    ["permesso", "Permesso", "text-sky-700", "text-sky-800"],
    ["malattia", "Malattia", "text-slate-600", "text-slate-700"],
    ["riposo", "Riposo", "text-violet-700", "text-violet-800"],
    ["festivita", "Festivita", "text-fuchsia-700", "text-fuchsia-800"],
    ["banca_ore", "Banca ore", "text-cyan-700", "text-cyan-800"],
    ["assenza_da_giustificare", "Assenza da giustificare", "text-rose-700", "text-rose-800"],
    ["causa_nuova", "causa nuova", "text-slate-600", "text-slate-700"],
  ])("retains %s label, value and tones in both layouts", async (cause, label, labelTone, valueTone) => {
    await workspace([record({ resolved_absence_cause: cause, absence_minutes: 65 })]);
    await assertBothSummaries([{ label, value: "1.1h", kind: "absence", labelTone, valueTone }]);
  });

  test("orders absences by descending aggregate minutes and retains insertion order for ties", async () => {
    await workspace([
      record({ resolved_absence_cause: "permesso", absence_minutes: 30 }),
      record({ id: "r26-ferie", work_date: "2026-05-19", resolved_absence_cause: "ferie", absence_minutes: 60 }),
      record({ id: "r26-permesso-again", work_date: "2026-05-20", resolved_absence_cause: "permesso", absence_minutes: 30 }),
      record({ id: "r26-malattia", work_date: "2026-05-21", resolved_absence_cause: "malattia", absence_minutes: 120 }),
    ]);
    await assertBothSummaries([
      { label: "Malattia", value: "2h", kind: "absence", labelTone: "text-slate-600", valueTone: "text-slate-700" },
      permesso,
      { label: "Ferie", value: "1h", kind: "absence", labelTone: "text-amber-700", valueTone: "text-amber-800" },
    ]);
  });

  test("sorts Saturday facts chronologically while retaining exact labels and separators", async () => {
    await workspace([
      record({ id: "r26-third", work_date: "2026-05-16", resolved_absence_cause: "malattia", absence_minutes: 120 }),
      record({ id: "r26-first-saturday", work_date: "2026-05-02", resolved_absence_cause: "permesso", absence_minutes: 60 }),
      record({ id: "r26-second", work_date: "2026-05-09", resolved_absence_cause: "ferie", absence_minutes: 180 }),
    ]);
    await assertBothSummaries([
      { ...saturday, value: "1° perm · 2° fer · 3° mal" },
      { label: "Ferie", value: "3h", kind: "absence", labelTone: "text-amber-700", valueTone: "text-amber-800" },
      { label: "Malattia", value: "2h", kind: "absence", labelTone: "text-slate-600", valueTone: "text-slate-700" },
      permesso,
    ]);
  });

  test("does not invent Saturday summaries for unworked days without a fact", async () => {
    await workspace([record({ work_date: "2026-05-16", ordinary_minutes: 0, operational_worked_minutes: 0 })]);
    await assertBothSummaries([]);
  });

  test.each([-60, 0, 120])("uses strict positive eligibility for effective extra %s", async (minutes) => {
    await workspace([record({ effective_extra_minutes: minutes })]);
    await assertBothSummaries(minutes > 0 ? [{ ...extra, value: "2h" }] : []);
  });

  test("keeps absence causes named like supplement keys distinct across rerenders", async () => {
    await workspace([
      record({ effective_extra_minutes: 90, resolved_absence_cause: "extra", absence_minutes: 60 }),
      record({ id: "r26-key-saturday", work_date: "2026-05-16", resolved_absence_cause: "saturday", absence_minutes: 120 }),
    ]);
    const expected: ExpectedRow[] = [
      extra, saturday,
      { label: "saturday", value: "2h", kind: "absence", labelTone: "text-slate-600", valueTone: "text-slate-700" },
      { label: "extra", value: "1h", kind: "absence", labelTone: "text-slate-600", valueTone: "text-slate-700" },
    ];
    await assertBothSummaries(expected);
    const gridLabel = within(heading().closest("th")!).getByText("extra", { exact: true });
    const apiCalls = api.listPresenzeDailyMatrixRecords.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    expect(screen.queryByText("Riepilogo operativo mese")).not.toBeInTheDocument();
    expect(within(heading().closest("th")!).getByText("extra", { exact: true })).toBe(gridLabel);
    await assertBothSummaries(expected);
    expect(api.listPresenzeDailyMatrixRecords).toHaveBeenCalledTimes(apiCalls);
    expect(api.getPresenzeDailyRecord).not.toHaveBeenCalled();
  });

  test("refreshes both summaries after an unchanged KM command without replacing the input", async () => {
    const original = record({ effective_extra_minutes: 90, resolved_absence_cause: "permesso", absence_minutes: 60 });
    await workspace([original]);
    await assertBothSummaries([extra, permesso]);
    const input = screen.getByLabelText("KM 2026-05-18");
    let resolve!: (value: PresenzeDailyRecord) => void;
    api.updatePresenzeDailyRecord.mockReturnValue(new Promise<PresenzeDailyRecord>((resolvePromise) => { resolve = resolvePromise; }));
    fireEvent.change(input, { target: { value: "7" } });
    fireEvent.blur(input);
    expect(api.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.stringMatching(/^r26-token-/), original.id, { km_value: 7 });
    expect(api.updatePresenzeDailyRecord).toHaveBeenCalledTimes(1);
    expect(input).toBeDisabled();
    assertGridSummary([extra, permesso]);
    assertModalSummary([extra, permesso]);
    await act(async () => resolve({ ...original, km_value: 7, effective_extra_minutes: 120, resolved_absence_cause: "malattia", absence_minutes: 90 }));
    await waitFor(() => expect(input).toBeEnabled());
    expect(screen.getByLabelText("KM 2026-05-18")).toBe(input);
    expect(input).toHaveValue("7");
    const updated: ExpectedRow[] = [
      { ...extra, value: "2h" },
      { label: "Malattia", value: "1.5h", kind: "absence", labelTone: "text-slate-600", valueTone: "text-slate-700" },
    ];
    assertGridSummary(updated);
    assertModalSummary(updated);
    expect(api.getPresenzeDailyRecord).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    await assertBothSummaries(updated);
  });
});
