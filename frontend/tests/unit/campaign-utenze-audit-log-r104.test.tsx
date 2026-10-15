import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import UtenzeSubjectDetailPage from "@/app/utenze/[id]/page";
import type { AnagraficaAuditLog, AnagraficaSubjectDetail, CurrentUser } from "@/types/api";

const api = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  getStoredAccessToken: vi.fn(), clearStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn<typeof import("@/lib/api").getCurrentUser>(),
  getMyPermissions: vi.fn<typeof import("@/lib/api").getMyPermissions>(),
  getUtenzeSubject: vi.fn<typeof import("@/lib/api").getUtenzeSubject>(),
  getUtenzeSubjectPaymentNotices: vi.fn<typeof import("@/lib/api").getUtenzeSubjectPaymentNotices>(),
  getUtenzeSubjectNasImportStatus: vi.fn<typeof import("@/lib/api").getUtenzeSubjectNasImportStatus>(),
  getUtenzeSubjectNasCandidates: vi.fn<typeof import("@/lib/api").getUtenzeSubjectNasCandidates>(),
  updateUtenzeSubject: vi.fn<typeof import("@/lib/api").updateUtenzeSubject>(),
  updateUtenzeDocument: vi.fn<typeof import("@/lib/api").updateUtenzeDocument>(),
  classifyUtenzeDocumentContent: vi.fn<typeof import("@/lib/api").classifyUtenzeDocumentContent>(),
  deleteUtenzeDocument: vi.fn<typeof import("@/lib/api").deleteUtenzeDocument>(),
  uploadUtenzeSubjectDocument: vi.fn<typeof import("@/lib/api").uploadUtenzeSubjectDocument>(),
  importUtenzeSubjectFromNas: vi.fn<typeof import("@/lib/api").importUtenzeSubjectFromNas>(),
  createElaborazioneRichiesta: vi.fn<typeof import("@/lib/api").createElaborazioneRichiesta>(),
  downloadUtenzeDocumentBlob: vi.fn<typeof import("@/lib/api").downloadUtenzeDocumentBlob>(),
  downloadCatastoDocumentBlob: vi.fn<typeof import("@/lib/api").downloadCatastoDocumentBlob>(),
  sendPresenceHeartbeat: vi.fn<typeof import("@/lib/api").sendPresenceHeartbeat>(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "subject-r104" }), useRouter: () => api.router,
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
}));
vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: api.getStoredAccessToken, clearStoredAccessToken: api.clearStoredAccessToken,
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getCurrentUser: api.getCurrentUser, getMyPermissions: api.getMyPermissions,
  getUtenzeSubject: api.getUtenzeSubject,
  getUtenzeSubjectPaymentNotices: api.getUtenzeSubjectPaymentNotices,
  getUtenzeSubjectNasImportStatus: api.getUtenzeSubjectNasImportStatus,
  getUtenzeSubjectNasCandidates: api.getUtenzeSubjectNasCandidates,
  updateUtenzeSubject: api.updateUtenzeSubject, updateUtenzeDocument: api.updateUtenzeDocument,
  classifyUtenzeDocumentContent: api.classifyUtenzeDocumentContent,
  deleteUtenzeDocument: api.deleteUtenzeDocument,
  uploadUtenzeSubjectDocument: api.uploadUtenzeSubjectDocument,
  importUtenzeSubjectFromNas: api.importUtenzeSubjectFromNas,
  createElaborazioneRichiesta: api.createElaborazioneRichiesta,
  downloadUtenzeDocumentBlob: api.downloadUtenzeDocumentBlob,
  downloadCatastoDocumentBlob: api.downloadCatastoDocumentBlob,
  sendPresenceHeartbeat: api.sendPresenceHeartbeat,
}));

const token = "r104-audit-token";
const timestamp = "2026-10-15T09:00:00Z";

function userFixture(): CurrentUser {
  return {
    id: 104, username: "r104", email: "r104@example.invalid", role: "viewer", is_active: true,
    module_accessi: false, module_rete: false, module_inventario: false, module_catasto: false,
    module_utenze: true, module_operazioni: false, module_riordino: false,
    module_ruolo: false, module_presenze: false, enabled_modules: ["utenze"],
  };
}

function eventFixture(overrides: Partial<AnagraficaAuditLog> = {}): AnagraficaAuditLog {
  return {
    id: "event-r104", subject_id: "subject-r104", action: "R104 aggiornamento soggetto",
    changed_by_user_id: 104, changed_at: timestamp,
    diff_json: { status: { before: "review", after: "active" } }, ...overrides,
  };
}

