import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import UtenzeSubjectDetailPage from "@/app/utenze/[id]/page";
import type { AnagraficaDocument, AnagraficaSubjectDetail, CurrentUser } from "@/types/api";

const api = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  getStoredAccessToken: vi.fn(), clearStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn<typeof import("@/lib/api").getCurrentUser>(),
  getMyPermissions: vi.fn<typeof import("@/lib/api").getMyPermissions>(),
  getUtenzeSubject: vi.fn<typeof import("@/lib/api").getUtenzeSubject>(),
  getUtenzeSubjectPaymentNotices: vi.fn<typeof import("@/lib/api").getUtenzeSubjectPaymentNotices>(),
  getUtenzeSubjectNasImportStatus: vi.fn<typeof import("@/lib/api").getUtenzeSubjectNasImportStatus>(),
  updateUtenzeDocument: vi.fn<typeof import("@/lib/api").updateUtenzeDocument>(),
  classifyUtenzeDocumentContent: vi.fn<typeof import("@/lib/api").classifyUtenzeDocumentContent>(),
  deleteUtenzeDocument: vi.fn<typeof import("@/lib/api").deleteUtenzeDocument>(),
  sendPresenceHeartbeat: vi.fn<typeof import("@/lib/api").sendPresenceHeartbeat>(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "subject-r103" }), useRouter: () => api.router,
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
  updateUtenzeDocument: api.updateUtenzeDocument,
  classifyUtenzeDocumentContent: api.classifyUtenzeDocumentContent,
  deleteUtenzeDocument: api.deleteUtenzeDocument,
  sendPresenceHeartbeat: api.sendPresenceHeartbeat,
}));

const token = "r103-collection-token";
const timestamp = "2026-10-15T09:00:00Z";

function userFixture(): CurrentUser {
  return {
    id: 103, username: "r103", email: "r103@example.invalid", role: "viewer", is_active: true,
    module_accessi: false, module_rete: false, module_inventario: false, module_catasto: false,
    module_utenze: true, module_operazioni: false, module_riordino: false,
    module_ruolo: false, module_presenze: false, enabled_modules: ["utenze"],
  };
}
function documentFixture(filename: string, overrides: Partial<AnagraficaDocument> = {}): AnagraficaDocument {
  return {
    id: `r103-${filename}`, filename, relative_path: filename, nas_path: `/archive/${filename}`,
    extension: ".pdf", is_pdf: true, doc_type: "altro", classification_source: "manual",
    smart_category: "other", smart_category_label: "Altro da classificare", smart_priority: 10,
    smart_confidence: 0, smart_reason: null, content_classification_status: "not_started",
    content_category: null, content_category_label: null, content_confidence: null,
    content_reason: null, content_excerpt: null, content_classification_source: null,
    content_classified_at: null, content_classification_error: null, warnings: [], ...overrides,
  };
}
function subjectFixture(documents: AnagraficaDocument[]): AnagraficaSubjectDetail {
  return {
    id: "subject-r103", subject_type: "company", status: "active", source_system: "campaign-r103",
    source_external_id: null, source_name_raw: "Azienda R103", nas_folder_path: null,
    nas_folder_letter: null, requires_review: false, imported_at: null,
    created_at: timestamp, updated_at: timestamp, person: null,
    company: {
      subject_id: "subject-r103", ragione_sociale: "Azienda R103", partita_iva: "12345678901",
      codice_fiscale: null, forma_giuridica: null, sede_legale: null, comune_sede: null,
      cap: null, email_pec: null, telefono: null, note: null, created_at: timestamp, updated_at: timestamp,
    },
    documents, catasto_documents: [], audit_log: [],
  };
}
async function ready(documents: AnagraficaDocument[]) {
  api.getUtenzeSubject.mockResolvedValue(subjectFixture(documents));
  render(<UtenzeSubjectDetailPage />);
  await screen.findByText("R103 NAS pronto");
  await act(async () => {});
  expect(api.getUtenzeSubject).toHaveBeenCalledExactlyOnceWith(token, "subject-r103");
}
function collectionElement(): HTMLElement {
  const article = screen.getByRole("searchbox", { name: "Cerca documenti associati" }).closest("article");
  if (!(article instanceof HTMLElement)) throw new Error("Missing actual document collection article");
  return article;
}
function collection() { return within(collectionElement()); }
function visibleFilenames(): string[] {
  return collection().getAllByRole("button")
    .filter((button) => button.getAttribute("role") === "button")
    .map((row) => within(row).getByText(/^[^/]+\.pdf$/).textContent ?? "");
}
function sectionFor(filename: string): HTMLElement {
  const section = collection().getByText(filename).closest("section");
  if (!(section instanceof HTMLElement)) throw new Error("Missing actual document group section");
  return section;
}
function search(query: string) {
  fireEvent.change(collection().getByRole("searchbox", { name: "Cerca documenti associati" }), { target: { value: query } });
}
function selectCategory(name: string) {
  const button = collection().getByRole("button", { name });
  expect(button).toBeEnabled();
  fireEvent.click(button);
}
function repeatedDocuments(): AnagraficaDocument[] {
  return [6, 2, 4, 1, 5, 3].map((number) => documentFixture(`repeat-${number}.pdf`, {
    smart_category: "contract", smart_category_label: "Contratti e convenzioni", smart_priority: 50,
  })).concat([
    documentFixture("other-2.pdf"), documentFixture("other-1.pdf"),
  ]);
}

beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState(null, "", "/utenze/subject-r103?embedded=1");
  api.getStoredAccessToken.mockReturnValue(token);
  api.getCurrentUser.mockResolvedValue(userFixture());
  api.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });
  api.getUtenzeSubjectPaymentNotices.mockResolvedValue([]);
  api.getUtenzeSubjectNasImportStatus.mockResolvedValue({
    can_import_from_nas: false, missing_in_nas: true, matched_folder_path: null,
    matched_folder_name: null, total_files_in_nas: 0, pending_files_in_nas: 0, message: "R103 NAS pronto",
  });
  api.sendPresenceHeartbeat.mockResolvedValue({ ok: true, last_seen_at: timestamp });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("R103 real document collection grouping and collapse", () => {
  test("exactly five documents remain fully visible in filename order without expansion controls", async () => {
    const documents = [5, 2, 4, 1, 3].map((number) => documentFixture(`boundary-${number}.pdf`));
    const originalOrder = documents.map((document) => document.filename);
    await ready(documents);
    expect(visibleFilenames()).toEqual(["boundary-1.pdf", "boundary-2.pdf", "boundary-3.pdf", "boundary-4.pdf", "boundary-5.pdf"]);
    expect(collection().getByText("5 documenti")).toBeVisible();
    expect(collection().queryByRole("button", { name: /Mostra altri|Mostra meno/ })).not.toBeInTheDocument();
    expect(collection().getByRole("button", { name: "Altro da classificare 5" })).toBeVisible();
    expect(documents.map((document) => document.filename)).toEqual(originalOrder);
  });

  test("priority then filename determine the first five, while expansion restores every grouped item", async () => {
    await ready([
      documentFixture("zero.pdf", { smart_category: "zero", smart_category_label: "Zero", smart_priority: 0 }),
      documentFixture("internal.pdf", { smart_category: "internal_practice", smart_category_label: "Pratiche interne", smart_priority: 40 }),
      documentFixture("debt.pdf", { smart_category: "debt_payment", smart_category_label: "Pagamenti e debito", smart_priority: 70 }),
      documentFixture("zeta-legal.pdf", { smart_category: "legal_action", smart_category_label: "Azioni legali", smart_priority: 100 }),
      documentFixture("contract.pdf", { smart_category: "contract", smart_category_label: "Contratti e convenzioni", smart_priority: 50 }),
      documentFixture("alpha-legal.pdf", { smart_category: "legal_action", smart_category_label: "Azioni legali", smart_priority: 100 }),
      documentFixture("notice.pdf", { smart_category: "notification", smart_category_label: "Notifiche e relate", smart_priority: 90 }),
      documentFixture("ordinary.pdf"),
    ]);
    expect(visibleFilenames()).toEqual(["alpha-legal.pdf", "zeta-legal.pdf", "notice.pdf", "debt.pdf", "contract.pdf"]);
    expect(collection().getByText("Sono presenti altri 3 documenti oltre ai primi 5.")).toBeVisible();
    expect(collection().getByText("Visualizzati 5 documenti su 8.")).toBeVisible();
    expect(collection().getByRole("button", { name: "Pratiche interne 1" })).toBeVisible();
    expect(collection().queryByText("internal.pdf")).not.toBeInTheDocument();
    fireEvent.click(collection().getByRole("button", { name: "Mostra altri 3 documenti" }));
    expect(visibleFilenames()).toEqual(["alpha-legal.pdf", "zeta-legal.pdf", "notice.pdf", "debt.pdf", "contract.pdf", "internal.pdf", "ordinary.pdf", "zero.pdf"]);
    expect(collection().getByText("Stai visualizzando tutti i 8 documenti associati.")).toBeVisible();
    expect(within(sectionFor("zero.pdf")).getByText("1 documento · priorità 0")).toBeVisible();
    expect(within(sectionFor("alpha-legal.pdf")).getByText("2 documenti · priorità 100")).toBeVisible();
    fireEvent.click(collection().getByRole("button", { name: "Mostra meno" }));
    expect(visibleFilenames()).toHaveLength(5);
    expect(collection().queryByText("zero.pdf")).not.toBeInTheDocument();
  });

  test("equal-priority groups use label order, preserving filename order inside each group", async () => {
    await ready([
      documentFixture("a-zeta.pdf", { smart_category: "zeta", smart_category_label: "Zeta", smart_priority: 50 }),
      documentFixture("z-alpha.pdf", { smart_category: "alpha", smart_category_label: "Alpha", smart_priority: 50 }),
      documentFixture("a-alpha.pdf", { smart_category: "alpha", smart_category_label: "Alpha", smart_priority: 50 }),
    ]);
    expect(visibleFilenames()).toEqual(["a-alpha.pdf", "z-alpha.pdf", "a-zeta.pdf"]);
    expect(collection().getAllByRole("button").filter((button) => /^(Alpha|Zeta) \d$/.test(button.textContent ?? "")).map((button) => button.textContent)).toEqual(["Alpha 2", "Zeta 1"]);
    expect(within(sectionFor("a-alpha.pdf")).getByText("2 documenti · priorità 50")).toBeVisible();
  });

  test("category options retain first source metadata while reading groups retain the first sorted item", async () => {
    await ready([
      documentFixture("first-source.pdf", { smart_category: "same", smart_category_label: "Original group", smart_priority: 40 }),
      documentFixture("first-sorted.pdf", { smart_category: "same", smart_category_label: "Sorted group", smart_priority: 90 }),
    ]);
    expect(collection().getByRole("button", { name: "Original group 2" })).toBeVisible();
    expect(visibleFilenames()).toEqual(["first-sorted.pdf", "first-source.pdf"]);
    expect(within(sectionFor("first-sorted.pdf")).getByText("Sorted group")).toBeVisible();
    expect(within(sectionFor("first-sorted.pdf")).getByText("2 documenti · priorità 90")).toBeVisible();
    expect(sectionFor("first-source.pdf")).toBe(sectionFor("first-sorted.pdf"));
  });

  test.each([
    { confidence: 0.85, label: "alta" }, { confidence: 0.849, label: "media" },
    { confidence: 0.6, label: "media" }, { confidence: 0.599, label: "bassa" },
    { confidence: 0, label: "bassa" },
  ])("collection displays confidence $confidence as $label", async ({ confidence, label }) => {
    await ready([documentFixture("confidence.pdf", { smart_confidence: confidence })]);
    expect(within(sectionFor("confidence.pdf")).getByText(`confidenza ${label}`)).toBeVisible();
  });
});