function subjectFixture(auditLog: AnagraficaAuditLog[]): AnagraficaSubjectDetail {
  return {
    id: "subject-r104", subject_type: "company", status: "active", source_system: "campaign-r104",
    source_external_id: null, source_name_raw: "Azienda R104", nas_folder_path: null,
    nas_folder_letter: null, requires_review: false, imported_at: null,
    created_at: timestamp, updated_at: timestamp, person: null,
    company: {
      subject_id: "subject-r104", ragione_sociale: "Azienda R104", partita_iva: "12345678901",
      codice_fiscale: null, forma_giuridica: null, sede_legale: null, comune_sede: null,
      cap: null, email_pec: null, telefono: null, note: null, created_at: timestamp, updated_at: timestamp,
    },
    documents: [], catasto_documents: [], audit_log: auditLog,
  };
}

function auditArticle(): HTMLElement {
  const article = screen.getByText("Audit log", { exact: true }).closest("article");
  if (!(article instanceof HTMLElement)) throw new Error("Missing actual Audit log article");
  return article;
}

function audit() { return within(auditArticle()); }

async function ready(auditLog: AnagraficaAuditLog[]) {
  api.getUtenzeSubject.mockResolvedValue(subjectFixture(auditLog));
  render(<UtenzeSubjectDetailPage />);
  await screen.findByText("R104 NAS pronto");
  await act(async () => {});
  expect(audit().getByText("Tracce minime delle operazioni effettuate sul soggetto.")).toBeVisible();
}

function expectOnlyInitialReads() {
  expect(api.getUtenzeSubject).toHaveBeenCalledExactlyOnceWith(token, "subject-r104");
  expect(api.getUtenzeSubjectPaymentNotices).toHaveBeenCalledExactlyOnceWith(token, "subject-r104");
  expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledExactlyOnceWith(token, "subject-r104");
  for (const request of [
    api.getUtenzeSubjectNasCandidates, api.updateUtenzeSubject, api.updateUtenzeDocument,
    api.classifyUtenzeDocumentContent, api.deleteUtenzeDocument, api.uploadUtenzeSubjectDocument,
    api.importUtenzeSubjectFromNas, api.createElaborazioneRichiesta,
    api.downloadUtenzeDocumentBlob, api.downloadCatastoDocumentBlob,
  ]) {
    expect(request).not.toHaveBeenCalled();
  }
  expect(api.router.push).not.toHaveBeenCalled();
  expect(api.router.replace).not.toHaveBeenCalled();
}

beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState(null, "", "/utenze/subject-r104?embedded=1");
  api.getStoredAccessToken.mockReturnValue(token);
  api.getCurrentUser.mockResolvedValue(userFixture());
  api.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });
  api.getUtenzeSubjectPaymentNotices.mockResolvedValue([]);
  api.getUtenzeSubjectNasImportStatus.mockResolvedValue({
    can_import_from_nas: false, missing_in_nas: true, matched_folder_path: null,
    matched_folder_name: null, total_files_in_nas: 0, pending_files_in_nas: 0, message: "R104 NAS pronto",
  });
  api.sendPresenceHeartbeat.mockResolvedValue({ ok: true, last_seen_at: timestamp });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("R104 real Audit log disclosure", () => {
  test("empty log starts collapsed and supports expand, collapse and reexpand without requests", async () => {
    await ready([]);
    expect(audit().getByRole("button", { name: "Espandi" })).toBeEnabled();
    expect(audit().getByText("Audit log ridotto di default. Nessun evento registrato.")).toBeVisible();
    expect(audit().queryByRole("button", { name: "Riduci" })).not.toBeInTheDocument();
    expect(auditArticle().querySelector("pre")).toBeNull();
    for (const cycle of [1, 2]) {
      fireEvent.click(audit().getByRole("button", { name: "Espandi" }));
      expect(audit().getByText("Nessun evento registrato.", { exact: true })).toBeVisible();
      expect(audit().queryByText(/Audit log ridotto di default/)).not.toBeInTheDocument();
      expect(auditArticle().querySelector("pre")).toBeNull();
      expectOnlyInitialReads();
      if (cycle === 1) {
        fireEvent.click(audit().getByRole("button", { name: "Riduci" }));
        expect(audit().getByText("Audit log ridotto di default. Nessun evento registrato.")).toBeVisible();
      }
    }
    expect(audit().getByRole("button", { name: "Riduci" })).toBeVisible();
  });

  test("populated log starts collapsed with its count but no action, date or event body", async () => {
    const events = [eventFixture(), eventFixture({ id: "second-r104", action: "R104 importazione" })];
    await ready(events);
    expect(audit().getByText("Audit log ridotto di default. 2 eventi disponibili.")).toBeVisible();
    expect(audit().getByRole("button", { name: "Espandi" })).toBeVisible();
    for (const event of events) {
      expect(audit().queryByText(event.action, { exact: true })).not.toBeInTheDocument();
      const date = new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(event.changed_at));
      expect(audit().queryByText(date, { exact: true })).not.toBeInTheDocument();
    }
    expect(auditArticle().querySelector("pre")).toBeNull();
    expect(audit().queryByText("Nessun evento registrato.", { exact: true })).not.toBeInTheDocument();
    expectOnlyInitialReads();
  });

  test("expansion renders actions, Italian dates and payloads in response order, not date or action order", async () => {
    const events = [
      eventFixture({ id: "latest-r104", action: "Zulu R104", changed_at: "2026-10-15T15:20:00Z", diff_json: { order: "first" } }),
      eventFixture({ id: "oldest-r104", action: "Alpha R104", changed_at: "2026-01-02T06:45:00Z", diff_json: { order: "second" } }),
      eventFixture({ id: "middle-r104", action: "Mike R104", changed_at: "2026-06-09T10:05:00Z", diff_json: { order: "third" } }),
    ];
    await ready(events);
    fireEvent.click(audit().getByRole("button", { name: "Espandi" }));
    expect(audit().getByRole("button", { name: "Riduci" })).toBeVisible();
    expect(audit().queryByText(/Audit log ridotto di default/)).not.toBeInTheDocument();
    const bodies = Array.from(auditArticle().querySelectorAll("pre"));
    expect(bodies).toHaveLength(events.length);
    const formatter = new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" });
    for (const [index, event] of events.entries()) {
      const row = bodies[index].parentElement;
      if (!(row instanceof HTMLElement)) throw new Error("Missing actual Audit log event row");
      expect(within(row).getByText(event.action, { exact: true })).toBeVisible();
      expect(within(row).getByText(formatter.format(new Date(event.changed_at)), { exact: true })).toBeVisible();
      expect(bodies[index].textContent).toBe(JSON.stringify(event.diff_json, null, 2));
    }
    expectOnlyInitialReads();
  });

  test.each<{ label: string; diff: AnagraficaAuditLog["diff_json"] }>([
    { label: "nested object", diff: { before: { active: false, count: 0 }, after: { active: true, labels: ["uno", "due"] } } },
    { label: "array", diff: [{ field: "note", before: null, after: "<b>testo letterale</b>" }, false, 0] },
    { label: "null", diff: null },
  ])("expanded $label payload uses literal pretty JSON", async ({ diff }) => {
    await ready([eventFixture({ diff_json: diff })]);
    fireEvent.click(audit().getByRole("button", { name: "Espandi" }));
    const bodies = auditArticle().querySelectorAll("pre");
    expect(bodies).toHaveLength(1);
    expect(bodies[0]).toBeVisible();
    expect(bodies[0].textContent).toBe(JSON.stringify(diff, null, 2));
    expect(bodies[0].childElementCount).toBe(0);
    expectOnlyInitialReads();
  });

  test("collapse and reexpand restore unchanged events without mutation, reload or navigation", async () => {
    const events = [eventFixture(), eventFixture({ id: "other-r104", action: "R104 seconda operazione", diff_json: ["originale", 104] })];
    const originalEvents = JSON.stringify(events);
    const originalItems = [...events];
    await ready(events);
    fireEvent.click(audit().getByRole("button", { name: "Espandi" }));
    const expandedText = auditArticle().textContent;
    fireEvent.click(audit().getByRole("button", { name: "Riduci" }));
    expect(audit().getByText("Audit log ridotto di default. 2 eventi disponibili.")).toBeVisible();
    expect(auditArticle().querySelector("pre")).toBeNull();
    for (const event of events) {
      expect(audit().queryByText(event.action, { exact: true })).not.toBeInTheDocument();
    }
    expectOnlyInitialReads();
    fireEvent.click(audit().getByRole("button", { name: "Espandi" }));
    expect(auditArticle().textContent).toBe(expandedText);
    expect(Array.from(auditArticle().querySelectorAll("pre"), (body) => body.textContent)).toEqual(
      events.map((event) => JSON.stringify(event.diff_json, null, 2)),
    );
    expect(JSON.stringify(events)).toBe(originalEvents);
    expect(events[0]).toBe(originalItems[0]);
    expect(events[1]).toBe(originalItems[1]);
    expectOnlyInitialReads();
  });
});