type SearchField = keyof Pick<AnagraficaDocument,
  "filename" | "nas_path" | "doc_type" | "classification_source" | "smart_category" |
  "smart_category_label" | "smart_reason" | "content_category" | "content_category_label" |
  "content_reason" | "content_excerpt" | "content_classification_source"
>;
const searchFields: SearchField[] = [
  "filename", "nas_path", "doc_type", "classification_source", "smart_category",
  "smart_category_label", "smart_reason", "content_category", "content_category_label",
  "content_reason", "content_excerpt", "content_classification_source",
];

describe("R103 real document collection search and category transitions", () => {
  test.each(searchFields)("search matches %s case-insensitively with trimmed query and no mutation", async (field) => {
    const matchingFilename = field === "filename" ? "NeEdLe.pdf" : "matched.pdf";
    const matching = documentFixture(matchingFilename, { [field]: field === "filename" ? matchingFilename : "NeEdLe" });
    await ready([documentFixture("unrelated.pdf"), matching]);
    search("  nEeDlE  ");
    await waitFor(() => expect(visibleFilenames()).toEqual([matchingFilename]));
    expect(collection().getByText("1 documenti su 2")).toBeVisible();
    expect(collection().getByText("Filtro attivo su nome file, percorso, tipo, categoria e origine classificazione.")).toBeVisible();
    expect(collection().getByRole("button", { name: "Tutti 1" })).toBeVisible();
    expect(within(sectionFor(matchingFilename)).getByRole("combobox")).toBeDisabled();
    expect(collection().queryByRole("button", { name: "Rimuovi" })).not.toBeInTheDocument();
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(1);
    expect(api.updateUtenzeDocument).not.toHaveBeenCalled();
    expect(api.classifyUtenzeDocumentContent).not.toHaveBeenCalled();
    expect(api.deleteUtenzeDocument).not.toHaveBeenCalled();
    expect(api.router.push).not.toHaveBeenCalled();
  });

  test("text search exposes all six matches without a collapse control or irrelevant category options", async () => {
    await ready(repeatedDocuments());
    search("repeat-");
    await waitFor(() => expect(visibleFilenames()).toEqual(["repeat-1.pdf", "repeat-2.pdf", "repeat-3.pdf", "repeat-4.pdf", "repeat-5.pdf", "repeat-6.pdf"]));
    expect(collection().getByRole("button", { name: "Tutti 6" })).toBeVisible();
    expect(collection().getByRole("button", { name: "Contratti e convenzioni 6" })).toBeVisible();
    expect(collection().queryByRole("button", { name: "Altro da classificare 2" })).not.toBeInTheDocument();
    expect(collection().queryByRole("button", { name: /Mostra altri|Mostra meno/ })).not.toBeInTheDocument();
    expect(collection().getByText("6 documenti su 8")).toBeVisible();
  });

  test("category filter exposes six matches and Tutti restores the default collapsed first five", async () => {
    await ready(repeatedDocuments());
    selectCategory("Contratti e convenzioni 6");
    expect(visibleFilenames()).toEqual(["repeat-1.pdf", "repeat-2.pdf", "repeat-3.pdf", "repeat-4.pdf", "repeat-5.pdf", "repeat-6.pdf"]);
    expect(collection().getByText("6 documenti su 8")).toBeVisible();
    expect(collection().getByRole("button", { name: "Altro da classificare 2" })).toBeVisible();
    expect(collection().queryByRole("button", { name: /Mostra altri|Mostra meno/ })).not.toBeInTheDocument();
    selectCategory("Tutti 8");
    expect(visibleFilenames()).toEqual(["repeat-1.pdf", "repeat-2.pdf", "repeat-3.pdf", "repeat-4.pdf", "repeat-5.pdf"]);
    expect(collection().getByRole("button", { name: "Mostra altri 3 documenti" })).toBeVisible();
    expect(collection().queryByRole("button", { name: "Azzera filtri" })).not.toBeInTheDocument();
  });

  test("changing category after expansion resets expansion and an explicit filter reset clears both filters", async () => {
    await ready(repeatedDocuments());
    fireEvent.click(collection().getByRole("button", { name: "Mostra altri 3 documenti" }));
    expect(visibleFilenames()).toHaveLength(8);
    selectCategory("Contratti e convenzioni 6");
    selectCategory("Tutti 8");
    expect(visibleFilenames()).toHaveLength(5);
    fireEvent.click(collection().getByRole("button", { name: "Mostra altri 3 documenti" }));
    search("repeat-");
    await waitFor(() => expect(visibleFilenames()).toHaveLength(6));
    selectCategory("Contratti e convenzioni 6");
    fireEvent.click(collection().getByRole("button", { name: "Azzera filtri" }));
    await waitFor(() => expect(visibleFilenames()).toHaveLength(5));
    expect(collection().getByRole("searchbox", { name: "Cerca documenti associati" })).toHaveValue("");
    expect(collection().getByRole("button", { name: "Tutti 8" })).toBeVisible();
    expect(collection().getByRole("button", { name: "Altro da classificare 2" })).toBeVisible();
    expect(collection().getByRole("button", { name: "Mostra altri 3 documenti" })).toBeVisible();
    expect(collection().queryByRole("button", { name: "Azzera filtri" })).not.toBeInTheDocument();
  });

  test("whitespace alone is not an active search and does not bypass default collapse", async () => {
    await ready(repeatedDocuments());
    search("   ");
    await act(async () => {});
    expect(collection().getByRole("searchbox", { name: "Cerca documenti associati" })).toHaveValue("   ");
    expect(visibleFilenames()).toHaveLength(5);
    expect(collection().queryByRole("button", { name: "Azzera filtri" })).not.toBeInTheDocument();
    expect(collection().getByRole("button", { name: "Mostra altri 3 documenti" })).toBeVisible();
  });

  test("a no-match search keeps the collection searchable and reset restores the original list", async () => {
    await ready(repeatedDocuments());
    search("absent-r103");
    expect(await collection().findByText("Nessun documento corrisponde al filtro impostato.")).toBeVisible();
    expect(collection().getByText("0 documenti su 8")).toBeVisible();
    expect(collection().getByRole("button", { name: "Tutti 0" })).toBeVisible();
    expect(collection().queryByRole("button", { name: /Contratti e convenzioni|Altro da classificare/ })).not.toBeInTheDocument();
    expect(collection().queryByText("Nessun documento associato.")).not.toBeInTheDocument();
    expect(collection().queryByRole("button", { name: /Mostra altri|Mostra meno/ })).not.toBeInTheDocument();
    fireEvent.click(collection().getByRole("button", { name: "Azzera filtri" }));
    await waitFor(() => expect(visibleFilenames()).toHaveLength(5));
    expect(collection().queryByText("Nessun documento corrisponde al filtro impostato.")).not.toBeInTheDocument();
  });

  test("search preserves a selected category even when its option disappears; Tutti clears only that category", async () => {
    await ready(repeatedDocuments());
    selectCategory("Contratti e convenzioni 6");
    search("other-");
    expect(await collection().findByText("Nessun documento corrisponde al filtro impostato.")).toBeVisible();
    expect(collection().getByText("0 documenti su 8")).toBeVisible();
    expect(collection().queryByRole("button", { name: "Contratti e convenzioni 6" })).not.toBeInTheDocument();
    expect(collection().getByRole("button", { name: "Altro da classificare 2" })).toBeVisible();
    selectCategory("Tutti 2");
    expect(visibleFilenames()).toEqual(["other-1.pdf", "other-2.pdf"]);
    expect(collection().getByRole("searchbox", { name: "Cerca documenti associati" })).toHaveValue("other-");
    expect(collection().getByText("2 documenti su 8")).toBeVisible();
    expect(collection().getByRole("button", { name: "Azzera filtri" })).toBeVisible();
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(1);
  });
});
